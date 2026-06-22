# P&L Measures

Covers pages: P&L Overview, P&L Statement, Trends, Profitability Drill, Bridge Chart. Depends on `Shared_Base.md` (`Actual Amount`, `Budget Amount`).

## Core P&L line items (Layer 2)

Each line item filters `Actual Amount` by `dim_gl_account[GL_Category]` or `[GL_Subcategory]`. Budget equivalents follow the identical filter pattern against `Budget Amount` — documented together below since the pattern is mechanical.

### Net Revenue / Budget Net Revenue
```dax
Net Revenue =
CALCULATE ( [Actual Amount], dim_gl_account[GL_Category] = "Revenue" )

Budget Net Revenue =
CALCULATE ( [Budget Amount], dim_gl_account[GL_Category] = "Revenue" )
```

### COGS / Budget COGS
**Sign convention:** `Actual Amount` stores COGS as a negative expense (consistent with how it's posted in `fact_pnl`). `COGS` flips the sign so it displays as a positive expense figure on the P&L statement table.

```dax
COGS =
CALCULATE (
    [Actual Amount] * -1,
    dim_gl_account[GL_Category] = "COGS"
)

Budget COGS =
CALCULATE ( [Budget Amount], dim_gl_account[GL_Category] = "COGS" )
```

Note the asymmetry: `COGS` flips sign, `Budget COGS` does not. This is intentional — `Budget COGS` feeds `Budget Gross Profit = Budget Net Revenue + Budget COGS`, which only works arithmetically if `Budget COGS` stays negative. `COGS` (the actual) is used standalone in the P&L Statement table where a positive display value is wanted. Mixing these two up is the most likely source of a sign error if this measure is ever modified.

### SG&A / Budget SG&A
```dax
SG&A =
CALCULATE (
    [Actual Amount],
    dim_gl_account[GL_Subcategory] IN { "SGA_Admin", "SGA_Sales", "SGA_Salaries" }
)

Budget SG&A =
CALCULATE ( [Budget Amount] * -1,
    dim_gl_account[GL_Category] = "SG&A" )
```

### R&D / Budget R&D
```dax
R&D =
CALCULATE ( [Actual Amount], dim_gl_account[GL_Subcategory] = "R&D" )

Budget R&D =
CALCULATE ( [Budget Amount] * -1,
    dim_gl_account[GL_Category] = "R&D" )
```

### D&A / Budget D&A
```dax
D&A =
CALCULATE ( [Actual Amount], dim_gl_account[GL_Subcategory] = "D&A" )

Budget D&A =
CALCULATE ( [Budget Amount] * -1,
    dim_gl_account[GL_Category] = "D&A" )
```

### Interest Expense
```dax
Interest Expense =
CALCULATE (
    [Actual Amount],
    dim_gl_account[GL_Subcategory] = "Interest_Exp"
) * -1
```

### Income Tax / Budget Income Tax
```dax
Income Tax =
CALCULATE ( [Actual Amount], dim_gl_account[GL_Category] = "Tax" )

Budget Income Tax =
CALCULATE ( [Budget Amount] * -1,
    dim_gl_account[GL_Category] = "Tax" )
```

### Total Non-Operating / Budget Total Non-Operating
```dax
Total Non-Operating =
CALCULATE ( [Actual Amount], dim_gl_account[GL_Category] = "Non-Operating" )
// Interest income/expense, FX gains/losses, other

Budget Total Non-Operating =
CALCULATE ( [Budget Amount], dim_gl_account[GL_Category] = "Non-Operating" )
```

### Total OpEx / Budget Total OpEx
```dax
Total OpEx =
CALCULATE ( [Actual Amount], dim_gl_account[GL_Category] = "OpEx" )

Budget Total OpEx =
CALCULATE ( [Budget Amount], dim_gl_account[GL_Category] = "OpEx" )
```

## Subtotals and margins (Layer 2)

### Gross Profit / Budget Gross Profit
```dax
Gross Profit = [Net Revenue] - [COGS]

Budget Gross Profit = [Budget Net Revenue] + [Budget COGS]
```

### EBIT / Budget EBIT
```dax
EBIT = [Gross Profit] + [Total OpEx]
// OpEx is negative -> addition reduces GP correctly

Budget EBIT = [Budget Gross Profit] + [Budget Total OpEx]
```

### EBITDA / Budget EBITDA
```dax
EBITDA = [EBIT] - [D&A]
// D&A is stored as negative; subtracting it adds back the absolute value
// Equivalent: EBITDA = EBIT + ABS(D&A)

Budget EBITDA = [Budget EBIT] - [Budget D&A]
```

### Pre-Tax Income / Budget Pre-Tax Income
```dax
Pre-Tax Income = [EBIT] + [Total Non-Operating]

Budget Pre-Tax Income = [Budget EBIT] + [Budget Total Non-Operating]
```

### Net Income / Budget Net Income
```dax
Net Income = [Pre-Tax Income] + [Income Tax]
// Tax is stored as negative

Budget Net Income = [Budget Pre-Tax Income] + [Budget Income Tax]
```

### Margin measures
```dax
Gross Margin % = DIVIDE ( [Gross Profit], [Net Revenue], 0 )
EBIT Margin % = DIVIDE ( [EBIT], [Net Revenue], 0 )
EBITDA Margin % = DIVIDE ( [EBITDA], [Net Revenue], 0 )
Net Margin % = DIVIDE ( [Net Income], [Net Revenue], 0 )

Budget Gross Margin % = DIVIDE ( [Budget Gross Profit], [Budget Net Revenue], 0 )
Budget EBITDA Margin % = DIVIDE ( [Budget EBITDA], [Budget Net Revenue], 0 )
Budget Net Margin % = DIVIDE ( [Budget Net Income], [Budget Net Revenue], 0 )
```

### Cost-as-percent-of-revenue measures
```dax
COGS % of Revenue = DIVIDE ( -[COGS], [Net Revenue], 0 )
OpEx % of Revenue = DIVIDE ( -[Total OpEx], [Net Revenue], 0 )
R&D % of Revenue = DIVIDE ( -[R&D], [Net Revenue], 0 )
SGA % of Revenue = DIVIDE ( -[Total SGA], [Net Revenue], 0 )
```

> **Known issue:** `SGA % of Revenue` depends on `Total SGA`, which filters `dim_gl_account[GL_Subcategory] IN {"Sales", "G&A", "Marketing"}`. The actual subcategory values used elsewhere in the model are `"SGA_Sales"`, `"SGA_Admin"`, `"SGA_Salaries"` (see `SG&A` above). This mismatch means `Total SGA` -- and therefore this ratio -- most likely evaluates to blank/zero rather than the intended SG&A percentage. Flagged for a fix; use `SG&A` (which uses the correct subcategory values) as the source of truth for SG&A figures until corrected.

### Benchmark constants
```dax
Gross Margin Benchmark = 0.41
EBITDA Margin Benchmark = 0.24
Net Margin Benchmark Mittelstand = 0.10
```

Hardcoded Mittelstand industrial averages used as reference lines on the Trends page charts.

## Time intelligence (Layer 2)

These build on `Net Revenue` / `EBITDA` / `Net Income` / `Gross Margin %` / `Net Margin %` / `ROE` using standard DAX time intelligence functions. All assume a continuous `dim_Calendar[Date]` marked as a date table — this works without the integer-`Date_Key` workaround because `fact_pnl` has a proper date relationship (unlike `fact_cashflow`, see `Shared_Base.md`).

```dax
Net Revenue LY = CALCULATE ( [Net Revenue], DATEADD ( dim_Calendar[Date], -1, YEAR ) )
Net Revenue PY = CALCULATE ( [Net Revenue], SAMEPERIODLASTYEAR ( dim_Calendar[Date] ) )
Net Revenue MTD = TOTALMTD ( [Net Revenue], dim_Calendar[Date] )
Net Revenue QTD = TOTALQTD ( [Net Revenue], dim_Calendar[Date] )
Net Revenue YTD = TOTALYTD ( [Net Revenue], dim_Calendar[Date] )
Net Revenue R12 =
CALCULATE (
    [Net Revenue],
    DATESINPERIOD ( dim_Calendar[Date], MAX ( dim_Calendar[Date] ), -12, MONTH )
)

Net Income LY = CALCULATE ( [Net Income], DATEADD ( dim_Calendar[Date], -1, YEAR ) )
Net Income PY = CALCULATE ( [Net Income], SAMEPERIODLASTYEAR ( dim_Calendar[Date] ) )
Net Income YTD = TOTALYTD ( [Net Income], dim_Calendar[Date] )

EBITDA PY = CALCULATE ( [EBITDA], SAMEPERIODLASTYEAR ( dim_Calendar[Date] ) )
EBITDA YTD = TOTALYTD ( [EBITDA], dim_Calendar[Date] )
EBITDA R12 =
CALCULATE (
    [EBITDA],
    DATESINPERIOD ( dim_Calendar[Date], LASTDATE ( dim_Calendar[Date] ), -12, MONTH )
)

Gross Margin % LY = CALCULATE ( [Gross Margin %], DATEADD ( dim_Calendar[Date], -1, YEAR ) )
EBITDA Margin % LY = CALCULATE ( [EBITDA Margin %], DATEADD ( dim_Calendar[Date], -1, YEAR ) )
Net Margin % LY = CALCULATE ( [Net Margin %], DATEADD ( dim_Calendar[Date], -1, YEAR ) )
ROE LY = CALCULATE ( [ROE], DATEADD ( dim_Calendar[Date], -1, YEAR ) )

Budget Net Revenue YTD = TOTALYTD ( [Budget Net Revenue], dim_Calendar[Date] )
```

### YoY helper family (used on Trends page)
```dax
YoY (EUR M) = [Current Year] - [Prior Year]
YoY % = DIVIDE ( [YoY (EUR M)], ABS ( [Prior Year] ), BLANK() )

YoY Revenue = [Net Revenue] - [Net Revenue PY]
YoY Revenue % = DIVIDE ( [YoY Revenue], [Net Revenue PY], 0 )

YoY EBITDA = [EBITDA] - [EBITDA PY]
YoY EBITDA % = DIVIDE ( [YoY EBITDA], [EBITDA PY], 0 )
```

```dax
Current Year =
CALCULATE(
    [PL Value],
    FILTER(
        ALL(dim_Calendar),
        dim_Calendar[Year] = MAX(dim_Calendar[Year])
    )
)

Prior Year =
CALCULATE(
    [PL Value],
    FILTER(
        ALL(dim_Calendar),
        dim_Calendar[Year] = SELECTEDVALUE(dim_Calendar[Year]) - 1
    )
)
```

`Current Year` and `Prior Year` both wrap `PL Value` (the `dim_PL_Structure`-driven matrix measure -- see below) rather than a single fixed line item, so the same YoY logic works across every row of the P&L Statement matrix without a separate measure per line.

### CF YoY Color (visual helper, but logically belongs with YoY family)
```dax
CF YoY Color =
VAR _yoy = DIVIDE([YoY %], ABS([Prior Year]), BLANK())
RETURN
    IF(
        _yoy > 0, "#00B050",
        IF(_yoy < 0, "#C00000", "#767676")
    )
```

## Matrix display pattern: dim_PL_Structure

**The problem this solves:** Power BI matrix visual rows cannot display DAX-calculated values directly as row headers -- only column values from a real or disconnected table. The P&L Statement page needs a matrix with rows like "Net Revenue", "(-) COGS", "Gross Profit", etc., each showing a different calculation.

**The fix:** a disconnected table `dim_PL_Structure[PL_Line]` holds the row labels as plain text values. A single master measure `PL Value` uses `SWITCH` on `SELECTEDVALUE(dim_PL_Structure[PL_Line])` to return the correct calculation per row.

### PL Value
**Layer:** 2 (matrix master measure)
**Depends on:** `dim_PL_Structure`, every core P&L measure above

```dax
PL Value =
SWITCH(
    SELECTEDVALUE(dim_PL_Structure[PL_Line]),
    "Net Revenue",          [Net Revenue],
    "(-) COGS",              [COGS] * -1,
    "Gross Profit",          [Gross Profit],
    "(-) SG&A",              [SG&A],
    "(-) R&D",                [R&D],
    "(-) D&A",                [D&A],
    "EBIT",                   [EBIT],
    "(-) Interest Expense",  [Interest Expense] * -1,
    "(-) Tax",                [Income Tax],
    "Net Income",             [Net Income],
    BLANK()
)
```

### 2023 / 2024 (year-pinned PL Value)
```dax
2023 = CALCULATE([PL Value], dim_Calendar[Year] = 2023)
2024 = CALCULATE([PL Value], dim_Calendar[Year] = 2024)
```

### % of Revenue (matrix row, vertical analysis)
```dax
% of Revenue =
VAR _rev =
    CALCULATE(
        [Current Year],
        ALL(dim_PL_Structure),
        dim_PL_Structure[PL_Line] = "Net Revenue"
    )
RETURN
    DIVIDE(ABS([Current Year]), ABS(_rev), BLANK())
```

`ALL(dim_PL_Structure)` strips the current row's filter so `_rev` always resolves to the Net Revenue row regardless of which row this measure is currently evaluating on -- otherwise every row would divide by itself.

## Bridge Chart (NI 2023 to NI 2024 waterfall)

Uses a second disconnected table, `Bridge_PL[Step]`, with one row per bridge component.

### Bridge Value
**Layer:** 2 (matrix/chart master measure)
**Depends on:** `Bridge_PL`, `Net Income`, `Net Revenue`, `COGS`, `SG&A`, `D&A`, `Interest Expense`, `Income Tax`

```dax
Bridge Value =
VAR Y_Curr = 2024
VAR Y_Prev = 2023
RETURN
SWITCH (
    SELECTEDVALUE ( Bridge_PL[Step] ),

    "NI 2023",
        CALCULATE ( [Net Income],
            FILTER ( ALL ( dim_Calendar ), dim_Calendar[Year] = Y_Prev ) ),

    "Revenue D",
        CALCULATE ( [Net Revenue], FILTER ( ALL ( dim_Calendar ), dim_Calendar[Year] = Y_Curr ) )
      - CALCULATE ( [Net Revenue], FILTER ( ALL ( dim_Calendar ), dim_Calendar[Year] = Y_Prev ) ),

    "COGS D",
        CALCULATE ( [COGS], FILTER ( ALL ( dim_Calendar ), dim_Calendar[Year] = Y_Curr ) )
      - CALCULATE ( [COGS], FILTER ( ALL ( dim_Calendar ), dim_Calendar[Year] = Y_Prev ) ),

    "SG&A D",
        CALCULATE ( [SG&A], FILTER ( ALL ( dim_Calendar ), dim_Calendar[Year] = Y_Curr ) )
      - CALCULATE ( [SG&A], FILTER ( ALL ( dim_Calendar ), dim_Calendar[Year] = Y_Prev ) ),

    "D&A D",
        CALCULATE ( [D&A], FILTER ( ALL ( dim_Calendar ), dim_Calendar[Year] = Y_Curr ) )
      - CALCULATE ( [D&A], FILTER ( ALL ( dim_Calendar ), dim_Calendar[Year] = Y_Prev ) ),

    "Interest D",
        CALCULATE ( [Interest Expense], FILTER ( ALL ( dim_Calendar ), dim_Calendar[Year] = Y_Curr ) )
      - CALCULATE ( [Interest Expense], FILTER ( ALL ( dim_Calendar ), dim_Calendar[Year] = Y_Prev ) ),

    "Tax D",
        CALCULATE ( [Income Tax], FILTER ( ALL ( dim_Calendar ), dim_Calendar[Year] = Y_Curr ) )
      - CALCULATE ( [Income Tax], FILTER ( ALL ( dim_Calendar ), dim_Calendar[Year] = Y_Prev ) ),

    "NI 2024",
        CALCULATE ( [Net Income], FILTER ( ALL ( dim_Calendar ), dim_Calendar[Year] = Y_Curr ) ),

    BLANK()
)
```

**Known limitation:** the years 2023/2024 are hardcoded inside `VAR Y_Curr` / `VAR Y_Prev` rather than driven by the Year slicer. The Bridge Chart page does not respond to the Year slicer as a result -- confirmed and documented on the Methodology page as an accepted limitation rather than a bug, since the bridge is conceptually a fixed "current vs. prior year" comparison by design.

**Known limitation (visual):** the Bridge Chart's X-axis sort order does not reliably respect "Sort by Column" in the DATANOMY Simple Waterfall custom visual -- documented separately in `Known_Issues.md`.

## Profitability Drill

### Cost Per Subcategory / Abs Cost / Pct of Total Cost
```dax
Cost Per Subcategory =
ABS(
    CALCULATE(
        [Actual Amount],
        dim_gl_account[GL_Category] = "COGS"
            || dim_gl_account[GL_Category] = "OpEx"
    )
)

Abs Cost = ABS([Cost Per Subcategory])

Pct of Total Cost =
DIVIDE(
    [Abs Cost],
    CALCULATE(
        [Abs Cost],
        ALL(dim_gl_account)
    )
)
```

### Key Insight Text (dynamic narrative)
```dax
Key Insight Text =
VAR TopCat =
    TOPN(1,
        SUMMARIZE(dim_gl_account, dim_gl_account[GL_Subcategory], "Amt", [Abs Cost]),
        [Amt], DESC
    )
VAR TopName = MAXX(TopCat, dim_gl_account[GL_Subcategory])
VAR TopPct = MAXX(TopCat, [Amt]) / CALCULATE([Abs Cost], ALL(dim_gl_account))
RETURN
"Top cost driver: " & TopName & " (" & FORMAT(TopPct, "0.0%") & " of total cost base)"
```

Generates the "Materials dominates cost base at 41%..." style callout text seen on the Profitability Drill page dynamically rather than as a static text box -- it recalculates if filters (Year, Division) change.

### Customer / Material / Sales decomposition measures
```dax
Customer Revenue =
SUMX (
    VALUES ( fact_sales_detail[Customer_ID] ),
    CALCULATE ( SUM ( fact_sales_detail[Net_Revenue_EUR] ) )
)

Customer Rank =
RANKX (
    ALL ( fact_sales_detail[Customer_ID] ),
    [Customer Revenue],
    , DESC,
    DENSE
)

Total Revenue = SUM ( fact_sales[Revenue_EUR] )
Total Quantity = SUM ( fact_sales[Quantity_Sold] )
Total Quantity Used = SUM ( fact_cogs_detail[Quantity_Used] )

Average Selling Price = DIVIDE ( [Total Revenue], [Total Quantity], 0 )

Total Revenue PY =
CALCULATE ( [Total Revenue], SAMEPERIODLASTYEAR ( dim_Calendar[Date] ) )

Revenue Growth = [Total Revenue] - [Total Revenue PY]
Revenue Growth % = DIVIDE ( [Revenue Growth], [Total Revenue PY], 0 )

Revenue Mix = [Net Revenue]
```

### Price / Volume effect decomposition
A classic controlling technique -- splitting a revenue change into the portion caused by price changes vs. the portion caused by volume changes, holding the other constant.

```dax
Price Effect =
SUMX (
    VALUES ( dim_product_group[Product_Group_ID] ),
    ( [Average Selling Price] -
      CALCULATE ( [Average Selling Price], SAMEPERIODLASTYEAR ( dim_Calendar[Date] ) ) )
    * [Total Quantity]
)

Volume Effect =
SUMX (
    VALUES ( dim_product_group[Product_Group_ID] ),
    ( [Total Quantity] -
      CALCULATE ( [Total Quantity], SAMEPERIODLASTYEAR ( dim_Calendar[Date] ) ) )
    * CALCULATE ( [Average Selling Price], SAMEPERIODLASTYEAR ( dim_Calendar[Date] ) )
)
```

Both use `SUMX` over `VALUES(dim_product_group[Product_Group_ID])` so the decomposition is computed per product group and then summed -- necessary because price x volume effects don't decompose linearly across a mixed product portfolio if computed at the aggregate level.

### Cost component drill-downs
```dax
Direct Labor Cost =
CALCULATE ( [Actual COGS Detail], fact_cogs_detail[Cost_Component] = "Direct Labor" )

Raw Materials Cost =
CALCULATE ( [Actual COGS Detail], fact_cogs_detail[Cost_Component] = "Raw Materials" )

Manufacturing Overhead =
CALCULATE ( [Actual COGS Detail], fact_cogs_detail[Cost_Component] = "Overhead" )

Avg Unit Cost = DIVIDE ( [Raw Materials Cost], [Total Quantity Used], 0 )

Material Cost by Material =
CALCULATE (
    SUM ( fact_cogs_detail[Amount_EUR] ),
    fact_cogs_detail[Cost_Component] = "Raw Materials"
)

Material Price Index Avg = AVERAGE ( fact_cogs_detail[Material_Price_Index] )
```

### Material Price Variance (standard costing variance)
```dax
Material Price Variance =
SUMX (
    VALUES ( fact_cogs_detail[Material_ID] ),
    ( CALCULATE ( AVERAGE ( fact_cogs_detail[Unit_Cost_EUR] ),
                  dim_Scenario[Scenario_ID] = "ACT" )
    - CALCULATE ( AVERAGE ( fact_cogs_detail[Unit_Cost_EUR] ),
                  dim_Scenario[Scenario_ID] = "BUD" ) )
    * CALCULATE ( SUM ( fact_cogs_detail[Quantity_Used] ),
                  dim_Scenario[Scenario_ID] = "ACT" )
)
```

Standard manufacturing variance formula: `(Actual Unit Cost - Standard Unit Cost) x Actual Quantity`, computed per material and summed via `SUMX`.
