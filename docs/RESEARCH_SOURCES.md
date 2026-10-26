# Research sources and modeling decisions

Reviewed on **26 October 2026** for an independent academic coffee procurement case study. Public descriptions establish product/material context; they do not disclose or validate internal purchasing records. All suppliers, stock, costs, lead times, demand, and quality-review notes in the separate coffee dataset are illustrative.

## Official company evidence

| Source | Evidence verified | How it informs this project |
|---|---|---|
| [Trung Nguyên product portfolio](https://trungnguyenlegend.com/trung-nguyen/) | The portfolio distinguishes roasted/ground coffee and whole-bean offerings. Its whole-bean section names Culi Robusta, Premium Culi, Arabica Robusta, and Culi Arabica. It describes Vietnam, Brazil, Colombia, Ethiopia, and Jamaica in its sourcing narrative. | Supports coffee-family terminology. Public finished products are not copied into a purported company bill of materials. |
| [Trung Nguyên Legend product portfolio](https://trungnguyenlegend.com/trung-nguyen-legend/) | Lists branded finished products and describes coffee processing and product positioning. | Establishes the difference between a finished product for sale and a procurement input. No confidential recipe or blend ratio is inferred. |
| [Continued innovation and global development, 27 June 2025](https://trungnguyenlegend.com/trung-nguyen-legend-lien-tuc-sang-tao-chinh-phuc-toan-cau/) | Discusses Robusta and Arabica, Buôn Ma Thuột, and origins including Brazil, Colombia, Ethiopia, and Jamaica. | Supports the business case and origin examples. It does not establish any specific supplier, purchase, contract, warehouse, volume, or current price used here. |
| [Published product declarations](https://trungnguyenlegend.com/cong-bo-san-pham/) | The official index includes roasted-bean, ground/instant, and other finished-product declarations. | Provides a public evidence trail for product stages. Individual declaration attachments were not treated as evidence of purchasing specifications or internal formulations. |
| [Brand repositioning, 28 September 2018](https://trungnguyenlegend.com/trung-nguyen-legend-tai-dinh-vi-thuong-hieu/) | The company describes changing its name/identity and moving from red/black to white/black, with monochrome packaging. | Supports restrained monochrome inspiration. Ivory, espresso accents, typography sizes, and application tokens are independent ProcureFlow design decisions. |
| [Official homepage](https://trungnguyenlegend.com/) | Reviewed as the primary brand entry point. Fetch availability varied during research; the official product/article pages above were readable. | No third-party logo download was substituted when the homepage was unavailable. |

These sources are corporate descriptions. Descriptive flavor claims are attributed to the company and are not independent test results. Their geographic narrative must not be interpreted as proof that every listed origin is purchased for every product.

## General coffee quality and handling evidence

| Source | Evidence verified | Application boundary |
|---|---|---|
| [FAO Arabica coffee manual: harvesting and processing](https://www.fao.org/4/ae939e/ae939e08.htm) | Green-bean preparation, grading, clean storage, moisture uptake, mold risk, and damage during transport affect coffee quality. | Supports general receiving-review notes: inspect condition, moisture evidence, cleanliness, packaging, and traceability. Its numerical guidance is not installed as a company acceptance standard. |
| [FDA Macroanalytical Procedures Manual: coffee beans](https://www.fda.gov/food/laboratory-methods/mpm-v-1-beverages-and-beverage-materials) | Describes inspection for insect damage, mold, deterioration, extraneous matter, and other defects in green coffee; notes adaptation for roasted beans. | Supports generic defect-review considerations. This application does not implement a regulatory inspection program or certify compliance. |
| [International Coffee Organization: quality and handling guidance](https://www.icocoffee.org/documents/ed1763r1e.pdf) | Describes drying, avoiding rewetting, and quality checks including cupping, moisture, and defects. | Provides industry context for qualitative receiving notes. The dataset does not claim official lab results, graded lots, or verified certifications. |
| [Lâm Đồng provincial agricultural extension: regional coffee development](https://khuyennong.lamdong.gov.vn/thong-tin-nong-nghiep/trong-trot/2027-n%E1%BB%97-l%E1%BB%B1c-x%C3%A2y-d%E1%BB%B1ng-th%C6%B0%C6%A1ng-hi%E1%BB%87u-c%C3%A0-ph%C3%AA-th%E1%BA%BF-m%E1%BA%A1nh) | Describes Arabica growing in Cầu Đất and parts of Lạc Dương, Lâm Đồng. | Makes the illustrative Lâm Đồng Arabica origin regionally coherent; no named real producer is copied into the supplier dataset. Historic production targets in that article are not presented as current figures. |
| [Embrapa: coffee production in the Brazilian Amazon](https://www.alice.cnptia.embrapa.br/alice/bitstream/doc/1023755/1/LivroCafenaAmazoniaDigital2015.pdf) | Describes Coffea canephora cultivation, including Conilon and Robusta groups, in the Brazilian Amazon. | Supports a general Brazilian canephora/Robusta example origin. It does not establish a company transaction or a specific purchased lot. |

## Procurement scope and assumptions

The modeled operation purchases **green beans for roasting**, selected **roasted beans for a separate blending/packing operation**, and **packaging consumables**. This is a deliberately simplified independent operation, not a reconstruction of Trung Nguyên's factory or purchasing organization.

| Material stage | Appropriate use in the modeled workflow | Treatment |
|---|---|---|
| Green Robusta / Arabica | Unroasted input to roasting | Procurement inputs measured in whole kg. |
| Selected Culi Robusta lots | A selection within Robusta; not a separate coffee species | Synthetic green-bean input; no proprietary selection or recipe asserted. |
| Roasted beans / blending inputs | Can be purchased for a defined blending/packing workflow | Separate category and explicit stage; not mislabeled as green coffee. |
| Ground coffee | A processed product; may be purchased by resellers or service operations | Excluded from the new raw-material dataset unless that different workflow is explicitly modeled. Existing user/starter records remain unchanged. |
| Valve bags, cartons, filters, labels, liners | Packaging/consumable inputs for the specified scenario | Counted in pieces, cartons, or rolls. Dimensions, price, stock, and review notes are illustrative. |
| Branded retail finished products | Resale or finished-goods stock | Not presented as raw coffee procurement. Public product names do not create a bill of materials. |

The existing `sales` schema is retained for compatibility. In the separate coffee scenario, its per-material demand rows represent **synthetic usage/withdrawal signals**. They do not represent actual company sales or finished-cup sales. Kg, pieces, cartons, and rolls must not be summed into a physical total across units; charts group compatible measures or show individual-material demand.

All monetary values use illustrative VND per stated unit. They are not market quotes, supplier offers, estimates of actual company purchasing costs, or verified savings. Costs are not derived from the research sources. Stock, reservations, supplier names/contacts, origin assignments, review periods, packaging choices, and lead times are scenario assumptions. Whole-number quantity handling is retained; fractional weighing and yield/BOM conversions are outside this version.

## Logo and brand assets

The correct company spelling is **Trung Nguyên Legend**. Official pages show and discuss its own identity; the project does not redraw, recolor, or approximate that logo. No explicit redistribution license or authorization covering this application's use of official logo assets was established in the reviewed sources. This is a statement about the reviewed evidence, not a legal determination about every possible use.

Consequently, the default UI uses an original neutral **ProcureFlow** wordmark. No official company logo is bundled. A documented optional local brand-asset slot can be used only after the project owner establishes appropriate permission. Authorized artwork must retain its original proportions and must not imply that this academic application is an official internal system.

An accessible independent-project notice remains in the interface. Black/white research is design inspiration; the warm ivory/charcoal/espresso application system is not presented as an official brand guideline.
