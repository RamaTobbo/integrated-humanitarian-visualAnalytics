import json
from pathlib import Path

import geopandas as gpd
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Global Conflict Overview", layout="wide")

# -----------------------------
# paths
# -----------------------------
world_geojson_path = Path("data/raw/boundaries/world_countries.geojson")
conflict_country_path = Path("data/cleaned/global/conflict_country_monthlybytype.csv")

# -----------------------------
# helpers
# -----------------------------
MONTH_MAP = {
    "January": 1,
    "February": 2,
    "March": 3,
    "April": 4,
    "May": 5,
    "June": 6,
    "July": 7,
    "August": 8,
    "September": 9,
    "October": 10,
    "November": 11,
    "December": 12,
}


@st.cache_data
def load_conflict():
    df = pd.read_csv(conflict_country_path)

    # numeric country code
    df["iso3"] = pd.to_numeric(df["iso3"], errors="coerce")
    df = df[df["iso3"].notna()].copy()
    df["iso_n3"] = df["iso3"].astype(int).astype(str).str.zfill(3)

    # clean fields
    df["country"] = df["country"].astype(str).str.strip()
    df["month"] = df["month"].astype(str).str.strip()
    df["event_type"] = df["event_type"].astype(str).str.strip()
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df["events"] = pd.to_numeric(df["events"], errors="coerce")
    df["fatalities"] = pd.to_numeric(df["fatalities"], errors="coerce")

    # month_num
    if "month_num" in df.columns:
        df["month_num"] = pd.to_numeric(df["month_num"], errors="coerce")
    else:
        df["month_num"] = df["month"].map(MONTH_MAP)

    # keep only 2022+
    df = df[df["year"] >= 2022].copy()

    # drop missing key values
    df = df[
        df["year"].notna()
        & df["month"].notna()
        & df["month_num"].notna()
        & df["country"].notna()
        & df["event_type"].notna()
    ].copy()

    df["year"] = df["year"].astype(int)
    df["month_num"] = df["month_num"].astype(int)

    return df


@st.cache_data
def load_world():
    world = gpd.read_file(world_geojson_path)
    world["iso_n3"] = world["iso_n3"].astype(str).str.strip().str.zfill(3)

    if "name" in world.columns:
        world["country_name_geo"] = world["name"]
    else:
        world["country_name_geo"] = world["iso_n3"]

    return world


conflict = load_conflict()
world = load_world()

# -----------------------------
# sidebar filters
# -----------------------------
st.sidebar.title("Filters")

years = sorted(conflict["year"].unique().tolist())
default_year_index = len(years) - 1 if years else 0
selected_year = st.sidebar.selectbox("Year", years, index=default_year_index)

available_months = (
    conflict.loc[conflict["year"] == selected_year, ["month_num", "month"]]
    .drop_duplicates()
    .sort_values("month_num")
)

month_list = available_months["month"].tolist()
selected_month = st.sidebar.selectbox("Month", month_list)

available_event_types = (
    conflict.loc[
        (conflict["year"] == selected_year)
        & (conflict["month"].str.lower() == selected_month.lower()),
        "event_type"
    ]
    .dropna()
    .drop_duplicates()
    .sort_values()
    .tolist()
)

# put All first if it exists
if "All" in available_event_types:
    available_event_types = ["All"] + [x for x in available_event_types if x != "All"]

selected_event_type = st.sidebar.selectbox("Event Type", available_event_types)

metric = st.sidebar.selectbox("Metric", ["events", "fatalities"])
show_top_n = st.sidebar.slider("Top countries table", 5, 20, 10)

color_scale = "YlOrRd" if metric == "events" else "Reds"

# -----------------------------
# filter data
# -----------------------------
filtered = conflict[
    (conflict["year"] == selected_year)
    & (conflict["month"].str.lower() == selected_month.lower())
    & (conflict["event_type"] == selected_event_type)
].copy()

if filtered.empty:
    st.title("Global Conflict Overview")
    st.caption(f"{selected_month} {selected_year} | {selected_event_type}")
    st.warning(f"No data available for {selected_month} {selected_year} and event type '{selected_event_type}'.")
    st.stop()

country_period = (
    filtered.groupby(["iso_n3", "country"], as_index=False)
    .agg({
        "events": "sum",
        "fatalities": "sum"
    })
)

merged = world.merge(country_period, how="left", on="iso_n3")

# -----------------------------
# title
# -----------------------------
st.title("Global Conflict Overview")
st.caption(f"{selected_month} {selected_year} | Event Type: {selected_event_type}")

# -----------------------------
# summary cards
# -----------------------------
total_events = int(country_period["events"].sum())
total_fatalities = int(country_period["fatalities"].sum())
countries_with_data = int(country_period["country"].nunique())

c1, c2, c3 = st.columns(3)
c1.metric("Total events", f"{total_events:,}")
c2.metric("Total fatalities", f"{total_fatalities:,}")
c3.metric("Countries with data", f"{countries_with_data:,}")

# -----------------------------
# map
# -----------------------------
fig = px.choropleth(
    merged,
    geojson=json.loads(merged.to_json()),
    locations="iso_n3",
    featureidkey="properties.iso_n3",
    color=metric,
    color_continuous_scale=color_scale,
    hover_name="country_name_geo",
    hover_data={
        "country": True,
        "events": ":,",
        "fatalities": ":,",
        "iso_n3": False,
    },
    projection="natural earth",
    title=f"Global Conflict Overview - {metric.capitalize()} ({selected_month} {selected_year}) | {selected_event_type}",
)

fig.update_geos(
    showcoastlines=True,
    showframe=False,
    bgcolor="rgba(0,0,0,0)",
)

fig.update_layout(
    margin=dict(l=0, r=0, t=60, b=0),
    height=650,
    coloraxis_colorbar_title=metric.capitalize(),
)

st.plotly_chart(fig, width="stretch")

# -----------------------------
# top countries table
# -----------------------------
st.subheader(f"Top {show_top_n} countries by {metric}")

top_countries = (
    country_period.sort_values(metric, ascending=False)
    .head(show_top_n)
    .reset_index(drop=True)
)

table_to_show = top_countries[["country", metric]].copy()
table_to_show.index = table_to_show.index + 1
table_to_show = table_to_show.rename(
    columns={
        "country": "Country",
        metric: metric.capitalize()
    }
)

st.dataframe(table_to_show, width="stretch")