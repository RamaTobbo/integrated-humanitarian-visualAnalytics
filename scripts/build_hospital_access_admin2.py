import pandas as pd
from pathlib import Path

# ==================================================
# PATHS
# ==================================================
input_file = Path("data/raw/acess/LBN_hospitals_access_wide.csv")
output_dir = Path("data/cleaned/access")
output_dir.mkdir(parents=True, exist_ok=True)

output_file = output_dir / "hospital_access_admin2.csv"

# ==================================================
# HELPERS
# ==================================================
def normalize_admin2_name(value):
    if pd.isna(value):
        return value

    value = str(value).strip().lower()

    replacements = {
        "sour": "tyre",
        "saida": "saida",
        "nabatiye": "nabatieh",
        "marjaayoun": "marjayoun",
        "rachaya": "rachaya",
        "kesrouan": "keserwan",
        "minieh-dinnieh": "minieh-danniyeh",
        "jbail": "jbeil",
        "bent jbail": "bint jbeil",
        "el metn": "matn",
        "koura": "koura",
        "bcharre": "bcharre",
        "west bekaa": "west bekaa",
        "batroun": "batroun",
        "baalbek": "baalbek",
        "beirut": "beirut",
        "tripoli": "tripoli",
        "zgharta": "zgharta",
        "chouf": "chouf",
        "jezzine": "jezzine",
        "akkar": "akkar",
        "zahle": "zahle",
        "baabda": "baabda",
        "aley": "aley",
        "hermel": "hermel",
        "hasbaya": "hasbaya",
    }

    return replacements.get(value, value)

# ==================================================
# LOAD
# ==================================================
df = pd.read_csv(input_file)

# Keep only district-level rows
df = df[df["admin_level"] == "ADM2"].copy()

# We choose 1800 seconds = 30 minutes as the access threshold
# You can change this to 1200 or 2400 later if you want
df = df[df["range"] == 1800].copy()

# Clean names
df["admin2"] = df["name"].astype(str).str.strip()
df["admin2_norm"] = df["admin2"].apply(normalize_admin2_name)

# population_share is percent of population within 30 minutes of a hospital
df["population_share"] = pd.to_numeric(df["population_share"], errors="coerce").fillna(0)

# Convert access to penalty:
# high access -> low penalty
# low access -> high penalty
df["health_access_penalty"] = 1 - (df["population_share"] / 100.0)

# Keep only needed columns
out = df[["admin2", "admin2_norm", "range", "population_share", "health_access_penalty"]].copy()

# In case duplicates exist
out = (
    out.groupby(["admin2", "admin2_norm", "range"], as_index=False)
       .agg({
           "population_share": "mean",
           "health_access_penalty": "mean"
       })
)

out = out.sort_values("admin2_norm").reset_index(drop=True)

# Save
out.to_csv(output_file, index=False, encoding="utf-8-sig")

print("Saved:")
print(output_file)
print("\nSample:")
print(out.head(10))