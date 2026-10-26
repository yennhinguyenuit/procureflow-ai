# Premium coffee upgrade — delivered changes

The existing React/FastAPI application and working local Qwen integration were upgraded in place. The starting version is preserved at checkpoint `816f6ba` on `feat/premium-coffee-workspace`; historical commits and the original business database remain intact.

| Area | Changed files |
|---|---|
| Interface and design | `frontend/src/App.tsx`, `Overview.tsx`, `OperationsPages.tsx`, `InsightsPages.tsx`, `WorkflowDialogs.tsx`, `AIWorkspace.tsx`, `Charts.tsx`, `components.tsx`, `styles.css`, `types.ts`, `workspaceData.ts`, `main.tsx`, `env.d.ts` |
| Neutral branding | `frontend/public/brand/README.md`; no official logo bundled |
| Metadata and integrity | `src/models.py`, `src/database.py`, `src/data_import.py`, `src/procurement.py`, `src/reporting.py` |
| Local application service | `src/api.py`, `scripts/run.py`, `run-coffee.bat` |
| Operational Assistant | `src/local_agent.py`, `tests/test_local_agent.py`, `docs/LOCAL_AGENT.md` |
| Separate coffee scenario | `scripts/seed_coffee.py`, `data/coffee/*.csv`, `data/coffee/*.xlsx`, manifest and README |
| New regression coverage | `tests/test_material_metadata.py`, `tests/test_premium_contracts.py` |
| Evidence and documentation | `README.md`, `docs/RESEARCH_SOURCES.md`, `docs/DESIGN_SYSTEM.md`, `docs/ARCHITECTURE.md`, `docs/DEMO_SCRIPT.md`, `docs/TEST_PLAN.md`, `docs/VERIFICATION.md`, screenshots |

The separate readability override stylesheet was consolidated into one token-based design stylesheet. Existing API routes, original six-SKU data/replay, storage services and tests were retained. Product metadata is additive; request costs, supplier and unit/category are saved as evidence. Original quantities are never silently converted.

The interface now uses ivory/charcoal/espresso styling, business-first page content, unit-safe charts, fitted inventory views, filters/sorting, accessible calculation tooltips and practical review dialogs. Assistant sources and real execution/model attribution remain available in expandable details.

Verified: **214 Python tests passed**, clean production build, dependency check, live local Qwen short-query matrix, and real browser workflows at desktop/mobile widths. See VERIFICATION.md for scope and limitations.

Launch the separate coffee workspace with `run-coffee.bat` or `python -m scripts.run --coffee`, then open http://127.0.0.1:8002. Normal startup continues to use the existing configured database on port8000.
