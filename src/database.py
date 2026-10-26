"""SQLAlchemy-managed SQLite storage with a compatible DB-API interface."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import URL, create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool

from src.models import Base


class Connection:
    """Expose SQLite cursors/Rows while SQLAlchemy owns the engine and pool.

    The starter's parameterized queries and transactional business layer keep
    their DB-API interface; declarative SQLAlchemy models own schema definitions.
    """
    def __init__(self, engine: Engine) -> None:
        self.engine = engine
        self._pooled = engine.raw_connection()
        self._driver: sqlite3.Connection = self._pooled.driver_connection
        self._driver.row_factory = sqlite3.Row

    def __getattr__(self, name: str) -> Any:
        return getattr(self._driver, name)

    def __enter__(self) -> Connection:
        self._driver.__enter__()
        return self

    def __exit__(self, *args: Any) -> bool:
        return self._driver.__exit__(*args)

    def close(self) -> None:
        self._pooled.close()
        self.engine.dispose()


def connect(path: str | Path = 'procureflow.db') -> Connection:
    engine = create_engine(URL.create('sqlite', database=str(path)),
                           connect_args={'check_same_thread': False, 'timeout': 15},
                           poolclass=StaticPool)

    @event.listens_for(engine, 'connect')
    def _configure(dbapi_conn: sqlite3.Connection, _: Any) -> None:
        dbapi_conn.execute('PRAGMA foreign_keys = ON')
        dbapi_conn.execute('PRAGMA busy_timeout = 15000')

    return Connection(engine)


def _columns(conn: Connection, table: str) -> set[str]:
    return {row['name'] for row in conn.execute(f'PRAGMA table_info({table})')}


def init_db(conn: Connection) -> None:
    """Create schema; migrate starter databases without deleting business rows."""
    product_columns = _columns(conn, 'products')
    proposal_columns = _columns(conn, 'proposals')
    # Only the original starter stored supplier identities exclusively inside
    # products. Subsequent startup must preserve missing-master exceptions.
    migrate_legacy_suppliers = bool(product_columns) and not _columns(conn, 'suppliers')
    with conn:
        if product_columns and 'reserved_qty' not in product_columns:
            conn.execute('ALTER TABLE products ADD COLUMN reserved_qty INTEGER NOT NULL DEFAULT 0 CHECK(reserved_qty >= 0)')
        additions = {
            'target_stock': 'INTEGER NOT NULL DEFAULT 0',
            'unit_cost_vnd': 'INTEGER NOT NULL DEFAULT 0',
            'supplier': "TEXT NOT NULL DEFAULT ''", 'snapshot_json': 'TEXT',
            'max_quantity': 'INTEGER', 'max_value_vnd': 'INTEGER',
        }
        for name, definition in additions.items():
            if proposal_columns and name not in proposal_columns:
                conn.execute(f'ALTER TABLE proposals ADD COLUMN {name} {definition}')
        if proposal_columns and 'unit_cost_vnd' not in proposal_columns:
            conn.execute('''UPDATE proposals SET unit_cost_vnd = COALESCE(
                (SELECT unit_cost_vnd FROM products WHERE products.sku=proposals.sku), 0),
                supplier = COALESCE((SELECT supplier FROM products WHERE products.sku=proposals.sku), '')''')
        audit_columns = _columns(conn, 'audit_logs')
        if audit_columns and 'before_json' not in audit_columns:
            conn.execute('ALTER TABLE audit_logs RENAME TO audit_logs_legacy')
            conn.execute('''CREATE TABLE audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                proposal_id INTEGER REFERENCES proposals(id), action TEXT NOT NULL,
                actor TEXT NOT NULL, comment TEXT, before_json TEXT, after_json TEXT,
                created_at TEXT NOT NULL)''')
            conn.execute('''INSERT INTO audit_logs (id,proposal_id,action,actor,comment,created_at)
                SELECT id,proposal_id,action,actor,comment,created_at FROM audit_logs_legacy''')
            conn.execute('DROP TABLE audit_logs_legacy')

    Base.metadata.create_all(conn.engine)
    with conn:
        if migrate_legacy_suppliers:
            conn.execute('''INSERT OR IGNORE INTO suppliers(name, lead_time_days)
                SELECT supplier, MIN(lead_time_days) FROM products
                WHERE TRIM(supplier) <> '' GROUP BY supplier''')
        conn.execute('''INSERT OR IGNORE INTO inventory(sku,on_hand,on_order,reserved_qty,updated_at)
            SELECT sku,on_hand,on_order,reserved_qty,? FROM products''', (now_utc(),))
        duplicate_drafts = conn.execute("""SELECT sku, COUNT(*) AS count FROM proposals
            WHERE status='DRAFT' GROUP BY sku HAVING COUNT(*) > 1""").fetchall()
        if not duplicate_drafts:
            conn.execute("""CREATE UNIQUE INDEX IF NOT EXISTS ix_proposals_one_draft_per_sku
                ON proposals(sku) WHERE status='DRAFT'""")
        else:
            # Preserve all legacy requests and make the conflict visible;
            # workflow transactions still prevent creating further duplicates.
            for row in duplicate_drafts:
                exists = conn.execute("""SELECT 1 FROM exceptions
                    WHERE sku=? AND exception_type='LEGACY_DUPLICATE_DRAFT' AND status='OPEN'""",
                    (row['sku'],)).fetchone()
                if not exists:
                    conn.execute("""INSERT INTO exceptions(sku,exception_type,severity,message,created_at)
                        VALUES(?,'LEGACY_DUPLICATE_DRAFT','WARNING',?,?)""",
                        (row['sku'], f'{row["count"]} legacy drafts preserved; review and reject redundant requests.', now_utc()))
    conn.executescript('''
        CREATE TRIGGER IF NOT EXISTS products_inventory_insert AFTER INSERT ON products
        BEGIN
            INSERT INTO inventory(sku,on_hand,on_order,reserved_qty,updated_at)
            VALUES(NEW.sku,NEW.on_hand,NEW.on_order,NEW.reserved_qty,strftime('%Y-%m-%dT%H:%M:%SZ','now'));
        END;
        CREATE TRIGGER IF NOT EXISTS products_inventory_update
        AFTER UPDATE OF on_hand,on_order,reserved_qty ON products
        WHEN OLD.on_hand != NEW.on_hand OR OLD.on_order != NEW.on_order OR OLD.reserved_qty != NEW.reserved_qty
        BEGIN
            UPDATE inventory SET on_hand=NEW.on_hand,on_order=NEW.on_order,reserved_qty=NEW.reserved_qty,
                updated_at=strftime('%Y-%m-%dT%H:%M:%SZ','now') WHERE sku=NEW.sku;
        END;
        CREATE TRIGGER IF NOT EXISTS inventory_products_update
        AFTER UPDATE OF on_hand,on_order,reserved_qty ON inventory
        WHEN OLD.on_hand != NEW.on_hand OR OLD.on_order != NEW.on_order OR OLD.reserved_qty != NEW.reserved_qty
        BEGIN
            UPDATE products SET on_hand=NEW.on_hand,on_order=NEW.on_order,reserved_qty=NEW.reserved_qty
                WHERE sku=NEW.sku AND (on_hand!=NEW.on_hand OR on_order!=NEW.on_order OR reserved_qty!=NEW.reserved_qty);
        END;
        CREATE TRIGGER IF NOT EXISTS audit_logs_no_update BEFORE UPDATE ON audit_logs
        BEGIN SELECT RAISE(ABORT,'Audit logs are append-only'); END;
        CREATE TRIGGER IF NOT EXISTS audit_logs_no_delete BEFORE DELETE ON audit_logs
        BEGIN SELECT RAISE(ABORT,'Audit logs are append-only'); END;
        CREATE TRIGGER IF NOT EXISTS approval_history_no_update BEFORE UPDATE ON approval_history
        BEGIN SELECT RAISE(ABORT,'Approval history is append-only'); END;
        CREATE TRIGGER IF NOT EXISTS approval_history_no_delete BEFORE DELETE ON approval_history
        BEGIN SELECT RAISE(ABORT,'Approval history is append-only'); END;
    ''')
    conn.commit()


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')
