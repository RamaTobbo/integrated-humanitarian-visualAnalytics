import json
from pathlib import Path

import geopandas as gpd
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Global Conflict Dashboard", layout="wide")

# ==================================================
# PATHS
# ==================================================
world_geojson_path = Path("data/raw/boundaries/world_countries.geojson")
lbn_admin2_path = Path("data/raw/boundaries/geoBoundaries-LBN-ADM2.geojson")
conflict_country_path = Path("data/cleaned/global/conflict_country_monthlybytype.csv")
conflict_admin_path = Path("data/cleaned/global/conflict_standardized_monthlybytype.csv")

# ==================================================
# CONSTANTS
# ==================================================
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

DISTRICT_TO_ADMIN1_GEO = {
    "Akkar": "Akkar",
    "Aley": "Mount Lebanon",
    "Baabda": "Mount Lebanon",
    "Baalbek": "Baalbek-Hermel",
    "Batroun": "North",
    "Bcharre": "North",
    "Beirut": "Beirut",
    "Bent Jbail": "Al Nabatieh",
    "Chouf": "Mount Lebanon",
    "El Metn": "Mount Lebanon",
    "Hasbaya": "Al Nabatieh",
    "Hermel": "Baalbek-Hermel",
    "Jbail": "Mount Lebanon",
    "Jezzine": "South",
    "Kesrouan": "Mount Lebanon",
    "Koura": "North",
    "Marjaayoun": "Al Nabatieh",
    "Minieh-Dinnieh": "North",
    "Nabatiye": "Al Nabatieh",
    "Rachaya": "Bekaa",
    "Saida": "South",
    "Sour": "South",
    "Tripoli": "North",
    "West Bekaa": "Bekaa",
    "Zahle": "Bekaa",
    "Zgharta": "North",
}

ADMIN1_VARIANTS = {
    "akkar": "Akkar",
    "al nabatieh": "Al Nabatieh",
    "nabatieh": "Al Nabatieh",
    "nabatiye": "Al Nabatieh",
    "nabatiyeh": "Al Nabatieh",
    "baalbek-hermel": "Baalbek-Hermel",
    "baalbek hermel": "Baalbek-Hermel",
    "beirut": "Beirut",
    "bekaa": "Bekaa",
    "beqaa": "Bekaa",
    "mount lebanon": "Mount Lebanon",
    "north": "North",
    "north lebanon": "North",
    "south": "South",
    "south lebanon": "South",
}

# ==================================================
# HELPERS
# ==================================================
def normalize_admin1_name(value):
    if pd.isna(value):
        return None
    value = str(value).strip().lower()
    value = value.replace("–", "-").replace("—", "-")
    value = " ".join(value.split())
    return ADMIN1_VARIANTS.get(value, str(value).strip())


def extract_selected_country(event):
    if event is None:
        return None

    try:
        if isinstance(event, dict):
            selection = event.get("selection", {})
            points = selection.get("points", [])
        else:
            selection = getattr(event, "selection", {})
            points = selection.get("points", []) if isinstance(selection, dict) else []
    except Exception:
        return None

    if not points:
        return None

    point = points[0]
    custom = point.get("customdata", [])

    if custom and len(custom) > 0:
        return custom[0]

    return None


def default_latest_period(df):
    temp = (
        df[["year", "month_num", "month"]]
        .drop_duplicates()
        .sort_values(["year", "month_num"])
    )
    last_row = temp.iloc[-1]
    return int(last_row["year"]), str(last_row["month"])


def ensure_required_files():
    required_paths = [
        world_geojson_path,
        lbn_admin2_path,
        conflict_country_path,
        conflict_admin_path,
    ]
    missing = [str(p) for p in required_paths if not p.exists()]
    if missing:
        st.error("Missing files:\n" + "\n".join(missing))
        st.stop()


def filter_event_type(df, selected_event_type):
    if selected_event_type == "All":
        return df.copy()
    return df[df["event_type"] == selected_event_type].copy()


def add_line_geometry(fig, geom, color="black", width=1.0):
    if geom is None or geom.is_empty:
        return

    if geom.geom_type == "LineString":
        x, y = geom.xy
        fig.add_trace(
            go.Scattergeo(
                lon=list(x),
                lat=list(y),
                mode="lines",
                line=dict(color=color, width=width),
                hoverinfo="skip",
                showlegend=False,
            )
        )
    elif geom.geom_type == "MultiLineString":
        for part in geom.geoms:
            x, y = part.xy
            fig.add_trace(
                go.Scattergeo(
                    lon=list(x),
                    lat=list(y),
                    mode="lines",
                    line=dict(color=color, width=width),
                    hoverinfo="skip",
                    showlegend=False,
                )
            )


def add_boundaries(fig, gdf):
    for geom in gdf.boundary:
        add_line_geometry(fig, geom, color="black", width=0.8)


def add_country_outline(fig, gdf):
    outline = (
        gdf.union_all().boundary
        if hasattr(gdf, "union_all")
        else gdf.unary_union.boundary
    )
    add_line_geometry(fig, outline, color="black", width=2.2)


def repair_geometries(gdf):
    gdf = gdf.copy()
    gdf = gdf[gdf.geometry.notna()].copy()
    gdf = gdf[~gdf.geometry.is_empty].copy()
    gdf["geometry"] = gdf["geometry"].buffer(0)
    gdf = gdf[gdf.geometry.notna()].copy()
    gdf = gdf[~gdf.geometry.is_empty].copy()
    return gdf


def make_hover_customdata(df):
    return df[["events", "fatalities"]].astype(float).values


def compute_conflict_priority(df, geo_col):
    out = (
        df.dropna(subset=[geo_col])
        .groupby(geo_col, as_index=False)
        .agg({"events": "sum", "fatalities": "sum"})
    )

    max_events = float(out["events"].max()) if not out.empty else 0.0
    max_fatalities = float(out["fatalities"].max()) if not out.empty else 0.0

    out["events_norm"] = out["events"] / max_events if max_events > 0 else 0.0
    out["fatalities_norm"] = out["fatalities"] / max_fatalities if max_fatalities > 0 else 0.0
    out["priority_score"] = 0.6 * out["events_norm"] + 0.4 * out["fatalities_norm"]

    out = out.sort_values(["priority_score", geo_col], ascending=[False, True]).reset_index(drop=True)
    out["priority_rank"] = out.index + 1
    return out


# ==================================================
# DATA LOADERS
# ==================================================
@st.cache_data(show_spinner=False)
def load_country_conflict():
    df = pd.read_csv(conflict_country_path)

    df["iso3"] = pd.to_numeric(df["iso3"], errors="coerce")
    df = df[df["iso3"].notna()].copy()
    df["iso_n3"] = df["iso3"].astype(int).astype(str).str.zfill(3)

    df["country"] = df["country"].astype(str).str.strip()
    df["month"] = df["month"].astype(str).str.strip()
    df["event_type"] = df["event_type"].astype(str).str.strip()

    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df["events"] = pd.to_numeric(df["events"], errors="coerce").fillna(0)
    df["fatalities"] = pd.to_numeric(df["fatalities"], errors="coerce").fillna(0)

    if "month_num" not in df.columns:
        df["month_num"] = df["month"].map(MONTH_MAP)
    else:
        df["month_num"] = pd.to_numeric(df["month_num"], errors="coerce")

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


@st.cache_data(show_spinner=False)
def load_admin_conflict():
    df = pd.read_csv(conflict_admin_path)

    for col in ["country", "admin1", "admin2", "month", "event_type"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    for col in ["year", "month_num", "events", "fatalities", "population_exposure"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df["events"] = df["events"].fillna(0)
    df["fatalities"] = df["fatalities"].fillna(0)

    if "month_num" not in df.columns:
        df["month_num"] = df["month"].map(MONTH_MAP)

    df = df[
        df["year"].notna()
        & df["month"].notna()
        & df["month_num"].notna()
        & df["country"].notna()
        & df["event_type"].notna()
        & df["admin1"].notna()
    ].copy()

    df["year"] = df["year"].astype(int)
    df["month_num"] = df["month_num"].astype(int)
    return df


@st.cache_data(show_spinner=False)
def load_world():
    world = gpd.read_file(world_geojson_path)

    if world.crs is None:
        world = world.set_crs(epsg=4326)
    else:
        world = world.to_crs(epsg=4326)

    world["iso_n3"] = world["iso_n3"].astype(str).str.strip().str.zfill(3)

    if "name" in world.columns:
        world["country_name_geo"] = world["name"]
    else:
        world["country_name_geo"] = world["iso_n3"]

    return world


@st.cache_data(show_spinner=False)
def load_lbn_admin2():
    gdf = gpd.read_file(lbn_admin2_path)

    if gdf.crs is None:
        gdf = gdf.set_crs(epsg=4326)
    else:
        gdf = gdf.to_crs(epsg=4326)

    gdf["shapeName"] = gdf["shapeName"].astype(str).str.strip()
    gdf = gdf[["shapeName", "geometry"]].copy()
    gdf = repair_geometries(gdf)
    return gdf


@st.cache_data(show_spinner=False)
def load_lbn_admin1():
    admin2 = load_lbn_admin2().copy()
    admin2["admin1"] = admin2["shapeName"].map(DISTRICT_TO_ADMIN1_GEO)
    admin1 = admin2.dissolve(by="admin1", as_index=False)
    admin1 = repair_geometries(admin1)
    return admin1[["admin1", "geometry"]]


# ==================================================
# LOAD EVERYTHING
# ==================================================
ensure_required_files()

country_conflict = load_country_conflict()
admin_conflict = load_admin_conflict()
world = load_world()
lbn_admin1 = load_lbn_admin1()

lebanon_only = admin_conflict[
    admin_conflict["country"].astype(str).str.lower() == "lebanon"
].copy()
lebanon_only["admin1_geo"] = lebanon_only["admin1"].apply(normalize_admin1_name)

# ==================================================
# SESSION STATE
# ==================================================
if "view" not in st.session_state:
    st.session_state["view"] = "world"

if "world_country" not in st.session_state:
    st.session_state["world_country"] = "All"

if "world_year" not in st.session_state or "world_month" not in st.session_state:
    y, m = default_latest_period(country_conflict)
    st.session_state["world_year"] = y
    st.session_state["world_month"] = m

if "world_event_type" not in st.session_state:
    st.session_state["world_event_type"] = "All"

if "world_metric" not in st.session_state:
    st.session_state["world_metric"] = "events"

if "lbn_year" not in st.session_state or "lbn_month" not in st.session_state:
    y, m = default_latest_period(lebanon_only)
    st.session_state["lbn_year"] = y
    st.session_state["lbn_month"] = m

if "lbn_event_type" not in st.session_state:
    st.session_state["lbn_event_type"] = "All"

if "lbn_metric" not in st.session_state:
    st.session_state["lbn_metric"] = "events"

# ==================================================
# WORLD VIEW
# ==================================================
if st.session_state["view"] == "world":
    st.sidebar.title("World Filters")

    country_options = ["All"] + sorted(country_conflict["country"].dropna().unique().tolist())
    selected_country = st.sidebar.selectbox(
        "Country",
        country_options,
        index=country_options.index(st.session_state["world_country"])
        if st.session_state["world_country"] in country_options
        else 0,
    )
    st.session_state["world_country"] = selected_country

    country_base = country_conflict.copy()
    if selected_country != "All":
        country_base = country_base[country_base["country"] == selected_country].copy()

    world_years = sorted(country_base["year"].unique().tolist())
    selected_year = st.sidebar.selectbox(
        "Year",
        world_years,
        index=world_years.index(st.session_state["world_year"])
        if st.session_state["world_year"] in world_years
        else 0,
    )
    st.session_state["world_year"] = selected_year

    available_months = (
        country_base.loc[
            country_base["year"] == selected_year, ["month_num", "month"]
        ]
        .drop_duplicates()
        .sort_values("month_num")
    )
    month_list = available_months["month"].tolist()

    selected_month = st.sidebar.selectbox(
        "Month",
        month_list,
        index=month_list.index(st.session_state["world_month"])
        if st.session_state["world_month"] in month_list
        else 0,
    )
    st.session_state["world_month"] = selected_month

    available_event_types = (
        country_base.loc[
            (country_base["year"] == selected_year)
            & (country_base["month"].str.lower() == selected_month.lower()),
            "event_type",
        ]
        .dropna()
        .drop_duplicates()
        .sort_values()
        .tolist()
    )
    available_event_types = ["All"] + available_event_types

    selected_event_type = st.sidebar.selectbox(
        "Event Type",
        available_event_types,
        index=available_event_types.index(st.session_state["world_event_type"])
        if st.session_state["world_event_type"] in available_event_types
        else 0,
    )
    st.session_state["world_event_type"] = selected_event_type

    metric = st.sidebar.selectbox(
        "Metric",
        ["events", "fatalities"],
        index=0 if st.session_state["world_metric"] == "events" else 1,
    )
    st.session_state["world_metric"] = metric

    filtered_world = country_base[
        (country_base["year"] == selected_year)
        & (country_base["month"].str.lower() == selected_month.lower())
    ].copy()
    filtered_world = filter_event_type(filtered_world, selected_event_type)

    color_scale = "YlOrRd" if metric == "events" else "Reds"

    st.title("Global Conflict Overview" if selected_country == "All" else f"{selected_country} Conflict Overview")
    st.caption(f"{selected_month} {selected_year} | Event Type: {selected_event_type}")

    # if selected_country == "All":
    #     st.info("Click Lebanon on the world map to open the Lebanon view.")
    # else:
    #     st.info("The map zooms to the selected country.")

    if filtered_world.empty:
        st.warning("No data available for the selected filters.")
        st.stop()

    country_period = (
        filtered_world.groupby(["iso_n3", "country"], as_index=False)
        .agg({"events": "sum", "fatalities": "sum"})
    )

    merged_world = world.merge(country_period, how="left", on="iso_n3")
    merged_world["events"] = merged_world["events"].fillna(0)
    merged_world["fatalities"] = merged_world["fatalities"].fillna(0)

    total_events = int(country_period["events"].sum())
    total_fatalities = int(country_period["fatalities"].sum())
    countries_with_data = int((country_period[metric] > 0).sum())

    c1, c2, c3 = st.columns(3)
    c1.metric("Total events", f"{total_events:,}")
    c2.metric("Total fatalities", f"{total_fatalities:,}")
    c3.metric("Countries with data", f"{countries_with_data:,}")

    if selected_country == "All":
        fig_world = px.choropleth(
            merged_world,
            geojson=json.loads(merged_world.to_json()),
            locations="iso_n3",
            featureidkey="properties.iso_n3",
            color=metric,
            color_continuous_scale=color_scale,
            hover_name="country_name_geo",
            hover_data={
                "country": True,
                "events": True,
                "fatalities": True,
                "iso_n3": False,
            },
            custom_data=["country_name_geo"],
            projection="natural earth",
            title=f"World Map - {metric.capitalize()} ({selected_month} {selected_year}) | {selected_event_type}",
        )

        fig_world.update_traces(marker_line_color="gray", marker_line_width=0.4)
        fig_world.update_geos(showcoastlines=True, showframe=False, bgcolor="rgba(0,0,0,0)")
        fig_world.update_layout(
            margin=dict(l=0, r=0, t=60, b=0),
            height=650,
            coloraxis_colorbar_title=metric.capitalize(),
        )

        event = st.plotly_chart(
            fig_world,
            use_container_width=True,
            on_select="rerun",
            selection_mode=("points",),
            key="world_chart_all",
        )

        clicked_country = extract_selected_country(event)
        if clicked_country == "Lebanon":
            st.session_state["view"] = "lebanon"
            st.rerun()

    else:
        selected_geo = merged_world[merged_world["iso_n3"].isin(country_period["iso_n3"].unique())].copy()

        fig_selected = px.choropleth(
            selected_geo,
            geojson=json.loads(selected_geo.to_json()),
            locations="iso_n3",
            featureidkey="properties.iso_n3",
            color=metric,
            color_continuous_scale=color_scale,
            hover_name="country_name_geo",
            hover_data={
                "country": True,
                "events": True,
                "fatalities": True,
                "iso_n3": False,
            },
            projection="mercator",
            title=f"{selected_country} - {metric.capitalize()} ({selected_month} {selected_year}) | {selected_event_type}",
        )

        fig_selected.update_traces(marker_line_color="gray", marker_line_width=0.6)
        fig_selected.update_geos(
            fitbounds="locations",
            visible=False,
            bgcolor="rgba(0,0,0,0)",
        )
        fig_selected.update_layout(
            margin=dict(l=0, r=0, t=60, b=0),
            height=550,
            coloraxis_colorbar_title=metric.capitalize(),
        )

        st.plotly_chart(fig_selected, use_container_width=True, key="world_chart_selected")

        if selected_country == "Lebanon":
            if st.button("Open Lebanon admin1 view"):
                st.session_state["view"] = "lebanon"
                st.rerun()

    st.subheader(f"Top 10 countries by {metric}")
    top_countries = (
        country_period.sort_values(metric, ascending=False)
        .head(10)
        .reset_index(drop=True)
    )
    top_countries.index = top_countries.index + 1
    top_table = top_countries[["country", metric]].rename(
        columns={"country": "Country", metric: metric.capitalize()}
    )
    st.dataframe(top_table, use_container_width=True)

# ==================================================
# LEBANON VIEW
# ==================================================
else:
    st.sidebar.title("Lebanon Filters")

    if st.sidebar.button("← Back to world"):
        st.session_state["view"] = "world"
        st.rerun()

    view_mode = st.sidebar.selectbox("Lebanon View", ["Conflict View", "Priority View"])

    lbn_years = sorted(lebanon_only["year"].unique().tolist())
    selected_year = st.sidebar.selectbox(
        "Year",
        lbn_years,
        index=lbn_years.index(st.session_state["lbn_year"])
        if st.session_state["lbn_year"] in lbn_years
        else 0,
    )
    st.session_state["lbn_year"] = selected_year

    available_months = (
        lebanon_only.loc[
            lebanon_only["year"] == selected_year, ["month_num", "month"]
        ]
        .drop_duplicates()
        .sort_values("month_num")
    )
    month_list = available_months["month"].tolist()

    selected_month = st.sidebar.selectbox(
        "Month",
        month_list,
        index=month_list.index(st.session_state["lbn_month"])
        if st.session_state["lbn_month"] in month_list
        else 0,
    )
    st.session_state["lbn_month"] = selected_month

    available_event_types = (
        lebanon_only.loc[
            (lebanon_only["year"] == selected_year)
            & (lebanon_only["month"].str.lower() == selected_month.lower()),
            "event_type",
        ]
        .dropna()
        .drop_duplicates()
        .sort_values()
        .tolist()
    )
    available_event_types = ["All"] + available_event_types

    selected_event_type = st.sidebar.selectbox(
        "Event Type",
        available_event_types,
        index=available_event_types.index(st.session_state["lbn_event_type"])
        if st.session_state["lbn_event_type"] in available_event_types
        else 0,
    )
    st.session_state["lbn_event_type"] = selected_event_type

    metric = st.sidebar.selectbox(
        "Metric",
        ["events", "fatalities"],
        index=0 if st.session_state["lbn_metric"] == "events" else 1,
    )
    st.session_state["lbn_metric"] = metric

    filtered_lbn = lebanon_only[
        (lebanon_only["year"] == selected_year)
        & (lebanon_only["month"].str.lower() == selected_month.lower())
    ].copy()
    filtered_lbn = filter_event_type(filtered_lbn, selected_event_type)

    # ==========================================
    # CONFLICT VIEW
    # ==========================================
    if view_mode == "Conflict View":
        st.title("Lebanon Governorate Map")
        st.caption(f"{selected_month} {selected_year} | Event Type: {selected_event_type}")

        grouped = (
            filtered_lbn.dropna(subset=["admin1_geo"])
            .groupby("admin1_geo", as_index=False)
            .agg({"events": "sum", "fatalities": "sum"})
            .rename(columns={"admin1_geo": "admin1"})
        )

        merged_lbn = lbn_admin1.merge(grouped, how="left", on="admin1")
        merged_lbn["events"] = pd.to_numeric(merged_lbn["events"], errors="coerce").fillna(0)
        merged_lbn["fatalities"] = pd.to_numeric(merged_lbn["fatalities"], errors="coerce").fillna(0)
        merged_lbn = repair_geometries(merged_lbn)

        total_events = int(merged_lbn["events"].sum())
        total_fatalities = int(merged_lbn["fatalities"].sum())
        areas_with_data = int((merged_lbn[metric] > 0).sum())

        c1, c2, c3 = st.columns(3)
        c1.metric("Lebanon events", f"{total_events:,}")
        c2.metric("Lebanon fatalities", f"{total_fatalities:,}")
        c3.metric("Governorates with data", f"{areas_with_data:,}")

        base_df = merged_lbn.copy()
        plot_df = merged_lbn[merged_lbn[metric] > 0].copy()

        color_scale = "YlOrRd" if metric == "events" else "Reds"
        real_max = float(plot_df[metric].max()) if not plot_df.empty else 1.0
        if real_max <= 0:
            real_max = 1.0

        minx, miny, maxx, maxy = lbn_admin1.total_bounds
        pad_x = (maxx - minx) * 0.08
        pad_y = (maxy - miny) * 0.08

        fig_lbn = go.Figure()

        fig_lbn.add_trace(
            go.Choropleth(
                geojson=json.loads(base_df.to_json()),
                locations=base_df["admin1"],
                z=[0] * len(base_df),
                featureidkey="properties.admin1",
                colorscale=[[0, "white"], [1, "white"]],
                zmin=0,
                zmax=1,
                showscale=False,
                marker_line_width=0,
                marker_line_color="rgba(0,0,0,0)",
                customdata=make_hover_customdata(base_df),
                hovertemplate=(
                    "<b>%{location}</b><br>"
                    "events=%{customdata[0]:.0f}<br>"
                    "fatalities=%{customdata[1]:.0f}<extra></extra>"
                ),
            )
        )

        if not plot_df.empty:
            fig_lbn.add_trace(
                go.Choropleth(
                    geojson=json.loads(plot_df.to_json()),
                    locations=plot_df["admin1"],
                    z=plot_df[metric],
                    featureidkey="properties.admin1",
                    colorscale=color_scale,
                    zmin=0,
                    zmax=real_max,
                    marker_line_width=0,
                    marker_line_color="rgba(0,0,0,0)",
                    colorbar=dict(title=metric.capitalize()),
                    customdata=make_hover_customdata(plot_df),
                    hovertemplate=(
                        "<b>%{location}</b><br>"
                        "events=%{customdata[0]:.0f}<br>"
                        "fatalities=%{customdata[1]:.0f}<extra></extra>"
                    ),
                )
            )

        fig_lbn.update_geos(
            visible=False,
            bgcolor="white",
            showland=False,
            showcountries=False,
            showcoastlines=False,
            showocean=False,
            showlakes=False,
            showrivers=False,
            lonaxis_range=[minx - pad_x, maxx + pad_x],
            lataxis_range=[miny - pad_y, maxy + pad_y],
        )

        fig_lbn.update_layout(
            title=f"Lebanon Governorates - {metric.capitalize()} ({selected_month} {selected_year}) | {selected_event_type}",
            margin=dict(l=0, r=0, t=60, b=0),
            height=700,
            paper_bgcolor="white",
            plot_bgcolor="white",
        )

        add_boundaries(fig_lbn, lbn_admin1)
        add_country_outline(fig_lbn, lbn_admin1)

        st.plotly_chart(fig_lbn, use_container_width=True, key="lbn_conflict_chart")

        st.subheader(f"Top 10 governorates by {metric}")
        top_areas = (
            merged_lbn[["admin1", "events", "fatalities"]]
            .sort_values(metric, ascending=False)
            .head(10)
            .reset_index(drop=True)
        )
        top_areas.index = top_areas.index + 1

        area_table = top_areas[["admin1", metric]].rename(
            columns={"admin1": "Governorate", metric: metric.capitalize()}
        )
        st.dataframe(area_table, use_container_width=True)

    # ==========================================
    # PRIORITY VIEW
    # ==========================================
    else:
        st.title("Lebanon Priority Map")
        st.caption(f"{selected_month} {selected_year} | Priority based on events and fatalities")

        priority_values = compute_conflict_priority(filtered_lbn, "admin1_geo").rename(columns={"admin1_geo": "admin1"})
        merged_priority = lbn_admin1.merge(priority_values, how="left", on="admin1")

        for col in ["events", "fatalities", "priority_score"]:
            merged_priority[col] = pd.to_numeric(merged_priority[col], errors="coerce").fillna(0)

        merged_priority["priority_rank"] = pd.to_numeric(
            merged_priority["priority_rank"], errors="coerce"
        )
        merged_priority = repair_geometries(merged_priority)

        top_row = merged_priority.sort_values("priority_score", ascending=False).head(1)
        highest_area = top_row["admin1"].iloc[0] if not top_row.empty else "-"
        highest_score = float(top_row["priority_score"].iloc[0]) if not top_row.empty else 0.0
        avg_score = float(merged_priority["priority_score"].mean()) if not merged_priority.empty else 0.0

        c1, c2, c3 = st.columns(3)
        c1.metric("Highest priority governorate", highest_area)
        c2.metric("Highest priority score", f"{highest_score:.3f}")
        c3.metric("Average priority score", f"{avg_score:.3f}")

        base_df = merged_priority.copy()
        plot_df = merged_priority[merged_priority["priority_score"] > 0].copy()

        real_max = float(plot_df["priority_score"].max()) if not plot_df.empty else 1.0
        if real_max <= 0:
            real_max = 1.0

        minx, miny, maxx, maxy = lbn_admin1.total_bounds
        pad_x = (maxx - minx) * 0.08
        pad_y = (maxy - miny) * 0.08

        fig_priority = go.Figure()

        fig_priority.add_trace(
            go.Choropleth(
                geojson=json.loads(base_df.to_json()),
                locations=base_df["admin1"],
                z=[0] * len(base_df),
                featureidkey="properties.admin1",
                colorscale=[[0, "white"], [1, "white"]],
                zmin=0,
                zmax=1,
                showscale=False,
                marker_line_width=0,
                marker_line_color="rgba(0,0,0,0)",
                customdata=base_df[["events", "fatalities", "priority_score"]].astype(float).values,
                hovertemplate=(
                    "<b>%{location}</b><br>"
                    "events=%{customdata[0]:.0f}<br>"
                    "fatalities=%{customdata[1]:.0f}<br>"
                    "priority score=%{customdata[2]:.3f}<extra></extra>"
                ),
            )
        )

        if not plot_df.empty:
            fig_priority.add_trace(
                go.Choropleth(
                    geojson=json.loads(plot_df.to_json()),
                    locations=plot_df["admin1"],
                    z=plot_df["priority_score"],
                    featureidkey="properties.admin1",
                    colorscale="OrRd",
                    zmin=0,
                    zmax=real_max,
                    marker_line_width=0,
                    marker_line_color="rgba(0,0,0,0)",
                    colorbar=dict(title="Priority Score"),
                    customdata=plot_df[["events", "fatalities", "priority_score"]].astype(float).values,
                    hovertemplate=(
                        "<b>%{location}</b><br>"
                        "events=%{customdata[0]:.0f}<br>"
                        "fatalities=%{customdata[1]:.0f}<br>"
                        "priority score=%{customdata[2]:.3f}<extra></extra>"
                    ),
                )
            )

        fig_priority.update_geos(
            visible=False,
            bgcolor="white",
            showland=False,
            showcountries=False,
            showcoastlines=False,
            showocean=False,
            showlakes=False,
            showrivers=False,
            lonaxis_range=[minx - pad_x, maxx + pad_x],
            lataxis_range=[miny - pad_y, maxy + pad_y],
        )

        fig_priority.update_layout(
            title=f"Lebanon Priority Map ({selected_month} {selected_year})",
            margin=dict(l=0, r=0, t=60, b=0),
            height=700,
            paper_bgcolor="white",
            plot_bgcolor="white",
        )

        add_boundaries(fig_priority, lbn_admin1)
        add_country_outline(fig_priority, lbn_admin1)

        st.plotly_chart(fig_priority, use_container_width=True, key="lbn_priority_chart")

        st.subheader("Top 10 governorates by priority")
        top_priority = (
            merged_priority[["admin1", "priority_score", "priority_rank"]]
            .sort_values(["priority_score", "admin1"], ascending=[False, True])
            .head(10)
            .reset_index(drop=True)
        )
        top_priority.index = top_priority.index + 1

        priority_table = top_priority.rename(
            columns={
                "admin1": "Governorate",
                "priority_score": "Priority Score",
                "priority_rank": "Priority Rank",
            }
        )
        st.dataframe(priority_table, use_container_width=True)