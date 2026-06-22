# Known Issues & Architectural Constraints

Two different categories live in this file, kept deliberately separate. **Architectural constraints** are intentional design decisions with documented trade-offs -- not bugs, and not something a reviewer should expect fixed. **Open issues** are things that should actually be corrected before this model is considered final. Mixing the two together would undersell the deliberate design choices and bury the real follow-ups.

## Architectural constraints (intentional, not bugs)

### 1. Scenario hardcoding instead of relationship-driven filtering
Every measure touching `fact_pnl`, `fact_balance_sheet`, or `fact_cashflow` filters scenario via a hardcoded `Scenario_ID = "ACT"` / `"BUD"` column filter rather than relying on the `dim_Scenario` relationship plus `USERELATIONSHIP`. This was originally adopted partly because `USERELATIONSHIP` inside `SUMMARIZECOLUMNS` proved unreliable during early build testing -- the `ADDCOLUMNS` + `TREATAS` pattern was the working alternative, but by that point the hardcoded-filter approach was already in place across the model and consistent, so it was kept rather than retrofitted.

**Follow-up still open:** an `INFO.RELATIONSHIPS()` query (2026-06-19) confirmed that `fact_cashflow` *does* have an active relationship to `dim_Calendar` and `dim_Scenario` -- contradicting an earlier belief that no such relationship existed. The Division and Scenario slicers were removed from the Cash Flow pages on the assumption that no relationship existed to support them. This removal has not been re-tested since the relationship was confirmed active. **Action item:** re-add Division/Scenario slicers to CF pages as a test, confirm they filter correctly given the now-confirmed relationship, and decide whether to keep the hardcoded filters as a safety net (current state) or migrate to relationship-driven filtering.

### 2. Integer Date_Key instead of a proper date column
`fact_balance_sheet`, `fact_debt`, and `fact_cashflow` all use an integer `Date_Key` (format `YYYYMMDD`) rather than a native `DATE` type column. This breaks `LASTDATE()` silently (returns `BLANK()`, no error) and breaks `DATEDIFF()` (which requires two real date values). Every measure that needs "as of the latest period" logic against these tables uses one of two workarounds documented throughout the domain files: (a) `MAXX(FILTER(ALL(table), ...), table[Date_Key])` to find the correct integer key manually, or (b) manual decomposition of the integer into year/month/day via division and `MOD`, then `DATE()` reconstruction (see `Avg Maturity Years` in `Debt_Liquidity.md` for the canonical example).

`Period_Year` calculated columns (via Power Query `Number.IntegerDivide([Date_Key], 10000)`) were added to `fact_cashflow`, `fact_balance_sheet`, and `fact_pnl` specifically to enable year-level filtering where the integer format broke standard time intelligence.

**Why this wasn't simply fixed at the source:** changing `Date_Key` to a proper date type would require reworking the Python mock-data generation script and re-validating every Layer 1/2 measure against the new column. Given the project timeline and the fact that the workarounds are well-understood and consistently applied, this was accepted as a documented limitation rather than a blocking issue. Worth flagging proactively in an interview context as evidence of pragmatic trade-off judgment, not a gap in understanding of why integer date keys are problematic.

### 3. Bridge Chart years hardcoded (2023/2024), does not respond to Year slicer
Both `Bridge Value` (P&L bridge) and the equivalent BvA bridge measure compute a fixed prior-year-to-current-year comparison with the years baked into `VAR` declarations rather than reading from the active Year slicer. Documented on the Methodology page as an accepted limitation: the bridge is conceptually "this year vs. last year," not a slicer-responsive view, so this is a scope decision rather than an oversight.

### 4. Bridge chart X-axis sort order
The DATANOMY Simple Waterfall custom visual used for the Bridge Chart does not reliably respect "Sort by Column" configuration for its X-axis ordering. Confirmed as a limitation of the custom visual itself (not the underlying DAX), and documented as an accepted workaround on the Methodology page rather than something fixable from the measure side.

### 5. Alt text does not trigger on hover in Power BI Desktop
Confirmed via live testing -- not a DAX issue, but documented here because it directly shaped the tooltip strategy decision below.

### 6. Tooltips deferred to backlog (all pages)
Tooltip work across the entire dashboard was suspended for four compounding reasons: tooltips are invisible in PDF exports (the primary publication channel for this portfolio's LinkedIn series); Report Page tooltips would require a dedicated page per KPI, multiplying page count significantly; per-row table tooltips on the Cash Flow Statement would require a `SWITCH`-based DAX measure per tooltip target; and Alt text (the fallback approach) does not trigger on hover in Power BI Desktop at all (see #5). Given PDF is the primary export format, the cost of building tooltip infrastructure that the primary distribution channel can't even display was judged not worth it. Revisit only if the dashboard's primary consumption shifts away from static PDF export.

### 7. CF pages do not support Division filter
`fact_cashflow` carries no division-level split in the source data -- Cash Flow is modeled at the company-consolidated level only. This is a data scope decision (consistent with how many mid-size companies don't produce divisional cash flow statements, since cash pooling typically happens centrally), not a missing relationship.

### 8. 35% revolver utilization assumption (Available Liquidity / Undrawn Revolver)
Both measures back into an implied committed revolver facility size by assuming the drawn amount represents exactly 35% utilization, rather than referencing a known contractual commitment figure. A real treasury function would have the committed facility size as a known input. Documented in `Debt_Liquidity.md` -- a reasonable simplification for portfolio purposes, but worth being able to name as an assumption rather than a fact if asked.

### 9. Overhead allocation uses direct method, not step-down or reciprocal
The Overhead Allocation page allocates indirect cost centers straight to Production without modeling allocations *between* indirect cost centers first (e.g., IT supporting Admin before either allocates to Production). This understates the full cost of indirect services but is a standard, defensible simplification for a portfolio-scope dashboard. Documented in `Cost_Center_Allocation.md`.

## Open issues (should be corrected)

### A. SGA % of Revenue likely evaluates to blank or zero
`Total SGA` filters `dim_gl_account[GL_Subcategory] IN {"Sales", "G&A", "Marketing"}`, but every other SG&A-related measure in the model (`SG&A`, `Budget Total SGA`) uses the actual subcategory values present in the data: `"SGA_Sales"`, `"SGA_Admin"`, `"SGA_Salaries"`. `Total SGA` is almost certainly returning blank/zero against real data, which means `SGA % of Revenue` (which divides by it) is unreliable. **Fix:** update `Total SGA`'s filter to match the correct subcategory values, or retire it in favor of referencing `SG&A` directly.

### B. Largest Receiver Share % hardcodes "CC01" instead of determining it dynamically
Currently correct for the present dataset (Production -- Industrial is genuinely the largest receiver), but will silently report the wrong percentage if the allocation data changes and a different cost center becomes the largest receiver. **Fix:** refactor using the same `TOPN`-against-a-virtual-summary-table pattern already used correctly in `Refinancing Wall Year` (`Debt_Liquidity.md`).

### C. Two unreconciled FCF calculation paths
`FCF` (built from `Operating CF` + `CF CAPEX`) and `Free Cash Flow` (built from `CF Operating` + `CAPEX`) use structurally different underlying measures that should converge but are not guaranteed to. Similarly, `CF Operating` (summed from nine CFO_* line items) and `Operating CF` (filtered directly by `GL_Category = "Operating"`) are two independent calculation paths for the same concept. **Fix:** pick one canonical path per concept, verify the two converge on the current data, and have all dependent measures route through the single canonical version.

### D. Three independent implementations of "Raw Materials / Finished Goods inventory"
`Inventory Raw Materials` / `Inventory Finished Goods` (in `Balance_Sheet_Support.md`, filtered by `GL_Subcategory` codes, using `LASTDATE()`), and the separate `DIO Raw Materials` / `DIO Finished Goods` measures (filtered by `GL_Account_Name` text match, averaged over `Year_Month`) compute conceptually the same figures via different paths. **Fix:** confirm which version each page actually references, retire the unused path, and consolidate to one calculation per inventory category.

### E. Weighted Avg Interest Rate is not snapshot-safe
Unlike `Avg Interest Rate` (which correctly restricts to the latest `Date_Key`), `Weighted Avg Interest Rate` computes its weighted average across whatever rows are in the current filter context with no date restriction -- if `fact_debt` contains multiple historical snapshots per instrument, this measure will blend across periods incorrectly. **Fix:** add the same `MAXX(ALL(...))` snapshot restriction used in `Avg Interest Rate`, or retire this measure in favor of the snapshot-safe version.

### F. Inconsistent date-relationship reliance across BS/Debt measures
Several measures (`Inventory Raw Materials`, `Inventory WIP`, `Inventory Finished Goods`, `Maturity Ladder`) use `LASTDATE(dim_calendar[Date])` directly against fact tables known elsewhere in the model to use integer `Date_Key` without a guaranteed working date relationship. Given constraint #2 above, these specific measures should be spot-checked in DAX Query View to confirm they're returning non-blank values before being trusted in a published dashboard -- if they are returning blanks or incorrect values, migrate them to the `MAXX(FILTER(ALL(...)))` pattern used correctly elsewhere.

### G. Stressed Net Debt to EBITDA and Net Debt / EBITDA use different Net Debt variants
The non-stressed ratio uses `Net Debt (Leverage)` (built on `Debt Outstanding (EOM)`); the stressed version uses the simpler `Net Debt` (built on `Debt Outstanding`). If the two underlying `Debt Outstanding` variants ever diverge, the stress test page's baseline and stressed figures would not be perfectly comparable. **Fix:** align both to the same `Net Debt` variant.

## Items excluded from this documentation entirely (not architectural, not worth fixing -- removed)

For completeness/transparency: the following measures existed in the raw `INFO.MEASURES()` export but were excluded from the domain files because they are dead code, broken references, or accidental artifacts rather than real design decisions worth documenting:

- `Revenue % of Total` -- references `ALL(dim_Region)` and `ALL(dim_customer_segment)`, dimension tables with no other measures referencing them anywhere in the model; likely a leftover from an earlier model iteration.
- `ROI LY` -- references `[ROI]`, a measure that does not exist anywhere in the model. Broken reference.
- `Debt-to-Equity` (hyphenated name) -- a legacy duplicate of `Debt to Equity (Leverage)`, built on `Total Liabilities` instead of `Debt Outstanding (EOM)`, producing a different (and less precise, since Total Liabilities includes non-debt liabilities) leverage figure under a near-identical name. Superseded by `Debt to Equity (Leverage)`.
- `Tax`, `Measure` -- empty placeholder measures with no formula, likely renamed-and-abandoned fields.
- `VAR Cat` -- a variable accidentally saved as a standalone measure (likely copy-paste artifact from editing another measure's code), not a real calculation.
