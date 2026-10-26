"""Local FastAPI service and React SPA hosting for ProcureFlow AI.

The API delegates all stock, import, approval, and reporting behavior to the
same tested services used by the command-line demo. The advisory agent is local
and read-only with respect to procurement data.
"""
from __future__ import annotations

import csv
import io
import json
import os
import sqlite3
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from typing import Any, Iterator, Literal

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator

from src import local_agent
from src.data_import import DATASET_HEADERS, MAX_FILE_BYTES, import_dataset
from src.database import Connection, connect, init_db, now_utc
from src.procurement import (
    business_today, create_drafts, decide, get_approval_history, get_audit_logs,
    get_exceptions, get_proposals, get_replenishment_table,
)
from src.reporting import build_report, make_csv, make_excel, report_fields
from src.seed import seed_if_empty

load_dotenv()

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_LOCAL_ORIGINS = {
    'http://localhost:5173', 'http://127.0.0.1:5173',
    'http://localhost:8000', 'http://127.0.0.1:8000',
}
_DEFAULT_SETTINGS = {
    'operator_name': 'Procurement Manager', 'workspace_name': 'ProcureFlow Workspace',
}
_REPORT_ALIASES = {
    'requests': 'proposals', 'audit': 'audit_logs',
    'approvals': 'approval_history', 'snapshots': 'inventory_snapshots',
}


def _iso_date(value: str | date | None) -> date | None:
    if value is None:
        return None
    if type(value) is date:
        return value
    if not isinstance(value, str):
        raise ValueError('Date must use YYYY-MM-DD')
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError('Date must use YYYY-MM-DD') from exc
    if parsed.isoformat() != value:
        raise ValueError('Date must use YYYY-MM-DD')
    return parsed


def _query_date(value: str | None) -> date:
    try:
        return _iso_date(value) or business_today()
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


class _Body(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class DatedBody(_Body):
    as_of: date | None = None

    @field_validator('as_of', mode='before')
    @classmethod
    def validate_date(cls, value: Any) -> date | None:
        return _iso_date(value)


class GenerateBody(DatedBody):
    actor: str = Field(min_length=1, max_length=100)


class DecisionBody(_Body):
    decision: Literal['APPROVED', 'REJECTED']
    actor: str = Field(min_length=1, max_length=100)
    comment: str = Field(min_length=1, max_length=2000)


class InventoryBody(DatedBody):
    on_hand: int = Field(ge=0, le=1_000_000_000, strict=True)
    on_order: int = Field(ge=0, le=1_000_000_000, strict=True)
    reserved_qty: int = Field(ge=0, le=1_000_000_000, strict=True)
    actor: str = Field(min_length=1, max_length=100)


class SettingsBody(_Body):
    operator_name: str | None = Field(default=None, min_length=1, max_length=100)
    workspace_name: str | None = Field(default=None, min_length=1, max_length=100)


class ChatBody(DatedBody):
    message: str = Field(min_length=1, max_length=4000)
    conversation_id: str | None = Field(default=None, min_length=1, max_length=100)
    sku: str | None = Field(default=None, min_length=1, max_length=200)


def _settings(conn: Connection) -> dict[str, str]:
    return {row['key']: row['value'] for row in conn.execute('SELECT key,value FROM app_settings')}


def _report(conn: Connection, as_of: date) -> dict[str, list[dict[str, Any]]]:
    with conn:
        conn.execute('BEGIN')
        tables = build_report(conn, as_of)
        # Include immutable supplier/cost snapshots and calculated values.
        tables['proposals'] = get_proposals(conn)
    return tables


def create_app(db_path: str | Path | None = None, static_dir: str | Path | None = None,
               seed_date: date | None = None) -> FastAPI:
    """Create an isolated local application; tests supply a temporary DB path."""
    configured_path = str(db_path or os.getenv('PROCUREFLOW_DB_PATH', 'procureflow.db'))
    distribution = Path(static_dir) if static_dir is not None else _PROJECT_ROOT / 'frontend' / 'dist'

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        conn = connect(configured_path)
        try:
            init_db(conn)
            seed_if_empty(conn, seed_date or business_today())
            local_agent.init_agent_db(conn)
            with conn:
                conn.execute('''CREATE TABLE IF NOT EXISTS app_settings(
                    key TEXT PRIMARY KEY,value TEXT NOT NULL)''')
                for key, value in _DEFAULT_SETTINGS.items():
                    conn.execute('INSERT OR IGNORE INTO app_settings(key,value) VALUES(?,?)', (key, value))
        finally:
            conn.close()
        yield

    application = FastAPI(title='ProcureFlow AI Local API', version='1.0.0', lifespan=lifespan)
    application.state.db_path = configured_path
    application.state.static_dir = distribution
    application.add_middleware(CORSMiddleware, allow_origins=sorted(_LOCAL_ORIGINS),
                               allow_methods=['GET', 'POST', 'PATCH', 'OPTIONS'],
                               allow_headers=['Content-Type'])

    @application.middleware('http')
    async def local_origin(request: Request, call_next):
        origin = request.headers.get('origin')
        if request.method in {'POST', 'PUT', 'PATCH', 'DELETE'} and origin and origin not in _LOCAL_ORIGINS:
            return JSONResponse({'detail': 'This local workspace accepts browser changes only from its local app.'}, status_code=403)
        return await call_next(request)

    @application.exception_handler(ValueError)
    async def validation_error(_: Request, exc: ValueError):
        return JSONResponse({'detail': str(exc)}, status_code=400)

    @application.exception_handler(sqlite3.IntegrityError)
    async def conflict_error(_: Request, __: sqlite3.IntegrityError):
        return JSONResponse({'detail': 'The change conflicts with existing workspace records.'}, status_code=409)

    @application.exception_handler(sqlite3.OperationalError)
    async def database_error(_: Request, __: sqlite3.OperationalError):
        return JSONResponse({'detail': 'The local database is temporarily unavailable. Retry the operation.'}, status_code=503)

    @application.exception_handler(Exception)
    async def unexpected_error(_: Request, __: Exception):
        return JSONResponse({'detail': 'The operation could not be completed. Check the local service and retry.'}, status_code=500)

    def database(request: Request) -> Iterator[Connection]:
        conn = connect(request.app.state.db_path)
        try:
            yield conn
        finally:
            conn.close()


    @application.get('/api/health')
    def health():
        return {'status': 'ok', 'service': 'procureflow-local'}

    @application.get('/api/workspace')
    def workspace(conn: Connection = Depends(database), as_of: str | None = None):
        assessed = _query_date(as_of)
        with conn:
            conn.execute('BEGIN')
            data = {
                'as_of': assessed.isoformat(),
                'inventory': get_replenishment_table(conn, assessed),
                'proposals': get_proposals(conn),
                'suppliers': [dict(row) for row in conn.execute('SELECT * FROM suppliers ORDER BY name')],
                'audit': get_audit_logs(conn), 'approvals': get_approval_history(conn),
                'exceptions': get_exceptions(conn),
                'sales': [dict(row) for row in conn.execute('SELECT * FROM sales ORDER BY sale_date,sku')],
                'snapshots': [dict(row) for row in conn.execute('SELECT * FROM inventory_snapshots ORDER BY snapshot_date,sku,id')],
                'settings': _settings(conn),
            }
        data['agent'] = local_agent.agent_status()
        return data

    @application.get('/api/settings')
    def settings(conn: Connection = Depends(database)):
        return _settings(conn)

    @application.patch('/api/settings')
    def update_settings(body: SettingsBody, conn: Connection = Depends(database)):
        updates = body.model_dump(exclude_unset=True)
        if not updates or any(value is None for value in updates.values()):
            raise HTTPException(422, 'Provide a nonempty operator_name or workspace_name')
        with conn:
            conn.execute('BEGIN IMMEDIATE')
            before = _settings(conn)
            after = {**before, **updates}
            if before != after:
                for key, value in updates.items():
                    conn.execute('UPDATE app_settings SET value=? WHERE key=?', (value, key))
                conn.execute('''INSERT INTO audit_logs(action,actor,comment,before_json,after_json,created_at)
                    VALUES('SETTINGS_UPDATED',?,'Workspace preferences updated',?,?,?)''',
                    (before['operator_name'], json.dumps(before), json.dumps(after), now_utc()))
        return after

    @application.post('/api/requests/generate')
    def generate(body: GenerateBody, conn: Connection = Depends(database)):
        count = create_drafts(conn, body.as_of or business_today(), actor=body.actor)
        return {'created': count, 'message': f'{count} purchase request draft(s) created.'}

    @application.post('/api/requests/{proposal_id}/decision')
    def decision(proposal_id: int, body: DecisionBody, conn: Connection = Depends(database)):
        decide(conn, proposal_id, body.decision, body.actor, body.comment)
        return {'message': f'Request {proposal_id} {body.decision.lower()}.'}

    @application.patch('/api/inventory/{sku}')
    def update_inventory(sku: str, body: InventoryBody, conn: Connection = Depends(database)):
        if conn.execute('SELECT 1 FROM products WHERE sku=?', (sku,)).fetchone() is None:
            raise HTTPException(404, 'SKU does not exist')
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=DATASET_HEADERS['inventory'])
        writer.writeheader()
        writer.writerow({'sku': sku, 'on_hand': body.on_hand, 'on_order': body.on_order,
                         'reserved_qty': body.reserved_qty})
        count = import_dataset(conn, output.getvalue().encode('utf-8'), 'inventory.csv',
                               'inventory', body.actor, body.as_of or business_today())
        return {'imported': count, 'message': 'Inventory saved.' if count else 'Inventory already matches these values.'}

    @application.post('/api/import/{dataset}')
    def upload(dataset: str, conn: Connection = Depends(database), file: UploadFile = File(...),
               actor: str = Form('demo_operator'), as_of: str | None = None):
        if dataset not in DATASET_HEADERS:
            raise HTTPException(404, 'Unknown import dataset')
        raw = file.file.read(MAX_FILE_BYTES + 1)
        if len(raw) > MAX_FILE_BYTES:
            raise HTTPException(413, 'File exceeds the 2 MB import limit')
        count = import_dataset(conn, raw, file.filename or '', dataset, actor, _query_date(as_of))
        return {'imported': count, 'message': f'{count} {dataset} row(s) imported.'}

    @application.get('/api/reports/workbook.xlsx')
    def workbook(conn: Connection = Depends(database), as_of: str | None = None):
        assessed = _query_date(as_of)
        return Response(make_excel(_report(conn, assessed)),
                        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                        headers={'Content-Disposition': f'attachment; filename="procureflow_{assessed.isoformat()}.xlsx"'})

    @application.get('/api/reports/{dataset}.csv')
    def csv_report(dataset: str, conn: Connection = Depends(database), as_of: str | None = None):
        normalized = _REPORT_ALIASES.get(dataset, dataset)
        tables = _report(conn, _query_date(as_of))
        if normalized not in tables:
            raise HTTPException(404, 'Unknown report dataset')
        rows = tables[normalized]
        fields = list(rows[0]) if rows else report_fields(normalized)
        if normalized == 'proposals' and not rows:
            fields += ['product_name', 'estimated_cost_vnd']
        return Response(make_csv(rows, fields), media_type='text/csv; charset=utf-8',
                        headers={'Content-Disposition': f'attachment; filename="procureflow_{normalized}.csv"'})

    @application.get('/api/templates/{dataset}.csv')
    def template(dataset: str):
        if dataset not in DATASET_HEADERS:
            raise HTTPException(404, 'Unknown import dataset')
        return Response(make_csv([], DATASET_HEADERS[dataset]), media_type='text/csv; charset=utf-8',
                        headers={'Content-Disposition': f'attachment; filename="{dataset}_template.csv"'})

    @application.get('/api/agent/status')
    def agent_status():
        return local_agent.agent_status()

    @application.post('/api/agent/chat')
    def agent_chat(body: ChatBody, conn: Connection = Depends(database)):
        return local_agent.chat(conn, body.message, conversation_id=body.conversation_id,
                                as_of=body.as_of, sku=body.sku)

    @application.get('/api/agent/conversations')
    def conversations(conn: Connection = Depends(database)):
        return local_agent.list_conversations(conn)

    @application.get('/api/agent/conversations/{conversation_id}/messages')
    def messages(conversation_id: str, conn: Connection = Depends(database)):
        return local_agent.get_messages(conn, conversation_id)

    @application.api_route('/api', methods=['GET', 'POST', 'PATCH', 'PUT', 'DELETE', 'OPTIONS'], include_in_schema=False)
    @application.api_route('/api/{path:path}', methods=['GET', 'POST', 'PATCH', 'PUT', 'DELETE', 'OPTIONS'], include_in_schema=False)
    def missing_api(path: str = ''):
        raise HTTPException(404, 'API endpoint does not exist')

    @application.get('/{path:path}', include_in_schema=False)
    def frontend(path: str):
        if path == 'api' or path.startswith('api/'):
            raise HTTPException(404, 'API endpoint does not exist')
        resolved_root = distribution.resolve()
        candidate = (resolved_root / path).resolve()
        if not candidate.is_relative_to(resolved_root):
            raise HTTPException(404, 'File does not exist')
        if path and candidate.is_file():
            return FileResponse(candidate)
        if path and (Path(path).suffix or path.startswith('assets/')):
            raise HTTPException(404, 'Frontend asset does not exist')
        index = resolved_root / 'index.html'
        if not index.is_file():
            raise HTTPException(503, 'Frontend build is missing. Build the frontend and restart the local app.')
        return FileResponse(index)

    return application


app = create_app()

