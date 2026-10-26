# Test plan and acceptance checks

Use an independent writable temporary directory; tests must not use the working business database.

```powershell
$testTemp = Join-Path ([IO.Path]::GetTempPath()) ("ProcureFlow_QA_" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $testTemp -Force | Out-Null
.\.venv\Scripts\python.exe -m pytest -q --basetemp=$testTemp -p no:cacheprovider
.\.venv\Scripts\python.exe -m pip check
Set-Location frontend
npm.cmd ci
npm.cmd run build
```

## Automated behavior checks

| Area | Acceptance |
|---|---|
| Policy | Exact ceilings, reservations, ROP boundary, target/pack rounding, zero demand, inbound coverage and physical risk. |
| Imports | CSV/XLSX validation, missing/negative/schema/date/reference errors, duplicates, conflicts, atomic rollback and identical reimports. |
| Metadata | Additive migrations preserve old records/imports; category/unit/origin/quality validation; correct blank optional cells. |
| Workflow | Draft creation, duplicate prevention, approve/reject once, stale inputs, saved cost/supplier/unit/category, limits. |
| Unit integrity | Historical quantities cannot silently change base unit; saved requests retain original units. |
| Audit | Actor/reason/timestamps/before-after persist; ordinary history updates/deletes are blocked. |
| Persistence/reporting | Temporary database reopen verifies import → assessment → draft → decision → workbook/CSV. |
| API | Existing routes, uploads/downloads/templates, settings, chat persistence, validation, local origin and SPA hosting. |
| Assistant | English/Vietnamese, compact SKU, short price/stock/why/supplier questions, context, scope, unit-aware facts, invalid plans, fallback and blocked writes. |
| Cloud exclusion | Offline summaries have no cloud calls; inference endpoints are loopback-only with no redirects or proxies. |
| Coffee data | Explicit new target, byte-preserving refusal of existing files, fictional 12-material scenario, 84-day withdrawals/snapshots and useful risk states. |

The retained Streamlit AppTest suite checks the compatibility UI; it does not substitute for real React browser testing. Mocked model tests do not establish live inference. Use a separate QA database for browser and live-model checks.

## Browser acceptance

Check desktop widths 1600/1280 and mobile width 390:

- Navigate all eight pages; inspect readable typography, contrast, spacing, loading/error/empty states and console exceptions.
- Inventory search/category/risk/supplier/sort and both table views; no horizontal table overflow on normal desktops.
- Material details/history/calculations and a persisted test balance edit.
- Native file selection for invalid/valid uploads; clear errors and no partial changes.
- Generate twice; required reason; approve one/reject another; verify statuses, balance and history.
- Real CSV/XLSX downloads and inspected contents.
- Contextual Giá, Bao nhiêu tiền?, Chi phí?, Còn hàng không?, Tại sao phải nhập thêm?, Nhà cung cấp nào?; correct units and actual execution mode.
- Saved conversation reload, expandable sources and system details, and blocked approval requests.
- Mobile navigation, contained tables, dialogs, Escape/focus behavior and keyboard-accessible tooltips.
- Compatible-unit charts only; no kg/piece/carton/roll physical total.

## Evidence

Git checkpoint `816f6ba` on `feat/premium-coffee-workspace` preserves the starting version. Baseline executed before this upgrade: **148 passed**, with one upstream Starlette/httpx deprecation warning. Final executed counts and browser/live-Qwen evidence are in VERIFICATION.md. No coverage percentage, business improvement, hosted-CI success or production-readiness claim is inferred.
