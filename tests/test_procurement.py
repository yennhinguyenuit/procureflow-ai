import csv
import io
from datetime import date, timedelta

import pytest

from src.ai_assistant import fallback_summary, summarize
from src.database import connect, init_db
from src.procurement import (
    calculate_replenishment, create_drafts, decide,
    get_audit_logs, get_proposals, get_replenishment_table, import_sales_csv,
)
from src.reporting import make_csv
from src.seed import seed_if_empty


@pytest.fixture
def db():
    conn = connect(':memory:')
    init_db(conn)
    seed_if_empty(conn, date(2026, 10, 26))
    yield conn
    conn.close()


def example_product(**changes):
    p = {'sku': 'X', 'product_name': 'Test', 'supplier': 'S', 'on_hand': 55,
         'on_order': 0, 'lead_time_days': 5, 'safety_stock': 20,
         'pack_size': 20, 'unit_cost_vnd': 1000}
    p.update(changes)
    return p


def test_reorder_calculation_and_pack_rounding():
    result = calculate_replenishment(example_product(), units_last_window=140)
    assert result['avg_daily_demand'] == 10
    assert result['reorder_point'] == 70
    assert result['target_stock'] == 110
    assert result['quantity'] == 60
    assert result['estimated_cost_vnd'] == 60000


def test_avoids_unnecessary_reorder_if_on_order_covers_need():
    result = calculate_replenishment(example_product(on_order=100), 140)
    assert result['quantity'] == 0


def test_zero_demand_does_not_trigger_order():
    assert calculate_replenishment(example_product(on_hand=0), 0)['quantity'] == 0


def test_invalid_horizon_rejected():
    with pytest.raises(ValueError):
        calculate_replenishment(example_product(), 10, window_days=0)


def test_policy_skips_duplicate_drafts(db):
    first = create_drafts(db, date(2026, 10, 26))
    assert first >= 1
    assert create_drafts(db, date(2026, 10, 26)) == 0
    assert len(get_proposals(db)) == first


def test_approval_updates_on_order_and_audit(db):
    create_drafts(db, date(2026, 10, 26))
    p = next(p for p in get_proposals(db) if p['status'] == 'DRAFT')
    original = db.execute('SELECT on_order FROM products WHERE sku=?', (p['sku'],)).fetchone()[0]
    decide(db, p['id'], 'APPROVED', 'tester', 'Approved in test')
    updated = db.execute('SELECT on_order FROM products WHERE sku=?', (p['sku'],)).fetchone()[0]
    assert updated - original == p['quantity']
    assert any(a['action'] == 'APPROVED' for a in get_audit_logs(db))
    with pytest.raises(ValueError):
        decide(db, p['id'], 'APPROVED', 'tester')


def test_rejection_does_not_change_inventory(db):
    create_drafts(db, date(2026, 10, 26))
    p = get_proposals(db)[0]
    original = db.execute('SELECT on_order FROM products WHERE sku=?', (p['sku'],)).fetchone()[0]
    decide(db, p['id'], 'REJECTED', 'tester', 'Supply plan reviewed; rejected')
    updated = db.execute('SELECT on_order FROM products WHERE sku=?', (p['sku'],)).fetchone()[0]
    assert updated == original
    assert any(a['action'] == 'REJECTED' for a in get_audit_logs(db))


def test_csv_import_valid_and_idempotent(db):
    raw = b'sale_date,sku,units\n2026-10-27,CF-001,12\n'
    assert import_sales_csv(db, raw, date(2026, 10, 27)) == 1
    assert import_sales_csv(db, raw, date(2026, 10, 27)) == 0


def test_csv_conflict_is_rejected_without_changes(db):
    raw = b'sale_date,sku,units\n2026-10-26,CF-001,999\n'
    before = db.execute('SELECT COUNT(*) FROM sales').fetchone()[0]
    with pytest.raises(ValueError, match='Conflicting'):
        import_sales_csv(db, raw, date(2026, 10, 26))
    assert db.execute('SELECT COUNT(*) FROM sales').fetchone()[0] == before


@pytest.mark.parametrize('raw', [
    b'sale_date,sku,units\n2026-10-27,CF-001,-1\n',
    b'sale_date,sku,units\n2026-10-27,BAD-SKU,2\n',
    b'sale_date,sku,units\n2026-10-28,CF-001,2\n',
    b'wrong,header\na,b\n',
])
def test_csv_validation(db, raw):
    with pytest.raises(ValueError):
        import_sales_csv(db, raw, date(2026, 10, 27))


def test_lookback_window_includes_zero_sale_days(db):
    table = get_replenishment_table(db, date(2026, 10, 26))
    assert len(table) == 6
    assert next(x for x in table if x['sku'] == 'SP-006')['avg_daily_demand'] == 0


def test_csv_formula_injection_escaped():
    output = make_csv([{'supplier': '=HYPERLINK("bad")'}], ['supplier']).decode('utf-8-sig')
    assert "'=HYPERLINK" in output


def test_summary_is_local_without_api_key(db, monkeypatch):
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    summary, source = summarize(get_replenishment_table(db, date(2026, 10, 26)))
    assert source == 'RULE_BASED_FALLBACK'
    assert 'human approval' in summary
