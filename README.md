# DAX Documentation — TechniCon Manufacturing GmbH

Power BI controlling portfolio · 262 working measures · Star schema, 5 fact tables / 4 dimension tables.

> Portfolio project by Serhii Kuznietsov. All data is fictional, generated via Python and modeled on 3M (MMM) 10-K FY2024 structure. Not affiliated with any real company.

## Build methodology

Every measure in this model was built using a strict 3-layer sequence. This is not a stylistic choice — it is the methodology used to prevent silent data errors before they reach a visual.

**Layer 0 — Data verification.**
Before writing a single measure, the raw fact table is queried directly in DAX Query View (`EVALUATE`, `COUNTROWS`, `SUMMARIZE`) to confirm row counts, key uniqueness, and date format. Integer `Date_Key` (format `YYYYMMDD`) breaks Power BI's built-in time intelligence functions silently — `LASTDATE()` returns `BLANK()` with no error — so this step exists specifically to catch that class of failure before it propagates into Layer 1.

**Layer 1 — Base measures.**
Atomic, single-purpose measures built directly on fact tables (`Amount PnL`, `Amount CF`, `Amount BS`, `AR Total`, `Debt Outstanding`, etc.). These never branch on scenario or apply business logic — they are the only measures in the model allowed to touch a fact table column directly with `SUM`/`SUMX`. Every higher-layer measure calls one of these rather than re-referencing a column.

**Layer 2 — Visual layer.**
Composed measures that branch (`SWITCH`, `IF`), apply scenario filters (`Actual Amount`, `Budget Amount`), compute ratios (`DIVIDE` with explicit zero-fallback), or feed a specific visual (`SWITCH` on a disconnected dimension table for matrix rows, `CF Value` for the cash flow bridge chart, color-coding helpers). These are the measures wired directly into report visuals.

This separation matters for one practical reason: when a number looks wrong on a dashboard, the layer tells you where to look. If a Layer 2 ratio is off, check the Layer 1 inputs first — Layer 0 already confirmed the data is sound, so the bug is almost always in the Layer 2 composition logic, not the data.

## Domain files

| File | Covers |
|---|---|
| [`Shared_Base.md`](./Shared_Base.md) | Layer 1 amount measures, scenario hardcoding pattern, language/translation helpers |
| [`PnL.md`](./PnL.md) | P&L Overview, P&L Statement, Trends, Profitability Drill, Bridge Chart |
| [`Budget_vs_Actual.md`](./Budget_vs_Actual.md) | Variance Heatmap, Variance Drill, Cost Center Plan vs Actual |
| [`Cash_Flow.md`](./Cash_Flow.md) | Cash Flow Statement, Operating CF Trend, Free Cash Flow & Conversion |
| [`Working_Capital.md`](./Working_Capital.md) | Cash Conversion Cycle, Receivables Aging & Risk |
| [`Cost_Center_Allocation.md`](./Cost_Center_Allocation.md) | Overhead Allocation page |
| [`Debt_Liquidity.md`](./Debt_Liquidity.md) | Debt Structure & Maturity, Leverage & Coverage Ratios, Refinancing Risk & Stress Test |
| [`Balance_Sheet_Support.md`](./Balance_Sheet_Support.md) | Shared BS snapshot logic underlying Working Capital and Debt pages |
| [`Known_Issues.md`](./Known_Issues.md) | Documented architectural constraints (not bugs) — scenario hardcoding, dual sign conventions, visual-level limitations |

## Reading a measure entry

Each measure in the domain files is documented as:

```
### Measure Name
**Layer:** 0 / 1 / 2
**Depends on:** [other measures or tables]
**Used in:** [page/visual]

​```dax
<formula>
​```

Notes on any non-obvious logic (sign conventions, filter context, known limitations).
```

## Data model summary

**Fact tables:** `fact_pnl` · `fact_balance_sheet` · `fact_cashflow` · `fact_debt` · `fact_ar_aging` · `fact_cogs_detail` · `fact_sales` / `fact_sales_detail` · `fact_cc_allocated_amounts` · `fact_cc_overhead_pool`

**Dimension tables:** `dim_Calendar` · `dim_Scenario` · `dim_Division` · `dim_gl_account` · `dim_cost_center` · `dim_product_group` · `dim_customer_segment` · `dim_translations` / `dim_language`

**Disconnected dimension tables (visual-only, not in star schema):** `dim_PL_Structure`, `Bridge_PL`, `'BvA Bridge Categories'`, `dim_CF_Structure`, `dim_GL_Category_Sort`, `dim_stress_levels`, `dim_rate_shock`, `dim_icr_sensitivity`, `dim_nd_sensitivity`, `'Stress_EBITDA_%'` — these exist purely to drive `SWITCH`-based matrix/chart measures (the Layer 2 pattern for putting calculated values on matrix rows, since Power BI matrices cannot show DAX-calculated row headers directly).

## Key formulas reference

| KPI | Formula |
|---|---|
| Gross Margin % | (Revenue − COGS) / Revenue |
| EBITDA Margin % | EBITDA / Revenue |
| Cash Conversion Rate | OCF / Net Income |
| DSO | AR / Revenue × 365 |
| DPO | AP / COGS × 365 |
| DIO | Inventory / COGS × 365 |
| CCC | DSO + DIO − DPO |
| Net Debt / EBITDA | (Debt − Cash) / EBITDA |
| FCF | OCF − CAPEX |
| Interest Coverage Ratio | EBIT / Interest Expense |
