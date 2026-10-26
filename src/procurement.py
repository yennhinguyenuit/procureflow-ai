"""Deterministic replenishment and transactional, human-controlled procurement."""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from typing import Any

from src.database import Connection, now_utc

SALES_WINDOW_DAYS = 14
REVIEW_PERIOD_DAYS = 4
MAX_ORDER_QUANTITY = 100_000
MAX_ORDER_VALUE_VND = 100_000_000


def business_today() -> date:
    return datetime.now(timezone(timedelta(hours=7))).date()


def _integer(value: Any, name: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f'{name} must be a whole number >= {minimum}')
    return value


def calculate_replenishment(product: dict[str, Any], units_last_window: int,
                            window_days: int = SALES_WINDOW_DAYS,
                            review_days: int = REVIEW_PERIOD_DAYS) -> dict[str, Any]:
    """ROP=ceil(demand*lead+safety); position=stock+on_order-reserved.

    Top up to the lead+review target only at/below ROP with positive demand.
    Round to a whole pack. The reader flags missing sales history separately.
    """
    _integer(window_days, 'window_days', 1)
    _integer(review_days, 'review_days')
    _integer(units_last_window, 'units_last_window')
    values = {}
    for field in ('on_hand', 'on_order', 'lead_time_days', 'safety_stock', 'pack_size', 'unit_cost_vnd'):
        if field not in product:
            raise ValueError(f'Missing product field: {field}')
        values[field] = _integer(product[field], field, 1 if field in ('lead_time_days', 'pack_size') else 0)
    reserved = _integer(product.get('reserved_qty', 0), 'reserved_qty')
    daily = units_last_window / window_days
    position = values['on_hand'] + values['on_order'] - reserved
    # Integer ceiling avoids floating-point artifacts at exact unit boundaries.
    reorder_point = (units_last_window * values['lead_time_days'] + window_days - 1) // window_days + values['safety_stock']
    target = (units_last_window * (values['lead_time_days'] + review_days) + window_days - 1) // window_days + values['safety_stock']
    shortage = max(0, target - position)
    should_reorder = daily > 0 and position <= reorder_point and shortage > 0
    pack = values['pack_size']
    quantity = ((shortage + pack - 1) // pack) * pack if should_reorder else 0
    available = values['on_hand'] - reserved
    # Inbound stock can remove a buying need while physical stock remains at risk.
    critical = daily > 0 and (available <= values['safety_stock'] or available * window_days < units_last_window * values['lead_time_days'])
    return {
        'sku': product.get('sku', ''), 'product_name': product.get('product_name', ''),
        'supplier': product.get('supplier', ''), **values, 'reserved_qty': reserved,
        'category': product.get('category', 'Unclassified'),
        'unit_of_measure': product.get('unit_of_measure', 'unit'),
        'origin': product.get('origin', ''),
        'quality_notes': product.get('quality_notes', ''),
        'available_stock': available, 'avg_daily_demand': round(daily, 3),
        'units_last_window': units_last_window,
        'inventory_position': position, 'reorder_point': reorder_point,
        'target_stock': target, 'quantity': quantity,
        'estimated_cost_vnd': quantity * values['unit_cost_vnd'],
        'risk': 'Critical Stock' if critical else ('Low Stock' if should_reorder else 'Normal'),
        'data_quality_issue': '',
    }


def get_replenishment_table(conn: Connection, as_of: date | None = None) -> list[dict[str, Any]]:
    as_of = as_of or business_today()
    start = as_of - timedelta(days=SALES_WINDOW_DAYS - 1)
    previous_start = start - timedelta(days=SALES_WINDOW_DAYS)
    sales = conn.execute('''SELECT sku,
        SUM(CASE WHEN sale_date >= ? THEN units ELSE 0 END) AS current_units,
        SUM(CASE WHEN sale_date < ? THEN units ELSE 0 END) AS previous_units,
        SUM(CASE WHEN sale_date >= ? THEN 1 ELSE 0 END) AS current_days,
        SUM(CASE WHEN sale_date < ? THEN 1 ELSE 0 END) AS previous_days
        FROM sales WHERE sale_date BETWEEN ? AND ? GROUP BY sku''',
        (start.isoformat(), start.isoformat(), start.isoformat(), start.isoformat(),
         previous_start.isoformat(), as_of.isoformat())).fetchall()
    demand = {r['sku']: dict(r) for r in sales}
    suppliers = {r['name'] for r in conn.execute('SELECT name FROM suppliers')}
    result = []
    for product in conn.execute('SELECT * FROM products ORDER BY sku'):
        history = demand.get(product['sku'], {})
        row = calculate_replenishment(dict(product), history.get('current_units', 0))
        current, previous = history.get('current_units', 0), history.get('previous_units', 0)
        row['sales_days_observed'] = history.get('current_days', 0)
        row['previous_window_days_observed'] = history.get('previous_days', 0)
        row['demand_change_pct'] = round((current - previous) / previous * 100, 1) if previous else None
        issues = []
        if not row['sales_days_observed']:
            issues.append('No sales observations in the demand window')
        if not row['supplier'].strip() or row['supplier'] not in suppliers:
            issues.append('Missing or unknown supplier')
        if issues:
            row.update(risk='Data Quality Issue', quantity=0, estimated_cost_vnd=0,
                       data_quality_issue='; '.join(issues))
        result.append(row)
    return result


def _audit(conn: Connection, action: str, actor: str, comment: str,
           proposal_id: int | None = None, before: Any = None, after: Any = None) -> None:
    conn.execute('''INSERT INTO audit_logs
        (proposal_id,action,actor,comment,before_json,after_json,created_at) VALUES (?,?,?,?,?,?,?)''',
        (proposal_id, action, actor, comment,
         json.dumps(before, sort_keys=True) if before is not None else None,
         json.dumps(after, sort_keys=True) if after is not None else None, now_utc()))


def _exception(conn: Connection, sku: str, kind: str, message: str, actor: str,
               proposal_id: int | None = None) -> None:
    if conn.execute("SELECT 1 FROM exceptions WHERE sku=? AND exception_type=? AND status='OPEN'",
                    (sku, kind)).fetchone():
        return
    conn.execute('''INSERT INTO exceptions
        (proposal_id,sku,exception_type,severity,message,status,created_at)
        VALUES (?,?,?,'WARNING',?,'OPEN',?)''', (proposal_id, sku, kind, message, now_utc()))
    _audit(conn, 'EXCEPTION_RECORDED', actor, message, proposal_id,
           after={'sku': sku, 'exception_type': kind})


def _resolve_exceptions(conn: Connection, sku: str, actor: str) -> None:
    records = conn.execute("SELECT id FROM exceptions WHERE sku=? AND status='OPEN' AND proposal_id IS NULL", (sku,)).fetchall()
    if records:
        conn.execute("UPDATE exceptions SET status='RESOLVED',resolved_at=? WHERE sku=? AND status='OPEN' AND proposal_id IS NULL",
                     (now_utc(), sku))
        _audit(conn, 'EXCEPTIONS_RESOLVED', actor, 'Current data passed policy validation',
               before={'exception_ids': [r['id'] for r in records]}, after={'status': 'RESOLVED'})


def create_drafts(conn: Connection, as_of: date | None = None, actor: str = 'policy_engine',
                  max_quantity: int = MAX_ORDER_QUANTITY,
                  max_value_vnd: int = MAX_ORDER_VALUE_VND) -> int:
    """Serialize check-and-insert across connections; skip open or approved SKUs."""
    as_of = as_of or business_today()
    if not actor.strip():
        raise ValueError('An operator name is required')
    _integer(max_quantity, 'max_quantity', 1)
    _integer(max_value_vnd, 'max_value_vnd', 1)
    inserted = 0
    with conn:
        conn.execute('BEGIN IMMEDIATE')
        for row in get_replenishment_table(conn, as_of):
            sku = row['sku']
            if row['data_quality_issue']:
                _exception(conn, sku, 'DATA_QUALITY', row['data_quality_issue'], actor)
                continue
            if row['quantity'] > max_quantity or row['estimated_cost_vnd'] > max_value_vnd:
                _exception(conn, sku, 'POLICY_LIMIT', 'Recommendation exceeds the simulated quantity or value limit', actor)
                continue
            _resolve_exceptions(conn, sku, actor)
            if not row['quantity']:
                continue
            if conn.execute("SELECT 1 FROM proposals WHERE sku=? AND status IN ('DRAFT','APPROVED') LIMIT 1", (sku,)).fetchone():
                continue
            reason = (f"Demand {row['avg_daily_demand']} units/day; inventory position "
                      f"{row['inventory_position']} <= reorder point {row['reorder_point']}; "
                      f"target {row['target_stock']}; full pack {row['pack_size']}. "
                      f"Assessment date {as_of.isoformat()}.")
            snapshot = {**row, 'as_of': as_of.isoformat()}
            cursor = conn.execute('''INSERT INTO proposals
                (sku,avg_daily_demand,inventory_position,reorder_point,target_stock,quantity,
                 unit_cost_vnd,supplier,category,unit_of_measure,snapshot_json,max_quantity,max_value_vnd,reason,created_at)
                 VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                (sku, row['avg_daily_demand'], row['inventory_position'], row['reorder_point'],
                 row['target_stock'], row['quantity'], row['unit_cost_vnd'], row['supplier'],
                 row['category'], row['unit_of_measure'],
                 json.dumps(snapshot, sort_keys=True), max_quantity, max_value_vnd, reason, now_utc()))
            _audit(conn, 'CREATED', actor.strip(), 'Rule-based draft generated', cursor.lastrowid,
                   after={'status': 'DRAFT', **snapshot})
            inserted += 1
    return inserted


def get_proposals(conn: Connection) -> list[dict[str, Any]]:
    return [dict(r) for r in conn.execute('''SELECT p.*, pr.product_name,
        pr.origin, pr.quality_notes,
        p.quantity * p.unit_cost_vnd AS estimated_cost_vnd
        FROM proposals p JOIN products pr ON p.sku=pr.sku ORDER BY p.id DESC''')]


def decide(conn: Connection, proposal_id: int, decision: str,
           actor: str, comment: str = '') -> None:
    decision = decision.upper()
    if decision not in ('APPROVED', 'REJECTED'):
        raise ValueError('Decision must be APPROVED or REJECTED')
    if not actor.strip():
        raise ValueError('An approver name is required')
    if not comment.strip():
        raise ValueError('A review reason is required')
    if len(actor) > 120 or len(comment) > 2000:
        raise ValueError('Reviewer or reason is too long')
    error = None
    with conn:
        conn.execute('BEGIN IMMEDIATE')
        stored = conn.execute('SELECT * FROM proposals WHERE id=?', (proposal_id,)).fetchone()
        if stored is None:
            raise ValueError('Proposal does not exist')
        proposal = dict(stored)
        if proposal['status'] != 'DRAFT':
            raise ValueError('Proposal has already been decided')
        if decision == 'APPROVED':
            snapshot = json.loads(proposal['snapshot_json']) if proposal['snapshot_json'] else None
            if snapshot is None:
                error = 'Legacy draft has no validation snapshot. Reject it and generate a new draft.'
            else:
                current = next((r for r in get_replenishment_table(conn, date.fromisoformat(snapshot['as_of']))
                                if r['sku'] == proposal['sku']), None)
                keys = ('on_hand', 'on_order', 'reserved_qty', 'supplier', 'unit_cost_vnd',
                        'quantity', 'inventory_position', 'reorder_point', 'target_stock',
                        'units_last_window', 'lead_time_days', 'safety_stock', 'pack_size')
                if (current is None or current['data_quality_issue']
                        or any(current[k] != snapshot[k] for k in keys)
                        or current['unit_of_measure'] != snapshot.get('unit_of_measure', 'unit')):
                    error = 'Inventory, demand, supplier, or policy changed. Reject this stale draft and generate a new one.'
                elif proposal['quantity'] > (proposal['max_quantity'] or MAX_ORDER_QUANTITY) or proposal['quantity'] * proposal['unit_cost_vnd'] > (proposal['max_value_vnd'] or MAX_ORDER_VALUE_VND):
                    error = 'Draft exceeds the simulated approval limit'
            if error:
                _exception(conn, proposal['sku'], 'STALE_DRAFT', error, actor, proposal_id)
        if not error:
            timestamp = now_utc()
            before = {'status': 'DRAFT'}
            after = {'status': decision, 'decided_by': actor.strip(), 'comment': comment.strip()}
            if decision == 'APPROVED':
                balance = conn.execute('SELECT on_order FROM products WHERE sku=?', (proposal['sku'],)).fetchone()['on_order']
                before['on_order'] = balance
                after['on_order'] = balance + proposal['quantity']
                conn.execute('UPDATE products SET on_order=on_order+? WHERE sku=?', (proposal['quantity'], proposal['sku']))
                from src.data_import import record_inventory_snapshot
                record_inventory_snapshot(conn, proposal['sku'], business_today(), f'approval_{proposal_id}')
            conn.execute('''UPDATE proposals SET status=?,decided_at=?,decided_by=?,comment=?
                WHERE id=? AND status='DRAFT' ''', (decision, timestamp, actor.strip(), comment.strip(), proposal_id))
            conn.execute('''INSERT INTO approval_history
                (proposal_id,decision,actor,comment,before_json,after_json,created_at) VALUES (?,?,?,?,?,?,?)''',
                (proposal_id, decision, actor.strip(), comment.strip(), json.dumps(before), json.dumps(after), timestamp))
            _audit(conn, decision, actor.strip(), comment.strip(), proposal_id, before, after)
            if decision == 'REJECTED':
                conn.execute("UPDATE exceptions SET status='RESOLVED',resolved_at=? WHERE proposal_id=? AND status='OPEN'",
                             (timestamp, proposal_id))
    if error:
        raise ValueError(error)


def get_audit_logs(conn: Connection) -> list[dict[str, Any]]:
    return [dict(r) for r in conn.execute('SELECT * FROM audit_logs ORDER BY id DESC')]


def get_approval_history(conn: Connection) -> list[dict[str, Any]]:
    return [dict(r) for r in conn.execute('SELECT * FROM approval_history ORDER BY id DESC')]


def get_exceptions(conn: Connection) -> list[dict[str, Any]]:
    return [dict(r) for r in conn.execute('SELECT * FROM exceptions ORDER BY id DESC')]


def import_sales_csv(conn: Connection, raw: bytes, as_of: date | None = None) -> int:
    """Backward-compatible starter API using the shared CSV/Excel validator."""
    from src.data_import import import_dataset
    return import_dataset(conn, raw, 'sales.csv', 'sales', as_of=as_of)

