import pandas as pd
from pathlib import Path

# ==================================================
# PATHS
# ==================================================
input_file = Path("data/raw/acess/road_status_events_template.csv")
output_dir = Path("data/cleaned/access")
output_dir.mkdir(parents=True, exist_ok=True)

output_file = output_dir / "road_access_admin2.csv"

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
        "jezzine": "jezzine",
    }

    return replacements.get(value, value)

def status_to_penalty(status):
    status = str(status).strip().lower()

    mapping = {
        "open": 0.0,
        "reopened": 0.0,
        "restricted": 0.5,
        "partial": 0.5,
        "partially open": 0.5,
        "closed": 1.0,
        "blocked": 1.0,
    }

    return mapping.get(status, 0.5)

# ==================================================
# LOAD
# ==================================================
df = pd.read_csv(input_file)

# Remove empty first row if present
df = df[df["district"].notna()].copy()

df["district"] = df["district"].astype(str).str.strip()
df["status"] = df["status"].astype(str).str.strip()
df["admin2_norm"] = df["district"].apply(normalize_admin2_name)

# Date cleaning
if "publish_date" in df.columns:
    df["publish_date"] = pd.to_datetime(df["publish_date"], errors="coerce")

# Convert status to penalty
df["road_event_penalty"] = df["status"].apply(status_to_penalty)

# Aggregate by district
# We keep:
# - max penalty = worst recent situation
# - mean penalty = average situation across records
out = (
    df.groupby("admin2_norm", as_index=False)
      .agg(
          road_access_penalty=("road_event_penalty", "max"),
          road_access_penalty_mean=("road_event_penalty", "mean"),
          road_events_count=("road_event_penalty", "size")
      )
)

out = out.sort_values("admin2_norm").reset_index(drop=True)

# Save
out.to_csv(output_file, index=False, encoding="utf-8-sig")

print("Saved:")
print(output_file)
print("\nSample:")
print(out.head(10))