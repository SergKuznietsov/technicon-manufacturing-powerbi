# Working Capital Measures

Covers pages: Cash Conversion Cycle, Receivables Aging & Risk. Depends on `Balance_Sheet_Support.md` (`Accounts Receivable`, `Accounts Payable`, `Inventory`) and `PnL.md` (`Net Revenue`, `COGS`).

## Cash Conversion Cycle (DSO / DPO / DIO / CCC)

These are the four headline ratios from the Key KPI Formulas reference table. All average the underlying balance over `dim_Calendar[Year_Month]` rather than using a single point-in-time balance -- this smooths out month-to-month noise in what would otherwise be a single-snapshot ratio.

### DSO (Days Sales Outstanding)
```dax
DSO =
DIVIDE (
    AVERAGEX (
        VALUES ( dim_Calendar[Year_Month] ),
        [Accounts Receivable]   -- AR balance at month-end
    ) * 365,
    [Net Revenue]
)
```

### DPO (Days Payable Outstanding)
```dax
DPO =
DIVIDE (
    AVERAGEX (
        VALUES ( dim_Calendar[Year_Month] ),
        [Accounts Payable]
    ) * 365,
    [COGS]
)
```

### DIO (Days Inventory Outstanding) — split by RM / WIP / FG
```dax
DIO RM =
DIVIDE (
    AVERAGEX ( VALUES ( dim_calendar[Year_Month] ), [Inventory Raw Materials] ) * 365,
    ABS ( [COGS] )
)

DIO WIP =
DIVIDE (
    AVERAGEX ( VALUES ( dim_calendar[Year_Month] ), [Inventory WIP] ) * 365,
    ABS ( [COGS] )
)

DIO FG =
DIVIDE (
    AVERAGEX ( VALUES ( dim_calendar[Year_Month] ), [Inventory Finished Goods] ) * 365,
    ABS ( [COGS] )
)

DIO Total = [DIO RM] + [DIO WIP] + [DIO FG]
```

The Cash Conversion Cycle page shows DIO split into its three components (Raw Materials / Work-in-Progress / Finished Goods) rather than a single blended figure -- this is the controlling-relevant view, since RM, WIP, and FG inventory each have different operational drivers and different levers to pull if a company wants to reduce inventory days.

A second, separately-built pair of measures computes Raw Materials and Finished Goods DIO using a different inventory lookup (text-matching `GL_Account_Name` instead of referencing the `Inventory Raw Materials` / `Inventory Finished Goods` measures from `Balance_Sheet_Support.md`):

```dax
DIO Raw Materials =
DIVIDE(
    AVERAGEX(
        VALUES( dim_Calendar[Year_Month] ),
        CALCULATE( SUM( fact_balance_sheet[Amount_EUR] ),
            dim_gl_account[GL_Account_Name] = "Inventory -- Raw Materials" )
    ) * 365,
    [COGS]
)

DIO Finished Goods =
DIVIDE(
    AVERAGEX(
        VALUES( dim_Calendar[Year_Month] ),
        CALCULATE( SUM( fact_balance_sheet[Amount_EUR] ),
            dim_gl_account[GL_Account_Name] = "Inventory -- Finished Goods" )
    ) * 365,
    [COGS]
)
```

These appear to be an earlier or alternate build of the same metric -- not referenced by `DIO Total` (which uses `DIO RM` / `DIO WIP` / `DIO FG` instead). Likely safe to remove once confirmed unused by any visual, but flagged here rather than silently dropped since both produce conceptually correct numbers if the underlying `GL_Account_Name` text values are accurate.

### CCC (Cash Conversion Cycle)
```dax
CCC = [DSO] + [DIO Total] - [DPO]
```

Standard formula: the number of days cash is tied up in operations before being converted back to cash from a sale. Lower is better -- DPO is subtracted because financing inventory and receivables via supplier credit (paying suppliers later) reduces the cash tied up.

## Receivables Aging & Risk

### AR Total / AR Aging (snapshot pattern, analogous to BS End-of-Period)
```dax
AR Total = SUM ( fact_ar_aging[Amount_EUR] )

AR Aging =
VAR LastKey = MAX(fact_ar_aging[Date_Key])
RETURN
CALCULATE(
    SUM(fact_ar_aging[Amount_EUR]),
    fact_ar_aging[Date_Key] = LastKey
)

AR Aging 2024 =
CALCULATE(
    [AR Aging],
    dim_calendar[Year] = 2024
)
```

`AR Aging` uses `MAX(fact_ar_aging[Date_Key])` directly rather than the `MAXX(FILTER(ALL(...)))` pattern from `BS End-of-Period` -- a simpler version that works here specifically because `fact_ar_aging` is a narrower, purpose-built aging snapshot table (unlike the multi-period `fact_balance_sheet`), so a plain `MAX` within the current filter context is sufficient.

### Aging bucket breakdown
```dax
AR Current =
CALCULATE ( [AR Total], fact_ar_aging[Aging_Bucket] = "0-30" )

AR 31-60 =
CALCULATE ( [AR Total], fact_ar_aging[Aging_Bucket] = "31-60" )

AR 61-90 =
CALCULATE ( [AR Total], fact_ar_aging[Aging_Bucket] = "61-90" )

AR 90+ =
CALCULATE ( [AR Total], fact_ar_aging[Aging_Bucket] = "90+" )

AR Overdue = [AR Total] - [AR Current]
AR Overdue % = DIVIDE ( [AR Overdue], [AR Total], 0 )
AR Critical Overdue % = DIVIDE ( [AR 90+], [AR Total], 0 )

AR Over 60d Benchmark = 0.10
```

### % AR Over 60d (combines two buckets)
```dax
% AR Over 60d =
DIVIDE(
    CALCULATE(
        [AR Aging],
        fact_ar_aging[Aging_Bucket] IN {"61-90", "90+"}
    ),
    [AR Aging]
)
```

### AR Provision (expected-loss style calculation)
```dax
AR Provision =
VAR LastKey = MAX(fact_ar_aging[Date_Key])
RETURN
CALCULATE(
    SUMX(
        fact_ar_aging,
        fact_ar_aging[Amount_EUR] * fact_ar_aging[Provision_Pct]
    ),
    fact_ar_aging[Date_Key] = LastKey
)

AR Provision Total = SUM ( fact_ar_aging[Provision_EUR] )

Provision % of AR = DIVIDE([AR Provision], [AR Aging])
Provision Rate % = DIVIDE ( [AR Provision Total], [AR Total], 0 )
```

Note: `AR Provision` *computes* the provision dynamically via `SUMX(Amount x Provision_Pct%)` row by row — a bottom-up expected-loss calculation per customer/segment row, weighted by each row's own provision percentage. `AR Provision Total` instead *sums a pre-calculated column* (`Provision_EUR`) that presumably already has this same multiplication baked in upstream (in the Python mock data generation step). Both should converge to the same figure if the source data is consistent; `AR Provision` is the more transparent of the two since the calculation logic is visible in the measure itself rather than hidden in an upstream column.
