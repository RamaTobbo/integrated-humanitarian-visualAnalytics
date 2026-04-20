import re
import unicodedata
from pathlib import Path

import pandas as pd

from lebanon_displacement_fallback import (
    apply_lebanon_displacement_fallback,
    ensure_displacement_metadata,
    month_num_to_name,
    summarize_country_months,
)

BASE_DIR = Path(__file__).resolve().parent.parent

input_path = BASE_DIR / "data" / "raw" / "global" / "event_data_lbn.csv"
output_path = BASE_DIR / "data" / "cleaned" / "global" / "lebanon_displacement_2026_from_events.csv"


def normalize_text(value):
    if pd.isna(value):
        return None
    value = str(value).lower().strip()
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.replace("-", " ")
    value = re.sub(r"\s+", " ", value)
    return value


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

    for key, admin1 in mapping.items():
        if key in location:
            return admin1

    return None


def extract_number(text):
    if pd.isna(text):
        return 0

    match = re.findall(r"\d{1,3}(?:,\d{3})*", str(text))
    if not match:
        return 0

    values = [int(value.replace(",", "")) for value in match]
    return max(values)


df = pd.read_csv(input_path)
df["event_start_date"] = pd.to_datetime(df["event_start_date"], errors="coerce")
df["year"] = df["event_start_date"].dt.year
df["month_num"] = df["event_start_date"].dt.month
df = df[df["year"] == 2026].copy()

df["location_clean"] = df["locations_name"].astype(str)
df["admin1_norm"] = df["location_clean"].apply(map_to_admin1)
df["displaced_in"] = df["description"].apply(extract_number)

df = df[
    df["admin1_norm"].notna() &
    (df["displaced_in"] > 0)
].copy()

final = (
    df.groupby(["year", "month_num", "admin1_norm"], as_index=False)["displaced_in"]
    .sum()
    .sort_values(["year", "month_num", "admin1_norm"])
    .reset_index(drop=True)
)

final["country"] = "lebanon"
final["country_name"] = "Lebanon"
final["month"] = final["month_num"].apply(month_num_to_name)

final = ensure_displacement_metadata(final)
final = apply_lebanon_displacement_fallback(final, value_col="displaced_in")
final = final[
    [
        "country",
        "country_name",
        "year",
        "month_num",
        "month",
        "admin1_norm",
        "displaced_in",
        "displacement_adjusted_flag",
        "displacement_source_note",
    ]
].copy()

final.to_csv(output_path, index=False)

print("Saved:", output_path)
print("\nLebanon 2026 displacement supplement:")
print(final.head(10).to_string(index=False))

summary = summarize_country_months(final, country="lebanon", value_col="displaced_in")
print("\nLebanon February and March 2026 displacement totals:")
if summary.empty:
    print("No Lebanon February or March 2026 rows found.")
else:
    print(summary.to_string(index=False))
