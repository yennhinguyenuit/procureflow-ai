"""Local agent tests use real business tools and mocked loopback HTTP only."""
from __future__ import annotations

from datetime import date
import json
from unittest.mock import Mock

import httpx
import pytest

from src import local_agent as agent
from src.database import connect, init_db
from src.procurement import create_drafts, get_replenishment_table
from src.seed import seed_if_empty

AS_OF = date(2026, 10, 26)


@pytest.fixture
def db(tmp_path, monkeypatch):
    monkeypatch.setenv('LOCAL_LLM_ENABLED', 'false')
    monkeypatch.setenv('LOCAL_LLM_URL', 'http://127.0.0.1:8089')
    monkeypatch.setenv('LOCAL_LLM_MODEL', agent.DEFAULT_MODEL)
    monkeypatch.setattr(agent, 'business_today', lambda: AS_OF)
    conn = connect(tmp_path / 'agent.db')
    init_db(conn)
    seed_if_empty(conn, AS_OF)
    agent.init_agent_db(conn)
    yield conn
    conn.close()


def _business_state(conn):
    return {table: [tuple(row) for row in conn.execute(f'SELECT * FROM {table} ORDER BY rowid')]
            for table in ('products', 'inventory', 'sales', 'suppliers', 'proposals',
                          'approval_history', 'audit_logs', 'exceptions', 'inventory_snapshots')}


def _mock_runtime(monkeypatch, content=None, status=200):
    requests = []

    def handle(request):
        requests.append(request)
        if request.url.path == '/health':
            return httpx.Response(status, json={'status': 'ok'})
        result = content or {'intent': 'why_reorder', 'sku': 'CF-001', 'language': 'en'}
        text = result if isinstance(result, str) else json.dumps(result)
        return httpx.Response(status, json={'choices': [{'message': {'content': text}}]})

    monkeypatch.setenv('LOCAL_LLM_ENABLED', 'true')
    monkeypatch.setattr(agent, '_model_client', lambda timeout: httpx.Client(
        transport=httpx.MockTransport(handle), follow_redirects=False, trust_env=False,
    ))
    return requests


def test_reorder_explanation_is_grounded_and_persists_both_turns(db):
    expected = next(row for row in get_replenishment_table(db, AS_OF) if row['sku'] == 'CF-001')
    before = _business_state(db)

    result = agent.chat(db, 'Why reorder CF001?', as_of=AS_OF)

    assert result['mode'] == 'local_tools'
    assert result['model'] == ''
    assert f"Recommended quantity {expected['quantity']:,}" in result['answer']
    assert f"{expected['estimated_cost_vnd']:,} VND" in result['answer']
    assert '26 + 0 - 5 = 21' in result['answer']
    assert 'human approval' in result['answer']
    assert result['sources'][0]['sku'] == 'CF-001'
    assert {tool['name'] for tool in result['tools']} == {'inventory_assessment', 'policy_rules'}
    messages = agent.get_messages(db, result['conversation_id'])
    assert [message['role'] for message in messages] == ['user', 'assistant']
    assert messages[1]['metadata']['sources'] == result['sources']
    assert messages[1]['metadata']['intent'] == 'why_reorder'
    assert _business_state(db) == before


def test_followup_keeps_sku_date_and_can_reset_to_global_scope(db):
    first = agent.chat(db, 'Tại sao cần mua CF-001?', as_of=date(2026, 10, 20))
    followup = agent.chat(db, 'Chi phí bao nhiêu?', first['conversation_id'])

    assert 'Phạm vi CF-001' in followup['answer']
    assert '2026-10-20' in followup['answer']
    assert followup['conversation_id'] == first['conversation_id']
    global_result = agent.chat(db, 'Tổng ngân sách tất cả SKU?', first['conversation_id'])
    assert 'Phạm vi tất cả SKU' in global_result['answer']
    assert agent.get_messages(db, first['conversation_id'])[-1]['metadata']['context_sku'] is None


def test_explicit_sku_overrides_prior_conversation_context(db):
    first = agent.chat(db, 'Show CF-001', as_of=AS_OF)

    second = agent.chat(db, 'What about RM005?', first['conversation_id'])

    assert second['sources'][0]['sku'] == 'RM-005'
    assert 'RM-005' in second['answer']


@pytest.mark.parametrize('question,tool', [
    ('Show stock risk for all SKUs', 'open_exceptions'),
    ('What is the total budget?', 'procurement_requests'),
    ('Who supplies CF-001? Show supplier lead time', 'supplier_master'),
    ('Show pending requests', 'procurement_requests'),
    ('Show demand trends', 'demand_history'),
    ('Explain the policy formula', 'policy_rules'),
    ('Show audit history', 'audit_history'),
    ('Hello, what can you do?', 'agent_capabilities'),
    ('Những đơn nào chờ phê duyệt?', 'procurement_requests'),
    ('Ai phê duyệt trước đây? Xem lịch sử', 'audit_history'),
])
def test_supported_english_and_vietnamese_intents(db, question, tool):
    result = agent.chat(db, question, as_of=AS_OF)

    assert tool in {item['name'] for item in result['tools']}
    assert result['answer']
    assert len(result['suggestions']) > 0


def test_budget_distinguishes_saved_drafts_from_current_recommendations(db):
    create_drafts(db, AS_OF)
    saved = db.execute("SELECT SUM(quantity*unit_cost_vnd) FROM proposals WHERE status='DRAFT'").fetchone()[0]

    result = agent.chat(db, 'What is the total budget?', as_of=AS_OF)

    assert f'saved value {saved:,} VND' in result['answer']
    assert 'do not add them together' in result['answer']


def test_audit_tool_cites_persisted_event_ids(db):
    create_drafts(db, AS_OF)
    result = agent.chat(db, 'Show audit history for CF-001', as_of=AS_OF)

    assert 'CREATED' in result['answer']
    assert result['sources'][0]['label'] == 'audit_logs'
    assert result['sources'][0]['sku'] == 'CF-001'


def test_local_model_really_plans_but_cannot_change_business_facts(db, monkeypatch):
    requests = _mock_runtime(monkeypatch)
    before = _business_state(db)

    result = agent.chat(db, 'Why reorder CF-001?', as_of=AS_OF)

    assert result['mode'] == 'local_model'
    assert result['model'] == agent.DEFAULT_MODEL
    assert result['tools'][0]['name'] == 'local_model_planner'
    assert len(requests) == 1
    assert requests[0].url == 'http://127.0.0.1:8089/v1/chat/completions'
    payload = json.loads(requests[0].content)
    assert payload['response_format']['schema']['additionalProperties'] is False
    assert payload['max_tokens'] == 100 and payload['stream'] is False
    assert 'tools' not in payload
    assert 'Recommended quantity' in result['answer']
    assert _business_state(db) == before


@pytest.mark.parametrize('question,intent,language', [
    ('Chi phí bao nhiêu?', 'budget', 'vi'),
    ('Show demand trends', 'demand', 'en'),
    ('Nhu cầu thay đổi thế nào?', 'demand', 'vi'),
])
def test_model_followup_prompt_prioritizes_current_question_and_resolved_context(
    db, monkeypatch, question, intent, language,
):
    first = agent.chat(db, 'Why reorder CF-001?', as_of=AS_OF)
    requests = _mock_runtime(monkeypatch, {'intent': intent, 'sku': 'CF-001', 'language': language})

    followup = agent.chat(db, question, first['conversation_id'])

    assert followup['mode'] == 'local_model'
    payload = json.loads(requests[0].content)
    planner_input = json.loads(payload['messages'][-1]['content'])
    assert planner_input['current_question'] == question
    assert planner_input['intent_hint'] == intent
    assert planner_input['context_sku'] == 'CF-001'
    assert planner_input['language_hint'] == language
    assert planner_input['normalized_question'] == agent._normalize(question)
    assert 'recent_questions' not in planner_input
    assert 'Chi phí bao nhiêu?' in payload['messages'][0]['content']
    assert followup['sources'][0].get('sku') == 'CF-001'


@pytest.mark.parametrize('output', [
    'not JSON', {'intent': 'execute_sql', 'sku': None, 'language': 'en'},
    {'intent': 'why_reorder', 'sku': 'UNKNOWN-999', 'language': 'en'},
    {'intent': 'why_reorder', 'sku': 'CF-001', 'language': 'en', 'quantity': 999},
    {'intent': 'budget', 'sku': 'CF-001', 'language': 'en'},
])
def test_invalid_or_inconsistent_model_plans_fall_back_honestly(db, monkeypatch, output):
    _mock_runtime(monkeypatch, output)

    result = agent.chat(db, 'Why reorder CF-001?', as_of=AS_OF)

    assert result['mode'] == 'local_tools'
    assert result['model'] == ''
    assert 'Recommended quantity' in result['answer']


@pytest.mark.parametrize('question', ['Approve CF-001 now', 'DELETE FROM products',
                                      'Phê duyệt CF-001 ngay', 'Tạo draft CF-001'])
def test_write_requests_never_run_model_or_business_write(db, monkeypatch, question):
    model = Mock(side_effect=AssertionError('No model should run for a write request'))
    monkeypatch.setattr(agent, '_infer_plan', model)
    before = _business_state(db)

    result = agent.chat(db, question, as_of=AS_OF)

    assert result['tools'][0]['name'] == 'permission_boundary'
    assert _business_state(db) == before
    model.assert_not_called()


@pytest.mark.parametrize('endpoint', [
    'https://example.com', 'http://192.168.1.2:8089',
    'http://127.0.0.1:8089@evil.example', 'http://user:secret@localhost:8089',
    'http://localhost:8089?target=example.com', 'file:///tmp/model',
])
def test_external_or_credentialed_endpoints_are_blocked_without_socket_use(db, monkeypatch, endpoint):
    monkeypatch.setenv('LOCAL_LLM_ENABLED', 'true')
    monkeypatch.setenv('LOCAL_LLM_URL', endpoint)
    client = Mock(side_effect=AssertionError('Endpoint must be rejected before HTTP'))
    monkeypatch.setattr(agent, '_model_client', client)

    status = agent.agent_status()
    result = agent.chat(db, 'Why reorder CF-001?', as_of=AS_OF)

    assert status['available'] is False and status['endpoint'] is None
    assert result['mode'] == 'local_tools'
    client.assert_not_called()


def test_health_status_reports_actual_local_runtime(db, monkeypatch):
    requests = _mock_runtime(monkeypatch)

    status = agent.agent_status()

    assert status['available'] is True and status['mode'] == 'local_model'
    assert requests[0].url.path == '/health'


def test_disabled_model_never_probes_or_calls_http(db, monkeypatch):
    client = Mock(side_effect=AssertionError('Disabled means no HTTP'))
    monkeypatch.setattr(agent, '_model_client', client)

    assert agent.agent_status()['mode'] == 'local_tools'
    assert agent.chat(db, 'Show inventory', as_of=AS_OF)['mode'] == 'local_tools'
    client.assert_not_called()


def test_redirect_to_external_host_is_never_followed(db, monkeypatch):
    requests = []
    def handler(request):
        requests.append(request)
        return httpx.Response(302, headers={'location': 'https://example.com/steal'})
    monkeypatch.setenv('LOCAL_LLM_ENABLED', 'true')
    monkeypatch.setattr(agent, '_model_client', lambda timeout: httpx.Client(
        transport=httpx.MockTransport(handler), follow_redirects=False, trust_env=False))

    assert agent.chat(db, 'Show inventory', as_of=AS_OF)['mode'] == 'local_tools'
    assert len(requests) == 1
    assert requests[0].url.host == '127.0.0.1'


@pytest.mark.parametrize('question', ['', ' ' * 10, 'x' * 4_001, 'hello\x00there'],
                         ids=['empty', 'whitespace', 'oversized', 'control-character'])
def test_invalid_messages_create_no_conversation(db, question):
    with pytest.raises(ValueError):
        agent.chat(db, question, as_of=AS_OF)
    assert agent.list_conversations(db) == []


def test_unknown_sku_and_conversation_ids_are_clear_errors(db):
    for message in ('Why reorder ZZ-999?', 'Show CF999'):
        with pytest.raises(ValueError, match='Unknown SKU'):
            agent.chat(db, message, as_of=AS_OF)
    with pytest.raises(ValueError, match='Unknown SKU'):
        agent.chat(db, 'Show inventory', sku='UNKNOWN', as_of=AS_OF)
    with pytest.raises(ValueError, match='Conversation not found'):
        agent.get_messages(db, 'a' * 32)
    with pytest.raises(ValueError, match='Invalid conversation'):
        agent.chat(db, 'Hello', conversation_id="'; DROP TABLE products;--")


def test_conversation_survives_connection_reopen(db):
    result = agent.chat(db, 'Show inventory CF-001', as_of=AS_OF)
    path = db.engine.url.database
    other = connect(path)
    try:
        assert agent.list_conversations(other)[0]['id'] == result['conversation_id']
        assert agent.get_messages(other, result['conversation_id'])[-1]['content'] == result['answer']
    finally:
        other.close()


def test_conversation_limit_and_future_date_leave_state_unchanged(db, monkeypatch):
    first = agent.chat(db, 'Hello', as_of=AS_OF)
    monkeypatch.setattr(agent, 'MAX_CONVERSATION_MESSAGES', 2)
    with pytest.raises(ValueError, match='Conversation limit'):
        agent.chat(db, 'Another question', first['conversation_id'])
    with pytest.raises(ValueError, match='current or past'):
        agent.chat(db, 'Hello', as_of=date(2026, 10, 27))
    assert len(agent.get_messages(db, first['conversation_id'])) == 2


def test_chat_refuses_to_commit_a_pending_business_transaction(db):
    db.execute("UPDATE products SET on_hand=999 WHERE sku='CF-001'")

    with pytest.raises(ValueError, match='transaction'):
        agent.chat(db, 'Show inventory', as_of=AS_OF)

    assert db.in_transaction
    db.rollback()
    assert db.execute("SELECT on_hand FROM products WHERE sku='CF-001'").fetchone()[0] == 26
