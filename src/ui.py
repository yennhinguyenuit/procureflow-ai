"""English Streamlit presentation layer; domain decisions live in procurement."""
from __future__ import annotations

import os
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

from src.ai_assistant import summarize
from src.data_import import import_dataset
from src.database import connect, init_db
from src.procurement import (
    create_drafts, decide, get_approval_history, get_audit_logs, get_exceptions,
    get_proposals, get_replenishment_table,
)
from src.reporting import build_report, make_csv, make_excel, report_fields
from src.seed import seed_if_empty


PAGES = ('Overview', 'Inventory', 'Procurement Requests', 'AI Insights',
         'Analytics', 'Audit Logs', 'Settings')
RISK_COLORS = {'Critical Stock': '#CB4B50', 'Low Stock': '#D69A26',
               'Normal': '#087F8C', 'Data Quality Issue': '#7A68A6'}
TEMPLATES = {
    'inventory': ['sku', 'on_hand', 'on_order', 'reserved_qty'],
    'sales': ['sale_date', 'sku', 'units'],
    'products': ['sku', 'product_name', 'supplier', 'lead_time_days', 'safety_stock',
                 'pack_size', 'unit_cost_vnd'],
    'suppliers': ['name', 'lead_time_days', 'contact_email'],
}


def _configure() -> None:
    load_dotenv(override=False)
    st.set_page_config(page_title='ProcureFlow AI', page_icon='P', layout='wide',
                       initial_sidebar_state='expanded')
    st.markdown('''<style>
      .block-container {padding-top: 2rem; padding-bottom: 2rem; max-width: 1560px;}
      h1 {font-weight: 750; letter-spacing: -1.1px;}
      h2,h3 {letter-spacing: -.35px;}
      [data-testid="stMetric"] {background: #F2F5F8; border: 1px solid #E4EAF0;
        border-radius: 12px; padding: 16px 18px; min-height: 118px;}
      [data-testid="stMetricLabel"] {color: #556B7C; font-size: 13px;}
      [data-testid="stMetricValue"] {font-size: 28px; color: #18324A;}
      .brand {font-size: 24px; font-weight: 800; color: #18324A; letter-spacing: -.7px;}
      .brand span {color: #087F8C;}
      .eyebrow {color: #087F8C; font-size: 11px; font-weight: 750;
        letter-spacing: 2px; margin-bottom: 6px;}
      div[data-testid="stSidebar"] {border-right: 1px solid #E4EAF0;}
    </style>''', unsafe_allow_html=True)


def _business_today() -> date:
    return datetime.now(timezone(timedelta(hours=7))).date()


def _frame(rows: list[dict[str, Any]], columns: list[str] | None = None) -> pd.DataFrame:
    frame = pd.DataFrame(rows)
    if columns and not frame.empty:
        return frame[[name for name in columns if name in frame.columns]]
    return frame


def _table(rows: list[dict[str, Any]], columns: list[str] | None = None) -> None:
    if not rows:
        st.info('No records match the current view.')
        return
    st.dataframe(_frame(rows, columns), width='stretch', hide_index=True,
                 column_config={
                     'estimated_cost_vnd': st.column_config.NumberColumn('Estimated value (VND)', format='%d'),
                     'unit_cost_vnd': st.column_config.NumberColumn('Unit cost (VND)', format='%d'),
                     'demand_change_pct': st.column_config.NumberColumn('Demand change (%)', format='%.1f'),
                 })


def _filtered(rows: list[dict[str, Any]], skus: list[str],
              suppliers: list[str]) -> list[dict[str, Any]]:
    return [r for r in rows if (not skus or r.get('sku') in skus)
            and (not suppliers or r.get('supplier') in suppliers)]


def _sidebar(rows: list[dict[str, Any]]) -> tuple[str, date, list[str], list[str], tuple[date, date]]:
    with st.sidebar:
        st.markdown('<div class="brand">ProcureFlow <span>AI</span></div>', unsafe_allow_html=True)
        st.caption('INTELLIGENT PROCUREMENT')
        st.divider()
        page = st.radio('Workspace', PAGES, label_visibility='collapsed', key='navigation')
        st.divider()
        st.caption('WORKSPACE FILTERS')
        as_of = st.date_input('Analysis date', value=_business_today(),
                              max_value=_business_today(), key='analysis_date')
        skus = st.multiselect('SKUs', sorted({r['sku'] for r in rows}), key='sku_filter')
        suppliers = st.multiselect('Suppliers', sorted({r['supplier'] for r in rows if r.get('supplier')}),
                                   key='supplier_filter')
        dates = st.date_input('Trend dates', value=(as_of - timedelta(days=29), as_of),
                              max_value=_business_today(), key='trend_dates')
        if isinstance(dates, tuple) and len(dates) == 2:
            period = dates
        else:
            period = (as_of - timedelta(days=29), as_of)
            st.caption('Select both trend dates. The previous 30 days are shown until the range is complete.')
        if page == 'Audit Logs':
            st.caption('Audit history shows all persisted events.')
        st.divider()
        st.caption('DEMO ENVIRONMENT')
        st.caption('Synthetic data · Human approval')
        st.caption('Local analysis available')
    return page, as_of, skus, suppliers, period


def _kpis(rows: list[dict[str, Any]], proposals: list[dict[str, Any]]) -> None:
    columns = st.columns(5)
    columns[0].metric('Total SKUs', len(rows))
    columns[1].metric('Low-stock items', sum(r['risk'] == 'Low Stock' for r in rows))
    columns[2].metric('Critical-stock items', sum(r['risk'] == 'Critical Stock' for r in rows))
    columns[3].metric('Pending requests', sum(p['status'] == 'DRAFT' for p in proposals))
    columns[4].metric('Order value (VND)', f"{sum(r['estimated_cost_vnd'] for r in rows):,.0f}",
                      help='VND. Current recommendations before pending-draft deduplication; not booked spend.')


def _plot(figure: Any, key: str) -> None:
    figure.update_layout(font={'family': 'Arial', 'color': '#18324A'},
                         paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                         margin={'l': 8, 'r': 8, 't': 30, 'b': 8}, height=300,
                         legend_title_text='')
    figure.update_xaxes(showgrid=False)
    figure.update_yaxes(gridcolor='#E8EEF2')
    st.plotly_chart(figure, width='stretch', key=key)


def _risk_chart(rows: list[dict[str, Any]]) -> None:
    if not rows:
        st.info('Select at least one tracked SKU to see inventory risk.')
        return
    risk = pd.DataFrame(rows).groupby('risk', as_index=False).size()
    _plot(px.pie(risk, names='risk', values='size', hole=.65,
                 color='risk', color_discrete_map=RISK_COLORS), 'inventory_risk_chart')


def _status_chart(proposals: list[dict[str, Any]]) -> None:
    if not proposals:
        st.info('Generate requests to begin tracking approval status.')
        return
    status = pd.DataFrame(proposals).groupby('status', as_index=False).size()
    _plot(px.bar(status, x='status', y='size', color='status',
                 color_discrete_map={'DRAFT': '#D69A26', 'APPROVED': '#087F8C', 'REJECTED': '#CB4B50'},
                 labels={'status': 'Request status', 'size': 'Requests'}), 'request_status_chart')


def _overview(rows: list[dict[str, Any]], proposals: list[dict[str, Any]],
              exceptions: list[dict[str, Any]]) -> None:
    _kpis(rows, proposals)
    st.write('')
    left, right = st.columns(2)
    with left:
        st.subheader('Inventory health')
        _risk_chart(rows)
    with right:
        st.subheader('Purchase request pipeline')
        _status_chart(proposals)
    st.subheader('Replenishment priorities')
    priorities = sorted((r for r in rows if r['quantity'] > 0),
                        key=lambda r: (r['risk'] != 'Critical Stock', -r['estimated_cost_vnd']))
    _table(priorities, ['sku', 'product_name', 'supplier', 'risk', 'on_hand',
                         'reserved_qty', 'reorder_point', 'quantity', 'estimated_cost_vnd'])
    st.subheader('Exception tracking')
    active = [e for e in exceptions if e.get('status') == 'OPEN']
    st.caption(f'{len(active)} open exception(s). Exceptions prevent unsafe drafts and preserve a review trail.')
    _table(active, ['id', 'sku', 'exception_type', 'severity', 'message', 'created_at'])


def _import_panel(conn: Any, as_of: date, prefix: str) -> None:
    st.subheader('Import operational data')
    st.caption('CSV or Excel (.xlsx). Import suppliers and products before dependent inventory or sales. '
               'Every file is validated before any rows are committed.')
    st.caption('Import limit: 2 MB and 10,000 rows. Excel files must contain one worksheet.')
    dataset = st.selectbox('Dataset', list(TEMPLATES), format_func=str.title, key=f'{prefix}_dataset')
    st.code(','.join(TEMPLATES[dataset]), language=None)
    st.download_button('Download CSV template', make_csv([], TEMPLATES[dataset]),
                       file_name=f'{dataset}_template.csv', mime='text/csv', key=f'{prefix}_template')
    if dataset == 'inventory':
        st.caption(f'Inventory updates the current balance and records a snapshot dated {as_of.isoformat()}. '
                   'Omitted reserved_qty defaults to zero. Open requests are checked again when reviewed.')
    elif dataset == 'products':
        st.caption('Optional columns: on_hand, on_order, reserved_qty. Omitted balances are preserved for existing products.')
    elif dataset == 'sales':
        st.caption('sale_date uses YYYY-MM-DD. Units must be whole non-negative numbers. Conflicting records are rejected.')
    else:
        st.caption('Only name is required. lead_time_days and contact_email are optional.')
    upload = st.file_uploader('Choose CSV or Excel file', type=['csv', 'xlsx'], key=f'{prefix}_upload')
    if st.button('Validate and import', key=f'{prefix}_import', disabled=upload is None):
        try:
            with st.spinner('Validating file and recording changes...'):
                count = import_dataset(conn, upload.getvalue(), upload.name, dataset,
                                       actor=st.session_state.get('operator', 'demo_manager'), as_of=as_of)
            st.session_state['flash'] = f'Imported {count} changed {dataset} record(s).'
            st.rerun()
        except ValueError as error:
            st.error(str(error))


def _inventory(conn: Any, rows: list[dict[str, Any]], as_of: date) -> None:
    risk = st.multiselect('Risk categories', list(RISK_COLORS), key='risk_filter')
    visible = [r for r in rows if not risk or r['risk'] in risk]
    _table(visible, ['sku', 'product_name', 'supplier', 'risk', 'on_hand', 'on_order',
                     'reserved_qty', 'safety_stock', 'lead_time_days', 'avg_daily_demand',
                     'demand_change_pct', 'inventory_position', 'reorder_point',
                     'target_stock', 'quantity', 'estimated_cost_vnd', 'sales_days_observed',
                     'data_quality_issue'])
    export_rows = [{'assessment_date': as_of.isoformat(), **row} for row in visible]
    st.download_button('Download inventory KPI CSV',
                       make_csv(export_rows, list(export_rows[0]) if export_rows else report_fields('replenishment')),
                       f'inventory_assessment_{as_of.isoformat()}.csv', 'text/csv')
    with st.expander('How replenishment is calculated'):
        st.markdown('''The policy uses the last **14 calendar days**, including the analysis date.

- **Average daily demand** = units sold in the window / 14.
- **Inventory position** = on-hand + on-order − reserved quantity.
- **Reorder point** = ceil(daily demand × supplier lead time + safety stock).
- **Target stock** = ceil(daily demand × (lead time + 4 review days) + safety stock).
- **Order quantity** = positive gap to target, rounded up to a full pack, when the reorder rule is met.

Python computes every quantity. Missing or invalid business data is flagged for review;
the AI assistant only explains the result. Pending requests are checked before drafting.''')
    st.divider()
    _import_panel(conn, as_of, 'inventory')


def _requests(conn: Any, proposals: list[dict[str, Any]], as_of: date) -> None:
    st.caption('Draft generation evaluates all SKUs at the analysis date. Existing pending requests are deduplicated. '
               'SKU and supplier filters control the request list below.')
    if st.button('Generate draft purchase requests', type='primary'):
        try:
            with st.spinner('Evaluating replenishment rules...'):
                count = create_drafts(conn, as_of=as_of,
                                      actor=st.session_state.get('operator', 'demo_manager'))
            st.session_state['flash'] = f'{count} new draft request(s) created. Review exceptions on Overview if any items were blocked.'
            st.rerun()
        except ValueError as error:
            st.error(str(error))
    statuses = st.multiselect('Request status', ['DRAFT', 'APPROVED', 'REJECTED'], key='status_filter')
    shown = [p for p in proposals if not statuses or p['status'] in statuses]
    _table(shown, ['id', 'sku', 'product_name', 'supplier', 'quantity', 'estimated_cost_vnd',
                   'status', 'reason', 'created_at', 'decided_at', 'decided_by', 'comment'])
    pending = [p for p in shown if p['status'] == 'DRAFT']
    if not pending:
        st.info('No drafts are awaiting review in this view.')
        return
    st.divider()
    st.subheader('Review a draft')
    ids = {p['id']: p for p in pending}
    chosen = st.selectbox('Select draft', list(ids),
                          format_func=lambda value: f"#{value} · {ids[value]['sku']} · {ids[value]['quantity']:,} units")
    proposal = ids[chosen]
    st.write(proposal.get('reason', 'Review the saved replenishment snapshot.'))
    st.caption(f"Snapshot value: {proposal['estimated_cost_vnd']:,} VND · Approval updates the on-order balance.")
    actor = st.text_input('Reviewer name (demo only)', value=st.session_state.get('operator', 'demo_manager'),
                          key='reviewer_name')
    if st.session_state.pop('clear_review_reason', False):
        st.session_state['review_reason'] = ''
    comment = st.text_area('Review reason', placeholder='Explain the approval or rejection.', key='review_reason')
    left, right = st.columns(2)
    approve = left.button('Approve selected draft', type='primary', width='stretch')
    reject = right.button('Reject selected draft', width='stretch')
    if approve or reject:
        try:
            decide(conn, chosen, 'APPROVED' if approve else 'REJECTED', actor, comment)
            st.session_state['clear_review_reason'] = True
            st.session_state['flash'] = ('Draft approved; on-order inventory updated. No supplier order was sent.'
                                         if approve else 'Draft rejected; the review decision was recorded.')
            st.rerun()
        except ValueError as error:
            st.error(str(error))


def _insights(rows: list[dict[str, Any]], as_of: date) -> None:
    snapshot = json.dumps(rows, sort_keys=True, default=str)
    st.write('Explain inventory risk, changing demand, and points for the procurement reviewer to check.')
    st.info('AI is advisory. Purchase quantities and approvals are controlled by Python rules and human review.')
    if st.button('Generate inventory risk summary', type='primary'):
        with st.spinner('Preparing read-only inventory analysis...'):
            text, source = summarize(rows)
        st.session_state['analysis'] = (text, source, as_of.isoformat(), snapshot)
    analysis = st.session_state.get('analysis')
    if analysis:
        text, source, saved_date, saved_snapshot = analysis
        if saved_date != as_of.isoformat() or saved_snapshot != snapshot:
            st.warning('The date, filters, or inventory changed since this analysis. Generate it again for the current view.')
        st.subheader('Analyst briefing')
        st.markdown(text)
        st.caption(f'Analysis source: {source} · Assessment date: {saved_date} · Human review required.')
    else:
        st.caption('Generate a briefing using the local business rules. The new web workspace includes the conversational agent.')
    with st.expander('Data shared with the assistant'):
        st.write('Only validated inventory metrics are supplied. API failures use the local deterministic summary. '
                 'The assistant has no database connection or approval tools.')
        _table(rows, ['sku', 'risk', 'avg_daily_demand', 'demand_change_pct',
                      'inventory_position', 'reorder_point', 'quantity', 'estimated_cost_vnd'])


def _analytics(conn: Any, rows: list[dict[str, Any]], proposals: list[dict[str, Any]],
               period: tuple[date, date], as_of: date) -> None:
    report = build_report(conn, as_of)
    skus = {r['sku'] for r in rows}
    start, end = (d.isoformat() for d in period)
    sales = [r for r in report['sales'] if r['sku'] in skus and start <= r['sale_date'] <= end]
    snapshots = [r for r in report['inventory_snapshots']
                 if r['sku'] in skus and start <= r['snapshot_date'] <= end]
    left, right = st.columns(2)
    with left:
        st.subheader('Demand trend')
        if sales:
            daily = pd.DataFrame(sales).groupby('sale_date', as_index=False)['units'].sum()
            _plot(px.line(daily, x='sale_date', y='units', markers=True,
                          labels={'sale_date': 'Sales date', 'units': 'Units sold'},
                          color_discrete_sequence=['#087F8C']), 'demand_trend')
        else:
            st.info('No sales records in the selected period.')
    with right:
        st.subheader('Inventory trend')
        if snapshots:
            snapshots_frame = pd.DataFrame(snapshots).sort_values(['created_at', 'id'])
            latest = snapshots_frame.drop_duplicates(['snapshot_date', 'sku'], keep='last')
            daily_stock = latest.groupby('snapshot_date', as_index=False)[['on_hand', 'on_order', 'reserved_qty']].sum()
            _plot(px.line(daily_stock, x='snapshot_date', y=['on_hand', 'on_order', 'reserved_qty'],
                          markers=True, labels={'snapshot_date': 'Snapshot date', 'value': 'Units'},
                          color_discrete_sequence=['#087F8C', '#6D91BC', '#D69A26']), 'inventory_trend')
            st.caption('Latest recorded balance per SKU/day. Dates without a snapshot are not fabricated.')
        else:
            st.info('No inventory snapshots in the selected period.')
    left, right = st.columns(2)
    with left:
        st.subheader('Supplier lead time')
        if rows:
            leads = pd.DataFrame(rows).groupby('supplier', as_index=False)['lead_time_days'].mean()
            _plot(px.bar(leads, x='supplier', y='lead_time_days',
                         labels={'supplier': 'Supplier', 'lead_time_days': 'Mean product lead time (days)'},
                         color_discrete_sequence=['#087F8C']), 'supplier_lead_time')
    with right:
        st.subheader('Purchase request status')
        _status_chart(proposals)
    st.divider()
    _exports(report, rows)


def _exports(report: dict[str, list[dict[str, Any]]], rows: list[dict[str, Any]]) -> None:
    st.subheader('Export reports')
    st.caption('The workbook contains all persisted records and the analysis-date assessment. '
               'CSV exports use normalized column names suitable for Power BI. Sidebar filters affect the inventory CSV.')
    st.download_button('Download full Excel report', make_excel(report),
                       file_name='procureflow_report.xlsx',
                       mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    dataset = st.selectbox('CSV report dataset', list(report), key='report_dataset')
    if dataset == 'replenishment':
        skus = {r['sku'] for r in rows}
        records = [r for r in report[dataset] if r['sku'] in skus]
    else:
        records = report[dataset]
    st.download_button('Download selected CSV report', make_csv(records, list(records[0]) if records else report_fields(dataset)),
                       file_name=f'{dataset}.csv', mime='text/csv')


def _audit(conn: Any) -> None:
    st.caption('Persisted events record actors, timestamps, and relevant before/after snapshots. '
               'Ordinary application actions retain the history.')
    audit = get_audit_logs(conn)
    st.subheader('Audit trail')
    _table(audit)
    st.download_button('Download audit log CSV', make_csv(audit, list(audit[0]) if audit else report_fields('audit_logs')),
                       'audit_logs.csv', 'text/csv')
    proposals = get_proposals(conn)
    st.download_button('Download proposal status report CSV',
                       make_csv(proposals, list(proposals[0]) if proposals else report_fields('proposals')),
                       'procurement_proposals.csv', 'text/csv')
    st.subheader('Approval history')
    _table(get_approval_history(conn))
    st.subheader('Exception history')
    _table(get_exceptions(conn))


def _settings(conn: Any, path: str, as_of: date) -> None:
    st.subheader('Demo operator')
    operator = st.text_input('Operator name', value=st.session_state.get('operator', 'demo_manager'),
                             key='operator_input',
                             help='Recorded on imports and draft creation. This is a demo identity, not authentication.')
    st.session_state['operator'] = operator
    st.subheader('Application configuration')
    st.write(f'Analysis date: **{as_of.isoformat()}**')
    st.code(f'Database: {Path(path).name}\nAgent: local business tools')
    st.write('Local summaries require no API key. The conversational agent is available in the React workspace.')
    st.caption('Configure PROCUREFLOW_DB_PATH using the environment or .env. Restart after changing configuration.')
    st.info('Academic prototype using synthetic data. Not affiliated with or endorsed by Trung Nguyen Legend. '
            'Demo reviewer names do not provide authentication or role-based access.')
    st.divider()
    _import_panel(conn, as_of, 'settings')


def run() -> None:
    """Open a fresh connection per rerun and close it after rendering the page."""
    _configure()
    path = os.getenv('PROCUREFLOW_DB_PATH', 'procureflow.db')
    conn = connect(path)
    try:
        init_db(conn)
        seed_if_empty(conn, as_of=_business_today())
        initial_rows = get_replenishment_table(conn)
        page, as_of, skus, suppliers, period = _sidebar(initial_rows)
        all_rows = get_replenishment_table(conn, as_of)
        rows = _filtered(all_rows, skus, suppliers)
        proposals = _filtered(get_proposals(conn), skus, suppliers)
        st.markdown('<div class="eyebrow">OPERATIONS WORKSPACE</div>', unsafe_allow_html=True)
        st.title(page)
        st.caption(f'Intelligent Procurement & Inventory Automation System · Demand window ends: {as_of.isoformat()}')
        if as_of != _business_today():
            st.caption('The analysis date changes the demand lookback window. Replenishment uses current inventory balances.')
        if 'flash' in st.session_state:
            st.success(st.session_state.pop('flash'))
        if page == 'Overview':
            selected_skus = {r['sku'] for r in rows}
            exceptions = [e for e in get_exceptions(conn)
                          if e.get('sku') is None or e['sku'] in selected_skus]
            _overview(rows, proposals, exceptions)
        elif page == 'Inventory':
            _inventory(conn, rows, as_of)
        elif page == 'Procurement Requests':
            _requests(conn, proposals, as_of)
        elif page == 'AI Insights':
            _insights(rows, as_of)
        elif page == 'Analytics':
            _analytics(conn, rows, proposals, period, as_of)
        elif page == 'Audit Logs':
            _audit(conn)
        else:
            _settings(conn, path, as_of)
        st.divider()
        st.caption('Academic prototype using synthetic data. Not affiliated with or endorsed by Trung Nguyen Legend. '
                   'No supplier orders or payments are sent. AI explanations require human review.')
    finally:
        conn.close()
