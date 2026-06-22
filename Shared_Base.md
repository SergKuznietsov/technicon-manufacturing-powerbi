# Shared Base Measures

Layer 0/1 foundation that every domain file depends on. These measures are not tied to a single dashboard page — they are the plumbing underneath all of them.

## Scenario hardcoding pattern

This is the single most important architectural decision in the model, and it shows up in every fact table.

`fact_pnl`, `fact_balance_sheet`, and `fact_cashflow` all carry a `Scenario_ID` (or join to `dim_Scenario[Scenario_ID]`) with values `"ACT"`, `"BUD"`, `"FOR"`. Rather than relying on a slicer-driven relationship at every measure, the model defines one pair of measures per fact table that hardcodes the scenario filter:

```dax
Actual Amount =
CALCULATE ( [Amount PnL], dim_Scenario[Scenario_ID] = "ACT" )

Budget Amount =
CALCULATE ( [Amount PnL], dim_Scenario[Scenario_ID] = "BUD" )
```

Every downstream measure (`Net Revenue`, `COGS`, `SG&A`, etc.) calls `Actual Amount` or `Budget Amount` — never `Amount PnL` directly with its own scenario filter. This means scenario logic exists in exactly one place per fact table, not duplicated across 60+ derived measures.

**Why this matters for `fact_cashflow` specifically:** the relationship between `fact_cashflow` and `dim_Scenario` was historically believed to be absent. A later `INFO.RELATIONSHIPS()` check confirmed the relationship is in fact active — but every CF measure was already built against the hardcoded `fact_cashflow[Scenario_ID] = "ACT"` column filter, not the relationship. This is now a deliberate redundancy, not a workaround for a missing link: removing the hardcode and relying on the relationship instead would require re-validating every CF measure against Division/Scenario slicers, which has not been done. See `Known_Issues.md`.

## Layer 1 — Amount measures (one per fact table)

### Amount PnL
**Layer:** 1
**Depends on:** `fact_pnl[Amount_EUR]`
**Used in:** base for all P&L and Budget vs Actual measures

```dax
Amount PnL = SUM ( fact_pnl[Amount_EUR] )
```

### Amount BS
**Layer:** 1
**Depends on:** `fact_balance_sheet[Amount_EUR]`
**Used in:** base for `BS End-of-Period`, all balance sheet derived measures

```dax
Amount BS = SUM ( fact_balance_sheet[Amount_EUR] )
```

### Amount CF
**Layer:** 1
**Depends on:** `fact_cashflow[Amount_EUR]`
**Used in:** base for all Cash Flow measures

```dax
Amount CF = SUM ( fact_cashflow[Amount_EUR] )
```

### Amount COGS Detail
**Layer:** 1
**Depends on:** `fact_cogs_detail[Amount_EUR]`
**Used in:** Profitability Drill (Materials, Labor, Logistics breakdown)

```dax
Amount COGS Detail = SUM ( fact_cogs_detail[Amount_EUR] )
```

### Amount Sales
**Layer:** 1
**Depends on:** `fact_sales[Revenue_EUR]`
**Used in:** Revenue by Division, Profitability Drill

```dax
Amount Sales = SUM ( fact_sales[Revenue_EUR] )
```

## Layer 2 — Scenario-filtered amounts

### Actual Amount
**Layer:** 2
**Depends on:** `Amount PnL`, `dim_Scenario`
**Used in:** every P&L line item measure

```dax
Actual Amount =
CALCULATE ( [Amount PnL], dim_Scenario[Scenario_ID] = "ACT" )
```

### Budget Amount
**Layer:** 2
**Depends on:** `Amount PnL`, `dim_Scenario`
**Used in:** every Budget vs Actual line item measure

```dax
Budget Amount =
CALCULATE ( [Amount PnL], dim_Scenario[Scenario_ID] = "BUD" )
```

### Actual BS Amount / Budget BS Amount
**Layer:** 2
**Depends on:** `Amount BS`, `dim_Scenario`
**Used in:** `BS End-of-Period`

```dax
Actual BS Amount =
CALCULATE ( [Amount BS], dim_Scenario[Scenario_ID] = "ACT" )

Budget BS Amount =
CALCULATE ( [Amount BS], dim_Scenario[Scenario_ID] = "BUD" )
```

### Actual CF Amount / Budget CF Amount
**Layer:** 2
**Depends on:** `Amount CF`, `dim_Scenario`
**Used in:** base for `Budget CF Operating/Investing/Financing`

```dax
Actual CF Amount =
CALCULATE ( [Amount CF], dim_Scenario[Scenario_ID] = "ACT" )

Budget CF Amount =
CALCULATE ( [Amount CF], dim_Scenario[Scenario_ID] = "BUD" )
```

### Actual COGS Detail / Budget COGS Detail
**Layer:** 2
**Depends on:** `Amount COGS Detail`, `dim_Scenario`
**Used in:** `Material Price Variance`, cost component drill-downs

```dax
Actual COGS Detail =
CALCULATE ( [Amount COGS Detail], dim_Scenario[Scenario_ID] = "ACT" )

Budget COGS Detail =
CALCULATE ( [Amount COGS Detail], dim_Scenario[Scenario_ID] = "BUD" )
```

### Debug BUD
**Layer:** 2 (diagnostic)
**Depends on:** `fact_pnl`, `dim_Scenario`
**Used in:** Layer 0 validation only — not wired to any visual

```dax
Debug BUD =
CALCULATE (
    COUNTROWS ( fact_pnl ),
    dim_Scenario[Scenario_ID] = "BUD"
)
```

Kept in the model as a Layer 0 sanity check: confirms the Budget scenario actually has rows before any Layer 2 measure built on top of it is trusted.

## Row count diagnostics (Layer 0)

### # PnL Rows
```dax
# PnL Rows = COUNTROWS ( fact_pnl )
```

### # Sales Detail Rows
```dax
# Sales Detail Rows = COUNTROWS ( fact_sales_detail )
```

These two measures are the literal first step of the Layer 0 → Layer 1 → Layer 2 sequence: before any business logic is written, row counts are checked in DAX Query View to confirm the fact table loaded as expected.

## Language / translation helpers

The model supports a disconnected `dim_language` table and `dim_translations` lookup table, used for an EN/DE toggle pattern. (Note: per the canonical strategy decision of 2026-06-21, the published TechniCon dashboard ships 100% English — these measures exist in the model but the toggle is not exposed in the published version. A fully German version is planned as a separate future project.)

### Selected Language
**Layer:** 1
**Depends on:** `dim_language[Language]`

```dax
Selected Language =
SELECTEDVALUE ( dim_language[Language], "EN" )
```

### Translate
**Layer:** 2
**Depends on:** `Selected Language`, `dim_translations`
**Used in:** generic key-based lookup, superseded in practice by the `Lbl *` measures below

```dax
Translate =
VAR _key = SELECTEDVALUE ( dim_translations[Key] )
VAR _result =
    SWITCH (
        [Selected Language],
        "EN", LOOKUPVALUE ( dim_translations[EN], dim_translations[Key], _key ),
        "DE", LOOKUPVALUE ( dim_translations[DE], dim_translations[Key], _key )
    )
RETURN _result
```

### Lbl Revenue / Lbl COGS / Lbl Gross_Profit
**Layer:** 2
**Depends on:** `Selected Language`, `dim_translations`

```dax
Lbl Revenue =
SWITCH ( [Selected Language],
    "EN", LOOKUPVALUE ( dim_translations[EN], dim_translations[Key], "lbl_revenue" ),
    "DE", LOOKUPVALUE ( dim_translations[DE], dim_translations[Key], "lbl_revenue" )
)
```

`Lbl COGS` and `Lbl Gross_Profit` follow the identical pattern with `"lbl_cogs"` / `"lbl_gross_profit"` as the lookup key.

### Label Revenue / Label Gross Profit / Label Net Revenue
**Layer:** 2
**Depends on:** `Selected Language`

```dax
Label Gross Profit =
SWITCH (
    [Selected Language],
    "EN", "Gross Profit",
    "DE", "Bruttoergebnis",
    "Gross Profit"
)
```

`Label Net Revenue` follows the same inline-string pattern (`"Net Revenue"` / `"Umsatzerlöse"`). `Label Revenue` instead delegates to the `dim_translations` lookup table rather than inlining strings — an inconsistent pattern across these three measures (two inline, one table-driven) but functionally equivalent for the EN-only published version.
