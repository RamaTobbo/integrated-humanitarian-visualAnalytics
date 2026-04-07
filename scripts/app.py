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
priority_path = Path("data/cleaned/lebanon/lebanon_priority_admin2.csv")
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

CANONICAL_TO_GEO = {
    "akkar": "Akkar",
    "aley": "Aley",
    "baabda": "Baabda",
    "baalbek": "Baalbek",
    "batroun": "Batroun",
    "bcharre": "Bcharre",
    "beirut": "Beirut",
    "bent jbail": "Bent Jbail",
    "chouf": "Chouf",
    "el metn": "El Metn",
    "hasbaya": "Hasbaya",
    "hermel": "Hermel",
    "jbail": "Jbail",
    "jezzine": "Jezzine",
    "kesrouan": "Kesrouan",
    "koura": "Koura",
    "marjaayoun": "Marjaayoun",
    "minieh-dinnieh": "Minieh-Dinnieh",
    "nabatiye": "Nabatiye",
    "rachaya": "Rachaya",
    "saida": "Saida",
    "sour": "Sour",
    "tripoli": "Tripoli",
    "west bekaa": "West Bekaa",
    "zahle": "Zahle",
    "zgharta": "Zgharta",
}

VARIANT_TO_CANONICAL = {
    "akkar": "akkar",
    "aakkar": "akkar",
    "aley": "aley",
    "baabda": "baabda",
    "baalbek": "baalbek",
    "batroun": "batroun",
    "al batroun": "batroun",
    "bcharre": "bcharre",
    "bsharri": "bcharre",
    "beirut": "beirut",
    "bent jbeil": "bent jbail",
    "bint jbeil": "bent jbail",
    "bent jbail": "bent jbail",
    "chouf": "chouf",
    "shouf": "chouf",
    "matn": "el metn",
    "metn": "el metn",
    "el metn": "el metn",
    "el meten": "el metn",
    "al matn": "el metn",
    "hasbaya": "hasbaya",
    "hasbaiya": "hasbaya",
    "hermel": "hermel",
    "el hermel": "hermel",
    "al hermel": "hermel",
    "jbeil": "jbail",
    "jbail": "jbail",
    "jubayl": "jbail",
    "jbjeil": "jbail",
    "jezzine": "jezzine",
    "kesrouan": "kesrouan",
    "keserwan": "kesrouan",
    "kesrwane": "kesrouan",
    "koura": "koura",
    "kura": "koura",
    "al kura": "koura",
    "marjaayoun": "marjaayoun",
    "marjayoun": "marjaayoun",
    "minieh-dinnieh": "minieh-dinnieh",
    "minieh-danniyeh": "minieh-dinnieh",
    "al minieh-danniyeh": "minieh-dinnieh",
    "danniyeh": "minieh-dinnieh",
    "nabatiye": "nabatiye",
    "nabatieh": "nabatiye",
    "nabatiyeh": "nabatiye",
    "al nabatieh": "nabatiye",
    "rachaya": "rachaya",
    "rashaya": "rachaya",
    "saida": "saida",
    "sidon": "saida",
    "sour": "sour",
    "tyre": "sour",
    "tyr": "sour",
    "tripoli": "tripoli",
    "west bekaa": "west bekaa",
    "beqaa west": "west bekaa",
    "zahle": "zahle",
    "zgharta": "zgharta",
}

# ==================================================
# HELPERS
# ==================================================
def normalize_admin2_name(value):
    if pd.isna(value):
        return None

    value = str(value).strip().lower()
    value = value.replace("–", "-").replace("—", "-")
    value = " ".join(value.split())
    return VARIANT_TO_CANONICAL.get(value, value)


def to_geo_district_name(value):
    canonical = normalize_admin2_name(value)
    return CANONICAL_TO_GEO.get(canonical)


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
        priority_path,
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


def add_district_boundaries(fig, gdf):
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

    if "month_num" in df.columns:
        df["month_num"] = pd.to_numeric(df["month_num"], errors="coerce")
    else:
        df["month_num"] = df["month"].map(MONTH_MAP)

    df = df[df["year"] >= 2022].copy()

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

    df["iso3"] = pd.to_numeric(df["iso3"], errors="coerce")
    df = df[df["iso3"].notna()].copy()
    df["iso_n3"] = df["iso3"].astype(int).astype(str).str.zfill(3)

    for col in ["country", "admin1", "admin2", "month", "event_type"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df["events"] = pd.to_numeric(df["events"], errors="coerce").fillna(0)
    df["fatalities"] = pd.to_numeric(df["fatalities"], errors="coerce").fillna(0)

    if "month_num" in df.columns:
        df["month_num"] = pd.to_numeric(df["month_num"], errors="coerce")
    else:
        df["month_num"] = df["month"].map(MONTH_MAP)

    df = df[df["year"] >= 2022].copy()

    df = df[
        df["year"].notna()
        & df["month"].notna()
        & df["month_num"].notna()
        & df["country"].notna()
        & df["event_type"].notna()
        & df["admin2"].notna()
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
def load_lbn_priority():
    df = pd.read_csv(priority_path)

    df["admin2_norm"] = df["admin2_norm"].astype(str).str.strip().str.lower()
    df["shapeName"] = df["admin2_norm"].apply(to_geo_district_name)

    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df["month_num"] = pd.to_numeric(df["month_num"], errors="coerce")
    df["month"] = df["month"].astype(str).str.strip()

    df["events"] = pd.to_numeric(df["events"], errors="coerce").fillna(0)
    df["fatalities"] = pd.to_numeric(df["fatalities"], errors="coerce").fillna(0)
    df["health_access_penalty"] = pd.to_numeric(
        df["health_access_penalty"], errors="coerce"
    ).fillna(0)
    df["priority_score"] = pd.to_numeric(df["priority_score"], errors="coerce").fillna(0)
    df["priority_rank"] = pd.to_numeric(df["priority_rank"], errors="coerce")

    df = df[
        df["year"].notna()
        & df["month_num"].notna()
        & df["month"].notna()
        & df["shapeName"].notna()
    ].copy()

    df["year"] = df["year"].astype(int)
    df["month_num"] = df["month_num"].astype(int)

    return df


# ==================================================
# LOAD EVERYTHING
# ==================================================
ensure_required_files()

country_conflict = load_country_conflict()
admin_conflict = load_admin_conflict()
world = load_world()
lbn_admin2 = load_lbn_admin2()
lbn_priority = load_lbn_priority()

lebanon_only = admin_conflict[
    admin_conflict["country"].astype(str).str.lower() == "lebanon"
].copy()

# ==================================================
# SESSION STATE
# ==================================================
if "view" not in st.session_state:
    st.session_state["view"] = "world"

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

    world_years = sorted(country_conflict["year"].unique().tolist())
    selected_year = st.sidebar.selectbox(
        "Year",
        world_years,
        index=world_years.index(st.session_state["world_year"])
        if st.session_state["world_year"] in world_years
        else 0,
    )
    st.session_state["world_year"] = selected_year

    available_months = (
        country_conflict.loc[
            country_conflict["year"] == selected_year, ["month_num", "month"]
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
        country_conflict.loc[
            (country_conflict["year"] == selected_year)
            & (country_conflict["month"].str.lower() == selected_month.lower()),
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

    color_scale = "YlOrRd" if metric == "events" else "Reds"

    filtered_world = country_conflict[
        (country_conflict["year"] == selected_year)
        & (country_conflict["month"].str.lower() == selected_month.lower())
    ].copy()

    filtered_world = filter_event_type(filtered_world, selected_event_type)

    st.title("Global Conflict Overview")
    st.caption(f"{selected_month} {selected_year} | Event Type: {selected_event_type}")
    st.info("Click Lebanon on the world map to open the Lebanon district view.")

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

    fig_world.update_geos(
        showcoastlines=True,
        showframe=False,
        bgcolor="rgba(0,0,0,0)",
    )

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
    )

    clicked_country = extract_selected_country(event)
    if clicked_country == "Lebanon":
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

    view_mode = st.sidebar.selectbox(
        "Lebanon View",
        ["Conflict View", "Priority View"]
    )

    # ==========================================
    # CONFLICT VIEW
    # ==========================================
    if view_mode == "Conflict View":
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

        st.title("Lebanon District Map")
        st.caption(f"{selected_month} {selected_year} | Event Type: {selected_event_type}")

        filtered_lbn = lebanon_only[
            (lebanon_only["year"] == selected_year)
            & (lebanon_only["month"].str.lower() == selected_month.lower())
        ].copy()

        filtered_lbn = filter_event_type(filtered_lbn, selected_event_type)
        filtered_lbn["shapeName"] = filtered_lbn["admin2"].apply(to_geo_district_name)

        if filtered_lbn.empty:
            district_values = pd.DataFrame(columns=["shapeName", "events", "fatalities"])
        else:
            district_values = (
                filtered_lbn.dropna(subset=["shapeName"])
                .groupby("shapeName", as_index=False)
                .agg({"events": "sum", "fatalities": "sum"})
            )

        merged_lbn = lbn_admin2.merge(
            district_values,
            how="left",
            on="shapeName",
        )

        merged_lbn["events"] = pd.to_numeric(merged_lbn["events"], errors="coerce").fillna(0)
        merged_lbn["fatalities"] = pd.to_numeric(merged_lbn["fatalities"], errors="coerce").fillna(0)

        merged_lbn = repair_geometries(merged_lbn)

        total_events = int(merged_lbn["events"].sum())
        total_fatalities = int(merged_lbn["fatalities"].sum())
        districts_with_data = int((merged_lbn[metric] > 0).sum())

        c1, c2, c3 = st.columns(3)
        c1.metric("Lebanon events", f"{total_events:,}")
        c2.metric("Lebanon fatalities", f"{total_fatalities:,}")
        c3.metric("Districts with data", f"{districts_with_data:,}")

        base_df = merged_lbn.copy()
        plot_df = merged_lbn[merged_lbn[metric] > 0].copy()

        color_scale = "YlOrRd" if metric == "events" else "Reds"
        real_max = float(plot_df[metric].max()) if not plot_df.empty else 1.0
        if real_max <= 0:
            real_max = 1.0

        minx, miny, maxx, maxy = lbn_admin2.total_bounds
        pad_x = (maxx - minx) * 0.08
        pad_y = (maxy - miny) * 0.08

        fig_lbn = go.Figure()

        fig_lbn.add_trace(
            go.Choropleth(
                geojson=json.loads(base_df.to_json()),
                locations=base_df["shapeName"],
                z=[0] * len(base_df),
                featureidkey="properties.shapeName",
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
                    locations=plot_df["shapeName"],
                    z=plot_df[metric],
                    featureidkey="properties.shapeName",
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
            title=f"Lebanon Districts - {metric.capitalize()} ({selected_month} {selected_year}) | {selected_event_type}",
            margin=dict(l=0, r=0, t=60, b=0),
            height=700,
            paper_bgcolor="white",
            plot_bgcolor="white",
        )

        add_district_boundaries(fig_lbn, lbn_admin2)
        add_country_outline(fig_lbn, lbn_admin2)

        st.plotly_chart(fig_lbn, use_container_width=True, key="lbn_conflict_chart")

        st.subheader(f"Top 10 Lebanon districts by {metric}")
        top_admin2 = (
            merged_lbn[["shapeName", "events", "fatalities"]]
            .sort_values(metric, ascending=False)
            .head(10)
            .reset_index(drop=True)
        )
        top_admin2.index = top_admin2.index + 1

        district_table = top_admin2[["shapeName", metric]].rename(
            columns={"shapeName": "District", metric: metric.capitalize()}
        )
        st.dataframe(district_table, use_container_width=True)

    # ==========================================
    # PRIORITY VIEW
    # ==========================================
    elif view_mode == "Priority View":
        lbn_years = sorted(lbn_priority["year"].unique().tolist())
        selected_year = st.sidebar.selectbox("Year", lbn_years)

        available_months = (
            lbn_priority.loc[
                lbn_priority["year"] == selected_year, ["month_num", "month"]
            ]
            .drop_duplicates()
            .sort_values("month_num")
        )
        month_list = available_months["month"].tolist()
        selected_month = st.sidebar.selectbox("Month", month_list)

        st.title("Lebanon Priority Map")
        st.caption(f"{selected_month} {selected_year} | Combined conflict + health access score")

        filtered_priority = lbn_priority[
            (lbn_priority["year"] == selected_year)
            & (lbn_priority["month"].str.lower() == selected_month.lower())
        ].copy()

        if filtered_priority.empty:
            st.warning("No priority data available for the selected month and year.")
            st.stop()

        district_priority = (
            filtered_priority.groupby("shapeName", as_index=False)
            .agg({
                "events": "sum",
                "fatalities": "sum",
                "health_access_penalty": "mean",
                "priority_score": "mean",
                "priority_rank": "min",
            })
        )

        merged_priority = lbn_admin2.merge(
            district_priority,
            how="left",
            on="shapeName",
        )

        merged_priority["events"] = pd.to_numeric(merged_priority["events"], errors="coerce").fillna(0)
        merged_priority["fatalities"] = pd.to_numeric(merged_priority["fatalities"], errors="coerce").fillna(0)
        merged_priority["health_access_penalty"] = pd.to_numeric(
            merged_priority["health_access_penalty"], errors="coerce"
        ).fillna(0)
        merged_priority["priority_score"] = pd.to_numeric(
            merged_priority["priority_score"], errors="coerce"
        ).fillna(0)

        merged_priority = repair_geometries(merged_priority)

        top_row = merged_priority.sort_values("priority_score", ascending=False).head(1)

        highest_district = top_row["shapeName"].iloc[0] if not top_row.empty else "-"
        highest_score = float(top_row["priority_score"].iloc[0]) if not top_row.empty else 0.0
        avg_score = float(merged_priority["priority_score"].mean()) if not merged_priority.empty else 0.0

        c1, c2, c3 = st.columns(3)
        c1.metric("Highest priority district", highest_district)
        c2.metric("Highest priority score", f"{highest_score:.3f}")
        c3.metric("Average priority score", f"{avg_score:.3f}")

        base_df = merged_priority.copy()
        plot_df = merged_priority[merged_priority["priority_score"] > 0].copy()

        real_max = float(plot_df["priority_score"].max()) if not plot_df.empty else 1.0
        if real_max <= 0:
            real_max = 1.0

        minx, miny, maxx, maxy = lbn_admin2.total_bounds
        pad_x = (maxx - minx) * 0.08
        pad_y = (maxy - miny) * 0.08

        fig_priority = go.Figure()

        fig_priority.add_trace(
            go.Choropleth(
                geojson=json.loads(base_df.to_json()),
                locations=base_df["shapeName"],
                z=[0] * len(base_df),
                featureidkey="properties.shapeName",
                colorscale=[[0, "white"], [1, "white"]],
                zmin=0,
                zmax=1,
                showscale=False,
                marker_line_width=0,
                marker_line_color="rgba(0,0,0,0)",
                customdata=base_df[
                    ["events", "fatalities", "health_access_penalty", "priority_score"]
                ].values,
                hovertemplate=(
                    "<b>%{location}</b><br>"
                    "events=%{customdata[0]:.0f}<br>"
                    "fatalities=%{customdata[1]:.0f}<br>"
                    "health penalty=%{customdata[2]:.2f}<br>"
                    "priority score=%{customdata[3]:.3f}<extra></extra>"
                ),
            )
        )

        if not plot_df.empty:
            fig_priority.add_trace(
                go.Choropleth(
                    geojson=json.loads(plot_df.to_json()),
                    locations=plot_df["shapeName"],
                    z=plot_df["priority_score"],
                    featureidkey="properties.shapeName",
                    colorscale="OrRd",
                    zmin=0,
                    zmax=real_max,
                    marker_line_width=0,
                    marker_line_color="rgba(0,0,0,0)",
                    colorbar=dict(title="Priority Score"),
                    customdata=plot_df[
                        ["events", "fatalities", "health_access_penalty", "priority_score"]
                    ].values,
                    hovertemplate=(
                        "<b>%{location}</b><br>"
                        "events=%{customdata[0]:.0f}<br>"
                        "fatalities=%{customdata[1]:.0f}<br>"
                        "health penalty=%{customdata[2]:.2f}<br>"
                        "priority score=%{customdata[3]:.3f}<extra></extra>"
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

        add_district_boundaries(fig_priority, lbn_admin2)
        add_country_outline(fig_priority, lbn_admin2)

        st.plotly_chart(fig_priority, use_container_width=True, key="lbn_priority_chart")

        st.subheader("Top 10 Lebanon districts by priority")
        top_priority = (
            merged_priority[["shapeName", "priority_score", "priority_rank"]]
            .sort_values(["priority_score", "shapeName"], ascending=[False, True])
            .head(10)
            .reset_index(drop=True)
        )
        top_priority.index = top_priority.index + 1

        priority_table = top_priority.rename(
            columns={
                "shapeName": "District",
                "priority_score": "Priority Score",
                "priority_rank": "Priority Rank",
            }
        )
        st.dataframe(priority_table, use_container_width=True)