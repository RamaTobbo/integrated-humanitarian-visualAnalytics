import pandas as pd
from pathlib import Path

# ---------- paths ----------
input_file = Path("data/raw/global/ACLED.csv")
output_dir = Path("data/cleaned/global")
output_dir.mkdir(parents=True, exist_ok=True)

output_main = output_dir / "conflict_standardized_monthlybytype.csv"
output_country = output_dir / "conflict_country_monthlybytype.csv"

# ---------- read ----------
if input_file.suffix.lower() == ".csv":
    df = pd.read_csv(input_file)
else:
    df = pd.read_excel(input_file)

print("Original columns:")
print(df.columns.tolist())

# ---------- rename ----------
rename_map = {
    "iso": "iso3",
    "country": "country",
    "admin1": "admin1",
    "admin2": "admin2",
    "event_date": "event_date",
    "event_type": "event_type",
    "fatalities": "fatalities"
}

df = df.rename(columns=rename_map)

# ---------- check needed columns ----------
needed = ["iso3", "country", "admin1", "admin2", "event_date", "event_type", "fatalities"]
missing = [c for c in needed if c not in df.columns]
if missing:
    raise ValueError(f"Missing expected columns: {missing}")

df = df[needed].copy()

# ---------- clean text ----------
for col in ["iso3", "country", "admin1", "admin2", "event_type"]:
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

# ---------- keep valid rows ----------
df = df[
    df["country"].notna()
    & df["iso3"].notna()
    & df["event_type"].notna()
].copy()

# ---------- detailed monthly table with event type ----------
main_by_type = (
    df.groupby(
        ["iso3", "country", "admin1", "admin2", "year", "month_num", "month", "event_type"],
        dropna=False,
        as_index=False
    )
    .agg(
        events=("event_date", "size"),
        fatalities=("fatalities", "sum")
    )
)

# ---------- detailed monthly table for ALL event types ----------
main_all = (
    df.groupby(
        ["iso3", "country", "admin1", "admin2", "year", "month_num", "month"],
        dropna=False,
        as_index=False
    )
    .agg(
        events=("event_date", "size"),
        fatalities=("fatalities", "sum")
    )
)

main_all["event_type"] = "All"

# combine both
main = pd.concat([main_all, main_by_type], ignore_index=True)

# ---------- country-level monthly table by event type ----------
country_by_type = (
    df.groupby(
        ["iso3", "country", "year", "month_num", "month", "event_type"],
        as_index=False
    )
    .agg(
        events=("event_date", "size"),
        fatalities=("fatalities", "sum")
    )
)

# ---------- country-level monthly table for ALL event types ----------
country_all = (
    df.groupby(
        ["iso3", "country", "year", "month_num", "month"],
        as_index=False
    )
    .agg(
        events=("event_date", "size"),
        fatalities=("fatalities", "sum")
    )
)

country_all["event_type"] = "All"

# combine both
country_monthly = pd.concat([country_all, country_by_type], ignore_index=True)

# ---------- sort ----------
main = main.sort_values(
    ["year", "month_num", "country", "admin1", "admin2", "event_type"]
).reset_index(drop=True)

country_monthly = country_monthly.sort_values(
    ["year", "month_num", "country", "event_type"]
).reset_index(drop=True)

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