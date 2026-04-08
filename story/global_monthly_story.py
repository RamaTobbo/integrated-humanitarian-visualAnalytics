import pandas as pd
from pathlib import Path

# ==================================================
# PATHS
# ==================================================
input_file = Path("data/cleaned/global/conflict_country_monthlybytype.csv")
output_file = Path("story/data/global_story_monthly.csv")

output_file.parent.mkdir(parents=True, exist_ok=True)

# ==================================================
# LOAD
# ==================================================
df = pd.read_csv(input_file)

print("Original columns:")
print(df.columns.tolist())

# ==================================================
# BASIC CLEANING
# ==================================================
for col in ["country", "month", "event_type"]:
    if col in df.columns:
        df[col] = df[col].astype(str).str.strip()

for col in ["year", "month_num", "events", "fatalities"]:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

needed = ["country", "year", "month_num", "month", "event_type", "events", "fatalities"]
missing = [c for c in needed if c not in df.columns]
if missing:
    raise ValueError(f"Missing expected columns: {missing}")

df = df[
    df["country"].notna()
    & df["year"].notna()
    & df["month_num"].notna()
    & df["month"].notna()
    & df["event_type"].notna()
].copy()

df["year"] = df["year"].astype(int)
df["month_num"] = df["month_num"].astype(int)
df["events"] = df["events"].fillna(0)
df["fatalities"] = df["fatalities"].fillna(0)

# ==================================================
# MONTHLY STORY DATASET
# ==================================================
story = (
    df.groupby(["year", "month_num", "month", "event_type"], as_index=False)
    .agg(
        events=("events", "sum"),
        fatalities=("fatalities", "sum"),
        countries_with_data=("country", "nunique"),
    )
    .sort_values(["year", "month_num", "event_type"])
    .reset_index(drop=True)
)

# nice label
story["label"] = story["month"] + " " + story["year"].astype(str)

# reorder columns
story = story[
    [
        "year",
        "month_num",
        "month",
        "label",
        "event_type",
        "events",
        "fatalities",
        "countries_with_data",
    ]
]

# ==================================================
# SAVE
# ==================================================
story.to_csv(output_file, index=False, encoding="utf-8-sig")

print("\nSaved:")
print(output_file)

print("\nSample:")
print(story.head(12))

print("\nEvent types found:")
print(sorted(story["event_type"].dropna().unique().tolist()))

print("\nYears found:")
print(sorted(story["year"].dropna().unique().tolist()))