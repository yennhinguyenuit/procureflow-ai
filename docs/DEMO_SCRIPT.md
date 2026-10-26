# Coffee procurement walkthrough

Independent academic case study with synthetic data; not an official Trung Nguyên Legend system. Every supplier, price, stock quantity, and demand value is illustrative.

## Open a separate scenario

```powershell
.\.venv\Scripts\python.exe -m scripts.run --coffee
```

Or double-click run-coffee.bat. Open http://127.0.0.1:8002. This explicitly selects outputs/coffee-workspace.db and preserves procureflow.db and normal port8000 startup. Pass --port to choose another web port.

For a new recording, choose an unused filename:

```powershell
.\.venv\Scripts\python.exe -m scripts.seed_coffee --db outputs/coffee-recording-02.db --as-of 2026-10-26
$env:PROCUREFLOW_DB_PATH='outputs/coffee-recording-02.db'
.\.venv\Scripts\python.exe -m scripts.run
```

The seeder refuses existing files. Select analysis date 2026-10-26 for this reference dataset. Demand represents synthetic material withdrawals in the retained sales schema, not measured company sales.

## Four-to-five-minute recording

| Time | Actions | Explain |
|---|---|---|
| 0:00–0:35 | Overview: metrics, demand, stock classification and priorities | Current balances, historical observations and procurement estimates are distinct; no real company KPIs are claimed. |
| 0:35–1:20 | Inventory: filter Green coffee, search CF-001, switch Stock balances/Replenishment, open details | Category, origin, kg, supplier, reservations, lead time, ROP, target and pack rounding are explicit. Chart totals use compatible units. |
| 1:20–1:50 | Import data: inspect a dataset template and upload a file | The whole file validates before changes are committed. Identical reference rows legitimately report zero changes. |
| 1:50–2:40 | Purchase requests: Generate twice, review one, approve and reject with reasons | A clean coffee reference has four recommendations; use the actual count shown. Repeated generation prevents duplicate open requests. Approval changes only internal on-order stock. |
| 2:40–3:30 | Operational Assistant: Why reorder CF-001? → Giá → Còn hàng không? → Nhà cung cấp nào? | Short follow-ups retain material context. Expand sources and execution details to show actual mode/model attribution. |
| 3:30–3:55 | Ask Approve CF-001 now. | The assistant cannot approve/reject, edit balances, run arbitrary SQL or place supplier orders. |
| 3:55–4:25 | Activity: filter event/record, inspect decisions and before/after evidence | Actor, timestamp, reason and affected record persist. |
| 4:25–5:00 | Analytics: change unit/supplier filters, download workbook; Settings: expand system details | Charts show recorded observations and estimates. Model diagnostics remain available without dominating the product. |

## Additional checks

- Stale draft: generate, adjust the material balance, then try approval. The exception is recorded and approval blocked. Reject and regenerate.
- Review reason: decision controls require a reviewer and non-empty reason.
- Fallback: use --without-model; the same read-only tools still answer. Verify actual per-answer mode.
- Persistence: reload, open conversation history, and inspect saved messages/evidence.
- Unit integrity: a material with stock/history cannot be reinterpreted in another base unit; saved requests retain the original unit.

## Retained offline replay

```powershell
.\.venv\Scripts\python.exe -m scripts.demo --as-of 2026-10-26
```

This original six-SKU scenario writes its own new outputs/demo/run_*/ folder, database, input files, workbook/CSVs and manifest, then reopens the database to verify persistence. It remains separate from the 12-material coffee dataset and never calls a cloud model.

See VERIFICATION.md for executed evidence, RESEARCH_SOURCES.md for material context, and DESIGN_SYSTEM.md for interface decisions. Authentication, ERP integration, receipt lifecycle and measured savings are not demonstrated.
