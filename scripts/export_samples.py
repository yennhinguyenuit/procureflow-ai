"""Create reproducible, importable synthetic CSV/XLSX portfolio samples."""
from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
from typing import Any

from src.data_import import DATASET_HEADERS
from src.database import connect, init_db
from src.procurement import get_replenishment_table
from src.reporting import make_csv, make_excel
from src.seed import seed_if_empty

REFERENCE_DATE = date(2026, 10, 26)
PRODUCT_FIELDS = DATASET_HEADERS['products'][:7]


def sample_datasets(as_of: date = REFERENCE_DATE) -> dict[str, list[dict[str, Any]]]:
    """Read an isolated reference seed; never touch the user's working DB."""
    conn = connect(':memory:')
    try:
        init_db(conn)
        seed_if_empty(conn, as_of)
        tables = {
            'suppliers': [dict(row) for row in conn.execute('SELECT * FROM suppliers ORDER BY name')],
            'products': [dict(row) for row in conn.execute(
                f'SELECT {",".join(PRODUCT_FIELDS)} FROM products ORDER BY sku')],
            'inventory': [dict(row) for row in conn.execute(
                'SELECT sku,on_hand,on_order,reserved_qty FROM inventory ORDER BY sku')],
            'sales': [dict(row) for row in conn.execute('SELECT * FROM sales ORDER BY sale_date,sku')],
            'replenishment': get_replenishment_table(conn, as_of),
        }
        return tables
    finally:
        conn.close()


def export_samples(destination: str | Path = 'data',
                   as_of: date = REFERENCE_DATE) -> dict[str, Path]:
    """Write generated input samples and dated KPI outputs; return paths.

    The product file contains master fields only. Import suppliers and products
    before inventory and sales. Every Excel input contains one worksheet.
    """
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    tables = sample_datasets(as_of)
    paths: dict[str, Path] = {}
    for dataset in ('suppliers', 'products', 'inventory', 'sales'):
        path = destination / f'synthetic_{dataset}.csv'
        fields = PRODUCT_FIELDS if dataset == 'products' else DATASET_HEADERS[dataset]
        path.write_bytes(make_csv(tables[dataset], fields))
        paths[dataset] = path
    for dataset in ('inventory', 'sales'):
        path = destination / f'synthetic_{dataset}.xlsx'
        path.write_bytes(make_excel({dataset: tables[dataset]}))
        paths[f'{dataset}_xlsx'] = path
    kpis = tables['replenishment']
    path = destination / f'synthetic_kpis_as_of_{as_of.isoformat()}.csv'
    path.write_bytes(make_csv(kpis, list(kpis[0]) if kpis else []))
    paths['kpis'] = path
    shortage = [{'sku': 'CF-001', 'on_hand': 12, 'on_order': 0, 'reserved_qty': 5}]
    path = destination / 'demo_inventory_shortage.csv'
    path.write_bytes(make_csv(shortage, DATASET_HEADERS['inventory']))
    paths['shortage'] = path
    # These match the seeded reference exactly, allowing safe repeated imports.
    sales = [row for row in tables['sales'] if row['sale_date'] == as_of.isoformat()]
    path = destination / 'demo_sales.csv'
    path.write_bytes(make_csv(sales, DATASET_HEADERS['sales']))
    paths['demo_sales'] = path
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=Path('data'))
    parser.add_argument('--as-of', type=date.fromisoformat, default=REFERENCE_DATE)
    args = parser.parse_args()
    for name, path in export_samples(args.output_dir, args.as_of).items():
        print(f'Wrote {name}: {path}')


if __name__ == '__main__':
    main()
