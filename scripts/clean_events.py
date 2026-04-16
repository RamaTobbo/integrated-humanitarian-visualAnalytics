import pandas as pd

df = pd.read_csv("story/data/ACLED Data_2026-04-09.csv")

# keep Lebanon only (safety)
df = df[df["country"] == "Lebanon"]

# convert date
df["event_date"] = pd.to_datetime(df["event_date"])

# keep only needed columns
df = df[[
    "event_date",
    "event_type",
    "sub_event_type",
    "admin1",
    "admin2",
    "location",
    "fatalities",
    "latitude",
    "longitude"
]]

# add exposure (fake/simple for now)
df["exposure"] = (df["fatalities"] + 1) * 10000

# create priority score
df["priority_score"] = (
    df["fatalities"] * 0.5 +
    df["exposure"] * 0.00001
)

df.to_csv("story/data/lebanon_events_clean.csv", index=False)