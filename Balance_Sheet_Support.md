# Balance Sheet Support Measures

Shared snapshot logic used by both Working Capital and Debt & Liquidity pages. Not a dedicated dashboard page itself -- this is the plumbing both of those domains stand on.

## Stock vs. flow logic: snapshot pattern

The balance sheet is a *stock* (a snapshot at a point in time), not a *flow* (a sum over a period) -- unlike P&L or Cash Flow lines, you cannot sum a balance sheet account across 12 months and get a meaningful number. Every BS-derived measure in this model routes through a single snapshot pattern: find the latest `Date_Key` within the current filter context, then sum only the rows matching that key.

### BS End-of-Period
**Layer:** 2 (snapshot master measure)
**Depends on:** `Actual BS Amount`, `fact_balance_sheet`

```dax
BS End-of-Period =
VAR CurrentYear = MAX(fact_balance_sheet[Period_Year])
VAR LastKey =
    MAXX(
        FILTER(ALL(fact_balance_sheet), fact_balance_sheet[Period_Year] = CurrentYear),
        fact_balance_sheet[Date_Key]
    )
RETURN
CALCULATE(
    [Actual BS Amount],
    fact_balance_sheet[Date_Key] = LastKey
)
```

**Why `MAXX(FILTER(ALL(...)))` instead of `LASTDATE()`:** `fact_balance_sheet` uses an integer `Date_Key` (format `YYYYMMDD`) rather than a proper `DATE` column. `LASTDATE(dim_Calendar[Date])` silently returns `BLANK()` against this kind of key with no error thrown -- a lesson learned the hard way during the Layer 0 verification phase. The fix is this VAR-based pattern: find the maximum `Date_Key` within the current year filter (using `ALL` to remove any pre-existing date filter before re-deriving the correct period boundary), then filter to exactly that key. Every BS-based "as of period end" measure in the model uses this same pattern rather than a built-in time-intelligence function.

Every account-level BS measure below calls `[BS End-of-Period]` filtered by `GL_Subcategory` or `GL_Category` -- they do not re-implement the snapshot logic themselves.

## Account-level balance sheet measures (Layer 2)

```dax
Accounts Receivable =
CALCULATE ( [BS End-of-Period], dim_gl_account[GL_Subcategory] = "AR" )

Accounts Payable =
CALCULATE ( [BS End-of-Period], dim_gl_account[GL_Subcategory] = "AP" )

Inventory =
CALCULATE ( [BS End-of-Period], dim_gl_account[GL_Subcategory] = "Inventory" )

Cash & Equivalents =
CALCULATE ( [BS End-of-Period], dim_gl_account[GL_Subcategory] = "Cash" )

Current Assets =
CALCULATE ( [BS End-of-Period], dim_gl_account[GL_Subcategory] = "Current Assets" )

Non-Current Assets =
CALCULATE ( [BS End-of-Period], dim_gl_account[GL_Subcategory] = "Non-Current Assets" )

Current Liabilities =
CALCULATE ( [BS End-of-Period], dim_gl_account[GL_Subcategory] = "Current Liabilities" )

Long-Term Debt =
CALCULATE ( [BS End-of-Period], dim_gl_account[GL_Subcategory] = "Long-Term Debt" )

Total Assets =
CALCULATE ( [BS End-of-Period], dim_gl_account[BS_Category] = "Assets" )

Total Liabilities =
CALCULATE ( [BS End-of-Period], dim_gl_account[BS_Category] = "Liabilities" )

Total Equity =
CALCULATE ( [BS End-of-Period], dim_gl_account[BS_Category] = "Equity" )
```

Note the two-level filter granularity: most measures filter by `GL_Subcategory` (account-level detail), while the three `Total *` measures filter by the broader `BS_Category` (Assets / Liabilities / Equity) -- the balance sheet equivalent of `GL_Category` vs `GL_Subcategory` on the P&L side.

### BS Balance Check (accounting identity validation)
```dax
BS Balance Check = [Total Assets] + [Total Liabilities] + [Total Equity]
```

A Layer 0-style validation measure: in a correctly modeled balance sheet where Liabilities and Equity are stored as negative numbers (the convention used throughout this model), `Assets + Liabilities + Equity` should always equal zero (the fundamental accounting identity `Assets = Liabilities + Equity`, rearranged). If this measure ever returns a non-zero value when dropped onto a card with no filters, it's an immediate signal that something in the balance sheet data or sign conventions is broken -- this is exactly the kind of check the Layer 0 methodology is built around.

### Inventory sub-components (used by DIO calculations in Working_Capital.md)
```dax
Inventory Raw Materials =
CALCULATE (
    SUM ( fact_balance_sheet[Amount_EUR] ),
    dim_gl_account[GL_Subcategory] = "Inventory_RM",
    LASTDATE ( dim_calendar[Date] )
)

Inventory WIP =
CALCULATE (
    SUM ( fact_balance_sheet[Amount_EUR] ),
    dim_gl_account[GL_Subcategory] = "Inventory_WIP",
    LASTDATE ( dim_calendar[Date] )
)

Inventory Finished Goods =
CALCULATE (
    SUM ( fact_balance_sheet[Amount_EUR] ),
    dim_gl_account[GL_Subcategory] = "Inventory_FG",
    LASTDATE ( dim_calendar[Date] )
)

Inventory Total =
[Inventory Raw Materials] + [Inventory WIP] + [Inventory Finished Goods]
```

**Inconsistency worth flagging:** these three sub-component measures use `LASTDATE(dim_calendar[Date])` directly, *not* the `MAXX(FILTER(ALL(...)))` snapshot pattern used in `BS End-of-Period` above. Given the documented issue that `LASTDATE()` can silently return `BLANK()` against integer `Date_Key` fact tables, these three measures should be checked against actual output -- if `dim_calendar[Date]` has a working relationship to `fact_balance_sheet[Date_Key]` (e.g., via a calculated `Period_Year` join or a proper date relationship), `LASTDATE()` may work correctly here; if not, these inherit the same risk the `BS End-of-Period` pattern was specifically built to avoid. Worth a Layer 0 spot-check before relying on these three in a published dashboard.

A near-duplicate pair exists with slightly different names and logic, used elsewhere (Cash Conversion Cycle page, see `Working_Capital.md`):
```dax
Inventory Raw Materials  -- via DIO Raw Materials measure, uses AVERAGEX(VALUES(Year_Month), ...) instead
Inventory Finished Goods -- via DIO Finished Goods measure, same pattern
```
These alternate `DIO Raw Materials` / `DIO Finished Goods` measures (documented in `Working_Capital.md`) compute their own inventory lookup using `GL_Account_Name` text matching rather than `GL_Subcategory` codes, and average across `Year_Month` rather than taking a single snapshot -- a third distinct calculation path for what is conceptually the same inventory figure. Three different ways to compute "raw materials inventory" exist across the model (`Inventory Raw Materials` here, `DIO Raw Materials`'s internal calculation, and whatever feeds `DIO RM`'s `[Inventory Raw Materials]` reference). This is the kind of redundancy that's worth consolidating in a v2 of the model, even though each individual path is internally correct.
