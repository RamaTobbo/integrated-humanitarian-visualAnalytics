import pandas as pd
from pathlib import Path

# ==================================================
# PATHS
# ==================================================
historical_file = Path("data/raw/global/ACLED.csv")
middle_east_file = Path("data/raw/global/Middle-East_aggregated_data_up_to_week_of-2026-03-21.xlsx")

output_dir = Path("data/cleaned/global")
output_dir.mkdir(parents=True, exist_ok=True)

# historical detailed admin file (same structure as before)
output_main = output_dir / "conflict_standardized_monthlybytype.csv"

# updated country file with 2024 + 2025 + 2026
output_country = output_dir / "conflict_country_monthlybytype.csv"

# new file for bubble maps / selected-country zoom / admin1 monthly view
output_admin1_bubbles = output_dir / "middle_east_admin1_monthlybytype_with_centroids.csv"

# ==================================================
# COUNTRY -> ISO NUMERIC CODE
# app uses numeric ISO through the old "iso3" column
# ==================================================
COUNTRY_TO_ISO_NUMERIC = {
    "Bahrain": 48,
    "Iran": 364,
    "Iraq": 368,
    "Israel": 376,
    "Jordan": 400,
    "Kuwait": 414,
    "Lebanon": 422,
    "Oman": 512,
    "Palestine": 275,
    "Qatar": 634,
    "Saudi Arabia": 682,
    "Syria": 760,
    "Turkey": 792,
    "United Arab Emirates": 784,
    "Yemen": 887,
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


# ==================================================
# 1) HISTORICAL ACLED EVENT-LEVEL DATA
#    use this for detailed admin output and historical country output
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
}

hist = hist.rename(columns=rename_map_hist)

needed_hist = ["iso3", "country", "admin1", "admin2", "event_date", "event_type", "fatalities"]
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
hist["iso3"] = pd.to_numeric(hist["iso3"], errors="coerce")

hist = hist[
    hist["country"].notna()
    & hist["iso3"].notna()
    & hist["event_type"].notna()
].copy()

hist["iso3"] = hist["iso3"].astype(int)

# keep historical part until end of 2025 to avoid overlap with 2026 extension
hist = hist[hist["year"] <= 2025].copy()

# detailed monthly table with event type
main_by_type = (
    hist.groupby(
        ["iso3", "country", "admin1", "admin2", "year", "month_num", "month", "event_type"],
        dropna=False,
        as_index=False
    )
    .agg(
        events=("event_date", "size"),
        fatalities=("fatalities", "sum")
    )
)

# detailed monthly table for ALL event types
main_all = (
    hist.groupby(
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

main = pd.concat([main_all, main_by_type], ignore_index=True)

# historical country monthly by type
hist_country_by_type = (
    hist.groupby(
        ["iso3", "country", "year", "month_num", "month", "event_type"],
        as_index=False
    )
    .agg(
        events=("event_date", "size"),
        fatalities=("fatalities", "sum")
    )
)

hist_country_all = (
    hist.groupby(
        ["iso3", "country", "year", "month_num", "month"],
        as_index=False
    )
    .agg(
        events=("event_date", "size"),
        fatalities=("fatalities", "sum")
    )
)

hist_country_all["event_type"] = "All"
hist_country_monthly = pd.concat([hist_country_all, hist_country_by_type], ignore_index=True)

# ==================================================
# 2) MIDDLE EAST WEEKLY AGGREGATED FILE
#    use this to extend country data to 2026
#    and build admin1 bubble data for 2024-2026
# ==================================================
me = read_table(middle_east_file)

print("\nMiddle East original columns:")
print(me.columns.tolist())

rename_map_me = {
    "WEEK": "event_date",
    "COUNTRY": "country",
    "ADMIN1": "admin1",
    "EVENT_TYPE": "event_type",
    "EVENTS": "events",
    "FATALITIES": "fatalities",
    "POPULATION_EXPOSURE": "population_exposure",
    "CENTROID_LATITUDE": "centroid_latitude",
    "CENTROID_LONGITUDE": "centroid_longitude",
}

me = me.rename(columns=rename_map_me)

needed_me = [
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

missing_me = [c for c in needed_me if c not in me.columns]
if missing_me:
    raise ValueError(f"Missing expected Middle East columns: {missing_me}")

me = me[needed_me].copy()
me = clean_text_cols(me, ["country", "admin1", "event_type"])

me["event_date"] = pd.to_datetime(me["event_date"], errors="coerce")
me = me[me["event_date"].notna()].copy()

me["year"] = me["event_date"].dt.year
me["month_num"] = me["event_date"].dt.month
me["month"] = me["event_date"].dt.strftime("%B")

me["events"] = pd.to_numeric(me["events"], errors="coerce").fillna(0)
me["fatalities"] = pd.to_numeric(me["fatalities"], errors="coerce").fillna(0)
me["population_exposure"] = pd.to_numeric(me["population_exposure"], errors="coerce").fillna(0)
me["centroid_latitude"] = pd.to_numeric(me["centroid_latitude"], errors="coerce")
me["centroid_longitude"] = pd.to_numeric(me["centroid_longitude"], errors="coerce")

me = me[
    me["country"].notna()
    & me["event_type"].notna()
].copy()

# map country to numeric ISO for world country file
me["iso3"] = me["country"].map(COUNTRY_TO_ISO_NUMERIC)

missing_iso = sorted(me.loc[me["iso3"].isna(), "country"].dropna().unique().tolist())
if missing_iso:
    raise ValueError(f"Missing ISO numeric mapping for countries: {missing_iso}")

me["iso3"] = me["iso3"].astype(int)

# --------------------------------------------------
# country monthly from 2026 only
# this extends your current world/country timeline
# --------------------------------------------------
me_2026 = me[me["year"] == 2026].copy()

me_country_by_type_2026 = (
    me_2026.groupby(
        ["iso3", "country", "year", "month_num", "month", "event_type"],
        as_index=False
    )
    .agg(
        events=("events", "sum"),
        fatalities=("fatalities", "sum")
    )
)

me_country_all_2026 = (
    me_2026.groupby(
        ["iso3", "country", "year", "month_num", "month"],
        as_index=False
    )
    .agg(
        events=("events", "sum"),
        fatalities=("fatalities", "sum")
    )
)

me_country_all_2026["event_type"] = "All"

me_country_monthly_2026 = pd.concat(
    [me_country_all_2026, me_country_by_type_2026],
    ignore_index=True
)

# combine historical global file + 2026 Middle East extension
country_monthly = pd.concat(
    [hist_country_monthly, me_country_monthly_2026],
    ignore_index=True
)

# --------------------------------------------------
# admin1 monthly with centroids for 2024-2026
# this is for your selected-country zoom + bubble map
# --------------------------------------------------
me_2024_2026 = me[me["year"].between(2024, 2026)].copy()

admin1_by_type = (
    me_2024_2026.groupby(
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
    me_2024_2026.groupby(
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
# SORT
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
# SAVE
# ==================================================
main.to_csv(output_main, index=False, encoding="utf-8-sig")
country_monthly.to_csv(output_country, index=False, encoding="utf-8-sig")
admin1_monthly.to_csv(output_admin1_bubbles, index=False, encoding="utf-8-sig")

print("\nSaved:")
print(output_main)
print(output_country)
print(output_admin1_bubbles)

print("\nHistorical detailed sample:")
print(main.head())

print("\nUpdated country monthly sample:")
print(country_monthly.head())

print("\nAdmin1 bubble sample:")
print(admin1_monthly.head())