"""Deterministic *synthetic* dataset. No business data from Trung Nguyen Legend."""
from __future__ import annotations

import random
import sqlite3
from datetime import date, timedelta

from src.database import now_utc


PRODUCTS = [
    ('CF-001', 'Coffee beans 1 kg', 'Demo supplier Alpha', 26, 0, 5, 18, 10, 175000, 11),
    ('CF-002', 'Ground coffee 500 g', 'Demo supplier Beta', 92, 0, 4, 20, 12, 80000, 9),
    ('PK-003', 'Drip filter packs', 'Demo supplier Gamma', 52, 0, 7, 25, 20, 40000, 12),
    ('PK-004', 'Packaging cartons', 'Demo supplier Alpha', 185, 0, 3, 40, 25, 11000, 7),
    ('RM-005', 'Raw coffee blend', 'Demo supplier Beta', 14, 0, 9, 20, 10, 255000, 8),
    ('SP-006', 'Seasonal sample kit', 'Demo supplier Gamma', 40, 0, 3, 5, 5, 50000, 0),
]


def seed_if_empty(conn: sqlite3.Connection, as_of: date | None = None) -> bool:
    if conn.execute('SELECT 1 FROM products LIMIT 1').fetchone():
        return False
    as_of = as_of or date.today()
    rng = random.Random(20261026)
    history_days = 84
    # Explicit reservations illustrate available stock without altering the
    # six starter SKUs. Historical balances below simulate depletion only.
    reservations = {'CF-001': 5, 'RM-005': 3, 'PK-003': 4}
    with conn:
        for supplier in sorted({row[2] for row in PRODUCTS}):
            lead = min(row[5] for row in PRODUCTS if row[2] == supplier)
            conn.execute('INSERT OR IGNORE INTO suppliers(name,lead_time_days) VALUES(?,?)',
                         (supplier, lead))
        for sku, name, supplier, stock, on_order, lead, safety, pack, cost, _ in PRODUCTS:
            conn.execute('''
                INSERT INTO products (sku,product_name,supplier,on_hand,on_order,
                lead_time_days,safety_stock,pack_size,unit_cost_vnd,reserved_qty)
                VALUES (?,?,?,?,?,?,?,?,?,?)
            ''', (sku, name, supplier, stock, on_order, lead, safety, pack, cost,
                  reservations.get(sku, 0)))
        sales_by_day: dict[tuple[str, str], int] = {}
        for days_ago in range(history_days):
            current_day = as_of - timedelta(days=days_ago)
            day = current_day.isoformat()
            for sku, *_, baseline in PRODUCTS:
                weekday_effect = 2 if current_day.weekday() < 5 else -2
                recent_growth = 2 if sku == 'CF-001' and days_ago < 14 else 0
                volume = max(0, baseline + weekday_effect + recent_growth + rng.randint(-3, 3)) if baseline else 0
                conn.execute('INSERT INTO sales (sale_date, sku, units) VALUES (?,?,?)',
                             (day, sku, volume))
                sales_by_day[(day, sku)] = volume
        # These are generated simulated end-of-day balances, not measured
        # operational history. Reconstruct a consistent no-receipts scenario:
        # yesterday's balance = today's balance + today's consumption.
        for sku, _, _, stock, on_order, *_ in PRODUCTS:
            balance = stock
            for days_ago in range(history_days):
                day = (as_of - timedelta(days=days_ago)).isoformat()
                conn.execute('''INSERT INTO inventory_snapshots
                    (snapshot_date,sku,on_hand,on_order,reserved_qty,source,created_at)
                    VALUES(?,?,?,?,?,'synthetic_seed',?)''',
                    (day, sku, balance, on_order, reservations.get(sku, 0), now_utc()))
                balance += sales_by_day[(day, sku)]
        conn.execute('''INSERT INTO audit_logs(action,actor,comment,after_json,created_at)
            VALUES('DEMO_SEEDED','seed_script',?, ?, ?)''',
            (f'Synthetic demo: 6 SKUs, {history_days} sales days; no-receipts inventory simulation',
             '{"synthetic": true, "products": 6, "sales_days": 84}', now_utc()))
    return True


if __name__ == '__main__':
    import argparse
    from src.database import connect, init_db

    parser = argparse.ArgumentParser(description='Create synthetic demo data in an empty database')
    parser.add_argument('--db', default='procureflow.db')
    parser.add_argument('--as-of', type=date.fromisoformat, default=date.today())
    args = parser.parse_args()
    db = connect(args.db)
    try:
        init_db(db)
        created = seed_if_empty(db, args.as_of)
        print(f'Synthetic dataset seeded through {args.as_of}.' if created else
              'Database already contains products; existing data preserved.')
    finally:
        db.close()
