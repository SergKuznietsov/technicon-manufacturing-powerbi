# Debt & Liquidity Measures

Covers pages: Debt Structure & Maturity Profile, Leverage & Coverage Ratios, Refinancing Risk & Stress Test. Depends on `Balance_Sheet_Support.md` (`Total Equity`, `Cash & Equivalents`) and `PnL.md` (`EBIT`, `Interest Expense`).

## Debt snapshot pattern

Like the balance sheet, `fact_debt` is a stock, not a flow -- the same snapshot logic from `Balance_Sheet_Support.md` reappears here, sometimes as the full `MAXX(FILTER(ALL(...)))` pattern, sometimes as a simpler `MAXX(ALL(...))` since `fact_debt` doesn't carry the same multi-scenario complexity as `fact_balance_sheet`.

### Debt Outstanding / Debt Outstanding (EOM) / Debt Outstanding Ladder
```dax
Debt Outstanding =
VAR SelectedYear = SELECTEDVALUE( dim_Calendar[Year], 2024 )
VAR MaxDateKey =
    CALCULATE(
        MAX( fact_debt[Date_Key] ),
        FILTER( ALL( fact_debt ), fact_debt[Year] = SelectedYear )
    )
RETURN
    CALCULATE(
        SUM( fact_debt[Outstanding_EUR] ),
        FILTER( ALL( fact_debt ), fact_debt[Date_Key] = MaxDateKey )
    )

Debt Outstanding (EOM) =
VAR CurrentYear = SELECTEDVALUE(dim_Calendar[Year], 2024)
VAR LastKey =
    MAXX(
        FILTER(ALL(fact_debt), fact_debt[Year] = CurrentYear),
        fact_debt[Date_Key]
    )
RETURN
CALCULATE(
    SUM(fact_debt[Outstanding_EUR]),
    fact_debt[Date_Key] = LastKey
)

Debt Outstanding Ladder =
VAR LastKey2024 =
    MAXX(FILTER(ALL(fact_debt), fact_debt[Year] = 2024), fact_debt[Date_Key])
RETURN
CALCULATE(
    SUM(fact_debt[Outstanding_EUR]),
    fact_debt[Date_Key] = LastKey2024
)
```

Three measures, three near-identical implementations of "debt balance as of year-end" -- `Debt Outstanding` and `Debt Outstanding (EOM)` are functionally the same (find the max `Date_Key` for the selected year, sum debt as of that key), differing only in whether the year defaults via `SELECTEDVALUE(..., 2024)` fallback or `SELECTEDVALUE` without an explicit default. `Debt Outstanding Ladder` hardcodes 2024 rather than using the slicer at all -- built specifically for the Maturity Ladder chart on the Debt Structure page, which is presented as a fixed 2024 snapshot regardless of the Year slicer (consistent with that page's design as a point-in-time structural view rather than a trended one).

`Total Debt Outstanding` (used for the page's headline "Total Debt Outstanding" card) is a fourth variant, also hardcoded to 2024:
```dax
Total Debt Outstanding =
VAR LastKey =
    CALCULATE(
        MAX(fact_debt[Date_Key]),
        fact_debt[Year] = 2024
    )
RETURN
CALCULATE(
    SUM(fact_debt[Outstanding_EUR]),
    fact_debt[Date_Key] = LastKey
)
```

**Consolidation candidate:** four measures computing the same underlying concept (debt balance at a point in time) with three different levels of year-flexibility is more redundancy than this metric needs. If extending this dashboard, picking one parameterized version and routing the others through it would reduce maintenance surface -- but since the Debt & Liquidity pages are presented as 2024 year-end snapshots rather than a trended view, the hardcoding is a defensible simplification for this portfolio's scope rather than a functional error.

## Debt composition and maturity

```dax
Debt Type % of Total =
DIVIDE (
    [Total Debt Outstanding],
    CALCULATE (
        [Total Debt Outstanding],
        ALL ( fact_debt[Debt_Type] )
    ),
    0
)

Maturity Concentration =
CALCULATE (
    SUM ( fact_debt[Outstanding_EUR] ),
    fact_debt[Maturity_Year] = SELECTEDVALUE ( dim_calendar[Year] )
)

Maturity Ladder =
CALCULATE (
    SUM ( fact_debt[Outstanding_EUR] ),
    LASTDATE ( dim_calendar[Date] )
)

Maturity Ladder Amount =
VAR LastKey = MAXX ( ALL ( fact_debt ), fact_debt[Date_Key] )
RETURN
CALCULATE (
    SUM ( fact_debt[Outstanding_EUR] ),
    fact_debt[Date_Key] = LastKey
)
```

`Maturity Ladder` uses `LASTDATE(dim_calendar[Date])` directly -- flagged with the same caution as the inventory sub-component measures in `Balance_Sheet_Support.md`: this works only if `fact_debt` has a properly functioning date relationship, not an integer `Date_Key` without one. `Maturity Ladder Amount` uses the safer `MAXX(ALL(...))` pattern instead. If the two produce different numbers, trust `Maturity Ladder Amount`.

### Refinancing Wall Year (find the year with the largest maturing balance)
```dax
Refinancing Wall Year =
VAR LastKey = MAXX ( ALL ( fact_debt ), fact_debt[Date_Key] )
VAR MaturityTable =
    CALCULATETABLE (
        SUMMARIZE (
            fact_debt,
            fact_debt[Maturity_Date].[Year],
            "Mat_Sum", SUM ( fact_debt[Outstanding_EUR] )
        ),
        fact_debt[Date_Key] = LastKey
    )
RETURN
    MAXX (
        TOPN ( 1, MaturityTable, [Mat_Sum], DESC ),
        fact_debt[Maturity_Date].[Year]
    )
```

This is the dynamic-TOPN pattern that `Largest Receiver Share %` (in `Cost_Center_Allocation.md`) does *not* use -- worth comparing the two side by side as an example of the more robust approach. `Refinancing Wall Year` builds a virtual summary table grouping outstanding debt by maturity year, then finds the year with the largest summed balance via `TOPN`. This correctly identifies "2029" as the refinancing wall dynamically rather than hardcoding it, so if the debt schedule changes, this measure adapts automatically.

```dax
Is Refinancing Wall =
VAR WallYear = [Refinancing Wall Year]
VAR CurrentYear = SELECTEDVALUE ( fact_debt[Maturity_Date].[Year] )
RETURN
IF ( CurrentYear = WallYear, 1, 0 )

Maturity Bar Color =
VAR WallYear    = [Refinancing Wall Year]
VAR CurrentYear = SELECTEDVALUE ( fact_debt[Maturity_Year] )
RETURN
IF ( CurrentYear = WallYear, "#C00000", "#2171B5" )
```

Both color/flag helper measures call `[Refinancing Wall Year]` rather than hardcoding 2029 -- so the maturity ladder chart's red highlight bar will correctly move if the underlying debt schedule changes in a future data refresh.

## Interest rate and maturity statistics

```dax
Avg Interest Rate =
VAR LastKey = MAXX ( ALL ( fact_debt ), fact_debt[Date_Key] )
RETURN
DIVIDE (
    CALCULATE (
        SUMX (
            fact_debt,
            fact_debt[Outstanding_EUR] * fact_debt[Interest_Rate_Pct]
        ),
        fact_debt[Date_Key] = LastKey
    ),
    CALCULATE (
        SUM ( fact_debt[Outstanding_EUR] ),
        fact_debt[Date_Key] = LastKey
    ),
    0
)

Weighted Avg Interest Rate =
DIVIDE(
    SUMX(
        fact_debt,
        fact_debt[Outstanding_EUR] * fact_debt[Interest_Rate_Pct]
    ),
    SUM( fact_debt[Outstanding_EUR] )
)
```

`Avg Interest Rate` is the snapshot-correct version (weighted average as of the latest `Date_Key` only). `Weighted Avg Interest Rate` computes the same weighted-average formula but across *all* rows in the current filter context with no `Date_Key` restriction -- meaning if `fact_debt` carries multiple historical snapshots per debt instrument, this second measure would double-count or blend across periods rather than reflecting a single point in time. Use `Avg Interest Rate` for any "current weighted rate" KPI; `Weighted Avg Interest Rate` is only safe to use in a context already filtered to a single date (e.g. inside another measure's `CALCULATE` that has already pinned `Date_Key`).

### Avg Maturity Years (manual date-key decomposition)
```dax
Avg Maturity Years =
VAR LastKey  = MAXX ( ALL ( fact_debt ), fact_debt[Date_Key] )
VAR RefYear  = LastKey / 10000
VAR RefMonth = MOD ( LastKey / 100, 100 )
VAR RefDay   = MOD ( LastKey, 100 )
VAR RefDate  = DATE ( RefYear, RefMonth, RefDay )
RETURN
DIVIDE (
    CALCULATE (
        SUMX (
            fact_debt,
            fact_debt[Outstanding_EUR] *
            DIVIDE (
                DATEDIFF ( RefDate, fact_debt[Maturity_Date], DAY ),
                365.25,
                0
            )
        ),
        fact_debt[Date_Key] = LastKey
    ),
    CALCULATE (
        SUM ( fact_debt[Outstanding_EUR] ),
        fact_debt[Date_Key] = LastKey
    ),
    0
)
```

**This is the canonical example of the integer `Date_Key` workaround pattern referenced throughout this documentation.** `Date_Key` (format `YYYYMMDD`, e.g. `20241231`) is an integer, not a date -- so `DATEDIFF` (which needs two actual dates) can't operate on it directly. The fix: manually decompose the integer back into year/month/day components using integer division and `MOD`, then reconstruct a real `DATE()` value (`RefDate`) before calling `DATEDIFF`. The weighted average maturity in years is then `SUMX` over each debt instrument's outstanding balance times its individual time-to-maturity in years, divided by total outstanding -- a standard weighted-average-life calculation.

### Drawn Revolver %
```dax
Drawn Revolver % =
VAR LastKey = MAXX ( ALL ( fact_debt ), fact_debt[Date_Key] )
RETURN
DIVIDE (
    CALCULATE (
        SUM ( fact_debt[Outstanding_EUR] ),
        fact_debt[Debt_Type] = "Revolving",
        fact_debt[Date_Key] = LastKey
    ),
    CALCULATE (
        SUM ( fact_debt[Outstanding_EUR] ),
        fact_debt[Date_Key] = LastKey
    ),
    0
)
```

## Liquidity (Available Liquidity, Undrawn Revolver)

Both measures share an identical pattern for re-deriving the drawn revolver balance, then deriving the undrawn portion by assuming the revolver is drawn at a fixed 35% utilization rate against its committed size.

```dax
Available Liquidity =
VAR CashAmt = [Cash & Equivalents]
VAR RevolverDrawn =
    CALCULATE(
        SUM( fact_debt[Outstanding_EUR] ),
        FILTER( ALL( fact_debt ),
            fact_debt[Debt_Type] = "Revolving"
                && fact_debt[Year] = SELECTEDVALUE( dim_Calendar[Year], 2024 )
                && fact_debt[Date_Key] = CALCULATE(
                    MAX( fact_debt[Date_Key] ),
                    FILTER( ALL( fact_debt ),
                        fact_debt[Debt_Type] = "Revolving"
                            && fact_debt[Year] = SELECTEDVALUE( dim_Calendar[Year], 2024 )
                    )
                )
        )
    )
VAR RevolverCommitted = DIVIDE( RevolverDrawn, 0.35 )
VAR UndrawnRevolver = RevolverCommitted - RevolverDrawn
RETURN
    CashAmt + UndrawnRevolver

Undrawn Revolver =
VAR RevolverDrawn =
    CALCULATE(
        SUM( fact_debt[Outstanding_EUR] ),
        FILTER( ALL( fact_debt ),
            fact_debt[Debt_Type] = "Revolving"
                && fact_debt[Year] = SELECTEDVALUE( dim_Calendar[Year], 2024 )
                && fact_debt[Date_Key] = CALCULATE(
                    MAX( fact_debt[Date_Key] ),
                    FILTER( ALL( fact_debt ),
                        fact_debt[Debt_Type] = "Revolving"
                            && fact_debt[Year] = SELECTEDVALUE( dim_Calendar[Year], 2024 )
                    )
                )
        )
    )
RETURN DIVIDE( RevolverDrawn, 0.35 ) - RevolverDrawn
```

**The 35% utilization assumption is hardcoded** (`DIVIDE(RevolverDrawn, 0.35)` backs into an implied committed facility size by assuming the drawn amount represents exactly 35% of the total commitment). This is a modeling simplification -- in reality the committed revolver size would be a known contractual figure stored in the data, not backed into via an assumed utilization rate. It produces a plausible number for portfolio purposes but should not be mistaken for how a real treasury function would calculate undrawn capacity (where the committed facility size is a known input, not a derived one). Worth being able to explain this assumption explicitly if asked about it.

## Leverage & Coverage Ratios

```dax
Net Debt = [Debt Outstanding] - [Cash & Equivalents]
Net Debt (Leverage) = [Debt Outstanding (EOM)] - [Cash & Equivalents]

Net Debt / EBITDA =
DIVIDE(
    [Net Debt (Leverage)],
    [EBITDA],
    0
)

Interest Coverage Ratio = DIVIDE ([EBIT], [Interest Expense])

DSCR = DIVIDE ( [EBITDA], [Interest Expense], 0 )

Debt to Equity (Leverage) =
DIVIDE(
    [Debt Outstanding (EOM)],
    [Total Equity],
    0
)

Debt to Total Capital =
DIVIDE(
    [Debt Outstanding (EOM)],
    [Debt Outstanding (EOM)] + [Total Equity],
    0
)
```

`Net Debt` and `Net Debt (Leverage)` differ only in which `Debt Outstanding` variant they call -- another instance of the multiple-near-duplicate pattern flagged above. `Net Debt / EBITDA` and the covenant logic below it are built on `Net Debt (Leverage)`, so that's the one to treat as canonical for leverage ratio purposes.

## Covenant compliance flags, headroom, and color-coding

A consistent four-measure pattern repeats for each covenant (Net Debt/EBITDA, Interest Coverage Ratio, Debt-to-Equity): a hardcoded covenant threshold constant, a headroom calculation, a breach flag, and a color helper for conditional formatting.

```dax
ND EBITDA Covenant = 3.5
ND EBITDA Breach Flag = IF([Net Debt / EBITDA] > 3.5, 1, 0)
ND EBITDA Headroom =
VAR Covenant = 3.5
RETURN
    Covenant - [Net Debt / EBITDA]
ND EBITDA Headroom Label = "+" & FORMAT([ND EBITDA Headroom], "0.00") & "x"
ND EBITDA Color = IF([ND EBITDA Breach Flag] = 1, "#C00000", "#107C10")

ICR Covenant = 4.0
ICR Breach Flag = IF([Interest Coverage Ratio] < 4.0, 1, 0)
ICR Headroom =
VAR Covenant = 4.0
RETURN
    [Interest Coverage Ratio] - Covenant
ICR Headroom Label = "+" & FORMAT([ICR Headroom], "0.00") & "x"
ICR Color = IF([ICR Breach Flag] = 1, "#C00000", "#107C10")

DE Covenant = 1.5
DE Breach Flag = IF([Debt to Equity (Leverage)] > 1.5, 1, 0)
DE Headroom =
VAR Covenant = 1.5
RETURN
    Covenant - [Debt to Equity (Leverage)]
DE Headroom Label = "+" & FORMAT([DE Headroom], "0.00") & "x"
DE Color = IF([DE Breach Flag] = 1, "#C00000", "#107C10")

DTC Covenant = 0.55
```

**Note the breach-direction asymmetry, and why it's correct, not a bug:** Net Debt/EBITDA and Debt-to-Equity breach when the ratio goes *above* the threshold (`> 3.5`, `> 1.5` -- too much leverage is the risk), while Interest Coverage Ratio breaches when it goes *below* the threshold (`< 4.0` -- too little coverage is the risk). This mirrors the same "favorable direction depends on what's being measured" logic documented in `CF Heatmap Color` (`Budget_vs_Actual.md`) -- getting the comparison operator direction right per ratio type is what makes the breach flags meaningful.

`Covenant Breach Count` and `Covenant Compliance %` operate at the row level across the full `fact_debt` table (counting how many individual debt instruments are flagged `Is_Covenant_Breach = TRUE()` in the source data) rather than deriving from the three ratio-level breach flags above -- a different granularity (per-instrument vs. per-period-ratio) answering a related but distinct question:

```dax
Covenant Breach Count =
CALCULATE (
    COUNTROWS ( fact_debt ),
    fact_debt[Is_Covenant_Breach] = TRUE ()
)

Covenant Compliance % =
DIVIDE (
    CALCULATE ( COUNTROWS ( fact_debt ),
                fact_debt[Is_Covenant_Breach] = FALSE () ),
    COUNTROWS ( fact_debt ),
    0
)
```

## Stress Test / Sensitivity (What-If scenario page)

### Stress_EBITDA_% Value (the What-If parameter input)
```dax
Stress_EBITDA_% Value = SELECTEDVALUE('Stress_EBITDA_%'[Stress_EBITDA_%], 0)
```

This is the measure auto-generated by Power BI's "What-If parameter" feature -- it reads the value selected on the page's stress-percentage slider, and every Stressed measure below references this single value, so dragging the slider recalculates the entire stress test chain.

```dax
Stressed EBITDA = [EBITDA R12] * ( 1 + [Stress_EBITDA_% Value] )

Stressed Net Debt to EBITDA = DIVIDE( [Net Debt], [Stressed EBITDA] )

Stressed ICR =
DIVIDE(
    [EBIT] * ( 1 + [Stress_EBITDA_% Value] ),
    [Interest Expense]
)
```

**Note:** `Stressed Net Debt to EBITDA` uses `[Net Debt]` (the simpler variant built on `Debt Outstanding`, not `Debt Outstanding (EOM)`) while the non-stressed `Net Debt / EBITDA` ratio elsewhere uses `[Net Debt (Leverage)]`. If these two `Net Debt` variants ever diverge numerically, the stressed and non-stressed leverage ratios on the page would not be perfectly comparable to each other -- worth aligning to the same `Net Debt` variant if revisiting this page.

```dax
Covenant Breach Flag =
SWITCH(
    TRUE(),
    [Stressed Net Debt to EBITDA] > 3.5 || [Stressed ICR] < 4.0, "BREACH",
    [Stressed Net Debt to EBITDA] > 3.0 || [Stressed ICR] < 5.0, "WARNING",
    "OK"
)

Covenant Color =
SWITCH(
    [Covenant Breach Flag],
    "OK",      "#107C10",
    "WARNING", "#E6550D",
    "BREACH",  "#C00000"
)
```

Note this combined `Covenant Breach Flag` uses *tighter* warning thresholds (3.0x / 5.0x) than the actual hard covenant limits (3.5x / 4.0x) -- a deliberate early-warning buffer zone, giving a "WARNING" amber state before the stress scenario actually breaches the contractual covenant level.

### Sensitivity tables (two-dimensional what-if grids)

The Refinancing Risk & Stress Test page shows two sensitivity matrices: Net Debt/EBITDA against EBITDA stress %, and ICR against EBITDA stress % crossed with an interest rate shock. Both use a disconnected dimension table on rows/columns to drive a SWITCH-free recalculation at each grid cell.

```dax
Sensitivity ND EBITDA =
VAR StressPct =
    IF(
        HASONEVALUE( dim_stress_levels[Stress_Level] ),
        VALUES( dim_stress_levels[Stress_Level] ),
        0
    )
VAR BaseEBITDA =
    CALCULATE(
        [EBITDA R12],
        ALL( dim_stress_levels ),
        ALL( dim_rate_shock )
    )
VAR BaseNetDebt =
    CALCULATE(
        [Net Debt],
        ALL( dim_stress_levels ),
        ALL( dim_rate_shock )
    )
VAR StressedEBITDA = BaseEBITDA * ( 1 + StressPct )
RETURN
    DIVIDE( BaseNetDebt, StressedEBITDA )
```

The `ALL( dim_stress_levels )` / `ALL( dim_rate_shock )` inside the `BaseEBITDA` and `BaseNetDebt` VARs is essential here: without stripping those filters, `EBITDA R12` and `Net Debt` would themselves be evaluated inside the current grid cell's stress filter context (since the disconnected tables are on the visual's rows/columns), creating a circular/incorrect calculation. Stripping them first establishes the *unstressed* baseline, then `StressPct` (read from the row/column context, which is *not* stripped) is applied deliberately on top.

### Color helpers for the sensitivity grids
```dax
CF Color ND EBITDA =
VAR Val = SELECTEDVALUE( dim_nd_sensitivity[ND_EBITDA], 0 )
RETURN
    SWITCH(
        TRUE(),
        Val >= 3.5, "#FFC7CE",
        Val >= 3.0, "#FFEB9C",
        "#C6EFCE"
    )

CF Color ICR =
VAR Val = SELECTEDVALUE( dim_icr_sensitivity[bps_0], 0 )
RETURN
    SWITCH(
        TRUE(),
        Val < 4.0, "#FFC7CE",
        Val < 5.0, "#FFEB9C",
        "#C6EFCE"
    )
```

These read from `dim_nd_sensitivity` / `dim_icr_sensitivity` -- separate disconnected tables from `dim_stress_levels`/`dim_rate_shock` used in `Sensitivity ND EBITDA` above, suggesting the sensitivity grid's calculated values and its conditional-formatting color logic were built against two different supporting table structures rather than one shared one. Functionally fine if both resolve correctly at render time, but a second place to update if the sensitivity grid's dimensions are ever restructured.
