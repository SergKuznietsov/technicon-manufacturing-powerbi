import os
import glob

CSV_DIR = r"D:\Project - Portfolio Controlling\02_Mock_Data\Generated_CSV"

csv_files = sorted(
    glob.glob(os.path.join(CSV_DIR, "*.csv")),
    key=lambda x: (not os.path.basename(x).startswith("dim_"), x)
)

print(f"Found {len(csv_files)} CSV files\n")
print("=" * 80)

for filepath in csv_files:
    filename = os.path.basename(filepath)
    try:
        with open(filepath, "r", encoding="utf-8-sig") as f:
            header = f.readline().strip()
        print(f"{filename}")
        print(f"  → {header}")
        print(f"  → columns: {len(header.split(','))}")
        print()
    except Exception as e:
        print(f"{filename} — ERROR: {e}\n")

print("=" * 80)