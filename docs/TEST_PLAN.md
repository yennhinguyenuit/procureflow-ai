# Testing plan and acceptance criteria

Tests use temporary or in-memory databases. They do not reset the working demo database. Run the full suite from the project root:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

See [VERIFICATION.md](VERIFICATION.md) for the actual executed commands, environment, pass/fail count, replay artifacts, and any browser evidence. This document defines coverage and acceptance criteria; it does not substitute planned checks for executed results.

## Automated coverage

| Area | Acceptance criteria | Test module |
|---|---|---|
| Inventory arithmetic | Demand window includes zero calendar days; reserved stock reduces position; reorder and target ceilings use exact unit boundaries; quantities round to packs; zero demand and adequate inbound coverage avoid unnecessary purchases. | `tests/test_procurement.py`, `tests/test_workflow.py` |
| Physical risk | Critical physical-stock risk remains visible even when inbound coverage makes the recommended quantity zero; risk classes and invalid numerical inputs are checked. | `tests/test_workflow.py` |
| Input validation | Reject missing/unexpected/duplicate headers, invalid or future dates, unknown references, duplicate keys, negative/fractional invalid quantities, malformed files, and invalid SKU identifiers. | `tests/test_data_import.py`, `tests/test_workflow.py` |
| Import persistence | CSV and Excel imports persist; identical sales reimports change zero rows; conflicting stored records and later-row failures roll back the whole file; product-master updates preserve omitted stock fields. | `tests/test_data_import.py` |
| Storage compatibility | Inventory and legacy product balances remain synchronized; starter-schema migration preserves business data; initialization does not silently repair a deliberately missing supplier. | `tests/test_data_import.py` |
| Draft control | Repeated generation creates no duplicate pending request; missing suppliers/history and simulated limits produce persistent exceptions; clean databases enforce one draft per SKU; legacy duplicates are preserved and reported. | `tests/test_procurement.py`, `tests/test_workflow.py`, `tests/test_data_import.py` |
| Human decisions | Reviewer and reason are required; approval adds on-order stock once; rejection leaves stock unchanged; repeated decisions fail; stale stock, demand, or policy inputs block approval; saved unit costs preserve request value. | `tests/test_workflow.py`, `tests/test_procurement.py` |
| Multi-connection behavior | Two database connections cannot create duplicate pending drafts or approve a request twice. These targeted checks are not a high-load benchmark. | `tests/test_workflow.py` |
| Audit traceability | Imports and workflow changes record evidence; ordinary SQL updates/deletes of audit and approval history are rejected by triggers; outstanding approved quantities cannot be erased through an inventory import. | `tests/test_data_import.py`, `tests/test_workflow.py` |
| AI fallback and boundaries | No-key mode loads no SDK client; mocked API failures, missing SDK, timeout, malformed/oversized output, invented SKU/risk, unsafe prose, and invalid input fall back without exposing details or mutating source rows. | `tests/test_ai_assistant.py` |
| AI request contract | Mocked SDK checks verify the allowlisted aggregates, structured-output schema, bounded timeout, configurable model, and numerical/risk consistency. No live service availability is inferred. | `tests/test_ai_assistant.py` |
| Streamlit application | AppTest renders all seven pages, filters inventory by SKU, persists operator identity, creates/deduplicates drafts, validates missing review reasons, approves/rejects, reads decisions in another session, shows local AI, and warns when its saved briefing is stale. | `tests/test_ui.py` |
| Export artifacts | CSV formula-style strings are escaped; Excel preserves numeric types, exports normalized tables with headers, and contains durable approval evidence. Rendered download controls are reachable. | `tests/test_procurement.py`, `tests/test_ui.py`, `tests/test_workflow.py` |
| Full replay | Import → shortage → drafts → fallback → approval/rejection → close/reopen → CSV/XLSX export verifies durable state; another run uses a separate folder and preserves the previous run. | `tests/test_demo.py` |

For a numerical reference, demand of 10/day, lead time of five, safety stock of 20, on-hand of 55, on-order of zero, reserved stock of zero, and pack size of 20 yields a reorder point of 70, target of 110, position of 55, and order quantity of 60. Changing reserved quantity to five gives a position of 50 and still rounds the order to 60. Critical-stock status and purchase need are separate assertions.

## Reproduce the full offline workflow

```powershell
.\.venv\Scripts\python.exe -m scripts.demo --as-of 2026-10-26
```

Check the newly printed run path and its `run_manifest.json`. It records actual import/draft counts, confirms zero changes for an identical sales reimport, and verifies approved/rejected statuses and the exact on-order increase after reopening the file. Inspect `reports.xlsx`, the normalized CSVs, and `offline_insights.txt`. A subsequent invocation must use a new folder and leave the earlier database and audit trail intact.

## Manual browser acceptance

AppTest exercises real Streamlit widget reruns, but it does not replace a browser layout review or operating-system download check. Follow [DEMO_SCRIPT.md](DEMO_SCRIPT.md) in a fresh database and record results in [VERIFICATION.md](VERIFICATION.md):

- Start Streamlit on Windows and confirm the local page and all seven navigation labels render.
- Check KPI readability, table scrolling, Plotly charts, and SKU/supplier/date filters at the target recording resolution.
- Upload the shortage CSV and sales XLSX through the real file picker; confirm the reported changed-row counts and useful errors for an invalid file.
- Generate twice, enter reasons, approve one draft, reject another, and inspect the audit/approval records after refreshing the browser.
- Download the workbook and a CSV through the browser and open them in a compatible spreadsheet viewer.
- Confirm `RULE_BASED_FALLBACK` with no key. A real Gemini request is optional and must be reported separately from mocked SDK tests.
- Ensure the recording contains synthetic data and no credentials. Check that the academic/non-affiliation notice is visible.

## CI configuration and verification limits

`.github/workflows/tests.yml` configures four combinations: Ubuntu and Windows with Python 3.11 and 3.13. It installs `requirements-dev.txt` and runs the full pytest suite with an empty Gemini key. The presence of this file does not establish that GitHub executed the matrix; link actual runs only after they exist.

Automated tests do not establish measured efficiency gains, full test coverage, production security, authenticated authorization, ERP/real supplier integration, a receipt lifecycle, live Gemini availability, or high-load SQLite behavior. Audit triggers protect normal application operations but cannot prevent database-administrator tampering. See [ARCHITECTURE.md](ARCHITECTURE.md) for these boundaries and [VERIFICATION.md](VERIFICATION.md) for the current evidence.
