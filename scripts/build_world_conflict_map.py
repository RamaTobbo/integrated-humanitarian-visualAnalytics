import json
from pathlib import Path

import geopandas as gpd
import pandas as pd
import plotly.express as px

world_geojson_path = Path("data/raw/boundaries/world_countries.geojson")
conflict_country_path = Path("data/cleaned/global/conflict_country_monthly.csv")

selected_year = 2024
selected_month = "June"
metric = "events"   # or "fatalities"

world = gpd.read_file(world_geojson_path)

print("World columns:")
print(world.columns.tolist())

conflict = pd.read_csv(conflict_country_path)

print("\nConflict columns:")
print(conflict.columns.tolist())

# -----------------------------
# Clean world numeric ISO code
# -----------------------------
world["iso_n3"] = world["iso_n3"].astype(str).str.strip()

# Some geojson files may store codes like 4, others like 004
world["iso_n3"] = world["iso_n3"].str.zfill(3)

# Optional nice country name
if "name" in world.columns:
    world["country_name_geo"] = world["name"]

# -----------------------------
# Clean conflict data
# -----------------------------
conflict["iso3"] = pd.to_numeric(conflict["iso3"], errors="coerce")
conflict = conflict[conflict["iso3"].notna()].copy()

# Convert numeric code to 3-digit string to match iso_n3
conflict["iso_n3"] = conflict["iso3"].astype(int).astype(str).str.zfill(3)

conflict["country"] = conflict["country"].astype(str).str.strip()
conflict["month"] = conflict["month"].astype(str).str.strip()
conflict["year"] = pd.to_numeric(conflict["year"], errors="coerce")
conflict["events"] = pd.to_numeric(conflict["events"], errors="coerce")
conflict["fatalities"] = pd.to_numeric(conflict["fatalities"], errors="coerce")

print("\nMonths:", sorted(conflict["month"].dropna().unique())[:20])
print("Years:", sorted(conflict["year"].dropna().unique())[:20])

filtered = conflict[
    (conflict["year"] == selected_year) &
    (conflict["month"].str.lower() == selected_month.lower())
].copy()

print(f"\nFiltered rows for {selected_month} {selected_year}: {len(filtered)}")
print(filtered.head())

country_period = (
    filtered.groupby(["iso_n3", "country"], as_index=False)
    .agg({
        "events": "sum",
        "fatalities": "sum"
    })
)

print("\nCountry-period sample:")
print(country_period.head())

# -----------------------------
# Merge on numeric ISO code
# -----------------------------
merged = world.merge(
    country_period,
    how="left",
    on="iso_n3"
)

print("\nMatched countries:", merged["country"].notna().sum())

# Leave missing values as NaN so countries without data stay blank
fig = px.choropleth(
    merged,
    geojson=json.loads(merged.to_json()),
    locations="iso_n3",
    featureidkey="properties.iso_n3",
    color=metric,
    hover_name="country_name_geo" if "country_name_geo" in merged.columns else "iso_n3",
    hover_data={
        "country": True,
        "events": True,
        "fatalities": True,
        "iso_n3": True
    },
    projection="natural earth",
    title=f"Global Conflict Overview - {metric.capitalize()} ({selected_month} {selected_year})"
)

fig.update_geos(showcoastlines=True, showframe=False)
fig.show()