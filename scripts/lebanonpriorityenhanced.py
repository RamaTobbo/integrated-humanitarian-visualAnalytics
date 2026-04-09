from pathlib import Path
import pandas as pd

# ==================================================
# PATHS
# ==================================================
admin2_priority_path = Path("data/cleaned/lebanon/lebanon_priority_admin2_enhanced.csv")
admin1_conflict_path = Path("data/cleaned/global/middle_east_admin1_monthlybytype_with_centroids.csv")
output_path = Path("data/cleaned/lebanon/lebanon_priority_admin1_enhanced.csv")

# ==================================================
# ADMIN2 -> ADMIN1 MAPPING
# ==================================================
ADMIN2_TO_ADMIN1 = {
    "beirut": "beirut",

    "baalbek": "baalbek-hermel",
    "hermel": "baalbek-hermel",

    "rachaya": "bekaa",
    "west bekaa": "bekaa",
    "zahle": "bekaa",

    "aley": "mount lebanon",
    "baabda": "mount lebanon",
    "chouf": "mount lebanon",
    "jbail": "mount lebanon",
    "kesrouan": "mount lebanon",
    "el metn": "mount lebanon",

    "bent jbail": "al nabatieh",
    "hasbaya": "al nabatieh",
    "marjaayoun": "al nabatieh",
    "nabatiye": "al nabatieh",

    "akkar": "akkar",

    "batroun": "north",
    "bcharre": "north",
    "koura": "north",
    "minieh-dinnieh": "north",
    "tripoli": "north",
    "zgharta": "north",

    "saida": "south",
    "jezzine": "south",
    "sour": "south",
}

# ==================================================
# HELPERS
# ==================================================
def normalize_text(value):
    if pd.isna(value):
        return None
    value = str(value).strip().lower()
    value = value.replace("–", "-").replace("—", "-")
    value = " ".join(value.split())
    return value

def minmax(series):
    s = pd.to_numeric(series, errors="coerce").fillna(0)
    smin = s.min()
    smax = s.max()
    if smax == smin:
        return pd.Series([0.0] * len(s), index=s.index)
    return (s - smin) / (smax - smin)

# ==================================================
# LOAD EXISTING ADMIN2 PRIORITY FILE
# We only use it to build static admin1 layers
# ==================================================
admin2_priority = pd.read_csv(admin2_priority_path)

admin2_priority["admin2_norm"] = admin2_priority["admin2_norm"].apply(normalize_text)
admin2_priority["admin1_norm"] = admin2_priority["admin2_norm"].map(ADMIN2_TO_ADMIN1)

# keep one static row per admin2
admin2_static = (
    admin2_priority
    .sort_values(["year", "month_num"])
    .drop_duplicates(subset=["admin2_norm"])
    [
        [
            "admin2_norm",
            "admin1_norm",
            "access_pop_hospitals_30min",
            "access_pop_primary_healthcare_30min",
            "children_u5",
            "elderly",
            "rural_pop_perc",
        ]
    ]
    .copy()
)

for col in [
    "access_pop_hospitals_30min",
    "access_pop_primary_healthcare_30min",
    "children_u5",
    "elderly",
    "rural_pop_perc",
]:
    admin2_static[col] = pd.to_numeric(admin2_static[col], errors="coerce").fillna(0)

# ==================================================
# AGGREGATE STATIC LAYERS TO ADMIN1
# counts -> sum
# rural percentage -> mean
# ==================================================
admin1_static = (
    admin2_static
    .dropna(subset=["admin1_norm"])
    .groupby("admin1_norm", as_index=False)
    .agg({
        "access_pop_hospitals_30min": "sum",
        "access_pop_primary_healthcare_30min": "sum",
        "children_u5": "sum",
        "elderly": "sum",
        "rural_pop_perc": "mean",
    })
)

# static normalization
admin1_static["hosp_access_norm"] = minmax(admin1_static["access_pop_hospitals_30min"])
admin1_static["phc_access_norm"] = minmax(admin1_static["access_pop_primary_healthcare_30min"])

admin1_static["hospital_access_risk"] = 1 - admin1_static["hosp_access_norm"]
admin1_static["phc_access_risk"] = 1 - admin1_static["phc_access_norm"]
admin1_static["access_risk"] = (
    0.5 * admin1_static["hospital_access_risk"] +
    0.5 * admin1_static["phc_access_risk"]
)

admin1_static["children_u5_norm"] = minmax(admin1_static["children_u5"])
admin1_static["elderly_norm"] = minmax(admin1_static["elderly"])
admin1_static["rural_norm"] = minmax(admin1_static["rural_pop_perc"])

admin1_static["demographic_vulnerability"] = (
    0.4 * admin1_static["children_u5_norm"] +
    0.4 * admin1_static["elderly_norm"] +
    0.2 * admin1_static["rural_norm"]
)

# ==================================================
# LOAD ADMIN1 CONFLICT FILE
# IMPORTANT: keep only Lebanon + event_type = All
# ==================================================
conflict_admin1 = pd.read_csv(admin1_conflict_path)

for col in ["country", "admin1", "month", "event_type"]:
    if col in conflict_admin1.columns:
        conflict_admin1[col] = conflict_admin1[col].astype(str).str.strip()

conflict_admin1["admin1_norm"] = conflict_admin1["admin1"].apply(normalize_text)
conflict_admin1["country"] = conflict_admin1["country"].astype(str).str.strip().str.lower()
conflict_admin1["event_type"] = conflict_admin1["event_type"].astype(str).str.strip().str.lower()

conflict_admin1["year"] = pd.to_numeric(conflict_admin1["year"], errors="coerce")
conflict_admin1["month_num"] = pd.to_numeric(conflict_admin1["month_num"], errors="coerce")
conflict_admin1["events"] = pd.to_numeric(conflict_admin1["events"], errors="coerce").fillna(0)
conflict_admin1["fatalities"] = pd.to_numeric(conflict_admin1["fatalities"], errors="coerce").fillna(0)
conflict_admin1["population_exposure"] = pd.to_numeric(conflict_admin1["population_exposure"], errors="coerce").fillna(0)

lebanon_admin1 = conflict_admin1[
    (conflict_admin1["country"] == "lebanon") &
    (conflict_admin1["event_type"] == "all")
].copy()

lebanon_admin1 = (
    lebanon_admin1
    .groupby(["admin1_norm", "year", "month_num", "month"], as_index=False)
    .agg({
        "events": "sum",
        "fatalities": "sum",
        "population_exposure": "sum",
    })
)

# ==================================================
# MERGE CONFLICT + STATIC
# ==================================================
priority_admin1 = lebanon_admin1.merge(admin1_static, on="admin1_norm", how="left")

# ==================================================
# MONTHLY CONFLICT NORMALIZATION
# ==================================================
priority_admin1["events_norm"] = (
    priority_admin1.groupby(["year", "month_num"])["events"]
    .transform(minmax)
)

priority_admin1["fatalities_norm"] = (
    priority_admin1.groupby(["year", "month_num"])["fatalities"]
    .transform(minmax)
)

priority_admin1["conflict_score"] = (
    0.6 * priority_admin1["events_norm"] +
    0.4 * priority_admin1["fatalities_norm"]
)

# ==================================================
# FINAL PRIORITY SCORE
# ==================================================
priority_admin1["priority_score"] = (
    0.5 * priority_admin1["conflict_score"] +
    0.3 * priority_admin1["access_risk"] +
    0.2 * priority_admin1["demographic_vulnerability"]
)

priority_admin1["priority_rank"] = (
    priority_admin1.groupby(["year", "month_num"])["priority_score"]
    .rank(method="dense", ascending=False)
    .astype(int)
)

# ==================================================
# FINAL COLUMN ORDER
# ==================================================
priority_admin1 = priority_admin1[
    [
        "admin1_norm",
        "year",
        "month_num",
        "month",
        "events",
        "fatalities",
        "population_exposure",
        "access_pop_hospitals_30min",
        "access_pop_primary_healthcare_30min",
        "children_u5",
        "elderly",
        "rural_pop_perc",
        "hosp_access_norm",
        "phc_access_norm",
        "hospital_access_risk",
        "phc_access_risk",
        "access_risk",
        "children_u5_norm",
        "elderly_norm",
        "rural_norm",
        "demographic_vulnerability",
        "events_norm",
        "fatalities_norm",
        "conflict_score",
        "priority_score",
        "priority_rank",
    ]
].sort_values(
    ["year", "month_num", "priority_score", "admin1_norm"],
    ascending=[True, True, False, True]
).reset_index(drop=True)

# ==================================================
# SAVE
# ==================================================
output_path.parent.mkdir(parents=True, exist_ok=True)
priority_admin1.to_csv(output_path, index=False)

print("Saved:", output_path)
print("Years:", sorted(priority_admin1["year"].dropna().unique()))
print(priority_admin1.head(20))