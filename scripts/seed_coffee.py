"""Create a separate, explicitly synthetic coffee-materials workspace.

An explicit --db path is required. Existing files are always refused so a
recording reset can never overwrite another workspace or its audit history.
"""
from __future__ import annotations

import argparse
import json
import random
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from src.data_import import DATASET_HEADERS, import_dataset
from src.database import Connection, connect, init_db, now_utc
from src.reporting import make_csv, make_excel

REFERENCE_DATE = date(2026, 10, 26)
HISTORY_DAYS = 84
PRODUCT_FIELDS = DATASET_HEADERS['products'][:7] + ['category', 'unit_of_measure', 'origin', 'quality_notes']

# Every supplier is fictional. Contacts deliberately use reserved .example
# domains. Prices, policy values, balances, and usage signals are illustrative.
SUPPLIERS = [
    {'name': 'Fictional Highlands Sample Cooperative', 'lead_time_days': 5, 'contact_email': 'sales@highlands.reserved.example'},
    {'name': 'Fictional Plateau Example Supplier', 'lead_time_days': 7, 'contact_email': 'sales@plateau.reserved.example'},
    {'name': 'Fictional Origin Sample Importer', 'lead_time_days': 12, 'contact_email': 'sales@origins.reserved.example'},
    {'name': 'Fictional Packaging Example Works', 'lead_time_days': 5, 'contact_email': 'sales@packaging.reserved.example'},
    {'name': 'Fictional Roasting Sample Partner', 'lead_time_days': 4, 'contact_email': 'sales@roasting.reserved.example'},
    {'name': 'Fictional Laboratory Example Supply', 'lead_time_days': 4, 'contact_email': 'sales@accessories.reserved.example'},
]
_GREEN_NOTE = ('Illustrative receiving checklist: review moisture condition, visible defects, pest evidence, '
               'lot traceability and cup sample. No numerical acceptance standard is asserted.')
_PACK_NOTE = ('Illustrative receiving checklist: verify dimensions, print or seal condition, lot traceability '
              'and relevant food-contact documentation. No certification is implied.')

# sku, name, supplier index, stock, reserved, lead, safety, pack, cost/unit,
# daily usage baseline, category, unit, illustrative origin, quality note.
MATERIALS = [
    ('CF-001', 'Green Robusta - Buon Ma Thuot', 0, 40, 10, 5, 60, 30, 98000, 18,
     'Green coffee', 'kg', 'Buon Ma Thuot, Vietnam', _GREEN_NOTE),
    ('CF-002', 'Green Arabica - Lam Dong', 1, 250, 15, 7, 40, 20, 160000, 12,
     'Green coffee', 'kg', 'Lam Dong, Vietnam', _GREEN_NOTE),
    ('PK-003', 'Paper coffee filters', 3, 400, 20, 4, 100, 100, 350, 55,
     'Packaging', 'piece', 'Vietnam - illustrative manufacturing origin', _PACK_NOTE),
    ('PK-004', 'Outer shipping cartons', 3, 130, 10, 5, 40, 25, 9000, 20,
     'Packaging', 'carton', 'Vietnam - illustrative manufacturing origin', _PACK_NOTE),
    ('RM-005', 'Green Culi Robusta - sorted lot', 0, 25, 5, 5, 40, 20, 115000, 10,
     'Green coffee', 'kg', 'Central Highlands, Vietnam',
     'Illustrative Culi Robusta lot; confirm lot identity, moisture condition, defects, pest evidence and cup sample.'),
    ('SP-006', 'Lot traceability label rolls', 3, 30, 0, 3, 3, 2, 32000, 1,
     'Packaging', 'roll', 'Vietnam - illustrative manufacturing origin',
     'Illustrative receiving checklist: verify print legibility, adhesive condition and lot-code layout.'),
    ('CF-007', 'Green Arabica - Colombia example lot', 2, 320, 20, 12, 20, 20, 180000, 8,
     'Green coffee', 'kg', 'Colombia - illustrative origin', _GREEN_NOTE),
    ('CF-008', 'Green Robusta - Brazil example lot', 2, 500, 20, 14, 30, 20, 105000, 10,
     'Green coffee', 'kg', 'Brazil - illustrative origin', _GREEN_NOTE),
    ('RB-009', 'Purchased roasted Arabica blending input', 4, 100, 5, 4, 20, 10, 235000, 6,
     'Roasted coffee', 'kg', 'Vietnam - illustrative roasting location',
     'Purchased roast input for a separate blending example; review roast date, aroma, traceability and cup profile. No recipe is asserted.'),
    ('PK-010', 'Valve coffee bags - 500 g format', 3, 250, 40, 6, 200, 100, 4200, 70,
     'Packaging', 'piece', 'Vietnam - illustrative manufacturing origin', _PACK_NOTE),
    ('PK-011', 'Food-contact inner liners', 3, 450, 20, 5, 40, 25, 5500, 20,
     'Packaging', 'piece', 'Vietnam - illustrative manufacturing origin', _PACK_NOTE),
    ('AC-012', 'Coffee sample cupping cups', 5, 100, 0, 4, 30, 12, 18500, 2,
     'Accessories', 'piece', 'Vietnam - illustrative manufacturing origin',
     'Illustrative receiving checklist: inspect chips, cleanliness, dimensional consistency and intended-use documentation.'),
]


def coffee_datasets(as_of: date = REFERENCE_DATE) -> dict[str, list[dict[str, Any]]]:
    """Return synthetic masters, integer-unit balances, and material usage."""
    products, inventory, sales = [], [], []
    rng = random.Random(20261026)
    for sku, name, supplier, stock, reserved, lead, safety, pack, cost, _, category, unit, origin, notes in MATERIALS:
        products.append(dict(zip(PRODUCT_FIELDS, (
            sku, name, SUPPLIERS[supplier]['name'], lead, safety, pack, cost,
            category, unit, origin, notes,
        ))))
        inventory.append({'sku': sku, 'on_hand': stock, 'on_order': 0, 'reserved_qty': reserved})
    for days_ago in range(HISTORY_DAYS - 1, -1, -1):
        day = as_of - timedelta(days=days_ago)
        for material in MATERIALS:
            sku, baseline = material[0], material[9]
            variation = max(1, baseline // 6)
            growth = 2 if sku == 'CF-001' and days_ago < 14 else 0
            usage = max(0, baseline + growth + rng.randint(-variation, variation))
            sales.append({'sale_date': day.isoformat(), 'sku': sku, 'units': usage})
    return {'suppliers': [dict(row) for row in SUPPLIERS], 'products': products,
            'inventory': inventory, 'sales': sales}


def _reference_database(as_of: date) -> Connection:
    reference = connect(':memory:')
    try:
        init_db(reference)
        datasets = coffee_datasets(as_of)
        for dataset in ('suppliers', 'products', 'inventory', 'sales'):
            fields = PRODUCT_FIELDS if dataset == 'products' else DATASET_HEADERS[dataset]
            import_dataset(reference, make_csv(datasets[dataset], fields),
                           f'coffee_{dataset}.csv', dataset, 'synthetic_coffee_seed', as_of)
        by_key = {(row['sale_date'], row['sku']): row['units'] for row in datasets['sales']}
        with reference:
            for item in datasets['inventory']:
                balance = item['on_hand']
                for days_ago in range(HISTORY_DAYS):
                    day = (as_of - timedelta(days=days_ago)).isoformat()
                    reference.execute('''INSERT INTO inventory_snapshots
                        (snapshot_date,sku,on_hand,on_order,reserved_qty,source,created_at)
                        VALUES(?,?,?,?,?,'synthetic_coffee_depletion',?)''',
                        (day, item['sku'], balance, item['on_order'], item['reserved_qty'], now_utc()))
                    balance += by_key[(day, item['sku'])]
            reference.execute('''INSERT INTO audit_logs(action,actor,comment,after_json,created_at)
                VALUES('COFFEE_DEMO_SEEDED','synthetic_coffee_seed',?,?,?)''',
                ('Fictional coffee-materials scenario; sales schema stores synthetic withdrawals; whole units only',
                 json.dumps({'synthetic': True, 'materials': 12, 'history_days': HISTORY_DAYS,
                             'as_of': as_of.isoformat(), 'signal': 'material_withdrawals',
                             'inventory_model': 'depletion_without_receipts'}), now_utc()))
        return reference
    except Exception:
        reference.close()
        raise


def seed_coffee(db_path: str | Path, as_of: date = REFERENCE_DATE) -> Path:
    """Publish a fully validated reference DB to a new, exclusively created file.

    Existing files, including empty databases, are refused. All construction
    happens before publication; SQLite backup commits the reference atomically.
    Existing business rows and audit history are never migrated or replaced by
    this scenario seeder. Normal app startup handles additive schema migration.
    """
    target = Path(db_path)
    if str(db_path) == ':memory:' or target.exists():
        raise ValueError('Coffee seed requires a new database filename; existing workspaces and history are preserved.')
    if not isinstance(as_of, date):
        raise ValueError('as_of must be a date')
    reference = _reference_database(as_of)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            # Exclusive creation also prevents a race with another seed process.
            with target.open('xb'):
                pass
        except FileExistsError as exc:
            raise ValueError('Target already exists; choose a new database filename.') from exc
        destination = connect(target)
        try:
            reference.backup(destination._driver)
        finally:
            destination.close()
    finally:
        reference.close()
    return target


def export_coffee_samples(destination: str | Path = 'data/coffee',
                          as_of: date = REFERENCE_DATE) -> dict[str, Path]:
    """Write importable synthetic reference files without modifying a database."""
    directory = Path(destination)
    directory.mkdir(parents=True, exist_ok=True)
    paths = {}
    datasets = coffee_datasets(as_of)
    for dataset, rows in datasets.items():
        fields = PRODUCT_FIELDS if dataset == 'products' else DATASET_HEADERS[dataset]
        path = directory / f'coffee_{dataset}.csv'
        path.write_bytes(make_csv(rows, fields))
        paths[dataset] = path
        workbook = directory / f'coffee_{dataset}.xlsx'
        workbook.write_bytes(make_excel({dataset: rows}))
        paths[f'{dataset}_xlsx'] = workbook
    manifest = {
        'synthetic': True, 'as_of': as_of.isoformat(), 'materials': 12, 'suppliers': len(SUPPLIERS),
        'history_days': HISTORY_DAYS, 'usage_rows': len(datasets['sales']),
        'source_signal': 'fictional material withdrawals stored in the existing sales schema',
        'units': 'Integer base units only; kg quantities are whole kilograms. No mass conversion, yield or BOM engine.',
        'inventory_history': 'Synthetic end-of-day depletion without receipts; not measured company history.',
        'quality_notes': 'Illustrative review reminders; not numerical acceptance standards or certification claims.',
        'commercial_values': 'All suppliers, contacts, costs, lead times, balances and usage are fictional.',
        'non_affiliation': 'Academic prototype using synthetic data. Not affiliated with or endorsed by Trung Nguyen Legend.',
    }
    path = directory / 'manifest.json'
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    paths['manifest'] = path
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', required=True, type=Path, help='New database path; existing files are refused')
    parser.add_argument('--as-of', type=date.fromisoformat, default=REFERENCE_DATE)
    parser.add_argument('--export-dir', type=Path, help='Also generate reference CSV/XLSX inputs, e.g. data/coffee')
    args = parser.parse_args()
    try:
        target = seed_coffee(args.db, args.as_of)
    except ValueError as exc:
        parser.exit(2, f'{exc}\n')
    if args.export_dir:
        export_coffee_samples(args.export_dir, args.as_of)
    print(f'Created synthetic coffee-materials workspace: {target.resolve()}')
    print(f'12 materials, {len(SUPPLIERS)} fictional suppliers, {HISTORY_DAYS} usage days; no supplier orders.')


if __name__ == '__main__':
    main()
