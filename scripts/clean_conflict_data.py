import pandas as pd
from pathlib import Path

# ---------- paths ----------
input_file = Path("data/raw/global/ACLED.csv")   # change if needed
output_dir = Path("data/cleaned/global")
output_dir.mkdir(parents=True, exist_ok=True)

output_main = output_dir / "conflict_standardized_monthly.csv"
output_country = output_dir / "conflict_country_monthly.csv"

# ---------- read ----------
if input_file.suffix.lower() == ".csv":
    df = pd.read_csv(input_file)
else:
    df = pd.read_excel(input_file)

print("Original columns:")
print(df.columns.tolist())

# ---------- rename from your actual ACLED columns ----------
rename_map = {
    "iso": "iso3",
    "country": "country",
    "admin1": "admin1",
    "admin2": "admin2",
    "event_date": "event_date",
    "fatalities": "fatalities"
}

df = df.rename(columns=rename_map)

# ---------- check needed columns ----------
needed = ["iso3", "country", "admin1", "admin2", "event_date", "fatalities"]
missing = [c for c in needed if c not in df.columns]
if missing:
    raise ValueError(f"Missing expected columns: {missing}")

df = df[needed].copy()

# ---------- clean text ----------
for col in ["iso3", "country", "admin1", "admin2"]:
    df[col] = df[col].astype(str).str.strip()
    df[col] = df[col].replace({"nan": pd.NA, "None": pd.NA, "": pd.NA})

# ---------- clean dates ----------
df["event_date"] = pd.to_datetime(df["event_date"], errors="coerce")
df = df[df["event_date"].notna()].copy()

df["year"] = df["event_date"].dt.year
df["month_num"] = df["event_date"].dt.month
df["month"] = df["event_date"].dt.strftime("%B")

# ---------- clean fatalities ----------
df["fatalities"] = pd.to_numeric(df["fatalities"], errors="coerce").fillna(0)

# ---------- keep rows with country ----------
df = df[df["country"].notna() & df["iso3"].notna()].copy()

# ---------- create monthly admin-level table ----------
main = (
    df.groupby(["iso3", "country", "admin1", "admin2", "year", "month_num", "month"], dropna=False, as_index=False)
      .agg(
          events=("event_date", "size"),
          fatalities=("fatalities", "sum")
      )
)

# ---------- create country-level monthly table ----------
country_monthly = (
    main.groupby(["iso3", "country", "year", "month_num", "month"], as_index=False)
        .agg({
            "events": "sum",
            "fatalities": "sum"
        })
)

# ---------- sort ----------
main = main.sort_values(["year", "month_num", "country", "admin1", "admin2"]).reset_index(drop=True)
country_monthly = country_monthly.sort_values(["year", "month_num", "country"]).reset_index(drop=True)

# ---------- save ----------
main.to_csv(output_main, index=False, encoding="utf-8-sig")
country_monthly.to_csv(output_country, index=False, encoding="utf-8-sig")

print("\nSaved:")
print(output_main)
print(output_country)

print("\nMain sample:")
print(main.head())

print("\nCountry-level sample:")
print(country_monthly.head())