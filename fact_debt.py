import pandas as pd
import numpy as np

# ══════════════════════════════════════════════════════════════
#  fact_debt.py  —  TechniCon Manufacturing GmbH
#  Debt Structure mock data  |  2020-01 → 2026-12
#  4 Facilities: Bond, Term Loan A, Revolving, Schuldschein
# ══════════════════════════════════════════════════════════════

# ── діапазон дат ──────────────────────────────────────────────
START  = pd.Timestamp("2020-01-01")
END    = pd.Timestamp("2026-12-01")   # freq="MS" → перший день місяця
months = pd.date_range(START, END, freq="MS")

# ── структура facility ────────────────────────────────────────
facilities = [
    {
        "Facility_ID":          "DEBT_001",
        "Facility_Name":        "Senior Unsecured Bond",
        "Debt_Type":            "Bond",
        "Base_Outstanding":     130_000_000,
        "Interest_Rate_Pct":    0.0425,
        "Maturity_Date":        pd.Timestamp("2029-06-30"),
        "Covenant_Debt_EBITDA": None,        # no covenant
        "amort_type":           "bullet",
    },
    {
        "Facility_ID":          "DEBT_002",
        "Facility_Name":        "Term Loan A",
        "Debt_Type":            "Term",
        "Base_Outstanding":     75_000_000,
        "Interest_Rate_Pct":    0.0380,
        "Maturity_Date":        pd.Timestamp("2031-03-31"),
        "Covenant_Debt_EBITDA": 3.5,         # Net Debt / EBITDA ≤ 3.5x
        "amort_type":           "amortizing", # bullet до 2029, потім -€1M/квартал
    },
    {
        "Facility_ID":          "DEBT_003",
        "Facility_Name":        "Revolving Credit Facility",
        "Debt_Type":            "Revolving",
        "Base_Outstanding":     35_000_000,
        "Interest_Rate_Pct":    0.0310,
        "Maturity_Date":        pd.Timestamp("2028-09-30"),
        "Covenant_Debt_EBITDA": 3.5,         # Net Debt / EBITDA ≤ 3.5x
        "amort_type":           "revolving",  # ±8% variance; вищий у стрес
    },
    {
        "Facility_ID":          "DEBT_004",
        "Facility_Name":        "Schuldscheindarlehen",
        "Debt_Type":            "Schuldschein",
        "Base_Outstanding":     15_000_000,
        "Interest_Rate_Pct":    0.0290,
        "Maturity_Date":        pd.Timestamp("2026-12-31"),
        "Covenant_Debt_EBITDA": None,        # no covenant
        "amort_type":           "bullet",
    },
]

# ── EBITDA proxy (річний) ─────────────────────────────────────
# 2022–2023: litigation stress → EBITDA падає → covenant breach
def get_ebitda(year):
    ebitda_map = {
        2020: 110_000_000,
        2021: 125_000_000,
        2022:  68_000_000,   # litigation — breach territory (ratio > 3.5x)
        2023:  71_000_000,   # litigation peak stress
        2024: 135_000_000,   # recovery
        2025: 142_000_000,
        2026: 148_000_000,
    }
    return ebitda_map.get(year, 142_000_000)

# ── Net Debt proxy (річний) ───────────────────────────────────
# Сума всіх facility; Revolving вищий у стрес (більше drawn)
def get_net_debt(year):
    net_debt_map = {
        2020: 245_000_000,
        2021: 250_000_000,
        2022: 258_000_000,   # revolver більше drawn під час стресу
        2023: 262_000_000,   # peak drawn
        2024: 255_000_000,
        2025: 252_000_000,
        2026: 252_000_000,
    }
    return net_debt_map.get(year, 252_000_000)

# ── генерація рядків ──────────────────────────────────────────
np.random.seed(42)
rows = []

for fac in facilities:
    outstanding = fac["Base_Outstanding"]

    for dt in months:
        # зупиняємось якщо місяць після Maturity
        if dt > fac["Maturity_Date"]:
            break

        # ── амортизація / варіація outstanding ────────────────
        if fac["amort_type"] == "bullet":
            # константа до погашення
            pass

        elif fac["amort_type"] == "amortizing":
            # bullet до 2029, потім -€1M/квартал
            # (весь діапазон 2020–2026 — без амортизації)
            if dt.year >= 2029 and dt.month in (3, 6, 9, 12):
                outstanding = max(0, outstanding - 1_000_000)

        elif fac["amort_type"] == "revolving":
            # base €35M ± 8%; у стрес 2022–2023 вищий drawn (+25%)
            stress_mult = 1.25 if dt.year in (2022, 2023) else 1.0
            noise       = np.random.uniform(-0.08, 0.08)
            outstanding = fac["Base_Outstanding"] * stress_mult * (1 + noise)
            outstanding = round(outstanding / 100_000) * 100_000  # округлення до €100K

        # ── covenant розрахунок ───────────────────────────────
        if fac["Covenant_Debt_EBITDA"] is not None:
            net_debt        = get_net_debt(dt.year)
            ebitda          = get_ebitda(dt.year)
            covenant_actual = round(net_debt / ebitda, 2)
            is_breach       = 1 if covenant_actual > fac["Covenant_Debt_EBITDA"] else 0
        else:
            covenant_actual = None
            is_breach       = 0

        rows.append({
            "Date_Key":             int(dt.strftime("%Y%m%d")),
            "Facility_ID":          fac["Facility_ID"],
            "Facility_Name":        fac["Facility_Name"],
            "Debt_Type":            fac["Debt_Type"],
            "Outstanding_EUR":      round(outstanding),
            "Interest_Rate_Pct":    fac["Interest_Rate_Pct"],
            "Maturity_Date":        fac["Maturity_Date"].date(),
            "Covenant_Debt_EBITDA": fac["Covenant_Debt_EBITDA"],
            "Covenant_Actual":      covenant_actual,
            "Is_Covenant_Breach":   is_breach,
        })

fact_debt = pd.DataFrame(rows)

# ══════════════════════════════════════════════════════════════
#  ВЕРИФІКАЦІЯ
# ══════════════════════════════════════════════════════════════

print("=" * 60)
print("SNAPSHOT 01.12.2026 (LASTDATE)")
print("=" * 60)
snapshot = fact_debt[fact_debt["Date_Key"] == 20261201]
print(snapshot[["Facility_Name", "Debt_Type", "Outstanding_EUR",
                "Maturity_Date", "Covenant_Actual", "Is_Covenant_Breach"]]
      .to_string(index=False))
print(f"\nTotal Debt Outstanding:  €{snapshot['Outstanding_EUR'].sum():>15,.0f}")
print(f"Debt Types present:       {sorted(snapshot['Debt_Type'].unique())}")

print()
print("=" * 60)
print("COVENANT BREACH SUMMARY (Term + Revolving тільки)")
print("=" * 60)
covenant_df = (
    fact_debt[fact_debt["Covenant_Debt_EBITDA"].notna()]
    .groupby(["Facility_Name", fact_debt.loc[
        fact_debt["Covenant_Debt_EBITDA"].notna(), "Date_Key"
    ].apply(lambda x: x // 10000)])  # витягуємо рік з Date_Key
    .agg(
        Covenant_Actual   = ("Covenant_Actual",   "first"),
        Is_Covenant_Breach= ("Is_Covenant_Breach", "first")
    )
    .reset_index()
)
# простіший варіант верифікації breach по роках:
print("\nBreach by Year (Term Loan A):")
term_df = fact_debt[
    (fact_debt["Facility_Name"] == "Term Loan A") &
    (fact_debt["Date_Key"] % 10000 == 101)   # January кожного року
][["Date_Key", "Covenant_Actual", "Is_Covenant_Breach"]].copy()
term_df["Year"] = term_df["Date_Key"] // 10000
print(term_df[["Year", "Covenant_Actual", "Is_Covenant_Breach"]].to_string(index=False))

print()
print("=" * 60)
print("MATURITY LADDER (Outstanding на LASTDATE по роках погашення)")
print("=" * 60)
maturity_ladder = (
    snapshot.assign(Maturity_Year=pd.to_datetime(snapshot["Maturity_Date"]).dt.year)
    .groupby("Maturity_Year")["Outstanding_EUR"]
    .sum()
    .reset_index()
    .sort_values("Maturity_Year")
)
print(maturity_ladder.to_string(index=False))

print()
print("=" * 60)
print("DEBT COMPOSITION % (на LASTDATE)")
print("=" * 60)
total = snapshot["Outstanding_EUR"].sum()
for _, row in snapshot.iterrows():
    pct = row["Outstanding_EUR"] / total * 100
    print(f"  {row['Debt_Type']:<15}  €{row['Outstanding_EUR']:>13,.0f}  ({pct:.0f}%)")

print()
print("=" * 60)
print(f"CSV saved → fact_debt.csv")
print(f"Total rows: {len(fact_debt)}")
print("=" * 60)

# ══════════════════════════════════════════════════════════════
#  ЗБЕРЕЖЕННЯ
# ══════════════════════════════════════════════════════════════
output_path = (
    r"D:\Project - Portfolio Controlling"
    r"\02_Mock_Data\Generated_CSV\fact_debt.csv"
)
fact_debt.to_csv(output_path, index=False)
print(f"\n✓ Saved: {output_path}")