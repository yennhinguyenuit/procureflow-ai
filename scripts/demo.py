"""Replay import -> policy -> human decisions -> persistent evidence offline.

Run ``python -m scripts.demo``. Each invocation creates a new run folder and
preserves all earlier databases and audit history. No Gemini call is made.
"""
from __future__ import annotations

import argparse
import json
from datetime import date
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from scripts.export_samples import REFERENCE_DATE, export_samples
from src.ai_assistant import fallback_summary
from src.data_import import import_dataset
from src.database import connect, init_db
from src.procurement import create_drafts, decide, get_proposals, get_replenishment_table
from src.reporting import build_report, make_csv, make_excel, report_fields


def run_demo(output_dir: str | Path = 'outputs/demo',
             as_of: date = REFERENCE_DATE) -> Path:
    """Return the new run directory after verifying durable workflow results."""
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    run_dir = Path(output_dir) / f'run_{timestamp}_{uuid4().hex[:8]}'
    run_dir.mkdir(parents=True, exist_ok=False)
    inputs = export_samples(run_dir / 'inputs', as_of)
    database_path = run_dir / 'procureflow.db'
    conn = connect(database_path)
    changes: dict[str, int] = {}
    try:
        init_db(conn)
        for dataset, source in (
            ('suppliers', 'suppliers'), ('products', 'products'),
            ('inventory', 'inventory_xlsx'), ('sales', 'sales_xlsx'),
        ):
            path = inputs[source]
            changes[dataset] = import_dataset(conn, path.read_bytes(), path.name,
                                              dataset, 'demo_operator', as_of)
        shortage_file = inputs['shortage']
        changes['shortage'] = import_dataset(conn, shortage_file.read_bytes(), shortage_file.name,
                                             'inventory', 'demo_operator', as_of)
        identical_import = import_dataset(conn, inputs['demo_sales'].read_bytes(),
                                           inputs['demo_sales'].name, 'sales', 'demo_operator', as_of)
        assessment = get_replenishment_table(conn, as_of)
        (run_dir / 'offline_insights.txt').write_text(fallback_summary(assessment), encoding='utf-8')
        created = create_drafts(conn, as_of, actor='demo_operator')
        repeated = create_drafts(conn, as_of, actor='demo_operator')
        drafts = [row for row in get_proposals(conn) if row['status'] == 'DRAFT']
        approve = next(row for row in drafts if row['sku'] == 'CF-001')
        reject = next(row for row in drafts if row['sku'] != approve['sku'])
        original_on_order = conn.execute('SELECT on_order FROM products WHERE sku=?',
                                         (approve['sku'],)).fetchone()[0]
        decide(conn, approve['id'], 'APPROVED', 'demo_manager',
               'Synthetic review: stock and pending deliveries verified; approve internal replenishment.')
        decide(conn, reject['id'], 'REJECTED', 'demo_manager',
               'Synthetic review: defer this material while the buyer confirms its demand assumptions.')
    finally:
        conn.close()

    # Reopen the file before exporting so the reports prove persistence rather
    # than merely showing objects still held by the initial connection.
    persisted = connect(database_path)
    try:
        report = build_report(persisted, as_of)
        stored_proposals = {row['id']: row for row in report['proposals']}
        stock = next(row for row in report['inventory'] if row['sku'] == approve['sku'])
        if (stored_proposals[approve['id']]['status'] != 'APPROVED'
                or stored_proposals[reject['id']]['status'] != 'REJECTED'
                or stock['on_order'] != original_on_order + approve['quantity']
                or repeated != 0 or identical_import != 0):
            raise RuntimeError('Persisted workflow verification failed')
        (run_dir / 'reports.xlsx').write_bytes(make_excel(report))
        for dataset, rows in report.items():
            fields = list(rows[0]) if rows else report_fields(dataset)
            (run_dir / f'{dataset}.csv').write_bytes(make_csv(rows, fields))
        manifest = {
            'synthetic': True, 'as_of': as_of.isoformat(),
            'ai_source': 'RULE_BASED_FALLBACK', 'imported_changed_rows': changes,
            'identical_sales_import_changed_rows': identical_import,
            'drafts_created': created, 'drafts_on_repeated_generation': repeated,
            'approved_request_id': approve['id'], 'rejected_request_id': reject['id'],
            'approved_sku': approve['sku'], 'approved_quantity': approve['quantity'],
            'on_order_before_approval': original_on_order, 'on_order_after_approval': stock['on_order'],
            'persisted_verification': True,
            'report_rows': {name: len(rows) for name, rows in report.items()},
        }
        (run_dir / 'run_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    finally:
        persisted.close()
    print('Synthetic procurement demo completed; internal decisions only, no supplier orders.')
    print('Imported changed rows:', ', '.join(f'{key}={value}' for key, value in changes.items()))
    print(f'Drafts created: {created}; repeated generation: {repeated}; identical sales import: {identical_import}')
    print(f'Approved request {approve["id"]}; rejected request {reject["id"]}. Persistence verified after reopen.')
    print(f'Database: {database_path.resolve()}')
    print(f'Reports and offline insights: {run_dir.resolve()}')
    return run_dir


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=Path('outputs/demo'))
    parser.add_argument('--as-of', type=date.fromisoformat, default=REFERENCE_DATE)
    args = parser.parse_args()
    run_demo(args.output_dir, args.as_of)


if __name__ == '__main__':
    main()
