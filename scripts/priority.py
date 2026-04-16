from pathlib import Path
import pandas as pd
import numpy as np

# ==================================================
# PATHS
# ==================================================
acled_files = [
    Path("data/raw/global/regions_2026/Africa_aggregated_data_up_to_week_of-2026-03-21.xlsx"),
    Path("data/raw/global/regions_2026/Europe-Central-Asia_aggregated_data_up_to_week_of-2026-03-28.xlsx"),
    Path("data/raw/global/regions_2026/Latin-America-the-Caribbean_aggregated_data_up_to_week_of-2026-03-21.xlsx"),
    Path("data/raw/global/regions_2026/Middle-East_aggregated_data_up_to_week_of-2026-03-21.xlsx"),
    Path("data/raw/global/regions_2026/US-and-Canada_aggregated_data_up_to_week_of-2026-03-28.xlsx"),
]



displacement_path = Path("data/cleaned/global/displacement_cleaned_2024_2026.csv")

output_dir = Path("data/cleaned/global")
output_dir.mkdir(parents=True, exist_ok=True)

output_admin1 = output_dir / "global_priority_admin1_with_displacement_monthly.csv"
output_country = output_dir / "global_priority_country_with_displacement_monthly.csv"

# ==================================================
# HELPERS
# ==================================================
def normalize_text(value):
    if pd.isna(value):
        return None
    value = str(value).strip().lower()
    value = value.replace("–", "-").replace("—", "-")
    value = value.replace("_", " ")
    value = " ".join(value.split())
    return value

def safe_numeric(series):
    return pd.to_numeric(series, errors="coerce").fillna(0)

def minmax(series):
    s = pd.to_numeric(series, errors="coerce").fillna(0)
    smin = s.min()
    smax = s.max()
    if smax == smin:
        return pd.Series([0.0] * len(s), index=s.index)
    return (s - smin) / (smax - smin)

def make_priority_class(series):
    q1 = series.quantile(0.25)
    q2 = series.quantile(0.50)
    q3 = series.quantile(0.75)

    def classify(x):
        if x >= q3:
            return "very high"
        elif x >= q2:
            return "high"
        elif x >= q1:
            return "medium"
        else:
            return "low"

    return series.apply(classify)

# ==================================================
# LOAD ACLED FILES
# ==================================================
acled_dfs = []

for file_path in acled_files:
    df = pd.read_excel(file_path)
    df.columns = [str(c).strip().upper() for c in df.columns]
    acled_dfs.append(df)

acled = pd.concat(acled_dfs, ignore_index=True)

# ==================================================
# CLEAN ACLED
# ==================================================
acled["WEEK"] = pd.to_datetime(acled["WEEK"], errors="coerce")
acled = acled.dropna(subset=["WEEK"]).copy()

acled["REGION"] = acled["REGION"].apply(normalize_text)
acled["COUNTRY"] = acled["COUNTRY"].apply(normalize_text)
acled["ADMIN1"] = acled["ADMIN1"].apply(normalize_text)
acled["EVENT_TYPE"] = acled["EVENT_TYPE"].apply(normalize_text)
acled["SUB_EVENT_TYPE"] = acled["SUB_EVENT_TYPE"].apply(normalize_text)
acled["DISORDER_TYPE"] = acled["DISORDER_TYPE"].apply(normalize_text)

acled["EVENTS"] = safe_numeric(acled["EVENTS"])
acled["FATALITIES"] = safe_numeric(acled["FATALITIES"])
acled["POPULATION_EXPOSURE"] = safe_numeric(acled["POPULATION_EXPOSURE"])
acled["CENTROID_LATITUDE"] = pd.to_numeric(acled["CENTROID_LATITUDE"], errors="coerce")
acled["CENTROID_LONGITUDE"] = pd.to_numeric(acled["CENTROID_LONGITUDE"], errors="coerce")

acled["year"] = acled["WEEK"].dt.year
acled["month_num"] = acled["WEEK"].dt.month
acled["month"] = acled["WEEK"].dt.strftime("%B")

# ==================================================
# MONTHLY ACLED AGGREGATION AT ADMIN1
# ==================================================
admin1_monthly = (
    acled.groupby(
        ["REGION", "COUNTRY", "ADMIN1", "year", "month_num", "month"],
        as_index=False
    )
    .agg({
        "EVENTS": "sum",
        "FATALITIES": "sum",
        "POPULATION_EXPOSURE": "sum",
        "CENTROID_LATITUDE": "mean",
        "CENTROID_LONGITUDE": "mean",
    })
    .rename(columns={
        "REGION": "region",
        "COUNTRY": "country",
        "ADMIN1": "admin1_norm",
        "EVENTS": "events",
        "FATALITIES": "fatalities",
        "POPULATION_EXPOSURE": "population_exposure",
        "CENTROID_LATITUDE": "centroid_latitude",
        "CENTROID_LONGITUDE": "centroid_longitude",
    })
)

admin1_monthly = admin1_monthly.dropna(subset=["country", "admin1_norm"]).copy()

# ==================================================
# LOAD DISPLACEMENT
# ==================================================
displacement = pd.read_csv(displacement_path)
displacement.columns = [str(c).strip() for c in displacement.columns]

# ==================================================
# CLEAN DISPLACEMENT
# admin0Name = country
# admin1Name = destination admin1
# numPresentIdpInd = number of displaced people present
# ==================================================
displacement = displacement.rename(columns={
    "admin0Name": "country",
    "admin1Name": "admin1_norm",
    "numPresentIdpInd": "displaced",
    "yearReportingDate": "year",
    "monthReportingDate": "month_num",
})

displacement["country"] = displacement["country"].apply(normalize_text)
displacement["admin1_norm"] = displacement["admin1_norm"].apply(normalize_text)

displacement["year"] = pd.to_numeric(displacement["year"], errors="coerce")
displacement["month_num"] = pd.to_numeric(displacement["month_num"], errors="coerce")
displacement["displaced"] = pd.to_numeric(displacement["displaced"], errors="coerce").fillna(0)

# keep only needed columns
displacement = displacement[
    ["country", "admin1_norm", "year", "month_num", "displaced"]
].copy()

# aggregate in case there are multiple rows per admin1/month
displacement = (
    displacement.groupby(["country", "admin1_norm", "year", "month_num"], as_index=False)
    .agg({"displaced": "sum"})
)

# ==================================================
# MERGE ACLED + DISPLACEMENT
# ==================================================
admin1_monthly = admin1_monthly.merge(
    displacement,
    on=["country", "admin1_norm", "year", "month_num"],
    how="left"
)

admin1_monthly["displaced"] = admin1_monthly["displaced"].fillna(0)

# ==================================================
# LOG TRANSFORMS
# ==================================================
admin1_monthly["events_log"] = np.log1p(admin1_monthly["events"])
admin1_monthly["fatalities_log"] = np.log1p(admin1_monthly["fatalities"])
admin1_monthly["exposure_log"] = np.log1p(admin1_monthly["population_exposure"])
admin1_monthly["displaced_log"] = np.log1p(admin1_monthly["displaced"])

# ==================================================
# COUNTRY-LEVEL NORMALIZATION
# compare admin1 INSIDE the same country/month
# ==================================================
admin1_monthly["events_norm_country"] = (
    admin1_monthly.groupby(["country", "year", "month_num"])["events_log"]
    .transform(minmax)
)

admin1_monthly["fatalities_norm_country"] = (
    admin1_monthly.groupby(["country", "year", "month_num"])["fatalities_log"]
    .transform(minmax)
)

admin1_monthly["exposure_norm_country"] = (
    admin1_monthly.groupby(["country", "year", "month_num"])["exposure_log"]
    .transform(minmax)
)

admin1_monthly["displaced_norm_country"] = (
    admin1_monthly.groupby(["country", "year", "month_num"])["displaced_log"]
    .transform(minmax)
)

# ==================================================
# GLOBAL NORMALIZATION
# compare all admin1 worldwide in same month
# ==================================================
admin1_monthly["events_norm_global"] = (
    admin1_monthly.groupby(["year", "month_num"])["events_log"]
    .transform(minmax)
)

admin1_monthly["fatalities_norm_global"] = (
    admin1_monthly.groupby(["year", "month_num"])["fatalities_log"]
    .transform(minmax)
)

admin1_monthly["exposure_norm_global"] = (
    admin1_monthly.groupby(["year", "month_num"])["exposure_log"]
    .transform(minmax)
)

admin1_monthly["displaced_norm_global"] = (
    admin1_monthly.groupby(["year", "month_num"])["displaced_log"]
    .transform(minmax)
)

# ==================================================
# PRIORITY SCORE
# conflict + displacement + exposure
# ==================================================
admin1_monthly["priority_score_country"] = (
    0.35 * admin1_monthly["events_norm_country"] +
    0.35 * admin1_monthly["fatalities_norm_country"] +
    0.20 * admin1_monthly["displaced_norm_country"] +
    0.10 * admin1_monthly["exposure_norm_country"]
)

admin1_monthly["priority_score_global"] = (
    0.35 * admin1_monthly["events_norm_global"] +
    0.35 * admin1_monthly["fatalities_norm_global"] +
    0.20 * admin1_monthly["displaced_norm_global"] +
    0.10 * admin1_monthly["exposure_norm_global"]
)

# ==================================================
# RANKS
# ==================================================
admin1_monthly["priority_rank_country"] = (
    admin1_monthly.groupby(["country", "year", "month_num"])["priority_score_country"]
    .rank(method="dense", ascending=False)
    .astype(int)
)

admin1_monthly["priority_rank_global"] = (
    admin1_monthly.groupby(["year", "month_num"])["priority_score_global"]
    .rank(method="dense", ascending=False)
    .astype(int)
)

# ==================================================
# PRIORITY CLASSES
# ==================================================
admin1_monthly["priority_class_country"] = (
    admin1_monthly.groupby(["country", "year", "month_num"])["priority_score_country"]
    .transform(make_priority_class)
)

admin1_monthly["priority_class_global"] = (
    admin1_monthly.groupby(["year", "month_num"])["priority_score_global"]
    .transform(make_priority_class)
)

# ==================================================
# FINAL ADMIN1 OUTPUT
# ==================================================
admin1_monthly = admin1_monthly[
    [
        "region",
        "country",
        "admin1_norm",
        "year",
        "month_num",
        "month",
        "events",
        "fatalities",
        "population_exposure",
        "displaced",
        "centroid_latitude",
        "centroid_longitude",
        "events_norm_country",
        "fatalities_norm_country",
        "displaced_norm_country",
        "exposure_norm_country",
        "priority_score_country",
        "priority_rank_country",
        "priority_class_country",
        "events_norm_global",
        "fatalities_norm_global",
        "displaced_norm_global",
        "exposure_norm_global",
        "priority_score_global",
        "priority_rank_global",
        "priority_class_global",
    ]
].sort_values(
    ["year", "month_num", "priority_score_global", "country", "admin1_norm"],
    ascending=[True, True, False, True, True]
).reset_index(drop=True)

# ==================================================
# COUNTRY-LEVEL OUTPUT
# for world choropleth
# ==================================================
country_monthly = (
    admin1_monthly.groupby(
        ["region", "country", "year", "month_num", "month"],
        as_index=False
    )
    .agg({
        "events": "sum",
        "fatalities": "sum",
        "population_exposure": "sum",
        "displaced": "sum",
    })
)

country_monthly["events_log"] = np.log1p(country_monthly["events"])
country_monthly["fatalities_log"] = np.log1p(country_monthly["fatalities"])
country_monthly["exposure_log"] = np.log1p(country_monthly["population_exposure"])
country_monthly["displaced_log"] = np.log1p(country_monthly["displaced"])

country_monthly["events_norm"] = (
    country_monthly.groupby(["year", "month_num"])["events_log"]
    .transform(minmax)
)

country_monthly["fatalities_norm"] = (
    country_monthly.groupby(["year", "month_num"])["fatalities_log"]
    .transform(minmax)
)

country_monthly["exposure_norm"] = (
    country_monthly.groupby(["year", "month_num"])["exposure_log"]
    .transform(minmax)
)

country_monthly["displaced_norm"] = (
    country_monthly.groupby(["year", "month_num"])["displaced_log"]
    .transform(minmax)
)

country_monthly["country_priority_score"] = (
    0.35 * country_monthly["events_norm"] +
    0.35 * country_monthly["fatalities_norm"] +
    0.20 * country_monthly["displaced_norm"] +
    0.10 * country_monthly["exposure_norm"]
)

country_monthly["country_priority_rank"] = (
    country_monthly.groupby(["year", "month_num"])["country_priority_score"]
    .rank(method="dense", ascending=False)
    .astype(int)
)

country_monthly["country_priority_class"] = (
    country_monthly.groupby(["year", "month_num"])["country_priority_score"]
    .transform(make_priority_class)
)

country_monthly = country_monthly.sort_values(
    ["year", "month_num", "country_priority_score", "country"],
    ascending=[True, True, False, True]
).reset_index(drop=True)

# ==================================================
# SAVE
# ==================================================
admin1_monthly.to_csv(output_admin1, index=False)
country_monthly.to_csv(output_country, index=False)

print("Saved admin1 file:", output_admin1)
print("Saved country file:", output_country)

print("\nAdmin1 sample:")
print(admin1_monthly.head(10))

print("\nCountry sample:")
print(country_monthly.head(10))

print("\nCheck displacement merge:")
print(admin1_monthly[["country", "admin1_norm", "year", "month_num", "displaced"]].head(20))