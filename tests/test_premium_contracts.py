"""Additive material metadata remains visible across existing API and reports."""
from datetime import date

from fastapi.testclient import TestClient
import pytest

from scripts.seed_coffee import seed_coffee
from src.api import create_app
from src.data_import import import_dataset
from src.database import connect, init_db
from src.procurement import create_drafts, decide, get_proposals
from src.reporting import make_csv


def test_legacy_api_keeps_values_and_adds_safe_metadata(tmp_path, monkeypatch):
    monkeypatch.setenv('LOCAL_LLM_ENABLED', 'false')
    with TestClient(create_app(tmp_path / 'legacy.db', seed_date=date(2026, 10, 26))) as client:
        row = next(r for r in client.get('/api/workspace?as_of=2026-10-26').json()['inventory'] if r['sku']=='CF-001')
        assert row['on_hand'] == 26
        assert row['product_name'] == 'Coffee beans 1 kg'
        assert row['category'] == 'Unclassified'
        assert row['unit_of_measure'] == 'unit'
        assert row['origin'] == ''
        assert row['quality_notes'] == ''


def test_coffee_metadata_in_assessment_proposals_and_csv(tmp_path, monkeypatch):
    monkeypatch.setenv('LOCAL_LLM_ENABLED', 'false')
    database = tmp_path / 'coffee.db'
    seed_coffee(database, date(2026, 10, 26))
    with TestClient(create_app(database)) as client:
        workspace = client.get('/api/workspace?as_of=2026-10-26').json()
        row = next(r for r in workspace['inventory'] if r['sku']=='CF-001')
        assert row['unit_of_measure'] == 'kg'
        assert 'Robusta' in row['product_name']
        assert row['category'] != 'Unclassified'
        assert row['origin']
        assert row['quality_notes']
        generated = client.post('/api/requests/generate', json={'as_of':'2026-10-26','actor':'contract_tester'})
        assert generated.status_code == 200
        proposal = next(r for r in client.get('/api/workspace?as_of=2026-10-26').json()['proposals'] if r['sku']=='CF-001')
        assert proposal['unit_of_measure'] == 'kg'
        assert proposal['category'] == row['category']
        report = client.get('/api/reports/replenishment.csv?as_of=2026-10-26').content.decode('utf-8-sig')
        assert 'unit_of_measure' in report.splitlines()[0]
        assert 'quality_notes' in report.splitlines()[0]
        assert 'Robusta' in report


def test_request_keeps_original_unit_and_rejects_stale_unit(tmp_path):
    database = seed_coffee(tmp_path / 'snapshot.db', date(2026, 10, 26))
    conn = connect(database)
    try:
        create_drafts(conn, date(2026, 10, 26))
        proposal = next(r for r in get_proposals(conn) if r['sku']=='CF-001')
        assert proposal['unit_of_measure'] == 'kg'
        with conn:
            # A direct administrator edit must still fail revalidation.
            conn.execute("UPDATE products SET unit_of_measure='carton' WHERE sku='CF-001'")
        saved = next(r for r in get_proposals(conn) if r['id']==proposal['id'])
        assert saved['unit_of_measure'] == 'kg'
        with pytest.raises(ValueError, match='changed'):
            decide(conn, proposal['id'], 'APPROVED', 'reviewer', 'Check original unit')
    finally:
        conn.close()


def test_import_cannot_reinterpret_recorded_material_units(tmp_path):
    database = seed_coffee(tmp_path / 'units.db', date(2026, 10, 26))
    conn = connect(database)
    try:
        product = dict(conn.execute("SELECT * FROM products WHERE sku='CF-001'").fetchone())
        product['unit_of_measure'] = 'carton'
        before = conn.execute('SELECT COUNT(*) FROM audit_logs').fetchone()[0]
        with pytest.raises(ValueError, match='base unit'):
            import_dataset(conn, make_csv([product], list(product)), 'products.csv', 'products', as_of=date(2026, 10, 26))
        assert conn.execute("SELECT unit_of_measure FROM products WHERE sku='CF-001'").fetchone()[0] == 'kg'
        assert conn.execute('SELECT COUNT(*) FROM audit_logs').fetchone()[0] == before
    finally:
        conn.close()


def test_explicit_local_app_port_keeps_same_origin_mutations_working(tmp_path, monkeypatch):
    monkeypatch.setenv('LOCAL_LLM_ENABLED', 'false')
    with TestClient(create_app(tmp_path / 'port.db'), base_url='http://127.0.0.1:8002') as client:
        accepted = client.patch('/api/settings', headers={'Origin':'http://127.0.0.1:8002'}, json={'operator_name':'Local reviewer'})
        assert accepted.status_code == 200
        blocked = client.patch('/api/settings', headers={'Origin':'https://external.example'}, json={'operator_name':'Wrong origin'})
        assert blocked.status_code == 403
