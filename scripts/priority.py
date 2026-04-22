from pathlib import Path
import pandas as pd
import numpy as np
import unicodedata
import re

from need_utils import (
    build_education_score,
    build_health_score,
    clean_country_names,
    load_need_data,
    merge_need_scores,
)
from lebanon_displacement_fallback import (
    DISPLACEMENT_ADJUSTED_FLAG_COL,
    DISPLACEMENT_SOURCE_NOTE_COL,
    apply_lebanon_displacement_fallback,
    combine_unique_text,
    ensure_displacement_metadata,
    summarize_country_months,
)

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

displacement_dest_path = Path("data/cleaned/global/displacement_admin1_destination_monthly_2024_2026.csv")

output_dir = Path("data/cleaned/global")
output_dir.mkdir(parents=True, exist_ok=True)

output_admin1 = output_dir / "global_priority_admin1_with_displacement_monthly.csv"
output_country = output_dir / "global_priority_country_with_displacement_monthly.csv"

# ==================================================
# CONSTANTS
# ==================================================
MIN_YEAR = 2024
MAX_YEAR = 2026
COUNTRY_PRIORITY_WEIGHTS = {
    "events_norm": 0.30,
    "fatalities_norm": 0.30,
    "displaced_norm": 0.18,
    "exposure_norm": 0.07,
    "health_priority_score": 0.075,
    "education_priority_score": 0.075,
}

# ==================================================
# HELPERS
# ==================================================
def normalize_text(value):
    if pd.isna(value):
        return None
    value = str(value).strip().lower()
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.replace("–", "-").replace("—", "-")
    value = value.replace("_", " ")
    value = value.replace("/", " ")
    value = value.replace(",", " ")
    value = value.replace("’", "'")
    value = re.sub(r"\s+", " ", value).strip()
    return value


def standardize_country(value):
    return clean_country_names(value)


def standardize_admin1(value, country=None):
    value = normalize_text(value)
    country = standardize_country(country)

    if value is None or value in {"", "nan", "none", "not available", "unknown"}:
        return None

    if country == "lebanon":
        mapping = {
            "akkar": "akkar",
            "aakkar": "akkar",

            "beirut": "beirut",
            "beyrouth": "beirut",

            "baabda": "mount lebanon",
            "aley": "mount lebanon",
            "aaley": "mount lebanon",
            "chouf": "mount lebanon",
            "shouf": "mount lebanon",
            "el metn": "mount lebanon",
            "metn": "mount lebanon",
            "matn": "mount lebanon",
            "kesrouan": "mount lebanon",
            "keserwan": "mount lebanon",
            "jbeil": "mount lebanon",
            "byblos": "mount lebanon",
            "mount lebanon": "mount lebanon",
            "mont liban": "mount lebanon",
            "mont-liban": "mount lebanon",
            "keserwan-jbeil": "mount lebanon",
            "keserwan jbeil": "mount lebanon",

            "tripoli": "north",
            "zgharta": "north",
            "batroun": "north",
            "koura": "north",
            "bcharre": "north",
            "bsharri": "north",
            "minieh dinnieh": "north",
            "minieh-dinnieh": "north",
            "north": "north",
            "liban nord": "north",
            "liban-nord": "north",

            "zahle": "bekaa",
            "zahleh": "bekaa",
            "west bekaa": "bekaa",
            "rachaya": "bekaa",
            "rashaya": "bekaa",
            "bekaa": "bekaa",
            "beqaa": "bekaa",

            "baalbek": "baalbek-hermel",
            "hermel": "baalbek-hermel",
            "baalbek hermel": "baalbek-hermel",
            "baalbek-hermel": "baalbek-hermel",

            "tyre": "south",
            "sour": "south",
            "saida": "south",
            "sidon": "south",
            "jezzine": "south",
            "south": "south",
            "liban sud": "south",
            "liban-sud": "south",

            "nabatiyeh": "al nabatieh",
            "nabatiye": "al nabatieh",
            "nabatyeh": "al nabatieh",
            "nabatye": "al nabatieh",
            "marjayoun": "al nabatieh",
            "marjaayoun": "al nabatieh",
            "bint jbeil": "al nabatieh",
            "bent jbail": "al nabatieh",
            "hasbaya": "al nabatieh",
            "al nabatieh": "al nabatieh",
        }
        return mapping.get(value, value)

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
required_acled_cols = [
    "WEEK",
    "REGION",
    "COUNTRY",
    "ADMIN1",
    "EVENTS",
    "FATALITIES",
    "POPULATION_EXPOSURE",
    "CENTROID_LATITUDE",
    "CENTROID_LONGITUDE",
]
missing_acled = [c for c in required_acled_cols if c not in acled.columns]
if missing_acled:
    raise ValueError(f"Missing ACLED columns: {missing_acled}")

acled["WEEK"] = pd.to_datetime(acled["WEEK"], errors="coerce")
acled = acled.dropna(subset=["WEEK"]).copy()

acled["REGION"] = acled["REGION"].apply(normalize_text)
acled["COUNTRY"] = acled["COUNTRY"].apply(standardize_country)
acled["ADMIN1"] = acled.apply(
    lambda r: standardize_admin1(r["ADMIN1"], r["COUNTRY"]),
    axis=1
)

if "EVENT_TYPE" in acled.columns:
    acled["EVENT_TYPE"] = acled["EVENT_TYPE"].apply(normalize_text)
if "SUB_EVENT_TYPE" in acled.columns:
    acled["SUB_EVENT_TYPE"] = acled["SUB_EVENT_TYPE"].apply(normalize_text)
if "DISORDER_TYPE" in acled.columns:
    acled["DISORDER_TYPE"] = acled["DISORDER_TYPE"].apply(normalize_text)

acled["EVENTS"] = safe_numeric(acled["EVENTS"])
acled["FATALITIES"] = safe_numeric(acled["FATALITIES"])
acled["POPULATION_EXPOSURE"] = safe_numeric(acled["POPULATION_EXPOSURE"])
acled["CENTROID_LATITUDE"] = pd.to_numeric(acled["CENTROID_LATITUDE"], errors="coerce")
acled["CENTROID_LONGITUDE"] = pd.to_numeric(acled["CENTROID_LONGITUDE"], errors="coerce")

acled["year"] = acled["WEEK"].dt.year
acled["month_num"] = acled["WEEK"].dt.month
acled["month"] = acled["WEEK"].dt.strftime("%B")

acled = acled[acled["year"].between(MIN_YEAR, MAX_YEAR)].copy()
acled = acled.dropna(subset=["COUNTRY", "ADMIN1"]).copy()

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
# Admin1 displacement stock snapshots.
# ==================================================
if not displacement_dest_path.exists():
    displacement = pd.DataFrame(
        columns=[
            "country",
            "admin1_norm",
            "year",
            "month_num",
            "displaced_in",
            DISPLACEMENT_ADJUSTED_FLAG_COL,
            DISPLACEMENT_SOURCE_NOTE_COL,
        ]
    )
else:
    displacement = pd.read_csv(displacement_dest_path)
    displacement.columns = [str(c).strip() for c in displacement.columns]

required_disp_cols = ["country", "admin1_norm", "year", "month_num", "displaced_in"]
missing_disp = [col for col in required_disp_cols if col not in displacement.columns]
if missing_disp:
    raise ValueError(f"Missing displacement columns in {displacement_dest_path}: {missing_disp}")

displacement["country"] = displacement["country"].apply(standardize_country)
displacement["admin1_norm"] = displacement.apply(
    lambda r: standardize_admin1(r["admin1_norm"], r["country"]),
    axis=1,
)
displacement["admin1_norm"] = displacement["admin1_norm"].replace({
    "baalbek-el hermel": "baalbek-hermel",
    "baalbek el hermel": "baalbek-hermel",
    "el nabatieh": "al nabatieh",
    "nabatieh": "al nabatieh",
})
displacement["year"] = pd.to_numeric(displacement["year"], errors="coerce")
displacement["month_num"] = pd.to_numeric(displacement["month_num"], errors="coerce")
displacement["displaced_in"] = pd.to_numeric(displacement["displaced_in"], errors="coerce").fillna(0)
displacement = ensure_displacement_metadata(displacement)
displacement = apply_lebanon_displacement_fallback(displacement, value_col="displaced_in")

displacement = displacement[
    displacement["year"].between(MIN_YEAR, MAX_YEAR)
].copy()

displacement = displacement[
    [
        "country",
        "admin1_norm",
        "year",
        "month_num",
        "displaced_in",
        DISPLACEMENT_ADJUSTED_FLAG_COL,
        DISPLACEMENT_SOURCE_NOTE_COL,
    ]
].copy()

displacement = displacement.dropna(subset=["country", "admin1_norm", "year", "month_num"])

displacement = (
    displacement.groupby(["country", "admin1_norm", "year", "month_num"], as_index=False)
    .agg({
        "displaced_in": "sum",
        DISPLACEMENT_ADJUSTED_FLAG_COL: "max",
        DISPLACEMENT_SOURCE_NOTE_COL: combine_unique_text,
    })
)

# use destination displacement as main humanitarian load
displacement["displaced"] = displacement["displaced_in"]

country_displacement_monthly = (
    displacement.groupby(["country", "year", "month_num"], as_index=False)
    .agg({
        "displaced": "sum",
        "displaced_in": "sum",
        DISPLACEMENT_ADJUSTED_FLAG_COL: "max",
        DISPLACEMENT_SOURCE_NOTE_COL: combine_unique_text,
    })
)

# ==================================================
# MERGE ACLED + DISPLACEMENT
# ==================================================
admin1_monthly = admin1_monthly.merge(
    displacement,
    on=["country", "admin1_norm", "year", "month_num"],
    how="left"
)

admin1_monthly["displaced_in"] = admin1_monthly["displaced_in"].fillna(0)
admin1_monthly["displaced"] = admin1_monthly["displaced"].fillna(0)
admin1_monthly = ensure_displacement_metadata(admin1_monthly)

# ==================================================
# LOG TRANSFORMS
# ==================================================
admin1_monthly["events_log"] = np.log1p(admin1_monthly["events"])
admin1_monthly["fatalities_log"] = np.log1p(admin1_monthly["fatalities"])
admin1_monthly["exposure_log"] = np.log1p(admin1_monthly["population_exposure"])
admin1_monthly["displaced_log"] = np.log1p(admin1_monthly["displaced"])

# ==================================================
# COUNTRY-LEVEL NORMALIZATION
# compare admin1 inside same country/month
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
        "displaced_in",
        DISPLACEMENT_ADJUSTED_FLAG_COL,
        DISPLACEMENT_SOURCE_NOTE_COL,
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
    })
)

country_monthly = country_monthly.merge(
    country_displacement_monthly,
    on=["country", "year", "month_num"],
    how="left"
)

country_monthly["displaced"] = country_monthly["displaced"].fillna(0)
country_monthly["displaced_in"] = country_monthly["displaced_in"].fillna(0)
country_monthly = ensure_displacement_metadata(country_monthly)

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

# ==================================================
# NEED DATA INTEGRATION
# ==================================================
need_data = load_need_data(valid_countries=country_monthly["country"].dropna().unique())
health_scores = build_health_score(need_data["health"])
education_scores = build_education_score(need_data["education"])
country_monthly = merge_need_scores(country_monthly, health_scores, education_scores)

country_monthly["country_priority_score_base"] = (
    0.35 * country_monthly["events_norm"] +
    0.35 * country_monthly["fatalities_norm"] +
    0.20 * country_monthly["displaced_norm"] +
    0.10 * country_monthly["exposure_norm"]
)

country_monthly["country_priority_score"] = (
    COUNTRY_PRIORITY_WEIGHTS["events_norm"] * country_monthly["events_norm"] +
    COUNTRY_PRIORITY_WEIGHTS["fatalities_norm"] * country_monthly["fatalities_norm"] +
    COUNTRY_PRIORITY_WEIGHTS["displaced_norm"] * country_monthly["displaced_norm"] +
    COUNTRY_PRIORITY_WEIGHTS["exposure_norm"] * country_monthly["exposure_norm"] +
    COUNTRY_PRIORITY_WEIGHTS["health_priority_score"] * country_monthly["health_priority_score"] +
    COUNTRY_PRIORITY_WEIGHTS["education_priority_score"] * country_monthly["education_priority_score"]
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

country_monthly = country_monthly[
    [
        "region",
        "country",
        "year",
        "month_num",
        "month",
        "events",
        "fatalities",
        "population_exposure",
        "displaced",
        "displaced_in",
        DISPLACEMENT_ADJUSTED_FLAG_COL,
        DISPLACEMENT_SOURCE_NOTE_COL,
        "events_log",
        "fatalities_log",
        "exposure_log",
        "displaced_log",
        "events_norm",
        "fatalities_norm",
        "exposure_norm",
        "displaced_norm",
        "country_priority_score_base",
        "health_priority_score",
        "health_source_year",
        "health_indicator_count",
        "health_data_available",
        "education_priority_score",
        "education_source_year",
        "education_indicator_count",
        "education_data_available",
        "country_priority_score",
        "country_priority_rank",
        "country_priority_class",
    ]
]

# ==================================================
# SAVE
# ==================================================
admin1_monthly.to_csv(output_admin1, index=False, encoding="utf-8-sig")
country_monthly.to_csv(output_country, index=False, encoding="utf-8-sig")

print("Saved admin1 file:", output_admin1)
print("Saved country file:", output_country)
print("Need data directory:", need_data["need_dir"])
print(
    "Need rows loaded:",
    {
        "health": int(len(need_data["health"])),
        "education": int(len(need_data["education"])),
        "health_scores": int(len(health_scores)),
        "education_scores": int(len(education_scores)),
    },
)

print("\nAdmin1 sample:")
print(admin1_monthly.head(10))

print("\nCountry sample:")
print(country_monthly.head(10))

print("\nCheck displacement merge:")
print(
    admin1_monthly[
        [
            "country",
            "admin1_norm",
            "year",
            "month_num",
            "displaced",
            "displaced_in",
            DISPLACEMENT_ADJUSTED_FLAG_COL,
        ]
    ].head(20)
)

summary = summarize_country_months(country_monthly, country="lebanon", value_col="displaced_in")
print("\nLebanon February and March 2026 priority displacement totals:")
if summary.empty:
    print("No Lebanon February or March 2026 rows found.")
else:
    print(summary.to_string(index=False))
