# Budget vs. Actual Measures

Covers pages: Variance Heatmap, Variance Drill, Plan vs Actual (Cost Center). Depends on `Shared_Base.md` and the core line-item measures in `PnL.md`.

## Variance core (Layer 2)

These are the universal variance measures -- the same pattern is reused across Revenue, COGS, EBIT, EBITDA, Net Income, OpEx, R&D, D&A, and Tax.

### Variance Abs / Variance %
**Layer:** 2
**Depends on:** `Actual Amount`, `Budget Amount`

```dax
Variance Abs = [Actual Amount] - [Budget Amount]

Variance % =
DIVIDE (
    [Actual Amount] - [Budget Amount],
    ABS ( [Budget Amount] )
)
```

**Why `ABS()` on the denominator:** `Budget Amount` for expense categories (COGS, OpEx) is stored as a negative number. Without `ABS()`, dividing by a negative budget would flip the sign of every expense variance percentage -- an unfavorable overspend would display as a positive (favorable-looking) percentage. This is the single most important sign-safety rule in the entire variance layer, and it is applied consistently in every `Variance X %` measure below.

```dax
Variance Abs Display = ABS ( [Variance Abs] )
Variance Abs Sort = ABS ( [Variance Abs] )
```

Two separate measures with identical logic -- `Variance Abs Display` for showing the unsigned magnitude in a card/label, `Variance Abs Sort` for forcing sort order in a chart independent of display formatting. Functionally redundant but kept separate so a future formatting change to one doesn't silently break sort behaviour on a visual relying on the other.

### Line-item variance family
```dax
Variance Revenue = [Net Revenue] - [Budget Net Revenue]
Variance Revenue % = DIVIDE ( [Variance Revenue], ABS ( [Budget Net Revenue] ), 0 )
Variance Revenue YTD = [Net Revenue YTD] - [Budget Net Revenue YTD]

Variance COGS = -1 * [COGS] - [Budget COGS]
Variance COGS % = DIVIDE ( [Variance COGS], ABS ( [Budget COGS] ), 0 )

Variance OpEx = [Total OpEx] - [Budget Total OpEx]
Variance OpEx % = DIVIDE ( [Variance OpEx], ABS ( [Budget Total OpEx] ), 0 )

Variance Gross Profit = [Gross Profit] - [Budget Gross Profit]
Variance Gross Profit % = DIVIDE ( [Variance Gross Profit], ABS ( [Budget Gross Profit] ), 0 )

Variance EBIT = [EBIT] - [Budget EBIT]
Variance EBIT % = DIVIDE ( [Variance EBIT], ABS ( [Budget EBIT] ), 0 )

Variance EBITDA = [EBITDA] - [Budget EBITDA]
Variance EBITDA % = DIVIDE ( [Variance EBITDA], ABS ( [Budget EBITDA] ), 0 )

Variance Net Income = [Net Income] - [Budget Net Income]
Variance Net Income % = DIVIDE ( [Variance Net Income], ABS ( [Budget Net Income] ), 0 )

Variance D&A =
CALCULATE ( [Actual Amount], dim_gl_account[GL_Subcategory] = "D&A" )
- CALCULATE ( [Budget Amount], dim_gl_account[GL_Subcategory] = "D&A" )

Variance R&D =
CALCULATE ( [Actual Amount], dim_gl_account[GL_Subcategory] = "R&D" )
- CALCULATE ( [Budget Amount], dim_gl_account[GL_Subcategory] = "R&D" )

Variance Tax =
CALCULATE ( [Actual Amount], dim_gl_account[GL_Category] = "Tax" )
- CALCULATE ( [Budget Amount], dim_gl_account[GL_Category] = "Tax" )
```

> **Key data correction (established during build):** Tax variance in FY2024 is *favorable*, not unfavorable -- the Variance Heatmap's "Worst Category" label for Tax refers to the *magnitude* of deviation from budget, not the direction. A large favorable variance and a large unfavorable variance both register as "worst" under a magnitude-only ranking. This is a labelling/interpretation note, not a calculation bug -- `Worst Category` (below) is explicitly magnitude-based by design.

### Margin variance (percentage-point deltas, not relative %)
```dax
Margin Variance Gross pp = [Gross Margin %] - [Budget Gross Margin %]
Margin Variance EBITDA pp = [EBITDA Margin %] - [Budget EBITDA Margin %]
```

These are *not* run through `DIVIDE` -- they are direct subtraction of two already-percentage measures, producing a percentage-point (pp) delta rather than a relative variance. Naming them with the `pp` suffix is deliberate to avoid confusion with the `%`-suffixed relative-variance measures elsewhere in this file.

### Status flags (for conditional formatting)
```dax
Variance Status Revenue =
SWITCH (
    TRUE (),
    [Variance Revenue %] >= 0,       "Green",
    [Variance Revenue %] >= -0.03,   "Yellow",
                                     "Red"
)

Variance Status EBITDA =
SWITCH (
    TRUE (),
    [Variance EBITDA %] >= 0,        "Green",
    [Variance EBITDA %] >= -0.05,    "Yellow",
                                     "Red"
)

Is Favorable = IF ( [Variance Abs] > 0, 1, 0 )
Is Unfavorable = IF ( [Variance Abs] < 0, 1, 0 )
```

Note the different tolerance bands: Revenue allows -3% before flagging Red, EBITDA allows -5%. This reflects that EBITDA naturally has higher period-to-period volatility than top-line revenue, so a tighter Revenue band catches deviations EBITDA's wider band would let through.

## Variance Heatmap

### Worst Category (TOPN pattern for "find the row with the extreme value")
**Layer:** 2
**Depends on:** `Variance %`, `dim_GL_Category_Sort`

```dax
Worst Category =
CALCULATE (
    SELECTEDVALUE ( dim_GL_Category_Sort[GL_Category] ),
    TOPN (
        1,
        ALL ( dim_GL_Category_Sort[GL_Category] ),
        [Variance %],
        ASC
    )
)
```

`ASC` sort on `Variance %` means the *most negative* variance percentage wins -- this is why a large favorable Tax variance can still be flagged "worst" if its magnitude (in the wrong direction for this sort) or a coincidentally large unfavorable swing elsewhere isn't present that period. See the Tax data-correction note above.

### Favorable / Unfavorable month counters
```dax
Favorable Months =
COUNTROWS (
    FILTER (
        VALUES ( dim_Calendar[Month_Name] ),
        CALCULATE (
            [Variance %],
            dim_GL_Category_Sort[GL_Category] = "Revenue"
        ) > 0
    )
)

Unfavorable Months =
COUNTROWS (
    FILTER (
        VALUES ( dim_Calendar[Month_Name] ),
        CALCULATE (
            [Variance %],
            dim_GL_Category_Sort[GL_Category] = "Revenue"
        ) < 0
    )
)
```

Both measures are explicitly scoped to Revenue variance only (hardcoded `GL_Category = "Revenue"` filter) -- the "Favorable Months" / "Unfavorable Months" cards on the Variance Heatmap page answer "how many months did Revenue beat budget," not a blended multi-category count.

### CF Heatmap Color (conditional formatting logic)
```dax
CF Heatmap Color =
VAR Cat = SELECTEDVALUE( dim_gl_account[GL_Category] )
VAR VarPct = [Variance %]
RETURN
    SWITCH(
        TRUE(),
        Cat = "Revenue"       && VarPct > 0, "#2171B5",
        Cat = "Revenue"       && VarPct < 0, "#E6550D",
        Cat = "COGS"          && VarPct < 0, "#2171B5",
        Cat = "COGS"          && VarPct > 0, "#E6550D",
        Cat = "OpEx"          && VarPct < 0, "#2171B5",
        Cat = "OpEx"          && VarPct > 0, "#E6550D",
        Cat = "Non-Operating" && VarPct > 0, "#2171B5",
        Cat = "Non-Operating" && VarPct < 0, "#E6550D",
        Cat = "Tax"           && VarPct < 0, "#2171B5",
        Cat = "Tax"           && VarPct > 0, "#E6550D",
        "#F5F5F5"
    )
```

This is the measure that encodes the controlling convention "favorable direction differs by category." For Revenue and Non-Operating, *positive* variance is favorable (blue). For COGS, OpEx, and Tax, *negative* variance is favorable (blue) -- spending less than budgeted is good. Getting this category-by-category sign logic right is what makes the heatmap colors meaningful rather than naively "green=positive, red=negative."

## Variance Drill (ranking unfavorable/favorable line items)

### Favorable Rank / Unfavorable Rank
**Layer:** 2
**Depends on:** `Variance Abs`, `dim_gl_account[GL_Subcategory]`

```dax
Favorable Rank =
IF (
    [Variance Abs] <= 0,
    BLANK(),
    RANKX (
        FILTER (
            ALL ( dim_gl_account[GL_Subcategory] ),
            CALCULATE ( [Variance Abs] ) > 0
        ),
        [Variance Abs],
        ,
        DESC,
        DENSE
    )
)

Unfavorable Rank =
IF (
    [Variance Abs] >= 0,
    BLANK(),
    RANKX (
        FILTER (
            ALL ( dim_gl_account[GL_Subcategory] ),
            CALCULATE ( [Variance Abs] ) < 0
        ),
        ABS ( [Variance Abs] ),
        ,
        DESC,
        DENSE
    )
)
```

**Pattern note -- this is the RANKX-inside-FILTER fix referenced in the project's lessons learned:** `RANKX` over a `FILTER(ALL(...), ...)` expression fails if the filter predicate references a measure directly in row context without wrapping it in `CALCULATE`. Both measures above wrap the filter predicate as `CALCULATE ( [Variance Abs] ) > 0` -- the `CALCULATE` forces the correct context transition so each subcategory's variance is evaluated independently before the comparison, rather than evaluating in the row context of whatever visual triggered the calculation. Without the `CALCULATE` wrapper, this measure either errors or silently returns the same value for every row.

The outer `IF` guard (`<= 0` / `>= 0` returning `BLANK()`) prevents an unfavorable line item from being shown with a favorable rank number and vice versa -- each measure only produces a result for the rows it's semantically meant to rank.

### Top Variance Rank (single combined ranking, used elsewhere)
```dax
Top Variance Rank =
RANKX (
    ALL ( dim_gl_account[GL_Subcategory] ),
    ABS ( [Variance Abs] ),
    ,
    DESC,
    DENSE
)
```

Simpler variant -- ranks by absolute magnitude regardless of favorable/unfavorable direction, used where the page wants "biggest swings" rather than a split favorable/unfavorable view.

## CF-side variance (Cash Flow vs Budget CF)

```dax
Variance CF Operating = [CF Operating] - [Budget CF Operating]
Variance CF Investing = [CF Investing] - [Budget CF Investing]
Variance CF Financing = [CF Financing] - [Budget CF Financing]
```

See `Cash_Flow.md` for `CF Operating` / `CF Investing` / `CF Financing` and `Budget CF Operating` / `Investing` / `Financing` definitions.

### Bridge Value BvA (Plan-to-Actual bridge, parallel pattern to PnL Bridge Value)
```dax
Bridge Value BvA =
SWITCH (
    SELECTEDVALUE ( 'BvA Bridge Categories'[Step] ),

    "01 Budget NI",    [Net Income] - [Variance Net Income],
    "02 Revenue D",    [Variance Revenue],
    "03 COGS D",       [Variance COGS],
    "04 SG&A D",       [Variance OpEx],
    "05 R&D D",        [Variance R&D],
    "06 D&A D",        [Variance D&A],
    "07 Tax D",        [Variance Tax],
    "08 Actual NI",    [Net Income],

    BLANK()
)
```

Same disconnected-table SWITCH pattern as the P&L Bridge Chart (`Bridge_PL` there, `'BvA Bridge Categories'` here) -- reconstructs Budget Net Income as `Net Income - Variance Net Income` rather than calling `Budget Net Income` directly, which is a slightly indirect but equivalent route to the same number.

## Cost Center Plan vs Actual

### CC Cost ACT / CC Cost BUD (and Display variants)
**Layer:** 2
**Depends on:** `fact_pnl`, `dim_gl_account`, `dim_Scenario`

```dax
CC Cost ACT =
CALCULATE(
    SUM(fact_pnl[Amount_EUR]),
    dim_gl_account[GL_Category] IN { "COGS", "OpEx" },
    dim_Scenario[Scenario_ID] = "ACT"
)

CC Cost BUD =
CALCULATE(
    SUM(fact_pnl[Amount_EUR]),
    dim_gl_account[GL_Category] IN { "COGS", "OpEx" },
    dim_Scenario[Scenario_ID] = "BUD"
)

CC Cost ACT Display = ABS([CC Cost ACT])
CC Cost BUD Display = ABS([CC Cost BUD])
```

These two go directly to `SUM(fact_pnl[Amount_EUR])` rather than calling `Actual Amount` / `Budget Amount` -- a deviation from the Shared_Base pattern. Functionally equivalent since `Actual Amount` is itself `CALCULATE([Amount PnL], Scenario="ACT")`, but worth flagging as an inconsistency: if the scenario-hardcoding logic in `Shared_Base.md` is ever changed, these two measures would need to be updated independently since they don't route through it.

### CC Variance Abs / CC Variance % / CC Status Flag
```dax
CC Variance Abs = [CC Cost ACT] - [CC Cost BUD]

CC Variance % =
DIVIDE(
    [CC Variance Abs],
    ABS([CC Cost BUD])
)

CC Status Flag =
IF(
    ISBLANK([CC Cost ACT]) || ISBLANK([CC Cost BUD]),
    BLANK(),
    SWITCH(
        TRUE(),
        ABS([CC Variance %]) <= 0.03, "(checkmark)",
        ABS([CC Variance %]) <= 0.07, "(warning)",
        "(x)"
    )
)

CC Variance % Display =
IF(
    ISBLANK([CC Cost ACT]) || ISBLANK([CC Cost BUD]),
    BLANK(),
    FORMAT(ABS([CC Variance %]), "0.0%")
    & IF([CC Variance Abs] < 0, " (up)", " (down)")
)
```

`CC Status Flag` uses a 3-tier tolerance band (<=3% on-target, <=7% warning, >7% breach) -- tighter than the Revenue/EBITDA variance status bands above, reflecting that cost center overspend tolerance in this model is set stricter than top-line revenue tolerance.

### CC Count Overspend
```dax
CC Count Overspend =
COUNTROWS(
    FILTER(
        VALUES(dim_cost_center[Cost_Center_ID]),
        [CC Variance Abs] < 0
    )
)
```

Counts how many distinct cost centers are running over budget (negative variance = overspend, since costs are negative numbers and a more-negative actual than budget means overspend).
