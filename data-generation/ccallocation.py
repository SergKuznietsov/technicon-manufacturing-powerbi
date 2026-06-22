# generate_cc_allocation.py
# Generates dim_cc_allocation.csv for Cost Center Overhead Allocation page
# Mirrors SAP CO Umlage (cycle-based allocation) logic:
# Sender CC → Receiver CC → Driver → Allocation %

import pandas as pd
import os

OUTPUT_PATH = r"D:\Project - Portfolio Controlling\02_Mock_Data\Generated_CSV"

# ─────────────────────────────────────────────
# 1. dim_cc_allocation
#    One row per Sender → Receiver pair
# ─────────────────────────────────────────────
allocation_rows = [
    # CC07 General & Administration → Production lines (Driver: Headcount)
    {"Sender_CC_ID": "CC07", "Sender_CC_Name": "General & Administration",
     "Receiver_CC_ID": "CC01", "Receiver_CC_Name": "Production — Industrial",
     "Allocation_Driver": "Headcount", "Allocation_Pct": 0.40},
    {"Sender_CC_ID": "CC07", "Sender_CC_Name": "General & Administration",
     "Receiver_CC_ID": "CC02", "Receiver_CC_Name": "Production — Safety",
     "Allocation_Driver": "Headcount", "Allocation_Pct": 0.35},
    {"Sender_CC_ID": "CC07", "Sender_CC_Name": "General & Administration",
     "Receiver_CC_ID": "CC03", "Receiver_CC_Name": "Production — Precision",
     "Allocation_Driver": "Headcount", "Allocation_Pct": 0.25},

    # CC08 Logistics & Warehousing → Production lines (Driver: Revenue Share)
    {"Sender_CC_ID": "CC08", "Sender_CC_Name": "Logistics & Warehousing",
     "Receiver_CC_ID": "CC01", "Receiver_CC_Name": "Production — Industrial",
     "Allocation_Driver": "Revenue_Share", "Allocation_Pct": 0.45},
    {"Sender_CC_ID": "CC08", "Sender_CC_Name": "Logistics & Warehousing",
     "Receiver_CC_ID": "CC02", "Receiver_CC_Name": "Production — Safety",
     "Allocation_Driver": "Revenue_Share", "Allocation_Pct": 0.30},
    {"Sender_CC_ID": "CC08", "Sender_CC_Name": "Logistics & Warehousing",
     "Receiver_CC_ID": "CC03", "Receiver_CC_Name": "Production — Precision",
     "Allocation_Driver": "Revenue_Share", "Allocation_Pct": 0.25},

    # CC09 IT & Digital → Production lines (Driver: Headcount)
    {"Sender_CC_ID": "CC09", "Sender_CC_Name": "IT & Digital",
     "Receiver_CC_ID": "CC01", "Receiver_CC_Name": "Production — Industrial",
     "Allocation_Driver": "Headcount", "Allocation_Pct": 0.40},
    {"Sender_CC_ID": "CC09", "Sender_CC_Name": "IT & Digital",
     "Receiver_CC_ID": "CC02", "Receiver_CC_Name": "Production — Safety",
     "Allocation_Driver": "Headcount", "Allocation_Pct": 0.35},
    {"Sender_CC_ID": "CC09", "Sender_CC_Name": "IT & Digital",
     "Receiver_CC_ID": "CC03", "Receiver_CC_Name": "Production — Precision",
     "Allocation_Driver": "Headcount", "Allocation_Pct": 0.25},

    # CC10 Quality Assurance → Production lines (Driver: Production Volume)
    {"Sender_CC_ID": "CC10", "Sender_CC_Name": "Quality Assurance",
     "Receiver_CC_ID": "CC01", "Receiver_CC_Name": "Production — Industrial",
     "Allocation_Driver": "Production_Volume", "Allocation_Pct": 0.35},
    {"Sender_CC_ID": "CC10", "Sender_CC_Name": "Quality Assurance",
     "Receiver_CC_ID": "CC02", "Receiver_CC_Name": "Production — Safety",
     "Allocation_Driver": "Production_Volume", "Allocation_Pct": 0.40},
    {"Sender_CC_ID": "CC10", "Sender_CC_Name": "Quality Assurance",
     "Receiver_CC_ID": "CC03", "Receiver_CC_Name": "Production — Precision",
     "Allocation_Driver": "Production_Volume", "Allocation_Pct": 0.25},
]

df_alloc = pd.DataFrame(allocation_rows)

# Validation: each Sender must sum to 100%
validation = df_alloc.groupby("Sender_CC_ID")["Allocation_Pct"].sum()
print("=== Allocation % validation (must all be 1.00) ===")
print(validation)
assert (validation == 1.00).all(), "ERROR: Allocation percentages do not sum to 100% per sender!"
print("✓ Validation passed\n")

# ─────────────────────────────────────────────
# 2. fact_cc_overhead_pool
#    Allocatable overhead amounts per Sender CC
#    Derived from verified fact_pnl 2024 ACT values
# ─────────────────────────────────────────────
overhead_pool_rows = [
    # CC07: only OpEx lines (D&A + SGA_Admin + SGA_Salaries)
    # Non-Operating and Tax excluded — not allocatable per HGB/CO convention
    {"Sender_CC_ID": "CC07", "Sender_CC_Name": "General & Administration",
     "GL_Account_ID": "PL024", "GL_Subcategory": "D&A",
     "Allocatable_Amount_EUR": 28502465.83},
    {"Sender_CC_ID": "CC07", "Sender_CC_Name": "General & Administration",
     "GL_Account_ID": "PL021", "GL_Subcategory": "SGA_Admin",
     "Allocatable_Amount_EUR": 22726641.72},
    {"Sender_CC_ID": "CC07", "Sender_CC_Name": "General & Administration",
     "GL_Account_ID": "PL022", "GL_Subcategory": "SGA_Salaries",
     "Allocatable_Amount_EUR": 16112565.29},

    # CC08: full amount allocatable (Logistics is pure operating cost)
    {"Sender_CC_ID": "CC08", "Sender_CC_Name": "Logistics & Warehousing",
     "GL_Account_ID": "PL013", "GL_Subcategory": "Logistics",
     "Allocatable_Amount_EUR": 23921933.56},

    # CC09: full amount allocatable
    {"Sender_CC_ID": "CC09", "Sender_CC_Name": "IT & Digital",
     "GL_Account_ID": "PL025", "GL_Subcategory": "Other_OpEx",
     "Allocatable_Amount_EUR": 6451265.84},

    # CC10: full amount allocatable
    {"Sender_CC_ID": "CC10", "Sender_CC_Name": "Quality Assurance",
     "GL_Account_ID": "PL014", "GL_Subcategory": "Write-downs",
     "Allocatable_Amount_EUR": 7973977.86},
]

df_pool = pd.DataFrame(overhead_pool_rows)

# Summary by sender
pool_summary = df_pool.groupby("Sender_CC_ID")["Allocatable_Amount_EUR"].sum()
print("=== Overhead Pool by Sender CC ===")
print(pool_summary)
print(f"\nTotal Overhead Pool: €{pool_summary.sum():,.0f}")

# ─────────────────────────────────────────────
# 3. Compute allocated amounts per Sender → Receiver
#    This is the key fact table for the Sankey / matrix visual
# ─────────────────────────────────────────────
pool_totals = df_pool.groupby("Sender_CC_ID")["Allocatable_Amount_EUR"].sum().reset_index()
pool_totals.columns = ["Sender_CC_ID", "Total_Pool_EUR"]

df_result = df_alloc.merge(pool_totals, on="Sender_CC_ID")
df_result["Allocated_Amount_EUR"] = df_result["Total_Pool_EUR"] * df_result["Allocation_Pct"]

print("\n=== Allocated Amounts (Sender → Receiver) ===")
print(df_result[["Sender_CC_ID", "Receiver_CC_ID",
                  "Allocation_Driver", "Allocation_Pct",
                  "Total_Pool_EUR", "Allocated_Amount_EUR"]].to_string(index=False))

# ─────────────────────────────────────────────
# 4. Save CSVs
# ─────────────────────────────────────────────
os.makedirs(OUTPUT_PATH, exist_ok=True)

path_alloc = os.path.join(OUTPUT_PATH, "dim_cc_allocation.csv")
path_pool  = os.path.join(OUTPUT_PATH, "fact_cc_overhead_pool.csv")
path_result = os.path.join(OUTPUT_PATH, "fact_cc_allocated_amounts.csv")

df_alloc.to_csv(path_alloc, index=False, encoding="utf-8-sig")
df_pool.to_csv(path_pool, index=False, encoding="utf-8-sig")
df_result.to_csv(path_result, index=False, encoding="utf-8-sig")

print(f"\n✓ dim_cc_allocation.csv saved → {path_alloc}")
print(f"✓ fact_cc_overhead_pool.csv saved → {path_pool}")
print(f"✓ fact_cc_allocated_amounts.csv saved → {path_result}")
