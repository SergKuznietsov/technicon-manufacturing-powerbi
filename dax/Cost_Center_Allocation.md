# Cost Center Allocation Measures

Covers page: Overhead Allocation. Distinct fact tables from the rest of the model -- `fact_cc_allocated_amounts` and `fact_cc_overhead_pool` -- built specifically to support an indirect-cost-to-production allocation walkthrough (Admin, IT, Logistics, QA costs allocated into Production cost centers).

## Layer 1

```dax
Allocated Overhead EUR =
SUM(fact_cc_allocated_amounts[Allocated_Amount_EUR])

Total Allocated EUR =
SUM(fact_cc_allocated_amounts[Allocated_Amount_EUR])

Total Overhead Pool EUR =
SUM(fact_cc_overhead_pool[Allocatable_Amount_EUR])
```

`Allocated Overhead EUR` and `Total Allocated EUR` are identical formulas under two names -- the same naming-duplication pattern seen elsewhere in the model (e.g. `CF Net Change` / `Net Cash Flow` in `Cash_Flow.md`). Harmless, but a candidate for consolidation.

## Layer 2

### Largest Receiver Share %
```dax
Largest Receiver Share % =
DIVIDE(
    CALCULATE(
        SUM(fact_cc_allocated_amounts[Allocated_Amount_EUR]),
        fact_cc_allocated_amounts[Receiver_CC_ID] = "CC01"
    ),
    SUM(fact_cc_allocated_amounts[Allocated_Amount_EUR])
)
```

**Hardcoded cost center ID:** `"CC01"` is hardcoded as "the largest receiver" rather than dynamically determined via `TOPN`/`RANKX` against all receiving cost centers. This works correctly for the current dataset (where Production -- Industrial, mapped to CC01, genuinely is the largest receiver at 40.8% per the Overhead Allocation page), but the measure will silently report the wrong "largest receiver" percentage if the underlying allocation data changes and a different cost center becomes the largest receiver in a future period. A dynamic version using `TOPN(1, SUMMARIZE(...), [Allocated_Amount_EUR], DESC)` (the same pattern used in `Worst Category` in `Budget_vs_Actual.md`) would remove this fragility. Flagged as a design choice to revisit, not a bug in the current published numbers.

## What this page demonstrates (controlling context)

The Overhead Allocation page implements a direct allocation method: indirect/overhead cost centers (Admin, IT & Digital, Logistics & Warehousing, Quality Assurance) are allocated into the three Production cost centers using different cost drivers per allocating center -- headcount for Admin/IT, revenue share for Logistics, production volume for QA (per the page's stated allocation drivers). Tax and Interest are explicitly excluded from the allocatable pool (not allocatable per HGB/German GAAP and standard CO convention), and R&D is excluded as a period cost under IFRS convention rather than a product cost subject to overhead absorption.

This is a deliberately simpler allocation method than step-down or reciprocal allocation (where indirect cost centers also allocate costs to each other before hitting production) -- a reasonable scope decision for a portfolio dashboard, and one worth being able to articulate the trade-off on if asked about allocation methodology in an interview context: direct allocation is simpler to build and explain but understates the true cost of services that indirect departments provide to each other (e.g., IT supporting Admin) before reaching production.
