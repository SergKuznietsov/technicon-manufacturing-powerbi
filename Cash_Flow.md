# Cash Flow Measures

Covers pages: Cash Flow Statement, Operating CF Trend, Free Cash Flow & Conversion. Depends on `Shared_Base.md` (`Amount CF`, `Actual CF Amount`, `Budget CF Amount`).

## Architecture note: hardcoded scenario, not relationship-driven

Every CF line-item measure below filters `fact_cashflow[Scenario_ID] = "ACT"` directly as a column filter, *not* via `dim_Scenario` relationship + `USERELATIONSHIP`. See `Shared_Base.md` for the full explanation of why, and `Known_Issues.md` for the follow-up item this creates (Division/Scenario slicers were removed from CF pages and have not been re-tested since the relationship was confirmed active).

## Layer 1 — CF line items (one per GL_Subcategory)

Each of these is a thin `CALCULATE(SUM(...), Scenario_ID = "ACT", GL_Subcategory = "...")` wrapper. Listed together since the pattern is identical across all of them.

```dax
CF NetIncome =
CALCULATE(
    SUM(fact_cashflow[Amount_EUR]),
    fact_cashflow[Scenario_ID] = "ACT",
    dim_gl_account[GL_Subcategory] = "CFO_NetIncome"
)

CF DA =
CALCULATE (
    SUM ( fact_cashflow[Amount_EUR] ),
    fact_cashflow[Scenario_ID] = "ACT",
    dim_gl_account[GL_Subcategory] = "CFO_DA"
)

CF SBC =
CALCULATE (
    SUM ( fact_cashflow[Amount_EUR] ),
    fact_cashflow[Scenario_ID] = "ACT",
    dim_gl_account[GL_Subcategory] = "CFO_SBC"
)

CF Delta AR =
CALCULATE (
    SUM ( fact_cashflow[Amount_EUR] ),
    fact_cashflow[Scenario_ID] = "ACT",
    dim_gl_account[GL_Subcategory] = "CFO_AR"
)

CF Delta Inventory =
CALCULATE (
    SUM ( fact_cashflow[Amount_EUR] ),
    fact_cashflow[Scenario_ID] = "ACT",
    dim_gl_account[GL_Subcategory] = "CFO_Inv"
)

CF Delta AP =
CALCULATE (
    SUM ( fact_cashflow[Amount_EUR] ),
    fact_cashflow[Scenario_ID] = "ACT",
    dim_gl_account[GL_Subcategory] = "CFO_AP"
)

CF Delta Prepaid =
CALCULATE (
    SUM ( fact_cashflow[Amount_EUR] ),
    fact_cashflow[Scenario_ID] = "ACT",
    dim_gl_account[GL_Subcategory] = "CFO_Prepaid"
)

CF Delta Accrued =
CALCULATE (
    SUM ( fact_cashflow[Amount_EUR] ),
    fact_cashflow[Scenario_ID] = "ACT",
    dim_gl_account[GL_Subcategory] = "CFO_Accrued"
)

CF Other Operating =
CALCULATE (
    SUM ( fact_cashflow[Amount_EUR] ),
    fact_cashflow[Scenario_ID] = "ACT",
    dim_gl_account[GL_Subcategory] = "CFO_Other"
)

CF CAPEX =
CALCULATE (
    SUM ( fact_cashflow[Amount_EUR] ),
    dim_gl_account[GL_Subcategory] = "CFI_CAPEX",
    fact_cashflow[Scenario_ID] = "ACT"
)

CF Acquisitions =
CALCULATE (
    SUM ( fact_cashflow[Amount_EUR] ),
    fact_cashflow[Scenario_ID] = "ACT",
    dim_gl_account[GL_Subcategory] = "CFI_Acq"
)

CF Disposals =
CALCULATE (
    SUM ( fact_cashflow[Amount_EUR] ),
    fact_cashflow[Scenario_ID] = "ACT",
    dim_gl_account[GL_Subcategory] = "CFI_Disp"
)

CF Other Investing =
CALCULATE (
    SUM ( fact_cashflow[Amount_EUR] ),
    fact_cashflow[Scenario_ID] = "ACT",
    dim_gl_account[GL_Subcategory] = "CFI_Other"
)

CF Debt Proceeds =
CALCULATE (
    SUM ( fact_cashflow[Amount_EUR] ),
    fact_cashflow[Scenario_ID] = "ACT",
    dim_gl_account[GL_Subcategory] = "CFF_Proceeds"
)

CF Debt Repayment =
CALCULATE (
    SUM ( fact_cashflow[Amount_EUR] ),
    fact_cashflow[Scenario_ID] = "ACT",
    dim_gl_account[GL_Subcategory] = "CFF_Repayment"
)

CF Dividends =
CALCULATE (
    SUM ( fact_cashflow[Amount_EUR] ),
    fact_cashflow[Scenario_ID] = "ACT",
    dim_gl_account[GL_Subcategory] = "CFF_Dividends"
)

CF Buyback =
CALCULATE (
    SUM ( fact_cashflow[Amount_EUR] ),
    fact_cashflow[Scenario_ID] = "ACT",
    dim_gl_account[GL_Subcategory] = "CFF_Buyback"
)

CF Other Financing =
CALCULATE (
    SUM ( fact_cashflow[Amount_EUR] ),
    fact_cashflow[Scenario_ID] = "ACT",
    dim_gl_account[GL_Subcategory] = "CFF_Other"
)
```

## Layer 2 — CF subtotals

```dax
CF Operating =
[CF NetIncome] + [CF DA] + [CF SBC]
    + [CF Delta AR] + [CF Delta Inventory] + [CF Delta AP]
    + [CF Delta Prepaid] + [CF Delta Accrued] + [CF Other Operating]

CF Investing =
[CF CAPEX] + [CF Acquisitions] + [CF Disposals] + [CF Other Investing]

CF Financing =
[CF Debt Proceeds] + [CF Debt Repayment] + [CF Dividends]
    + [CF Buyback] + [CF Other Financing]

CF Net Change = [CF Operating] + [CF Investing] + [CF Financing]

Net Cash Flow = [CF Operating] + [CF Investing] + [CF Financing]
```

`CF Net Change` and `Net Cash Flow` are identical formulas under two names -- a naming duplication rather than a logic error, likely from iterating on the Cash Flow Statement page and the Cash Flow Bridge chart separately without consolidating.

### Operating CF (alternate route via GL_Category, used for time intelligence)
```dax
Operating CF =
CALCULATE (
    SUM ( fact_cashflow[Amount_EUR] ),
    dim_gl_account[CF_Category] = "Operating",
    fact_cashflow[Scenario_ID] = "ACT"
)
```

**Worth noting:** `CF Operating` (above, built by summing the nine CFO_* line items) and `Operating CF` (this measure, built by filtering `CF_Category = "Operating"` directly on the fact table) should produce the same number if the data is internally consistent, but they are two structurally independent calculation paths. `Operating CF` is the one extended with time intelligence below (R12, YoY, annual pins) -- `CF Operating` is the one used in the Cash Flow Statement bridge chart and CF Value SWITCH. If the two ever diverge, that divergence itself would be a useful Layer 0 data-integrity check.

## CF Value (matrix display pattern -- same technique as PL Value)

Uses disconnected table `dim_CF_Structure[CF_Label]` to drive Cash Flow Statement matrix rows, exactly the same `SWITCH`-on-disconnected-table technique used for `PL Value` in `PnL.md`.

### CF Value
**Layer:** 2 (matrix master measure)

```dax
CF Value =
DIVIDE (
    SWITCH (
        SELECTEDVALUE ( dim_CF_Structure[CF_Label] ),
        "Net Income",            [CF NetIncome],
        "(+) D&A",               [CF DA],
        "(+) SBC",               [CF SBC],
        "(+) D AR",              [CF Delta AR],
        "(+) D Inventory",       [CF Delta Inventory],
        "(+) D AP",              [CF Delta AP],
        "(+) D Prepaid",         [CF Delta Prepaid],
        "(+) D Accrued",         [CF Delta Accrued],
        "(+) Other Operating",   [CF Other Operating],
        "Operating Cash Flow",   [CF Operating],
        "(-) CAPEX",             [CF CAPEX],
        "(+) Acquisitions",      [CF Acquisitions],
        "(+) Disposals",         [CF Disposals],
        "(+) Other Investing",   [CF Other Investing],
        "Investing Cash Flow",   [CF Investing],
        "(+) Debt Proceeds",     [CF Debt Proceeds],
        "(-) Debt Repayment",    [CF Debt Repayment],
        "(-) Dividends",         [CF Dividends],
        "(-) Buyback",           [CF Buyback],
        "(+) Other Financing",   [CF Other Financing],
        "Financing Cash Flow",   [CF Financing],
        "Net Change in Cash",    [CF Net Change]
    ),
    1000000,
    BLANK ()
)
```

Divides by 1,000,000 to display in EUR millions directly in the matrix -- the rounding/scaling is baked into the measure rather than handled by visual-level format strings, so the underlying value matches what's displayed exactly.

```dax
CF Value ACT 2023 =
CALCULATE (
    [CF Value],
    dim_calendar[Year] = 2023,
    dim_scenario[Scenario_Name] = "Actual"
)

CF Value ACT 2024 =
CALCULATE (
    [CF Value],
    dim_calendar[Year] = 2024,
    dim_scenario[Scenario_Name] = "Actual"
)
```

Note these two filter on `dim_scenario[Scenario_Name] = "Actual"` (the friendly name column) rather than `dim_Scenario[Scenario_ID] = "ACT"` (the code column) used everywhere else in the model -- a minor inconsistency, functionally fine as long as both columns stay in sync in `dim_Scenario`, but a second source of truth for "what counts as actual" that didn't need to exist.

## Cash Flow Bridge chart (waterfall, separate from the CF Value matrix)

```dax
CF Waterfall Value =
SWITCH (
    SELECTEDVALUE ( dim_CF_Structure[CF_Section] ),
    "Operating CF", [CF Operating],
    "Investing CF",  [CF Investing],
    "Financing CF",  [CF Financing],
    "Net Change",    [CF Net Change]
) / 1000000

CF WF Operating = [CF Operating] / 1000000
CF WF Investing = [CF Investing] / 1000000
CF WF Financing = [CF Financing] / 1000000
CF WF Net Change = [CF Net Change] / 1000000
```

`CF Waterfall Value` is the single SWITCH-based version (drives the bridge chart from `dim_CF_Structure[CF_Section]`); the four `CF WF *` measures are the same four numbers exposed individually, likely used for chart data labels or KPI cards alongside the waterfall rather than the waterfall itself.

### CF Chart Title (dynamic title)
```dax
CF Chart Title =
"Cash Flow Bridge -- " & SELECTEDVALUE(dim_scenario[Scenario_Name])
& " " & SELECTEDVALUE(dim_calendar[Year])
```

### Color helpers
```dax
CF Background Color =
SWITCH(
    SELECTEDVALUE(dim_PL_Structure[PL_Line]),
    "Gross Profit",  "#1F4E79",
    "EBIT",          "#1F4E79",
    "Net Income",    "#0070C0",
    "#FFFFFF"
)

CF Font Color =
SWITCH(
    SELECTEDVALUE(dim_PL_Structure[PL_Line]),
    "Gross Profit",  "#FFFFFF",
    "EBIT",          "#FFFFFF",
    "Net Income",    "#FFFFFF",
    "#171717"
)
```

These two reference `dim_PL_Structure[PL_Line]`, not `dim_CF_Structure` -- they appear to be leftover/reused from the P&L matrix styling pattern rather than purpose-built for the CF page, since the values being matched ("Gross Profit", "EBIT", "Net Income") are P&L line labels, not CF labels. If these are actually wired to a CF visual, double-check they're matching against the correct disconnected table.

### OCF Bar Color
```dax
OCF Bar Color = IF ( [Operating CF] >= 0, "#378ADD", "#D85A30" )
```

## Operating CF Trend (time intelligence)

```dax
Operating CF 2024 = CALCULATE ( [Operating CF], dim_calendar[Year] = 2024 )
Operating CF Annual 2024 = CALCULATE ( [Operating CF], dim_calendar[Year] = 2024 )
```

Another duplicate pair (`Operating CF 2024` and `Operating CF Annual 2024` are identical) -- harmless but redundant; consolidate to one if cleaning up before publishing.

```dax
Operating CF R12 =
CALCULATE (
    [Operating CF],
    DATESINPERIOD (
        dim_calendar[Date],
        LASTDATE ( dim_calendar[Date] ),
        -12,
        MONTH
    )
)

Operating CF YoY % =
DIVIDE (
    [Operating CF] - CALCULATE ( [Operating CF], SAMEPERIODLASTYEAR ( dim_calendar[Date] ) ),
    ABS ( CALCULATE ( [Operating CF], SAMEPERIODLASTYEAR ( dim_calendar[Date] ) ) )
)

OCF Margin % 2024 =
CALCULATE (
    DIVIDE ( [Operating CF], [Net Revenue] ),
    dim_calendar[Year] = 2024
)
```

### CF Operating R13W (rolling 13-week operating cash flow)
```dax
CF Operating R13W =
CALCULATE (
    [CF Operating],
    DATESINPERIOD (
        dim_Calendar[Date],
        MAX ( dim_Calendar[Date] ),
        -91,
        DAY
    )
)
```

-91 days is the DAX implementation of a "rolling 13-week cash forecast" (13 x 7 = 91 days) -- one of the controlling techniques on the project's terminology list, implemented here as a trailing rolling window rather than a forward-looking forecast (since this model has no forecast fact table for cash).

## Free Cash Flow & Conversion

```dax
FCF = CALCULATE ( [Operating CF] + [CF CAPEX] )
FCF 2024 = CALCULATE([FCF], dim_calendar[Year] = 2024)

Free Cash Flow = [CF Operating] + [CAPEX]
// CAPEX stored as negative outflow -> adding gives FCF correctly
```

**Two FCF formulas, two different inputs:** `FCF` is built from `Operating CF` + `CF CAPEX` (the GL_Category-filtered Operating CF). `Free Cash Flow` is built from `CF Operating` + `CAPEX` (the summed-CFO-lines version, and a separate `CAPEX` measure defined under `CF Investing` filtering -- see below). Both rely on CAPEX being stored as a negative number so addition (not subtraction) produces the correct FCF. Functionally these should converge to the same figure given consistent data, but -- like the `CF Operating` / `Operating CF` split above -- they are not the same formula and should not be assumed interchangeable without checking.

```dax
CAPEX =
CALCULATE (
    [CF Investing],
    dim_gl_account[GL_Subcategory] = "CAPEX"
)
```

Note: this `CAPEX` measure filters `[CF Investing]` (the subtotal) by subcategory "CAPEX" -- a slightly unusual pattern since `CF Investing` itself is already a sum of `CF CAPEX` + other investing lines, so filtering it further by subcategory is logically circular unless `dim_gl_account[GL_Subcategory] = "CAPEX"` is what isolates just the CAPEX portion of that sum within the current filter context. Works in practice but is a denser piece of logic than it needs to be; a direct `CF CAPEX` reference would be more transparent.

```dax
FCF Conversion % = DIVIDE ( [Free Cash Flow], [EBITDA], 0 )
CF Cash Conversion = DIVIDE ( [CF Free Cash Flow 2024], [CF NetIncome] )

CF Free Cash Flow 2024 =
CALCULATE (
    [Operating CF] + [CF CAPEX],
    dim_calendar[Year] = 2024
)

FCF Benchmark 10% = CALCULATE([Net Revenue]) * 0.10
```

### Cash Conversion Rate (OCF / Net Income -- the headline ratio from the Key KPI Formulas table)
```dax
Cash Conversion Rate =
DIVIDE(
    [CF NetIncome] + [CF DA] + [CF SBC]
    + [CF Delta AR] + [CF Delta Inventory] + [CF Delta AP]
    + [CF Delta Prepaid] + [CF Delta Accrued] + [CF Other Operating],
    [CF NetIncome]
)

Cash Conversion Rate 2024 =
CALCULATE([Cash Conversion Rate], dim_calendar[Year] = 2024)
```

This inlines the full `CF Operating` formula rather than calling `[CF Operating]` directly -- functionally identical, but means if `CF Operating`'s formula changes, this measure needs to be updated separately to stay in sync. Refactoring to `DIVIDE([CF Operating], [CF NetIncome])` would remove that duplication risk.

### CF FCF Margin % (uses hardcoded historical revenue, not the live Net Revenue measure)
```dax
CF FCF Margin % for Table =
VAR FCF = SELECTEDVALUE(fact_cashflow[Period_Year])
VAR Revenue =
    SWITCH(
        FCF,
        2020, 426700000,
        2021, 467400000,
        2022, 542000000,
        2023, 562500000,
        2024, 645080000,
        2025, 676430000,
        1
    )
RETURN
DIVIDE([FCF], Revenue)

CF FCF Margin % 2024 =
CALCULATE([CF FCF Margin % for Table], dim_calendar[Year] = 2024)
```

**Architectural note:** this measure hardcodes annual revenue figures as a `SWITCH` lookup rather than calling `[Net Revenue]` filtered by year. This exists because the FCF table on the Free Cash Flow & Conversion page is built from `fact_cashflow[Period_Year]` (a calculated column added specifically to work around the integer `Date_Key` time-intelligence limitation -- see `Shared_Base.md`/`Known_Issues.md`), and at the time this measure was built, pulling live Net Revenue into that same row context proved unreliable, so the known correct annual revenue figures were hardcoded directly. This is a pragmatic workaround, not the preferred long-term approach -- if `fact_cashflow`'s relationship to `dim_Calendar` is revisited (see `Known_Issues.md`), this is the measure most likely to be refactored to pull `Net Revenue` live instead.

A near-identical pattern appears in `NI for CF Table`, used for the FCF/Net Income comparison line chart:

```dax
NI for CF Table =
SWITCH(
    SELECTEDVALUE(fact_cashflow[Period_Year]),
    2020, 55730000,
    2021, 52480000,
    2022, 10180000,
    2023, 7170000,
    2024, 63430000,
    2025, 62380000,
    BLANK()
)
```

## Budget CF (for Cash Flow variance against plan)

```dax
Budget CF Operating =
CALCULATE ( [Budget CF Amount], fact_cashflow[CF_Category] = "Operating" )

Budget CF Investing =
CALCULATE ( [Budget CF Amount], fact_cashflow[CF_Category] = "Investing" )

Budget CF Financing =
CALCULATE ( [Budget CF Amount], fact_cashflow[CF_Category] = "Financing" )

Budget Net Cash Flow =
[Budget CF Operating] + [Budget CF Investing] + [Budget CF Financing]
```

See `Budget_vs_Actual.md` for `Variance CF Operating/Investing/Financing`, which compare these against the actual CF subtotals above.
