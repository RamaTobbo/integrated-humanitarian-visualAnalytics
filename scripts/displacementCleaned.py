from pathlib import Path
import pandas as pd
import unicodedata
import re

from lebanon_displacement_fallback import (
    apply_lebanon_displacement_fallback,
    ensure_displacement_metadata,
    summarize_country_months,
)

BASE_DIR = Path(__file__).resolve().parent.parent

input_path = BASE_DIR / "data" / "raw" / "global" / "global-iom-dtm-from-api-admin-0-to-2.csv"
output_dir = BASE_DIR / "data" / "cleaned" / "global"
output_dir.mkdir(parents=True, exist_ok=True)

cleaned_output_path = output_dir / "displacement_cleaned_2024_2026.csv"
dest_output_path = output_dir / "displacement_admin1_destination_monthly_2024_2026.csv"
origin_output_path = output_dir / "displacement_admin1_origin_monthly_2024_2026.csv"


def normalize_text(value):
    if pd.isna(value):
        return None
    value = str(value).strip().lower()
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.replace("–", "-").replace("—", "-").replace("_", " ")
    value = value.replace("/", " ")
    value = value.replace(",", " ")
    value = re.sub(r"\s+", " ", value).strip()
    return value


def month_num_to_name(month_num):
    month_map = {
        1: "January",
        2: "February",
        3: "March",
        4: "April",
        5: "May",
        6: "June",
        7: "July",
        8: "August",
        9: "September",
        10: "October",
        11: "November",
        12: "December",
    }
    return month_map.get(int(month_num), None)


df = pd.read_csv(input_path)

keep_cols = [
    "admin0Name",
    "admin1Name",
    "admin2Name",
    "idpOriginAdmin1Name",
    "numPresentIdpInd",
    "reportingDate",
    "yearReportingDate",
    "monthReportingDate",
    "displacementReason",
]

df = df[keep_cols].copy()

for col in ["admin0Name", "admin1Name", "admin2Name", "idpOriginAdmin1Name", "displacementReason"]:
    df[col] = df[col].astype(str).str.strip()

df["numPresentIdpInd"] = pd.to_numeric(df["numPresentIdpInd"], errors="coerce").fillna(0)
df["yearReportingDate"] = pd.to_numeric(df["yearReportingDate"], errors="coerce")
df["monthReportingDate"] = pd.to_numeric(df["monthReportingDate"], errors="coerce")

df = df[
    df["yearReportingDate"].notna()
    & df["monthReportingDate"].notna()
    & df["admin0Name"].notna()
    & df["admin1Name"].notna()
].copy()

df["yearReportingDate"] = df["yearReportingDate"].astype(int)
df["monthReportingDate"] = df["monthReportingDate"].astype(int)

df = df[df["yearReportingDate"].between(2024, 2026)].copy()

# remove obvious placeholders
bad_values = {"", "nan", "none", "not available", "unknown"}

df["country"] = df["admin0Name"].apply(normalize_text)
df["admin1_dest_norm"] = df["admin1Name"].apply(normalize_text)
df["admin1_origin_norm"] = df["idpOriginAdmin1Name"].apply(normalize_text)

df.loc[df["country"].isin(bad_values), "country"] = None
df.loc[df["admin1_dest_norm"].isin(bad_values), "admin1_dest_norm"] = None
df.loc[df["admin1_origin_norm"].isin(bad_values), "admin1_origin_norm"] = None

df["month"] = df["monthReportingDate"].apply(month_num_to_name)

# save cleaned row-level file
df.to_csv(cleaned_output_path, index=False)

# =========================================================
# DESTINATION MONTHLY ADMIN1
# =========================================================
dest = (
    df.dropna(subset=["country", "admin1_dest_norm", "month"])
    .groupby(
        ["country", "admin0Name", "yearReportingDate", "monthReportingDate", "month", "admin1_dest_norm"],
        as_index=False
    )["numPresentIdpInd"]
    .sum()
    .rename(columns={
        "admin0Name": "country_name",
        "yearReportingDate": "year",
        "monthReportingDate": "month_num",
        "admin1_dest_norm": "admin1_norm",
        "numPresentIdpInd": "displaced_in",
    })
)

dest = ensure_displacement_metadata(dest)
dest = apply_lebanon_displacement_fallback(dest, value_col="displaced_in")
dest.to_csv(dest_output_path, index=False)

# =========================================================
# ORIGIN MONTHLY ADMIN1
# =========================================================
origin = (
    df.dropna(subset=["country", "admin1_origin_norm", "month"])
    .groupby(
        ["country", "admin0Name", "yearReportingDate", "monthReportingDate", "month", "admin1_origin_norm"],
        as_index=False
    )["numPresentIdpInd"]
    .sum()
    .rename(columns={
        "admin0Name": "country_name",
        "yearReportingDate": "year",
        "monthReportingDate": "month_num",
        "admin1_origin_norm": "admin1_norm",
        "numPresentIdpInd": "displaced_from",
    })
)

origin = ensure_displacement_metadata(origin)
origin.to_csv(origin_output_path, index=False)

print("Saved cleaned rows to:", cleaned_output_path)
print("Saved destination monthly admin1 to:", dest_output_path)
print("Saved origin monthly admin1 to:", origin_output_path)
print("Cleaned rows:", len(df))
print("Destination rows:", len(dest))
print("Origin rows:", len(origin))

summary = summarize_country_months(dest, country="lebanon", value_col="displaced_in")
print("\nLebanon February and March 2026 destination totals:")
if summary.empty:
    print("No Lebanon February or March 2026 rows found.")
else:
    print(summary.to_string(index=False))
