import pandas as pd
from pathlib import Path
import pycountry

# ==================================================
# PATHS
# ==================================================
historical_file = Path("data/raw/global/ACLED.csv")

regional_files = [
    Path("data/raw/global/regions_2026/Africa_aggregated_data_up_to_week_of-2026-03-21.xlsx"),
    Path("data/raw/global/regions_2026/Europe-Central-Asia_aggregated_data_up_to_week_of-2026-03-28.xlsx"),
    Path("data/raw/global/regions_2026/Latin-America-the-Caribbean_aggregated_data_up_to_week_of-2026-03-21.xlsx"),
    Path("data/raw/global/regions_2026/Middle-East_aggregated_data_up_to_week_of-2026-03-21.xlsx"),
    Path("data/raw/global/regions_2026/US-and-Canada_aggregated_data_up_to_week_of-2026-03-28.xlsx"),
]

output_dir = Path("data/cleaned/global")
output_dir.mkdir(parents=True, exist_ok=True)

output_main = output_dir / "conflict_standardized_monthlybytype.csv"
output_country = output_dir / "conflict_country_monthlybytype.csv"
output_admin1 = output_dir / "admin1_monthlybytype_with_centroids.csv"

# ==================================================
# CONSTANTS
# ==================================================
MIN_YEAR = 2024
MAX_YEAR = 2026

# Fix names that pycountry may not resolve directly
COUNTRY_FIXES = {
    "United States of America": "United States",
    "Russian Federation": "Russia",
    "Türkiye": "Turkey",
    "Czech Republic": "Czechia",
    "Syrian Arab Republic": "Syria",
    "Iran (Islamic Republic of)": "Iran",
    "Venezuela (Bolivarian Republic of)": "Venezuela",
    "Bolivia (Plurinational State of)": "Bolivia",
    "United Republic of Tanzania": "Tanzania",
    "Republic of Moldova": "Moldova",
    "Lao People's Democratic Republic": "Laos",
    "State of Palestine": "Palestine",
    "Democratic Republic of Congo": "Congo, The Democratic Republic of the",
    "DR Congo": "Congo, The Democratic Republic of the",
    "Congo, Dem. Rep.": "Congo, The Democratic Republic of the",
    "Congo, Rep.": "Congo",
    "Republic of the Congo": "Congo",
    "Myanmar (Burma)": "Myanmar",
    "North Macedonia": "North Macedonia",
    "Kosovo": "Kosovo",  # may remain unresolved in pycountry
}

# manual fallback for names pycountry may not resolve
COUNTRY_TO_ISO_NUMERIC_FALLBACK = {
    "Kosovo": 383,
    "Palestine": 275,
}

# ==================================================
# HELPERS
# ==================================================
def read_table(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    return pd.read_excel(path)

def clean_text_cols(df: pd.DataFrame, cols):
    for col in cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
            df[col] = df[col].replace({"nan": pd.NA, "None": pd.NA, "": pd.NA})
    return df

def get_iso_numeric(country_name):
    if pd.isna(country_name):
        return None

    name = str(country_name).strip()
    name = COUNTRY_FIXES.get(name, name)

    if name in COUNTRY_TO_ISO_NUMERIC_FALLBACK:
        return COUNTRY_TO_ISO_NUMERIC_FALLBACK[name]

    try:
        country = pycountry.countries.lookup(name)
        return int(country.numeric)
    except Exception:
        return None

# ==================================================
# 1) HISTORICAL ACLED EVENT-LEVEL DATA
# keep only 2024-2025 from ACLED to avoid overlap with 2026 regional extension
# ==================================================
hist = read_table(historical_file)

print("Historical original columns:")
print(hist.columns.tolist())

rename_map_hist = {
    "iso": "iso3",
    "country": "country",
    "admin1": "admin1",
    "admin2": "admin2",
    "event_date": "event_date",
    "event_type": "event_type",
    "fatalities": "fatalities",
    "population_best": "population_best",
}

hist = hist.rename(columns=rename_map_hist)

needed_hist = [
    "iso3",
    "country",
    "admin1",
    "admin2",
    "event_date",
    "event_type",
    "fatalities",
    "population_best",
]

missing_hist = [c for c in needed_hist if c not in hist.columns]
if missing_hist:
    raise ValueError(f"Missing expected historical columns: {missing_hist}")

hist = hist[needed_hist].copy()
hist = clean_text_cols(hist, ["iso3", "country", "admin1", "admin2", "event_type"])

hist["event_date"] = pd.to_datetime(hist["event_date"], errors="coerce")
hist = hist[hist["event_date"].notna()].copy()

hist["year"] = hist["event_date"].dt.year
hist["month_num"] = hist["event_date"].dt.month
hist["month"] = hist["event_date"].dt.strftime("%B")

hist["fatalities"] = pd.to_numeric(hist["fatalities"], errors="coerce").fillna(0)
hist["population_exposure"] = pd.to_numeric(hist["population_best"], errors="coerce").fillna(0)
hist["iso3"] = pd.to_numeric(hist["iso3"], errors="coerce")

hist = hist[
    hist["country"].notna()
    & hist["iso3"].notna()
    & hist["event_type"].notna()
].copy()

hist["iso3"] = hist["iso3"].astype(int)

# only 2024-2025 from historical ACLED
hist = hist[hist["year"].between(2024, 2025)].copy()

# detailed monthly admin table
hist_main_by_type = (
    hist.groupby(
        ["iso3", "country", "admin1", "admin2", "year", "month_num", "month", "event_type"],
        dropna=False,
        as_index=False
    )
    .agg(
        events=("event_date", "size"),
        fatalities=("fatalities", "sum"),
        population_exposure=("population_exposure", "sum"),
    )
)

hist_main_all = (
    hist.groupby(
        ["iso3", "country", "admin1", "admin2", "year", "month_num", "month"],
        dropna=False,
        as_index=False
    )
    .agg(
        events=("event_date", "size"),
        fatalities=("fatalities", "sum"),
        population_exposure=("population_exposure", "sum"),
    )
)

hist_main_all["event_type"] = "All"
hist_main = pd.concat([hist_main_all, hist_main_by_type], ignore_index=True)

# historical country monthly
hist_country_by_type = (
    hist.groupby(
        ["iso3", "country", "year", "month_num", "month", "event_type"],
        as_index=False
    )
    .agg(
        events=("event_date", "size"),
        fatalities=("fatalities", "sum"),
        population_exposure=("population_exposure", "sum"),
    )
)

hist_country_all = (
    hist.groupby(
        ["iso3", "country", "year", "month_num", "month"],
        as_index=False
    )
    .agg(
        events=("event_date", "size"),
        fatalities=("fatalities", "sum"),
        population_exposure=("population_exposure", "sum"),
    )
)

hist_country_all["event_type"] = "All"
hist_country_monthly = pd.concat([hist_country_all, hist_country_by_type], ignore_index=True)

# ==================================================
# 2) REGIONAL AGGREGATED FILES
# use these for 2024-2026 admin1 bubbles and 2026 extension
# ==================================================
regional_frames = []

for file_path in regional_files:
    print(f"\nReading regional file: {file_path.name}")
    df = read_table(file_path)
    print(df.columns.tolist())

    rename_map_reg = {
        "WEEK": "event_date",
        "COUNTRY": "country",
        "ADMIN1": "admin1",
        "EVENT_TYPE": "event_type",
        "EVENTS": "events",
        "FATALITIES": "fatalities",
        "POPULATION_EXPOSURE": "population_exposure",
        "CENTROID_LATITUDE": "centroid_latitude",
        "CENTROID_LONGITUDE": "centroid_longitude",
        "ISO3": "iso3",
    }

    df = df.rename(columns=rename_map_reg)

    needed_reg = [
        "event_date",
        "country",
        "admin1",
        "event_type",
        "events",
        "fatalities",
        "population_exposure",
        "centroid_latitude",
        "centroid_longitude",
    ]

    missing_reg = [c for c in needed_reg if c not in df.columns]
    if missing_reg:
        raise ValueError(f"{file_path.name} is missing expected columns: {missing_reg}")

    df = df[needed_reg].copy()
    df = clean_text_cols(df, ["country", "admin1", "event_type"])

    df["event_date"] = pd.to_datetime(df["event_date"], errors="coerce")
    df = df[df["event_date"].notna()].copy()

    df["year"] = df["event_date"].dt.year
    df["month_num"] = df["event_date"].dt.month
    df["month"] = df["event_date"].dt.strftime("%B")

    df["events"] = pd.to_numeric(df["events"], errors="coerce").fillna(0)
    df["fatalities"] = pd.to_numeric(df["fatalities"], errors="coerce").fillna(0)
    df["population_exposure"] = pd.to_numeric(df["population_exposure"], errors="coerce").fillna(0)
    df["centroid_latitude"] = pd.to_numeric(df["centroid_latitude"], errors="coerce")
    df["centroid_longitude"] = pd.to_numeric(df["centroid_longitude"], errors="coerce")

    # add ISO numeric from country name
    df["country"] = df["country"].replace(COUNTRY_FIXES)
    df["iso3"] = df["country"].apply(get_iso_numeric)

    unresolved = sorted(df.loc[df["iso3"].isna(), "country"].dropna().unique().tolist())
    if unresolved:
        print(f"\nUnresolved country names in {file_path.name}:")
        print(unresolved)

    df = df[
        df["country"].notna()
        & df["event_type"].notna()
        & df["iso3"].notna()
    ].copy()

    df["iso3"] = df["iso3"].astype(int)

    # only 2024-2026
    df = df[df["year"].between(MIN_YEAR, MAX_YEAR)].copy()

    regional_frames.append(df)

if not regional_frames:
    raise ValueError("No regional files were loaded.")

reg = pd.concat(regional_frames, ignore_index=True)
reg = reg.drop_duplicates().reset_index(drop=True)

# ==================================================
# 3) COUNTRY MONTHLY OUTPUT
# historical 2024-2025 + regional 2026
# ==================================================
reg_2026 = reg[reg["year"] == 2026].copy()

reg_country_by_type_2026 = (
    reg_2026.groupby(
        ["iso3", "country", "year", "month_num", "month", "event_type"],
        as_index=False
    )
    .agg(
        events=("events", "sum"),
        fatalities=("fatalities", "sum"),
        population_exposure=("population_exposure", "sum"),
    )
)

reg_country_all_2026 = (
    reg_2026.groupby(
        ["iso3", "country", "year", "month_num", "month"],
        as_index=False
    )
    .agg(
        events=("events", "sum"),
        fatalities=("fatalities", "sum"),
        population_exposure=("population_exposure", "sum"),
    )
)

reg_country_all_2026["event_type"] = "All"
reg_country_monthly_2026 = pd.concat([reg_country_all_2026, reg_country_by_type_2026], ignore_index=True)

country_monthly = pd.concat([hist_country_monthly, reg_country_monthly_2026], ignore_index=True)

# keep only 2024-2026
country_monthly = country_monthly[country_monthly["year"].between(MIN_YEAR, MAX_YEAR)].copy()

# ==================================================
# 4) ADMIN1 MONTHLY WITH CENTROIDS (from regional files)
# this is for 2024-2026
# ==================================================
reg_2024_2026 = reg[reg["year"].between(MIN_YEAR, MAX_YEAR)].copy()

admin1_by_type = (
    reg_2024_2026.groupby(
        ["iso3", "country", "admin1", "year", "month_num", "month", "event_type"],
        as_index=False
    )
    .agg(
        events=("events", "sum"),
        fatalities=("fatalities", "sum"),
        population_exposure=("population_exposure", "sum"),
        centroid_latitude=("centroid_latitude", "mean"),
        centroid_longitude=("centroid_longitude", "mean"),
    )
)

admin1_all = (
    reg_2024_2026.groupby(
        ["iso3", "country", "admin1", "year", "month_num", "month"],
        as_index=False
    )
    .agg(
        events=("events", "sum"),
        fatalities=("fatalities", "sum"),
        population_exposure=("population_exposure", "sum"),
        centroid_latitude=("centroid_latitude", "mean"),
        centroid_longitude=("centroid_longitude", "mean"),
    )
)

admin1_all["event_type"] = "All"
admin1_monthly = pd.concat([admin1_all, admin1_by_type], ignore_index=True)

# ==================================================
# 5) ADMIN DETAILED OUTPUT
# historical ACLED detailed output only
# keep only 2024-2025 because regional files are admin1 aggregated, not admin2 event-level
# ==================================================
main = hist_main.copy()
main = main[main["year"].between(MIN_YEAR, MAX_YEAR)].copy()

# ==================================================
# 6) SORT
# ==================================================
main = main.sort_values(
    ["year", "month_num", "country", "admin1", "admin2", "event_type"]
).reset_index(drop=True)

country_monthly = country_monthly.sort_values(
    ["year", "month_num", "country", "event_type"]
).reset_index(drop=True)

admin1_monthly = admin1_monthly.sort_values(
    ["year", "month_num", "country", "admin1", "event_type"]
).reset_index(drop=True)

# ==================================================
# 7) SAVE
# ==================================================
main.to_csv(output_main, index=False, encoding="utf-8-sig")
country_monthly.to_csv(output_country, index=False, encoding="utf-8-sig")
admin1_monthly.to_csv(output_admin1, index=False, encoding="utf-8-sig")

print("\nSaved:")
print(output_main)
print(output_country)
print(output_admin1)

print("\nDetailed historical admin sample:")
print(main.head())

print("\nCountry monthly sample:")
print(country_monthly.head())

print("\nAdmin1 monthly sample:")
print(admin1_monthly.head())