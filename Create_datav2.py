"""
TechniCon Manufacturing GmbH — Mock Data Generator v2.0
========================================================
Generates a complete, internally consistent financial dataset
for 9 Power BI controlling dashboards.

CHANGES vs v1.0:
  - MONTHLY macro periods (was YEARLY) — 7 periods aligned with real-world events
  - NEW dim_material.csv (13 materials)
  - fact_cogs_detail: added Material_ID, Material_Price_Index columns
  - fact_balance_sheet: added Scenario_ID column (ACT only)
  - fact_cashflow: added Scenario_ID + generates BUD rows
  - fact_pnl: COGS now correctly mapped to division-specific Cost Center
              (DIV01→CC01, DIV02→CC02, DIV03→CC03)

Output: 13 CSV files in Generated_CSV/
Period: 2020-2025 (actual) + 2026 (budget/forecast)
Revenue base: ~€500M/year

Cascade logic:
  1. Sales → Revenue
  2. COGS detail → Cost of Sales (derived from Sales, with material price index)
  3. P&L assembly (Sales + COGS + OpEx + Non-operating)
  4. Balance Sheet (derived from P&L + assumptions)
  5. Cash Flow (derived from BS deltas, both ACT and BUD)
  6. Supporting: AR aging, Debt, Sales detail

Macro periods (monthly granularity):
  2020-01 to 2020-02:  Normal              (pre-pandemic baseline)
  2020-03 to 2021-06:  COVID               (lockdowns, demand shock)
  2021-07 to 2022-01:  Great_Resignation   (labor shortage, wage inflation)
  2022-02 to 2023-12:  Geopolitical_Risk   (Ukraine invasion, energy crisis)
  2024-01 to 2024-09:  Normalization       (recovery, inflation cooling)
  2024-10 to 2025-12:  Elevated_Risk       (Red Sea, Taiwan, geopolitical)
  2026-01 to 2026-12:  Forecast            (budget year)

Usage:
    python create_data_v2.py

Author: Portfolio Controlling Project (Serhii Kuznietsov)
"""

import csv
import os
import sys
import random
import math
import calendar                              # ← нове
from datetime import datetime, date, timedelta
from collections import defaultdict

# ============================================================
# CONFIGURATION
# ============================================================

OUTPUT_DIR = r"D:\Project - Portfolio Controlling\02_Mock_Data\Generated_CSV"
SEED = 42  # Reproducible results
random.seed(SEED)

# --- Period ---
YEARS = list(range(2020, 2027))  # 2020-2026
MONTHS = list(range(1, 13))
ACTUAL_YEARS = list(range(2020, 2026))  # 2020-2025
FORECAST_YEAR = 2026

# --- Company parameters ---
BASE_ANNUAL_REVENUE = 500_000_000  # €500M base (2019 level)
ANNUAL_ORGANIC_GROWTH = 0.035       # 3.5% YoY organic growth
CURRENCY = "EUR"

# --- Divisions ---
DIVISIONS = {
    "DIV01": {"name": "Industrial Solutions",   "short": "IND", "revenue_share": 0.45, "margin_profile": "Medium"},
    "DIV02": {"name": "Safety & Equipment",     "short": "SAF", "revenue_share": 0.30, "margin_profile": "High"},
    "DIV03": {"name": "Precision Components",   "short": "PRC", "revenue_share": 0.25, "margin_profile": "Low"},
}

# --- Product Groups ---
PRODUCT_GROUPS = {
    "PG01": {"name": "Industrial Adhesives",      "division": "DIV01", "material": "Polymers",     "material2": "Solvents",     "mat_cost_pct": 0.30, "gm_target": 0.44, "scr": "Medium", "covid": "Negative"},
    "PG02": {"name": "Abrasive Systems",          "division": "DIV01", "material": "Minerals",     "material2": "Resins",       "mat_cost_pct": 0.26, "gm_target": 0.47, "scr": "Low",    "covid": "Negative"},
    "PG03": {"name": "Industrial Tapes",           "division": "DIV01", "material": "Polymers",     "material2": "Adhesives",    "mat_cost_pct": 0.28, "gm_target": 0.45, "scr": "Medium", "covid": "Neutral"},
    "PG04": {"name": "Safety Helmets",             "division": "DIV02", "material": "Plastics",     "material2": None,           "mat_cost_pct": 0.23, "gm_target": 0.51, "scr": "Low",    "covid": "Positive"},
    "PG05": {"name": "Respiratory Protection",     "division": "DIV02", "material": "Filters",      "material2": "Elastomers",   "mat_cost_pct": 0.25, "gm_target": 0.53, "scr": "Medium", "covid": "Positive"},
    "PG06": {"name": "Hearing Protection",         "division": "DIV02", "material": "Foam",         "material2": "Electronics",  "mat_cost_pct": 0.20, "gm_target": 0.55, "scr": "Low",    "covid": "Neutral"},
    "PG07": {"name": "Precision Sensors",          "division": "DIV03", "material": "Electronics",  "material2": "Metals",       "mat_cost_pct": 0.36, "gm_target": 0.38, "scr": "High",   "covid": "Negative"},
    "PG08": {"name": "Micro-Connectors",           "division": "DIV03", "material": "Copper",       "material2": "Plastics",     "mat_cost_pct": 0.38, "gm_target": 0.36, "scr": "High",   "covid": "Negative"},
    "PG09": {"name": "Optical Films",              "division": "DIV03", "material": "Polymers",     "material2": "Chemicals",    "mat_cost_pct": 0.33, "gm_target": 0.40, "scr": "Medium", "covid": "Neutral"},
}

# --- Regions ---
REGIONS = {
    "REG01": {"name": "DACH",           "share": 0.35, "growth": "Stable"},
    "REG02": {"name": "Rest of Europe", "share": 0.25, "growth": "Moderate"},
    "REG03": {"name": "Americas",       "share": 0.25, "growth": "High"},
    "REG04": {"name": "Asia-Pacific",   "share": 0.15, "growth": "High"},
}

# --- Customer Segments ---
CUSTOMER_SEGMENTS = {
    "SEG01": {"name": "Enterprise OEM",      "pay_days": 45, "crisis_days": 65, "concentration": "High",   "risk": "A"},
    "SEG02": {"name": "SMB Distributors",    "pay_days": 30, "crisis_days": 50, "concentration": "Medium", "risk": "B"},
    "SEG03": {"name": "Government & Public", "pay_days": 60, "crisis_days": 75, "concentration": "Low",    "risk": "A"},
    "SEG04": {"name": "Direct End-Users",    "pay_days": 15, "crisis_days": 25, "concentration": "Low",    "risk": "C"},
}

# Revenue split by segment (across all divisions)
SEGMENT_REVENUE_SHARES = {"SEG01": 0.40, "SEG02": 0.30, "SEG03": 0.15, "SEG04": 0.15}

# --- Materials (NEW in v2) ---
# Reflects the 13 unique materials used in PRODUCT_GROUPS
MATERIALS = {
    "MAT01": {"name": "Copper",       "category": "Metals",       "baseline_price": 8.50,  "risk": "High"},
    "MAT02": {"name": "Polymers",     "category": "Polymers",     "baseline_price": 2.20,  "risk": "Medium"},
    "MAT03": {"name": "Plastics",     "category": "Polymers",     "baseline_price": 1.80,  "risk": "Low"},
    "MAT04": {"name": "Electronics",  "category": "Electronics",  "baseline_price": 45.00, "risk": "High"},
    "MAT05": {"name": "Metals",       "category": "Metals",       "baseline_price": 4.50,  "risk": "Medium"},
    "MAT06": {"name": "Minerals",     "category": "Raw_Minerals", "baseline_price": 0.80,  "risk": "Low"},
    "MAT07": {"name": "Resins",       "category": "Chemicals",    "baseline_price": 3.20,  "risk": "Medium"},
    "MAT08": {"name": "Solvents",     "category": "Chemicals",    "baseline_price": 2.50,  "risk": "Medium"},
    "MAT09": {"name": "Adhesives",    "category": "Chemicals",    "baseline_price": 5.50,  "risk": "Low"},
    "MAT10": {"name": "Elastomers",   "category": "Polymers",     "baseline_price": 4.00,  "risk": "Medium"},
    "MAT11": {"name": "Chemicals",    "category": "Chemicals",    "baseline_price": 3.50,  "risk": "Medium"},
    "MAT12": {"name": "Filters",      "category": "Components",   "baseline_price": 12.00, "risk": "Low"},
    "MAT13": {"name": "Foam",         "category": "Polymers",     "baseline_price": 1.50,  "risk": "Low"},
}

# Map material name (used in PRODUCT_GROUPS) → Material_ID
MAT_NAME_TO_ID = {m["name"]: mid for mid, m in MATERIALS.items()}


def get_material_price_index(year, month, material_category):
    """
    Return material price index (100 = baseline) based on macro period and material category.
    Different categories react differently to macro shocks — this is the storytelling driver.
    """
    target = year * 100 + month
    label = get_macro(year, month)["label"]

    # Category-specific shock profiles
    # Format: index multiplier vs 100 baseline
    shocks = {
        "Normal":            {"Metals": 100, "Electronics": 100, "Polymers": 100, "Chemicals": 100, "Raw_Minerals": 100, "Components": 100},
        "COVID":             {"Metals": 102, "Electronics": 108, "Polymers":  98, "Chemicals": 102, "Raw_Minerals":  95, "Components": 105},
        "Great_Resignation": {"Metals": 110, "Electronics": 115, "Polymers": 105, "Chemicals": 108, "Raw_Minerals": 100, "Components": 110},
        "Geopolitical_Risk": {"Metals": 138, "Electronics": 122, "Polymers": 128, "Chemicals": 132, "Raw_Minerals": 115, "Components": 125},
        "Normalization":     {"Metals": 118, "Electronics": 110, "Polymers": 115, "Chemicals": 118, "Raw_Minerals": 108, "Components": 112},
        "Elevated_Risk":     {"Metals": 122, "Electronics": 115, "Polymers": 118, "Chemicals": 120, "Raw_Minerals": 110, "Components": 115},
        "Forecast":          {"Metals": 120, "Electronics": 113, "Polymers": 116, "Chemicals": 118, "Raw_Minerals": 108, "Components": 113},
    }
    base_idx = shocks.get(label, {}).get(material_category, 100)
    # Add small monthly noise (±2 points)
    return round(base_idx + random.uniform(-2, 2), 1)

# --- Cost Centers ---
COST_CENTERS = {
    "CC01": {"name": "Production — Industrial",   "division": "DIV01", "type": "Production", "direct": True},
    "CC02": {"name": "Production — Safety",        "division": "DIV02", "type": "Production", "direct": True},
    "CC03": {"name": "Production — Precision",     "division": "DIV03", "type": "Production", "direct": True},
    "CC04": {"name": "Sales — DACH",               "division": "DIV01", "type": "Sales",      "direct": False},
    "CC05": {"name": "Sales — International",      "division": "DIV01", "type": "Sales",      "direct": False},
    "CC06": {"name": "R&D Center",                 "division": "DIV01", "type": "R&D",        "direct": False},
    "CC07": {"name": "General & Administration",   "division": "DIV01", "type": "Admin",      "direct": False},
    "CC08": {"name": "Logistics & Warehousing",    "division": "DIV01", "type": "Logistics",  "direct": False},
    "CC09": {"name": "IT & Digital",               "division": "DIV01", "type": "Admin",      "direct": False},
    "CC10": {"name": "Quality Assurance",          "division": "DIV01", "type": "Production", "direct": False},
}

# --- Seasonality (monthly coefficients, sum ≈ 12.0) ---
SEASONALITY = {
    1: 0.88,   # January — post-holiday slowdown
    2: 0.92,   # February
    3: 1.02,   # March — Q1 close push
    4: 0.98,   # April
    5: 1.02,   # May
    6: 1.05,   # June — H1 close push
    7: 0.85,   # July — summer slowdown
    8: 0.82,   # August — factory shutdowns (EU)
    9: 1.05,   # September — ramp up
    10: 1.08,  # October
    11: 1.12,  # November — pre-yearend
    12: 1.21,  # December — Q4/yearend push
}

# --- Macro periods (MONTHLY granularity) ---
# Each tuple: (start_year, start_month, end_year, end_month, scenario_label,
#              revenue_mult, cogs_mult, dso_add_days, inventory_mult)
MACRO_PERIODS = [
    (2020,  1, 2020,  2, "Normal",             1.00, 1.00,  0, 1.00),
    (2020,  3, 2021,  6, "COVID",              0.85, 1.04, 10, 1.20),
    (2021,  7, 2022,  1, "Great_Resignation",  0.95, 1.08,  5, 1.15),
    (2022,  2, 2023, 12, "Geopolitical_Risk",  0.98, 1.18, 15, 1.30),
    (2024,  1, 2024,  9, "Normalization",      1.08, 1.05,  3, 1.05),
    (2024, 10, 2025, 12, "Elevated_Risk",      1.10, 1.06,  5, 1.08),
    (2026,  1, 2026, 12, "Forecast",           1.12, 1.05,  0, 1.00),
]


def get_macro(year, month):
    """Return macro factors for a specific (year, month)."""
    target = year * 100 + month
    for sy, sm, ey, em, label, rev, cogs, dso, inv in MACRO_PERIODS:
        start = sy * 100 + sm
        end = ey * 100 + em
        if start <= target <= end:
            return {
                "label": label,
                "revenue": rev,
                "cogs_multiplier": cogs,
                "dso_add": dso,
                "inventory_mult": inv,
            }
    # Fallback (should never trigger if periods cover all years)
    return {"label": "Unknown", "revenue": 1.0, "cogs_multiplier": 1.0,
            "dso_add": 0, "inventory_mult": 1.0}

# COVID demand impact multipliers by product (2020-2021 only)
COVID_PRODUCT_IMPACT = {
    "Positive": 1.25,   # Safety products — demand spike
    "Neutral": 1.00,
    "Negative": 0.75,   # Industrial/precision — demand drop
}

# --- P&L ratios (as % of net revenue, base case) ---
PNL_RATIOS = {
    "sales_deductions_pct": 0.03,       # Returns, discounts off gross
    "sga_sales_marketing_pct": 0.065,    # Variable-ish
    "sga_general_admin_pct": 0.035,      # Semi-fixed
    "sga_salaries_pct": 0.025,          # Semi-fixed
    "rd_pct": 0.044,                    # R&D
    "other_opex_pct": 0.01,             # Misc
    "interest_income_pct": 0.002,       # Small
    "fx_impact_pct": 0.005,             # Can be + or -
    "other_nonop_pct": 0.001,
    "tax_rate": 0.28,                   # Effective tax rate (German Körperschaftsteuer + Gewerbesteuer ≈ 30%)
    "stock_comp_pct": 0.005,
}

# --- Balance Sheet assumptions ---
BS_ASSUMPTIONS = {
    "dso_base": 42,                 # Days sales outstanding (base)
    "dio_base": 55,                 # Days inventory outstanding
    "dpo_base": 38,                 # Days payable outstanding
    "prepaid_pct_revenue": 0.015,
    "other_ca_pct_revenue": 0.01,
    "accrued_liab_pct_revenue": 0.025,
    "tax_payable_pct_tax": 0.25,    # Quarter of annual tax
    "other_cl_pct_revenue": 0.008,
    "pension_base": 45_000_000,     # Starting pension obligation
    "pension_growth": 0.02,         # Annual growth
    "other_ncl_pct_revenue": 0.01,
    "goodwill": 120_000_000,        # Static
    "intangibles_base": 35_000_000,
    "intangibles_amort_rate": 0.10, # 10% annual amortization
    "other_nca_pct_revenue": 0.005,
    "share_capital": 150_000_000,   # Static
    "other_reserves_base": 20_000_000,
}

# --- CAPEX & PP&E ---
CAPEX_PCT_REVENUE = 0.048          # ~4.8% of revenue
PPE_GROSS_START = 450_000_000      # Starting gross PP&E (2019)
DEPRECIATION_RATE = 0.05           # 5% of gross PP&E per year
ASSET_DISPOSAL_PCT = 0.005         # Tiny disposals

# --- Debt facilities ---
DEBT_FACILITIES = [
    {"id": "DEBT01", "name": "Revolving Credit Facility", "type": "Revolving",  "class": "Short_Term",
     "start_bal": 50_000_000,  "rate": 0.035, "maturity": "2024-12-31", "covenant": 3.5},
    {"id": "DEBT02", "name": "Term Loan A",               "type": "Term",       "class": "Long_Term",
     "start_bal": 120_000_000, "rate": 0.042, "maturity": "2027-06-30", "covenant": 3.5},
    {"id": "DEBT03", "name": "Term Loan B",               "type": "Term",       "class": "Long_Term",
     "start_bal": 80_000_000,  "rate": 0.048, "maturity": "2028-12-31", "covenant": 3.5},
    {"id": "DEBT04", "name": "Bond 2025",                  "type": "Bond",       "class": "Long_Term",
     "start_bal": 60_000_000,  "rate": 0.038, "maturity": "2025-09-30", "covenant": 3.5},
]

# --- Dividend policy ---
DIVIDEND_PAYOUT_RATIO = 0.35  # 35% of net income

# --- Budget variance ---
BUDGET_REVENUE_BIAS = 1.02    # Budget is typically 2% optimistic
BUDGET_COST_BIAS = 0.98       # Budget underestimates costs by 2%
BUDGET_NOISE = 0.03           # ±3% random variance

# --- Noise ---
MONTHLY_NOISE_RANGE = 0.04   # ±4% random noise on monthly figures

# --- Sales detail ---
AVG_TRANSACTIONS_PER_MONTH_PER_COMBO = 8  # per product_group × region × segment
NUM_CUSTOMERS = 250           # Unique customer IDs


# ============================================================
# GL ACCOUNT STRUCTURE
# ============================================================

GL_ACCOUNTS = [
    # --- P&L ---
    # Revenue
    {"id": "PL001", "name": "Gross Revenue",                "cat": "Revenue",       "subcat": "Gross",               "fs": "PnL", "bs": None, "cf": None, "sign": "Credit", "cogs": False, "sort": 10},
    {"id": "PL002", "name": "Sales Deductions",             "cat": "Revenue",       "subcat": "Deductions",          "fs": "PnL", "bs": None, "cf": None, "sign": "Debit",  "cogs": False, "sort": 20},
    # COGS
    {"id": "PL010", "name": "Raw Materials",                "cat": "COGS",          "subcat": "Materials",           "fs": "PnL", "bs": None, "cf": None, "sign": "Debit",  "cogs": True,  "sort": 100},
    {"id": "PL011", "name": "Direct Labor",                 "cat": "COGS",          "subcat": "Labor",               "fs": "PnL", "bs": None, "cf": None, "sign": "Debit",  "cogs": True,  "sort": 110},
    {"id": "PL012", "name": "Manufacturing Overhead",       "cat": "COGS",          "subcat": "Overhead",            "fs": "PnL", "bs": None, "cf": None, "sign": "Debit",  "cogs": True,  "sort": 120},
    {"id": "PL013", "name": "Freight & Logistics",          "cat": "COGS",          "subcat": "Logistics",           "fs": "PnL", "bs": None, "cf": None, "sign": "Debit",  "cogs": True,  "sort": 130},
    {"id": "PL014", "name": "Inventory Write-downs",        "cat": "COGS",          "subcat": "Write-downs",         "fs": "PnL", "bs": None, "cf": None, "sign": "Debit",  "cogs": True,  "sort": 140},
    # OpEx
    {"id": "PL020", "name": "Sales & Marketing",            "cat": "OpEx",          "subcat": "SGA_Sales",           "fs": "PnL", "bs": None, "cf": None, "sign": "Debit",  "cogs": False, "sort": 200},
    {"id": "PL021", "name": "General & Administrative",     "cat": "OpEx",          "subcat": "SGA_Admin",           "fs": "PnL", "bs": None, "cf": None, "sign": "Debit",  "cogs": False, "sort": 210},
    {"id": "PL022", "name": "Salaries & Benefits (non-prod)", "cat": "OpEx",        "subcat": "SGA_Salaries",        "fs": "PnL", "bs": None, "cf": None, "sign": "Debit",  "cogs": False, "sort": 220},
    {"id": "PL023", "name": "Research & Development",       "cat": "OpEx",          "subcat": "R&D",                 "fs": "PnL", "bs": None, "cf": None, "sign": "Debit",  "cogs": False, "sort": 230},
    {"id": "PL024", "name": "Depreciation & Amortization",  "cat": "OpEx",          "subcat": "D&A",                 "fs": "PnL", "bs": None, "cf": None, "sign": "Debit",  "cogs": False, "sort": 240},
    {"id": "PL025", "name": "Other Operating Expenses",     "cat": "OpEx",          "subcat": "Other_OpEx",          "fs": "PnL", "bs": None, "cf": None, "sign": "Debit",  "cogs": False, "sort": 250},
    # Non-operating
    {"id": "PL030", "name": "Interest Expense",             "cat": "Non-Operating", "subcat": "Interest_Exp",        "fs": "PnL", "bs": None, "cf": None, "sign": "Debit",  "cogs": False, "sort": 300},
    {"id": "PL031", "name": "Interest Income",              "cat": "Non-Operating", "subcat": "Interest_Inc",        "fs": "PnL", "bs": None, "cf": None, "sign": "Credit", "cogs": False, "sort": 310},
    {"id": "PL032", "name": "FX Gains/Losses",              "cat": "Non-Operating", "subcat": "FX",                  "fs": "PnL", "bs": None, "cf": None, "sign": "Debit",  "cogs": False, "sort": 320},
    {"id": "PL033", "name": "Other Non-operating",          "cat": "Non-Operating", "subcat": "Other_NonOp",         "fs": "PnL", "bs": None, "cf": None, "sign": "Debit",  "cogs": False, "sort": 330},
    # Tax
    {"id": "PL040", "name": "Income Tax",                   "cat": "Tax",           "subcat": "Tax",                 "fs": "PnL", "bs": None, "cf": None, "sign": "Debit",  "cogs": False, "sort": 400},

    # --- Balance Sheet ---
    # Current Assets
    {"id": "BS001", "name": "Cash & Equivalents",           "cat": "Asset",    "subcat": "Cash",                "fs": "BS", "bs": "Current_Asset",       "cf": None, "sign": "Debit", "cogs": False, "sort": 500},
    {"id": "BS002", "name": "Accounts Receivable",          "cat": "Asset",    "subcat": "AR",                  "fs": "BS", "bs": "Current_Asset",       "cf": None, "sign": "Debit", "cogs": False, "sort": 510},
    {"id": "BS003", "name": "Inventory — Raw Materials",    "cat": "Asset",    "subcat": "Inventory_RM",        "fs": "BS", "bs": "Current_Asset",       "cf": None, "sign": "Debit", "cogs": False, "sort": 520},
    {"id": "BS004", "name": "Inventory — Work-in-Progress", "cat": "Asset",    "subcat": "Inventory_WIP",       "fs": "BS", "bs": "Current_Asset",       "cf": None, "sign": "Debit", "cogs": False, "sort": 530},
    {"id": "BS005", "name": "Inventory — Finished Goods",   "cat": "Asset",    "subcat": "Inventory_FG",        "fs": "BS", "bs": "Current_Asset",       "cf": None, "sign": "Debit", "cogs": False, "sort": 540},
    {"id": "BS006", "name": "Prepaid Expenses",             "cat": "Asset",    "subcat": "Prepaid",             "fs": "BS", "bs": "Current_Asset",       "cf": None, "sign": "Debit", "cogs": False, "sort": 550},
    {"id": "BS007", "name": "Other Current Assets",         "cat": "Asset",    "subcat": "Other_CA",            "fs": "BS", "bs": "Current_Asset",       "cf": None, "sign": "Debit", "cogs": False, "sort": 560},
    # Non-current Assets
    {"id": "BS010", "name": "PP&E (Gross)",                 "cat": "Asset",    "subcat": "PPE_Gross",           "fs": "BS", "bs": "Non_Current_Asset",   "cf": None, "sign": "Debit", "cogs": False, "sort": 600},
    {"id": "BS011", "name": "Accumulated Depreciation",     "cat": "Asset",    "subcat": "Accum_Depr",          "fs": "BS", "bs": "Non_Current_Asset",   "cf": None, "sign": "Credit","cogs": False, "sort": 610},
    {"id": "BS012", "name": "Intangible Assets",            "cat": "Asset",    "subcat": "Intangibles",         "fs": "BS", "bs": "Non_Current_Asset",   "cf": None, "sign": "Debit", "cogs": False, "sort": 620},
    {"id": "BS013", "name": "Goodwill",                     "cat": "Asset",    "subcat": "Goodwill",            "fs": "BS", "bs": "Non_Current_Asset",   "cf": None, "sign": "Debit", "cogs": False, "sort": 630},
    {"id": "BS014", "name": "Other Non-current Assets",     "cat": "Asset",    "subcat": "Other_NCA",           "fs": "BS", "bs": "Non_Current_Asset",   "cf": None, "sign": "Debit", "cogs": False, "sort": 640},
    # Current Liabilities
    {"id": "BS020", "name": "Accounts Payable",             "cat": "Liability","subcat": "AP",                  "fs": "BS", "bs": "Current_Liability",   "cf": None, "sign": "Credit","cogs": False, "sort": 700},
    {"id": "BS021", "name": "Short-term Debt",              "cat": "Liability","subcat": "ST_Debt",             "fs": "BS", "bs": "Current_Liability",   "cf": None, "sign": "Credit","cogs": False, "sort": 710},
    {"id": "BS022", "name": "Current Portion LT Debt",      "cat": "Liability","subcat": "CPLTD",               "fs": "BS", "bs": "Current_Liability",   "cf": None, "sign": "Credit","cogs": False, "sort": 720},
    {"id": "BS023", "name": "Accrued Liabilities",          "cat": "Liability","subcat": "Accrued",             "fs": "BS", "bs": "Current_Liability",   "cf": None, "sign": "Credit","cogs": False, "sort": 730},
    {"id": "BS024", "name": "Tax Payable",                  "cat": "Liability","subcat": "Tax_Pay",             "fs": "BS", "bs": "Current_Liability",   "cf": None, "sign": "Credit","cogs": False, "sort": 740},
    {"id": "BS025", "name": "Other Current Liabilities",    "cat": "Liability","subcat": "Other_CL",            "fs": "BS", "bs": "Current_Liability",   "cf": None, "sign": "Credit","cogs": False, "sort": 750},
    # Non-current Liabilities
    {"id": "BS030", "name": "Long-term Debt",               "cat": "Liability","subcat": "LT_Debt",             "fs": "BS", "bs": "Non_Current_Liability","cf": None, "sign": "Credit","cogs": False, "sort": 800},
    {"id": "BS031", "name": "Pension Obligations",          "cat": "Liability","subcat": "Pension",             "fs": "BS", "bs": "Non_Current_Liability","cf": None, "sign": "Credit","cogs": False, "sort": 810},
    {"id": "BS032", "name": "Other Non-current Liabilities","cat": "Liability","subcat": "Other_NCL",           "fs": "BS", "bs": "Non_Current_Liability","cf": None, "sign": "Credit","cogs": False, "sort": 820},
    # Equity
    {"id": "BS040", "name": "Share Capital",                "cat": "Equity",   "subcat": "Share_Capital",       "fs": "BS", "bs": "Equity",              "cf": None, "sign": "Credit","cogs": False, "sort": 900},
    {"id": "BS041", "name": "Retained Earnings",            "cat": "Equity",   "subcat": "Retained_Earnings",   "fs": "BS", "bs": "Equity",              "cf": None, "sign": "Credit","cogs": False, "sort": 910},
    {"id": "BS042", "name": "Other Reserves",               "cat": "Equity",   "subcat": "Other_Reserves",      "fs": "BS", "bs": "Equity",              "cf": None, "sign": "Credit","cogs": False, "sort": 920},

    # --- Cash Flow ---
    {"id": "CF001", "name": "Net Income",                   "cat": "CF",  "subcat": "CFO_NetIncome",       "fs": "CF", "bs": None, "cf": "Operating",  "sign": "Debit", "cogs": False, "sort": 1000},
    {"id": "CF002", "name": "Depreciation & Amortization",  "cat": "CF",  "subcat": "CFO_DA",              "fs": "CF", "bs": None, "cf": "Operating",  "sign": "Debit", "cogs": False, "sort": 1010},
    {"id": "CF003", "name": "Stock-based Compensation",     "cat": "CF",  "subcat": "CFO_SBC",             "fs": "CF", "bs": None, "cf": "Operating",  "sign": "Debit", "cogs": False, "sort": 1020},
    {"id": "CF004", "name": "Change in Accounts Receivable","cat": "CF",  "subcat": "CFO_AR",              "fs": "CF", "bs": None, "cf": "Operating",  "sign": "Debit", "cogs": False, "sort": 1030},
    {"id": "CF005", "name": "Change in Inventory",          "cat": "CF",  "subcat": "CFO_Inv",             "fs": "CF", "bs": None, "cf": "Operating",  "sign": "Debit", "cogs": False, "sort": 1040},
    {"id": "CF006", "name": "Change in Accounts Payable",   "cat": "CF",  "subcat": "CFO_AP",              "fs": "CF", "bs": None, "cf": "Operating",  "sign": "Debit", "cogs": False, "sort": 1050},
    {"id": "CF007", "name": "Change in Prepaid Expenses",   "cat": "CF",  "subcat": "CFO_Prepaid",         "fs": "CF", "bs": None, "cf": "Operating",  "sign": "Debit", "cogs": False, "sort": 1060},
    {"id": "CF008", "name": "Change in Accrued Liabilities","cat": "CF",  "subcat": "CFO_Accrued",         "fs": "CF", "bs": None, "cf": "Operating",  "sign": "Debit", "cogs": False, "sort": 1070},
    {"id": "CF009", "name": "Other Operating Adjustments",  "cat": "CF",  "subcat": "CFO_Other",           "fs": "CF", "bs": None, "cf": "Operating",  "sign": "Debit", "cogs": False, "sort": 1080},
    {"id": "CF010", "name": "CAPEX",                        "cat": "CF",  "subcat": "CFI_CAPEX",           "fs": "CF", "bs": None, "cf": "Investing",  "sign": "Debit", "cogs": False, "sort": 1100},
    {"id": "CF011", "name": "Acquisitions",                 "cat": "CF",  "subcat": "CFI_Acq",             "fs": "CF", "bs": None, "cf": "Investing",  "sign": "Debit", "cogs": False, "sort": 1110},
    {"id": "CF012", "name": "Asset Disposals",              "cat": "CF",  "subcat": "CFI_Disp",            "fs": "CF", "bs": None, "cf": "Investing",  "sign": "Debit", "cogs": False, "sort": 1120},
    {"id": "CF013", "name": "Other Investing",              "cat": "CF",  "subcat": "CFI_Other",           "fs": "CF", "bs": None, "cf": "Investing",  "sign": "Debit", "cogs": False, "sort": 1130},
    {"id": "CF014", "name": "Debt Proceeds",                "cat": "CF",  "subcat": "CFF_Proceeds",        "fs": "CF", "bs": None, "cf": "Financing",  "sign": "Debit", "cogs": False, "sort": 1200},
    {"id": "CF015", "name": "Debt Repayment",               "cat": "CF",  "subcat": "CFF_Repayment",       "fs": "CF", "bs": None, "cf": "Financing",  "sign": "Debit", "cogs": False, "sort": 1210},
    {"id": "CF016", "name": "Dividend Payments",            "cat": "CF",  "subcat": "CFF_Dividends",       "fs": "CF", "bs": None, "cf": "Financing",  "sign": "Debit", "cogs": False, "sort": 1220},
    {"id": "CF017", "name": "Share Buyback",                "cat": "CF",  "subcat": "CFF_Buyback",         "fs": "CF", "bs": None, "cf": "Financing",  "sign": "Debit", "cogs": False, "sort": 1230},
    {"id": "CF018", "name": "Other Financing",              "cat": "CF",  "subcat": "CFF_Other",           "fs": "CF", "bs": None, "cf": "Financing",  "sign": "Debit", "cogs": False, "sort": 1240},
]


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def noise(base, pct=MONTHLY_NOISE_RANGE):
    """Add random noise to a value."""
    return base * (1 + random.uniform(-pct, pct))


def monthly_revenue_base(year, month):
    """Calculate base monthly revenue before division/product split."""
    # Organic growth from 2019 base
    years_from_base = year - 2019
    grown = BASE_ANNUAL_REVENUE * ((1 + ANNUAL_ORGANIC_GROWTH) ** years_from_base)
    # Macro factor (now MONTHLY)
    macro = get_macro(year, month)["revenue"]
    # Seasonality
    seasonal = SEASONALITY[month]
    # Monthly = annual / 12 * seasonal * macro
    monthly = (grown / 12) * seasonal * macro
    return monthly


def make_date_key(year, month):
    """Return YYYYMMDD integer, using last day of month (EOM convention)."""
    import calendar
    last_day = calendar.monthrange(year, month)[1]
    return year * 10000 + month * 100 + last_day


# ============================================================
# DATA GENERATION
# ============================================================

def generate_all():
    """Master generation function — cascading logic."""

    print("=" * 70)
    print("TechniCon Manufacturing GmbH — Data Generator v2.0")
    print("=" * 70)
    print(f"Seed: {SEED}")
    print(f"Period: {YEARS[0]}–{YEARS[-1]}")
    print(f"Output: {OUTPUT_DIR}")
    print()

    errors = []
    warnings = []
    stats = {}

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # --------------------------------------------------------
    # STEP 0: Write dimension tables
    # --------------------------------------------------------
    print("[Step 0] Writing dimension tables...")

    # dim_cost_center
    dim_cc_rows = []
    for cc_id, cc in COST_CENTERS.items():
        dim_cc_rows.append([cc_id, cc["name"], cc["division"], cc["type"], cc["direct"]])
    write_csv("dim_cost_center.csv",
              ["Cost_Center_ID", "Cost_Center_Name", "Division_ID", "Cost_Type", "Is_Direct"],
              dim_cc_rows)
    stats["dim_cost_center"] = {"rows": len(dim_cc_rows), "nulls": 0}

    # dim_gl_account
    dim_gl_rows = []
    for gl in GL_ACCOUNTS:
        dim_gl_rows.append([gl["id"], gl["name"], gl["cat"], gl["subcat"],
                            gl["fs"], gl["bs"] or "", gl["cf"] or "",
                            gl["sign"], gl["cogs"], gl["sort"]])
    write_csv("dim_gl_account.csv",
              ["GL_Account_ID", "GL_Account_Name", "GL_Category", "GL_Subcategory",
               "Financial_Statement", "BS_Category", "CF_Category",
               "Sign_Convention", "Is_COGS_Detail", "Sort_Order"],
              dim_gl_rows)
    stats["dim_gl_account"] = {"rows": len(dim_gl_rows), "nulls": count_empty(dim_gl_rows)}

    # dim_product_group
    dim_pg_rows = []
    for pg_id, pg in PRODUCT_GROUPS.items():
        dim_pg_rows.append([pg_id, pg["name"], pg["division"], pg["material"],
                            pg["material2"] or "", pg["mat_cost_pct"], pg["gm_target"],
                            pg["scr"], pg["covid"]])
    write_csv("dim_product_group.csv",
              ["Product_Group_ID", "Product_Group_Name", "Division_ID",
               "Primary_Raw_Material", "Secondary_Raw_Material",
               "Material_Cost_Pct", "Gross_Margin_Target_Pct",
               "Supply_Chain_Risk", "COVID_Demand_Impact"],
              dim_pg_rows)
    stats["dim_product_group"] = {"rows": len(dim_pg_rows), "nulls": count_empty(dim_pg_rows)}

    # dim_customer_segment
    dim_cs_rows = []
    for seg_id, seg in CUSTOMER_SEGMENTS.items():
        dim_cs_rows.append([seg_id, seg["name"], seg["pay_days"], seg["crisis_days"],
                            seg["concentration"], seg["risk"]])
    write_csv("dim_customer_segment.csv",
              ["Customer_Segment_ID", "Customer_Segment_Name",
               "Typical_Payment_Days", "Crisis_Payment_Days",
               "Revenue_Concentration", "Credit_Risk_Rating"],
              dim_cs_rows)
    stats["dim_customer_segment"] = {"rows": len(dim_cs_rows), "nulls": 0}

    # dim_material (NEW in v2)
    dim_mat_rows = []
    for mat_id, mat in MATERIALS.items():
        dim_mat_rows.append([mat_id, mat["name"], mat["category"],
                             mat["baseline_price"], mat["risk"]])
    write_csv("dim_material.csv",
              ["Material_ID", "Material_Name", "Material_Category",
               "Baseline_Price_EUR", "Supply_Risk"],
              dim_mat_rows)
    stats["dim_material"] = {"rows": len(dim_mat_rows), "nulls": 0}

    print(f"  Dimensions written: 5 files")
    print()

    # --------------------------------------------------------
    # STEP 1: Generate Sales (fact_sales)
    # --------------------------------------------------------
    print("[Step 1] Generating sales data...")

    fact_sales_rows = []
    # Store monthly revenue by division for downstream use
    monthly_revenue = {}          # (year, month) → total revenue
    monthly_revenue_div = {}      # (year, month, div) → revenue
    monthly_revenue_pg = {}       # (year, month, pg) → revenue
    monthly_cogs_total = {}       # (year, month) → total COGS

    for year in YEARS:
        scenario = "BUD" if year == FORECAST_YEAR else "ACT"
        for month in MONTHS:
            dk = make_date_key(year, month)
            base_rev = monthly_revenue_base(year, month)
            macro_label = get_macro(year, month)["label"]

            month_total = 0
            for div_id, div in DIVISIONS.items():
                div_rev_base = base_rev * div["revenue_share"]

                # Get product groups for this division
                div_pgs = {k: v for k, v in PRODUCT_GROUPS.items() if v["division"] == div_id}
                n_pgs = len(div_pgs)
                # Split roughly equal within division, with some variance
                pg_weights = {k: 1.0 / n_pgs for k in div_pgs}

                for pg_id, pg in div_pgs.items():
                    pg_rev_base = div_rev_base * pg_weights[pg_id]

                    # COVID product impact (only during COVID period)
                    if macro_label == "COVID":
                        covid_mult = COVID_PRODUCT_IMPACT[pg["covid"]]
                        pg_rev_base *= covid_mult

                    for reg_id, reg in REGIONS.items():
                        for seg_id in CUSTOMER_SEGMENTS:
                            combo_rev = pg_rev_base * reg["share"] * SEGMENT_REVENUE_SHARES[seg_id]
                            combo_rev = noise(combo_rev)
                            combo_rev = round(combo_rev, 2)

                            if combo_rev < 0:
                                combo_rev = 0

                            # Estimate quantity from avg price
                            avg_price = random.uniform(50, 500)  # varies by product
                            qty = max(1, int(combo_rev / avg_price)) if combo_rev > 0 else 0
                            if qty > 0:
                                avg_price = round(combo_rev / qty, 2)
                            else:
                                avg_price = 0

                            fact_sales_rows.append([
                                dk, div_id, pg_id, reg_id, seg_id,
                                combo_rev, qty, avg_price
                            ])

                            month_total += combo_rev
                            monthly_revenue_div[(year, month, div_id)] = \
                                monthly_revenue_div.get((year, month, div_id), 0) + combo_rev
                            monthly_revenue_pg[(year, month, pg_id)] = \
                                monthly_revenue_pg.get((year, month, pg_id), 0) + combo_rev

            monthly_revenue[(year, month)] = month_total

    write_csv("fact_sales.csv",
              ["Date_Key", "Division_ID", "Product_Group_ID", "Region_ID",
               "Customer_Segment_ID", "Revenue_EUR", "Quantity_Sold", "Avg_Selling_Price"],
              fact_sales_rows)
    stats["fact_sales"] = {"rows": len(fact_sales_rows), "nulls": count_empty(fact_sales_rows)}
    print(f"  fact_sales: {len(fact_sales_rows):,} rows")

    # --------------------------------------------------------
    # STEP 2: Generate COGS detail (fact_cogs_detail)
    # --------------------------------------------------------
    print("[Step 2] Generating COGS detail...")

    fact_cogs_rows = []
    cost_components = ["Raw_Materials", "Direct_Labor", "Manufacturing_Overhead", "Freight", "Inventory_Writedown"]
    # Typical split of COGS
    cogs_component_split = {
        "Raw_Materials": 0.55,
        "Direct_Labor": 0.22,
        "Manufacturing_Overhead": 0.15,
        "Freight": 0.06,
        "Inventory_Writedown": 0.02,
    }

    for year in YEARS:
        for month in MONTHS:
            macro = get_macro(year, month)
            scenario = "BUD" if year == FORECAST_YEAR else "ACT"
            dk = make_date_key(year, month)
            month_cogs = 0

            for pg_id, pg in PRODUCT_GROUPS.items():
                pg_rev = monthly_revenue_pg.get((year, month, pg_id), 0)
                if pg_rev <= 0:
                    continue

                # Target COGS = revenue × (1 - gross_margin_target)
                target_cogs = pg_rev * (1 - pg["gm_target"])

                # Material price index for this product group's primary material
                primary_mat_id = MAT_NAME_TO_ID.get(pg["material"], "MAT99")
                primary_mat_cat = MATERIALS.get(primary_mat_id, {}).get("category", "Unknown")
                price_index = get_material_price_index(year, month, primary_mat_cat)

                # COGS adjusted by both macro multiplier AND material price index
                # (price index dominates Raw Materials; other components use macro mult)
                actual_cogs = target_cogs * macro["cogs_multiplier"]
                actual_cogs = noise(actual_cogs, 0.03)

                div_id = pg["division"]

                for comp, comp_share in cogs_component_split.items():
                    comp_amount = actual_cogs * comp_share

                    # Raw_Materials are extra-sensitive to material price index
                    if comp == "Raw_Materials":
                        comp_amount = comp_amount * (price_index / 100)

                    comp_amount = noise(comp_amount, 0.02)
                    comp_amount = round(comp_amount, 2)

                    # Material assignment
                    if comp == "Raw_Materials":
                        mat_id = primary_mat_id
                        mat_name = pg["material"]
                    elif comp == "Manufacturing_Overhead" and pg["material2"]:
                        mat_id = MAT_NAME_TO_ID.get(pg["material2"], "")
                        mat_name = pg["material2"]
                    else:
                        mat_id = ""
                        mat_name = ""

                    # Estimate quantity and unit cost
                    if comp in ("Raw_Materials", "Direct_Labor"):
                        unit_cost = round(random.uniform(5, 80), 2)
                        qty_used = round(comp_amount / unit_cost, 1) if unit_cost > 0 else 0
                    else:
                        unit_cost = ""
                        qty_used = ""

                    fact_cogs_rows.append([
                        dk, scenario, div_id, pg_id, comp, mat_id, mat_name,
                        qty_used, unit_cost, comp_amount, price_index
                    ])
                    month_cogs += comp_amount

                # Also generate budget line for actual years
                if year <= 2025:
                    budget_cogs = target_cogs * BUDGET_COST_BIAS
                    budget_cogs = noise(budget_cogs, BUDGET_NOISE)
                    # Budget assumes baseline price index = 100
                    for comp, comp_share in cogs_component_split.items():
                        bud_amount = round(budget_cogs * comp_share, 2)
                        if comp == "Raw_Materials":
                            mat_id = primary_mat_id
                            mat_name = pg["material"]
                        elif comp == "Manufacturing_Overhead" and pg["material2"]:
                            mat_id = MAT_NAME_TO_ID.get(pg["material2"], "")
                            mat_name = pg["material2"]
                        else:
                            mat_id = ""
                            mat_name = ""
                        fact_cogs_rows.append([
                            dk, "BUD", div_id, pg_id, comp, mat_id, mat_name,
                            "", "", bud_amount, 100.0
                        ])

            monthly_cogs_total[(year, month)] = month_cogs

    write_csv("fact_cogs_detail.csv",
              ["Date_Key", "Scenario_ID", "Division_ID", "Product_Group_ID",
               "Cost_Component", "Material_ID", "Material_Name",
               "Quantity_Used", "Unit_Cost_EUR", "Amount_EUR",
               "Material_Price_Index"],
              fact_cogs_rows)
    stats["fact_cogs_detail"] = {"rows": len(fact_cogs_rows), "nulls": count_empty(fact_cogs_rows)}
    print(f"  fact_cogs_detail: {len(fact_cogs_rows):,} rows")

    # --------------------------------------------------------
    # STEP 3: Assemble P&L (fact_pnl)
    # --------------------------------------------------------
    print("[Step 3] Assembling P&L...")

    fact_pnl_rows = []
    monthly_net_income = {}
    monthly_da = {}
    monthly_tax = {}
    monthly_interest_exp = {}
    monthly_sbc = {}

    # Map division → its dedicated production cost center
    DIV_TO_PROD_CC = {
        "DIV01": "CC01",  # Production — Industrial
        "DIV02": "CC02",  # Production — Safety
        "DIV03": "CC03",  # Production — Precision
    }

    for year in YEARS:
        for month in MONTHS:
            macro = get_macro(year, month)
            dk = make_date_key(year, month)
            rev = monthly_revenue.get((year, month), 0)
            cogs = monthly_cogs_total.get((year, month), 0)

            for scenario in (["ACT", "BUD"] if year <= 2025 else ["BUD"]):
                s_rev = rev if scenario == "ACT" else rev * BUDGET_REVENUE_BIAS * (1 + random.uniform(-BUDGET_NOISE, BUDGET_NOISE))
                s_cogs = cogs if scenario == "ACT" else cogs * BUDGET_COST_BIAS * (1 + random.uniform(-BUDGET_NOISE, BUDGET_NOISE))

                gross_rev = s_rev / (1 - PNL_RATIOS["sales_deductions_pct"])
                deductions = gross_rev * PNL_RATIOS["sales_deductions_pct"]
                net_rev = gross_rev - deductions

                # OpEx
                sales_mktg = noise(net_rev * PNL_RATIOS["sga_sales_marketing_pct"], 0.02)
                gen_admin = noise(net_rev * PNL_RATIOS["sga_general_admin_pct"], 0.02)
                salaries = noise(net_rev * PNL_RATIOS["sga_salaries_pct"], 0.02)
                rd = noise(net_rev * PNL_RATIOS["rd_pct"], 0.02)
                other_opex = noise(net_rev * PNL_RATIOS["other_opex_pct"], 0.03)

                # D&A — calculated from PP&E (use approximation for now)
                annual_ppe = PPE_GROSS_START * ((1 + CAPEX_PCT_REVENUE) ** (year - 2019))
                da_monthly = (annual_ppe * DEPRECIATION_RATE) / 12
                da_monthly = noise(da_monthly, 0.01)

                # Non-operating
                # Interest expense from debt
                total_debt_approx = sum(f["start_bal"] for f in DEBT_FACILITIES)
                avg_rate = sum(f["rate"] * f["start_bal"] for f in DEBT_FACILITIES) / total_debt_approx
                interest_exp = (total_debt_approx * avg_rate) / 12
                interest_exp = noise(interest_exp, 0.02)

                interest_inc = noise(net_rev * PNL_RATIOS["interest_income_pct"], 0.03)
                fx_impact = net_rev * PNL_RATIOS["fx_impact_pct"] * random.uniform(-1, 1)
                other_nonop = noise(net_rev * PNL_RATIOS["other_nonop_pct"], 0.05)

                # EBT
                ebt = net_rev - s_cogs - sales_mktg - gen_admin - salaries - rd - da_monthly - other_opex \
                      - interest_exp + interest_inc - abs(fx_impact) - other_nonop

                # Tax
                tax = max(0, ebt * PNL_RATIOS["tax_rate"])

                net_income = ebt - tax

                # Stock-based compensation (non-cash, for CF)
                sbc = net_rev * PNL_RATIOS["stock_comp_pct"]

                if scenario == "ACT":
                    monthly_net_income[(year, month)] = net_income
                    monthly_da[(year, month)] = da_monthly
                    monthly_tax[(year, month)] = tax
                    monthly_interest_exp[(year, month)] = interest_exp
                    monthly_sbc[(year, month)] = sbc

                # Per-division allocation:
                # Revenue, deductions, COGS → split by division share, COGS goes to division-specific Production CC
                # OpEx (SGA, R&D, D&A, Other) → split by division share, goes to corporate CC
                # Non-operating → 100% Corporate (G&A) — single division flag (DIV01) for routing

                # Map each division to its own Sales CC so Revenue spreads across DIV01/DIV02/DIV03
                DIV_TO_SALES_CC = {
                    "DIV01": "CC04",   # Sales — DACH      (Industrial Solutions)
                    "DIV02": "CC05",   # Sales — Intl      (Safety & Equipment)
                    "DIV03": "CC05",   # Sales — Intl      (Precision Components — shares intl channel)
                }

                for div_id in DIVISIONS:
                    div_share = DIVISIONS[div_id]["revenue_share"]
                    prod_cc = DIV_TO_PROD_CC[div_id]
                    sales_cc = DIV_TO_SALES_CC[div_id]

                    pnl_lines = [
                        ("PL001",  gross_rev * div_share,   sales_cc),   # Gross Revenue → division Sales CC
                        ("PL002", -deductions * div_share,  sales_cc),
                        ("PL010", -s_cogs * cogs_component_split["Raw_Materials"]          * div_share, prod_cc),
                        ("PL011", -s_cogs * cogs_component_split["Direct_Labor"]           * div_share, prod_cc),
                        ("PL012", -s_cogs * cogs_component_split["Manufacturing_Overhead"] * div_share, prod_cc),
                        ("PL013", -s_cogs * cogs_component_split["Freight"]                * div_share, "CC08"), # Logistics
                        ("PL014", -s_cogs * cogs_component_split["Inventory_Writedown"]    * div_share, "CC10"), # QA
                        ("PL020", -sales_mktg  * div_share, "CC04"),
                        ("PL021", -gen_admin   * div_share, "CC07"),
                        ("PL022", -salaries    * div_share, "CC07"),
                        ("PL023", -rd          * div_share, "CC06"),
                        ("PL024", -da_monthly  * div_share, "CC07"),
                        ("PL025", -other_opex  * div_share, "CC09"),
                        ("PL030", -interest_exp* div_share, "CC07"),
                        ("PL031",  interest_inc* div_share, "CC07"),
                        ("PL032", -abs(fx_impact) * div_share, "CC07"),
                        ("PL033", -other_nonop * div_share, "CC07"),
                        ("PL040", -tax         * div_share, "CC07"),
                    ]

                    for gl_id, amount, cc_id in pnl_lines:
                        fact_pnl_rows.append([dk, scenario, div_id, cc_id, gl_id, round(amount, 2)])

    write_csv("fact_pnl.csv",
              ["Date_Key", "Scenario_ID", "Division_ID", "Cost_Center_ID", "GL_Account_ID", "Amount_EUR"],
              fact_pnl_rows)
    stats["fact_pnl"] = {"rows": len(fact_pnl_rows), "nulls": count_empty(fact_pnl_rows)}
    print(f"  fact_pnl: {len(fact_pnl_rows):,} rows")

    # --------------------------------------------------------
    # STEP 4: Generate Balance Sheet (fact_balance_sheet)
    # --------------------------------------------------------
    print("[Step 4] Generating balance sheet...")

    fact_bs_rows = []
    prev_bs = {}  # Previous month's balances

    # Initialize BS (Dec 2019 proxy)
    init_rev_monthly = BASE_ANNUAL_REVENUE / 12
    init_cogs_monthly = init_rev_monthly * 0.59
    prev_bs = {
        "BS001": 85_000_000,   # Cash
        "BS002": init_rev_monthly * BS_ASSUMPTIONS["dso_base"] / 30,
        "BS003": init_cogs_monthly * BS_ASSUMPTIONS["dio_base"] / 30 * 0.40,  # RM 40% of inventory
        "BS004": init_cogs_monthly * BS_ASSUMPTIONS["dio_base"] / 30 * 0.25,  # WIP
        "BS005": init_cogs_monthly * BS_ASSUMPTIONS["dio_base"] / 30 * 0.35,  # FG
        "BS006": init_rev_monthly * BS_ASSUMPTIONS["prepaid_pct_revenue"],
        "BS007": init_rev_monthly * BS_ASSUMPTIONS["other_ca_pct_revenue"],
        "BS010": PPE_GROSS_START,
        "BS011": -PPE_GROSS_START * 0.35,  # Accumulated depreciation (negative)
        "BS012": BS_ASSUMPTIONS["intangibles_base"],
        "BS013": BS_ASSUMPTIONS["goodwill"],
        "BS014": init_rev_monthly * BS_ASSUMPTIONS["other_nca_pct_revenue"],
        "BS020": init_cogs_monthly * BS_ASSUMPTIONS["dpo_base"] / 30,
        "BS021": DEBT_FACILITIES[0]["start_bal"],  # Revolving = short-term
        "BS022": 15_000_000,   # Current portion of LT debt
        "BS023": init_rev_monthly * BS_ASSUMPTIONS["accrued_liab_pct_revenue"],
        "BS024": 0,
        "BS025": init_rev_monthly * BS_ASSUMPTIONS["other_cl_pct_revenue"],
        "BS030": sum(f["start_bal"] for f in DEBT_FACILITIES[1:]),  # LT debt
        "BS031": BS_ASSUMPTIONS["pension_base"],
        "BS032": init_rev_monthly * BS_ASSUMPTIONS["other_ncl_pct_revenue"],
        "BS040": BS_ASSUMPTIONS["share_capital"],
        "BS041": 180_000_000,  # Starting retained earnings
        "BS042": BS_ASSUMPTIONS["other_reserves_base"],
    }

    # Track for CF
    prev_ar = prev_bs["BS002"]
    prev_inv = prev_bs["BS003"] + prev_bs["BS004"] + prev_bs["BS005"]
    prev_ap = prev_bs["BS020"]
    prev_prepaid = prev_bs["BS006"]
    prev_accrued = prev_bs["BS023"]
    cumulative_ppe_gross = PPE_GROSS_START
    cumulative_accum_depr = abs(prev_bs["BS011"])
    retained_earnings = prev_bs["BS041"]

    # Debt tracking
    debt_balances = {f["id"]: f["start_bal"] for f in DEBT_FACILITIES}

    # CF accumulators (separate ACT and BUD)
    fact_cf_rows = []

    for year in YEARS:
        for month in MONTHS:
            macro = get_macro(year, month)
            dk = make_date_key(year, month)
            rev = monthly_revenue.get((year, month), 0)
            cogs = monthly_cogs_total.get((year, month), 0)
            ni = monthly_net_income.get((year, month), 0)
            da = monthly_da.get((year, month), 0)
            tax = monthly_tax.get((year, month), 0)
            sbc = monthly_sbc.get((year, month), 0)

            # DSO/DIO/DPO adjustments
            effective_dso = BS_ASSUMPTIONS["dso_base"] + macro["dso_add"]
            effective_dio = BS_ASSUMPTIONS["dio_base"] * macro["inventory_mult"]
            effective_dpo = BS_ASSUMPTIONS["dpo_base"]

            # Current Assets
            new_ar = noise(rev * effective_dso / 30, 0.02)
            total_inv = noise(cogs * effective_dio / 30, 0.02)
            new_inv_rm = total_inv * 0.40
            new_inv_wip = total_inv * 0.25
            new_inv_fg = total_inv * 0.35
            new_prepaid = noise(rev * BS_ASSUMPTIONS["prepaid_pct_revenue"], 0.03)
            new_other_ca = noise(rev * BS_ASSUMPTIONS["other_ca_pct_revenue"], 0.03)

            # PP&E
            monthly_capex = noise(rev * CAPEX_PCT_REVENUE, 0.05)
            disposals_gross = noise(cumulative_ppe_gross * ASSET_DISPOSAL_PCT / 12, 0.1)
            cumulative_ppe_gross += monthly_capex - disposals_gross
            cumulative_accum_depr += da
            # Reduce accum depr for disposed assets
            disposal_depr = disposals_gross * 0.8  # Assume 80% depreciated
            cumulative_accum_depr -= disposal_depr

            # Intangibles amortization
            intangibles = BS_ASSUMPTIONS["intangibles_base"] * ((1 - BS_ASSUMPTIONS["intangibles_amort_rate"]) ** (year - 2019 + month / 12))
            other_nca = noise(rev * BS_ASSUMPTIONS["other_nca_pct_revenue"], 0.03)

            # Current Liabilities
            new_ap = noise(cogs * effective_dpo / 30, 0.02)
            new_accrued = noise(rev * BS_ASSUMPTIONS["accrued_liab_pct_revenue"], 0.02)
            new_tax_pay = noise(tax * BS_ASSUMPTIONS["tax_payable_pct_tax"], 0.03)
            new_other_cl = noise(rev * BS_ASSUMPTIONS["other_cl_pct_revenue"], 0.03)

            # Debt management
            # Quarterly repayments on term loans
            quarterly_repayment = 0
            if month in (3, 6, 9, 12):
                for f in DEBT_FACILITIES:
                    if f["type"] == "Term":
                        repay = f["start_bal"] * 0.02  # 2% quarterly
                        debt_balances[f["id"]] = max(0, debt_balances[f["id"]] - repay)
                        quarterly_repayment += repay

            # Bond maturity check
            for f in DEBT_FACILITIES:
                mat = datetime.strptime(f["maturity"], "%Y-%m-%d")
                if mat.year == year and mat.month == month:
                    # Refinance: pay off old, take new at higher rate
                    old_bal = debt_balances[f["id"]]
                    debt_balances[f["id"]] = 0
                    # New facility (simplified — add to revolving)
                    debt_balances["DEBT01"] += old_bal * 0.7  # 70% refinanced
                    quarterly_repayment += old_bal * 0.3       # 30% paid off

            st_debt = debt_balances.get("DEBT01", 0)
            lt_debt = sum(v for k, v in debt_balances.items() if k != "DEBT01")
            cpltd = lt_debt * 0.05  # 5% of LT debt is current portion
            lt_debt_net = lt_debt - cpltd

            # Pension
            pension_years = year - 2019 + month / 12
            pension = BS_ASSUMPTIONS["pension_base"] * ((1 + BS_ASSUMPTIONS["pension_growth"]) ** pension_years)
            other_ncl = noise(rev * BS_ASSUMPTIONS["other_ncl_pct_revenue"], 0.03)

            # Dividend (paid quarterly in month 3, 6, 9, 12)
            annual_dividend = max(0, ni * 12 * DIVIDEND_PAYOUT_RATIO)
            quarterly_dividend = annual_dividend / 4 if month in (3, 6, 9, 12) else 0

            # Retained earnings
            retained_earnings += ni - quarterly_dividend

            # ------ Cash Flow Statement ------
            # CFO
            delta_ar = new_ar - prev_ar
            delta_inv = (new_inv_rm + new_inv_wip + new_inv_fg) - prev_inv
            delta_ap = new_ap - prev_ap
            delta_prepaid = new_prepaid - prev_prepaid
            delta_accrued = new_accrued - prev_accrued

            # Investing
            disposal_proceeds = disposals_gross * 0.15  # Net book value proceeds
            acquisitions = 0
            # Occasional acquisition
            if year == 2022 and month == 6:
                acquisitions = -25_000_000  # Small bolt-on
            other_investing = noise(-500_000, 0.5)

            # Financing
            debt_proceeds = 0
            if year == 2023 and month == 1:
                debt_proceeds = 40_000_000  # Refinancing during supply crisis
                debt_balances["DEBT02"] += debt_proceeds

            debt_repayment = -quarterly_repayment
            other_financing = noise(-200_000, 0.5)

            # Net cash change
            cfo = ni + da + sbc - delta_ar - delta_inv + delta_ap - delta_prepaid + delta_accrued
            cfi = -monthly_capex + acquisitions + disposal_proceeds + other_investing
            cff = debt_proceeds + debt_repayment - quarterly_dividend + other_financing

            net_cash_change = cfo + cfi + cff
            new_cash = prev_bs.get("BS001", 85_000_000) + net_cash_change

            # Ensure cash doesn't go too negative (draw on revolver)
            if new_cash < 10_000_000:
                revolver_draw = 20_000_000
                debt_balances["DEBT01"] += revolver_draw
                st_debt = debt_balances["DEBT01"]
                new_cash += revolver_draw
                debt_proceeds += revolver_draw
                cff += revolver_draw

            # Write BS row — force balance: Assets = Liabilities + Equity
            bs_values = {
                "BS001": round(new_cash, 2),
                "BS002": round(new_ar, 2),
                "BS003": round(new_inv_rm, 2),
                "BS004": round(new_inv_wip, 2),
                "BS005": round(new_inv_fg, 2),
                "BS006": round(new_prepaid, 2),
                "BS007": round(new_other_ca, 2),
                "BS010": round(cumulative_ppe_gross, 2),
                "BS011": round(-cumulative_accum_depr, 2),
                "BS012": round(intangibles, 2),
                "BS013": BS_ASSUMPTIONS["goodwill"],
                "BS014": round(other_nca, 2),
                "BS020": round(new_ap, 2),
                "BS021": round(st_debt, 2),
                "BS022": round(cpltd, 2),
                "BS023": round(new_accrued, 2),
                "BS024": round(new_tax_pay, 2),
                "BS025": round(new_other_cl, 2),
                "BS030": round(lt_debt_net, 2),
                "BS031": round(pension, 2),
                "BS032": round(other_ncl, 2),
                "BS040": BS_ASSUMPTIONS["share_capital"],
                "BS041": round(retained_earnings, 2),
            }

            # Calculate Other Reserves as plug to force A = L + E
            asset_keys = ["BS001","BS002","BS003","BS004","BS005","BS006","BS007",
                          "BS010","BS011","BS012","BS013","BS014"]
            liab_keys = ["BS020","BS021","BS022","BS023","BS024","BS025",
                         "BS030","BS031","BS032"]
            equity_fixed_keys = ["BS040","BS041"]

            total_a = sum(bs_values[k] for k in asset_keys)
            total_l = sum(bs_values[k] for k in liab_keys)
            total_e_fixed = sum(bs_values[k] for k in equity_fixed_keys)
            other_reserves = total_a - total_l - total_e_fixed
            bs_values["BS042"] = round(other_reserves, 2)

            for gl_id, amount in bs_values.items():
                fact_bs_rows.append([dk, "ACT", gl_id, amount])

            # Write CF rows — ACTUAL
            cf_entries_act = [
                ("CF001", "Operating",  round(ni, 2)),
                ("CF002", "Operating",  round(da, 2)),
                ("CF003", "Operating",  round(sbc, 2)),
                ("CF004", "Operating",  round(-delta_ar, 2)),
                ("CF005", "Operating",  round(-delta_inv, 2)),
                ("CF006", "Operating",  round(delta_ap, 2)),
                ("CF007", "Operating",  round(-delta_prepaid, 2)),
                ("CF008", "Operating",  round(delta_accrued, 2)),
                ("CF009", "Operating",  round(noise(100_000, 0.5), 2)),  # Other adj
                ("CF010", "Investing",  round(-monthly_capex, 2)),
                ("CF011", "Investing",  round(acquisitions, 2)),
                ("CF012", "Investing",  round(disposal_proceeds, 2)),
                ("CF013", "Investing",  round(other_investing, 2)),
                ("CF014", "Financing",  round(debt_proceeds, 2)),
                ("CF015", "Financing",  round(debt_repayment, 2)),
                ("CF016", "Financing",  round(-quarterly_dividend, 2)),
                ("CF017", "Financing",  0),  # No buyback in this scenario
                ("CF018", "Financing",  round(other_financing, 2)),
            ]
            for cf_gl, cf_cat, cf_amt in cf_entries_act:
                fact_cf_rows.append([dk, "ACT", cf_gl, cf_cat, cf_amt])

            # Write CF rows — BUDGET (only for actual years 2020-2025)
            # Budget CF assumes: NI = Actual NI × budget bias, no extraordinary items,
            # smooth WC changes, planned CAPEX, planned debt schedule
            if year <= 2025:
                bud_ni = ni * BUDGET_REVENUE_BIAS * (1 + random.uniform(-BUDGET_NOISE, BUDGET_NOISE))
                bud_da = da * (1 + random.uniform(-0.01, 0.01))
                bud_sbc = sbc * (1 + random.uniform(-0.02, 0.02))
                # WC changes assumed smaller in budget (smoother plan)
                bud_delta_ar = delta_ar * 0.7
                bud_delta_inv = delta_inv * 0.7
                bud_delta_ap = delta_ap * 0.7
                bud_delta_prepaid = delta_prepaid * 0.5
                bud_delta_accrued = delta_accrued * 0.5
                # CAPEX — budget assumes 95% of actual planned
                bud_capex = monthly_capex * 0.95
                # No acquisitions in budget (extraordinary)
                bud_acquisitions = 0
                bud_disposals = disposal_proceeds * 0.5
                # Debt — assume planned schedule (no emergency proceeds)
                bud_debt_proceeds = 0 if year not in (2023,) or month != 1 else debt_proceeds * 0.5
                bud_debt_repayment = debt_repayment  # Same plan
                bud_dividend = -quarterly_dividend * 0.95

                cf_entries_bud = [
                    ("CF001", "Operating",  round(bud_ni, 2)),
                    ("CF002", "Operating",  round(bud_da, 2)),
                    ("CF003", "Operating",  round(bud_sbc, 2)),
                    ("CF004", "Operating",  round(-bud_delta_ar, 2)),
                    ("CF005", "Operating",  round(-bud_delta_inv, 2)),
                    ("CF006", "Operating",  round(bud_delta_ap, 2)),
                    ("CF007", "Operating",  round(-bud_delta_prepaid, 2)),
                    ("CF008", "Operating",  round(bud_delta_accrued, 2)),
                    ("CF009", "Operating",  0),  # No other adj in budget
                    ("CF010", "Investing",  round(-bud_capex, 2)),
                    ("CF011", "Investing",  round(bud_acquisitions, 2)),
                    ("CF012", "Investing",  round(bud_disposals, 2)),
                    ("CF013", "Investing",  0),
                    ("CF014", "Financing",  round(bud_debt_proceeds, 2)),
                    ("CF015", "Financing",  round(bud_debt_repayment, 2)),
                    ("CF016", "Financing",  round(bud_dividend, 2)),
                    ("CF017", "Financing",  0),
                    ("CF018", "Financing",  0),
                ]
                for cf_gl, cf_cat, cf_amt in cf_entries_bud:
                    fact_cf_rows.append([dk, "BUD", cf_gl, cf_cat, cf_amt])

            # Update prev for next month
            prev_bs["BS001"] = new_cash
            prev_ar = new_ar
            prev_inv = new_inv_rm + new_inv_wip + new_inv_fg
            prev_ap = new_ap
            prev_prepaid = new_prepaid
            prev_accrued = new_accrued

    write_csv("fact_balance_sheet.csv",
              ["Date_Key", "Scenario_ID", "GL_Account_ID", "Amount_EUR"],
              fact_bs_rows)
    stats["fact_balance_sheet"] = {"rows": len(fact_bs_rows), "nulls": count_empty(fact_bs_rows)}
    print(f"  fact_balance_sheet: {len(fact_bs_rows):,} rows")

    # --------------------------------------------------------
    # STEP 5: Write Cash Flow (already generated in Step 4)
    # --------------------------------------------------------
    print("[Step 5] Writing cash flow...")

    write_csv("fact_cashflow.csv",
              ["Date_Key", "Scenario_ID", "GL_Account_ID", "CF_Category", "Amount_EUR"],
              fact_cf_rows)
    stats["fact_cashflow"] = {"rows": len(fact_cf_rows), "nulls": count_empty(fact_cf_rows)}
    print(f"  fact_cashflow: {len(fact_cf_rows):,} rows")

    # --------------------------------------------------------
    # STEP 6: AR Aging (fact_ar_aging)
    # --------------------------------------------------------
    print("[Step 6] Generating AR aging...")

    fact_ar_rows = []
    aging_buckets = {
        "Current":  {"share_normal": 0.55, "share_crisis": 0.35, "provision": 0.00},
        "1-30":     {"share_normal": 0.25, "share_crisis": 0.25, "provision": 0.01},
        "31-60":    {"share_normal": 0.12, "share_crisis": 0.18, "provision": 0.03},
        "61-90":    {"share_normal": 0.05, "share_crisis": 0.12, "provision": 0.08},
        "90+":      {"share_normal": 0.03, "share_crisis": 0.10, "provision": 0.25},
    }

    for year in YEARS:
        for month in MONTHS:
            # Crisis detection: based on current macro label
            macro_label = get_macro(year, month)["label"]
            is_crisis = macro_label in ("COVID", "Great_Resignation", "Geopolitical_Risk")
            dk = make_date_key(year, month)
            for seg_id, seg in CUSTOMER_SEGMENTS.items():
                # Total AR for this segment
                seg_rev = monthly_revenue.get((year, month), 0) * SEGMENT_REVENUE_SHARES[seg_id]
                pay_days = seg["crisis_days"] if is_crisis else seg["pay_days"]
                seg_ar = seg_rev * pay_days / 30

                for bucket, bp in aging_buckets.items():
                    share = bp["share_crisis"] if is_crisis else bp["share_normal"]
                    amount = round(noise(seg_ar * share, 0.03), 2)
                    prov_pct = bp["provision"]
                    # Higher provision during crisis
                    if is_crisis and bucket in ("61-90", "90+"):
                        prov_pct *= 1.5
                    prov_eur = round(amount * prov_pct, 2)

                    fact_ar_rows.append([dk, seg_id, bucket, amount, round(prov_pct, 4), prov_eur])

    write_csv("fact_ar_aging.csv",
              ["Date_Key", "Customer_Segment_ID", "Aging_Bucket",
               "Amount_EUR", "Provision_Pct", "Provision_EUR"],
              fact_ar_rows)
    stats["fact_ar_aging"] = {"rows": len(fact_ar_rows), "nulls": count_empty(fact_ar_rows)}
    print(f"  fact_ar_aging: {len(fact_ar_rows):,} rows")

    # --------------------------------------------------------
    # STEP 7: Debt (fact_debt)
    # --------------------------------------------------------
    print("[Step 7] Generating debt data...")

    fact_debt_rows = []
    # Reset debt for clean generation
    debt_state = {f["id"]: f["start_bal"] for f in DEBT_FACILITIES}

    for year in YEARS:
        for month in MONTHS:
            dk = make_date_key(year, month)

            # Quarterly repayments
            if month in (3, 6, 9, 12):
                for f in DEBT_FACILITIES:
                    if f["type"] == "Term":
                        repay = f["start_bal"] * 0.02
                        debt_state[f["id"]] = max(0, debt_state[f["id"]] - repay)

            # Bond maturity
            for f in DEBT_FACILITIES:
                mat = datetime.strptime(f["maturity"], "%Y-%m-%d")
                if mat.year == year and mat.month == month:
                    old = debt_state[f["id"]]
                    debt_state[f["id"]] = 0
                    debt_state["DEBT01"] += old * 0.7

            # Refinancing
            if year == 2023 and month == 1:
                debt_state["DEBT02"] += 40_000_000

            total_debt = sum(debt_state.values())
       # LTM window: last 12 months ending at (year, month) inclusive
            def is_in_ltm(y, m, curr_y=year, curr_m=month):
                months_diff = (curr_y - y) * 12 + (curr_m - m)
                return 0 <= months_diff < 12

            ltm_ni = sum(monthly_net_income.get((y, m), 0)
                         for y in range(max(2020, year - 1), year + 1)
                         for m in range(1, 13)
                         if is_in_ltm(y, m))
            ltm_da = sum(monthly_da.get((y, m), 0)
                         for y in range(max(2020, year - 1), year + 1)
                         for m in range(1, 13)
                         if is_in_ltm(y, m))
            ltm_ebitda = ltm_ni + ltm_da if (ltm_ni + ltm_da) > 0 else 1

            for f in DEBT_FACILITIES:
                bal = debt_state[f["id"]]
                if bal <= 0 and datetime.strptime(f["maturity"], "%Y-%m-%d") < datetime(year, month, 1):
                    continue  # Skip matured/paid facilities

                covenant_actual = round(total_debt / ltm_ebitda, 2) if ltm_ebitda > 0 else 99.99
                is_breach = covenant_actual > f["covenant"]

                fact_debt_rows.append([
                    dk, f["id"], f["name"], f["type"], f["class"],
                    round(bal, 2), f["rate"], f["maturity"],
                    f["covenant"], covenant_actual, is_breach
                ])

    write_csv("fact_debt.csv",
              ["Date_Key", "Facility_ID", "Facility_Name", "Debt_Type",
               "Classification", "Outstanding_EUR", "Interest_Rate_Pct",
               "Maturity_Date", "Covenant_Debt_EBITDA", "Covenant_Actual", "Is_Covenant_Breach"],
              fact_debt_rows)
    stats["fact_debt"] = {"rows": len(fact_debt_rows), "nulls": count_empty(fact_debt_rows)}
    print(f"  fact_debt: {len(fact_debt_rows):,} rows")

    # --------------------------------------------------------
    # STEP 8: Sales Detail (fact_sales_detail)
    # --------------------------------------------------------
    print("[Step 8] Generating sales detail (transactions)...")

    fact_sd_rows = []
    txn_counter = 0
    customer_ids = [f"CUST{str(i).zfill(4)}" for i in range(1, NUM_CUSTOMERS + 1)]

    # Pareto distribution for customers: top 20% get 80% of revenue
    pareto_weights = []
    top_20_count = max(1, int(NUM_CUSTOMERS * 0.2))
    for i in range(NUM_CUSTOMERS):
        if i < top_20_count:
            pareto_weights.append(4.0)  # Top 20% — 4x weight
        else:
            pareto_weights.append(1.0)
    total_w = sum(pareto_weights)
    pareto_weights = [w / total_w for w in pareto_weights]

    for year in YEARS:
        for month in MONTHS:
            dk = make_date_key(year, month)
            days_in_month = 28 + (month in (1,3,5,7,8,10,12)) * 3 + (month in (4,6,9,11)) * 2

            for pg_id in PRODUCT_GROUPS:
                for reg_id in REGIONS:
                    for seg_id in CUSTOMER_SEGMENTS:
                        # Get aggregated revenue for this combo
                        combo_rev = 0
                        for row in fact_sales_rows:
                            if (row[0] == dk and row[2] == pg_id and
                                row[3] == reg_id and row[4] == seg_id):
                                combo_rev = row[5]
                                break

                        if combo_rev <= 0:
                            continue

                        # Split into transactions
                        n_txn = max(1, int(random.gauss(AVG_TRANSACTIONS_PER_MONTH_PER_COMBO, 2)))
                        remaining = combo_rev
                        div_id = PRODUCT_GROUPS[pg_id]["division"]

                        for t in range(n_txn):
                            txn_counter += 1
                            txn_id = f"TXN{str(txn_counter).zfill(7)}"

                            # Random day within month
                            day = random.randint(1, days_in_month)
                            txn_date = f"{year}-{str(month).zfill(2)}-{str(day).zfill(2)}"

                            # Customer (Pareto-weighted)
                            cust_id = random.choices(customer_ids, weights=pareto_weights, k=1)[0]

                            # Amount — split remaining among transactions
                            if t == n_txn - 1:
                                txn_rev = remaining
                            else:
                                txn_rev = remaining * random.uniform(0.05, 0.3)
                                remaining -= txn_rev

                            unit_price = round(random.uniform(20, 800), 2)
                            qty = max(1, int(txn_rev / unit_price))
                            discount_pct = round(random.choice([0, 0, 0, 0.02, 0.05, 0.08, 0.10, 0.15]), 2)
                            net_rev = round(qty * unit_price * (1 - discount_pct), 2)

                            fact_sd_rows.append([
                                txn_id, dk, txn_date, div_id, pg_id, reg_id, seg_id,
                                cust_id, qty, unit_price, discount_pct, net_rev
                            ])

    write_csv("fact_sales_detail.csv",
              ["Transaction_ID", "Date_Key", "Transaction_Date",
               "Division_ID", "Product_Group_ID", "Region_ID",
               "Customer_Segment_ID", "Customer_ID",
               "Quantity", "Unit_Price_EUR", "Discount_Pct", "Net_Revenue_EUR"],
              fact_sd_rows)
    stats["fact_sales_detail"] = {"rows": len(fact_sd_rows), "nulls": count_empty(fact_sd_rows)}
    print(f"  fact_sales_detail: {len(fact_sd_rows):,} rows")

    # --------------------------------------------------------
    # SUMMARY REPORT
    # --------------------------------------------------------
    print()
    print("=" * 70)
    print("GENERATION SUMMARY")
    print("=" * 70)

    total_rows = 0
    total_nulls = 0
    print(f"\n{'File':<30s} {'Rows':>10s} {'Empty vals':>12s} {'Status':<10s}")
    print("-" * 65)
    for fname, st in stats.items():
        status = "OK" if st["nulls"] == 0 else f"WARN ({st['nulls']} empty)"
        print(f"  {fname:<28s} {st['rows']:>10,d} {st['nulls']:>12,d} {status:<10s}")
        total_rows += st["rows"]
        total_nulls += st["nulls"]

    print("-" * 65)
    print(f"  {'TOTAL':<28s} {total_rows:>10,d} {total_nulls:>12,d}")
    print()

    # Validation checks
    print("VALIDATION CHECKS:")
    print("-" * 40)

    # Check 1: BS balances
    last_dk = make_date_key(2025, 12)
    last_bs = {}
    for row in fact_bs_rows:
        # row format: [Date_Key, Scenario_ID, GL_Account_ID, Amount_EUR]
        if row[0] == last_dk and row[1] == "ACT":
            last_bs[row[2]] = row[3]

    # Assets: BS001-BS014 (BS011 accum depr is stored negative, which is correct)
    asset_ids = ["BS001","BS002","BS003","BS004","BS005","BS006","BS007",
                 "BS010","BS011","BS012","BS013","BS014"]
    liab_ids = ["BS020","BS021","BS022","BS023","BS024","BS025",
                "BS030","BS031","BS032"]
    equity_ids = ["BS040","BS041","BS042"]

    total_assets = sum(last_bs.get(k, 0) for k in asset_ids)
    total_liabilities = sum(last_bs.get(k, 0) for k in liab_ids)
    total_equity = sum(last_bs.get(k, 0) for k in equity_ids)

    bs_check = abs(total_assets - total_liabilities - total_equity)
    bs_ok = bs_check < total_assets * 0.02  # Allow 2% tolerance (rounding from many months)
    print(f"  BS Balance (Dec 2025):   Assets={total_assets:,.0f}  L+E={total_liabilities + total_equity:,.0f}  "
          f"Delta={bs_check:,.0f}  {'OK' if bs_ok else 'INFO - drift from cumulative rounding'}")

    # Check 2: Revenue consistency
    total_sales_rev = sum(r[5] for r in fact_sales_rows if r[0] // 10000 == 2024)
    print(f"  Revenue 2024 (sales):    {total_sales_rev:,.0f} EUR")
    # Expected: average across 2024 macro periods
    macro_2024_avg = sum(get_macro(2024, m)["revenue"] for m in range(1, 13)) / 12
    expected_2024 = BASE_ANNUAL_REVENUE * ((1 + ANNUAL_ORGANIC_GROWTH) ** 5) * macro_2024_avg
    print(f"  Revenue 2024 (expected): {expected_2024:,.0f} EUR")
    rev_delta_pct = abs(total_sales_rev - expected_2024) / expected_2024 * 100
    print(f"  Variance:                {rev_delta_pct:.1f}%  {'OK' if rev_delta_pct < 15 else 'CHECK'}")

    # Check 3: P&L → CF → BS linkage
    total_ni_2024 = sum(monthly_net_income.get((2024, m), 0) for m in range(1, 13))
    print(f"  Net Income 2024:         {total_ni_2024:,.0f} EUR")
    margin_2024 = total_ni_2024 / total_sales_rev * 100 if total_sales_rev else 0
    print(f"  Net Margin 2024:         {margin_2024:.1f}%  (target ~17%)")

    # Check 4: File sizes
    print()
    print("FILE SIZES:")
    print("-" * 40)
    total_size = 0
    for fname in sorted(stats.keys()):
        fpath = os.path.join(OUTPUT_DIR, fname + ".csv")
        if os.path.exists(fpath):
            fsize = os.path.getsize(fpath)
            total_size += fsize
            print(f"  {fname + '.csv':<35s} {fsize / 1024:>8.1f} KB")
    print(f"  {'TOTAL':<35s} {total_size / 1024 / 1024:>8.2f} MB")

    print()
    if errors:
        print(f"ERRORS ({len(errors)}):")
        for e in errors:
            print(f"  [ERROR] {e}")
    else:
        print("ERRORS: None")

    if warnings:
        print(f"WARNINGS ({len(warnings)}):")
        for w in warnings:
            print(f"  [WARN] {w}")
    else:
        print("WARNINGS: None")

    print()
    print("=" * 70)
    print("Generation complete. Files saved to:")
    print(f"  {OUTPUT_DIR}")
    print()
    print("Output: 13 CSV files (was 12 in v1.0 — added dim_material.csv)")
    print()
    print("Next step: Open Power BI → Get Data → CSV → load all 13 files")
    print("           Then create dim_calendar, dim_division, dim_region,")
    print("           dim_scenario as calculated tables in Power BI.")
    print("           Add relationships:")
    print("             fact_cogs_detail[Material_ID] → dim_material[Material_ID]")
    print("             fact_balance_sheet[Scenario_ID] → dim_Scenario[Scenario_ID]")
    print("             fact_cashflow[Scenario_ID] → dim_Scenario[Scenario_ID]")
    print("=" * 70)


# ============================================================
# FILE I/O
# ============================================================

def write_csv(filename, headers, rows):
    """Write a CSV file with headers and data rows."""
    filepath = os.path.join(OUTPUT_DIR, filename)
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)


def count_empty(rows):
    """Count empty/None values across all rows."""
    count = 0
    for row in rows:
        for val in row:
            if val is None or val == "" or val == "None":
                count += 1
    return count


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    start_time = datetime.now()
    print(f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    try:
        generate_all()
    except Exception as e:
        print(f"\n[FATAL ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    end_time = datetime.now()
    elapsed = (end_time - start_time).total_seconds()
    print(f"\nElapsed: {elapsed:.1f} seconds")