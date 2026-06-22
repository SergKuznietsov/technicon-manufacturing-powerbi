# TechniCon Manufacturing GmbH — Controlling Dashboard

A Power BI financial controlling portfolio project built around a fictional Mittelstand industrial company. 18 dashboard pages covering P&L, Budget vs. Actual, Cash Flow, Working Capital, and Debt & Liquidity analysis — built end-to-end with Python-generated mock data, a star schema model, and a layered DAX architecture.

**Author:** Serhii Kuznietsov — Financial Analyst / Data Analyst · Power BI Developer · Dortmund, NRW, Germany
[LinkedIn](https://linkedin.com/in/serg-kuznietsov) · [LinkedIn post series](#linkedin-post-series)

> Portfolio project. Mock data, fictional company. Not affiliated with 3M or any real company.

---

## What this is

TechniCon Manufacturing GmbH is a fictional Mittelstand company (~€645M revenue, ~2,800 employees, HQ Düsseldorf) built to demonstrate senior financial controlling competency: budget variance analysis, cash flow and working capital management, debt structuring, and covenant/stress-test monitoring — the kind of analysis a controller actually does, not a generic BI showcase.

The dataset covers 2020–2025 with intentional stress scenarios:

| Period | Scenario |
|---|---|
| 2020 | COVID-19 demand shock — revenue decline, margin compression |
| 2022–2023 | Litigation reserve — OCF dip, temporary covenant breach |
| 2024 | Normalization — margin recovery, deleveraging |
| 2025 | Forecast scenario, based on management guidance |

## Dashboard structure (18 pages)

| Section | Pages | Content |
|---|---|---|
| P&L Dashboard | 1–3 | Executive summary · P&L statement · multi-year trends |
| Budget vs. Actual | 4–6 | Profitability drill · variance heatmap · bridge chart |
| Monthly P&L | 7–8 | Variance drill-down · management commentary |
| Cash Flow | 9–11 | Cash flow statement · OCF trend · FCF & conversion |
| Working Capital | 12–15 | Cash conversion cycle · AR aging & risk · plan vs actual by cost center · overhead allocation |
| Debt & KPI | 16–18 | Debt structure & maturity · leverage & coverage ratios · refinancing risk & stress test |

## Key 2024 (ACT) figures

| KPI | Value |
|---|---|
| Net Revenue | €645.08M |
| Gross Margin | 38.19% |
| EBITDA Margin | 20.28% |
| Net Income | €63.43M |
| Net Margin | 9.83% |
| Operating Cash Flow | €121.21M |
| Free Cash Flow | €90.42M |
| Cash Conversion Rate | 1.91x |
| DSO / DPO / DIO | 45.9d / 38.7d / 58.9d |
| Cash Conversion Cycle | 66.0d |
| Total Debt | €254M |
| Net Debt / EBITDA | 1.52x (covenant ceiling 3.5x) |
| Interest Coverage Ratio | 7.93x (covenant floor 4.0x) |

## Data model

Star schema — 5 fact tables, 4 dimension tables:

- **Fact tables:** `fact_pnl` · `fact_balance_sheet` · `fact_cashflow` · `fact_debt` · `fact_working_capital`
- **Dimension tables:** `dim_calendar` · `dim_scenario` · `dim_division` · `dim_gl_account`

Mock data generated in Python (pandas, numpy), with seasonality, noise, and plan-fact variance built in. Cost structure and margin ratios benchmarked against 3M's FY2024 10-K (COGS ~59%, SG&A ~17%, R&D ~4.4%, operating margin ~19.6%).

### DAX architecture

All measures follow a 3-layer build sequence, verified in DAX Query View before any visual is built:

1. **Layer 0** — data verification (row counts, key checks, totals against source)
2. **Layer 1** — base measures (Gross Margin %, EBITDA Margin %, FCF, Net Debt/EBITDA, DSO/DPO/DIO, and similar)
3. **Layer 2** — visual-layer measures (formatting, conditional logic, what-if parameters)

Design notes:
- Balance sheet and debt tables are point-in-time snapshots — `LASTNONBLANK` over the calendar is used, never a plain `SUM`, since summing a stock value across periods produces a meaningless number.
- `fact_cashflow` has no relationship to `dim_scenario`; `Scenario_ID = "ACT"` is hardcoded directly into the CF measures — an architectural constraint of the cash flow build, not a data error.
- The 2022–2023 litigation reserve is modeled as a deliberate anomaly period, to demonstrate handling non-recurring items in financial analysis and covenant monitoring.

## Tools

Power BI Desktop · DAX · Python (pandas, numpy) · SAP FI/CO-aligned data structures (cost centers, profit centers, GL accounts, scenarios)

## Repository contents

- `/dashboard` — full PDF export of all 18 pages
- `/data-generation` — Python script used to generate the mock dataset
- `/dax` — DAX measure documentation by layer

## LinkedIn post series

This project was published as a serialized LinkedIn post series, each post covering one analytical theme:

| Post | Topic | Pages |
|---|---|---|
| 0 | Origin story | — |
| 0.5 | Star schema, behind the scenes | — |
| 1 | P&L overview, statement & trends | 1–3 |
| 2 | Profitability drill | 4 |
| 3 | Variance heatmap & bridge chart | 5–6 |
| 4 | Variance drill & commentary | 7–8 |
| 5 | Cash flow statement & OCF trend | 9–10 |
| 6 | Free cash flow & conversion | 11 |
| 7 | Cash conversion cycle | 12 |
| 8 | Receivables aging & risk | 13 |
| 9 | Plan vs actual & overhead allocation | 14–15 |
| 10 | Debt structure & leverage/coverage | 16–17 |
| 11 | Refinancing risk & stress test | 16–18 |

Follow along: [linkedin.com/in/serg-kuznietsov](https://linkedin.com/in/serg-kuznietsov)

---

*Die Daten sind fiktiv — die Build-Logik dahinter nicht.*
