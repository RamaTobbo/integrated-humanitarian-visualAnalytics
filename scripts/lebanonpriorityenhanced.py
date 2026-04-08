from pathlib import Path
import pandas as pd

# ==================================================
# PATHS
# ==================================================
conflict_admin_path = Path("data/cleaned/global/conflict_standardized_monthlybytype.csv")

# uploaded files
access_path = Path("data/raw/acess/LBN_ADM2_access.csv")
demographics_path = Path("data/raw/acess/LBN_ADM2_demographics.csv")
vulnerability_path = Path("data/raw/acess/LBN_ADM2_vulnerability.csv")

# output
output_path = Path("data/cleaned/lebanon/lebanon_priority_admin2_enhanced.csv")

# ==================================================
# NAME NORMALIZATION
# ==================================================
VARIANT_TO_CANONICAL = {
    "akkar": "akkar",
    "aakkar": "akkar",
    "aley": "aley",
    "baabda": "baabda",
    "baalbek": "baalbek",
    "batroun": "batroun",
    "al batroun": "batroun",
    "bcharre": "bcharre",
    "bsharri": "bcharre",
    "beirut": "beirut",
    "bent jbeil": "bent jbail",
    "bint jbeil": "bent jbail",
    "bent jbail": "bent jbail",
    "chouf": "chouf",
    "shouf": "chouf",
    "matn": "el metn",
    "metn": "el metn",
    "el metn": "el metn",
    "el meten": "el metn",
    "al matn": "el metn",
    "hasbaya": "hasbaya",
    "hasbaiya": "hasbaya",
    "hermel": "hermel",
    "el hermel": "hermel",
    "al hermel": "hermel",
    "jbeil": "jbail",
    "jbail": "jbail",
    "jubayl": "jbail",
    "jbjeil": "jbail",
    "jezzine": "jezzine",
    "kesrouan": "kesrouan",
    "keserwan": "kesrouan",
    "kesrwane": "kesrouan",
    "koura": "koura",
    "kura": "koura",
    "al kura": "koura",
    "marjaayoun": "marjaayoun",
    "marjayoun": "marjaayoun",
    "minieh-dinnieh": "minieh-dinnieh",
    "minieh-dennie": "minieh-dinnieh",
    "minieh-denniye": "minieh-dinnieh",
    "minieh-danniyeh": "minieh-dinnieh",
    "al minieh-danniyeh": "minieh-dinnieh",
    "danniyeh": "minieh-dinnieh",
    "nabatiye": "nabatiye",
    "nabatieh": "nabatiye",
    "nabatiyeh": "nabatiye",
    "el nabatieh": "nabatiye",
    "al nabatieh": "nabatiye",
    "rachaya": "rachaya",
    "rashaya": "rachaya",
    "rashayya": "rachaya",
    "saida": "saida",
    "sayda": "saida",
    "sidon": "saida",
    "sour": "sour",
    "tyre": "sour",
    "tyr": "sour",
    "tripoli": "tripoli",
    "west bekaa": "west bekaa",
    "beqaa west": "west bekaa",
    "zahle": "zahle",
    "zgharta": "zgharta",
}

def normalize_admin2_name(value):
    if pd.isna(value):
        return None
    value = str(value).strip().lower()
    value = value.replace("–", "-").replace("—", "-")
    value = " ".join(value.split())
    return VARIANT_TO_CANONICAL.get(value, value)

# ==================================================
# ADM2 PCODE -> DISTRICT NAME
# ==================================================
ADM2_PCODE_TO_CANONICAL = {
    "LB11": "beirut",
    "LB21": "baalbek",
    "LB22": "hermel",
    "LB23": "rachaya",
    "LB24": "west bekaa",
    "LB25": "zahle",
    "LB31": "aley",
    "LB32": "baabda",
    "LB33": "chouf",
    "LB34": "jbail",
    "LB35": "kesrouan",
    "LB36": "el metn",
    "LB41": "bent jbail",
    "LB42": "hasbaya",
    "LB43": "marjaayoun",
    "LB44": "nabatiye",
    "LB51": "akkar",
    "LB52": "batroun",
    "LB53": "bcharre",
    "LB54": "koura",
    "LB55": "minieh-dinnieh",
    "LB56": "tripoli",
    "LB57": "zgharta",
    "LB61": "saida",
    "LB62": "jezzine",
    "LB63": "sour",
}

# ==================================================
# LOAD ACLED ADMIN2 MONTHLY DATA
# ==================================================
conflict = pd.read_csv(conflict_admin_path)

for col in ["country", "admin2", "month", "event_type"]:
    if col in conflict.columns:
        conflict[col] = conflict[col].astype(str).str.strip()

conflict["year"] = pd.to_numeric(conflict["year"], errors="coerce")
conflict["events"] = pd.to_numeric(conflict["events"], errors="coerce").fillna(0)
conflict["fatalities"] = pd.to_numeric(conflict["fatalities"], errors="coerce").fillna(0)

lebanon = conflict[
    conflict["country"].astype(str).str.lower() == "lebanon"
].copy()

lebanon["admin2_norm"] = lebanon["admin2"].apply(normalize_admin2_name)

# aggregate by district/month
lebanon_monthly = (
    lebanon.dropna(subset=["admin2_norm"])
    .groupby(["admin2_norm", "year", "month_num", "month"], as_index=False)
    .agg({
        "events": "sum",
        "fatalities": "sum",
    })
)

# ==================================================
# LOAD STATIC DISTRICT TABLES
# ==================================================
access = pd.read_csv(access_path)
demographics = pd.read_csv(demographics_path)
vulnerability = pd.read_csv(vulnerability_path)

for df in [access, demographics, vulnerability]:
    df["admin2_norm"] = df["ADM2_PCODE"].map(ADM2_PCODE_TO_CANONICAL)

# keep only the fields you actually want
access = access[
    [
        "admin2_norm",
        "access_pop_hospitals_30min",
        "access_pop_primary_healthcare_30min",
    ]
].copy()

demographics = demographics[
    [
        "admin2_norm",
        "children_u5",
        "elderly",
    ]
].copy()

vulnerability = vulnerability[
    [
        "admin2_norm",
        "rural_pop_perc",
    ]
].copy()

static_layers = (
    access.merge(demographics, on="admin2_norm", how="outer")
    .merge(vulnerability, on="admin2_norm", how="outer")
)

# fill missing numeric fields
for col in [
    "access_pop_hospitals_30min",
    "access_pop_primary_healthcare_30min",
    "children_u5",
    "elderly",
    "rural_pop_perc",
]:
    static_layers[col] = pd.to_numeric(static_layers[col], errors="coerce").fillna(0)

# ==================================================
# MERGE MONTHLY CONFLICT + STATIC LAYERS
# ==================================================
priority = lebanon_monthly.merge(static_layers, on="admin2_norm", how="left")

for col in [
    "access_pop_hospitals_30min",
    "access_pop_primary_healthcare_30min",
    "children_u5",
    "elderly",
    "rural_pop_perc",
]:
    priority[col] = pd.to_numeric(priority[col], errors="coerce").fillna(0)

# ==================================================
# NORMALIZATION HELPERS
# ==================================================
def minmax(series):
    s = pd.to_numeric(series, errors="coerce").fillna(0)
    smin = s.min()
    smax = s.max()
    if smax == smin:
        return pd.Series([0.0] * len(s), index=s.index)
    return (s - smin) / (smax - smin)

# ==================================================
# STATIC NORMALIZED LAYERS
# note: access fields are counts, not percentages
# so this is a district-relative proxy, not a true coverage rate
# ==================================================
priority["hosp_access_norm"] = minmax(priority["access_pop_hospitals_30min"])
priority["phc_access_norm"] = minmax(priority["access_pop_primary_healthcare_30min"])

# lower access -> higher risk
priority["hospital_access_risk"] = 1 - priority["hosp_access_norm"]
priority["phc_access_risk"] = 1 - priority["phc_access_norm"]
priority["access_risk"] = 0.5 * priority["hospital_access_risk"] + 0.5 * priority["phc_access_risk"]

priority["children_u5_norm"] = minmax(priority["children_u5"])
priority["elderly_norm"] = minmax(priority["elderly"])
priority["rural_norm"] = minmax(priority["rural_pop_perc"])

priority["demographic_vulnerability"] = (
    0.4 * priority["children_u5_norm"]
    + 0.4 * priority["elderly_norm"]
    + 0.2 * priority["rural_norm"]
)

# ==================================================
# MONTHLY CONFLICT NORMALIZATION
# normalize events/fatalities inside each month
# ==================================================
priority["events_norm"] = (
    priority.groupby(["year", "month_num"])["events"]
    .transform(minmax)
)

priority["fatalities_norm"] = (
    priority.groupby(["year", "month_num"])["fatalities"]
    .transform(minmax)
)

priority["conflict_score"] = (
    0.6 * priority["events_norm"]
    + 0.4 * priority["fatalities_norm"]
)

# ==================================================
# FINAL PRIORITY SCORE
# ==================================================
priority["priority_score"] = (
    0.5 * priority["conflict_score"]
    + 0.3 * priority["access_risk"]
    + 0.2 * priority["demographic_vulnerability"]
)

priority["priority_rank"] = (
    priority.groupby(["year", "month_num"])["priority_score"]
    .rank(method="dense", ascending=False)
    .astype(int)
)

# sort output
priority = priority.sort_values(
    ["year", "month_num", "priority_score", "admin2_norm"],
    ascending=[True, True, False, True]
).reset_index(drop=True)

# ==================================================
# SAVE
# ==================================================
output_path.parent.mkdir(parents=True, exist_ok=True)
priority.to_csv(output_path, index=False)

print("Saved:", output_path)
print(priority.head(20))

# optional debug
unmatched_conflict = sorted(set(lebanon_monthly["admin2_norm"]) - set(static_layers["admin2_norm"]))
unmatched_static = sorted(set(static_layers["admin2_norm"]) - set(lebanon_monthly["admin2_norm"]))

print("\nUnmatched conflict districts:", unmatched_conflict)
print("Unmatched static districts:", unmatched_static)