# Synthetic coffee-materials scenario

This is a separate reference dataset for an academic procurement demonstration. It contains 12 materials and six explicitly fictional suppliers. It is not affiliated with or endorsed by Trung Nguyen Legend or Bosch. Supplier identities, reserved `.example` email contacts, costs, lead times, balances, and demand signals are illustrative.

The original six-SKU starter dataset is preserved separately under `data/`. Material identifiers shared with that dataset belong to different scenarios; these files must be imported into a new workspace, not used to relabel an existing business database.

`coffee_products.csv` and its single-sheet Excel equivalent include optional `category`, `unit_of_measure`, `origin`, and `quality_notes` fields. Import suppliers, products, inventory, then sales. All four inputs have CSV and `.xlsx` equivalents. `manifest.json` records the scenario date and limitations.

The existing `sales` schema stores **synthetic material withdrawals** in this scenario: 84 days and 1,008 records. These are not company sales or actual manufacturing measurements. Green coffee, purchased roasted blending input, packaging, and accessories remain distinct categories. No blend recipe, production yield, bill of materials, or mass conversion is modeled.

Quantities are whole base units: `kg`, `piece`, `carton`, or `roll`. Kilograms are integer kilograms; fractional material flows are outside this prototype. Do not add physical quantities across different units. Quality notes are general receiving reminders, not acceptance standards, certified results, or purchasing specifications.

Create a new database without touching an existing workspace:

```powershell
.\.venv\Scripts\python.exe -m scripts.seed_coffee --db outputs/coffee-workspace.db --as-of 2026-10-26 --export-dir data/coffee
$env:PROCUREFLOW_DB_PATH='outputs/coffee-workspace.db'
.\.venv\Scripts\python.exe -m scripts.run
```

The seeder refuses every existing target file and requires `--db`. Choose another filename for another recording. It builds the validated scenario in isolation and publishes a new persistent database with audit evidence and explicitly labeled inventory snapshots. Historical balances simulate depletion without receipts.
