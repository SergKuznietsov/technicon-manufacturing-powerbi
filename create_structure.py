"""
TechniCon Manufacturing GmbH — Mock Data Structure Generator (v2)
Creates empty CSV files with column headers for Power BI portfolio.

12 files total:
  - Dimensions (4): dim_cost_center, dim_gl_account, dim_product_group, dim_customer_segment
  - Facts (8): fact_pnl, fact_balance_sheet, fact_cashflow, fact_sales,
               fact_sales_detail, fact_cogs_detail, fact_ar_aging, fact_debt

NOT generated here (Power BI creates these automatically):
  - dim_calendar (DAX CALENDARAUTO)
  - dim_division (lookup table in Power BI)
  - dim_region (lookup table in Power BI)
  - dim_scenario (lookup table in Power BI)

Usage:
    python create_structure.py

Period: 2020-2025 (actual) + 2026 (budget/forecast)
"""

import csv
import os

# === CONFIGURE YOUR PATH HERE ===
OUTPUT_DIR = r"D:\\Project - Portfolio Controlling\\02_Mock_Data\\Generated_CSV"


# ============================================================
# DIMENSION TABLES (4 files)
# ============================================================

dimensions = {

    "dim_cost_center.csv": {
        "description": "Cost centers with division mapping and type classification",
        "columns": [
            "Cost_Center_ID",       # CC01, CC02, ...
            "Cost_Center_Name",     # e.g. "Production - Industrial", "Sales DACH"
            "Division_ID",          # DIV01, DIV02, DIV03 (FK to Power BI dim_division)
            "Cost_Type",            # Production / Sales / Admin / R&D / Logistics
            "Is_Direct",            # TRUE = direct cost center, FALSE = overhead
        ],
    },

    "dim_gl_account.csv": {
        "description": "Chart of accounts — ~50-60 rows covering P&L, BS, CF structure",
        "columns": [
            "GL_Account_ID",        # PL001, BS001, CF001, ...
            "GL_Account_Name",      # e.g. "Gross Revenue", "Raw Materials", "Cash & Equivalents"
            "GL_Category",          # Revenue / COGS / OpEx / Non-Operating / Tax / Asset / Liability / Equity / CF
            "GL_Subcategory",       # e.g. "Sales Deductions", "Manufacturing Overhead", "Current Assets"
            "Financial_Statement",  # PnL / BS / CF
            "BS_Category",          # Current_Asset / Non_Current_Asset / Current_Liability / Non_Current_Liability / Equity / NULL
            "CF_Category",          # Operating / Investing / Financing / NULL
            "Sign_Convention",      # Debit / Credit — for correct P&L display
            "Is_COGS_Detail",       # TRUE for Raw Materials, Direct Labor, Mfg Overhead lines
            "Sort_Order",           # Integer for correct display order in reports
        ],
    },

    "dim_product_group.csv": {
        "description": "Product groups per division with margin and supply chain attributes",
        "columns": [
            "Product_Group_ID",         # PG01, PG02, ...
            "Product_Group_Name",       # e.g. "Industrial Adhesives", "Safety Helmets"
            "Division_ID",              # DIV01, DIV02, DIV03
            "Primary_Raw_Material",     # e.g. "Polymers", "Steel", "Electronics"
            "Secondary_Raw_Material",   # e.g. "Solvents", "Plastics", NULL
            "Material_Cost_Pct",        # Target material cost as % of revenue (e.g. 35)
            "Gross_Margin_Target_Pct",  # Target gross margin % (e.g. 42)
            "Supply_Chain_Risk",        # Low / Medium / High
            "COVID_Demand_Impact",      # Positive / Negative / Neutral
        ],
    },

    "dim_customer_segment.csv": {
        "description": "Customer segments with payment behavior and risk profile",
        "columns": [
            "Customer_Segment_ID",      # SEG01, SEG02, ...
            "Customer_Segment_Name",    # e.g. "Enterprise OEM", "SMB Distributors", "Government"
            "Typical_Payment_Days",     # Normal DSO for this segment (e.g. 30, 45, 60)
            "Crisis_Payment_Days",      # DSO during crisis periods (e.g. 50, 75, 90)
            "Revenue_Concentration",    # High / Medium / Low — Pareto indicator
            "Credit_Risk_Rating",       # A / B / C
        ],
    },
}


# ============================================================
# FACT TABLES — AGGREGATED (6 files)
# ============================================================

facts_aggregated = {

    "fact_pnl.csv": {
        "description": "P&L data — monthly by scenario, division, cost center, GL account",
        "columns": [
            "Date_Key",         # 202001, 202002, ... (YYYYMM)
            "Scenario_ID",      # ACT / BUD / FC1 / FC2
            "Division_ID",      # DIV01, DIV02, DIV03
            "Cost_Center_ID",   # CC01, CC02, ... (FK to dim_cost_center)
            "GL_Account_ID",    # PL001, PL002, ... (FK to dim_gl_account)
            "Amount_EUR",       # Amount in EUR (positive = debit convention per GL)
        ],
    },

    "fact_balance_sheet.csv": {
        "description": "Balance sheet snapshots — monthly closing balances",
        "columns": [
            "Date_Key",         # 202001, 202002, ...
            "GL_Account_ID",    # BS001, BS002, ... (FK to dim_gl_account)
            "Amount_EUR",       # Closing balance in EUR
        ],
    },

    "fact_cashflow.csv": {
        "description": "Cash flow statement — monthly by CF category",
        "columns": [
            "Date_Key",         # 202001, 202002, ...
            "GL_Account_ID",    # CF001, CF002, ... (FK to dim_gl_account)
            "CF_Category",      # Operating / Investing / Financing
            "Amount_EUR",       # Amount in EUR (positive = inflow, negative = outflow)
        ],
    },

    "fact_sales.csv": {
        "description": "Aggregated sales cube — monthly by division, product, region, segment",
        "columns": [
            "Date_Key",             # 202001, 202002, ...
            "Division_ID",          # DIV01, DIV02, DIV03
            "Product_Group_ID",     # PG01, PG02, ... (FK to dim_product_group)
            "Region_ID",            # REG01, REG02, ... (FK to Power BI dim_region)
            "Customer_Segment_ID",  # SEG01, SEG02, ... (FK to dim_customer_segment)
            "Revenue_EUR",          # Net revenue in EUR
            "Quantity_Sold",        # Units sold
            "Avg_Selling_Price",    # Revenue / Quantity
        ],
    },

    "fact_ar_aging.csv": {
        "description": "Accounts receivable aging — monthly by customer segment and bucket",
        "columns": [
            "Date_Key",             # 202001, 202002, ...
            "Customer_Segment_ID",  # SEG01, SEG02, ...
            "Aging_Bucket",         # Current / 1-30 / 31-60 / 61-90 / 90+
            "Amount_EUR",           # Outstanding amount in EUR
            "Provision_Pct",        # Bad debt provision % for this bucket
            "Provision_EUR",        # Calculated provision amount
        ],
    },

    "fact_debt.csv": {
        "description": "Debt facilities — monthly status of each loan/facility",
        "columns": [
            "Date_Key",             # 202001, 202002, ...
            "Facility_ID",          # DEBT01, DEBT02, ...
            "Facility_Name",        # e.g. "Revolving Credit Facility", "Term Loan A"
            "Debt_Type",            # Revolving / Term / Bond / Lease
            "Classification",       # Short_Term / Long_Term
            "Outstanding_EUR",      # Current outstanding balance
            "Interest_Rate_Pct",    # Annual interest rate
            "Maturity_Date",        # YYYY-MM-DD
            "Covenant_Debt_EBITDA", # Maximum allowed Debt/EBITDA ratio
            "Covenant_Actual",      # Actual Debt/EBITDA at this date
            "Is_Covenant_Breach",   # TRUE / FALSE
        ],
    },
}


# ============================================================
# FACT TABLES — DETAILED (2 files)
# ============================================================

facts_detailed = {

    "fact_sales_detail.csv": {
        "description": "Transaction-level sales — for Pareto, seasonality, price analysis",
        "columns": [
            "Transaction_ID",       # TXN000001, TXN000002, ...
            "Date_Key",             # 202001 (month key for joining)
            "Transaction_Date",     # 2020-01-15 (actual date for daily granularity)
            "Division_ID",          # DIV01, DIV02, DIV03
            "Product_Group_ID",     # PG01, PG02, ...
            "Region_ID",            # REG01, REG02, ...
            "Customer_Segment_ID",  # SEG01, SEG02, ...
            "Customer_ID",          # CUST0001, CUST0002, ... (for Pareto analysis)
            "Quantity",             # Units in this transaction
            "Unit_Price_EUR",       # List price per unit
            "Discount_Pct",        # Discount applied (0-25%)
            "Net_Revenue_EUR",      # Quantity * Unit_Price * (1 - Discount)
        ],
    },

    "fact_cogs_detail.csv": {
        "description": "COGS breakdown — for root cause analysis of margin changes",
        "columns": [
            "Date_Key",             # 202001, 202002, ...
            "Scenario_ID",          # ACT / BUD
            "Division_ID",          # DIV01, DIV02, DIV03
            "Product_Group_ID",     # PG01, PG02, ...
            "Cost_Component",       # Raw_Materials / Direct_Labor / Manufacturing_Overhead / Freight / Inventory_Writedown
            "Material_Type",        # e.g. "Polymers", "Steel", "Electronics", NULL (for non-material costs)
            "Quantity_Used",        # Units/kg/hours consumed
            "Unit_Cost_EUR",        # Cost per unit of input
            "Amount_EUR",           # Total cost = Quantity_Used * Unit_Cost_EUR
        ],
    },
}


# ============================================================
# SCRIPT EXECUTION
# ============================================================

def main():
    """Create all CSV files with headers only."""

    # Create output directory if it doesn't exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    all_tables = {}
    all_tables.update(dimensions)
    all_tables.update(facts_aggregated)
    all_tables.update(facts_detailed)

    print("=" * 60)
    print("TechniCon Manufacturing GmbH — Structure Generator v2")
    print("=" * 60)
    print(f"\nOutput: {OUTPUT_DIR}")
    print(f"Files to create: {len(all_tables)}")
    print()

    # Group for display
    groups = [
        ("DIMENSIONS", dimensions),
        ("FACTS — Aggregated", facts_aggregated),
        ("FACTS — Detailed", facts_detailed),
    ]

    created = 0
    for group_name, tables in groups:
        print(f"--- {group_name} ---")
        for filename, spec in tables.items():
            filepath = os.path.join(OUTPUT_DIR, filename)
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(spec["columns"])
            col_count = len(spec["columns"])
            print(f"  [OK] {filename:<30s} ({col_count} columns) — {spec['description']}")
            created += 1
        print()

    print("=" * 60)
    print(f"Done! Created {created} files.")
    print()
    print("NOT created (Power BI will generate these):")
    print("  - dim_calendar     (DAX CALENDARAUTO)")
    print("  - dim_division     (lookup table)")
    print("  - dim_region       (lookup table)")
    print("  - dim_scenario     (lookup table)")
    print()
    print("Next step: generate mock data with create_data.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
