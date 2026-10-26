# Executed local verification

Verified on **26 October 2026** in Windows with **CPython 3.13.6** and a project-local `.venv`. These are observed results, not a coverage claim. The GitHub Actions matrix is configured but has not been executed on GitHub.

## Automated tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Observed result: **117 passed, 0 failed** (9.70 seconds on the recorded full run).

| Test file | Cases | Verified scope |
|---|---:|---|
| `tests/test_procurement.py` | 16 | Starter policy, workflow, imports, reporting, fallback regression |
| `tests/test_data_import.py` | 26 | CSV/XLSX validation, atomicity, references, migration, inventory synchronization, partial draft index |
| `tests/test_workflow.py` | 18 | Reservations, boundaries, missing data, limits, stale drafts, frozen prices, concurrent creation/approval, protected history, persisted import-to-report integration |
| `tests/test_ai_assistant.py` | 51 | Missing key/SDK, timeout/network/quota, structured output, safe payload, exact risk references, fallback; all clients mocked |
| `tests/test_ui.py` | 4 | Seven rendered pages, filters, imports/exports controls, operator persistence, draft/review buttons, separate session persistence, AI fallback/staleness, workbook cells |
| `tests/test_demo.py` | 2 | Complete offline replay and importable sample generation |

Tests use temporary or in-memory databases. They do not mutate the working demo database. UI file ingestion is tested through its shared import service; browser upload and native download dialogs are not automated.

```powershell
.\.venv\Scripts\python.exe -m pip check
```

Observed result: **No broken requirements found.** Installed core versions included Streamlit 1.66.1, Pandas 2.3.3, SQLAlchemy 2.1.6, Pydantic 2.14.1, Plotly 6.9.0, openpyxl 3.1.5, google-genai 2.33.0, pytest 9.1.1.

## Executed offline replay

```powershell
.\.venv\Scripts\python.exe -m scripts.demo --as-of 2026-10-26
```

The recorded run created `outputs/demo/run_20261026_022814_80b0b932/`. Its manifest verified:

- Imported 3 suppliers, 6 products, 6 inventory balances, and 504 sales rows.
- Applied one shortage update; identical sales reimport changed zero rows.
- Created 3 drafts; immediate repeated generation created zero.
- Approved request 1 (`CF-001`, 140 units) and rejected request 3.
- On-order quantity for `CF-001` changed from 0 to 140.
- Closed/reopened the SQLite file and verified saved statuses and balances.
- Exported `reports.xlsx`, ten CSV datasets, input samples, offline insights, and `run_manifest.json`.
- Persisted 3 proposals, 2 approval-history rows, and 10 audit events.

The run directory is local and ignored by Git. Each replay preserves existing runs. Inputs in the committed `data/` directory were regenerated with `python -m scripts.export_samples` for the fixed reference date.

## Application and visual checks

Started the actual Streamlit server at `http://127.0.0.1:8501`. Its `/_stcore/health` endpoint returned **HTTP 200** with `ok`. Opened the live app in headless Chrome 155, waited for rendered controls, navigated Overview → Inventory → Analytics, and captured actual screenshots in `docs/screenshots/`.

Overview and Analytics screenshots were visually inspected: navigation, KPI values, risk pie, inventory table, demand/inventory trends, supplier lead time chart, empty request state, and report controls rendered. The Inventory screenshot also captured the live inventory view. These are application screenshots, not generated mockups.

The headless browser returned to Overview after capture. The working `procureflow.db` contains the synthetic seed and is excluded from Git. Approval/rejection behavior was exercised in isolated AppTest and CLI databases.

## Unverified or deliberately excluded

- No live Gemini request was made; a real API key/account/quota was not supplied. SDK configuration types and failure paths were tested locally with mocked clients.
- Python 3.11 and Linux were not executed locally. CI is configured for Python 3.11/3.13 on Windows/Linux.
- No GitHub repository was initialized/pushed and no remote Actions result is claimed.
- Native browser file picker/download behavior, Excel Desktop, Power BI Desktop, enterprise concurrency, authentication, ERP integration, and production security were not verified.
- No performance improvement, business savings, forecast quality, or percentage of code coverage was measured.

See [TEST_PLAN.md](TEST_PLAN.md) for repeatable checks and [DEMO_SCRIPT.md](DEMO_SCRIPT.md) for the recording workflow.
