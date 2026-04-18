import os
os.environ["OGR_GEOJSON_MAX_OBJ_SIZE"] = "0"

import json
import re
import unicodedata
from pathlib import Path

import geopandas as gpd
import pandas as pd
import plotly.express as px
import streamlit as st

# ──────────────────────────────────────────────────
# PAGE CONFIG & GLOBAL STYLE
# ──────────────────────────────────────────────────
st.set_page_config(
    page_title="Conflict & Priority Intelligence Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Playfair+Display:wght@500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
    --bg-base:        #f7f8fa;
    --bg-panel:       #ffffff;
    --bg-card:        #ffffff;
    --bg-soft:        #eef1f6;
    --bg-hover:       #f1f4f9;
    --border:         #e4e8ef;
    --border-bright:  #d3dae4;

    --accent:         #2c4a6e;
    --accent-soft:    #5a7aa0;
    --accent-light:   #e8eef6;
    --accent-ink:     #1a2e48;

    --hl-warm:        #b8703a;
    --hl-warm-soft:   #f4e5d6;
    --hl-teal:        #5a8a82;
    --hl-teal-soft:   #e2eeec;
    --hl-gold:        #a8864a;
    --hl-gold-soft:   #f2ead8;

    --text-primary:   #1b2230;
    --text-secondary: #5a6577;
    --text-dim:       #8893a4;
    --text-faint:     #b0b9c7;

    --shadow-sm:      0 1px 2px rgba(20, 30, 50, 0.04);
    --shadow-md:      0 2px 8px rgba(20, 30, 50, 0.06);
    --shadow-lg:      0 6px 24px rgba(20, 30, 50, 0.08);
}

html, body, [data-testid="stAppViewContainer"] {
    background-color: var(--bg-base) !important;
    font-family: 'Inter', sans-serif;
    color: var(--text-primary);
    -webkit-font-smoothing: antialiased;
}

[data-testid="stSidebar"] {
    background-color: var(--bg-panel) !important;
    border-right: 1px solid var(--border) !important;
    box-shadow: var(--shadow-sm);
}
[data-testid="stSidebar"] * { color: var(--text-primary) !important; }

.sidebar-brand {
    padding: 22px 4px 18px 4px;
    border-bottom: 1px solid var(--border);
    margin-bottom: 14px;
    display: flex;
    align-items: center;
    gap: 12px;
}
.sidebar-brand .brand-icon {
    width: 38px; height: 38px;
    border-radius: 10px;
    background: linear-gradient(135deg, var(--accent) 0%, var(--accent-soft) 100%);
    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff !important;
    font-family: 'Playfair Display', serif;
    font-weight: 700;
    font-size: 18px;
    box-shadow: var(--shadow-md);
}
.sidebar-brand .brand-text .brand-sub-label {
    font-family: 'Inter', sans-serif;
    font-weight: 500;
    font-size: 10px;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--text-dim) !important;
    line-height: 1;
}
.sidebar-brand .brand-text .brand-main {
    font-family: 'Playfair Display', serif;
    font-weight: 700;
    font-size: 19px;
    color: var(--text-primary) !important;
    letter-spacing: -0.01em;
    line-height: 1.15;
    margin-top: 3px;
}

.sidebar-section {
    font-family: 'Inter', sans-serif;
    font-weight: 600;
    font-size: 10px;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--text-dim) !important;
    margin: 18px 0 8px 0;
    padding-bottom: 6px;
    border-bottom: 1px solid var(--border);
}

.dash-header {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    padding: 26px 0 20px 0;
    border-bottom: 1px solid var(--border);
    margin-bottom: 22px;
}
.dash-title {
    font-family: 'Playfair Display', serif;
    font-weight: 700;
    font-size: 32px;
    letter-spacing: -0.02em;
    color: var(--text-primary);
    line-height: 1.1;
}
.dash-title .accent { color: var(--accent); font-style: italic; }
.dash-subtitle {
    font-family: 'Inter', sans-serif;
    font-size: 12px;
    font-weight: 500;
    color: var(--text-dim);
    letter-spacing: 0.04em;
    margin-top: 8px;
    text-transform: uppercase;
}
.dash-badge {
    font-family: 'Inter', sans-serif;
    font-weight: 600;
    font-size: 10px;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    padding: 7px 14px;
    border: 1px solid var(--accent);
    color: var(--accent);
    border-radius: 20px;
    background: var(--accent-light);
}

.kpi-row { display: flex; gap: 14px; margin-bottom: 26px; }
.kpi-card {
    flex: 1;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 18px 20px;
    position: relative;
    overflow: hidden;
    box-shadow: var(--shadow-sm);
    transition: transform 0.18s ease, box-shadow 0.18s ease;
}
.kpi-card:hover {
    transform: translateY(-2px);
    box-shadow: var(--shadow-md);
}
.kpi-card .kpi-accent {
    position: absolute;
    left: 0; top: 0; bottom: 0;
    width: 3px;
    background: var(--accent);
    border-radius: 14px 0 0 14px;
}
.kpi-card.warm   .kpi-accent { background: var(--hl-warm); }
.kpi-card.teal   .kpi-accent { background: var(--hl-teal); }
.kpi-card.gold   .kpi-accent { background: var(--hl-gold); }

.kpi-label {
    font-family: 'Inter', sans-serif;
    font-weight: 500;
    font-size: 11px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--text-dim);
    margin-bottom: 10px;
}
.kpi-value {
    font-family: 'Playfair Display', serif;
    font-weight: 600;
    font-size: 30px;
    color: var(--text-primary);
    line-height: 1.05;
    letter-spacing: -0.01em;
}
.kpi-sub {
    font-family: 'Inter', sans-serif;
    font-size: 11px;
    font-weight: 500;
    color: var(--text-secondary);
    margin-top: 6px;
}

.section-title {
    font-family: 'Playfair Display', serif;
    font-weight: 600;
    font-size: 18px;
    letter-spacing: -0.01em;
    color: var(--text-primary);
    margin: 30px 0 14px 0;
    display: flex;
    align-items: center;
    gap: 12px;
}
.section-title::after {
    content: '';
    flex: 1;
    height: 1px;
    background: linear-gradient(90deg, var(--border) 0%, transparent 100%);
}
.section-dot {
    width: 7px; height: 7px;
    background: var(--accent);
    border-radius: 50%;
    flex-shrink: 0;
}

div[data-baseweb="select"] > div,
div[data-baseweb="select"] div[role="combobox"] {
    background-color: var(--bg-card) !important;
    border-color: var(--border-bright) !important;
    border-radius: 10px !important;
    color: var(--text-primary) !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    transition: all 0.15s ease !important;
}
div[data-baseweb="select"] > div:hover {
    border-color: var(--accent-soft) !important;
}
div[data-baseweb="select"] svg { fill: var(--text-secondary) !important; }

.stSelectbox label,
.stSlider label,
.stRadio label {
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;
    font-size: 11px !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
    color: var(--text-dim) !important;
}

button[data-testid="baseButton-secondary"],
button[data-testid="baseButton-primary"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--border-bright) !important;
    color: var(--text-primary) !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;
    font-size: 12px !important;
    letter-spacing: 0.04em !important;
    border-radius: 10px !important;
    padding: 8px 18px !important;
    transition: all 0.15s ease !important;
    box-shadow: var(--shadow-sm) !important;
}
button[data-testid="baseButton-secondary"]:hover,
button[data-testid="baseButton-primary"]:hover {
    border-color: var(--accent) !important;
    color: var(--accent) !important;
    background: var(--accent-light) !important;
    transform: translateY(-1px);
    box-shadow: var(--shadow-md) !important;
}

[data-testid="stDataFrame"] {
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
    background: var(--bg-card) !important;
    overflow: hidden;
    box-shadow: var(--shadow-sm);
}
[data-testid="stDataFrame"] th {
    background: var(--bg-soft) !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;
    font-size: 11px !important;
    letter-spacing: 0.06em !important;
    text-transform: uppercase !important;
    color: var(--text-dim) !important;
}
[data-testid="stDataFrame"] td {
    font-family: 'Inter', sans-serif !important;
    font-size: 13px !important;
    font-weight: 400 !important;
    color: var(--text-primary) !important;
}

[data-testid="stAlert"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
    color: var(--text-secondary) !important;
    font-family: 'Inter', sans-serif !important;
    box-shadow: var(--shadow-sm);
}

#MainMenu, footer{ visibility: hidden; }
[data-testid="stToolbar"] { display: none; }

hr { border-color: var(--border) !important; }

[data-testid="stPlotlyChart"] {
    border: 1px solid var(--border);
    border-radius: 14px;
    background: var(--bg-card);
    padding: 8px;
    box-shadow: var(--shadow-sm);
    overflow: hidden;
}

[data-testid="stRadio"] > div {
    flex-direction: row !important;
    gap: 8px !important;
}
[data-testid="stRadio"] label {
    border: 1px solid var(--border-bright) !important;
    padding: 7px 16px !important;
    cursor: pointer;
    font-weight: 500 !important;
    font-size: 12px !important;
    letter-spacing: 0.02em !important;
    border-radius: 20px !important;
    background: var(--bg-card) !important;
    color: var(--text-secondary) !important;
    transition: all 0.15s ease;
}
[data-testid="stRadio"] label:has(input:checked) {
    border-color: var(--accent) !important;
    color: var(--accent) !important;
    background: var(--accent-light) !important;
    font-weight: 600 !important;
}
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────
# PATHS
# ──────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent

world_geojson_path       = BASE_DIR / "data" / "raw"     / "boundaries" / "world_countries.geojson"
conflict_country_path    = BASE_DIR / "data" / "cleaned" / "global"     / "conflict_country_monthlybytype.csv"
conflict_admin_path      = BASE_DIR / "data" / "cleaned" / "global"     / "conflict_standardized_monthlybytype.csv"
priority_country_path    = BASE_DIR / "data" / "cleaned" / "global"     / "global_priority_country_with_displacement_monthly.csv"
priority_admin1_path     = BASE_DIR / "data" / "cleaned" / "global"     / "global_priority_admin1_with_displacement_monthly.csv"
displacement_dest_path   = BASE_DIR / "data" / "cleaned" / "global"     / "displacement_admin1_destination_monthly_2024_2026.csv"
displacement_origin_path = BASE_DIR / "data" / "cleaned" / "global"     / "displacement_admin1_origin_monthly_2024_2026.csv"
country_boundaries_dir   = BASE_DIR / "data" / "cleaned" / "boundaries" / "countries"
lbn_admin2_fallback_path = BASE_DIR / "data" / "raw"     / "boundaries" / "geoBoundaries-LBN-ADM2.geojson"

# ──────────────────────────────────────────────────
# CONSTANTS
# ──────────────────────────────────────────────────
MIN_YEAR = 2024
MAX_YEAR = 2026

MONTH_MAP = {
    "January":1,"February":2,"March":3,"April":4,
    "May":5,"June":6,"July":7,"August":8,
    "September":9,"October":10,"November":11,"December":12,
}

DISTRICT_TO_ADMIN1_GEO = {
    "Akkar":"Akkar","Aley":"Mount Lebanon","Baabda":"Mount Lebanon",
    "Baalbek":"Baalbek-Hermel","Batroun":"North","Bcharre":"North",
    "Beirut":"Beirut","Bent Jbail":"Al Nabatieh","Chouf":"Mount Lebanon",
    "El Metn":"Mount Lebanon","Hasbaya":"Al Nabatieh","Hermel":"Baalbek-Hermel",
    "Jbail":"Mount Lebanon","Jezzine":"South","Kesrouan":"Mount Lebanon",
    "Koura":"North","Marjaayoun":"Al Nabatieh","Minieh-Dinnieh":"North",
    "Nabatiye":"Al Nabatieh","Rachaya":"Bekaa","Saida":"South",
    "Sour":"South","Tripoli":"North","West Bekaa":"Bekaa",
    "Zahle":"Bekaa","Zgharta":"North",
}

COUNTRY_NAME_ALIASES = {
    "Russia":["Russia","Russian Federation"],
    "United States of America":["United States of America","United States","USA"],
    "Syria":["Syria","Syrian Arab Republic"],
    "Iran":["Iran","Iran (Islamic Republic of)","Islamic Republic of Iran"],
    "Venezuela":["Venezuela","Venezuela, Bolivarian Republic of"],
    "Bolivia":["Bolivia","Bolivia (Plurinational State of)"],
    "Tanzania":["Tanzania","United Republic of Tanzania"],
    "Moldova":["Moldova","Republic of Moldova"],
    "Laos":["Laos","Lao People's Democratic Republic"],
    "Czechia":["Czechia","Czech Republic"],
    "North Macedonia":["North Macedonia","Macedonia"],
    "Myanmar":["Myanmar","Burma"],
    "Palestine":["Palestine","State of Palestine"],
    "Democratic Republic of the Congo":[
        "Democratic Republic of the Congo",
        "Democratic Republic Of Congo","Congo, Dem. Rep.","DR Congo"],
    "Republic of the Congo":["Republic of the Congo","Congo","Congo, Rep."],
}

COUNTRY_CANONICAL_ALIASES = {
    "russian federation":"russia",
    "syrian arab republic":"syria",
    "iran (islamic republic of)":"iran",
    "islamic republic of iran":"iran",
    "venezuela, bolivarian republic of":"venezuela",
    "bolivia (plurinational state of)":"bolivia",
    "united republic of tanzania":"tanzania",
    "republic of moldova":"moldova",
    "lao people's democratic republic":"laos",
    "czech republic":"czechia",
    "state of palestine":"palestine",
    "democratic republic of congo":"democratic republic of the congo",
    "congo, dem. rep.":"democratic republic of the congo",
    "dr congo":"democratic republic of the congo",
    "congo, rep.":"republic of the congo",
}

NON_ADMIN_LOCATIONS = {
    "sea of azov","azov sea","eastern black sea","black sea",
    "mediterranean sea","red sea","persian gulf","cape fiolent",
    "international waters","unknown","not available","",
}

GENERIC_SUFFIX_PATTERNS = [
    r"\s+governorate$",r"\s+governorates$",r"\s+governate$",
    r"\s+province$",r"\s+provinces$",r"\s+prefecture$",r"\s+prefectures$",
    r"\s+department$",r"\s+departments$",r"\s+region$",r"\s+regions$",
    r"\s+district$",r"\s+districts$",r"\s+county$",r"\s+counties$",
    r"\s+municipality$",r"\s+municipalities$",r"\s+state$",r"\s+states$",
    r"\s+oblast$",
]

KEEP_SUFFIX_EXACT = {"moscow oblast","kyiv oblast","odessa oblast"}

# ──────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────
def normalize_text(value):
    if pd.isna(value):
        return None
    value = str(value).strip().lower()
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.replace("–","-").replace("—","-").replace("_"," ")
    value = value.replace("/"," ").replace(","," ").replace("’","'")
    value = re.sub(r"\s+"," ",value).strip()
    return value

def strip_generic_suffixes(value):
    if value is None:
        return None
    if value in KEEP_SUFFIX_EXACT:
        return value
    out = value
    for pattern in GENERIC_SUFFIX_PATTERNS:
        out = re.sub(pattern,"",out).strip()
    return re.sub(r"\s+"," ",out).strip()

def canonical_country_norm(name):
    n = normalize_text(name)
    if n is None:
        return None
    return COUNTRY_CANONICAL_ALIASES.get(n, n)

def standardize_admin_name(value, country=None):
    value   = normalize_text(value)
    country = canonical_country_norm(country)
    if value is None or value in NON_ADMIN_LOCATIONS:
        return None

    pre = {
        "kyiv city":"kyiv","odesa":"odessa","oddesa":"odessa",
        "republic of adygea":"adygea","republic of bashkortostan":"bashkortostan",
        "republic of chuvash":"chuvashia","republic of mordovia":"mordovia",
        "republic of tatarstan":"tatarstan","republic of tuva":"tuva",
        "republic of karelia":"karelia","sakha republic":"sakha",
        "komi republic":"komi","autonomous republic of crimea":"autonomous republic of crimea",
    }
    value = pre.get(value, value)
    value = strip_generic_suffixes(value)

    post = {
        "crimea":"autonomous republic of crimea","kyiv city":"kyiv",
        "odesa":"odessa","oddesa":"odessa","nabatyeh":"al nabatieh",
        "nabatiyeh":"al nabatieh","nabatiye":"al nabatieh",
        "republic of mordovia":"mordovia","republic of karelia":"karelia",
    }
    value = post.get(value, value)

    country_specific = {
        "lebanon":{
            "aakkar":"akkar","akkar":"akkar","beyrouth":"beirut","beirut":"beirut",
            "beqaa":"bekaa","bekaa":"bekaa","baalbek hermel":"baalbek-hermel",
            "baalbek-hermel":"baalbek-hermel","mont-liban":"mount lebanon",
            "mont liban":"mount lebanon","mount lebanon":"mount lebanon",
            "keserwan-jbeil":"mount lebanon","keserwan jbeil":"mount lebanon",
            "liban-nord":"north","liban nord":"north","north":"north",
            "liban-sud":"south","liban sud":"south","south":"south",
            "nabatiye":"al nabatieh","nabatiyeh":"al nabatieh",
            "nabatyeh":"al nabatieh","nabatye":"al nabatieh","al nabatieh":"al nabatieh",
        },
        "ukraine":{
            "crimea":"autonomous republic of crimea",
            "autonomous republic of crimea":"autonomous republic of crimea",
            "kyiv city":"kyiv","kyiv":"kyiv","odesa":"odessa","odessa":"odessa","sevastopol":"sevastopol",
        },
        "russia":{
            "republic of adygea":"adygea","adygea":"adygea",
            "republic of bashkortostan":"bashkortostan","bashkortostan":"bashkortostan",
            "republic of chuvash":"chuvashia","chuvashia":"chuvashia",
            "republic of mordovia":"mordovia","mordovia":"mordovia",
            "republic of tatarstan":"tatarstan","tatarstan":"tatarstan",
            "republic of tuva":"tuva","tuva":"tuva",
            "republic of karelia":"karelia","karelia":"karelia",
            "komi republic":"komi","komi":"komi","sakha republic":"sakha","sakha":"sakha",
            "altai":"altai krai","altai republic":"altai republic","moscow oblast":"moscow oblast",
        },
    }
    if country in country_specific:
        value = country_specific[country].get(value, value)
    return value

def default_latest_period(df):
    temp = df[["year","month_num","month"]].drop_duplicates().sort_values(["year","month_num"])
    last = temp.iloc[-1]
    return int(last["year"]), str(last["month"])

def default_latest_period_with_year_bounds(df, min_year=MIN_YEAR, max_year=MAX_YEAR):
    temp = df[["year","month_num","month"]].drop_duplicates().sort_values(["year","month_num"])
    temp = temp[(temp["year"]>=min_year)&(temp["year"]<=max_year)].copy()
    if temp.empty:
        return default_latest_period(df)
    last = temp.iloc[-1]
    return int(last["year"]), str(last["month"])

def ensure_required_files():
    required = [
        world_geojson_path, conflict_country_path, conflict_admin_path,
        priority_country_path, priority_admin1_path
    ]
    missing = [str(p) for p in required if not p.exists()]
    if missing:
        st.error("Missing files:\n" + "\n".join(missing))
        st.stop()

def filter_event_type(df, selected):
    if selected == "All":
        return df.copy()
    return df[df["event_type"] == selected].copy()

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

def detect_name_column(gdf):
    for col in ["shapeName","shapeName_en","admin1Name","ADM1_EN","adm1_en",
                "NAME_1","name_1","province","region","state","admin1","name"]:
        if col in gdf.columns:
            return col
    return None

def extract_selected_country_info(event):
    if event is None:
        return None, None
    try:
        if isinstance(event, dict):
            points = event.get("selection", {}).get("points", [])
        else:
            sel = getattr(event, "selection", {})
            points = sel.get("points", []) if isinstance(sel, dict) else []
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

def resolve_clicked_country(clicked_id=None, clicked_name=None, fallback_name=None):
    clicked_id = str(clicked_id).strip().upper() if clicked_id else None
    iso3 = None
    world_match = world.iloc[0:0].copy()

    if clicked_id:
        if len(clicked_id) == 3 and clicked_id.isalpha():
            iso3 = clicked_id
            world_match = world[world["iso_a3"] == iso3]
        else:
            iso_n3 = clicked_id.zfill(3) if clicked_id.isdigit() else clicked_id
            world_match = world[(world["iso_n3"] == iso_n3) | (world["iso_a3"] == clicked_id)]
            if not world_match.empty:
                iso3 = str(world_match["iso_a3"].iloc[0]).strip().upper()

    if world_match.empty:
        for name in [clicked_name, fallback_name]:
            cnorm = canonical_country_norm(name)
            if cnorm is None:
                continue
            world_match = world[world["country_norm"] == cnorm]
            if not world_match.empty:
                iso3 = str(world_match["iso_a3"].iloc[0]).strip().upper()
                break

    if iso3 is None:
        return None, None

    if world_match.empty:
        world_match = world[world["iso_a3"] == iso3]

    country_norm = world_match["country_norm"].iloc[0] if not world_match.empty else None
    if country_norm is None:
        country_norm = canonical_country_norm(clicked_name) or canonical_country_norm(fallback_name)

    resolved_name = None
    for df_name in ["admin_conflict", "admin1_priority", "country_conflict", "country_priority"]:
        df = globals().get(df_name)
        if df is None or "country_norm" not in df.columns or "country" not in df.columns or country_norm is None:
            continue
        matches = df[df["country_norm"] == country_norm]
        if not matches.empty:
            resolved_name = str(matches["country"].dropna().astype(str).str.strip().iloc[0])
            break

    if resolved_name is None and clicked_name:
        resolved_name = str(clicked_name).strip()
    if resolved_name is None and fallback_name:
        resolved_name = str(fallback_name).strip()
    if resolved_name is None and not world_match.empty:
        resolved_name = str(world_match["country_name_geo"].iloc[0]).strip()

    return iso3, resolved_name

def get_country_admin_rows(admin_df, selected_country_name):
    country_norm = canonical_country_norm(selected_country_name)
    out = admin_df[admin_df["country_norm"] == country_norm].copy()
    if not out.empty:
        return out
    aliases = COUNTRY_NAME_ALIASES.get(selected_country_name, [selected_country_name])
    alias_norms = [canonical_country_norm(x) for x in aliases]
    return admin_df[admin_df["country_norm"].isin(alias_norms)].copy()

def metric_label(metric):
    return {
        "events":"Events","fatalities":"Fatalities",
        "population_exposure":"Pop. Exposure","displaced":"Displaced",
        "country_priority_score":"Priority Score",
        "priority_score_country":"Priority Score",
        "priority_score_global":"Priority Score (Global)",
    }.get(metric, metric)

def fmt_big(n):
    try:
        n = float(n)
    except Exception:
        return "—"
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}K"
    return f"{n:,.0f}"

def render_top10_grid(df, name_col, val_col, fmt_fn=None):
    items = df[[name_col, val_col]].reset_index(drop=True)
    if items.empty:
        return
    max_val = float(items[val_col].max()) if not items.empty else 1.0
    if max_val <= 0:
        max_val = 1.0
    r1,g1,b1 = 0x1b,0x22,0x30
    r2,g2,b2 = 0xb0,0xb9,0xc7
    n = len(items)
    default_fmt = fmt_fn or (lambda v: f"{v:.3f}" if max_val < 10 else fmt_big(v))
    cards = []
    for i, row in items.iterrows():
        rank = i + 1
        t = (rank - 1) / max(n - 1, 1)
        rc = int(r1+(r2-r1)*t); gc = int(g1+(g2-g1)*t); bc = int(b1+(b2-b1)*t)
        rank_color = f"#{rc:02x}{gc:02x}{bc:02x}"
        name = str(row[name_col])
        val = float(row[val_col]) if pd.notna(row[val_col]) else 0.0
        pct = val / max_val * 100
        val_str = default_fmt(val)
        cards.append(f'''<div style="background:#fff;border:1px solid #e4e8ef;border-radius:12px;padding:14px 16px;box-shadow:0 1px 2px rgba(20,30,50,.04);">
  <div style="display:flex;align-items:flex-start;gap:10px;margin-bottom:8px;">
    <span style="font-family:'Playfair Display',serif;font-size:22px;font-weight:700;color:{rank_color};line-height:1;flex-shrink:0;min-width:26px;text-align:right;">{rank}</span>
    <div style="flex:1;min-width:0;">
      <div style="font-family:'Inter',sans-serif;font-size:13px;font-weight:600;color:#1b2230;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="{name}">{name}</div>
      <div style="font-family:'JetBrains Mono',monospace;font-size:12px;font-weight:500;color:#5a6577;margin-top:2px;">{val_str}</div>
    </div>
  </div>
  <div style="height:3px;background:#eef1f6;border-radius:2px;overflow:hidden;">
    <div style="height:100%;width:{pct:.1f}%;background:linear-gradient(90deg,#2c4a6e,#5a7aa0);border-radius:2px;"></div>
  </div>
</div>''')
    st.markdown(
        '<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:4px;">'
        + ''.join(cards) + '</div>',
        unsafe_allow_html=True,
    )

def build_mapbox_center(gdf, default_lat=20, default_lon=10):
    if gdf is None or gdf.empty or "geometry" not in gdf.columns:
        return {"lat": default_lat, "lon": default_lon}
    try:
        rp = gdf.geometry.representative_point()
        return {"lat": float(rp.y.mean()), "lon": float(rp.x.mean())}
    except Exception:
        return {"lat": default_lat, "lon": default_lon}

LIGHT_LAYOUT = dict(
    paper_bgcolor="#ffffff",
    plot_bgcolor="#ffffff",
    font=dict(family="Inter", color="#5a6577", size=11),
    title=dict(font=dict(family="Playfair Display", size=16, color="#1b2230"), x=0.02, xanchor="left", y=0.97),
    margin=dict(l=0, r=0, t=50, b=0),
)

SCALE_BLUE  = [[0,"#f4f7fb"],[0.25,"#d2dceb"],[0.5,"#8fa7c9"],[0.75,"#4f6c95"],[1,"#2c4a6e"]]
SCALE_WARM  = [[0,"#fbf6f0"],[0.25,"#f2e0cc"],[0.5,"#dcb48a"],[0.75,"#b8703a"],[1,"#7a4418"]]
SCALE_TEAL  = [[0,"#f1f7f5"],[0.25,"#d0e3dd"],[0.5,"#95bcb0"],[0.75,"#5a8a82"],[1,"#2e5652"]]
SCALE_GOLD  = [[0,"#faf5ea"],[0.25,"#ecd9ad"],[0.5,"#c8a26a"],[0.75,"#a8864a"],[1,"#6e5727"]]

# ──────────────────────────────────────────────────
# DATA LOADERS
# ──────────────────────────────────────────────────
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
    if "population_exposure" in df.columns:
        df["population_exposure"] = pd.to_numeric(df["population_exposure"], errors="coerce").fillna(0)
    else:
        df["population_exposure"] = 0
    if "month_num" not in df.columns:
        df["month_num"] = df["month"].map(MONTH_MAP)
    else:
        df["month_num"] = pd.to_numeric(df["month_num"], errors="coerce")
    df = df[df["year"].notna() & df["month"].notna() & df["month_num"].notna() &
            df["country"].notna() & df["event_type"].notna()].copy()
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
    if "population_exposure" not in df.columns:
        df["population_exposure"] = 0
    else:
        df["population_exposure"] = df["population_exposure"].fillna(0)
    if "month_num" not in df.columns:
        df["month_num"] = df["month"].map(MONTH_MAP)
    df = df[df["year"].notna() & df["month"].notna() & df["month_num"].notna() &
            df["country"].notna() & df["event_type"].notna() & df["admin1"].notna()].copy()
    df["year"] = df["year"].astype(int)
    df["month_num"] = df["month_num"].astype(int)
    df["country_norm"] = df["country"].apply(canonical_country_norm)
    df["admin1_norm"] = df.apply(lambda row: standardize_admin_name(row["admin1"], row["country"]), axis=1)
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
    df = df[df["year"].notna() & df["month"].notna() & df["month_num"].notna() & df["country"].notna()].copy()
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
        "displaced_in", "displaced_from", "centroid_latitude", "centroid_longitude",
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
    df["admin1_norm"] = df.apply(lambda row: standardize_admin_name(row["admin1_norm"], row["country"]), axis=1)
    df["month"] = df["month"].astype(str).str.strip()
    df = df[df["year"].notna() & df["month"].notna() & df["month_num"].notna() &
            df["country"].notna() & df["admin1_norm"].notna()].copy()
    df["year"] = df["year"].astype(int)
    df["month_num"] = df["month_num"].astype(int)
    df = df[(df["year"] >= MIN_YEAR) & (df["year"] <= MAX_YEAR)].copy()
    return df

@st.cache_data(show_spinner=False)
def load_displacement_dest():
    if not displacement_dest_path.exists():
        return pd.DataFrame(columns=["country","country_name","year","month_num","month","admin1_norm","displaced_in"])
    df = pd.read_csv(displacement_dest_path)
    df["country"] = df["country"].apply(canonical_country_norm)
    df["admin1_norm"] = df.apply(lambda r: standardize_admin_name(r["admin1_norm"], r["country"]), axis=1)
    df["month"] = df["month"].astype(str).str.strip()
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df["month_num"] = pd.to_numeric(df["month_num"], errors="coerce")
    df["displaced_in"] = pd.to_numeric(df["displaced_in"], errors="coerce").fillna(0)
    df = df[df["year"].notna() & df["month_num"].notna() & df["admin1_norm"].notna()].copy()
    df["year"] = df["year"].astype(int)
    df["month_num"] = df["month_num"].astype(int)
    df = df[(df["year"] >= MIN_YEAR) & (df["year"] <= MAX_YEAR)].copy()
    return df

@st.cache_data(show_spinner=False)
def load_displacement_origin():
    if not displacement_origin_path.exists():
        return pd.DataFrame(columns=["country","country_name","year","month_num","month","admin1_norm","displaced_from"])
    df = pd.read_csv(displacement_origin_path)
    df["country"] = df["country"].apply(canonical_country_norm)
    df["admin1_norm"] = df.apply(lambda r: standardize_admin_name(r["admin1_norm"], r["country"]), axis=1)
    df["month"] = df["month"].astype(str).str.strip()
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df["month_num"] = pd.to_numeric(df["month_num"], errors="coerce")
    df["displaced_from"] = pd.to_numeric(df["displaced_from"], errors="coerce").fillna(0)
    df = df[df["year"].notna() & df["month_num"].notna() & df["admin1_norm"].notna()].copy()
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
    iso_to_country = {"LBN": "Lebanon", "UKR": "Ukraine", "RUS": "Russia"}

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
        gdf["admin_name_norm"] = gdf["admin_name"].apply(lambda x: standardize_admin_name(x, country_name))
        gdf = gdf[gdf["admin_name_norm"].notna()].copy()
        gdf = gdf[["admin_name","admin_name_norm","geometry"]].copy()
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
        gdf["admin_name_norm"] = gdf["admin_name"].apply(lambda x: standardize_admin_name(x, "Lebanon"))
        gdf = gdf[gdf["admin_name_norm"].notna()].copy()
        gdf = gdf[["admin_name","admin_name_norm","geometry"]].copy()
        return gdf, "admin_name"

    return None, None

# ──────────────────────────────────────────────────
# LOAD DATA
# ──────────────────────────────────────────────────
ensure_required_files()

country_conflict    = load_country_conflict()
admin_conflict      = load_admin_conflict()
country_priority    = load_country_priority()
admin1_priority     = load_admin1_priority()
displacement_dest   = load_displacement_dest()
displacement_origin = load_displacement_origin()
world               = load_world()

# ──────────────────────────────────────────────────
# SESSION STATE
# ──────────────────────────────────────────────────
defaults = [
    ("view","world"),
    ("selected_iso3",None),
    ("selected_country_name",None),
    ("world_country","All"),
    ("world_mode","Conflict View"),
    ("world_event_type","All"),
    ("world_metric","events"),
    ("country_year",None),
    ("country_month",None),
    ("country_event_type","All"),
    ("country_metric","events"),
]
for key, default in defaults:
    if key not in st.session_state:
        st.session_state[key] = default

if "world_year" not in st.session_state or "world_month" not in st.session_state:
    y, m = default_latest_period_with_year_bounds(country_conflict)
    st.session_state["world_year"] = y
    st.session_state["world_month"] = m

# ──────────────────────────────────────────────────
# SIDEBAR BRAND
# ──────────────────────────────────────────────────
st.sidebar.markdown("""
<div class="sidebar-brand">

</div>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────
# WORLD VIEW
# ──────────────────────────────────────────────────
if st.session_state["view"] == "world":
    st.sidebar.markdown('<div class="sidebar-section">View Mode</div>', unsafe_allow_html=True)
    world_mode = st.sidebar.selectbox(
        "Dashboard Mode",
        ["Conflict View","Priority View"],
        index=0 if st.session_state["world_mode"] == "Conflict View" else 1,
        label_visibility="collapsed",
    )
    st.session_state["world_mode"] = world_mode

    source_df = country_conflict.copy() if world_mode == "Conflict View" else country_priority.copy()

    st.sidebar.markdown('<div class="sidebar-section">Scope</div>', unsafe_allow_html=True)
    country_options = ["All"] + sorted(source_df["country"].dropna().unique().tolist())
    selected_country = st.sidebar.selectbox(
        "Country",
        country_options,
        index=country_options.index(st.session_state["world_country"])
              if st.session_state["world_country"] in country_options else 0,
    )
    st.session_state["world_country"] = selected_country

    if selected_country != "All" and st.sidebar.button("← Back to World Map", key="world_reset_to_all"):
        st.session_state.update({
            "view": "world",
            "world_country": "All",
            "selected_iso3": None,
            "selected_country_name": None,
        })
        st.rerun()

    base_df = source_df.copy()
    if selected_country != "All":
        cnorm = canonical_country_norm(selected_country)
        base_df = base_df[base_df["country_norm"] == cnorm].copy()

    st.sidebar.markdown('<div class="sidebar-section">Period</div>', unsafe_allow_html=True)
    world_years = sorted([y for y in base_df["year"].dropna().unique() if MIN_YEAR <= y <= MAX_YEAR])
    if not world_years:
        st.warning("No years available.")
        st.stop()

    selected_year = st.sidebar.selectbox(
        "Year",
        world_years,
        index=world_years.index(st.session_state["world_year"])
              if st.session_state["world_year"] in world_years else len(world_years) - 1,
    )
    st.session_state["world_year"] = selected_year

    avail_months = (
        base_df[base_df["year"] == selected_year][["month_num","month"]]
        .drop_duplicates()
        .sort_values("month_num")
    )
    month_list = avail_months["month"].tolist()
    if not month_list:
        st.warning("No months available.")
        st.stop()

    selected_month = st.sidebar.selectbox(
        "Month",
        month_list,
        index=month_list.index(st.session_state["world_month"])
              if st.session_state["world_month"] in month_list else len(month_list) - 1,
    )
    st.session_state["world_month"] = selected_month

    is_priority = world_mode == "Priority View"
    view_label  = "Priority Analysis" if is_priority else "Conflict Analysis"
    area_label  = selected_country if selected_country != "All" else "Global"

    st.markdown(f"""
    <div class="dash-header">
      <div>
        <div class="dash-title"><span class="accent">{area_label}</span> {view_label}</div>
        <div class="dash-subtitle">{selected_month} {selected_year} &nbsp;·&nbsp; Data Explorer</div>
      </div>
      <div class="dash-badge">{'Priority' if is_priority else 'Conflict'} View</div>
    </div>
    """, unsafe_allow_html=True)

    # ─────────────────────────────────────────────
    # CONFLICT VIEW
    # ─────────────────────────────────────────────
    if world_mode == "Conflict View":
        st.sidebar.markdown('<div class="sidebar-section">Filters</div>', unsafe_allow_html=True)
        avail_et = (
            base_df[(base_df["year"] == selected_year) &
                    (base_df["month"].str.lower() == selected_month.lower())]
            ["event_type"].dropna().drop_duplicates().sort_values().tolist()
        )
        avail_et = ["All"] + avail_et
        selected_et = st.sidebar.selectbox(
            "Event Type",
            avail_et,
            index=avail_et.index(st.session_state["world_event_type"])
                  if st.session_state["world_event_type"] in avail_et else 0,
        )
        st.session_state["world_event_type"] = selected_et

        metric = st.sidebar.selectbox(
            "Metric",
            ["events","fatalities"],
            index=0 if st.session_state["world_metric"] == "events" else 1,
        )
        st.session_state["world_metric"] = metric

        filtered = base_df[(base_df["year"] == selected_year) &
                           (base_df["month"].str.lower() == selected_month.lower())].copy()
        filtered = filter_event_type(filtered, selected_et)

        if filtered.empty:
            st.warning("No data for selected filters.")
            st.stop()

        country_period = (
            filtered.groupby(["iso_n3","country","country_norm"], as_index=False)
            .agg({"events":"sum","fatalities":"sum","population_exposure":"sum"})
        )
        merged_w = world.merge(country_period, how="left", on=["iso_n3","country_norm"])
        merged_w["events"] = merged_w["events"].fillna(0)
        merged_w["fatalities"] = merged_w["fatalities"].fillna(0)
        merged_w["population_exposure"] = merged_w["population_exposure"].fillna(0)
        merged_w["country"] = merged_w["country"].fillna(merged_w["country_name_geo"])

        total_ev = int(country_period["events"].sum())
        total_fat = int(country_period["fatalities"].sum())
        ctry_count = int((country_period[metric] > 0).sum())

        st.markdown(f"""
        <div class="kpi-row">
          <div class="kpi-card">
            <div class="kpi-accent"></div>
            <div class="kpi-label">Total Events</div>
            <div class="kpi-value">{total_ev:,}</div>
            <div class="kpi-sub">{selected_month} {selected_year}</div>
          </div>
          <div class="kpi-card warm">
            <div class="kpi-accent"></div>
            <div class="kpi-label">Total Fatalities</div>
            <div class="kpi-value">{total_fat:,}</div>
            <div class="kpi-sub">Reported deaths</div>
          </div>
          <div class="kpi-card teal">
            <div class="kpi-accent"></div>
            <div class="kpi-label">Countries with Data</div>
            <div class="kpi-value">{ctry_count}</div>
            <div class="kpi-sub">Active conflict zones</div>
          </div>
          <div class="kpi-card gold">
            <div class="kpi-accent"></div>
            <div class="kpi-label">Active Metric</div>
            <div class="kpi-value" style="font-size:22px;text-transform:capitalize">{metric}</div>
            <div class="kpi-sub">{selected_et}</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        cscale = SCALE_BLUE if metric == "events" else SCALE_WARM

        if selected_country == "All":
            fig = px.choropleth_mapbox(
                merged_w,
                geojson=json.loads(merged_w.to_json()),
                locations="iso_n3",
                featureidkey="properties.iso_n3",
                color=metric,
                color_continuous_scale=cscale,
                hover_name="country_name_geo",
                hover_data={
                    "country":True,"events":True,"fatalities":True,
                    "iso_n3":False,"iso_a3":False,
                },
                custom_data=["iso_a3","country_name_geo"],
                mapbox_style="carto-positron",
                zoom=0.8,
                center={"lat": 20, "lon": 10},
                opacity=0.85,
                title=f"{metric.capitalize()} — {selected_month} {selected_year}",
            )
            fig.update_layout(
                **LIGHT_LAYOUT,
                height=800,
                coloraxis_colorbar=dict(
                    title=metric.capitalize(),
                    tickfont=dict(family="Inter", size=10, color="#5a6577"),
                    title_font=dict(family="Inter", size=11, color="#1b2230"),
                )
            )
            event = st.plotly_chart(
                fig,
                use_container_width=True,
                on_select="rerun",
                selection_mode=("points",),
                key="world_conflict_all",
            )
            clicked_iso3, clicked_name = extract_selected_country_info(event)
            resolved_iso3, resolved_name = resolve_clicked_country(clicked_iso3, clicked_name)
            if resolved_iso3 and resolved_name:
                st.session_state.update({
                    "selected_iso3":resolved_iso3,
                    "selected_country_name":resolved_name,
                    "view":"country",
                    "country_year":None,
                    "country_month":None,
                })
                st.rerun()
        else:
            sgeo = merged_w[merged_w["country_norm"] == canonical_country_norm(selected_country)].copy()
            fig = px.choropleth_mapbox(
                sgeo,
                geojson=json.loads(sgeo.to_json()),
                locations="iso_n3",
                featureidkey="properties.iso_n3",
                color=metric,
                color_continuous_scale=cscale,
                hover_name="country_name_geo",
                hover_data={
                    "country":True,"events":True,"fatalities":True,
                    "iso_n3":False,"iso_a3":False,
                },
                custom_data=["iso_a3","country_name_geo"],
                mapbox_style="carto-positron",
                zoom=3.2,
                center=build_mapbox_center(sgeo),
                opacity=0.90,
                title=f"{selected_country} — {metric.capitalize()}",
            )
            fig.update_layout(
                **LIGHT_LAYOUT,
                height=800,
                coloraxis_colorbar=dict(
                    title=metric.capitalize(),
                    tickfont=dict(family="Inter", size=10, color="#5a6577"),
                    title_font=dict(family="Inter", size=11, color="#1b2230"),
                )
            )
            event = st.plotly_chart(
                fig,
                use_container_width=True,
                on_select="rerun",
                selection_mode=("points",),
                key="world_conflict_selected",
            )
            clicked_iso3, clicked_name = extract_selected_country_info(event)
            resolved_iso3, resolved_name = resolve_clicked_country(clicked_iso3, clicked_name, selected_country)
            if resolved_iso3 and resolved_name:
                st.session_state.update({
                    "selected_iso3":resolved_iso3,
                    "selected_country_name":resolved_name,
                    "view":"country",
                    "country_year":None,
                    "country_month":None,
                })
                st.rerun()

        st.markdown(
            f'<div class="section-title"><span class="section-dot"></span>Top 10 by {metric.capitalize()}</div>',
            unsafe_allow_html=True
        )
        top = country_period.sort_values(metric, ascending=False).head(10).reset_index(drop=True)
        render_top10_grid(top, "country", metric, fmt_fn=lambda v: f"{int(v):,}")

    # ─────────────────────────────────────────────
    # PRIORITY VIEW
    # ─────────────────────────────────────────────
    else:
        st.sidebar.markdown('<div class="sidebar-section">Metric</div>', unsafe_allow_html=True)
        metric = st.sidebar.selectbox(
            "Priority Metric",
            ["country_priority_score","events","fatalities","displaced","population_exposure"],
            index=0,
            label_visibility="collapsed",
        )

        filtered = base_df[(base_df["year"] == selected_year) &
                           (base_df["month"].str.lower() == selected_month.lower())].copy()
        if filtered.empty:
            st.warning("No priority data for selected filters.")
            st.stop()

        world_pri = (
            filtered.groupby("country_norm", as_index=False)
            .agg({
                "events":"sum","fatalities":"sum","population_exposure":"sum",
                "displaced":"sum","country_priority_score":"mean","country_priority_rank":"min"
            })
        )
        cname_lk = filtered.groupby("country_norm", as_index=False)["country"].first()
        world_pri = world_pri.merge(cname_lk, how="left", on="country_norm")

        merged_w = world.merge(world_pri, how="left", on="country_norm")
        for col in ["events","fatalities","population_exposure","displaced","country_priority_score"]:
            merged_w[col] = pd.to_numeric(merged_w[col], errors="coerce").fillna(0)
        merged_w["country"] = merged_w["country"].fillna(merged_w["country_name_geo"])

        total_ev = int(world_pri["events"].sum())
        total_fat = int(world_pri["fatalities"].sum())
        total_disp = float(world_pri["displaced"].sum())
        ctry_count = int((merged_w["country_priority_score"] > 0).sum())

        st.markdown(f"""
        <div class="kpi-row">
          <div class="kpi-card">
            <div class="kpi-accent"></div>
            <div class="kpi-label">Total Events</div>
            <div class="kpi-value">{total_ev:,}</div>
            <div class="kpi-sub">{selected_month} {selected_year}</div>
          </div>
          <div class="kpi-card warm">
            <div class="kpi-accent"></div>
            <div class="kpi-label">Total Fatalities</div>
            <div class="kpi-value">{total_fat:,}</div>
            <div class="kpi-sub">Reported deaths</div>
          </div>
          <div class="kpi-card teal">
            <div class="kpi-accent"></div>
            <div class="kpi-label">Total Displaced</div>
            <div class="kpi-value">{fmt_big(total_disp)}</div>
            <div class="kpi-sub">Displacement events</div>
          </div>
          <div class="kpi-card gold">
            <div class="kpi-accent"></div>
            <div class="kpi-label">Priority Countries</div>
            <div class="kpi-value">{ctry_count}</div>
            <div class="kpi-sub">With priority score</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        cscale = SCALE_BLUE if metric == "country_priority_score" else SCALE_WARM if metric == "fatalities" else SCALE_TEAL if metric == "displaced" else SCALE_GOLD if metric == "population_exposure" else SCALE_BLUE

        if selected_country == "All":
            fig = px.choropleth_mapbox(
                merged_w,
                geojson=json.loads(merged_w.to_json()),
                locations="iso_n3",
                featureidkey="properties.iso_n3",
                color=metric,
                color_continuous_scale=cscale,
                hover_name="country_name_geo",
                hover_data={
                    "country":True,"events":True,"fatalities":True,
                    "displaced":True,"population_exposure":True,
                    "country_priority_score":":.3f","iso_n3":False,"iso_a3":False
                },
                custom_data=["iso_a3","country_name_geo"],
                mapbox_style="carto-positron",
                zoom=0.8,
                center={"lat": 20, "lon": 10},
                opacity=0.85,
                title=f"{metric_label(metric)} — {selected_month} {selected_year}",
            )
            fig.update_layout(
                **LIGHT_LAYOUT,
                height=800,
                coloraxis_colorbar=dict(
                    title=metric_label(metric),
                    tickfont=dict(family="Inter", size=10, color="#5a6577"),
                    title_font=dict(family="Inter", size=11, color="#1b2230"),
                    len=0.6, thickness=10, outlinewidth=0,
                )
            )
            event = st.plotly_chart(
                fig,
                use_container_width=True,
                on_select="rerun",
                selection_mode=("points",),
                key="world_priority_all",
            )
            clicked_iso3, clicked_name = extract_selected_country_info(event)
            resolved_iso3, resolved_name = resolve_clicked_country(clicked_iso3, clicked_name)
            if resolved_iso3 and resolved_name:
                st.session_state.update({
                    "selected_iso3":resolved_iso3,
                    "selected_country_name":resolved_name,
                    "view":"country",
                    "country_year":None,
                    "country_month":None,
                })
                st.rerun()
        else:
            sgeo = merged_w[merged_w["country_norm"] == canonical_country_norm(selected_country)].copy()
            fig = px.choropleth_mapbox(
                sgeo,
                geojson=json.loads(sgeo.to_json()),
                locations="iso_n3",
                featureidkey="properties.iso_n3",
                color=metric,
                color_continuous_scale=cscale,
                hover_name="country_name_geo",
                hover_data={
                    "country":True,"events":True,"fatalities":True,
                    "displaced":True,"population_exposure":True,
                    "country_priority_score":":.3f","iso_n3":False,"iso_a3":False
                },
                custom_data=["iso_a3","country_name_geo"],
                mapbox_style="carto-positron",
                zoom=3.2,
                center=build_mapbox_center(sgeo),
                opacity=0.90,
                title=f"{selected_country} — {metric_label(metric)}",
            )
            fig.update_layout(
                **LIGHT_LAYOUT,
                height=800,
                coloraxis_colorbar=dict(
                    title=metric_label(metric),
                    tickfont=dict(family="Inter", size=10, color="#5a6577"),
                    title_font=dict(family="Inter", size=11, color="#1b2230"),
                )
            )
            event = st.plotly_chart(
                fig,
                use_container_width=True,
                on_select="rerun",
                selection_mode=("points",),
                key="world_priority_selected",
            )
            clicked_iso3, clicked_name = extract_selected_country_info(event)
            resolved_iso3, resolved_name = resolve_clicked_country(clicked_iso3, clicked_name, selected_country)
            if resolved_iso3 and resolved_name:
                st.session_state.update({
                    "selected_iso3":resolved_iso3,
                    "selected_country_name":resolved_name,
                    "view":"country",
                    "country_year":None,
                    "country_month":None,
                })
                st.rerun()

        st.markdown(
            f'<div class="section-title"><span class="section-dot"></span>Top 10 by {metric_label(metric)}</div>',
            unsafe_allow_html=True
        )
        top = world_pri.sort_values(metric, ascending=False).head(10).reset_index(drop=True)
        pfmt = (lambda v: f"{v:.3f}") if metric == "country_priority_score" else fmt_big
        render_top10_grid(top, "country", metric, fmt_fn=pfmt)

# ──────────────────────────────────────────────────
# COUNTRY VIEW
# ──────────────────────────────────────────────────
else:
    selected_iso3 = st.session_state["selected_iso3"]
    selected_country_name = st.session_state["selected_country_name"]

    if not selected_iso3 or not selected_country_name:
        st.session_state.update({
            "view": "world",
            "world_country": "All",
            "selected_iso3": None,
            "selected_country_name": None,
        })
        st.rerun()

    st.sidebar.markdown('<div class="sidebar-section">Navigation</div>', unsafe_allow_html=True)
    if st.sidebar.button("← Back to World Map"):
        st.session_state.update({
            "view": "world",
            "world_country": "All",
            "selected_iso3": None,
            "selected_country_name": None,
        })
        st.rerun()

    boundary_gdf, boundary_name_col = load_country_admin1_boundary(selected_iso3)

    if boundary_gdf is None or boundary_gdf.empty:
        st.markdown(f"""
        <div class="dash-header">
          <div>
            <div class="dash-title"><span class="accent">{selected_country_name}</span> Admin1 View</div>
          </div>
        </div>
        """, unsafe_allow_html=True)
        st.warning(
            f"No ADM1 boundary file for {selected_country_name} ({selected_iso3}).\n\n"
            f"Expected: data/cleaned/boundaries/countries/{selected_iso3}_adm1.geojson"
        )
        st.stop()

    country_conflict_rows = get_country_admin_rows(admin_conflict, selected_country_name)
    country_priority_rows = get_country_admin_rows(admin1_priority, selected_country_name)

    if country_conflict_rows.empty and country_priority_rows.empty:
        st.warning("No admin-level data found for this country.")
        st.stop()

    available_source = country_conflict_rows if not country_conflict_rows.empty else country_priority_rows
    avail_years = sorted([y for y in available_source["year"].dropna().unique() if MIN_YEAR <= y <= MAX_YEAR])

    if not avail_years:
        st.warning("No years available.")
        st.stop()

    if st.session_state["country_year"] is None or st.session_state["country_year"] not in avail_years:
        ly, lm = default_latest_period_with_year_bounds(available_source)
        st.session_state["country_year"] = ly
        st.session_state["country_month"] = lm

    st.sidebar.markdown('<div class="sidebar-section">Period</div>', unsafe_allow_html=True)
    selected_year = st.sidebar.selectbox(
        "Year",
        avail_years,
        index=avail_years.index(st.session_state["country_year"])
              if st.session_state["country_year"] in avail_years else len(avail_years)-1,
    )
    st.session_state["country_year"] = selected_year

    month_source = available_source[available_source["year"] == selected_year][["month_num","month"]].drop_duplicates().sort_values("month_num")
    month_list = month_source["month"].tolist()
    if not month_list:
        st.warning("No months available.")
        st.stop()

    selected_month = st.sidebar.selectbox(
        "Month",
        month_list,
        index=month_list.index(st.session_state["country_month"])
              if st.session_state["country_month"] in month_list else len(month_list)-1,
    )
    st.session_state["country_month"] = selected_month

    st.sidebar.markdown('<div class="sidebar-section">Country View</div>', unsafe_allow_html=True)
    country_mode = st.sidebar.radio("Mode", ["Conflict", "Priority"], horizontal=True)

    st.markdown(f"""
    <div class="dash-header">
      <div>
        <div class="dash-title"><span class="accent">{selected_country_name}</span> Admin1 Analysis</div>
        <div class="dash-subtitle">{selected_month} {selected_year} &nbsp;·&nbsp; {country_mode} View</div>
      </div>
      <div class="dash-badge">{selected_iso3}</div>
    </div>
    """, unsafe_allow_html=True)

    if country_mode == "Conflict":
        avail_event_types = (
            country_conflict_rows[
                (country_conflict_rows["year"] == selected_year) &
                (country_conflict_rows["month"].str.lower() == selected_month.lower())
            ]["event_type"].dropna().drop_duplicates().sort_values().tolist()
        )
        avail_event_types = ["All"] + avail_event_types

        selected_event_type = st.sidebar.selectbox(
            "Event Type",
            avail_event_types,
            index=avail_event_types.index(st.session_state["country_event_type"])
                  if st.session_state["country_event_type"] in avail_event_types else 0,
        )
        st.session_state["country_event_type"] = selected_event_type

        selected_metric = st.sidebar.selectbox(
            "Metric",
            ["events", "fatalities", "population_exposure"],
            index=["events", "fatalities", "population_exposure"].index(st.session_state["country_metric"])
                  if st.session_state["country_metric"] in ["events", "fatalities", "population_exposure"] else 0,
        )
        st.session_state["country_metric"] = selected_metric

        conflict_slice = country_conflict_rows[
            (country_conflict_rows["year"] == selected_year) &
            (country_conflict_rows["month"].str.lower() == selected_month.lower())
        ].copy()
        conflict_slice = filter_event_type(conflict_slice, selected_event_type)

        agg_dict = {"events":"sum", "fatalities":"sum"}
        if "population_exposure" in conflict_slice.columns:
            agg_dict["population_exposure"] = "sum"

        merged = boundary_gdf.merge(
            conflict_slice.groupby("admin1_norm", as_index=False).agg(agg_dict),
            how="left",
            left_on="admin_name_norm",
            right_on="admin1_norm",
        )

        for col in ["events", "fatalities", "population_exposure"]:
            if col not in merged.columns:
                merged[col] = 0
            merged[col] = pd.to_numeric(merged[col], errors="coerce").fillna(0)

        total_ev = int(merged["events"].sum())
        total_fat = int(merged["fatalities"].sum())
        total_exp = float(merged["population_exposure"].sum())

        st.markdown(f"""
        <div class="kpi-row">
          <div class="kpi-card">
            <div class="kpi-accent"></div>
            <div class="kpi-label">Total Events</div>
            <div class="kpi-value">{total_ev:,}</div>
            <div class="kpi-sub">{selected_month} {selected_year}</div>
          </div>
          <div class="kpi-card warm">
            <div class="kpi-accent"></div>
            <div class="kpi-label">Total Fatalities</div>
            <div class="kpi-value">{total_fat:,}</div>
            <div class="kpi-sub">Admin1 aggregation</div>
          </div>
          <div class="kpi-card teal">
            <div class="kpi-accent"></div>
            <div class="kpi-label">Population Exposure</div>
            <div class="kpi-value">{fmt_big(total_exp)}</div>
            <div class="kpi-sub">If available</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        cscale = SCALE_BLUE if selected_metric == "events" else SCALE_WARM if selected_metric == "fatalities" else SCALE_GOLD

        fig = px.choropleth_mapbox(
            merged,
            geojson=json.loads(merged.to_json()),
            locations="admin_name_norm",
            featureidkey="properties.admin_name_norm",
            color=selected_metric,
            color_continuous_scale=cscale,
            hover_name="admin_name",
            hover_data={
                "events":True,"fatalities":True,"population_exposure":True,
                "admin_name_norm":False,
            },
            mapbox_style="carto-positron",
            center=build_mapbox_center(merged),
            zoom=5.0,
            opacity=0.88,
            title=f"{selected_country_name} — {metric_label(selected_metric)} by Admin1",
        )
        fig.update_layout(
            **LIGHT_LAYOUT,
            height=800,
            coloraxis_colorbar=dict(
                title=metric_label(selected_metric),
                tickfont=dict(family="Inter", size=10, color="#5a6577"),
                title_font=dict(family="Inter", size=11, color="#1b2230"),
            )
        )
        st.plotly_chart(fig, use_container_width=True, key="country_conflict_map")

        st.markdown(
            f'<div class="section-title"><span class="section-dot"></span>Top Admin1 by {metric_label(selected_metric)}</div>',
            unsafe_allow_html=True
        )
        top_admin = merged.sort_values(selected_metric, ascending=False)[["admin_name", selected_metric]].head(10).reset_index(drop=True)
        render_top10_grid(top_admin, "admin_name", selected_metric, fmt_fn=fmt_big)

    else:
        selected_metric = st.sidebar.selectbox(
            "Metric",
            ["priority_score_country", "priority_score_global", "events", "fatalities", "displaced", "population_exposure"],
            index=0,
        )

        priority_slice = country_priority_rows[
            (country_priority_rows["year"] == selected_year) &
            (country_priority_rows["month"].str.lower() == selected_month.lower())
        ].copy()

        disp_in_slice = displacement_dest[
            (displacement_dest["country"] == canonical_country_norm(selected_country_name)) &
            (displacement_dest["year"] == selected_year) &
            (displacement_dest["month"].str.lower() == selected_month.lower())
        ].copy()

        disp_out_slice = displacement_origin[
            (displacement_origin["country"] == canonical_country_norm(selected_country_name)) &
            (displacement_origin["year"] == selected_year) &
            (displacement_origin["month"].str.lower() == selected_month.lower())
        ].copy()

        agg_dict = {"events":"sum", "fatalities":"sum"}
        if "displaced" in priority_slice.columns:
            agg_dict["displaced"] = "sum"
        if "population_exposure" in priority_slice.columns:
            agg_dict["population_exposure"] = "sum"
        if "priority_score_country" in priority_slice.columns:
            agg_dict["priority_score_country"] = "mean"
        if "priority_score_global" in priority_slice.columns:
            agg_dict["priority_score_global"] = "mean"
        if "displaced_in" in priority_slice.columns:
            agg_dict["displaced_in"] = "sum"
        if "displaced_from" in priority_slice.columns:
            agg_dict["displaced_from"] = "sum"

        merged = boundary_gdf.merge(
            priority_slice.groupby("admin1_norm", as_index=False).agg(agg_dict),
            how="left",
            left_on="admin_name_norm",
            right_on="admin1_norm",
        )

        if not disp_in_slice.empty:
            merged = merged.merge(
                disp_in_slice.groupby("admin1_norm", as_index=False)["displaced_in"].sum(),
                how="left",
                left_on="admin_name_norm",
                right_on="admin1_norm",
                suffixes=("", "_dest")
            )
        else:
            merged["displaced_in"] = merged.get("displaced_in", 0)

        if not disp_out_slice.empty:
            merged = merged.merge(
                disp_out_slice.groupby("admin1_norm", as_index=False)["displaced_from"].sum(),
                how="left",
                left_on="admin_name_norm",
                right_on="admin1_norm",
                suffixes=("", "_orig")
            )
        else:
            merged["displaced_from"] = merged.get("displaced_from", 0)

        for col in ["events","fatalities","displaced","population_exposure","priority_score_country",
                    "priority_score_global","displaced_in","displaced_from"]:
            if col not in merged.columns:
                merged[col] = 0
            merged[col] = pd.to_numeric(merged[col], errors="coerce").fillna(0)

        total_priority = float(merged["priority_score_country"].sum())
        total_disp = float(merged["displaced"].sum())
        total_ev = int(merged["events"].sum())

        st.markdown(f"""
        <div class="kpi-row">
          <div class="kpi-card gold">
            <div class="kpi-accent"></div>
            <div class="kpi-label">Priority Sum</div>
            <div class="kpi-value">{total_priority:.2f}</div>
            <div class="kpi-sub">Country-normalized</div>
          </div>
          <div class="kpi-card teal">
            <div class="kpi-accent"></div>
            <div class="kpi-label">Displaced</div>
            <div class="kpi-value">{fmt_big(total_disp)}</div>
            <div class="kpi-sub">Priority layer</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-accent"></div>
            <div class="kpi-label">Events</div>
            <div class="kpi-value">{total_ev:,}</div>
            <div class="kpi-sub">{selected_month} {selected_year}</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        if selected_metric in ["priority_score_country", "priority_score_global"]:
            cscale = SCALE_BLUE
            fmt_fn = lambda v: f"{v:.3f}"
        elif selected_metric == "fatalities":
            cscale = SCALE_WARM
            fmt_fn = fmt_big
        elif selected_metric == "population_exposure":
            cscale = SCALE_GOLD
            fmt_fn = fmt_big
        else:
            cscale = SCALE_TEAL
            fmt_fn = fmt_big

        fig = px.choropleth_mapbox(
            merged,
            geojson=json.loads(merged.to_json()),
            locations="admin_name_norm",
            featureidkey="properties.admin_name_norm",
            color=selected_metric,
            color_continuous_scale=cscale,
            hover_name="admin_name",
            hover_data={
                "events":True,"fatalities":True,"displaced":True,
                "population_exposure":True,"priority_score_country":":.3f",
                "priority_score_global":":.3f","displaced_in":True,
                "displaced_from":True,"admin_name_norm":False,
            },
            mapbox_style="carto-positron",
            center=build_mapbox_center(merged),
            zoom=5.0,
            opacity=0.88,
            title=f"{selected_country_name} — {metric_label(selected_metric)} by Admin1",
        )
        fig.update_layout(
            **LIGHT_LAYOUT,
            height=800,
            coloraxis_colorbar=dict(
                title=metric_label(selected_metric),
                tickfont=dict(family="Inter", size=10, color="#5a6577"),
                title_font=dict(family="Inter", size=11, color="#1b2230"),
            )
        )
        st.plotly_chart(fig, use_container_width=True, key="country_priority_map")

        st.markdown(
            f'<div class="section-title"><span class="section-dot"></span>Top Admin1 by {metric_label(selected_metric)}</div>',
            unsafe_allow_html=True
        )
        top_admin = merged.sort_values(selected_metric, ascending=False)[["admin_name", selected_metric]].head(10).reset_index(drop=True)
        render_top10_grid(top_admin, "admin_name", selected_metric, fmt_fn=fmt_fn)
