# Interview demo: 3–5 minutes

This script demonstrates a working academic prototype with synthetic data. It is not affiliated with or endorsed by Trung Nguyen Legend and sends no supplier orders or payments. Use a fresh database for each recording so previous approvals and audit history remain intact.

## Prepare a reproducible UI session

Run these commands from the project root in PowerShell after completing the README installation steps:

```powershell
.\.venv\Scripts\python.exe -m scripts.export_samples --as-of 2026-10-26
.\.venv\Scripts\python.exe -m src.seed --db procureflow_interview_20261026_01.db --as-of 2026-10-26
$env:PROCUREFLOW_DB_PATH = 'procureflow_interview_20261026_01.db'
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Open `http://localhost:8501`. Select **Analysis date → 2026-10-26** and use trend dates within the preceding 84 days. Leave SKU/supplier filters empty initially. The app normally seeds a new database through the current Vietnam business date; the explicit seed command above fixes the scenario date for repeatable recording. If the named database already contains products, seeding preserves them. For another clean recording, choose a new filename such as `procureflow_interview_20261026_02.db`, seed that path, and update `PROCUREFLOW_DB_PATH`; do not delete an old database to reset the demo.

For the offline AI segment, leave `GEMINI_API_KEY` unconfigured in the environment, `.env`, and Streamlit secrets. Keep configuration files with secrets off-screen. The offline command-line replay below always uses the local fallback, regardless of a configured key.

Keep these synthetic inputs ready:

- `data/demo_inventory_shortage.csv`: changes `CF-001` on-hand to 12, on-order to zero, reserved quantity to five.
- `data/synthetic_sales.xlsx`: the reference seed's 84-day sales history, in one worksheet.
- `data/demo_sales.csv`: reference-date sales, useful for demonstrating identical reimports.

## Recording sequence and English narration

| Time | Actions | Suggested narration |
|---|---|---|
| 0:00–0:30 | Open **Overview**. Show SKU count, physical-stock risk, pending requests, and recommended value. | “ProcureFlow AI turns a manual inventory review into a traceable replenishment workflow. This is an academic prototype with synthetic data. Python calculates the purchasing recommendation; a person makes the decision.” |
| 0:30–1:10 | Open **Settings**. Enter `portfolio_reviewer` as **Operator name**. Under **Import operational data**, choose **Inventory**, upload `demo_inventory_shortage.csv`, then click **Validate and import**. Choose **Sales**, upload `synthetic_sales.xlsx`, and import again. | “Files are validated before database changes are committed. This inventory file creates a controlled shortage. The sales workbook is already present in this seeded scenario, so importing identical records reports zero changed rows. That is safe replay behavior.” |
| 1:10–1:45 | Open **Inventory**. Filter **SKUs** to `CF-001`. Show on-hand, reserved stock, position, reorder point, target, and recommended quantity. Expand **How replenishment is calculated**. Clear the SKU filter afterwards. | “The rule uses fourteen calendar days of demand, supplier lead time, safety stock, and pack size. Reserved stock reduces availability. The order quantity fills the target gap in complete packs. These values are deterministic and testable.” |
| 1:45–2:15 | Open **Procurement Requests**. Click **Generate draft purchase requests**, then click it again. For this fresh fixed-date scenario, the first click creates three drafts and the second creates zero. Show a saved reason. | “Draft creation is repeatable. Existing pending or approved requests prevent another request for the same item. Each draft stores the numbers and cost used in its recommendation.” |
| 2:15–2:45 | Open **AI Insights**. Click **Generate inventory risk summary**. Show **Analysis source: RULE_BASED_FALLBACK**. | “The assistant explains risk and review checks. The application works without an API key. If Gemini is configured but times out or returns invalid output, the same local explanation keeps the workflow available. AI cannot change stock or approve a request.” |
| 2:45–3:35 | Return to **Procurement Requests**. Select the `CF-001` draft. Enter reviewer `portfolio_reviewer` and reason `Physical stock, reservations, and inbound deliveries reviewed.` Click **Approve selected draft**. Select a different draft, enter reason `Defer replenishment until the buyer confirms the demand assumptions.` Click **Reject selected draft**. | “Both decisions require a reviewer and a reason. Approval revalidates the saved snapshot before increasing simulated on-order stock. Rejection keeps inventory unchanged. This is an internal sign-off, not a supplier purchase order.” |
| 3:35–4:00 | Open **Audit Logs**. Show creation events, decisions, approval history, timestamps, and before/after evidence. | “The database retains who acted, when they acted, and the relevant state changes. Normal application actions cannot delete this history. Reviewer names are manual demo identities; production authentication remains future work.” |
| 4:00–4:40 | Open **Analytics**. Show demand trend, recorded inventory snapshots, product lead times by supplier, and request status. Click **Download full Excel report**. Select a dataset under **CSV report dataset** and click **Download selected CSV report**. | “Reports expose clean tables for Excel or Power BI import. The inventory history is labeled synthetic, and charts use recorded snapshots. I have not claimed measured savings or created a Power BI dashboard.” |
| 4:40–5:00 | Return to **Overview**. Show the reduced pending count and current recommendation. | “The loop is complete: import, calculate, draft, explain, review, persist, and report. Incoming quantities can remove another buying recommendation while physical-stock risk remains until delivery. Receiving goods is outside this prototype.” |

The sidebar pages are exactly **Overview**, **Inventory**, **Procurement Requests**, **AI Insights**, **Analytics**, **Audit Logs**, and **Settings**. Use the labels above when rehearsing. The generation count of three applies to a clean reference scenario; for any modified database, report the count actually shown rather than promising that number.

The sales workbook is an intentional idempotency demonstration, not a claim that new sales were inserted. To demonstrate new sales, supply a previously unseen date/SKU record within the selected analysis date. Do not edit an existing sales value: conflicting stored records are rejected atomically. Import changes before generating drafts for the main recording; changing their numerical inputs afterwards deliberately makes approvals stale.

## Optional exception demonstration

Use a separate fresh recording database. Generate a draft, then change that SKU's on-hand inventory through **Settings** or **Inventory** import. Try approving the old draft with a reason. Approval is blocked, a stale-draft exception is recorded, and no on-order quantity is added. Reject the stale draft and generate a new one. This demonstrates revalidation; do not describe it as an AI decision.

## Command-line replay and saved evidence

```powershell
.\.venv\Scripts\python.exe -m scripts.demo --as-of 2026-10-26
```

Each invocation creates a new `outputs/demo/run_<UTC timestamp>_<unique suffix>/` directory. It imports suppliers and products, imports inventory and sales from Excel, applies the shortage CSV, demonstrates an identical sales reimport, creates drafts twice, approves one, rejects another, closes the connection, and reopens the database to verify persistence. It writes:

- `procureflow.db` with persisted requests, decisions, balances, exceptions, and audit evidence.
- `inputs/` with the replay's CSV/XLSX inputs.
- `offline_insights.txt` with the deterministic explanation.
- `reports.xlsx` and one CSV per exported dataset.
- `run_manifest.json` with actual changed-row counts, draft counts, decision IDs, and verified on-order values.

The script never calls Gemini or modifies a previous run folder. Inspect the manifest and [VERIFICATION.md](VERIFICATION.md) for results that were actually executed. The replay's workbook and database are evidence artifacts; they do not automatically download through the browser.

To inspect one replay in the UI, set `PROCUREFLOW_DB_PATH` to its printed database path, start Streamlit, and choose the replay's analysis date. That run already contains its approval and rejection; it is not a clean starting point for recording those actions again.

## Interview questions

**Why keep AI out of quantity calculations?** Integer rules make every value reproducible, testable, and explainable. Gemini is restricted to validated advisory text.

**What does the history prove?** It shows persisted application events and before/after evidence, with triggers protecting ordinary updates and deletes. A database administrator can still alter the SQLite file; this is not a tamper-proof compliance archive.

**How is the project relevant to manufacturing digitalization?** It demonstrates validated data collection, SQL storage, operational dashboards, rule automation, human review, and document traceability in an adjacent procurement workflow. It does not implement OEE or a manufacturing execution system.

**What remains before production use?** Authenticated roles, approval governance, ERP integration, receipt/cancellation lifecycles, backups, security review, and production-scale validation. Approved requests currently remain outstanding indefinitely.

**What has been verified?** Automated policy, import, workflow, reporting, mocked AI, and Streamlit AppTest scenarios. State the local test count from [VERIFICATION.md](VERIFICATION.md). Do not claim a live Gemini request or GitHub-hosted CI run unless evidence is added there.
