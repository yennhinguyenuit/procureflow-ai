"""Import, migration, persistence, and audit integrity use isolated databases."""
import io
import json
import sqlite3
from datetime import date

import pytest
from openpyxl import Workbook

from src.data_import import import_dataset
from src.database import connect, init_db
from src.seed import seed_if_empty


AS_OF = date(2026, 10, 26)


@pytest.fixture
def db():
    conn = connect(':memory:')
    init_db(conn)
    seed_if_empty(conn, AS_OF)
    yield conn
    conn.close()


def test_inventory_import_updates_both_stores_and_records_evidence(db):
    raw = b'sku,on_hand,on_order,reserved_qty\nCF-001,12,20,3\n'
    assert import_dataset(db, raw, 'inventory.csv', 'inventory', 'tester', AS_OF) == 1
    product = db.execute("SELECT * FROM products WHERE sku='CF-001'").fetchone()
    inventory = db.execute("SELECT * FROM inventory WHERE sku='CF-001'").fetchone()
    assert (product['on_hand'], product['on_order'], product['reserved_qty']) == (12, 20, 3)
    assert (inventory['on_hand'], inventory['on_order'], inventory['reserved_qty']) == (12, 20, 3)
    log = db.execute("SELECT * FROM audit_logs WHERE action='DATA_IMPORTED'").fetchone()
    assert log['actor'] == 'tester'
    assert json.loads(log['before_json'])['records'][0]['on_hand'] == 26
    assert json.loads(log['after_json'])['records'][0]['on_hand'] == 12
    snapshot = db.execute("SELECT * FROM inventory_snapshots WHERE source='import:inventory'").fetchone()
    assert (snapshot['snapshot_date'], snapshot['on_hand']) == ('2026-10-26', 12)
    assert import_dataset(db, raw, 'inventory.csv', 'inventory', 'tester', AS_OF) == 0
    assert db.execute("SELECT COUNT(*) FROM audit_logs WHERE action='DATA_IMPORTED'").fetchone()[0] == 1


def test_import_is_atomic_when_later_record_references_unknown_sku(db):
    raw = b'sku,on_hand,on_order\nCF-001,1,0\nUNKNOWN,3,0\n'
    with pytest.raises(ValueError, match='Unknown SKU'):
        import_dataset(db, raw, 'inventory.csv', 'inventory', as_of=AS_OF)
    assert db.execute("SELECT on_hand FROM products WHERE sku='CF-001'").fetchone()[0] == 26
    assert db.execute("SELECT COUNT(*) FROM audit_logs WHERE action='DATA_IMPORTED'").fetchone()[0] == 0
    assert db.execute("SELECT COUNT(*) FROM inventory_snapshots WHERE source='import:inventory'").fetchone()[0] == 0


@pytest.mark.parametrize('raw, dataset', [
    (b'sku,on_hand,on_order\nCF-001,-1,0\n', 'inventory'),
    (b'sku,on_hand,on_order\nCF-001,1.5,0\n', 'inventory'),
    (b'sku,on_hand,on_order\nCF-001,,0\n', 'inventory'),
    (b'sku,on_hand,on_order\nCF-001,3,0\nCF-001,3,0\n', 'inventory'),
    (b'sku,on_hand,on_hand\nCF-001,3,3\n', 'inventory'),
    (b'sku,on_hand,on_order,extra\nCF-001,3,0,x\n', 'inventory'),
    (b'sale_date,sku,units\n2026-13-01,CF-001,2\n', 'sales'),
    (b'sale_date,sku,units\n20261026,CF-001,2\n', 'sales'),
    (b'sale_date,sku,units\n2026-10-27,CF-001,2\n', 'sales'),
    (b'sale_date,sku,units\n2026-10-26,CF-001,2\n2026-10-26,CF-001,2\n', 'sales'),
    (b'sku,on_hand,on_order\n', 'inventory'),
    (b'name,lead_time_days\nSupplier,0\n', 'suppliers'),
])
def test_invalid_files_are_rejected(db, raw, dataset):
    with pytest.raises(ValueError):
        import_dataset(db, raw, 'invalid.csv', dataset, as_of=AS_OF)


def test_xlsx_import_handles_date_cells_and_identical_reimport(db):
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(['sale_date', 'sku', 'units'])
    sheet.append([date(2026, 7, 1), 'CF-001', 17])
    output = io.BytesIO()
    workbook.save(output)
    raw = output.getvalue()
    assert import_dataset(db, raw, 'sales.xlsx', 'sales', as_of=AS_OF) == 1
    assert import_dataset(db, raw, 'sales.xlsx', 'sales', as_of=AS_OF) == 0
    assert db.execute("SELECT units FROM sales WHERE sale_date='2026-07-01' AND sku='CF-001'").fetchone()[0] == 17


def test_supplier_and_product_upsert_and_unknown_supplier_rejected(db):
    supplier = b'name,lead_time_days,contact_email\nDemo New,5,buyer@example.invalid\n'
    assert import_dataset(db, supplier, 'suppliers.csv', 'suppliers', as_of=AS_OF) == 1
    raw = (b'sku,product_name,supplier,lead_time_days,safety_stock,pack_size,unit_cost_vnd\n'
           b'NEW-001,New synthetic material,Demo New,5,10,5,12000\n')
    assert import_dataset(db, raw, 'products.csv', 'products', as_of=AS_OF) == 1
    assert import_dataset(db, raw, 'products.csv', 'products', as_of=AS_OF) == 0
    assert db.execute("SELECT on_hand FROM inventory WHERE sku='NEW-001'").fetchone()[0] == 0
    bad = raw.replace(b'Demo New,5,10', b'Missing Supplier,5,10')
    with pytest.raises(ValueError, match='Unknown supplier'):
        import_dataset(db, bad, 'products.csv', 'products', as_of=AS_OF)


def test_product_master_import_preserves_inventory_when_optional_columns_absent(db):
    raw = (b'sku,product_name,supplier,lead_time_days,safety_stock,pack_size,unit_cost_vnd\n'
           b'CF-001,Updated synthetic coffee,Demo supplier Alpha,5,18,10,180000\n')
    assert import_dataset(db, raw, 'products.csv', 'products', as_of=AS_OF) == 1
    p = db.execute("SELECT * FROM products WHERE sku='CF-001'").fetchone()
    assert (p['on_hand'], p['reserved_qty'], p['unit_cost_vnd']) == (26, 5, 180000)


def test_sales_conflict_rolls_back_earlier_rows(db):
    raw = b'sale_date,sku,units\n2026-07-01,CF-001,2\n2026-10-26,CF-001,999\n'
    with pytest.raises(ValueError, match='Conflicting'):
        import_dataset(db, raw, 'sales.csv', 'sales', as_of=AS_OF)
    assert db.execute("SELECT COUNT(*) FROM sales WHERE sale_date='2026-07-01'").fetchone()[0] == 0


def test_approved_orders_cannot_be_erased_by_inventory_import(db):
    db.execute('''INSERT INTO proposals(sku,avg_daily_demand,inventory_position,reorder_point,
        quantity,reason,status,created_at) VALUES('CF-001',10,26,68,50,'test','APPROVED','2026-10-26')''')
    db.execute("UPDATE products SET on_order=50 WHERE sku='CF-001'")
    db.commit()
    with pytest.raises(ValueError, match='APPROVED'):
        import_dataset(db, b'sku,on_hand,on_order\nCF-001,26,0\n', 'inventory.csv', 'inventory', as_of=AS_OF)
    assert db.execute("SELECT on_order FROM inventory WHERE sku='CF-001'").fetchone()[0] == 50


def test_direct_stock_updates_remain_synchronized(db):
    with db:
        db.execute("UPDATE products SET on_order=40 WHERE sku='CF-001'")
    assert db.execute("SELECT on_order FROM inventory WHERE sku='CF-001'").fetchone()[0] == 40
    with db:
        db.execute("UPDATE inventory SET reserved_qty=9 WHERE sku='CF-001'")
    assert db.execute("SELECT reserved_qty FROM products WHERE sku='CF-001'").fetchone()[0] == 9


def test_reinitialization_does_not_recreate_a_missing_supplier(db):
    with db:
        db.execute("DELETE FROM suppliers WHERE name='Demo supplier Alpha'")
    init_db(db)
    assert db.execute("SELECT 1 FROM suppliers WHERE name='Demo supplier Alpha'").fetchone() is None


def test_database_enforces_one_open_draft_per_sku(db):
    statement = '''INSERT INTO proposals(sku,avg_daily_demand,inventory_position,reorder_point,
        quantity,reason,status,created_at) VALUES('CF-001',10,26,68,50,'test','DRAFT','2026-10-26')'''
    with db:
        db.execute(statement)
    with pytest.raises(sqlite3.IntegrityError, match='UNIQUE'):
        with db:
            db.execute(statement)
    assert db.execute("SELECT COUNT(*) FROM proposals WHERE sku='CF-001'").fetchone()[0] == 1


def test_existing_duplicate_drafts_are_preserved_and_reported(db):
    with db:
        db.execute('DROP INDEX ix_proposals_one_draft_per_sku')
        for _ in range(2):
            db.execute('''INSERT INTO proposals(sku,avg_daily_demand,inventory_position,reorder_point,
                quantity,reason,status,created_at) VALUES('CF-001',10,26,68,50,'legacy','DRAFT','2026-10-26')''')
    init_db(db)
    init_db(db)
    assert db.execute("SELECT COUNT(*) FROM proposals WHERE sku='CF-001'").fetchone()[0] == 2
    assert db.execute("SELECT COUNT(*) FROM exceptions WHERE exception_type='LEGACY_DUPLICATE_DRAFT'").fetchone()[0] == 1


def test_audit_is_append_only(db):
    for statement in ('DELETE FROM audit_logs', "UPDATE audit_logs SET actor='changed'"):
        with pytest.raises(sqlite3.IntegrityError, match='append-only'):
            with db:
                db.execute(statement)


def test_seed_inventory_history_is_explicit_and_matches_current_state(db):
    assert db.execute('SELECT COUNT(*) FROM sales').fetchone()[0] == 6 * 84
    assert db.execute('SELECT COUNT(*) FROM inventory_snapshots').fetchone()[0] == 6 * 84
    for product in db.execute('SELECT * FROM products'):
        snapshot = db.execute('SELECT * FROM inventory_snapshots WHERE snapshot_date=? AND sku=?',
                              (AS_OF.isoformat(), product['sku'])).fetchone()
        assert (snapshot['on_hand'], snapshot['on_order'], snapshot['reserved_qty']) == (
            product['on_hand'], product['on_order'], product['reserved_qty'])
    assert not seed_if_empty(db, AS_OF)


def test_starter_database_migration_preserves_business_data(tmp_path):
    path = tmp_path / 'legacy.db'
    legacy = sqlite3.connect(path)
    legacy.executescript('''
        CREATE TABLE products(sku TEXT PRIMARY KEY, product_name TEXT NOT NULL,supplier TEXT NOT NULL,
            on_hand INTEGER NOT NULL,on_order INTEGER NOT NULL DEFAULT 0,lead_time_days INTEGER NOT NULL,
            safety_stock INTEGER NOT NULL,pack_size INTEGER NOT NULL,unit_cost_vnd INTEGER NOT NULL);
        CREATE TABLE sales(sale_date TEXT,sku TEXT REFERENCES products(sku),units INTEGER,PRIMARY KEY(sale_date,sku));
        CREATE TABLE proposals(id INTEGER PRIMARY KEY,sku TEXT REFERENCES products(sku),avg_daily_demand REAL,
            inventory_position INTEGER,reorder_point INTEGER,quantity INTEGER,reason TEXT,status TEXT,
            created_at TEXT,decided_at TEXT,decided_by TEXT,comment TEXT);
        CREATE TABLE audit_logs(id INTEGER PRIMARY KEY,proposal_id INTEGER NOT NULL REFERENCES proposals(id),
            action TEXT CHECK(action IN ('CREATED','APPROVED','REJECTED')),actor TEXT,comment TEXT,created_at TEXT);
        INSERT INTO products VALUES('OLD','Legacy synthetic item','Legacy supplier',12,5,3,5,5,1000);
        INSERT INTO sales VALUES('2026-10-25','OLD',4);
        INSERT INTO proposals VALUES(1,'OLD',4,12,17,10,'Old reason','DRAFT','2026-10-25',NULL,NULL,NULL);
        INSERT INTO audit_logs VALUES(1,1,'CREATED','legacy','kept','2026-10-25');
    ''')
    legacy.close()
    conn = connect(path)
    try:
        init_db(conn)
        init_db(conn)
        assert conn.execute('SELECT COUNT(*) FROM sales').fetchone()[0] == 1
        assert conn.execute('SELECT COUNT(*) FROM audit_logs').fetchone()[0] == 1
        assert conn.execute('SELECT reserved_qty FROM products').fetchone()[0] == 0
        assert conn.execute('SELECT on_order FROM inventory').fetchone()[0] == 5
        proposal = conn.execute('SELECT * FROM proposals').fetchone()
        assert (proposal['unit_cost_vnd'], proposal['supplier']) == (1000, 'Legacy supplier')
        with conn:
            conn.execute("INSERT INTO audit_logs(action,actor,created_at) VALUES('DATA_IMPORTED','tester','2026-10-26')")
    finally:
        conn.close()
    reopened = connect(path)
    try:
        assert reopened.execute('SELECT COUNT(*) FROM audit_logs').fetchone()[0] == 2
    finally:
        reopened.close()
