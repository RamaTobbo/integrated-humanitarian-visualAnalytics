import os
os.environ["OGR_GEOJSON_MAX_OBJ_SIZE"] = "0"

import json
import re
import unicodedata
from pathlib import Path

import geopandas as gpd
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Global Conflict & Priority Dashboard", layout="wide")

# ==================================================
# PATHS
# ==================================================
BASE_DIR = Path(__file__).resolve().parent.parent

world_geojson_path = BASE_DIR / "data" / "raw" / "boundaries" / "world_countries.geojson"
conflict_country_path = BASE_DIR / "data" / "cleaned" / "global" / "conflict_country_monthlybytype.csv"
conflict_admin_path = BASE_DIR / "data" / "cleaned" / "global" / "conflict_standardized_monthlybytype.csv"

priority_country_path = BASE_DIR / "data" / "cleaned" / "global" / "global_priority_country_with_displacement_monthly.csv"
priority_admin1_path = BASE_DIR / "data" / "cleaned" / "global" / "global_priority_admin1_with_displacement_monthly.csv"

displacement_dest_path = BASE_DIR / "data" / "cleaned" / "global" / "displacement_admin1_destination_monthly_2024_2026.csv"
displacement_origin_path = BASE_DIR / "data" / "cleaned" / "global" / "displacement_admin1_origin_monthly_2024_2026.csv"

country_boundaries_dir = BASE_DIR / "data" / "cleaned" / "boundaries" / "countries"
lbn_admin2_fallback_path = BASE_DIR / "data" / "raw" / "boundaries" / "geoBoundaries-LBN-ADM2.geojson"

# ==================================================
# CONSTANTS
# ==================================================
MIN_YEAR = 2024
MAX_YEAR = 2026

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

COUNTRY_NAME_ALIASES = {
    "Russia": ["Russia", "Russian Federation"],
    "United States of America": ["United States of America", "United States", "USA"],
    "Syria": ["Syria", "Syrian Arab Republic"],
    "Iran": ["Iran", "Iran (Islamic Republic of)", "Islamic Republic of Iran"],
    "Venezuela": ["Venezuela", "Venezuela, Bolivarian Republic of"],
    "Bolivia": ["Bolivia", "Bolivia (Plurinational State of)"],
    "Tanzania": ["Tanzania", "United Republic of Tanzania"],
    "Moldova": ["Moldova", "Republic of Moldova"],
    "Laos": ["Laos", "Lao People's Democratic Republic"],
    "Czechia": ["Czechia", "Czech Republic"],
    "North Macedonia": ["North Macedonia", "Macedonia"],
    "Myanmar": ["Myanmar", "Burma"],
    "Palestine": ["Palestine", "State of Palestine"],
    "Democratic Republic of the Congo": [
        "Democratic Republic of the Congo",
        "Democratic Republic Of Congo",
        "Congo, Dem. Rep.",
        "DR Congo",
    ],
    "Republic of the Congo": [
        "Republic of the Congo",
        "Congo",
        "Congo, Rep.",
    ],
}

COUNTRY_CANONICAL_ALIASES = {
    "russian federation": "russia",
    "syrian arab republic": "syria",
    "iran (islamic republic of)": "iran",
    "islamic republic of iran": "iran",
    "venezuela, bolivarian republic of": "venezuela",
    "bolivia (plurinational state of)": "bolivia",
    "united republic of tanzania": "tanzania",
    "republic of moldova": "moldova",
    "lao people's democratic republic": "laos",
    "czech republic": "czechia",
    "state of palestine": "palestine",
    "democratic republic of congo": "democratic republic of the congo",
    "congo, dem. rep.": "democratic republic of the congo",
    "dr congo": "democratic republic of the congo",
    "congo, rep.": "republic of the congo",
}

NON_ADMIN_LOCATIONS = {
    "sea of azov",
    "azov sea",
    "eastern black sea",
    "black sea",
    "mediterranean sea",
    "red sea",
    "persian gulf",
    "cape fiolent",
    "international waters",
    "unknown",
    "not available",
    "",
}

GENERIC_SUFFIX_PATTERNS = [
    r"\s+governorate$",
    r"\s+governorates$",
    r"\s+governate$",
    r"\s+province$",
    r"\s+provinces$",
    r"\s+prefecture$",
    r"\s+prefectures$",
    r"\s+department$",
    r"\s+departments$",
    r"\s+region$",
    r"\s+regions$",
    r"\s+district$",
    r"\s+districts$",
    r"\s+county$",
    r"\s+counties$",
    r"\s+municipality$",
    r"\s+municipalities$",
    r"\s+state$",
    r"\s+states$",
    r"\s+oblast$",
]

KEEP_SUFFIX_EXACT = {
    "moscow oblast",
    "kyiv oblast",
    "odessa oblast",
}

# ==================================================
# HELPERS
# ==================================================
def normalize_text(value):
    if pd.isna(value):
        return None

    value = str(value).strip().lower()
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))

    value = value.replace("–", "-").replace("—", "-")
    value = value.replace("_", " ")
    value = value.replace("/", " ")
    value = value.replace(",", " ")
    value = value.replace("’", "'")
    value = re.sub(r"\s+", " ", value).strip()
    return value


def strip_generic_suffixes(value):
    if value is None:
        return None
    if value in KEEP_SUFFIX_EXACT:
        return value

    out = value
    for pattern in GENERIC_SUFFIX_PATTERNS:
        out = re.sub(pattern, "", out).strip()

    out = re.sub(r"\s+", " ", out).strip()
    return out


def canonical_country_norm(name):
    n = normalize_text(name)
    if n is None:
        return None
    return COUNTRY_CANONICAL_ALIASES.get(n, n)


def standardize_admin_name(value, country=None):
    value = normalize_text(value)
    country = canonical_country_norm(country)

    if value is None or value in NON_ADMIN_LOCATIONS:
        return None

    generic_aliases_before = {
        "kyiv city": "kyiv",
        "odesa": "odessa",
        "oddesa": "odessa",
        "republic of adygea": "adygea",
        "republic of bashkortostan": "bashkortostan",
        "republic of chuvash": "chuvashia",
        "republic of mordovia": "mordovia",
        "republic of tatarstan": "tatarstan",
        "republic of tuva": "tuva",
        "republic of karelia": "karelia",
        "sakha republic": "sakha",
        "komi republic": "komi",
        "altai republic": "altai republic",
        "autonomous republic of crimea": "autonomous republic of crimea",
    }
    value = generic_aliases_before.get(value, value)

    value = strip_generic_suffixes(value)

    generic_aliases_after = {
        "crimea": "autonomous republic of crimea",
        "kyiv city": "kyiv",
        "odesa": "odessa",
        "oddesa": "odessa",
        "nabatyeh": "al nabatieh",
        "nabatiyeh": "al nabatieh",
        "nabatiye": "al nabatieh",
        "republic of mordovia": "mordovia",
        "republic of karelia": "karelia",
    }
    value = generic_aliases_after.get(value, value)

    country_specific = {
        "lebanon": {
            "aakkar": "akkar",
            "akkar": "akkar",
            "beyrouth": "beirut",
            "beirut": "beirut",
            "beqaa": "bekaa",
            "bekaa": "bekaa",
            "baalbek hermel": "baalbek-hermel",
            "baalbek-hermel": "baalbek-hermel",
            "mont-liban": "mount lebanon",
            "mont liban": "mount lebanon",
            "mount lebanon": "mount lebanon",
            "keserwan-jbeil": "mount lebanon",
            "keserwan jbeil": "mount lebanon",
            "liban-nord": "north",
            "liban nord": "north",
            "north": "north",
            "liban-sud": "south",
            "liban sud": "south",
            "south": "south",
            "nabatiye": "al nabatieh",
            "nabatiyeh": "al nabatieh",
            "nabatyeh": "al nabatieh",
            "nabatye": "al nabatieh",
            "al nabatieh": "al nabatieh",
        },
        "ukraine": {
            "crimea": "autonomous republic of crimea",
            "autonomous republic of crimea": "autonomous republic of crimea",
            "kyiv city": "kyiv",
            "kyiv": "kyiv",
            "odesa": "odessa",
            "odessa": "odessa",
            "sevastopol": "sevastopol",
        },
        "russia": {
            "republic of adygea": "adygea",
            "adygea": "adygea",
            "republic of bashkortostan": "bashkortostan",
            "bashkortostan": "bashkortostan",
            "republic of chuvash": "chuvashia",
            "chuvashia": "chuvashia",
            "republic of mordovia": "mordovia",
            "mordovia": "mordovia",
            "republic of tatarstan": "tatarstan",
            "tatarstan": "tatarstan",
            "republic of tuva": "tuva",
            "tuva": "tuva",
            "republic of karelia": "karelia",
            "karelia": "karelia",
            "komi republic": "komi",
            "komi": "komi",
            "sakha republic": "sakha",
            "sakha": "sakha",
            "altai": "altai krai",
            "altai republic": "altai republic",
            "moscow oblast": "moscow oblast",
        },
    }

    if country in country_specific:
        value = country_specific[country].get(value, value)

    return value


def default_latest_period(df):
    temp = (
        df[["year", "month_num", "month"]]
        .drop_duplicates()
        .sort_values(["year", "month_num"])
    )
    last_row = temp.iloc[-1]
    return int(last_row["year"]), str(last_row["month"])


def default_latest_period_with_year_bounds(df, min_year=MIN_YEAR, max_year=MAX_YEAR):
    temp = (
        df[["year", "month_num", "month"]]
        .drop_duplicates()
        .sort_values(["year", "month_num"])
    )
    temp = temp[(temp["year"] >= min_year) & (temp["year"] <= max_year)].copy()
    if temp.empty:
        return default_latest_period(df)
    last_row = temp.iloc[-1]
    return int(last_row["year"]), str(last_row["month"])


def ensure_required_files():
    required_paths = [
        world_geojson_path,
        conflict_country_path,
        conflict_admin_path,
        priority_country_path,
        priority_admin1_path,
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
    outline = gdf.union_all().boundary if hasattr(gdf, "union_all") else gdf.unary_union.boundary
    add_line_geometry(fig, outline, color="black", width=2.2)


def repair_geometries(gdf):
    gdf = gdf.copy()
    gdf = gdf[gdf.geometry.notna()].copy()
    gdf = gdf[~gdf.geometry.is_empty].copy()
    try:
        gdf["geometry"] = gdf["geometry"].buffer(0)
    except Exception:
        pass
    gdf = gdf[gdf.geometry.notna()].copy()
    gdf = gdf[~gdf.geometry.is_empty].copy()
    return gdf


def extract_selected_country_info(event):
    if event is None:
        return None, None

    try:
        if isinstance(event, dict):
            selection = event.get("selection", {})
            points = selection.get("points", [])
        else:
            selection = getattr(event, "selection", {})
            points = selection.get("points", []) if isinstance(selection, dict) else []
    except Exception:
        return None, None

    if not points:
        return None, None

    point = points[0]
    custom = point.get("customdata", [])

    if custom and len(custom) >= 2:
        return str(custom[0]).strip().upper(), str(custom[1]).strip()

    location = point.get("location")
    if location:
        return str(location).strip().upper(), None

    return None, None


def detect_name_column(gdf):
    candidates = [
        "shapeName",
        "shapeName_en",
        "admin1Name",
        "ADM1_EN",
        "adm1_en",
        "NAME_1",
        "name_1",
        "province",
        "region",
        "state",
        "admin1",
        "name",
    ]
    for col in candidates:
        if col in gdf.columns:
            return col
    return None


def build_country_alias_lookup():
    lookup = {}
    for canonical, names in COUNTRY_NAME_ALIASES.items():
        all_names = [canonical] + names
        normalized = [normalize_text(x) for x in all_names]
        canonical_norm = normalize_text(canonical)
        for name in normalized:
            lookup[name] = canonical_norm
    return lookup


ALIAS_LOOKUP = build_country_alias_lookup()


def get_country_admin_rows(admin_df, selected_country_name):
    country_norm = canonical_country_norm(selected_country_name)

    out = admin_df[admin_df["country_norm"] == country_norm].copy()
    if not out.empty:
        return out

    aliases = COUNTRY_NAME_ALIASES.get(selected_country_name, [selected_country_name])
    alias_norms = [canonical_country_norm(x) for x in aliases]
    out = admin_df[admin_df["country_norm"].isin(alias_norms)].copy()
    return out


def metric_label(metric):
    labels = {
        "events": "Events",
        "fatalities": "Fatalities",
        "population_exposure": "Population Exposure",
        "displaced": "Displaced",
        "country_priority_score": "Priority Score",
        "priority_score_country": "Priority Score",
        "priority_score_global": "Priority Score",
    }
    return labels.get(metric, metric)

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
    df["country_norm"] = df["country"].apply(canonical_country_norm)

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
    df = df[(df["year"] >= MIN_YEAR) & (df["year"] <= MAX_YEAR)].copy()
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
    df["country_norm"] = df["country"].apply(canonical_country_norm)
    df["admin1_norm"] = df.apply(
        lambda row: standardize_admin_name(row["admin1"], row["country"]),
        axis=1
    )
    df = df[df["admin1_norm"].notna()].copy()
    df = df[(df["year"] >= MIN_YEAR) & (df["year"] <= MAX_YEAR)].copy()
    return df


@st.cache_data(show_spinner=False)
def load_country_priority():
    df = pd.read_csv(priority_country_path)

    for col in ["region", "country", "month", "country_priority_class"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    numeric_cols = [
        "year", "month_num", "events", "fatalities", "population_exposure", "displaced",
        "events_log", "fatalities_log", "exposure_log", "displaced_log",
        "events_norm", "fatalities_norm", "exposure_norm", "displaced_norm",
        "country_priority_score", "country_priority_rank",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df["country"] = df["country"].astype(str).str.strip()
    df["country_norm"] = df["country"].apply(canonical_country_norm)
    df["month"] = df["month"].astype(str).str.strip()

    df = df[
        df["year"].notna()
        & df["month"].notna()
        & df["month_num"].notna()
        & df["country"].notna()
    ].copy()

    df["year"] = df["year"].astype(int)
    df["month_num"] = df["month_num"].astype(int)
    df = df[(df["year"] >= MIN_YEAR) & (df["year"] <= MAX_YEAR)].copy()
    return df


@st.cache_data(show_spinner=False)
def load_admin1_priority():
    df = pd.read_csv(priority_admin1_path)

    for col in ["region", "country", "admin1_norm", "month", "priority_class_country", "priority_class_global"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    numeric_cols = [
        "year", "month_num", "events", "fatalities", "population_exposure", "displaced",
        "centroid_latitude", "centroid_longitude",
        "events_norm_country", "fatalities_norm_country", "displaced_norm_country", "exposure_norm_country",
        "priority_score_country", "priority_rank_country",
        "events_norm_global", "fatalities_norm_global", "displaced_norm_global", "exposure_norm_global",
        "priority_score_global", "priority_rank_global",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df["country"] = df["country"].astype(str).str.strip()
    df["country_norm"] = df["country"].apply(canonical_country_norm)
    df["admin1_norm"] = df.apply(
        lambda row: standardize_admin_name(row["admin1_norm"], row["country"]),
        axis=1
    )
    df["month"] = df["month"].astype(str).str.strip()

    df = df[
        df["year"].notna()
        & df["month"].notna()
        & df["month_num"].notna()
        & df["country"].notna()
        & df["admin1_norm"].notna()
    ].copy()

    df["year"] = df["year"].astype(int)
    df["month_num"] = df["month_num"].astype(int)
    df = df[(df["year"] >= MIN_YEAR) & (df["year"] <= MAX_YEAR)].copy()
    return df


@st.cache_data(show_spinner=False)
def load_displacement_dest():
    if not displacement_dest_path.exists():
        return pd.DataFrame(columns=[
            "country", "country_name", "year", "month_num", "month", "admin1_norm", "displaced_in"
        ])

    df = pd.read_csv(displacement_dest_path)
    df["country"] = df["country"].apply(canonical_country_norm)
    df["admin1_norm"] = df["admin1_norm"].apply(normalize_text)
    df["month"] = df["month"].astype(str).str.strip()

    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df["month_num"] = pd.to_numeric(df["month_num"], errors="coerce")
    df["displaced_in"] = pd.to_numeric(df["displaced_in"], errors="coerce").fillna(0)

    df = df[
        df["year"].notna()
        & df["month_num"].notna()
        & df["admin1_norm"].notna()
    ].copy()

    df["year"] = df["year"].astype(int)
    df["month_num"] = df["month_num"].astype(int)
    df = df[(df["year"] >= MIN_YEAR) & (df["year"] <= MAX_YEAR)].copy()
    return df


@st.cache_data(show_spinner=False)
def load_displacement_origin():
    if not displacement_origin_path.exists():
        return pd.DataFrame(columns=[
            "country", "country_name", "year", "month_num", "month", "admin1_norm", "displaced_from"
        ])

    df = pd.read_csv(displacement_origin_path)
    df["country"] = df["country"].apply(canonical_country_norm)
    df["admin1_norm"] = df["admin1_norm"].apply(normalize_text)
    df["month"] = df["month"].astype(str).str.strip()

    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df["month_num"] = pd.to_numeric(df["month_num"], errors="coerce")
    df["displaced_from"] = pd.to_numeric(df["displaced_from"], errors="coerce").fillna(0)

    df = df[
        df["year"].notna()
        & df["month_num"].notna()
        & df["admin1_norm"].notna()
    ].copy()

    df["year"] = df["year"].astype(int)
    df["month_num"] = df["month_num"].astype(int)
    df = df[(df["year"] >= MIN_YEAR) & (df["year"] <= MAX_YEAR)].copy()
    return df


@st.cache_data(show_spinner=False)
def load_world():
    world = gpd.read_file(world_geojson_path)

    if world.crs is None:
        world = world.set_crs(epsg=4326)
    else:
        world = world.to_crs(epsg=4326)

    world["iso_n3"] = world["iso_n3"].astype(str).str.strip().str.zfill(3)
    world["iso_a3"] = world["iso_a3"].astype(str).str.strip().str.upper()

    if "name" in world.columns:
        world["country_name_geo"] = world["name"].astype(str).str.strip()
    else:
        world["country_name_geo"] = world["iso_a3"]

    world["country_norm"] = world["country_name_geo"].apply(canonical_country_norm)
    world = world[world["iso_a3"] != "-99"].copy()
    return world


@st.cache_data(show_spinner=False)
def load_country_admin1_boundary(iso3):
    iso3 = str(iso3).strip().upper()
    path = country_boundaries_dir / f"{iso3}_adm1.geojson"

    iso_to_country = {
        "LBN": "Lebanon",
        "UKR": "Ukraine",
        "RUS": "Russia",
    }

    if path.exists():
        gdf = gpd.read_file(path)

        if gdf.crs is None:
            gdf = gdf.set_crs(epsg=4326)
        else:
            gdf = gdf.to_crs(epsg=4326)

        try:
            gdf["geometry"] = gdf["geometry"].simplify(0.01, preserve_topology=True)
        except Exception:
            pass

        gdf = repair_geometries(gdf)

        name_col = detect_name_column(gdf)
        if name_col is None:
            return None, None

        country_name = iso_to_country.get(iso3)
        gdf["admin_name"] = gdf[name_col].astype(str).str.strip()
        gdf["admin_name_norm"] = gdf["admin_name"].apply(
            lambda x: standardize_admin_name(x, country_name)
        )
        gdf = gdf[gdf["admin_name_norm"].notna()].copy()
        gdf = gdf[["admin_name", "admin_name_norm", "geometry"]].copy()
        return gdf, name_col

    if iso3 == "LBN" and lbn_admin2_fallback_path.exists():
        gdf = gpd.read_file(lbn_admin2_fallback_path)

        if gdf.crs is None:
            gdf = gdf.set_crs(epsg=4326)
        else:
            gdf = gdf.to_crs(epsg=4326)

        gdf["shapeName"] = gdf["shapeName"].astype(str).str.strip()
        gdf["admin_name"] = gdf["shapeName"].map(DISTRICT_TO_ADMIN1_GEO)
        gdf = gdf.dropna(subset=["admin_name"]).copy()
        gdf = gdf.dissolve(by="admin_name", as_index=False)
        gdf = repair_geometries(gdf)
        gdf["admin_name_norm"] = gdf["admin_name"].apply(
            lambda x: standardize_admin_name(x, "Lebanon")
        )
        gdf = gdf[gdf["admin_name_norm"].notna()].copy()
        gdf = gdf[["admin_name", "admin_name_norm", "geometry"]].copy()
        return gdf, "admin_name"

    return None, None

# ==================================================
# LOAD
# ==================================================
ensure_required_files()

country_conflict = load_country_conflict()
admin_conflict = load_admin_conflict()
country_priority = load_country_priority()
admin1_priority = load_admin1_priority()
displacement_dest = load_displacement_dest()
displacement_origin = load_displacement_origin()
world = load_world()

# ==================================================
# SESSION STATE
# ==================================================
if "view" not in st.session_state:
    st.session_state["view"] = "world"

if "selected_iso3" not in st.session_state:
    st.session_state["selected_iso3"] = None

if "selected_country_name" not in st.session_state:
    st.session_state["selected_country_name"] = None

if "world_country" not in st.session_state:
    st.session_state["world_country"] = "All"

if "world_mode" not in st.session_state:
    st.session_state["world_mode"] = "Conflict View"

if "world_year" not in st.session_state or "world_month" not in st.session_state:
    y, m = default_latest_period_with_year_bounds(country_conflict)
    st.session_state["world_year"] = y
    st.session_state["world_month"] = m

if "world_event_type" not in st.session_state:
    st.session_state["world_event_type"] = "All"

if "world_metric" not in st.session_state:
    st.session_state["world_metric"] = "events"

if "country_year" not in st.session_state:
    st.session_state["country_year"] = None

if "country_month" not in st.session_state:
    st.session_state["country_month"] = None

if "country_event_type" not in st.session_state:
    st.session_state["country_event_type"] = "All"

if "country_metric" not in st.session_state:
    st.session_state["country_metric"] = "events"


# ==================================================
# WORLD VIEW
# ==================================================
if st.session_state["view"] == "world":
    st.sidebar.title("World Filters")

    world_mode = st.sidebar.selectbox(
        "World View",
        ["Conflict View", "Priority View"],
        index=0 if st.session_state["world_mode"] == "Conflict View" else 1,
    )
    st.session_state["world_mode"] = world_mode

    source_df = country_conflict.copy() if world_mode == "Conflict View" else country_priority.copy()

    country_options = ["All"] + sorted(source_df["country"].dropna().unique().tolist())
    selected_country = st.sidebar.selectbox(
        "Country",
        country_options,
        index=country_options.index(st.session_state["world_country"])
        if st.session_state["world_country"] in country_options else 0,
    )
    st.session_state["world_country"] = selected_country

    base_df = source_df.copy()
    if selected_country != "All":
        selected_country_norm = canonical_country_norm(selected_country)
        base_df = base_df[base_df["country_norm"] == selected_country_norm].copy()

    world_years = sorted([y for y in base_df["year"].dropna().unique().tolist() if MIN_YEAR <= y <= MAX_YEAR])
    if not world_years:
        st.warning("No years available in the selected range.")
        st.stop()

    selected_year = st.sidebar.selectbox(
        "Year",
        world_years,
        index=world_years.index(st.session_state["world_year"])
        if st.session_state["world_year"] in world_years else len(world_years) - 1,
    )
    st.session_state["world_year"] = selected_year

    available_months = (
        base_df.loc[base_df["year"] == selected_year, ["month_num", "month"]]
        .drop_duplicates()
        .sort_values("month_num")
    )
    month_list = available_months["month"].tolist()
    if not month_list:
        st.warning("No months available for the selected year.")
        st.stop()

    selected_month = st.sidebar.selectbox(
        "Month",
        month_list,
        index=month_list.index(st.session_state["world_month"])
        if st.session_state["world_month"] in month_list else len(month_list) - 1,
    )
    st.session_state["world_month"] = selected_month

    if world_mode == "Conflict View":
        available_event_types = (
            base_df.loc[
                (base_df["year"] == selected_year)
                & (base_df["month"].str.lower() == selected_month.lower()),
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
            if st.session_state["world_event_type"] in available_event_types else 0,
        )
        st.session_state["world_event_type"] = selected_event_type

        metric = st.sidebar.selectbox(
            "Metric",
            ["events", "fatalities"],
            index=0 if st.session_state["world_metric"] == "events" else 1,
        )
        st.session_state["world_metric"] = metric

        filtered_world = base_df[
            (base_df["year"] == selected_year)
            & (base_df["month"].str.lower() == selected_month.lower())
        ].copy()
        filtered_world = filter_event_type(filtered_world, selected_event_type)

        if filtered_world.empty:
            st.warning("No data available for the selected filters.")
            st.stop()

        country_period = (
            filtered_world.groupby(["iso_n3", "country", "country_norm"], as_index=False)
            .agg({"events": "sum", "fatalities": "sum"})
        )

        merged_world = world.merge(country_period, how="left", on=["iso_n3", "country_norm"])
        merged_world["events"] = merged_world["events"].fillna(0)
        merged_world["fatalities"] = merged_world["fatalities"].fillna(0)
        merged_world["country"] = merged_world["country"].fillna(merged_world["country_name_geo"])

        total_events = int(country_period["events"].sum())
        total_fatalities = int(country_period["fatalities"].sum())
        countries_with_data = int((country_period[metric] > 0).sum())

        st.title("Global Conflict Overview" if selected_country == "All" else f"{selected_country} Conflict Overview")
        st.caption(f"{selected_month} {selected_year} | Event Type: {selected_event_type}")

        c1, c2, c3 = st.columns(3)
        c1.metric("Total events", f"{total_events:,}")
        c2.metric("Total fatalities", f"{total_fatalities:,}")
        c3.metric("Countries with data", f"{countries_with_data:,}")

        color_scale = "YlOrRd" if metric == "events" else "Reds"

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
                    "iso_a3": False,
                },
                custom_data=["iso_a3", "country_name_geo"],
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
                key="world_chart_conflict_all",
            )

            clicked_iso3, clicked_country_name = extract_selected_country_info(event)
            if clicked_iso3:
                st.session_state["selected_iso3"] = clicked_iso3
                st.session_state["selected_country_name"] = clicked_country_name
                st.session_state["view"] = "country"
                st.session_state["country_year"] = None
                st.session_state["country_month"] = None
                st.rerun()

        else:
            selected_geo = merged_world[
                merged_world["country_norm"] == canonical_country_norm(selected_country)
            ].copy()

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
                    "iso_a3": False,
                },
                projection="natural earth",
                title=f"{selected_country} - {metric.capitalize()} ({selected_month} {selected_year}) | {selected_event_type}",
            )

            fig_selected.update_traces(marker_line_color="gray", marker_line_width=0.6)
            fig_selected.update_geos(
                showcountries=True,
                showcoastlines=True,
                showframe=False,
                bgcolor="rgba(0,0,0,0)",
            )
            fig_selected.update_layout(
                margin=dict(l=0, r=0, t=60, b=0),
                height=550,
                coloraxis_colorbar_title=metric.capitalize(),
            )

            st.plotly_chart(fig_selected, use_container_width=True, key="world_chart_conflict_selected")

            selected_row = world[world["country_norm"] == canonical_country_norm(selected_country)]
            if not selected_row.empty:
                selected_iso3 = selected_row["iso_a3"].iloc[0]
                if st.button(f"Open {selected_country} admin1 view"):
                    st.session_state["selected_iso3"] = selected_iso3
                    st.session_state["selected_country_name"] = selected_country
                    st.session_state["view"] = "country"
                    st.session_state["country_year"] = None
                    st.session_state["country_month"] = None
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

    else:
        metric = st.sidebar.selectbox(
            "Priority Metric",
            ["country_priority_score", "events", "fatalities", "displaced", "population_exposure"],
            index=0,
        )

        filtered_world = base_df[
            (base_df["year"] == selected_year)
            & (base_df["month"].str.lower() == selected_month.lower())
        ].copy()

        if filtered_world.empty:
            st.warning("No priority data available for the selected filters.")
            st.stop()

        world_priority = (
            filtered_world.groupby(["country_norm"], as_index=False)
            .agg({
                "events": "sum",
                "fatalities": "sum",
                "population_exposure": "sum",
                "displaced": "sum",
                "country_priority_score": "mean",
                "country_priority_rank": "min",
            })
        )

        country_name_lookup = (
            filtered_world.groupby("country_norm", as_index=False)["country"]
            .first()
        )
        world_priority = world_priority.merge(country_name_lookup, how="left", on="country_norm")

        merged_world = world.merge(world_priority, how="left", on="country_norm")
        for col in ["events", "fatalities", "population_exposure", "displaced", "country_priority_score"]:
            merged_world[col] = pd.to_numeric(merged_world[col], errors="coerce").fillna(0)

        merged_world["country"] = merged_world["country"].fillna(merged_world["country_name_geo"])

        total_events = int(world_priority["events"].sum())
        total_fatalities = int(world_priority["fatalities"].sum())
        total_displaced = float(world_priority["displaced"].sum())
        countries_with_data = int((merged_world["country_priority_score"] > 0).sum())

        st.title("Global Priority Overview" if selected_country == "All" else f"{selected_country} Priority Overview")
        st.caption(f"{selected_month} {selected_year} | Priority based on events, fatalities, displacement, and exposure")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total events", f"{total_events:,}")
        c2.metric("Total fatalities", f"{total_fatalities:,}")
        c3.metric("Total displaced", f"{total_displaced:,.0f}")
        c4.metric("Countries with priority", f"{countries_with_data:,}")

        color_scale = "OrRd" if metric == "country_priority_score" else "YlOrRd"

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
                    "displaced": True,
                    "population_exposure": True,
                    "country_priority_score": ':.3f',
                    "iso_n3": False,
                    "iso_a3": False,
                },
                custom_data=["iso_a3", "country_name_geo"],
                projection="natural earth",
                title=f"World Priority Map - {metric_label(metric)} ({selected_month} {selected_year})",
            )

            fig_world.update_traces(marker_line_color="gray", marker_line_width=0.4)
            fig_world.update_geos(showcoastlines=True, showframe=False, bgcolor="rgba(0,0,0,0)")
            fig_world.update_layout(
                margin=dict(l=0, r=0, t=60, b=0),
                height=650,
                coloraxis_colorbar_title=metric_label(metric),
            )

            event = st.plotly_chart(
                fig_world,
                use_container_width=True,
                on_select="rerun",
                selection_mode=("points",),
                key="world_chart_priority_all",
            )

            clicked_iso3, clicked_country_name = extract_selected_country_info(event)
            if clicked_iso3:
                st.session_state["selected_iso3"] = clicked_iso3
                st.session_state["selected_country_name"] = clicked_country_name
                st.session_state["view"] = "country"
                st.session_state["country_year"] = None
                st.session_state["country_month"] = None
                st.rerun()

        else:
            selected_geo = merged_world[
                merged_world["country_norm"] == canonical_country_norm(selected_country)
            ].copy()

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
                    "displaced": True,
                    "population_exposure": True,
                    "country_priority_score": ':.3f',
                    "iso_n3": False,
                    "iso_a3": False,
                },
                projection="natural earth",
                title=f"{selected_country} - {metric_label(metric)} ({selected_month} {selected_year})",
            )

            fig_selected.update_traces(marker_line_color="gray", marker_line_width=0.6)
            fig_selected.update_geos(
                showcountries=True,
                showcoastlines=True,
                showframe=False,
                bgcolor="rgba(0,0,0,0)",
            )
            fig_selected.update_layout(
                margin=dict(l=0, r=0, t=60, b=0),
                height=550,
                coloraxis_colorbar_title=metric_label(metric),
            )

            st.plotly_chart(fig_selected, use_container_width=True, key="world_chart_priority_selected")

            selected_row = world[world["country_norm"] == canonical_country_norm(selected_country)]
            if not selected_row.empty:
                selected_iso3 = selected_row["iso_a3"].iloc[0]
                if st.button(f"Open {selected_country} admin1 view"):
                    st.session_state["selected_iso3"] = selected_iso3
                    st.session_state["selected_country_name"] = selected_country
                    st.session_state["view"] = "country"
                    st.session_state["country_year"] = None
                    st.session_state["country_month"] = None
                    st.rerun()

        st.subheader(f"Top 10 countries by {metric_label(metric)}")
        top_countries = (
            world_priority.sort_values(metric, ascending=False)
            .head(10)
            .reset_index(drop=True)
        )
        top_countries.index = top_countries.index + 1

        cols = ["country", metric]
        if metric == "country_priority_score" and "country_priority_rank" in top_countries.columns:
            cols.append("country_priority_rank")

        top_table = top_countries[cols].rename(
            columns={
                "country": "Country",
                metric: metric_label(metric),
                "country_priority_rank": "Priority Rank",
            }
        )
        st.dataframe(top_table, use_container_width=True)

# ==================================================
# COUNTRY VIEW
# ==================================================
else:
    selected_iso3 = st.session_state["selected_iso3"]
    selected_country_name = st.session_state["selected_country_name"]

    if not selected_iso3 or not selected_country_name:
        st.session_state["view"] = "world"
        st.rerun()

    st.sidebar.title("Country Filters")

    if st.sidebar.button("← Back to world"):
        st.session_state["view"] = "world"
        st.rerun()

    boundary_gdf, boundary_name_col = load_country_admin1_boundary(selected_iso3)

    if boundary_gdf is None or boundary_gdf.empty:
        st.title(f"{selected_country_name} Admin1 View")
        st.warning(
            f"No ADM1 boundary file found for {selected_country_name} ({selected_iso3}). "
            f"Add this file:\n\n"
            f"data/cleaned/boundaries/countries/{selected_iso3}_adm1.geojson"
        )
        st.stop()

    country_conflict_rows = get_country_admin_rows(admin_conflict, selected_country_name)
    country_priority_rows = get_country_admin_rows(admin1_priority, selected_country_name)

    if country_conflict_rows.empty and country_priority_rows.empty:
        st.title(f"{selected_country_name} Admin1 View")
        st.warning("No admin-level data found for this country.")
        st.stop()

    available_years = sorted(country_conflict_rows["year"].dropna().unique().tolist())
    available_years = [y for y in available_years if MIN_YEAR <= y <= MAX_YEAR]

    if not available_years:
        st.warning("No conflict year values available for this country.")
        st.stop()

    if (
        st.session_state["country_year"] is None
        or st.session_state["country_year"] not in available_years
    ):
        latest_y, latest_m = default_latest_period_with_year_bounds(country_conflict_rows)
        st.session_state["country_year"] = latest_y
        st.session_state["country_month"] = latest_m

    selected_year = st.sidebar.selectbox(
        "Year",
        available_years,
        index=available_years.index(st.session_state["country_year"]),
    )
    st.session_state["country_year"] = selected_year

    available_months = (
        country_conflict_rows.loc[
            country_conflict_rows["year"] == selected_year,
            ["month_num", "month"]
        ]
        .drop_duplicates()
        .sort_values("month_num")
    )

    month_list = available_months["month"].tolist()

    if not month_list:
        st.warning("No conflict months available for the selected year.")
        st.stop()

    if st.session_state["country_month"] not in month_list:
        st.session_state["country_month"] = month_list[0]

    selected_month = st.sidebar.selectbox(
        "Month",
        month_list,
        index=month_list.index(st.session_state["country_month"]),
    )
    st.session_state["country_month"] = selected_month

    view_mode = st.sidebar.selectbox("Country View", ["Conflict View", "Priority View"])

    metric = st.sidebar.selectbox(
        "Conflict Metric",
        ["events", "fatalities"],
        index=0 if st.session_state["country_metric"] == "events" else 1,
    )
    st.session_state["country_metric"] = metric

    if view_mode == "Conflict View":
        available_event_types = (
            country_conflict_rows.loc[
                (country_conflict_rows["year"] == selected_year)
                & (country_conflict_rows["month"].str.lower() == selected_month.lower()),
                "event_type",
            ]
            .dropna()
            .drop_duplicates()
            .sort_values()
            .tolist()
        )
        available_event_types = ["All"] + available_event_types if available_event_types else ["All"]

        if st.session_state["country_event_type"] not in available_event_types:
            st.session_state["country_event_type"] = "All"

        selected_event_type = st.sidebar.selectbox(
            "Event Type",
            available_event_types,
            index=available_event_types.index(st.session_state["country_event_type"]),
        )
        st.session_state["country_event_type"] = selected_event_type

        filtered_country = country_conflict_rows[
            (country_conflict_rows["year"] == selected_year)
            & (country_conflict_rows["month"].str.lower() == selected_month.lower())
        ].copy()
        filtered_country = filter_event_type(filtered_country, selected_event_type)

        if filtered_country.empty:
            st.title(f"{selected_country_name} Admin1 Conflict Map")
            st.warning("No conflict data available for the selected filters.")
            st.stop()

        grouped = (
            filtered_country.dropna(subset=["admin1_norm"])
            .groupby("admin1_norm", as_index=False)
            .agg({"events": "sum", "fatalities": "sum"})
        )

        merged_country = boundary_gdf.merge(
            grouped,
            how="left",
            left_on="admin_name_norm",
            right_on="admin1_norm"
        )
        merged_country["events"] = pd.to_numeric(merged_country["events"], errors="coerce").fillna(0)
        merged_country["fatalities"] = pd.to_numeric(merged_country["fatalities"], errors="coerce").fillna(0)
        merged_country = repair_geometries(merged_country)

        minx, miny, maxx, maxy = merged_country.total_bounds
        pad_x = (maxx - minx) * 0.08 if maxx > minx else 1
        pad_y = (maxy - miny) * 0.08 if maxy > miny else 1

        st.title(f"{selected_country_name} Admin1 Conflict Map")
        st.caption(f"{selected_month} {selected_year} | Event Type: {selected_event_type}")

        total_events = int(merged_country["events"].sum())
        total_fatalities = int(merged_country["fatalities"].sum())
        areas_with_data = int((merged_country[metric] > 0).sum())

        c1, c2, c3 = st.columns(3)
        c1.metric(f"{selected_country_name} events", f"{total_events:,}")
        c2.metric(f"{selected_country_name} fatalities", f"{total_fatalities:,}")
        c3.metric("Admin1 areas with data", f"{areas_with_data:,}")

        base_df = merged_country.copy()
        plot_df = merged_country[merged_country[metric] > 0].copy()

        color_scale = "YlOrRd" if metric == "events" else "Reds"
        real_max = float(plot_df[metric].max()) if not plot_df.empty else 1.0
        if real_max <= 0:
            real_max = 1.0

        fig_country = go.Figure()

        fig_country.add_trace(
            go.Choropleth(
                geojson=json.loads(base_df.to_json()),
                locations=base_df["admin_name"],
                z=[0] * len(base_df),
                featureidkey="properties.admin_name",
                colorscale=[[0, "white"], [1, "white"]],
                zmin=0,
                zmax=1,
                showscale=False,
                marker_line_width=0,
                marker_line_color="rgba(0,0,0,0)",
                customdata=base_df[["events", "fatalities"]].fillna(0).astype(float).values,
                hovertemplate=(
                    "<b>%{location}</b><br>"
                    "events=%{customdata[0]:.0f}<br>"
                    "fatalities=%{customdata[1]:.0f}<extra></extra>"
                ),
            )
        )

        if not plot_df.empty:
            fig_country.add_trace(
                go.Choropleth(
                    geojson=json.loads(plot_df.to_json()),
                    locations=plot_df["admin_name"],
                    z=plot_df[metric],
                    featureidkey="properties.admin_name",
                    colorscale=color_scale,
                    zmin=0,
                    zmax=real_max,
                    marker_line_width=0,
                    marker_line_color="rgba(0,0,0,0)",
                    colorbar=dict(title=metric.capitalize()),
                    customdata=plot_df[["events", "fatalities"]].fillna(0).astype(float).values,
                    hovertemplate=(
                        "<b>%{location}</b><br>"
                        "events=%{customdata[0]:.0f}<br>"
                        "fatalities=%{customdata[1]:.0f}<extra></extra>"
                    ),
                )
            )

        fig_country.update_geos(
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

        fig_country.update_layout(
            title=f"{selected_country_name} Admin1 - {metric.capitalize()} ({selected_month} {selected_year}) | {selected_event_type}",
            margin=dict(l=0, r=0, t=60, b=0),
            height=700,
            paper_bgcolor="white",
            plot_bgcolor="white",
        )

        add_boundaries(fig_country, merged_country)
        add_country_outline(fig_country, merged_country)

        st.plotly_chart(fig_country, use_container_width=True, key=f"{selected_iso3}_conflict_chart")

        st.subheader(f"Top 10 admin1 areas by {metric}")
        top_areas = (
            merged_country[["admin_name", "events", "fatalities"]]
            .sort_values(metric, ascending=False)
            .head(10)
            .reset_index(drop=True)
        )
        top_areas.index = top_areas.index + 1

        area_table = top_areas[["admin_name", metric]].rename(
            columns={"admin_name": "Admin1", metric: metric.capitalize()}
        )
        st.dataframe(area_table, use_container_width=True)

    else:
        

        country_priority_df = country_priority_rows[
            (country_priority_rows["year"] == selected_year)
            & (country_priority_rows["month"].str.lower() == selected_month.lower())
        ].copy()

        # Merge displacement for all countries
        selected_country_norm = canonical_country_norm(selected_country_name)

        disp_dest_month = displacement_dest[
            (displacement_dest["country"] == selected_country_norm)
            & (displacement_dest["year"] == selected_year)
            & (displacement_dest["month"].str.lower() == selected_month.lower())
        ][["admin1_norm", "displaced_in"]].copy()

        disp_origin_month = displacement_origin[
            (displacement_origin["country"] == selected_country_norm)
            & (displacement_origin["year"] == selected_year)
            & (displacement_origin["month"].str.lower() == selected_month.lower())
        ][["admin1_norm", "displaced_from"]].copy()

        # Apply same standardization before merge
        disp_dest_month["admin1_norm"] = disp_dest_month["admin1_norm"].apply(
            lambda x: standardize_admin_name(x, selected_country_name)
        )
        disp_origin_month["admin1_norm"] = disp_origin_month["admin1_norm"].apply(
            lambda x: standardize_admin_name(x, selected_country_name)
        )

        country_priority_df = country_priority_df.merge(
            disp_dest_month,
            how="left",
            on="admin1_norm"
        )

        country_priority_df = country_priority_df.merge(
            disp_origin_month,
            how="left",
            on="admin1_norm"
        )

        country_priority_df["displaced_in"] = pd.to_numeric(
            country_priority_df.get("displaced_in", 0), errors="coerce"
        ).fillna(0)

        country_priority_df["displaced_from"] = pd.to_numeric(
            country_priority_df.get("displaced_from", 0), errors="coerce"
        ).fillna(0)

        # humanitarian pressure = current incoming/present displacement
        country_priority_df["displaced"] = country_priority_df["displaced_in"]

        if country_priority_df.empty:
            st.title(f"{selected_country_name} Priority Map")
            st.warning("No priority data available for this country for the selected month/year.")
            st.stop()
        score_col = "priority_score_country"
        rank_col = "priority_rank_country"
        class_col = "priority_class_country"
        title_suffix = "Priority"

        merged_priority = boundary_gdf.merge(
            country_priority_df,
            how="left",
            left_on="admin_name_norm",
            right_on="admin1_norm"
        )

        for col in ["events", "fatalities", "population_exposure", "displaced", "displaced_in", "displaced_from", score_col]:
            if col in merged_priority.columns:
                merged_priority[col] = pd.to_numeric(merged_priority[col], errors="coerce").fillna(0)

        if rank_col in merged_priority.columns:
            merged_priority[rank_col] = pd.to_numeric(merged_priority[rank_col], errors="coerce")

        merged_priority = repair_geometries(merged_priority)

        minx, miny, maxx, maxy = merged_priority.total_bounds
        pad_x = (maxx - minx) * 0.08 if maxx > minx else 1
        pad_y = (maxy - miny) * 0.08 if maxy > miny else 1

        top_row = merged_priority.sort_values(score_col, ascending=False).head(1)
        highest_area = top_row["admin_name"].iloc[0] if not top_row.empty else "-"
        highest_score = float(top_row[score_col].iloc[0]) if not top_row.empty else 0.0
        avg_score = float(merged_priority[score_col].fillna(0).mean()) if not merged_priority.empty else 0.0
        total_displaced = float(merged_priority["displaced"].sum()) if "displaced" in merged_priority.columns else 0.0

        st.title(f"{selected_country_name} Priority Map")
        st.caption(f"{selected_month} {selected_year} | {title_suffix}")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Highest priority area", highest_area)
        c2.metric("Highest priority score", f"{highest_score:.3f}")
        c3.metric("Average priority score", f"{avg_score:.3f}")
        c4.metric("Total displaced", f"{total_displaced:,.0f}")

        base_df = merged_priority.copy()
        plot_df = merged_priority[merged_priority[score_col] > 0].copy()

        for extra_col in ["displaced_in", "displaced_from"]:
            if extra_col not in base_df.columns:
                base_df[extra_col] = 0
            if extra_col not in plot_df.columns:
                plot_df[extra_col] = 0

        real_max = float(plot_df[score_col].max()) if not plot_df.empty else 1.0
        if real_max <= 0:
            real_max = 1.0

        fig_priority = go.Figure()

        fig_priority.add_trace(
            go.Choropleth(
                geojson=json.loads(base_df.to_json()),
                locations=base_df["admin_name"],
                z=[0] * len(base_df),
                featureidkey="properties.admin_name",
                colorscale=[[0, "white"], [1, "white"]],
                zmin=0,
                zmax=1,
                showscale=False,
                marker_line_width=0,
                marker_line_color="rgba(0,0,0,0)",
                customdata=base_df[
                    ["events", "fatalities", "displaced_in", "displaced_from", "population_exposure", score_col]
                ].fillna(0).astype(float).values,
                hovertemplate=(
                    "<b>%{location}</b><br>"
                    "events=%{customdata[0]:.0f}<br>"
                    "fatalities=%{customdata[1]:.0f}<br>"
                    "displaced in=%{customdata[2]:,.0f}<br>"
                    "displaced from=%{customdata[3]:,.0f}<br>"
                    "exposure=%{customdata[4]:,.0f}<br>"
                    "priority score=%{customdata[5]:.3f}<extra></extra>"
                ),
            )
        )

        if not plot_df.empty:
            fig_priority.add_trace(
                go.Choropleth(
                    geojson=json.loads(plot_df.to_json()),
                    locations=plot_df["admin_name"],
                    z=plot_df[score_col],
                    featureidkey="properties.admin_name",
                    colorscale="OrRd",
                    zmin=0,
                    zmax=real_max,
                    marker_line_width=0,
                    marker_line_color="rgba(0,0,0,0)",
                    colorbar=dict(title="Priority Score"),
                    customdata=plot_df[
                        ["events", "fatalities", "displaced_in", "displaced_from", "population_exposure", score_col]
                    ].fillna(0).astype(float).values,
                    hovertemplate=(
                        "<b>%{location}</b><br>"
                        "events=%{customdata[0]:.0f}<br>"
                        "fatalities=%{customdata[1]:.0f}<br>"
                        "displaced in=%{customdata[2]:,.0f}<br>"
                        "displaced from=%{customdata[3]:,.0f}<br>"
                        "exposure=%{customdata[4]:,.0f}<br>"
                        "priority score=%{customdata[5]:.3f}<extra></extra>"
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
            title=f"{selected_country_name} Priority Map ({selected_month} {selected_year}) | {title_suffix}",
            margin=dict(l=0, r=0, t=60, b=0),
            height=700,
            paper_bgcolor="white",
            plot_bgcolor="white",
        )

        add_boundaries(fig_priority, merged_priority)
        add_country_outline(fig_priority, merged_priority)

        st.plotly_chart(fig_priority, use_container_width=True, key=f"{selected_iso3}_priority_chart")

        st.subheader("Top 10 admin1 areas by priority")
        top_priority = (
            merged_priority[["admin_name", score_col, rank_col, class_col]]
            .sort_values([score_col, "admin_name"], ascending=[False, True])
            .head(10)
            .reset_index(drop=True)
        )
        top_priority.index = top_priority.index + 1

        priority_table = top_priority.rename(
            columns={
                "admin_name": "Admin1",
                score_col: "Priority Score",
                rank_col: "Priority Rank",
                class_col: "Priority Class",
            }
        )
        st.dataframe(priority_table, use_container_width=True)