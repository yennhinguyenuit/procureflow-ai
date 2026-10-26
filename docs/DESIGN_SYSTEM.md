# ProcureFlow design system

The interface is a restrained operations workspace for the coffee procurement case study. It uses the existing React, TypeScript, Vite, and Recharts application and preserves the persistent Python workflows. The visual identity is ProcureFlow's own neutral wordmark. No official Trung Nguyen Legend or Bosch logo is bundled, and the interface does not imply company endorsement.

## Palette and meaning

The single token layer lives at the start of [`frontend/src/styles.css`](../frontend/src/styles.css). Page and component rules consume these tokens; the previous readability override stylesheet has been removed.

| Token | Value | Purpose |
|---|---|---|
| Canvas | `#F7F5F1` | Warm ivory application background |
| Surface | `#FFFFFF` | Tables, records, dialogs, and reporting panels |
| Ink | `#25231F` | Primary text, headings, and the neutral wordmark |
| Muted | `#756D63` | Secondary operational text |
| Border | `#E7E1D8` | Warm gray structural dividers |
| Espresso | `#5B3E2B` | Primary actions and selected navigation |
| Bronze | `#A58763` | Restrained icons, focus indicators, and chart accents |
| Bronze ink | `#846643` | Small bronze text requiring stronger contrast |
| Soft | `#F3EEE6` | Quiet selected and contextual surfaces |

Status colors have explicit labels, rather than relying on color alone. Healthy/approved uses muted olive, low stock/pending review uses ochre, critical stock uses clay red, and data quality/rejected uses neutral warm gray. These are semantic signals, not decorative brand colors. Charts use espresso and bronze, with warm gray for inbound comparison. There are no teal/purple themes, glowing gradients, robot illustrations, or promotional assistant cards.

Calculated contrast ratios against the actual designated backgrounds:

| Foreground / background | Ratio |
|---|---|
| Ink `#25231F` / white | 15.68:1 |
| Muted `#756D63` / white | 5.09:1 |
| Espresso `#5B3E2B` / white | 9.68:1 |
| Bronze ink `#846643` / white | 5.30:1 |
| Healthy text `#526248` / `#F0F3EB` | 5.85:1 |
| Critical text `#995746` / `#F9EEEA` | 4.85:1 |
| Low-stock text `#876933` / `#F9F3E6` | 4.63:1 |
| Neutral status text `#70685D` / `#F3F1EC` | 4.86:1 |

Bronze `#A58763` is 3.36:1 on white and is reserved for decorative/interactive non-text accents rather than ordinary body copy. These calculations verify the listed token pairs; they do not constitute a full WCAG conformance audit of every browser state.

## Typography, spacing, and density

Inter is bundled locally through `@fontsource/inter` in weights 400, 500, 600, and 700, including Vietnamese subsets. The application does not request a font CDN. The root text size is 14 px; operational table text is 11–13 px depending on viewport and density. Primary page titles are 29 px on desktop and 26 px on mobile. Section headings are 14–17 px. Small IDs, annotations, and navigation grouping labels are intentionally secondary and should not carry the only instance of a critical value.

Spacing follows an 8 px grid: 8, 16, 24, 32, and 40 px. Four-pixel optical adjustments are allowed for badges, icon alignment, and compact controls. Standard page padding is 32 px, panel padding 24 px, and compact control height 35–40 px. Panels use 8 px corners; controls use 4 px corners. Shadows are limited to dialogs, search results, and transient feedback. Borders and whitespace establish most hierarchy.

All numeric tables align quantities and currency to the right. Quantities retain the material's unit of measure (`kg`, `piece`, `carton`, `roll`, or legacy `unit`). VND values use a consistent `VND` suffix; detail drawers show full values and compact summaries may show abbreviations. Unlike units are never added into one physical total. Material counts and monetary values can be summed across unit types.

## Layout and responsive behavior

- Desktop uses a 232 px white sidebar, a 72 px top toolbar, and an ivory main canvas. Navigation has eight business pages: Overview, Inventory, Purchase requests, Suppliers, Operational Assistant, Analytics, Activity, and Settings.
- At 1250 px, spacing and table controls tighten while retaining the two inventory views. At 1080 px, analytical layouts simplify and contextual assistant panels move below the conversation.
- Below 900 px, navigation becomes a controlled drawer. Below 680 px, the toolbar uses two rows so both search and the analysis date remain available. Cards stack, forms adapt, and wide tables scroll within their panel rather than forcing page-level horizontal scrolling.
- The inventory table deliberately separates **Stock balances** from **Replenishment**. Fixed column proportions and wrapped material names expose the policy fields without requiring a desktop table wider than the content area. The material drawer contains the complete record.
- Recharts animations are disabled to keep state changes calm and prevent partial chart captures. Reduced-motion preferences also disable remaining transitions and loading animations.

## Page patterns

**Overview** contains five compact KPIs, a unit-specific material-demand chart, a current stock classification, replenishment priorities, recorded stock changes, and procurement activity. Every count and value comes from the API. Empty histories state that no events exist rather than inventing activity or performance improvements.

**Inventory** supports category, supplier, risk, search, and sorting. Material names, SKUs, suppliers, categories, and units remain discoverable. The drawer shows origin, quality notes, reservations, policy inputs, the demand observation window, and the calculation method. Missing metadata displays `Unclassified`, `unit`, or an explicit missing-data label without replacing legacy business values.

**Purchase requests** retains saved costs, quantities, unit/category snapshots, the calculation evidence, and review history. Approve/reject controls require a reviewer and decision reason. Feedback reports server validation and stale-draft errors directly. No screen claims that approval dispatches an external purchase order.

**Suppliers** exposes assigned materials, reference lead time, pending requests, contact information, and actual data completeness. A “fields complete” count refers only to the displayed supplier master fields; it is not an inferred supplier-quality score.

**Operational Assistant** is a read-only review surface. Common questions use business language. English and Vietnamese questions are supported; conversations remain persisted through the existing API. Source references, analysis steps, and execution/model details are available through expandable details, without technical status badges dominating the main interface. There is no robotic identity or oversized assistant hero.

**Analytics** separates unit-specific recorded demand/stock trends from material-count risk distribution and VND replenishment value. Recorded usage is labeled material demand rather than cup sales. Chart filters are distinct from full-database export scope, which is disclosed beside the downloads.

**Activity** supports actor/action search, affected-material filters, dates, full timestamps in Vietnam time (UTC+7), human-readable before/after differences, and complete stored evidence. Approval and exception records use dedicated views. The append-only application boundary is described without claiming protection against a database administrator.

**Settings** prioritizes workspace preferences and validated data imports. Runtime/model configuration is in a collapsed advanced section. Manual operator names are clearly distinguished from authentication.

## Interaction and accessibility

Buttons and links have visible hover/focus treatments; no decorative control is presented as a working action. Dialogs and record drawers use `role="dialog"`, a labeled title, a focus loop, Escape dismissal, and focus restoration. Form controls have labels, native validation where applicable, and explicit error feedback. Loading states and empty states distinguish missing data from request failure. Toasts expose success/error feedback through live status/alert roles.

Inventory calculation tooltips are focusable buttons with `aria-describedby` and `role="tooltip"`. They open on pointer hover or keyboard focus and close with Escape, blur, or pointer exit. Definitions cover reservations, daily demand, inventory position, reorder point, and target stock. Expanded calculation sections provide the same formulas in the material record.

The analysis date controls the historical demand window; replenishment uses current balances. This distinction is stated in the overview, material drawer, assistant context, and assessment exports. Displayed timestamps use Vietnam time, while stored audit evidence remains UTC.

## Optional authorized asset slot

The default identity is neutral ProcureFlow. [`frontend/public/brand/README.md`](../frontend/public/brand/README.md) documents the local asset slot. Both `VITE_BRAND_ASSET_AUTHORIZED=true` and a valid `/brand/<filename>.svg|png|webp` build-time path are required. External URLs, nested paths, query strings, and unapproved default logos are rejected by the component's path check. The flag records an operator assertion; it does not establish permission or transfer rights.

The help panel retains the academic, synthetic-data, and non-affiliation notice. The ordinary product flow uses a discreet synthetic-data footer rather than repeated large prototype disclaimers. Verification screenshots and browser findings belong in the project's verification record; this document describes the implemented design decisions rather than claiming unexecuted validation.
