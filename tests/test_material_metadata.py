"""Optional material metadata and separate coffee scenarios preserve old workspaces."""
import json
from datetime import date

import pytest
from scripts.seed_coffee import export_coffee_samples, seed_coffee
from src.data_import import DATASET_HEADERS, PRODUCT_METADATA_DEFAULTS, import_dataset
from src.database import connect, init_db
from src.models import Base
from src.procurement import create_drafts, decide, get_proposals, get_replenishment_table
from src.reporting import build_report, make_csv, make_excel
from src.seed import seed_if_empty


AS_OF = date(2026, 10, 26)


@pytest.fixture
def db():
    conn = connect(':memory:')
    init_db(conn)
    seed_if_empty(conn, AS_OF)
    yield conn
    conn.close()


def _product(**updates):
    row = {
        'sku': 'MAT-001', 'product_name': 'Synthetic material', 'supplier': 'Demo supplier Alpha',
        'lead_time_days': 5, 'safety_stock': 20, 'pack_size': 10, 'unit_cost_vnd': 1000,
        'category': 'Green coffee', 'unit_of_measure': 'kg', 'origin': 'Vietnam - illustrative',
        'quality_notes': 'Review moisture condition, defects, pests and cup sample; illustrative only.',
    }
    row.update(updates)
    return row


def test_metadata_csv_xlsx_persists_and_omitted_metadata_is_preserved(db):
    row = _product()
    assert import_dataset(db, make_csv([row], list(row)), 'products.csv', 'products', as_of=AS_OF) == 1
    stored = dict(db.execute("SELECT * FROM products WHERE sku='MAT-001'").fetchone())
    for field in PRODUCT_METADATA_DEFAULTS:
        assert stored[field] == row[field]
    row['quality_notes'] = 'A new illustrative receiving reminder.'
    assert import_dataset(db, make_excel({'products': [row]}), 'products.xlsx', 'products', as_of=AS_OF) == 1
    legacy = {key: value for key, value in row.items() if key not in PRODUCT_METADATA_DEFAULTS}
    legacy['product_name'] = 'Updated name only'
    assert import_dataset(db, make_csv([legacy], list(legacy)), 'old-products.csv', 'products', as_of=AS_OF) == 1
    after = dict(db.execute("SELECT * FROM products WHERE sku='MAT-001'").fetchone())
    assert after['category'] == 'Green coffee'
    assert after['unit_of_measure'] == 'kg'
    assert after['quality_notes'] == row['quality_notes']
    assert after['product_name'] == 'Updated name only'


def test_old_required_headers_and_six_sku_seed_are_unchanged(db):
    assert db.execute('SELECT COUNT(*) FROM products').fetchone()[0] == 6
    assert db.execute('SELECT COUNT(*) FROM sales').fetchone()[0] == 504
    for product in db.execute('SELECT * FROM products'):
        for field, default in PRODUCT_METADATA_DEFAULTS.items():
            assert product[field] == default
    legacy = {key: value for key, value in _product().items() if key not in PRODUCT_METADATA_DEFAULTS}
    assert import_dataset(db, make_csv([legacy], list(legacy)), 'legacy.csv', 'products', as_of=AS_OF) == 1
    added = db.execute("SELECT * FROM products WHERE sku='MAT-001'").fetchone()
    assert added['category'] == 'Unclassified' and added['unit_of_measure'] == 'unit'


@pytest.mark.parametrize('updates', [
    {'category': 'x' * 101}, {'unit_of_measure': 'tonne'},
    {'origin': 'x' * 121}, {'quality_notes': 'x' * 501},
    {'quality_notes': 'invalid\x00notes'},
])
def test_bad_metadata_rejects_whole_import(db, updates):
    valid, invalid = _product(), _product(sku='MAT-002', **updates)
    count = db.execute('SELECT COUNT(*) FROM products').fetchone()[0]
    audit = db.execute('SELECT COUNT(*) FROM audit_logs').fetchone()[0]
    with pytest.raises(ValueError):
        import_dataset(db, make_csv([valid, invalid], list(valid)), 'products.csv', 'products', as_of=AS_OF)
    assert db.execute('SELECT COUNT(*) FROM products').fetchone()[0] == count
    assert db.execute('SELECT COUNT(*) FROM audit_logs').fetchone()[0] == audit


def test_blank_optional_origin_notes_can_be_cleared(db):
    row = _product(origin='', quality_notes='')
    assert import_dataset(db, make_csv([row], list(row)), 'products.csv', 'products', as_of=AS_OF) == 1
    after = db.execute("SELECT origin,quality_notes FROM products WHERE sku='MAT-001'").fetchone()
    assert tuple(after) == ('', '')


def test_full_template_blank_optional_cells_preserve_existing_values_and_default_new(db):
    initial = _product(on_hand=37, on_order=11, reserved_qty=3)
    import_dataset(db, make_csv([initial], list(initial)), 'products.csv', 'products', as_of=AS_OF)
    update = {**initial, 'product_name': 'Updated through full template',
              'category': '', 'unit_of_measure': '', 'on_hand': '', 'on_order': '', 'reserved_qty': ''}
    assert import_dataset(db, make_csv([update], DATASET_HEADERS['products']),
                          'template.csv', 'products', as_of=AS_OF) == 1
    existing = db.execute("SELECT * FROM products WHERE sku='MAT-001'").fetchone()
    assert (existing['category'], existing['unit_of_measure']) == ('Green coffee', 'kg')
    assert (existing['on_hand'], existing['on_order'], existing['reserved_qty']) == (37, 11, 3)
    update['sku'] = 'MAT-002'
    assert import_dataset(db, make_csv([update], DATASET_HEADERS['products']),
                          'template.csv', 'products', as_of=AS_OF) == 1
    added = db.execute("SELECT * FROM products WHERE sku='MAT-002'").fetchone()
    assert (added['category'], added['unit_of_measure']) == ('Unclassified', 'unit')
    assert (added['on_hand'], added['on_order'], added['reserved_qty']) == (0, 0, 0)


def test_additive_migration_preserves_all_existing_business_records(tmp_path):
    """Recreate the immediately preceding schema, including active requests."""
    path = tmp_path / 'existing.db'
    conn = connect(path)
    try:
        conn.execute('''CREATE TABLE products(sku TEXT PRIMARY KEY,product_name TEXT NOT NULL,
            supplier TEXT NOT NULL,on_hand INTEGER NOT NULL,on_order INTEGER NOT NULL DEFAULT 0,
            reserved_qty INTEGER NOT NULL DEFAULT 0,lead_time_days INTEGER NOT NULL,
            safety_stock INTEGER NOT NULL,pack_size INTEGER NOT NULL,unit_cost_vnd INTEGER NOT NULL)''')
        Base.metadata.create_all(conn.engine)
        seed_if_empty(conn, AS_OF)
        with conn:
            conn.execute('''INSERT INTO inventory(sku,on_hand,on_order,reserved_qty,updated_at)
                SELECT sku,on_hand,on_order,reserved_qty,'2026-10-26' FROM products''')
            proposal_id = conn.execute('''INSERT INTO proposals
                (sku,avg_daily_demand,inventory_position,reorder_point,quantity,reason,status,
                 created_at,decided_at,decided_by,comment)
                VALUES('CF-001',12,21,78,100,'Existing reason','APPROVED',
                       '2026-10-25','2026-10-26','Existing reviewer','Preserve prior decision')''').lastrowid
            conn.execute("UPDATE products SET on_order=100 WHERE sku='CF-001'")
            conn.execute("UPDATE inventory SET on_order=100 WHERE sku='CF-001'")
            conn.execute('''INSERT INTO approval_history(proposal_id,decision,actor,comment,created_at)
                VALUES(?,'APPROVED','Existing reviewer','Preserve prior decision','2026-10-26')''', (proposal_id,))
            conn.execute('''INSERT INTO audit_logs(proposal_id,action,actor,comment,created_at)
                VALUES(?,'APPROVED','Existing reviewer','Preserve prior decision','2026-10-26')''', (proposal_id,))
        tables = ['products', 'suppliers', 'inventory', 'sales', 'proposals',
                  'approval_history', 'audit_logs', 'exceptions', 'inventory_snapshots']
        before = {table: [dict(row) for row in conn.execute(f'SELECT * FROM {table}')] for table in tables}
        init_db(conn)
        after = {table: [dict(row) for row in conn.execute(f'SELECT * FROM {table}')] for table in tables}
        for table in tables:
            if table == 'products':
                assert [{key: row[key] for key in old} for row, old in zip(after[table], before[table])] == before[table]
                assert all({key: row[key] for key in PRODUCT_METADATA_DEFAULTS} == PRODUCT_METADATA_DEFAULTS for row in after[table])
            else:
                assert after[table] == before[table]
    finally:
        conn.close()


def test_existing_metadata_free_database_gets_defaults_without_rewriting_rows(tmp_path):
    conn = connect(tmp_path / 'old.db')
    try:
        conn.execute('''CREATE TABLE products(sku TEXT PRIMARY KEY,product_name TEXT NOT NULL,
            supplier TEXT NOT NULL,on_hand INTEGER NOT NULL,on_order INTEGER NOT NULL DEFAULT 0,
            reserved_qty INTEGER NOT NULL DEFAULT 0,lead_time_days INTEGER NOT NULL,
            safety_stock INTEGER NOT NULL,pack_size INTEGER NOT NULL,unit_cost_vnd INTEGER NOT NULL)''')
        conn.execute("INSERT INTO products VALUES('KEEP','Keep existing name','Old supplier',91,13,7,5,20,10,123456)")
        conn.commit()
        old = dict(conn.execute('SELECT * FROM products').fetchone())
        init_db(conn)
        new = dict(conn.execute('SELECT * FROM products').fetchone())
        assert {field: new[field] for field in old} == old
        assert {field: new[field] for field in PRODUCT_METADATA_DEFAULTS} == PRODUCT_METADATA_DEFAULTS
        init_db(conn)
        assert dict(conn.execute('SELECT * FROM products').fetchone()) == new
    finally:
        conn.close()


def test_coffee_seed_creates_separate_coherent_workspace_and_real_workflow(tmp_path):
    target = seed_coffee(tmp_path / 'coffee.db', AS_OF)
    conn = connect(target)
    try:
        products = [dict(row) for row in conn.execute('SELECT * FROM products')]
        assert len(products) == 12
        assert {'CF-001', 'CF-002', 'PK-003', 'PK-004', 'RM-005', 'SP-006'} <= {row['sku'] for row in products}
        assert all('Fictional' in row['supplier'] for row in products)
        assert all(row['category'] != 'Unclassified' for row in products)
        assert all(row['contact_email'].endswith('.reserved.example') for row in conn.execute('SELECT * FROM suppliers'))
        assert conn.execute('SELECT COUNT(*) FROM sales').fetchone()[0] == 12 * 84
        assert conn.execute("SELECT COUNT(*) FROM inventory_snapshots WHERE source='synthetic_coffee_depletion'").fetchone()[0] == 12 * 84
        for item in products:
            today = conn.execute("SELECT * FROM inventory_snapshots WHERE source='synthetic_coffee_depletion' AND sku=? AND snapshot_date=?",
                                 (item['sku'], AS_OF.isoformat())).fetchone()
            yesterday = conn.execute("SELECT * FROM inventory_snapshots WHERE source='synthetic_coffee_depletion' AND sku=? AND snapshot_date=?",
                                     (item['sku'], '2026-10-25')).fetchone()
            usage = conn.execute('SELECT units FROM sales WHERE sku=? AND sale_date=?', (item['sku'], AS_OF.isoformat())).fetchone()[0]
            assert today['on_hand'] == item['on_hand']
            assert yesterday['on_hand'] == today['on_hand'] + usage
        risks = {row['risk'] for row in get_replenishment_table(conn, AS_OF)}
        assert {'Critical Stock', 'Low Stock', 'Normal'} <= risks
        assert create_drafts(conn, AS_OF) >= 3
        assert create_drafts(conn, AS_OF) == 0
        drafts = get_proposals(conn)
        approve = drafts[0]
        decide(conn, approve['id'], 'APPROVED', 'Coffee reviewer', 'Checked fictional usage and stock')
        decide(conn, drafts[1]['id'], 'REJECTED', 'Coffee reviewer', 'Review the fictional consumption assumptions')
        assert conn.execute('SELECT on_order FROM products WHERE sku=?', (approve['sku'],)).fetchone()[0] == approve['quantity']
        assert len(build_report(conn, AS_OF)) == 10
        assert conn.execute("SELECT COUNT(*) FROM audit_logs WHERE action='COFFEE_DEMO_SEEDED'").fetchone()[0] == 1
    finally:
        conn.close()


def test_seed_refuses_existing_workspace_without_any_byte_changes(tmp_path):
    target = seed_coffee(tmp_path / 'coffee.db', AS_OF)
    before = target.read_bytes()
    with pytest.raises(ValueError, match='existing workspaces'):
        seed_coffee(target, AS_OF)
    assert target.read_bytes() == before


def test_coffee_exports_are_importable_and_identify_synthetic_limits(tmp_path):
    paths = export_coffee_samples(tmp_path, AS_OF)
    manifest = json.loads(paths['manifest'].read_text(encoding='utf-8'))
    assert manifest['synthetic'] is True
    assert manifest['usage_rows'] == 1008
    assert 'whole kilograms' in manifest['units']
    conn = connect(':memory:')
    try:
        init_db(conn)
        for dataset in ('suppliers', 'products', 'inventory', 'sales'):
            path = paths[f'{dataset}_xlsx']
            assert import_dataset(conn, path.read_bytes(), path.name, dataset, as_of=AS_OF) > 0
        assert conn.execute('SELECT COUNT(*) FROM products').fetchone()[0] == 12
        assert conn.execute('SELECT COUNT(*) FROM sales').fetchone()[0] == 1008
    finally:
        conn.close()
