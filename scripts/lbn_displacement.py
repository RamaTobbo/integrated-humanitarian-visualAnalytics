import pandas as pd
import re
from pathlib import Path
import unicodedata

BASE_DIR = Path(__file__).resolve().parent.parent

input_path = BASE_DIR / "data" / "raw" / "global" / "event_data_lbn.csv"
output_path = BASE_DIR / "data" / "cleaned" / "global" / "lebanon_displacement_2026_from_events.csv"


# ----------------------------
# normalize text
# ----------------------------
def normalize_text(value):
    if pd.isna(value):
        return None
    value = str(value).lower().strip()
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.replace("-", " ")
    value = re.sub(r"\s+", " ", value)
    return value


# ----------------------------
# Lebanon admin1 mapping
# ----------------------------
def map_to_admin1(location):
    location = normalize_text(location)

    mapping = {
        "akkar": "akkar",
        "tripoli": "north",
        "zgharta": "north",
        "batroun": "north",
        "koura": "north",
        "bcharre": "north",

        "beirut": "beirut",

        "baabda": "mount lebanon",
        "aley": "mount lebanon",
        "chouf": "mount lebanon",
        "metn": "mount lebanon",
        "keserwan": "mount lebanon",
        "jbeil": "mount lebanon",

        "zahleh": "bekaa",
        "west bekaa": "bekaa",
        "rashaya": "bekaa",

        "baalbek": "baalbek-hermel",
        "hermel": "baalbek-hermel",

        "tyre": "south",
        "sidon": "south",
        "jezzine": "south",

        "nabatiyeh": "al nabatieh",
        "marjayoun": "al nabatieh",
        "bint jbeil": "al nabatieh",
        "hasbaya": "al nabatieh",
    }

    for key in mapping:
        if key in location:
            return mapping[key]

    return None


# ----------------------------
# extract displacement number
# ----------------------------
def extract_number(text):
    if pd.isna(text):
        return 0

    text = str(text)

    # find numbers like 1,200 or 50000
    match = re.findall(r"\d{1,3}(?:,\d{3})*", text)

    if match:
        nums = [int(x.replace(",", "")) for x in match]
        return max(nums)  # take biggest number

    return 0


# ----------------------------
# load data
# ----------------------------
df = pd.read_csv(input_path)

# ----------------------------
# extract year & month
# ----------------------------
df["event_start_date"] = pd.to_datetime(df["event_start_date"], errors="coerce")

df["year"] = df["event_start_date"].dt.year
df["month"] = df["event_start_date"].dt.month

# keep only 2026
df = df[df["year"] == 2026].copy()

# ----------------------------
# extract location
# ----------------------------
df["location_clean"] = df["locations_name"].astype(str)

# ----------------------------
# map to admin1
# ----------------------------
df["admin1_norm"] = df["location_clean"].apply(map_to_admin1)

# ----------------------------
# extract displacement numbers
# ----------------------------
df["displaced_in"] = df["description"].apply(extract_number)

# ----------------------------
# filter valid rows
# ----------------------------
df = df[
    (df["admin1_norm"].notna()) &
    (df["displaced_in"] > 0)
].copy()

# ----------------------------
# aggregate monthly
# ----------------------------
final = (
    df.groupby(["year", "month", "admin1_norm"], as_index=False)["displaced_in"]
    .sum()
)

final["country"] = "lebanon"

# ----------------------------
# save
# ----------------------------
final.to_csv(output_path, index=False)

print("Saved:", output_path)
print(final.head())