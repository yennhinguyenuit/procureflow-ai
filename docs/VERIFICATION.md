# Executed verification — premium coffee upgrade

Verified on **26 October 2026**, Windows, Python **3.13.6**, Node **24.13.0**.

## Preserved starting version and data

- Initial Git commit: `a752cc5`.
- Upgrade branch: `feat/premium-coffee-workspace`.
- Starting-state checkpoint: `816f6ba`.
- Baseline test run before changes: **148 passed**, one upstream Starlette/httpx deprecation warning.
- Existing `procureflow.db` was read into a preservation snapshot before changes. A final comparison of all original columns and rows across **12 tables** passed. No original supplier, product, balance, sale, request, approval, audit, snapshot, preference, or conversation value was replaced.
- The untracked `procureflow-review.zip` was left untouched. No remote push was performed.
- `outputs/coffee-workspace.db` is a separate synthetic reference database. Browser mutations used `outputs/premium-browser-qa.db`, not the original or reference workspace.

## Complete Python suite

Executed with a new independent writable temporary directory:

```powershell
$testTemp = Join-Path ([IO.Path]::GetTempPath()) ("ProcureFlow_Premium_" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $testTemp -Force | Out-Null
.\.venv\Scripts\python.exe -m pytest -q --basetemp=$testTemp -p no:cacheprovider
.\.venv\Scripts\python.exe -m pip check
```

Observed result: **214 passed, 0 failed, 1 warning in 46.16 seconds**. The warning is the upstream Starlette/httpx TestClient deprecation, not a failed application check. No coverage percentage is claimed.

| Test module | Cases |
|---|---:|
| test_procurement.py | 16 |
| test_data_import.py | 26 |
| test_workflow.py | 18 |
| test_ai_assistant.py | 17 |
| test_local_agent.py | 92 |
| test_api.py | 20 |
| test_demo.py | 2 |
| test_ui.py | 4 |
| test_material_metadata.py | 14 |
| test_premium_contracts.py | 5 |
| **Total** | **214** |

The suite covers retained calculations/imports/workflows, additive metadata migration, immutable request units, prohibited historical unit reinterpretation, database persistence, reports, API behavior, short Vietnamese queries, context, safe local planning, fallbacks, and permission boundaries. Streamlit AppTest exercises the retained compatibility UI; React checks below were performed separately in a real browser.

`pip check`: **No broken requirements found.** Python source compilation and `git diff --check` also passed. Git reported line-ending normalization notices, without whitespace errors.

## Frontend installation and production build

Executed:

```powershell
Set-Location frontend
npm.cmd ci
npm.cmd run build
```

The clean dependency installation completed with 110 packages. TypeScript and the Vite production build completed successfully with no build warnings. No frontend framework or component dependency was added for the premium redesign. Fonts are served locally, including Vietnamese subsets.

## Coffee scenario

The actual seeder created a new `outputs/coffee-workspace.db` and exported the separate `data/coffee/` inputs:

- 12 materials, six explicitly fictional suppliers.
- 84 days and 1,008 synthetic demand/withdrawal rows.
- Labeled synthetic depletion snapshots; no measured company inventory history.
- Green coffee, purchased roasted input, packaging, and accessories with whole kg/piece/carton/roll measures.
- Critical, low-stock, and healthy examples; four draft candidates in the clean reference.
- Tests verified refusal of an existing target file without changing its bytes, importable CSV/XLSX examples, and a working approval/rejection workflow.

Commercial values and supplier identities remain assumptions. Research provenance and the logo decision are in [RESEARCH_SOURCES.md](RESEARCH_SOURCES.md).

## Actual local Qwen inference

Runtime: official llama.cpp **b11889**, CPU, local loopback port 8089. Model: official **Qwen2.5 1.5B Instruct Q4_K_M**, 1,117,320,736 bytes. Runtime/model checksums were verified by the installer; provenance is retained in the ignored runtime manifest.

A live in-memory question matrix accepted local-model plans for:

- Giá / gia / Bao nhiêu tiền? / Chi phí? → budget.
- Còn hàng không? → inventory.
- Tại sao phải nhập thêm? → why_reorder.
- Nhà cung cấp nào? → suppliers.

Contextual questions retained CF-001. Fresh unscoped price/why questions kept SKU scope unset. Observed individual calls in that matrix were approximately 1.51–1.78 seconds; this is a local observation, not a performance guarantee.

The actual React chat also used local_model for a Vietnamese reorder question and the short follow-up **Giá**. Messages and evidence were restored after a real page reload. No cloud inference or Gemini request was used. Business values were rendered by Python tools, not invented by the model.

## Real Chrome browser acceptance

Used headless Chrome 155 through DevTools, with isolated QA data.

Passed:

- All eight pages rendered at 1600 px desktop and 390 px mobile.
- Both Inventory views fit at **1280 px** without table horizontal overflow.
- No page-level horizontal overflow across the mobile pages.
- Mobile navigation open/close.
- Category/risk filters, material sorting, keyboard-focus tooltips and Escape dismissal.
- Drawer focus loop/restoration, contextual supplier imports and the global search shortcut.
- Settings saved through the rendered form.
- Inventory search, record drawer, and a persisted balance edit.
- Native file selection, rejected negative inventory, useful error feedback, and a valid CSV import.
- Four draft requests; repeated generation did not duplicate them.
- Required review reason, one approval and one rejection; saved statuses, approval history and inbound balances verified independently.
- Native browser CSV and Excel downloads; the workbook's actual approval-history content was inspected.
- Vietnamese local-model chat, contextual price follow-up and restored conversation history.
- No JavaScript exceptions during the acceptance sessions.

The actual `python -m scripts.run --coffee` launcher was also started successfully and served the separate reference workspace on port8002. Normal startup and the original database remain separate.

Actual screenshots are in `docs/screenshots/`, including overview, inventory, assistant, 1280 px replenishment, mobile overview, material/request drawers and QA review outcomes. They were captured from the running application rather than generated as mockups.

## Boundaries

- No GitHub-hosted CI run or remote publication is claimed.
- Linux and Python 3.11 were not run locally; they remain configured CI targets.
- No authentication, enterprise load/security validation, ERP, goods receipt/cancellation, supplier-order transmission, or real company procurement has been added.
- No official company logo is bundled because applicable authorization was not established.
- No measured savings, forecast accuracy, performance improvement, or complete accessibility certification is claimed.
