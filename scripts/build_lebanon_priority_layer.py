import pandas as pd
from pathlib import Path

# ==================================================
# PATHS
# ==================================================
conflict_path = Path("data/cleaned/global/conflict_standardized_monthlybytype.csv")
road_path = Path("data/cleaned/acess/road_access_admin2.csv")
health_path = Path("data/cleaned/acess/hospital_access_admin2.csv")

output_dir = Path("data/cleaned/lebanon")
output_dir.mkdir(parents=True, exist_ok=True)

output_file = output_dir / "lebanon_priority_admin2.csv"

# ==================================================
# HELPERS
# ==================================================
def normalize_admin2_name(value):
    if pd.isna(value):
        return value

    value = str(value).strip().lower()

    replacements = {
        "tyr": "tyre",
        "tyre": "tyre",
        "sidon": "saida",
        "saida": "saida",
        "jubayl": "jbeil",
        "jbjeil": "jbeil",
        "jbeil": "jbeil",
        "bent jbeil": "bint jbeil",
        "bint jbeil": "bint jbeil",
        "al minieh-danniyeh": "minieh-danniyeh",
        "minieh-danniyeh": "minieh-danniyeh",
        "al batroun": "batroun",
        "batroun": "batroun",
        "al kura": "koura",
        "kura": "koura",
        "koura": "koura",
        "al matn": "matn",
        "el metn": "matn",
        "el meten": "matn",
        "matn": "matn",
        "al hermel": "hermel",
        "el hermel": "hermel",
        "hermel": "hermel",
        "al nabatieh": "nabatieh",
        "nabatiyeh": "nabatieh",
        "nabatieh": "nabatieh",
        "hasbaiya": "hasbaya",
        "hasbaya": "hasbaya",
        "marjaayoun": "marjayoun",
        "marjayoun": "marjayoun",
        "bsharri": "bcharre",
        "bcharre": "bcharre",
        "rashaya": "rachaya",
        "rachaya": "rachaya",
        "kesrwane": "keserwan",
        "keserwan": "keserwan",
        "west bekaa": "west bekaa",
        "zahle": "zahle",
        "baalbek": "baalbek",
        "baabda": "baabda",
        "aley": "aley",
        "chouf": "chouf",
        "tripoli": "tripoli",
        "akkar": "akkar",
        "beirut": "beirut",
        "zgharta": "zgharta",
    }

    return replacements.get(value, value)


def minmax(series):
    series = pd.to_numeric(series, errors="coerce").fillna(0)
    min_val = series.min()
    max_val = series.max()

    if max_val == min_val:
        return pd.Series([0.0] * len(series), index=series.index)

    return (series - min_val) / (max_val - min_val)


# ==================================================
# LOAD FILES
# ==================================================
conflict = pd.read_csv(conflict_path)
road = pd.read_csv(road_path)
health = pd.read_csv(health_path)

# ==================================================
# CLEAN CONFLICT
# ==================================================
conflict["country"] = conflict["country"].astype(str).str.strip()
conflict["admin2"] = conflict["admin2"].astype(str).str.strip()
conflict["event_type"] = conflict["event_type"].astype(str).str.strip()
conflict["year"] = pd.to_numeric(conflict["year"], errors="coerce")
conflict["month_num"] = pd.to_numeric(conflict["month_num"], errors="coerce")
conflict["events"] = pd.to_numeric(conflict["events"], errors="coerce").fillna(0)
conflict["fatalities"] = pd.to_numeric(conflict["fatalities"], errors="coerce").fillna(0)

conflict = conflict[conflict["country"] == "Lebanon"].copy()
conflict["admin2_norm"] = conflict["admin2"].apply(normalize_admin2_name)

# keep only "All" event type for priority model
if "event_type" in conflict.columns:
    conflict = conflict[conflict["event_type"] == "All"].copy()

# aggregate in case duplicates exist
conflict_admin2 = (
    conflict.groupby(
        ["admin2_norm", "year", "month_num", "month"],
        as_index=False
    )
    .agg({
        "events": "sum",
        "fatalities": "sum"
    })
)

# ==================================================
# CLEAN ROAD
# ==================================================

road["road_access_penalty"] = pd.to_numeric(road["road_access_penalty"], errors="coerce").fillna(0)


road = (
    road.groupby("admin2_norm", as_index=False)
    .agg({"road_access_penalty": "mean"})
)

# ==================================================
# CLEAN HEALTH
# ==================================================
health["admin2"] = health["admin2"].astype(str).str.strip()
health["health_access_penalty"] = pd.to_numeric(health["health_access_penalty"], errors="coerce").fillna(0)
health["admin2_norm"] = health["admin2"].apply(normalize_admin2_name)

health = (
    health.groupby("admin2_norm", as_index=False)
    .agg({"health_access_penalty": "mean"})
)

# ==================================================
# MERGE
# ==================================================
priority = conflict_admin2.merge(road, how="left", on="admin2_norm")
priority = priority.merge(health, how="left", on="admin2_norm")

priority["road_access_penalty"] = priority["road_access_penalty"].fillna(0)
priority["health_access_penalty"] = priority["health_access_penalty"].fillna(0)

# ==================================================
# NORMALIZE
# ==================================================
priority["events_norm"] = minmax(priority["events"])
priority["fatalities_norm"] = minmax(priority["fatalities"])

# road_access_penalty and health_access_penalty are already assumed 0..1
priority["road_penalty_norm"] = priority["road_access_penalty"].clip(0, 1)
priority["health_penalty_norm"] = priority["health_access_penalty"].clip(0, 1)

# ==================================================
# PRIORITY SCORE
# ==================================================
priority["priority_score"] = (
    0.40 * priority["events_norm"]
    + 0.30 * priority["fatalities_norm"]
    + 0.15 * priority["road_penalty_norm"]
    + 0.15 * priority["health_penalty_norm"]
)

priority["priority_rank"] = (
    priority.groupby(["year", "month_num"])["priority_score"]
    .rank(method="dense", ascending=False)
    .astype(int)
)

# ==================================================
# SAVE
# ==================================================
priority = priority.sort_values(
    ["year", "month_num", "priority_rank", "admin2_norm"]
).reset_index(drop=True)

priority.to_csv(output_file, index=False, encoding="utf-8-sig")

print("Saved:")
print(output_file)
print("\nSample:")
print(priority.head(10))