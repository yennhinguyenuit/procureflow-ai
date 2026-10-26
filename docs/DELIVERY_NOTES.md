# Delivered files

This workspace began with a working SQLite/Streamlit starter. Its policy, CSV interface, draft workflow, and regression tests were retained and upgraded; the application was not replaced with a static mockup.

| Area | Created or updated files |
|---|---|
| Entry and interface | `app.py`, `src/ui.py`, `.streamlit/config.toml` |
| Schema and storage | `src/database.py`, `src/models.py` |
| Imports and generated data | `src/data_import.py`, `src/validation.py`, `src/seed.py`, CSV/XLSX files under `data/` |
| Procurement | `src/procurement.py` |
| Advisory AI | `src/ai_assistant.py` |
| Reports and replay | `src/reporting.py`, `scripts/demo.py`, `scripts/export_samples.py` |
| Tests | All six `tests/test_*.py` files, including the retained starter regression tests |
| Portfolio | `README.md`, `docs/ARCHITECTURE.md`, `docs/DEMO_SCRIPT.md`, `docs/TEST_PLAN.md`, `docs/VERIFICATION.md`, `docs/screenshots/*.png`, `LICENSE` |
| Configuration | `requirements.txt`, `requirements-dev.txt`, `.env.example`, `.gitignore`, `.github/workflows/tests.yml` |

The starter's old `docs/OFFLINE_DEMO_OUTPUT.txt` was superseded by the actual replay manifest/output and the dated verification document; it is no longer presented as evidence of the upgraded system.

Local mutable artifacts (`.venv/`, `procureflow.db`, `outputs/`, caches) are ignored. No secrets, real supplier/customer data, or remote publication were introduced.

Implemented behavior, setup, Gemini configuration, GitHub commands, limitations, and three evidence-based English resume bullets are in the [README](../README.md). Executed results are in [VERIFICATION.md](VERIFICATION.md).
