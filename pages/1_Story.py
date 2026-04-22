import os
os.environ["OGR_GEOJSON_MAX_OBJ_SIZE"] = "0"

import base64
import json
import math
import mimetypes
import re
import unicodedata
from html import escape
from pathlib import Path

import geopandas as gpd
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

import hierarchy_aggregation as hierarchy
from dashboard_compare_utils import (
    build_country_comparison_radar,
    prepare_radar_comparison_data,
)
from displacement_snapshot_utils import (
    CUMULATIVE_DISPLACEMENT_NOTE,
    filter_to_period,
    format_period_label,
    get_latest_displacement_snapshot,
    get_latest_period,
    get_peak_displacement,
)

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
div[data-baseweb="select"] [data-baseweb="tag"] {
    background: linear-gradient(135deg, #0d657d 0%, #11485b 100%) !important;
    border: none !important;
    border-radius: 999px !important;
    box-shadow: 0 6px 16px rgba(13, 101, 125, 0.22) !important;
}
div[data-baseweb="select"] [data-baseweb="tag"] span,
div[data-baseweb="select"] [data-baseweb="tag"] div,
div[data-baseweb="select"] [data-baseweb="tag"] svg {
    color: #ffffff !important;
    fill: #ffffff !important;
}

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
    gap: 6px !important;
    padding: 4px !important;
    border: none !important;
    border-radius: 0 !important;
    background: transparent !important;
    box-shadow: none !important;
}
[data-testid="stRadio"] label {
    border: none !important;
    padding: 9px 16px !important;
    cursor: pointer;
    font-weight: 500 !important;
    font-size: 12px !important;
    letter-spacing: 0.02em !important;
    border-radius: 9px !important;
    background: transparent !important;
    color: var(--text-secondary) !important;
    transition: all 0.15s ease;
}
[data-testid="stRadio"] label:hover {
    border: none !important;
    background: var(--bg-hover) !important;
    color: var(--text-primary) !important;
}
[data-testid="stRadio"] label:has(input:checked) {
    border: none !important;
    color: var(--text-primary) !important;
    background: var(--bg-soft) !important;
    font-weight: 600 !important;
    box-shadow: none !important;
}

[data-testid="stTabs"] [data-baseweb="tab-list"] {
    gap: 8px !important;
    border-bottom: none !important;
    padding: 0 4px !important;
}
[data-testid="stTabs"] [data-baseweb="tab-border"] {
    display: none !important;
}
[data-testid="stTabs"] button[role="tab"] {
    height: auto !important;
    min-height: 42px !important;
    padding: 10px 16px !important;
    border: 1px solid var(--border-bright) !important;
    border-radius: 12px 12px 0 0 !important;
    background: var(--bg-card) !important;
    color: var(--text-secondary) !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 12px !important;
    font-weight: 600 !important;
    letter-spacing: 0.04em !important;
    transition: all 0.15s ease !important;
    box-shadow: var(--shadow-sm) !important;
}
[data-testid="stTabs"] button[role="tab"]:hover {
    border-color: var(--accent-soft) !important;
    color: var(--accent-ink) !important;
    background: rgba(44, 74, 110, 0.05) !important;
}
[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
    border-color: var(--accent) !important;
    background: var(--accent) !important;
    color: #ffffff !important;
    box-shadow: var(--shadow-md) !important;
}
[data-testid="stTabs"] [role="tabpanel"],
[data-testid="stTabs"] [data-baseweb="tab-panel"] {
    border: 1px solid var(--border) !important;
    border-radius: 0 14px 14px 14px !important;
    background: var(--bg-card) !important;
    box-shadow: var(--shadow-sm) !important;
    padding: 18px 18px 10px 18px !important;
    margin-top: -1px !important;
}
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────
# PATHS
# ──────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent

world_geojson_path       = BASE_DIR / "data" / "raw"     / "boundaries" / "world_countries.geojson"
conflict_country_path    = BASE_DIR / "data" / "cleaned" / "global"     / "conflict_country_monthlybytype.csv"
conflict_admin_path      = BASE_DIR / "data" / "cleaned" / "global"     / "admin1_monthlybytype_with_centroids.csv"
priority_country_path    = BASE_DIR / "data" / "cleaned" / "global"     / "global_priority_country_with_displacement_monthly.csv"
priority_admin1_path     = BASE_DIR / "data" / "cleaned" / "global"     / "global_priority_admin1_with_displacement_monthly.csv"
displacement_dest_path   = BASE_DIR / "data" / "cleaned" / "global"     / "displacement_admin1_destination_monthly_2024_2026.csv"
displacement_origin_path = BASE_DIR / "data" / "cleaned" / "global"     / "displacement_admin1_origin_monthly_2024_2026.csv"
country_boundaries_dir   = BASE_DIR / "data" / "cleaned" / "boundaries" / "countries"
lbn_admin2_fallback_path = BASE_DIR / "data" / "raw"     / "boundaries" / "geoBoundaries-LBN-ADM2.geojson"
lbn_admin2_clean_path    = BASE_DIR / "data" / "cleaned" / "boundaries" / "lbn_admin2.geojson"
lbn_admin2_priority_path = BASE_DIR / "data" / "cleaned" / "lebanon"    / "lebanon_priority_admin2_enhanced.csv"
lbn_admin2_conflict_path = BASE_DIR / "data" / "cleaned" / "global"     / "conflict_standardized_monthlybytype.csv"
global_admin2_path       = BASE_DIR / "data" / "raw"     / "boundaries" / "geoBoundariesCGAZ_ADM2.geojson"

# ──────────────────────────────────────────────────
# INTRO STORY CONFIG
# Update these paths, colors, timings, and messages to swap assets later.
# ──────────────────────────────────────────────────
INTRO_VIDEO_PATH = Path(
    r"C:\Users\rama\Downloads\From KlickPin CF Pin di Nana Sujana su Videogram _ Sfondi Sfondi per telefono Parola di dio - Pin-20336635812903131.mp4"
)

INTRO_IMAGE_PATHS = {
    "conflict": Path(r"C:\Users\rama\Downloads\download.jpg"),
    "limits": Path(r"C:\Users\rama\Downloads\download (1).jpg"),
    "displacement": Path(r"C:\Users\rama\Downloads\download (3).jpg"),
    "priority": Path(r"C:\Users\rama\Downloads\download (2).jpg"),
}

INTRO_STORY_THEME = {
    "navy_900": "#071627",
    "navy_800": "#10243d",
    "navy_700": "#1a3658",
    "navy_500": "#365d87",
    "text_main": "#f5f4ef",
    "text_soft": "rgba(245, 244, 239, 0.74)",
    "text_dim": "rgba(245, 244, 239, 0.46)",
    "danger": "#c96a69",
    "priority": "#8fae92",
}

INTRO_STORY_MOTION = {
    "component_height_px": 920,    # Intro viewport height in Streamlit
    "hero_transition_ms": 1400,    # Delay before auto-scroll after the video ends
    "reveal_ms": 950,              # Fade/slide reveal duration
    "parallax_shift_px": 28,       # Image motion intensity
}

INTRO_STORY_COPY = {
    # Replace these messages with your final scrollytelling text later.
    "hero_eyebrow": "Conflict Intelligence Story",
    "hero_title": "Conflicts: never only a battle.",
    "hero_body": "It expands into displacement, interrupted services, and harder decisions about where help should go first.",
    "slide_1_eyebrow": "01 / Global Conflict",
    "slide_1_title": "Conflict first appears as scale.",
    "slide_1_body": "Events and fatalities reveal where violence is concentrated, but the numbers are only the beginning of the story.",
    "slide_2_eyebrow": "02 / Limits",
    "slide_2_title": "Conflict alone is not enough.",
    "slide_2_body": "A country can record violence and still hide a deeper humanitarian reality. Risk grows when conflict meets exposure, displacement, and weaker access.",
    "slide_3_eyebrow": "03 / Displacement",
    "slide_3_title": "People carry the cost forward.",
    "slide_3_body": "Displacement turns conflict into lived disruption, reshaping shelter, education, health access, and the geography of need.",
    "slide_4_eyebrow": "04 / Priority",
    "slide_4_title": "Priority matters when resources do not stretch equally.",
    "slide_4_body": "Priority is the bridge between what happened and where response becomes most urgent.",
    "slide_5_eyebrow": "05 / Method",
    "slide_5_title": "Priority is measured through overlap.",
    "slide_5_body": "Conflict intensity, displacement pressure, exposed populations, and service access combine to identify where conditions tighten fastest.",
    "slide_6_eyebrow": "06 / Priority View",
    "slide_6_title": "The priority lens sharpens the picture.",
    "slide_6_body": "This final view is less about where conflict happened and more about where humanitarian pressure is now most concentrated.",
    "slide_7_eyebrow": "07 / Explore",
    "slide_7_title": "Enter the dashboard.",
    "slide_7_body": "Move from the guided story into the interactive dashboard to explore countries, months, displacement flows, and priority rankings in detail.",
}

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
        "odesa":"odessa","oddesa":"odessa","nabatyeh":"el nabatieh",
        "nabatiyeh":"el nabatieh","nabatiye":"el nabatieh","nabatieh":"el nabatieh",
        "al nabatieh":"el nabatieh","baalbek hermel":"baalbek-el hermel",
        "baalbek-hermel":"baalbek-el hermel","baalbek el hermel":"baalbek-el hermel",
        "republic of mordovia":"mordovia","republic of karelia":"karelia",
    }
    value = post.get(value, value)

    country_specific = {
        "lebanon":{
            "aakkar":"akkar","akkar":"akkar","beyrouth":"beirut","beirut":"beirut",
            "beqaa":"bekaa","bekaa":"bekaa","baalbek hermel":"baalbek-el hermel",
            "baalbek-hermel":"baalbek-el hermel","baalbek el hermel":"baalbek-el hermel",
            "baalbek-el hermel":"baalbek-el hermel","mont-liban":"mount lebanon",
            "mont liban":"mount lebanon","mount lebanon":"mount lebanon",
            "keserwan-jbeil":"mount lebanon","keserwan jbeil":"mount lebanon",
            "liban-nord":"north","liban nord":"north","north":"north",
            "liban-sud":"south","liban sud":"south","south":"south",
            "nabatiye":"el nabatieh","nabatiyeh":"el nabatieh",
            "nabatieh":"el nabatieh","nabatyeh":"el nabatieh",
            "nabatye":"el nabatieh","al nabatieh":"el nabatieh","el nabatieh":"el nabatieh",
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

def build_available_periods(*frames):
    period_frames = []
    for frame in frames:
        if frame is None or frame.empty:
            continue
        if not {"year", "month_num", "month"}.issubset(frame.columns):
            continue
        period_frame = frame[["year", "month_num", "month"]].copy()
        period_frame["year"] = pd.to_numeric(period_frame["year"], errors="coerce")
        period_frame["month_num"] = pd.to_numeric(period_frame["month_num"], errors="coerce")
        period_frame["month"] = period_frame["month"].astype(str).str.strip()
        period_frame = period_frame[
            period_frame["year"].notna() &
            period_frame["month_num"].notna() &
            period_frame["month"].ne("") &
            period_frame["month"].ne("nan")
        ].copy()
        if period_frame.empty:
            continue
        period_frame["year"] = period_frame["year"].astype(int)
        period_frame["month_num"] = period_frame["month_num"].astype(int)
        period_frame = period_frame[
            (period_frame["year"] >= MIN_YEAR) &
            (period_frame["year"] <= MAX_YEAR)
        ].copy()
        if not period_frame.empty:
            period_frames.append(period_frame)

    if not period_frames:
        return pd.DataFrame(columns=["year", "month_num", "month"])

    return (
        pd.concat(period_frames, ignore_index=True)
        .drop_duplicates()
        .sort_values(["year", "month_num"])
        .reset_index(drop=True)
    )

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

def add_area_proxy(gdf):
    gdf = gdf.copy()
    if "area_sqkm" in gdf.columns:
        gdf["area_sqkm"] = pd.to_numeric(gdf["area_sqkm"], errors="coerce").fillna(0).clip(lower=0)
        return gdf
    try:
        area = gdf.to_crs(epsg=3857).geometry.area / 1_000_000
        gdf["area_sqkm"] = pd.to_numeric(area, errors="coerce").fillna(0).clip(lower=0)
    except Exception:
        gdf["area_sqkm"] = 0.0
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

def extract_selected_map_location(event):
    if event is None:
        return None
    try:
        if isinstance(event, dict):
            points = event.get("selection", {}).get("points", [])
        else:
            sel = getattr(event, "selection", {})
            points = sel.get("points", []) if isinstance(sel, dict) else []
    except Exception:
        return None
    if not points:
        return None
    point = points[0]
    location = point.get("location")
    if location:
        return str(location).strip()
    custom = point.get("customdata", [])
    if custom:
        return str(custom[0]).strip()
    return None

def standardize_lebanon_admin2_name(value):
    value = normalize_text(value)
    if value is None:
        return None
    mapping = {
        "akkar": "akkar",
        "al batroun": "batroun",
        "el batroun": "batroun",
        "batroun": "batroun",
        "aley": "aley",
        "baabda": "baabda",
        "baalbek": "baalbek",
        "beirut": "beirut",
        "bcharre": "bcharre",
        "bsharri": "bcharre",
        "bint jbeil": "bent jbail",
        "bent jbeil": "bent jbail",
        "chouf": "chouf",
        "el hermel": "hermel",
        "al hermel": "hermel",
        "hermel": "hermel",
        "el koura": "koura",
        "al kura": "koura",
        "koura": "koura",
        "el meten": "el metn",
        "el metn": "el metn",
        "al matn": "el metn",
        "matn": "el metn",
        "hasbaya": "hasbeiya",
        "hasbeiya": "hasbeiya",
        "jbail": "jbail",
        "jbeil": "jbail",
        "jubayl": "jbail",
        "jezzine": "jezzine",
        "keserwan": "kesrouan",
        "kesrwane": "kesrouan",
        "kesrouan": "kesrouan",
        "marjayoun": "marjaayoun",
        "marjaayoun": "marjaayoun",
        "al miniyeh al danniyeh": "al miniyeh al danniyeh",
        "el miniyeh al danniyeh": "al miniyeh al danniyeh",
        "el minieh dennie": "al miniyeh al danniyeh",
        "el minieh-dennie": "al miniyeh al danniyeh",
        "el minieh denniyeh": "al miniyeh al danniyeh",
        "minieh danniyeh": "al miniyeh al danniyeh",
        "al miniyeh-danniyeh": "al miniyeh al danniyeh",
        "nabatieh": "nabatiye",
        "al nabatieh": "nabatiye",
        "el nabatieh": "nabatiye",
        "nabatiye": "nabatiye",
        "rachaya": "rachaya",
        "rashaya": "rachaya",
        "rashayya": "rachaya",
        "saida": "saida",
        "sayda": "saida",
        "sidon": "saida",
        "sour": "sour",
        "tyr": "sour",
        "tyre": "sour",
        "tripoli": "tripoli",
        "west bekaa": "west bekaa",
        "zahle": "zahle",
        "zgharta": "zgharta",
    }
    return mapping.get(value, value)

def format_lebanon_admin2_label(value):
    normalized = standardize_lebanon_admin2_name(value)
    label_map = {
        "akkar": "Akkar",
        "al miniyeh al danniyeh": "Al Miniyeh-Danniyeh",
        "aley": "Aley",
        "baabda": "Baabda",
        "baalbek": "Baalbek",
        "batroun": "Batroun",
        "bcharre": "Bcharre",
        "beirut": "Beirut",
        "bent jbail": "Bent Jbeil",
        "chouf": "Chouf",
        "el metn": "El Metn",
        "hasbeiya": "Hasbeiya",
        "hermel": "Hermel",
        "jbail": "Jbeil",
        "jezzine": "Jezzine",
        "kesrouan": "Kesrouan",
        "koura": "Koura",
        "marjaayoun": "Marjaayoun",
        "nabatiye": "Nabatiye",
        "rachaya": "Rachaya",
        "saida": "Saida",
        "sour": "Sour",
        "tripoli": "Tripoli",
        "west bekaa": "West Bekaa",
        "zahle": "Zahle",
        "zgharta": "Zgharta",
    }
    return label_map.get(normalized, str(value).strip().title() if value is not None else "")

def standardize_admin2_name(value, country_name=None):
    if canonical_country_norm(country_name) == "lebanon":
        return standardize_lebanon_admin2_name(value)
    return normalize_text(value)

def format_admin2_label(value, country_name=None):
    if canonical_country_norm(country_name) == "lebanon":
        return format_lebanon_admin2_label(value)
    if value is None:
        return ""
    return str(value).strip()

def _coerce_col(frame, col, default=0.0):
    if col in frame.columns:
        return pd.to_numeric(frame[col], errors="coerce").fillna(default)
    return pd.Series(default, index=frame.index, dtype="float64")

def ensure_numeric_columns(frame, columns, default=0.0):
    frame = frame.copy()
    for col in columns:
        frame[col] = _coerce_col(frame, col, default)
    return frame

def allocate_total_by_weights(total_value, weight_series):
    total_value = int(round(float(total_value or 0)))
    weights = pd.to_numeric(weight_series, errors="coerce").fillna(0)
    if total_value <= 0 or len(weights) == 0:
        return pd.Series([0] * len(weights), index=weights.index, dtype="int64")
    if float(weights.sum()) <= 0:
        weights = pd.Series([1.0] * len(weights), index=weights.index)
    shares = weights / float(weights.sum())
    raw = shares * total_value
    allocated = raw.astype(int)
    remainder = total_value - int(allocated.sum())
    if remainder > 0:
        fractions = (raw - allocated).sort_values(ascending=False)
        for idx in fractions.index[:remainder]:
            allocated.loc[idx] += 1
    return allocated.astype(int)

def row_to_values(row):
    if row is None:
        return {}
    if isinstance(row, pd.DataFrame):
        if row.empty:
            return {}
        return row.iloc[0].to_dict()
    if isinstance(row, pd.Series):
        return row.to_dict()
    try:
        return dict(row)
    except Exception:
        return {}

def numeric_value(values, key, default=0.0):
    try:
        value = values.get(key, default)
        value = pd.to_numeric(value, errors="coerce")
        return float(default if pd.isna(value) else value)
    except Exception:
        return float(default)

def scale_to_max(series):
    numeric = pd.to_numeric(series, errors="coerce").fillna(0).clip(lower=0)
    max_value = float(numeric.max()) if len(numeric) else 0.0
    if max_value <= 0:
        return pd.Series(0.0, index=numeric.index)
    return numeric / max_value

def _fallback_priority_score(frame):
    work = ensure_numeric_columns(
        frame.copy(),
        ["events", "fatalities", "population_exposure", "displaced_in", "displaced"],
    )
    displaced_source = (
        work["displaced_in"]
        if float(work["displaced_in"].sum()) > 0
        else work["displaced"]
    )
    components = [
        (scale_to_max(work["events"]), 0.35),
        (scale_to_max(work["fatalities"]), 0.30),
        (scale_to_max(displaced_source), 0.25),
        (scale_to_max(work["population_exposure"]), 0.10),
    ]
    score = pd.Series(0.0, index=work.index, dtype="float64")
    active_weight = 0.0
    for component, weight in components:
        if float(component.sum()) > 0:
            score = score + component * weight
            active_weight += weight
    if active_weight <= 0:
        return score
    return score / active_weight

def district_signal_weights(frame):
    return hierarchy.allocation_weights(frame)

def compute_admin2_priority_scores(frame):
    frame = ensure_numeric_columns(
        frame,
        [
            "events", "fatalities", "population_exposure", "displaced", "displaced_in",
            "priority_score_country", "priority_score_global",
            "access_risk", "demographic_vulnerability",
            "health_priority_score", "education_priority_score",
        ],
    )
    frame["events_norm"] = scale_to_max(frame["events"])
    frame["fatalities_norm"] = scale_to_max(frame["fatalities"])
    frame["conflict_score"] = 0.6 * frame["events_norm"] + 0.4 * frame["fatalities_norm"]
    disp_source = frame["displaced_in"] if float(frame["displaced_in"].sum()) > 0 else frame["displaced"]
    frame["displacement_score"] = scale_to_max(disp_source)
    frame["exposure_score"] = scale_to_max(frame["population_exposure"])
    frame["access_score"] = scale_to_max(frame["access_risk"])
    frame["vulnerability_score"] = scale_to_max(frame["demographic_vulnerability"])
    frame["health_score"] = scale_to_max(frame["health_priority_score"])
    frame["education_score"] = scale_to_max(frame["education_priority_score"])
    parent_source = (
        frame["priority_score_country"]
        if float(frame["priority_score_country"].sum()) > 0
        else frame["priority_score_global"]
    )
    frame["parent_priority_score"] = scale_to_max(parent_source)

    weighted_components = [
        ("conflict_score", 0.40),
        ("displacement_score", 0.25),
        ("exposure_score", 0.12),
        ("access_score", 0.10),
        ("vulnerability_score", 0.07),
        ("health_score", 0.03),
        ("education_score", 0.03),
        ("parent_priority_score", 0.05),
    ]
    score = pd.Series(0.0, index=frame.index, dtype="float64")
    active_weight = 0.0
    for col, weight in weighted_components:
        if float(frame[col].sum()) > 0:
            score = score + frame[col] * weight
            active_weight += weight
    frame["priority_score"] = score / active_weight if active_weight > 0 else 0.0
    frame["priority_rank"] = 0
    positive = frame["priority_score"] > 0
    if positive.any():
        frame.loc[positive, "priority_rank"] = (
            frame.loc[positive, "priority_score"]
            .rank(method="dense", ascending=False)
            .astype(int)
        )
    return frame

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
        "population_exposure":"Pop. Exposure","displaced":"Displacement Snapshot",
        "country_priority_score":"Priority Score",
        "country_priority_score_base":"Base Priority Score",
        "health_priority_score":"Health Priority",
        "education_priority_score":"Education Priority",
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

def is_score_metric(metric):
    return metric in {
        "country_priority_score",
        "country_priority_score_base",
        "priority_score_country",
        "priority_score_global",
        "health_priority_score",
        "education_priority_score",
    }

def format_metric_value(metric, value):
    try:
        value = float(value)
    except Exception:
        return "—"
    return f"{value:.3f}" if is_score_metric(metric) else fmt_big(value)

def get_country_priority_period_row(country_rows, selected_year, selected_month):
    period_rows = country_rows[
        (country_rows["year"] == selected_year) &
        (country_rows["month"].str.lower() == selected_month.lower())
    ].copy()
    if period_rows.empty:
        return None
    return period_rows.sort_values(["year", "month_num"]).iloc[-1]

def render_country_need_detail(selected_country_name, period_row):
    if period_row is None:
        return

    radar_labels = [
        "Conflict",
        "Fatalities",
        "Displacement",
        "Exposure",
        "Health Need",
        "Education Need",
    ]
    radar_values = [
        float(period_row.get("events_norm", 0) or 0),
        float(period_row.get("fatalities_norm", 0) or 0),
        float(period_row.get("displaced_norm", 0) or 0),
        float(period_row.get("exposure_norm", 0) or 0),
        float(period_row.get("health_priority_score", 0) or 0),
        float(period_row.get("education_priority_score", 0) or 0),
    ]
    radar_values.append(radar_values[0])
    radar_labels.append(radar_labels[0])

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=radar_values,
        theta=radar_labels,
        fill="toself",
        line=dict(color="#2c4a6e", width=2),
        fillcolor="rgba(44, 74, 110, 0.18)",
        hoverinfo="skip",
        showlegend=False,
    ))
    fig.update_layout(
        polar=dict(
            bgcolor="#ffffff",
            radialaxis=dict(
                visible=True,
                range=[0, 1],
                tickfont=dict(family="Inter", size=9, color="#8893a4"),
                gridcolor="#eef1f6",
                linecolor="#eef1f6",
            ),
            angularaxis=dict(
                tickfont=dict(family="Inter", size=10, color="#1b2230"),
                gridcolor="#eef1f6",
                linecolor="#eef1f6",
            ),
        ),
        paper_bgcolor="#ffffff",
        margin=dict(l=20, r=20, t=20, b=20),
        height=340,
    )

    health_year = int(period_row["health_source_year"]) if pd.notna(period_row.get("health_source_year")) else None
    education_year = int(period_row["education_source_year"]) if pd.notna(period_row.get("education_source_year")) else None
    health_count = int(period_row.get("health_indicator_count", 0) or 0)
    education_count = int(period_row.get("education_indicator_count", 0) or 0)

    st.markdown(
        f'<div class="section-title"><span class="section-dot"></span>{selected_country_name} Need Profile</div>',
        unsafe_allow_html=True,
    )
    left_col, right_col = st.columns([1.05, 1.15], gap="large")
    with left_col:
        st.plotly_chart(fig, use_container_width=True, key=f"need_profile_{canonical_country_norm(selected_country_name)}")
    with right_col:
        st.markdown(f"""
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
          <div class="kpi-card gold" style="margin:0;">
            <div class="kpi-accent"></div>
            <div class="kpi-label">Priority Score</div>
            <div class="kpi-value" style="font-size:28px;">{float(period_row.get("country_priority_score", 0)):.3f}</div>
            <div class="kpi-sub">Country score for this period</div>
          </div>
          <div class="kpi-card" style="margin:0;">
            <div class="kpi-accent"></div>
            <div class="kpi-label">Base Score</div>
            <div class="kpi-value" style="font-size:28px;">{float(period_row.get("country_priority_score_base", 0)):.3f}</div>
            <div class="kpi-sub">Conflict, exposure, displacement only</div>
          </div>
          <div class="kpi-card teal" style="margin:0;">
            <div class="kpi-accent"></div>
            <div class="kpi-label">Health Priority</div>
            <div class="kpi-value" style="font-size:28px;">{float(period_row.get("health_priority_score", 0)):.3f}</div>
            <div class="kpi-sub">Latest health year: {health_year if health_year is not None else "N/A"} · {health_count} indicator(s)</div>
          </div>
          <div class="kpi-card warm" style="margin:0;">
            <div class="kpi-accent"></div>
            <div class="kpi-label">Education Priority</div>
            <div class="kpi-value" style="font-size:28px;">{float(period_row.get("education_priority_score", 0)):.3f}</div>
            <div class="kpi-sub">Latest education year: {education_year if education_year is not None else "N/A"} · {education_count} indicator(s)</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

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

@st.cache_data(show_spinner=False)
def file_to_data_uri(path_str):
    path = Path(path_str)
    if not path.exists():
        return None
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"

def build_intro_story_html(video_uri, image_uris, story_stats):
    theme = INTRO_STORY_THEME
    motion = INTRO_STORY_MOTION
    copy = INTRO_STORY_COPY

    def bg_style(key):
        uri = image_uris.get(key)
        if uri:
            return f"background-image:url('{uri}');"
        return ""

    def render_stat_cards(items, class_name):
        return "".join(
            f"""
            <article class="{class_name}">
              <div class="{class_name}__label">{escape(str(item['label']))}</div>
              <div class="{class_name}__value">{escape(str(item['value']))}</div>
              <p class="{class_name}__copy">{escape(str(item['copy']))}</p>
            </article>
            """
            for item in items
        )

    conflict_cards = [
        {"label": "Global Events", "value": story_stats["total_events"], "copy": "Recorded across the active conflict layer."},
        {"label": "Fatalities", "value": story_stats["total_fatalities"], "copy": "The most immediate visible cost."},
        {"label": "Latest Hotspot", "value": story_stats["top_conflict_country"], "copy": f"{story_stats['top_conflict_events']} events in {story_stats['latest_label']}."},
        {"label": "Countries", "value": story_stats["country_count"], "copy": "Covered in the country-level conflict view."},
    ]

    formula_cards = [
        {"label": "Conflict", "value": "Events + fatalities", "copy": "Intensity is the first signal.", "tone": "danger"},
        {"label": "Displacement", "value": "Movement pressure", "copy": "Need travels with people.", "tone": "danger"},
        {"label": "Exposure", "value": "People at risk", "copy": "Scale sharpens the urgency.", "tone": "priority"},
        {"label": "Access", "value": "Services within reach", "copy": "Health access changes the response picture.", "tone": "priority"},
    ]

    formula_markup = "".join(
        f"""
        <article class="story-formula-card tone-{escape(card['tone'])}">
          <div class="story-formula-card__label">{escape(card['label'])}</div>
          <div class="story-formula-card__value">{escape(card['value'])}</div>
          <p class="story-formula-card__copy">{escape(card['copy'])}</p>
        </article>
        """
        for card in formula_cards
    )

    priority_cards = [
        {"label": "Priority Country", "value": story_stats["priority_country"], "copy": f"Highest latest country score in {story_stats['latest_label']}."},
        {"label": "Priority Score", "value": story_stats["priority_score"], "copy": "Higher values indicate tighter overlap of risk."},
        {"label": "Population Exposure", "value": story_stats["population_exposure"], "copy": "Exposure expands the story beyond incidents alone."},
        {"label": "Health Signal", "value": story_stats["health_signal"], "copy": f"{story_stats['health_area']} currently leads the Lebanon health-access signal."},
    ]

    html = f"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Conflict Story Intro</title>
  <style>
    :root {{
      --story-navy-900: {theme['navy_900']};
      --story-navy-800: {theme['navy_800']};
      --story-navy-700: {theme['navy_700']};
      --story-navy-500: {theme['navy_500']};
      --story-text: {theme['text_main']};
      --story-text-soft: {theme['text_soft']};
      --story-text-dim: {theme['text_dim']};
      --story-danger: {theme['danger']};
      --story-priority: {theme['priority']};
      --story-reveal-ms: {motion['reveal_ms']}ms;
      --story-parallax-y: {motion['parallax_shift_px']}px;
    }}

    * {{ box-sizing: border-box; }}
    html, body {{
      margin: 0;
      padding: 0;
      height: 100%;
      background: var(--story-navy-900);
      color: var(--story-text);
      font-family: Inter, "Helvetica Neue", Arial, sans-serif;
      overflow: hidden;
    }}

    .story-shell {{
      height: 100vh;
      overflow-y: auto;
      scroll-snap-type: y mandatory;
      scroll-behavior: smooth;
      background: var(--story-navy-900);
    }}
    .story-shell.is-locked {{
      overflow: hidden;
    }}

    .story-step {{
      position: relative;
      min-height: 100vh;
      scroll-snap-align: start;
      overflow: hidden;
      display: flex;
      align-items: center;
      justify-content: center;
      background:
        radial-gradient(circle at 70% 15%, rgba(54, 93, 135, 0.18), transparent 20%),
        linear-gradient(180deg, var(--story-navy-900) 0%, var(--story-navy-800) 100%);
    }}
    .story-step--light {{
      background:
        radial-gradient(circle at 18% 16%, rgba(54, 93, 135, 0.08), transparent 18%),
        linear-gradient(180deg, #f6f7fa 0%, #eef2f7 100%);
      color: #0f1b2c;
    }}

    .story-media,
    .story-video {{
      position: absolute;
      inset: 0;
      width: 100%;
      height: 100%;
      object-fit: cover;
    }}
    .story-media {{
      background-position: center center;
      background-size: cover;
      opacity: 0.48;
      transform: scale(1.08) translateY(var(--story-parallax-y));
      filter: saturate(0.9) contrast(1.03) brightness(0.78);
      transition:
        transform 2200ms cubic-bezier(.2,.75,.2,1),
        opacity 1200ms ease,
        filter 1200ms ease;
    }}
    .story-step.is-visible .story-media {{
      opacity: 0.72;
      transform: scale(1.02) translateY(0);
      filter: saturate(1) contrast(1.06) brightness(0.9);
    }}

    .story-video {{
      opacity: 1;
      filter: saturate(0.85) brightness(0.62);
    }}

    .story-overlay {{
      position: absolute;
      inset: 0;
      background:
        linear-gradient(180deg, rgba(7, 22, 39, 0.36) 0%, rgba(7, 22, 39, 0.74) 100%),
        radial-gradient(circle at center, rgba(7, 22, 39, 0.10) 0%, rgba(7, 22, 39, 0.68) 100%);
    }}
    .story-step--light .story-overlay {{
      background:
        linear-gradient(180deg, rgba(246, 247, 250, 0.50) 0%, rgba(238, 242, 247, 0.92) 100%);
    }}

    .story-content {{
      position: relative;
      z-index: 2;
      width: min(1180px, calc(100vw - 64px));
      padding: 68px 24px;
    }}
    .story-content > * {{
      opacity: 0;
      transform: translateY(28px);
      filter: blur(12px);
      transition:
        opacity var(--story-reveal-ms) ease,
        transform var(--story-reveal-ms) ease,
        filter var(--story-reveal-ms) ease;
    }}
    .story-step.is-visible .story-content > * {{
      opacity: 1;
      transform: translateY(0);
      filter: blur(0);
    }}
    .story-step.is-visible .story-content > *:nth-child(2) {{ transition-delay: 90ms; }}
    .story-step.is-visible .story-content > *:nth-child(3) {{ transition-delay: 180ms; }}
    .story-step.is-visible .story-content > *:nth-child(4) {{ transition-delay: 260ms; }}

    .story-kicker {{
      margin: 0 0 18px;
      font-size: 11px;
      font-weight: 500;
      letter-spacing: 0.28em;
      text-transform: uppercase;
      color: var(--story-text-dim);
    }}
    .story-step--light .story-kicker {{
      color: rgba(16, 36, 61, 0.56);
    }}

    .story-headline {{
      margin: 0;
      max-width: 12ch;
      font-size: clamp(48px, 7vw, 72px);
      font-weight: 500;
      line-height: 0.98;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--story-text);
    }}
    .story-step--light .story-headline {{
      color: #10243d;
    }}

    .story-body {{
      margin: 24px 0 0;
      max-width: 32rem;
      font-size: clamp(16px, 1.9vw, 20px);
      font-weight: 400;
      line-height: 1.8;
      color: var(--story-text-soft);
    }}
    .story-step--light .story-body {{
      color: rgba(16, 36, 61, 0.72);
    }}

    .story-accent-danger {{ color: var(--story-danger); }}
    .story-accent-priority {{ color: var(--story-priority); }}

    .story-grid {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 18px;
      margin-top: 34px;
    }}
    .story-stat-card,
    .story-priority-card,
    .story-formula-card {{
      min-height: 220px;
      padding: 24px 22px;
      border-radius: 26px;
      border: 1px solid rgba(255,255,255,0.08);
      background: rgba(255,255,255,0.05);
      backdrop-filter: blur(10px);
      box-shadow: 0 18px 38px rgba(0,0,0,0.16);
    }}
    .story-step--light .story-stat-card,
    .story-step--light .story-priority-card,
    .story-step--light .story-formula-card {{
      border-color: rgba(16, 36, 61, 0.08);
      background: rgba(255,255,255,0.72);
      box-shadow: 0 16px 34px rgba(16, 36, 61, 0.08);
    }}
    .story-stat-card__label,
    .story-priority-card__label,
    .story-formula-card__label {{
      font-size: 10px;
      font-weight: 500;
      letter-spacing: 0.2em;
      text-transform: uppercase;
      color: var(--story-text-dim);
    }}
    .story-step--light .story-stat-card__label,
    .story-step--light .story-priority-card__label,
    .story-step--light .story-formula-card__label {{
      color: rgba(16, 36, 61, 0.48);
    }}
    .story-stat-card__value,
    .story-priority-card__value,
    .story-formula-card__value {{
      margin-top: 18px;
      font-size: clamp(28px, 3.8vw, 44px);
      font-weight: 500;
      line-height: 1.04;
      letter-spacing: 0.02em;
    }}
    .story-formula-card__value {{
      font-size: clamp(22px, 2.8vw, 30px);
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}
    .story-stat-card__copy,
    .story-priority-card__copy,
    .story-formula-card__copy {{
      margin: 18px 0 0;
      font-size: 15px;
      line-height: 1.75;
      color: var(--story-text-soft);
    }}
    .story-step--light .story-stat-card__copy,
    .story-step--light .story-priority-card__copy,
    .story-step--light .story-formula-card__copy {{
      color: rgba(16, 36, 61, 0.72);
    }}

    .tone-danger {{
      box-shadow: inset 0 0 0 1px rgba(201, 106, 105, 0.24), 0 18px 38px rgba(0,0,0,0.16);
    }}
    .tone-priority {{
      box-shadow: inset 0 0 0 1px rgba(143, 174, 146, 0.24), 0 18px 38px rgba(0,0,0,0.16);
    }}

    .story-priority-visual {{
      display: grid;
      grid-template-columns: 1.1fr 0.9fr;
      gap: 26px;
      align-items: stretch;
      margin-top: 32px;
    }}
    .story-priority-scene {{
      position: relative;
      min-height: 430px;
      border-radius: 34px;
      overflow: hidden;
      border: 1px solid rgba(255,255,255,0.08);
      background:
        radial-gradient(circle at 25% 25%, rgba(201, 106, 105, 0.14), transparent 20%),
        radial-gradient(circle at 72% 28%, rgba(143, 174, 146, 0.12), transparent 24%),
        linear-gradient(180deg, rgba(16,36,61,0.76) 0%, rgba(7,22,39,0.86) 100%);
    }}
    .story-priority-scene::before {{
      content: "";
      position: absolute;
      inset: 0;
      {bg_style("priority")}
      background-position: center;
      background-size: cover;
      opacity: 0.34;
      transform: scale(1.05);
    }}
    .story-priority-scene::after {{
      content: "";
      position: absolute;
      inset: 0;
      background:
        linear-gradient(180deg, rgba(7,22,39,0.10) 0%, rgba(7,22,39,0.82) 100%);
    }}
    .story-priority-scene-copy {{
      position: absolute;
      left: 28px;
      right: 28px;
      bottom: 28px;
      z-index: 2;
    }}
    .story-priority-scene-copy h3 {{
      margin: 0;
      font-size: clamp(24px, 3vw, 34px);
      font-weight: 500;
      letter-spacing: 0.08em;
      line-height: 1.05;
      text-transform: uppercase;
    }}
    .story-priority-scene-copy p {{
      margin: 14px 0 0;
      max-width: 28rem;
      font-size: 16px;
      line-height: 1.8;
      color: var(--story-text-soft);
    }}

    .story-cta {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-width: 290px;
      margin-top: 28px;
      padding: 17px 32px;
      border-radius: 999px;
      border: 1px solid rgba(245, 244, 239, 0.12);
      background: rgba(255,255,255,0.08);
      color: var(--story-text);
      text-decoration: none;
      font-size: 13px;
      font-weight: 500;
      letter-spacing: 0.18em;
      text-transform: uppercase;
      appearance: none;
      cursor: pointer;
      transition: transform 180ms ease, background 180ms ease, border-color 180ms ease;
    }}
    .story-cta:hover {{
      transform: translateY(-1px);
      background: rgba(255,255,255,0.12);
      border-color: rgba(245, 244, 239, 0.22);
    }}

    .story-skip {{
      position: absolute;
      right: 28px;
      bottom: 28px;
      z-index: 3;
      border: 1px solid rgba(245, 244, 239, 0.14);
      background: rgba(7,22,39,0.35);
      color: var(--story-text);
      padding: 12px 16px;
      border-radius: 999px;
      font-size: 11px;
      font-weight: 500;
      letter-spacing: 0.18em;
      text-transform: uppercase;
      cursor: pointer;
    }}

    @media (max-width: 1024px) {{
      .story-grid,
      .story-priority-visual {{
        grid-template-columns: 1fr;
      }}
      .story-headline {{
        max-width: 100%;
      }}
      .story-content {{
        width: min(100vw, calc(100vw - 28px));
        padding: 42px 16px;
      }}
    }}

    @media (max-width: 680px) {{
      .story-headline {{
        font-size: clamp(42px, 12vw, 56px);
      }}
      .story-body,
      .story-priority-scene-copy p {{
        font-size: 16px;
      }}
      .story-stat-card,
      .story-priority-card,
      .story-formula-card {{
        min-height: auto;
      }}
    }}
  </style>
</head>
<body>
  <main class="story-shell is-locked" id="storyShell">
    <section class="story-step story-step--hero is-visible" id="storyHero">
      <video class="story-video" id="storyVideo" autoplay muted playsinline preload="auto">
        <source src="{video_uri or ''}" type="video/mp4">
      </video>
      <div class="story-overlay"></div>
      <div class="story-content">
        <p class="story-kicker">{escape(copy['hero_eyebrow'])}</p>
        <h1 class="story-headline">{escape(copy['hero_title'])}</h1>
        <p class="story-body">{escape(copy['hero_body'])}</p>
      </div>
      <button class="story-skip" id="storySkip">Skip intro</button>
    </section>

    <section class="story-step" data-step>
      <div class="story-media" style="{bg_style('conflict')}"></div>
      <div class="story-overlay"></div>
      <div class="story-content">
        <p class="story-kicker">{escape(copy['slide_1_eyebrow'])}</p>
        <h2 class="story-headline">{escape(copy['slide_1_title'])}</h2>
        <p class="story-body">{escape(copy['slide_1_body'])}</p>
        <div class="story-grid">
          {render_stat_cards(conflict_cards, "story-stat-card")}
        </div>
      </div>
    </section>

    <section class="story-step story-step--light" data-step>
      <div class="story-media" style="{bg_style('limits')}"></div>
      <div class="story-overlay"></div>
      <div class="story-content">
        <p class="story-kicker">{escape(copy['slide_2_eyebrow'])}</p>
        <h2 class="story-headline">{escape(copy['slide_2_title'])}</h2>
        <p class="story-body">{escape(copy['slide_2_body'])}</p>
      </div>
    </section>

    <section class="story-step" data-step>
      <div class="story-media" style="{bg_style('displacement')}"></div>
      <div class="story-overlay"></div>
      <div class="story-content">
        <p class="story-kicker">{escape(copy['slide_3_eyebrow'])}</p>
        <h2 class="story-headline">{escape(copy['slide_3_title'])}</h2>
        <p class="story-body">{escape(copy['slide_3_body'])}</p>
        <div class="story-grid">
          {render_stat_cards([
              {"label": "Total displacement movements", "value": story_stats["total_displaced"], "copy": CUMULATIVE_DISPLACEMENT_NOTE},
              {"label": "Exposure", "value": story_stats["population_exposure"], "copy": "People living inside the pressure field."},
              {"label": "Priority Country", "value": story_stats["priority_country"], "copy": "Latest monthly concentration of need."},
              {"label": "Story Lens", "value": "Human impact", "copy": "This is where conflict becomes lived disruption."},
          ], "story-stat-card")}
        </div>
      </div>
    </section>

    <section class="story-step story-step--light" data-step>
      <div class="story-media" style="{bg_style('priority')}"></div>
      <div class="story-overlay"></div>
      <div class="story-content">
        <p class="story-kicker">{escape(copy['slide_4_eyebrow'])}</p>
        <h2 class="story-headline">{escape(copy['slide_4_title'])}</h2>
        <p class="story-body">{escape(copy['slide_4_body'])}</p>
      </div>
    </section>

    <section class="story-step" data-step>
      <div class="story-overlay"></div>
      <div class="story-content">
        <p class="story-kicker">{escape(copy['slide_5_eyebrow'])}</p>
        <h2 class="story-headline">{escape(copy['slide_5_title'])}</h2>
        <p class="story-body">{escape(copy['slide_5_body'])}</p>
        <div class="story-grid">
          {formula_markup}
        </div>
      </div>
    </section>

    <section class="story-step" data-step>
      <div class="story-overlay"></div>
      <div class="story-content">
        <p class="story-kicker">{escape(copy['slide_6_eyebrow'])}</p>
        <h2 class="story-headline">{escape(copy['slide_6_title'])}</h2>
        <p class="story-body">{escape(copy['slide_6_body'])}</p>
        <div class="story-priority-visual">
          <div class="story-priority-scene">
            <div class="story-priority-scene-copy">
              <h3><span class="story-accent-priority">{escape(story_stats['priority_country'])}</span> carries the sharpest latest priority signal.</h3>
              <p>Conflict data becomes more actionable when it is reframed through exposure, displacement, and access pressure.</p>
            </div>
          </div>
          <div class="story-grid">
            {render_stat_cards(priority_cards, "story-priority-card")}
          </div>
        </div>
      </div>
    </section>

    <section class="story-step" data-step>
      <div class="story-media" style="{bg_style('priority')}"></div>
      <div class="story-overlay"></div>
      <div class="story-content">
        <p class="story-kicker">{escape(copy['slide_7_eyebrow'])}</p>
        <h2 class="story-headline">{escape(copy['slide_7_title'])}</h2>
        <p class="story-body">{escape(copy['slide_7_body'])}</p>
        
      </div>
    </section>
  </main>

  <script>
    const shell = document.getElementById("storyShell");
    const hero = document.getElementById("storyHero");
    const video = document.getElementById("storyVideo");
    const skipButton = document.getElementById("storySkip");
    const firstStep = document.querySelector('[data-step]');
    const unlockDelay = {motion['hero_transition_ms']};

    function unlockAndAdvance() {{
      shell.classList.remove("is-locked");
      setTimeout(() => {{
        if (firstStep) {{
          firstStep.scrollIntoView({{ behavior: "smooth", block: "start" }});
        }}
      }}, unlockDelay);
    }}

    function buildAppUrl() {{
      const candidates = [];

      if (document.referrer) {{
        candidates.push(document.referrer);
      }}

      try {{
        if (window.parent?.location?.href) {{
          candidates.push(window.parent.location.href);
        }}
      }} catch (error) {{}}

      try {{
        if (window.top?.location?.href) {{
          candidates.push(window.top.location.href);
        }}
      }} catch (error) {{}}

      try {{
        if (window.location?.href) {{
          candidates.push(window.location.href);
        }}
      }} catch (error) {{}}

      for (const href of candidates) {{
        try {{
          const url = new URL(href, window.location.origin);
          if (url.protocol === "about:") {{
            continue;
          }}
          url.searchParams.set("open_app", "1");
          return url.toString();
        }} catch (error) {{}}
      }}

      return "/?open_app=1";
    }}

    function openApp(event) {{
      if (event) {{
        event.preventDefault();
      }}

      const targetUrl = buildAppUrl();

      try {{
        window.open(targetUrl, "_top");
        return;
      }} catch (error) {{}}

      try {{
        window.top.location.assign(targetUrl);
        return;
      }} catch (error) {{}}

      try {{
        window.parent.location.assign(targetUrl);
        return;
      }} catch (error) {{}}

      window.location.assign(targetUrl);
    }}

    if (video) {{
      video.play().catch(() => {{
        shell.classList.remove("is-locked");
      }});
      video.addEventListener("ended", unlockAndAdvance, {{ once: true }});
    }} else {{
      shell.classList.remove("is-locked");
    }}

    skipButton?.addEventListener("click", unlockAndAdvance);

    const enterAppButton = document.getElementById("storyOpenApp");
    if (enterAppButton) {{
      enterAppButton.addEventListener("click", openApp);
    }}

    const observer = new IntersectionObserver((entries) => {{
      entries.forEach((entry) => {{
        entry.target.classList.toggle("is-visible", entry.isIntersecting);
      }});
    }}, {{ threshold: 0.35 }});

    document.querySelectorAll(".story-step").forEach((step) => observer.observe(step));
  </script>
</body>
</html>
"""
    return html

def render_bubble_story(selected_country_name, boundary_gdf):
    cnorm = canonical_country_norm(selected_country_name)

    # --- aggregate displacement over full period ---
    disp_agg = (
        displacement_dest[displacement_dest["country"] == cnorm]
        .groupby("admin1_norm", as_index=False)["displaced_in"].sum()
    )
    # --- aggregate priority over full period ---
    pri_sub = admin1_priority[admin1_priority["country_norm"] == cnorm].copy()
    if pri_sub.empty:
        pri_agg = pd.DataFrame(columns=["admin1_norm"])
    else:
        agg_d = {"events": "sum", "fatalities": "sum"}
        for c in ["priority_score_country", "displaced", "population_exposure"]:
            if c in pri_sub.columns:
                agg_d[c] = "mean" if "score" in c else "sum"
        pri_agg = pri_sub.groupby("admin1_norm", as_index=False).agg(agg_d)

    bdf = disp_agg.merge(pri_agg, how="outer", on="admin1_norm")

    # display names from boundary
    name_map = dict(zip(boundary_gdf["admin_name_norm"], boundary_gdf["admin_name"]))
    bdf["display_name"] = bdf["admin1_norm"].map(name_map).fillna(
        bdf["admin1_norm"].apply(lambda x: str(x).replace("-", " ").title() if pd.notna(x) else "")
    )

    for col in ["displaced_in", "events", "fatalities",
                "priority_score_country", "displaced", "population_exposure"]:
        if col not in bdf.columns:
            bdf[col] = 0.0
        bdf[col] = pd.to_numeric(bdf[col], errors="coerce").fillna(0.0)

    bdf = bdf[bdf["admin1_norm"].notna() & (bdf["admin1_norm"].astype(str) != "nan")].copy()
    bdf = bdf.sort_values("displaced_in", ascending=False).reset_index(drop=True)

    if bdf.empty:
        st.info("No displacement data available for this country.")
        return

    # --- bubble sizes ---
    max_disp = float(bdf["displaced_in"].max())
    use_priority = max_disp <= 0
    size_col = "priority_score_country" if use_priority else "displaced_in"
    max_v = float(bdf[size_col].max()) or 1.0
    MAX_D, MIN_D = 90.0, 12.0
    bdf["px_d"] = bdf[size_col].apply(
        lambda v: float(max(MIN_D, (max(0.0, v) / max_v) ** 0.5 * MAX_D))
    )

    # --- phyllotaxis layout ---
    n = len(bdf)
    golden_angle = math.pi * (3.0 - math.sqrt(5.0))
    spread = MAX_D * 1.65
    bdf["x"] = [spread * math.sqrt(i) * math.cos(i * golden_angle) for i in range(n)]
    bdf["y"] = [spread * math.sqrt(i) * math.sin(i * golden_angle) for i in range(n)]

    all_coords = list(bdf["x"]) + list(bdf["y"])
    axis_r = (max(abs(v) for v in all_coords) + MAX_D + 45) if n > 0 else 300.0

    pri_max = float(max(bdf["priority_score_country"].max(), 0.001))
    bdf["label"] = bdf.apply(
        lambda r: str(r["display_name"]).split()[0] if r["px_d"] >= 36 else "", axis=1
    )

    # --- size legend (3 reference circles, bottom-right) ---
    leg_vals = [max_v, max_v * 0.30, max_v * 0.08]
    leg_ds = [float(max(MIN_D, (v / max_v) ** 0.5 * MAX_D)) for v in leg_vals]
    lx = axis_r * 0.80
    leg_y = [-axis_r * 0.46, -axis_r * 0.62, -axis_r * 0.73]

    fig = go.Figure()

    # bubbles
    fig.add_trace(go.Scatter(
        x=bdf["x"], y=bdf["y"],
        mode="markers+text",
        marker=dict(
            size=bdf["px_d"], sizemode="diameter",
            color=bdf["priority_score_country"],
            colorscale=SCALE_BUBBLE, cmin=0.0, cmax=pri_max,
            line=dict(width=1.5, color="rgba(255,255,255,0.5)"),
            opacity=0.87,
            colorbar=dict(
                title=dict(text="Priority", font=dict(family="Inter", size=11, color="#1b2230")),
                tickfont=dict(family="Inter", size=9, color="#5a6577"),
                len=0.42, thickness=10, outlinewidth=0, x=1.01,
            ),
        ),
        text=bdf["label"],
        textfont=dict(family="Inter", size=9, color="rgba(255,255,255,0.95)"),
        textposition="middle center",
        customdata=bdf[["display_name", "displaced_in",
                         "priority_score_country", "priority_score_country",
                         "events", "fatalities"]].values,
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "Displaced: <b>%{customdata[1]:,.0f}</b><br>"
            "Priority score: %{customdata[2]:.3f}<br>"
            "Events: %{customdata[4]:,.0f}  ·  Fatalities: %{customdata[5]:,.0f}"
            "<extra></extra>"
        ),
        showlegend=False, name="",
    ))

    # size legend circles
    fig.add_trace(go.Scatter(
        x=[lx, lx, lx], y=leg_y, mode="markers",
        marker=dict(size=leg_ds, sizemode="diameter",
                    color="rgba(175,188,205,0.40)",
                    line=dict(width=1.5, color="#b0b9c7")),
        hoverinfo="skip", showlegend=False,
    ))
    # size legend labels
    fig.add_trace(go.Scatter(
        x=[axis_r * 0.93, axis_r * 0.93, axis_r * 0.93], y=leg_y,
        mode="text",
        text=[fmt_big(v) for v in leg_vals],
        textfont=dict(family="Inter", size=9, color="#8893a4"),
        textposition="middle right",
        hoverinfo="skip", showlegend=False,
    ))

    fig.update_layout(
        paper_bgcolor="#ffffff", plot_bgcolor="#ffffff",
        font=dict(family="Inter", color="#5a6577", size=11),
        xaxis=dict(visible=False, range=[-axis_r, axis_r], fixedrange=True),
        yaxis=dict(visible=False, range=[-axis_r, axis_r],
                   scaleanchor="x", scaleratio=1, fixedrange=True),
        margin=dict(l=10, r=90, t=10, b=10),
        height=580,
        hoverlabel=dict(
            bgcolor="white", bordercolor="#e4e8ef",
            font=dict(family="Inter", size=12, color="#1b2230"),
        ),
    )
    st.plotly_chart(fig, use_container_width=True, key=f"bubble_{cnorm}")


def render_story_overview(selected_country_name, boundary_gdf, total_arrived, total_departed=0):
    cnorm = canonical_country_norm(selected_country_name)

    total_events_full = float(admin_conflict[admin_conflict["country_norm"] == cnorm]["events"].sum())
    total_fat_full    = float(admin_conflict[admin_conflict["country_norm"] == cnorm]["fatalities"].sum())

    st.markdown(f"""
    <div style="padding:20px 0 10px 0;">
      <p style="font-family:'Playfair Display',serif;font-size:22px;font-weight:600;color:#1b2230;line-height:1.4;margin:0 0 10px 0;">
        The full picture of {selected_country_name}, 2024–2026
      </p>
      <p style="font-family:'Inter',sans-serif;font-size:14px;color:#5a6577;line-height:1.85;margin:0;max-width:640px;">
        Across all regions, <strong style="color:#1b2230;">{fmt_big(total_arrived)}</strong> displaced people
        are present in the latest stock snapshot.
        The conflict left <strong style="color:#b8703a;">{fmt_big(total_fat_full)}</strong> fatalities
        across <strong style="color:#2c4a6e;">{fmt_big(total_events_full)}</strong> recorded events.
        Below are the ten admin areas that absorbed the most displaced people.
      </p>
    </div>
    """, unsafe_allow_html=True)

    # KPI chips
    st.markdown(f"""
    <div style="display:flex;gap:14px;flex-wrap:wrap;margin:10px 0 22px 0;">
      <div style="background:#e8eef6;border-radius:10px;padding:12px 20px;">
        <div style="font-family:'Inter',sans-serif;font-size:10px;font-weight:600;letter-spacing:.1em;text-transform:uppercase;color:#5a7aa0;margin-bottom:4px;">Displaced</div>
        <div style="font-family:'Playfair Display',serif;font-size:22px;font-weight:700;color:#2c4a6e;">{fmt_big(total_arrived)}</div>
      </div>
      <div style="background:#eef1f6;border-radius:10px;padding:12px 20px;">
        <div style="font-family:'Inter',sans-serif;font-size:10px;font-weight:600;letter-spacing:.1em;text-transform:uppercase;color:#5a6577;margin-bottom:4px;">Conflict Events</div>
        <div style="font-family:'Playfair Display',serif;font-size:22px;font-weight:700;color:#1b2230;">{fmt_big(total_events_full)}</div>
      </div>
      <div style="background:#fdf3eb;border-radius:10px;padding:12px 20px;">
        <div style="font-family:'Inter',sans-serif;font-size:10px;font-weight:600;letter-spacing:.1em;text-transform:uppercase;color:#b8703a;margin-bottom:4px;">Fatalities</div>
        <div style="font-family:'Playfair Display',serif;font-size:22px;font-weight:700;color:#7a4418;">{fmt_big(total_fat_full)}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Top admin1 by displaced people — horizontal bar
    disp_agg = (
        displacement_dest[displacement_dest["country"] == cnorm]
        .groupby("admin1_norm", as_index=False)["displaced_in"].sum()
    )
    if disp_agg.empty:
        st.info("No displacement data available.")
        return

    name_map = {}
    if boundary_gdf is not None and not boundary_gdf.empty:
        name_map = dict(zip(boundary_gdf["admin_name_norm"], boundary_gdf["admin_name"]))
    disp_agg["display_name"] = disp_agg["admin1_norm"].map(name_map).fillna(
        disp_agg["admin1_norm"].apply(lambda x: str(x).replace("-", " ").title())
    )
    top = disp_agg.sort_values("displaced_in", ascending=False).head(10)

    bar_colors = [
        f"rgba(44,74,110,{max(0.35, 1.0 - i*0.07):.2f})" for i in range(len(top))
    ]

    fig = go.Figure(go.Bar(
        y=top["display_name"][::-1],
        x=top["displaced_in"][::-1],
        orientation="h",
        marker=dict(color=bar_colors[::-1], line=dict(width=0)),
        text=[fmt_big(v) for v in top["displaced_in"][::-1]],
        textposition="inside",
        textfont=dict(family="Inter", size=11, color="rgba(255,255,255,0.9)"),
        hovertemplate="<b>%{y}</b><br>Displaced: %{x:,.0f}<extra></extra>",
    ))
    fig.update_layout(
        paper_bgcolor="#ffffff", plot_bgcolor="#ffffff",
        font=dict(family="Inter", color="#5a6577", size=11),
        margin=dict(l=10, r=30, t=10, b=30),
        height=max(280, len(top) * 34),
        xaxis=dict(
            showgrid=True, gridcolor="#eef1f6", gridwidth=1,
            showline=False, zeroline=False,
            tickfont=dict(family="Inter", size=10),
        ),
        yaxis=dict(
            showgrid=False, showline=False,
            tickfont=dict(family="Inter", size=11, color="#1b2230"),
        ),
        hoverlabel=dict(bgcolor="white", bordercolor="#e4e8ef",
                        font=dict(family="Inter", size=12, color="#1b2230")),
    )
    st.plotly_chart(fig, use_container_width=True, key=f"story_bar_{cnorm}")


def render_story_priority_scatter(selected_country_name, boundary_gdf):
    cnorm = canonical_country_norm(selected_country_name)

    pri_sub = admin1_priority[admin1_priority["country_norm"] == cnorm].copy()
    if pri_sub.empty:
        st.info("No priority data available for this country.")
        return

    agg_d: dict = {"events": "sum", "fatalities": "sum"}
    for c in ["priority_score_country", "displaced", "population_exposure"]:
        if c in pri_sub.columns:
            agg_d[c] = "mean" if "score" in c else "sum"
    sdf = pri_sub.groupby("admin1_norm", as_index=False).agg(agg_d)

    disp_agg = (
        displacement_dest[displacement_dest["country"] == cnorm]
        .groupby("admin1_norm", as_index=False)["displaced_in"].sum()
    )
    sdf = sdf.merge(disp_agg, how="left", on="admin1_norm")

    name_map = {}
    if boundary_gdf is not None and not boundary_gdf.empty:
        name_map = dict(zip(boundary_gdf["admin_name_norm"], boundary_gdf["admin_name"]))
    sdf["display_name"] = sdf["admin1_norm"].map(name_map).fillna(
        sdf["admin1_norm"].apply(lambda x: str(x).replace("-", " ").title())
    )

    for col in ["displaced_in", "fatalities", "priority_score_country", "population_exposure", "events"]:
        if col not in sdf.columns:
            sdf[col] = 0.0
        sdf[col] = pd.to_numeric(sdf[col], errors="coerce").fillna(0.0)

    fallback_score = _fallback_priority_score(sdf)
    real_score = pd.to_numeric(sdf["priority_score_country"], errors="coerce").fillna(0.0)
    missing_score = real_score <= 0
    fallback_used = bool(float(fallback_score[missing_score].sum()) > 0)
    sdf["priority_score_country"] = real_score.where(~missing_score, fallback_score)

    sdf = sdf[sdf["priority_score_country"] > 0].copy()
    if sdf.empty:
        st.info("No conflict, displacement, exposure, or priority signal is available for this snapshot.")
        return

    max_fat = float(sdf["fatalities"].max()) or 1.0
    MAX_SZ, MIN_SZ = 55.0, 8.0
    sdf["bubble_sz"] = sdf["fatalities"].apply(
        lambda v: float(max(MIN_SZ, (max(0, v) / max_fat) ** 0.5 * MAX_SZ))
    )

    # Annotate outliers: top 3 by priority + top 3 by displaced_in
    top_pri = set(sdf.nlargest(3, "priority_score_country")["admin1_norm"])
    top_disp = set(sdf.nlargest(3, "displaced_in")["admin1_norm"])
    highlight = top_pri | top_disp
    sdf["label"] = sdf.apply(
        lambda r: r["display_name"] if r["admin1_norm"] in highlight else "", axis=1
    )

    max_exp = float(sdf["population_exposure"].max()) or 1.0
    score_note = (
        "Precomputed priority scores were missing for some regions, so those scores are estimated from "
        "same-period events, fatalities, displacement, and exposure."
        if fallback_used else
        "Priority scores come from the precomputed priority model for this snapshot."
    )

    st.markdown(f"""
    <div style="padding:20px 0 10px 0;">
      <p style="font-family:'Playfair Display',serif;font-size:22px;font-weight:600;color:#1b2230;line-height:1.4;margin:0 0 10px 0;">
        Why does priority differ across regions?
      </p>
      <p style="font-family:'Inter',sans-serif;font-size:14px;color:#5a6577;line-height:1.85;margin:0;max-width:660px;">
        Humanitarian priority is not simply a function of how many people were displaced.
        Regions with <em>lower displacement</em> can rank highest if they also face intense conflict,
        high fatality rates, or large population exposure. Each circle below is one admin area —
        <strong>horizontal position</strong> shows displaced people,
        <strong>vertical position</strong> shows priority score,
        <strong>circle size</strong> scales with fatalities, and
        <strong>color</strong> reflects population exposure.
        Areas that sit <em>high but left</em> are priority hot-spots driven by conflict intensity, not volume.
      </p>
    </div>
    """, unsafe_allow_html=True)

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=sdf["displaced_in"],
        y=sdf["priority_score_country"],
        mode="markers+text",
        marker=dict(
            size=sdf["bubble_sz"],
            sizemode="diameter",
            color=sdf["population_exposure"],
            colorscale=SCALE_WARM,
            cmin=0, cmax=max_exp,
            opacity=0.82,
            line=dict(width=1.2, color="rgba(255,255,255,0.6)"),
            colorbar=dict(
                title=dict(text="Population<br>Exposure", font=dict(family="Inter", size=10, color="#1b2230")),
                tickfont=dict(family="Inter", size=9, color="#5a6577"),
                len=0.5, thickness=10, outlinewidth=0, x=1.01,
            ),
        ),
        text=sdf["label"],
        textfont=dict(family="Inter", size=9, color="#1b2230"),
        textposition="top center",
        customdata=sdf[["display_name", "displaced_in", "fatalities",
                         "priority_score_country", "population_exposure", "events"]].values,
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "Displaced: <b>%{customdata[1]:,.0f}</b><br>"
            "Priority score: <b>%{customdata[3]:.3f}</b><br>"
            "Fatalities: %{customdata[2]:,.0f}<br>"
            "Pop. exposure: %{customdata[4]:,.0f}<br>"
            "Events: %{customdata[5]:,.0f}"
            "<extra></extra>"
        ),
        showlegend=False,
    ))

    # Quadrant reference lines at medians
    med_x = float(sdf["displaced_in"].median())
    med_y = float(sdf["priority_score_country"].median())
    x_max = float(sdf["displaced_in"].max()) * 1.08
    y_max = float(sdf["priority_score_country"].max()) * 1.12

    for xv, yv, lbl, anchor in [
        (x_max * 0.55, y_max * 0.97, "HIGH PRIORITY · HIGH DISPLACEMENT", "center"),
        (x_max * 0.05, y_max * 0.97, "HIGH PRIORITY · LOW DISPLACEMENT", "left"),
        (x_max * 0.55, y_max * 0.04, "LOW PRIORITY · HIGH DISPLACEMENT", "center"),
    ]:
        fig.add_annotation(
            x=xv, y=yv, text=lbl,
            showarrow=False,
            font=dict(family="Inter", size=8, color="#b0b9c7"),
            xanchor=anchor, yanchor="top",
        )

    fig.add_shape(type="line", x0=med_x, x1=med_x, y0=0, y1=y_max,
                  line=dict(color="#e4e8ef", width=1, dash="dot"))
    fig.add_shape(type="line", x0=0, x1=x_max, y0=med_y, y1=med_y,
                  line=dict(color="#e4e8ef", width=1, dash="dot"))

    fig.update_layout(
        paper_bgcolor="#ffffff", plot_bgcolor="#ffffff",
        font=dict(family="Inter", color="#5a6577", size=11),
        margin=dict(l=50, r=90, t=20, b=50),
        height=500,
        xaxis=dict(
            title=dict(text="Total Displaced (2024–2026)", font=dict(family="Inter", size=11, color="#5a6577")),
            showgrid=True, gridcolor="#f1f4f9", zeroline=False, showline=False,
            tickfont=dict(family="Inter", size=10),
        ),
        yaxis=dict(
            title=dict(text="Avg Priority Score", font=dict(family="Inter", size=11, color="#5a6577")),
            showgrid=True, gridcolor="#f1f4f9", zeroline=False, showline=False,
            tickfont=dict(family="Inter", size=10),
        ),
        hoverlabel=dict(bgcolor="white", bordercolor="#e4e8ef",
                        font=dict(family="Inter", size=12, color="#1b2230")),
    )
    st.plotly_chart(fig, use_container_width=True, key=f"story_scatter_{cnorm}")

    # Footer callout
    high_pri_low_disp = sdf[
        (sdf["priority_score_country"] >= med_y) & (sdf["displaced_in"] <= med_x)
    ].nlargest(3, "priority_score_country")
    if not high_pri_low_disp.empty:
        names = ", ".join(high_pri_low_disp["display_name"].tolist())
        st.markdown(f"""
        <div style="margin-top:6px;padding:12px 16px;background:#fdf3eb;border-left:3px solid #b8703a;border-radius:0 8px 8px 0;">
          <span style="font-family:'Inter',sans-serif;font-size:12px;color:#7a4418;">
            <strong>Conflict-driven priority:</strong> {names} rank high on priority despite
            relatively lower displacement — driven by conflict intensity and fatalities.
          </span>
        </div>
        """, unsafe_allow_html=True)


def render_displacement_snapshot_bubble_story(
    selected_country_name,
    boundary_gdf,
    snapshot_period=None,
    displacement_mode="latest",
):
    cnorm = canonical_country_norm(selected_country_name)
    disp_in_rows = displacement_dest[displacement_dest["country"] == cnorm].copy()
    pri_rows = admin1_priority[admin1_priority["country_norm"] == cnorm].copy()

    if displacement_mode == "peak":
        disp_agg = get_peak_displacement(disp_in_rows, ["admin1_norm"], "displaced_in")
        pri_slice = filter_to_period(pri_rows, get_latest_period(pri_rows))
        disp_in_hover_label = "Peak displaced"
    else:
        snapshot_period = (
            snapshot_period
            or get_latest_period(disp_in_rows, pri_rows, intersection=True)
            or get_latest_period(disp_in_rows)
            or get_latest_period(pri_rows)
        )
        disp_agg, _ = get_latest_displacement_snapshot(
            disp_in_rows,
            ["admin1_norm"],
            "displaced_in",
            period=snapshot_period,
        )
        pri_slice = filter_to_period(pri_rows, snapshot_period)
        disp_in_hover_label = "Displaced"

    if pri_slice.empty:
        pri_agg = pd.DataFrame(columns=["admin1_norm"])
    else:
        agg_d = {"events": "sum", "fatalities": "sum"}
        for c in ["priority_score_country", "displaced", "population_exposure"]:
            if c in pri_slice.columns:
                agg_d[c] = "mean" if "score" in c else "sum"
        pri_agg = pri_slice.groupby("admin1_norm", as_index=False).agg(agg_d)

    bdf = disp_agg.merge(pri_agg, how="outer", on="admin1_norm")

    name_map = {}
    if boundary_gdf is not None and not boundary_gdf.empty:
        name_map = dict(zip(boundary_gdf["admin_name_norm"], boundary_gdf["admin_name"]))
    bdf["display_name"] = bdf["admin1_norm"].map(name_map).fillna(
        bdf["admin1_norm"].apply(lambda x: str(x).replace("-", " ").title() if pd.notna(x) else "")
    )

    for col in [
        "displaced_in",
        "events",
        "fatalities",
        "priority_score_country",
        "displaced",
        "population_exposure",
    ]:
        if col not in bdf.columns:
            bdf[col] = 0.0
        bdf[col] = pd.to_numeric(bdf[col], errors="coerce").fillna(0.0)

    bdf = bdf[bdf["admin1_norm"].notna() & (bdf["admin1_norm"].astype(str) != "nan")].copy()
    bdf = bdf.sort_values("displaced_in", ascending=False).reset_index(drop=True)

    if bdf.empty:
        st.info("No displacement snapshot data available for this country.")
        return

    max_disp = float(bdf["displaced_in"].max())
    use_priority = max_disp <= 0
    size_col = "priority_score_country" if use_priority else "displaced_in"
    max_v = float(bdf[size_col].max()) or 1.0
    max_diameter, min_diameter = 90.0, 12.0
    bdf["px_d"] = bdf[size_col].apply(
        lambda value: float(max(min_diameter, (max(0.0, value) / max_v) ** 0.5 * max_diameter))
    )

    n = len(bdf)
    golden_angle = math.pi * (3.0 - math.sqrt(5.0))
    spread = max_diameter * 1.65
    bdf["x"] = [spread * math.sqrt(i) * math.cos(i * golden_angle) for i in range(n)]
    bdf["y"] = [spread * math.sqrt(i) * math.sin(i * golden_angle) for i in range(n)]

    all_coords = list(bdf["x"]) + list(bdf["y"])
    axis_r = (max(abs(v) for v in all_coords) + max_diameter + 45) if n > 0 else 300.0

    pri_max = float(max(bdf["priority_score_country"].max(), 0.001))
    bdf["label"] = bdf.apply(
        lambda row: str(row["display_name"]).split()[0] if row["px_d"] >= 36 else "",
        axis=1,
    )

    leg_vals = [max_v, max_v * 0.30, max_v * 0.08]
    leg_ds = [float(max(min_diameter, (v / max_v) ** 0.5 * max_diameter)) for v in leg_vals]
    lx = axis_r * 0.80
    leg_y = [-axis_r * 0.46, -axis_r * 0.62, -axis_r * 0.73]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=bdf["x"],
        y=bdf["y"],
        mode="markers+text",
        marker=dict(
            size=bdf["px_d"],
            sizemode="diameter",
            color=bdf["priority_score_country"],
            colorscale=SCALE_BUBBLE,
            cmin=0.0,
            cmax=pri_max,
            line=dict(width=1.5, color="rgba(255,255,255,0.5)"),
            opacity=0.87,
            colorbar=dict(
                title=dict(text="Priority", font=dict(family="Inter", size=11, color="#1b2230")),
                tickfont=dict(family="Inter", size=9, color="#5a6577"),
                len=0.42,
                thickness=10,
                outlinewidth=0,
                x=1.01,
            ),
        ),
        text=bdf["label"],
        textfont=dict(family="Inter", size=9, color="rgba(255,255,255,0.95)"),
        textposition="middle center",
        customdata=bdf[[
            "display_name",
            "displaced_in",
            "priority_score_country",
            "priority_score_country",
            "events",
            "fatalities",
        ]].values,
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            f"{disp_in_hover_label}: <b>%{{customdata[1]:,.0f}}</b><br>"
            "Priority score: %{customdata[3]:.3f}<br>"
            "Events: %{customdata[4]:,.0f}  ·  Fatalities: %{customdata[5]:,.0f}"
            "<extra></extra>"
        ),
        showlegend=False,
        name="",
    ))
    fig.add_trace(go.Scatter(
        x=[lx, lx, lx],
        y=leg_y,
        mode="markers",
        marker=dict(
            size=leg_ds,
            sizemode="diameter",
            color="rgba(175,188,205,0.40)",
            line=dict(width=1.5, color="#b0b9c7"),
        ),
        hoverinfo="skip",
        showlegend=False,
    ))
    fig.add_trace(go.Scatter(
        x=[axis_r * 0.93, axis_r * 0.93, axis_r * 0.93],
        y=leg_y,
        mode="text",
        text=[fmt_big(v) for v in leg_vals],
        textfont=dict(family="Inter", size=9, color="#8893a4"),
        textposition="middle right",
        hoverinfo="skip",
        showlegend=False,
    ))

    fig.update_layout(
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        font=dict(family="Inter", color="#5a6577", size=11),
        xaxis=dict(visible=False, range=[-axis_r, axis_r], fixedrange=True),
        yaxis=dict(
            visible=False,
            range=[-axis_r, axis_r],
            scaleanchor="x",
            scaleratio=1,
            fixedrange=True,
        ),
        margin=dict(l=10, r=90, t=10, b=10),
        height=580,
        hoverlabel=dict(
            bgcolor="white",
            bordercolor="#e4e8ef",
            font=dict(family="Inter", size=12, color="#1b2230"),
        ),
    )
    st.plotly_chart(fig, use_container_width=True, key=f"bubble_snapshot_{cnorm}")


def render_displacement_snapshot_overview(
    selected_country_name,
    boundary_gdf,
    arrivals_snapshot,
    arrivals_period,
    departures_snapshot=None,
    departures_period=None,
    displacement_mode="latest",
):
    cnorm = canonical_country_norm(selected_country_name)
    total_events_full = float(admin_conflict[admin_conflict["country_norm"] == cnorm]["events"].sum())
    total_fat_full = float(admin_conflict[admin_conflict["country_norm"] == cnorm]["fatalities"].sum())

    total_arrived = float(arrivals_snapshot["displaced_in"].sum()) if not arrivals_snapshot.empty else 0.0
    total_departed = 0.0
    arrivals_label = format_period_label(arrivals_period) or "No snapshot"
    departures_label = ""
    arrived_display = fmt_big(total_arrived) if not arrivals_snapshot.empty else "—"
    departed_display = ""

    if displacement_mode == "peak":
        title = f"Peak displacement snapshot for {selected_country_name}"
        lead_copy = (
            "Peak displaced values are shown by admin1 across the selected range."
        )
        bar_hover_label = "Peak displaced"
    else:
        title = f"Latest displacement snapshot for {selected_country_name}"
        lead_copy = (
            f"Displaced values use the latest stock snapshot in "
            f"<strong style=\"color:#1b2230;\">{arrivals_label}</strong>."
        )
        bar_hover_label = "Displaced"

    st.markdown(f"""
    <div style="padding:20px 0 10px 0;">
      <p style="font-family:'Playfair Display',serif;font-size:22px;font-weight:600;color:#1b2230;line-height:1.4;margin:0 0 10px 0;">
        {title}
      </p>
      <p style="font-family:'Inter',sans-serif;font-size:14px;color:#5a6577;line-height:1.85;margin:0;max-width:680px;">
        {lead_copy}
        Across the cumulative 2024–2026 conflict layer, <strong style="color:#b8703a;">{fmt_big(total_fat_full)}</strong>
        fatalities were recorded across <strong style="color:#2c4a6e;">{fmt_big(total_events_full)}</strong> events.
        The chart below ranks admin areas by the current displaced stock snapshot instead of summing every month together.
      </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div style="display:flex;gap:14px;flex-wrap:wrap;margin:10px 0 22px 0;">
      <div style="background:#e8eef6;border-radius:10px;padding:12px 20px;">
        <div style="font-family:'Inter',sans-serif;font-size:10px;font-weight:600;letter-spacing:.1em;text-transform:uppercase;color:#5a7aa0;margin-bottom:4px;">Displaced</div>
        <div style="font-family:'Playfair Display',serif;font-size:22px;font-weight:700;color:#2c4a6e;">{arrived_display}</div>
        <div style="font-family:'Inter',sans-serif;font-size:11px;color:#5a6577;margin-top:4px;">Latest snapshot · {arrivals_label}</div>
      </div>
      <div style="display:none;background:#fdf3eb;border-radius:10px;padding:12px 20px;">
        <div style="font-family:'Inter',sans-serif;font-size:10px;font-weight:600;letter-spacing:.1em;text-transform:uppercase;color:#b8703a;margin-bottom:4px;"></div>
        <div style="font-family:'Playfair Display',serif;font-size:22px;font-weight:700;color:#b8703a;">{departed_display}</div>
        <div style="font-family:'Inter',sans-serif;font-size:11px;color:#7a4418;margin-top:4px;">Latest snapshot · {departures_label}</div>
      </div>
      <div style="background:#eef1f6;border-radius:10px;padding:12px 20px;">
        <div style="font-family:'Inter',sans-serif;font-size:10px;font-weight:600;letter-spacing:.1em;text-transform:uppercase;color:#5a6577;margin-bottom:4px;">Conflict Events</div>
        <div style="font-family:'Playfair Display',serif;font-size:22px;font-weight:700;color:#1b2230;">{fmt_big(total_events_full)}</div>
        <div style="font-family:'Inter',sans-serif;font-size:11px;color:#5a6577;margin-top:4px;">2024–2026 cumulative</div>
      </div>
      <div style="background:#fdf3eb;border-radius:10px;padding:12px 20px;">
        <div style="font-family:'Inter',sans-serif;font-size:10px;font-weight:600;letter-spacing:.1em;text-transform:uppercase;color:#b8703a;margin-bottom:4px;">Fatalities</div>
        <div style="font-family:'Playfair Display',serif;font-size:22px;font-weight:700;color:#7a4418;">{fmt_big(total_fat_full)}</div>
        <div style="font-family:'Inter',sans-serif;font-size:11px;color:#7a4418;margin-top:4px;">2024–2026 cumulative</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    if arrivals_snapshot.empty:
        st.info("No displacement snapshot data available.")
        return

    disp_agg = arrivals_snapshot.copy()
    name_map = {}
    if boundary_gdf is not None and not boundary_gdf.empty:
        name_map = dict(zip(boundary_gdf["admin_name_norm"], boundary_gdf["admin_name"]))
    disp_agg["display_name"] = disp_agg["admin1_norm"].map(name_map).fillna(
        disp_agg["admin1_norm"].apply(lambda x: str(x).replace("-", " ").title())
    )
    top = disp_agg.sort_values("displaced_in", ascending=False).head(10)

    bar_colors = [
        f"rgba(44,74,110,{max(0.35, 1.0 - i*0.07):.2f})" for i in range(len(top))
    ]

    fig = go.Figure(go.Bar(
        y=top["display_name"][::-1],
        x=top["displaced_in"][::-1],
        orientation="h",
        marker=dict(color=bar_colors[::-1], line=dict(width=0)),
        text=[fmt_big(v) for v in top["displaced_in"][::-1]],
        textposition="inside",
        textfont=dict(family="Inter", size=11, color="rgba(255,255,255,0.9)"),
        hovertemplate=f"<b>%{{y}}</b><br>{bar_hover_label}: %{{x:,.0f}}<extra></extra>",
    ))
    fig.update_layout(
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        font=dict(family="Inter", color="#5a6577", size=11),
        margin=dict(l=10, r=30, t=10, b=30),
        height=max(280, len(top) * 34),
        xaxis=dict(
            showgrid=True,
            gridcolor="#eef1f6",
            gridwidth=1,
            showline=False,
            zeroline=False,
            tickfont=dict(family="Inter", size=10),
        ),
        yaxis=dict(
            showgrid=False,
            showline=False,
            tickfont=dict(family="Inter", size=11, color="#1b2230"),
        ),
        hoverlabel=dict(
            bgcolor="white",
            bordercolor="#e4e8ef",
            font=dict(family="Inter", size=12, color="#1b2230"),
        ),
    )
    st.plotly_chart(fig, use_container_width=True, key=f"story_bar_snapshot_{cnorm}")


def render_displacement_snapshot_priority_scatter(
    selected_country_name,
    boundary_gdf,
    snapshot_period=None,
    displacement_mode="latest",
):
    cnorm = canonical_country_norm(selected_country_name)
    pri_rows = admin1_priority[admin1_priority["country_norm"] == cnorm].copy()
    disp_in_rows = displacement_dest[displacement_dest["country"] == cnorm].copy()
    conflict_rows = admin_conflict[admin_conflict["country_norm"] == cnorm].copy()

    def _aggregate_priority_rows(frame):
        columns = [
            "admin1_norm",
            "events",
            "fatalities",
            "population_exposure",
            "priority_score_country",
            "displaced",
        ]
        if frame is None or frame.empty or "admin1_norm" not in frame.columns:
            return pd.DataFrame(columns=columns)
        work = ensure_numeric_columns(
            frame.copy(),
            ["events", "fatalities", "population_exposure", "priority_score_country", "displaced"],
        )
        agg_d = {}
        for col in ["events", "fatalities", "population_exposure", "displaced"]:
            if col in work.columns:
                agg_d[col] = "sum"
        if "priority_score_country" in work.columns:
            agg_d["priority_score_country"] = "first"
        if not agg_d:
            return pd.DataFrame(columns=columns)
        return work.groupby("admin1_norm", as_index=False).agg(agg_d)

    def _aggregate_conflict_rows(frame, period):
        columns = ["admin1_norm", "events", "fatalities", "population_exposure"]
        if frame is None or frame.empty or "admin1_norm" not in frame.columns:
            return pd.DataFrame(columns=columns)
        work = filter_to_period(frame, period) if period else frame.iloc[0:0].copy()
        if work.empty:
            return pd.DataFrame(columns=columns)
        if "event_type" in work.columns:
            event_norm = work["event_type"].astype(str).str.strip().str.lower()
            all_rows = work[event_norm == "all"].copy()
            if not all_rows.empty:
                work = all_rows
        work = ensure_numeric_columns(work, ["events", "fatalities", "population_exposure"])
        return (
            work.groupby("admin1_norm", as_index=False)
            .agg({"events": "sum", "fatalities": "sum", "population_exposure": "sum"})
        )

    def _fallback_priority_score(frame):
        work = ensure_numeric_columns(
            frame.copy(),
            ["events", "fatalities", "population_exposure", "displaced_in", "displaced"],
        )
        displaced_source = (
            work["displaced_in"]
            if float(work["displaced_in"].sum()) > 0
            else work["displaced"]
        )
        components = [
            (scale_to_max(work["events"]), 0.35),
            (scale_to_max(work["fatalities"]), 0.30),
            (scale_to_max(displaced_source), 0.25),
            (scale_to_max(work["population_exposure"]), 0.10),
        ]
        score = pd.Series(0.0, index=work.index, dtype="float64")
        active_weight = 0.0
        for component, weight in components:
            if float(component.sum()) > 0:
                score = score + component * weight
                active_weight += weight
        if active_weight <= 0:
            return score
        return score / active_weight

    if displacement_mode == "peak":
        disp_agg = get_peak_displacement(disp_in_rows, ["admin1_norm"], "displaced_in")
        priority_period = get_latest_period(pri_rows) or get_latest_period(conflict_rows)
        pri_slice = filter_to_period(pri_rows, priority_period) if priority_period else pd.DataFrame()
        conflict_period = priority_period
        priority_period_text = format_period_label(priority_period)
        period_label = (
            f"peak displacement with priority inputs from {priority_period_text}"
            if priority_period_text else "peak displacement with the latest available priority inputs"
        )
        displacement_hover_label = "Peak displaced"
        xaxis_title = "Peak Displaced"
        yaxis_title = "Latest Priority Score"
    else:
        snapshot_period = (
            snapshot_period
            or get_latest_period(disp_in_rows, pri_rows, intersection=True)
            or get_latest_period(disp_in_rows)
            or get_latest_period(pri_rows)
            or get_latest_period(conflict_rows)
        )
        pri_slice = filter_to_period(pri_rows, snapshot_period) if snapshot_period else pd.DataFrame()
        conflict_period = snapshot_period
        disp_agg, _ = get_latest_displacement_snapshot(
            disp_in_rows,
            ["admin1_norm"],
            "displaced_in",
            period=snapshot_period,
        )
        period_text = format_period_label(snapshot_period)
        period_label = period_text or "the latest available month"
        displacement_hover_label = "Displaced"
        xaxis_title = (
            f"Displaced Snapshot ({period_text})"
            if period_text else "Displaced Snapshot"
        )
        yaxis_title = (
            f"Priority Score Snapshot ({period_text})"
            if period_text else "Priority Score Snapshot"
        )

    if disp_agg is None or disp_agg.empty:
        disp_agg = pd.DataFrame(columns=["admin1_norm", "displaced_in"])

    pri_agg = _aggregate_priority_rows(pri_slice)
    conflict_agg = _aggregate_conflict_rows(conflict_rows, conflict_period)

    sdf = pd.DataFrame({"admin1_norm": pd.Series(dtype="object")})
    for frame in [disp_agg, pri_agg]:
        if frame is not None and not frame.empty:
            sdf = frame.copy() if sdf.empty else sdf.merge(frame, on="admin1_norm", how="outer")
    if not conflict_agg.empty:
        conflict_join = conflict_agg.rename(
            columns={
                "events": "events_conflict",
                "fatalities": "fatalities_conflict",
                "population_exposure": "population_exposure_conflict",
            }
        )
        sdf = conflict_join.copy() if sdf.empty else sdf.merge(conflict_join, on="admin1_norm", how="outer")

    if sdf.empty:
        st.info("No conflict, displacement, or priority rows are available for this snapshot.")
        return

    for metric in ["events", "fatalities", "population_exposure"]:
        base = (
            pd.to_numeric(sdf[metric], errors="coerce")
            if metric in sdf.columns
            else pd.Series(index=sdf.index, dtype="float64")
        )
        conflict_col = f"{metric}_conflict"
        if conflict_col in sdf.columns:
            conflict_values = pd.to_numeric(sdf[conflict_col], errors="coerce")
            sdf[metric] = conflict_values.combine_first(base).fillna(0.0)
            sdf = sdf.drop(columns=[conflict_col])
        else:
            sdf[metric] = base.fillna(0.0)

    name_map = {}
    if boundary_gdf is not None and not boundary_gdf.empty:
        name_map = dict(zip(boundary_gdf["admin_name_norm"], boundary_gdf["admin_name"]))
    sdf["display_name"] = sdf["admin1_norm"].map(name_map).fillna(
        sdf["admin1_norm"].apply(lambda x: str(x).replace("-", " ").title())
    )

    for col in ["displaced_in", "fatalities", "priority_score_country", "population_exposure", "events"]:
        if col not in sdf.columns:
            sdf[col] = 0.0
        sdf[col] = pd.to_numeric(sdf[col], errors="coerce").fillna(0.0)

    fallback_score = _fallback_priority_score(sdf)
    real_score = pd.to_numeric(sdf["priority_score_country"], errors="coerce").fillna(0.0)
    missing_score = real_score <= 0
    fallback_used = bool(float(fallback_score[missing_score].sum()) > 0)
    sdf["priority_score_country"] = real_score.where(~missing_score, fallback_score)
    sdf["score_source"] = "Priority model"
    if fallback_used:
        sdf.loc[missing_score & (fallback_score > 0), "score_source"] = "Estimated from same-period inputs"

    sdf = sdf[sdf["priority_score_country"] > 0].copy()
    if sdf.empty:
        st.info("No conflict, displacement, exposure, or priority signal is available for this snapshot.")
        return

    max_fat = float(sdf["fatalities"].max()) or 1.0
    max_size, min_size = 55.0, 8.0
    sdf["bubble_sz"] = sdf["fatalities"].apply(
        lambda value: float(max(min_size, (max(0, value) / max_fat) ** 0.5 * max_size))
    )

    top_pri = set(sdf.nlargest(3, "priority_score_country")["admin1_norm"])
    top_disp = set(sdf.nlargest(3, "displaced_in")["admin1_norm"])
    highlight = top_pri | top_disp
    sdf["label"] = sdf.apply(
        lambda row: row["display_name"] if row["admin1_norm"] in highlight else "",
        axis=1,
    )

    max_exp = float(sdf["population_exposure"].max()) or 1.0
    score_note = (
        "Precomputed priority scores were missing for some regions, so those scores are estimated from "
        "same-period events, fatalities, displacement, and exposure."
        if fallback_used else
        "Priority scores come from the precomputed priority model for this snapshot."
    )

    st.markdown(f"""
    <div style="padding:20px 0 10px 0;">
      <p style="font-family:'Playfair Display',serif;font-size:22px;font-weight:600;color:#1b2230;line-height:1.4;margin:0 0 10px 0;">
        Why does priority differ across regions?
      </p>
      <p style="font-family:'Inter',sans-serif;font-size:14px;color:#5a6577;line-height:1.85;margin:0;max-width:680px;">
        This chart uses <strong>the latest shared displacement and priority snapshot in {period_label}</strong>.
        Regions with lower displacement can still rank highest if they also face intense conflict,
        high fatality rates, or large population exposure. Each circle is one admin area:
        horizontal position shows displaced people, vertical position shows priority score,
        circle size scales with fatalities, and color reflects population exposure.
        {score_note}
      </p>
    </div>
    """, unsafe_allow_html=True)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=sdf["displaced_in"],
        y=sdf["priority_score_country"],
        mode="markers+text",
        marker=dict(
            size=sdf["bubble_sz"],
            sizemode="diameter",
            color=sdf["population_exposure"],
            colorscale=SCALE_WARM,
            cmin=0,
            cmax=max_exp,
            opacity=0.82,
            line=dict(width=1.2, color="rgba(255,255,255,0.6)"),
            colorbar=dict(
                title=dict(text="Population<br>Exposure", font=dict(family="Inter", size=10, color="#1b2230")),
                tickfont=dict(family="Inter", size=9, color="#5a6577"),
                len=0.5,
                thickness=10,
                outlinewidth=0,
                x=1.01,
            ),
        ),
        text=sdf["label"],
        textfont=dict(family="Inter", size=9, color="#1b2230"),
        textposition="top center",
        customdata=sdf[[
            "display_name",
            "displaced_in",
            "fatalities",
            "priority_score_country",
            "population_exposure",
            "events",
            "score_source",
        ]].values,
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            f"{displacement_hover_label}: <b>%{{customdata[1]:,.0f}}</b><br>"
            "Priority score: <b>%{customdata[3]:.3f}</b><br>"
            "Fatalities: %{customdata[2]:,.0f}<br>"
            "Pop. exposure: %{customdata[4]:,.0f}<br>"
            "Events: %{customdata[5]:,.0f}<br>"
            "Score source: %{customdata[6]}"
            "<extra></extra>"
        ),
        showlegend=False,
    ))

    med_x = float(sdf["displaced_in"].median())
    med_y = float(sdf["priority_score_country"].median())
    x_max = max(float(sdf["displaced_in"].max()) * 1.08, 1.0)
    y_max = max(float(sdf["priority_score_country"].max()) * 1.12, 0.05)

    for xv, yv, lbl, anchor in [
        (x_max * 0.55, y_max * 0.97, "HIGH PRIORITY · HIGH DISPLACEMENT", "center"),
        (x_max * 0.05, y_max * 0.97, "HIGH PRIORITY · LOW DISPLACEMENT", "left"),
        (x_max * 0.55, y_max * 0.04, "LOW PRIORITY · HIGH DISPLACEMENT", "center"),
    ]:
        fig.add_annotation(
            x=xv,
            y=yv,
            text=lbl,
            showarrow=False,
            font=dict(family="Inter", size=8, color="#b0b9c7"),
            xanchor=anchor,
            yanchor="top",
        )

    fig.add_shape(type="line", x0=med_x, x1=med_x, y0=0, y1=y_max,
                  line=dict(color="#e4e8ef", width=1, dash="dot"))
    fig.add_shape(type="line", x0=0, x1=x_max, y0=med_y, y1=med_y,
                  line=dict(color="#e4e8ef", width=1, dash="dot"))

    fig.update_layout(
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        font=dict(family="Inter", color="#5a6577", size=11),
        margin=dict(l=50, r=90, t=20, b=50),
        height=500,
        xaxis=dict(
            title=dict(text=xaxis_title, font=dict(family="Inter", size=11, color="#5a6577")),
            showgrid=True,
            gridcolor="#f1f4f9",
            zeroline=False,
            showline=False,
            tickfont=dict(family="Inter", size=10),
        ),
        yaxis=dict(
            title=dict(text=yaxis_title, font=dict(family="Inter", size=11, color="#5a6577")),
            showgrid=True,
            gridcolor="#f1f4f9",
            zeroline=False,
            showline=False,
            tickfont=dict(family="Inter", size=10),
        ),
        hoverlabel=dict(
            bgcolor="white",
            bordercolor="#e4e8ef",
            font=dict(family="Inter", size=12, color="#1b2230"),
        ),
    )
    st.plotly_chart(fig, use_container_width=True, key=f"story_scatter_snapshot_{cnorm}")

    high_pri_low_disp = sdf[
        (sdf["priority_score_country"] >= med_y) & (sdf["displaced_in"] <= med_x)
    ].nlargest(3, "priority_score_country")
    if not high_pri_low_disp.empty:
        names = ", ".join(high_pri_low_disp["display_name"].tolist())
        st.markdown(f"""
        <div style="margin-top:6px;padding:12px 16px;background:#fdf3eb;border-left:3px solid #b8703a;border-radius:0 8px 8px 0;">
          <span style="font-family:'Inter',sans-serif;font-size:12px;color:#7a4418;">
            <strong>Conflict-driven priority:</strong> {names} rank high on priority despite
            relatively lower displacement in the latest snapshot.
          </span>
        </div>
        """, unsafe_allow_html=True)


def build_mapbox_center(gdf, default_lat=20, default_lon=10):
    if gdf is None or gdf.empty or "geometry" not in gdf.columns:
        return {"lat": default_lat, "lon": default_lon}
    try:
        rp = gdf.geometry.representative_point()
        return {"lat": float(rp.y.mean()), "lon": float(rp.x.mean())}
    except Exception:
        return {"lat": default_lat, "lon": default_lon}

def build_mapbox_zoom(gdf, base_zoom, max_zoom=8.0):
    if gdf is None or gdf.empty or "geometry" not in gdf.columns:
        return base_zoom
    try:
        minx, miny, maxx, maxy = gdf.total_bounds
        span_x = max(float(maxx - minx), 0.15)
        span_y = max(float(maxy - miny), 0.15)
        span = max(span_x, span_y)
        adaptive_zoom = 7.5 - math.log2(span)
        return float(max(base_zoom, min(max_zoom, adaptive_zoom)))
    except Exception:
        return base_zoom

LIGHT_LAYOUT = dict(
    paper_bgcolor="#ffffff",
    plot_bgcolor="#ffffff",
    font=dict(family="Inter", color="#5a6577", size=11),
    title=dict(font=dict(family="Playfair Display", size=16, color="#1b2230"), x=0.02, xanchor="left", y=0.97),
    margin=dict(l=0, r=0, t=50, b=0),
)

SCALE_BLUE  = [[0,"#f4f7fb"],[0.25,"#d2dceb"],[0.5,"#8fa7c9"],[0.75,"#4f6c95"],[1,"#2c4a6e"]]
SCALE_BUBBLE = [[0,"#dce8f4"],[0.25,"#b7cbe1"],[0.5,"#84a4c3"],[0.75,"#4e7098"],[1,"#1a2e48"]]
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
            df["country"].notna() & df["event_type"].notna()].copy()
    df["year"] = df["year"].astype(int)
    df["month_num"] = df["month_num"].astype(int)
    if "iso3" in df.columns:
        df["iso3"] = pd.to_numeric(df["iso3"], errors="coerce")
        df["iso_n3"] = df["iso3"].fillna(0).astype(int).astype(str).str.zfill(3)
    if "admin1" not in df.columns:
        df["admin1"] = hierarchy.UNKNOWN_ADMIN1_LABEL
    df["admin1"] = df["admin1"].where(df["admin1"].notna(), hierarchy.UNKNOWN_ADMIN1_LABEL)
    df["admin1"] = df["admin1"].replace({"nan": hierarchy.UNKNOWN_ADMIN1_LABEL, "None": hierarchy.UNKNOWN_ADMIN1_LABEL, "": hierarchy.UNKNOWN_ADMIN1_LABEL})
    df["country_norm"] = df["country"].apply(canonical_country_norm)
    df["admin1_norm"] = df.apply(lambda row: standardize_admin_name(row["admin1"], row["country"]), axis=1)
    df["admin1_norm"] = df["admin1_norm"].fillna(hierarchy.UNKNOWN_ADMIN1_NORM)
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
        "country_priority_score_base", "country_priority_score", "country_priority_rank",
        "health_priority_score", "health_source_year", "health_indicator_count", "health_data_available",
        "education_priority_score", "education_source_year", "education_indicator_count", "education_data_available",
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
        if gdf["admin_name_norm"].duplicated().any():
            gdf = gdf[["admin_name_norm", "geometry"]].dissolve(by="admin_name_norm", as_index=False)
            gdf = repair_geometries(gdf)
            gdf["admin_name"] = gdf["admin_name_norm"].astype(str).str.replace("-", " ").str.title()
            gdf["admin_name"] = gdf["admin_name"].str.replace("Baalbek Hermel", "Baalbek-Hermel", regex=False)
        gdf = gdf[["admin_name","admin_name_norm","geometry"]].copy()
        return gdf, "admin_name"

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

@st.cache_data(show_spinner=False)
def load_global_admin2_boundaries():
    if not global_admin2_path.exists():
        return gpd.GeoDataFrame(
            columns=["shapeGroup", "shapeName", "geometry"],
            geometry="geometry",
            crs="EPSG:4326",
        )
    gdf = gpd.read_file(global_admin2_path)
    if gdf.crs is None:
        gdf = gdf.set_crs(epsg=4326)
    else:
        gdf = gdf.to_crs(epsg=4326)
    try:
        gdf["geometry"] = gdf["geometry"].simplify(0.01, preserve_topology=True)
    except Exception:
        pass
    gdf = repair_geometries(gdf)
    keep_cols = [col for col in ["shapeGroup", "shapeName", "geometry"] if col in gdf.columns]
    return gdf[keep_cols].copy()

def load_country_admin2_boundary(iso3, boundary_gdf, selected_country_name):
    iso3 = str(iso3 or "").strip().upper()
    if iso3 == "LBN":
        return load_lebanon_admin2_boundary().copy()

    global_admin2 = load_global_admin2_boundaries()
    if global_admin2.empty or "shapeGroup" not in global_admin2.columns:
        return gpd.GeoDataFrame(
            columns=["admin1_name", "admin1_norm", "admin2_name", "admin2_label", "admin2_norm", "area_sqkm", "geometry"],
            geometry="geometry",
            crs="EPSG:4326",
        )

    gdf = global_admin2[global_admin2["shapeGroup"].astype(str).str.strip().str.upper() == iso3].copy()
    if gdf.empty:
        return gpd.GeoDataFrame(
            columns=["admin1_name", "admin1_norm", "admin2_name", "admin2_label", "admin2_norm", "area_sqkm", "geometry"],
            geometry="geometry",
            crs="EPSG:4326",
        )
    gdf = add_area_proxy(gdf)

    gdf["admin2_name"] = gdf["shapeName"].astype(str).str.strip()
    gdf["admin2_norm"] = gdf["admin2_name"].apply(lambda value: standardize_admin2_name(value, selected_country_name))
    gdf["admin2_label"] = gdf["admin2_name"].apply(lambda value: format_admin2_label(value, selected_country_name))
    gdf = gdf[gdf["admin2_norm"].notna()].copy()
    gdf["adm2_row_id"] = range(len(gdf))

    if boundary_gdf is not None and not boundary_gdf.empty:
        admin1_lookup = boundary_gdf[["admin_name", "admin_name_norm", "geometry"]].copy()
        rep_points = gdf[["adm2_row_id", "geometry"]].copy()
        rep_points = gpd.GeoDataFrame(
            rep_points.drop(columns=["geometry"]),
            geometry=gdf.geometry.representative_point(),
            crs=gdf.crs,
        )
        try:
            joined = gpd.sjoin(rep_points, admin1_lookup, how="left", predicate="within")
        except TypeError:
            joined = gpd.sjoin(rep_points, admin1_lookup, how="left", op="within")
        if joined["admin_name_norm"].isna().any():
            missing = joined[joined["admin_name_norm"].isna()][["adm2_row_id", "geometry"]].copy()
            if not missing.empty:
                try:
                    nearest = gpd.sjoin_nearest(missing, admin1_lookup, how="left")
                    joined = pd.concat(
                        [joined[joined["admin_name_norm"].notna()], nearest],
                        ignore_index=True,
                    )
                except Exception:
                    pass
        joined = joined.dropna(subset=["admin_name_norm"]).drop_duplicates(subset=["adm2_row_id"])
        gdf = gdf.merge(
            joined[["adm2_row_id", "admin_name", "admin_name_norm"]],
            on="adm2_row_id",
            how="left",
        )
    else:
        gdf["admin_name"] = pd.NA
        gdf["admin_name_norm"] = pd.NA

    gdf = gdf[gdf["admin_name_norm"].notna()].copy()
    gdf = gdf.rename(columns={"admin_name": "admin1_name", "admin_name_norm": "admin1_norm"})
    return gdf[["admin1_name", "admin1_norm", "admin2_name", "admin2_label", "admin2_norm", "area_sqkm", "geometry"]].copy()

@st.cache_data(show_spinner=False)
def load_lebanon_admin2_boundary():
    if lbn_admin2_clean_path.exists():
        gdf = gpd.read_file(lbn_admin2_clean_path)
        if gdf.crs is None:
            gdf = gdf.set_crs(epsg=4326)
        else:
            gdf = gdf.to_crs(epsg=4326)
        gdf = repair_geometries(gdf)
        gdf = add_area_proxy(gdf)
        gdf["admin1_name"] = gdf["adm1_name"].astype(str).str.strip()
        gdf["admin2_name"] = gdf["adm2_name"].astype(str).str.strip()
        gdf["admin1_norm"] = gdf["admin1_name"].apply(lambda value: standardize_admin_name(value, "Lebanon"))
        gdf["admin2_norm"] = gdf["admin2_name"].apply(standardize_lebanon_admin2_name)
        gdf = gdf[gdf["admin1_norm"].notna() & gdf["admin2_norm"].notna()].copy()
        gdf["admin2_label"] = gdf["admin2_norm"].apply(format_lebanon_admin2_label)
        gdf = gdf[["admin1_name", "admin1_norm", "admin2_name", "admin2_label", "admin2_norm", "area_sqkm", "geometry"]].copy()
        return gdf

    if lbn_admin2_fallback_path.exists():
        gdf = gpd.read_file(lbn_admin2_fallback_path)
        if gdf.crs is None:
            gdf = gdf.set_crs(epsg=4326)
        else:
            gdf = gdf.to_crs(epsg=4326)
        gdf = repair_geometries(gdf)
        gdf = add_area_proxy(gdf)
        gdf["admin2_name"] = gdf["shapeName"].astype(str).str.strip()
        gdf["admin2_norm"] = gdf["admin2_name"].apply(standardize_lebanon_admin2_name)
        gdf["admin1_name"] = gdf["shapeName"].map(DISTRICT_TO_ADMIN1_GEO)
        gdf["admin1_norm"] = gdf["admin1_name"].apply(lambda value: standardize_admin_name(value, "Lebanon"))
        gdf = gdf[gdf["admin1_norm"].notna() & gdf["admin2_norm"].notna()].copy()
        gdf["admin2_label"] = gdf["admin2_norm"].apply(format_lebanon_admin2_label)
        gdf = gdf[["admin1_name", "admin1_norm", "admin2_name", "admin2_label", "admin2_norm", "area_sqkm", "geometry"]].copy()
        return gdf

    return gpd.GeoDataFrame(columns=["admin1_name", "admin1_norm", "admin2_name", "admin2_label", "admin2_norm", "area_sqkm", "geometry"], geometry="geometry", crs="EPSG:4326")

@st.cache_data(show_spinner=False)
def load_lebanon_admin2_conflict():
    if not lbn_admin2_conflict_path.exists():
        return pd.DataFrame(
            columns=[
                "country", "admin1", "admin2", "year", "month_num", "month",
                "event_type", "events", "fatalities", "population_exposure",
                "admin1_norm", "admin2_norm",
            ]
        )
    df = pd.read_csv(lbn_admin2_conflict_path)
    for col in ["country", "admin1", "admin2", "month", "event_type"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
    for col in ["year", "month_num", "events", "fatalities", "population_exposure"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "population_exposure" not in df.columns:
        df["population_exposure"] = 0
    df["country"] = df["country"].astype(str).str.strip().str.lower()
    df = df[df["country"].eq("lebanon")].copy()
    df["admin1_norm"] = df["admin1"].apply(lambda value: standardize_admin_name(value, "Lebanon"))
    df["admin2_norm"] = df["admin2"].apply(standardize_lebanon_admin2_name)
    df["year"] = df["year"].fillna(0).astype(int)
    df["month_num"] = df["month_num"].fillna(0).astype(int)
    df["events"] = df["events"].fillna(0)
    df["fatalities"] = df["fatalities"].fillna(0)
    df["population_exposure"] = df["population_exposure"].fillna(0)
    df = df[
        df["admin1_norm"].notna() &
        df["admin2_norm"].notna() &
        df["year"].between(MIN_YEAR, MAX_YEAR)
    ].copy()
    return df

@st.cache_data(show_spinner=False)
def load_lebanon_admin2_priority():
    if not lbn_admin2_priority_path.exists():
        return pd.DataFrame(
            columns=[
                "admin2_norm", "year", "month_num", "month", "events", "fatalities",
                "priority_score", "priority_rank", "access_risk", "demographic_vulnerability",
                "admin1_norm",
            ]
        )
    df = pd.read_csv(lbn_admin2_priority_path)
    for col in ["admin2_norm", "month"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
    numeric_cols = [
        "year", "month_num", "events", "fatalities", "priority_score", "priority_rank",
        "access_risk", "demographic_vulnerability",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df["admin2_norm"] = df["admin2_norm"].apply(standardize_lebanon_admin2_name)
    boundary = load_lebanon_admin2_boundary()[["admin1_norm", "admin2_norm"]].drop_duplicates()
    df = df.merge(boundary, on="admin2_norm", how="left")
    df["year"] = df["year"].fillna(0).astype(int)
    df["month_num"] = df["month_num"].fillna(0).astype(int)
    df = df[
        df["admin1_norm"].notna() &
        df["admin2_norm"].notna() &
        df["year"].between(MIN_YEAR, MAX_YEAR)
    ].copy()
    return df

@st.cache_data(show_spinner=False)
def load_admin2_conflict_historical():
    if not lbn_admin2_conflict_path.exists():
        return pd.DataFrame(
            columns=[
                "country", "country_norm", "admin1", "admin1_norm", "admin2", "admin2_norm",
                "year", "month_num", "month", "event_type", "events", "fatalities", "population_exposure",
            ]
        )
    df = pd.read_csv(lbn_admin2_conflict_path)
    for col in ["country", "admin1", "admin2", "month", "event_type"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
    for col in ["year", "month_num", "events", "fatalities", "population_exposure"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "population_exposure" not in df.columns:
        df["population_exposure"] = 0
    df["country_norm"] = df["country"].apply(canonical_country_norm)
    df["admin1_norm"] = df.apply(lambda row: standardize_admin_name(row["admin1"], row["country"]), axis=1)
    df["admin2_norm"] = df.apply(lambda row: standardize_admin2_name(row["admin2"], row["country"]), axis=1)
    df["year"] = df["year"].fillna(0).astype(int)
    df["month_num"] = df["month_num"].fillna(0).astype(int)
    df["events"] = pd.to_numeric(df["events"], errors="coerce").fillna(0)
    df["fatalities"] = pd.to_numeric(df["fatalities"], errors="coerce").fillna(0)
    df["population_exposure"] = pd.to_numeric(df["population_exposure"], errors="coerce").fillna(0)
    df = df[
        df["country_norm"].notna() &
        df["admin1_norm"].notna() &
        df["admin2_norm"].notna() &
        df["year"].between(MIN_YEAR, MAX_YEAR)
    ].copy()
    return df

def get_country_admin2_basis_rows(selected_country_name, admin1_norm, target_year, target_month_num, event_type="All"):
    base = load_admin2_conflict_historical().copy()
    country_norm = canonical_country_norm(selected_country_name)
    base = base[base["country_norm"] == country_norm].copy()
    base["event_type_norm"] = base["event_type"].astype(str).str.strip().str.lower()
    candidates = base[
        (base["admin1_norm"] == admin1_norm) &
        (
            (base["year"] < int(target_year)) |
            ((base["year"] == int(target_year)) & (base["month_num"] < int(target_month_num)))
        )
    ].copy()
    if candidates.empty:
        return pd.DataFrame(), None, None

    event_type_norm = str(event_type or "All").strip().lower()
    matching = candidates[candidates["event_type_norm"] == event_type_norm].copy()
    basis_kind = event_type_norm
    if matching.empty and event_type_norm != "all":
        matching = candidates[candidates["event_type_norm"] == "all"].copy()
        basis_kind = "all"
    if matching.empty:
        return pd.DataFrame(), None, None

    same_month = matching[matching["month_num"] == int(target_month_num)].copy()
    if not same_month.empty:
        latest_year = int(same_month["year"].max())
        matching = same_month[same_month["year"] == latest_year].copy()
    else:
        latest_pair = (
            matching[["year", "month_num", "month"]]
            .drop_duplicates()
            .sort_values(["year", "month_num"])
            .iloc[-1]
        )
        matching = matching[
            (matching["year"] == int(latest_pair["year"])) &
            (matching["month_num"] == int(latest_pair["month_num"]))
        ].copy()

    if matching.empty:
        return pd.DataFrame(), None, None

    basis_period = {
        "year": int(matching["year"].iloc[0]),
        "month_num": int(matching["month_num"].iloc[0]),
        "month": str(matching["month"].iloc[0]).strip(),
    }
    return matching, basis_period, basis_kind

def _fill_empty_acled_cols(df):
    df = df.copy()
    df = ensure_numeric_columns(df, ["events", "fatalities", "population_exposure"])
    for col_val in [
        ("has_acled_data", False),
        ("has_acled_data_label", "No"),
        ("acled_match_status", "No data"),
        ("acled_data_note", "No data"),
    ]:
        if col_val[0] not in df.columns:
            df[col_val[0]] = col_val[1]
    return df

def build_country_admin2_conflict_view(country_admin2_boundary, selected_country_name, admin1_norm, selected_year, selected_month, selected_event_type="All"):
    if canonical_country_norm(selected_country_name) == "lebanon":
        boundary = country_admin2_boundary[country_admin2_boundary["admin1_norm"] == admin1_norm].copy()
        if boundary.empty:
            return _fill_empty_acled_cols(boundary), False, None

        month_num = MONTH_MAP.get(str(selected_month).strip(), int(selected_month) if str(selected_month).isdigit() else None)
        if month_num is None:
            return _fill_empty_acled_cols(boundary), False, None

        detail_rows = load_lebanon_admin2_conflict().copy()
        detail_rows = detail_rows[
            (detail_rows["admin1_norm"] == admin1_norm) &
            (detail_rows["year"] == int(selected_year)) &
            (detail_rows["month_num"] == int(month_num))
        ].copy()
        _sel_et = str(selected_event_type or "All").strip()
        if _sel_et == "All":
            _et_rows = detail_rows[detail_rows["event_type"].astype(str).str.strip() == "All"].copy()
            detail_rows = _et_rows if not _et_rows.empty else detail_rows
        else:
            detail_rows = detail_rows[detail_rows["event_type"].astype(str).str.strip() == _sel_et].copy()

        metric_source = (
            detail_rows.groupby("admin2_norm", as_index=False)
            .agg({
                "events": "sum",
                "fatalities": "sum",
                "population_exposure": "sum",
            })
            if not detail_rows.empty
            else pd.DataFrame(columns=["admin2_norm", "events", "fatalities", "population_exposure"])
        )
        merged = boundary.merge(metric_source, on="admin2_norm", how="left")
        merged = ensure_numeric_columns(merged, ["events", "fatalities", "population_exposure"])
        parent_rows = admin_conflict[
            (admin_conflict["country_norm"] == "lebanon") &
            (admin_conflict["admin1_norm"] == admin1_norm) &
            (admin_conflict["year"] == int(selected_year)) &
            (admin_conflict["month_num"] == int(month_num)) &
            (admin_conflict["event_type"].astype(str).str.strip().str.lower() == _sel_et.lower())
        ].copy()
        if parent_rows.empty:
            parent_rows = admin_conflict[
                (admin_conflict["country_norm"] == "lebanon") &
                (admin_conflict["admin1_norm"] == admin1_norm) &
                (admin_conflict["year"] == int(selected_year)) &
                (admin_conflict["month_num"] == int(month_num)) &
                (admin_conflict["event_type"].astype(str).str.strip().str.lower() == "all")
            ].copy()
        parent_values = {
            metric: float(pd.to_numeric(parent_rows[metric], errors="coerce").fillna(0).sum())
            if metric in parent_rows.columns else 0.0
            for metric in ["events", "fatalities", "population_exposure"]
        }
        estimated_from_basis = False
        basis_estimate_note = None
        if detail_rows.empty and any(parent_values.get(metric, 0) > 0 for metric in ["events", "fatalities", "population_exposure"]):
            basis_rows, basis_period, basis_kind = get_country_admin2_basis_rows(
                selected_country_name,
                admin1_norm,
                int(selected_year),
                int(month_num),
                selected_event_type,
            )
            if not basis_rows.empty:
                basis = (
                    basis_rows.groupby("admin2_norm", as_index=False)
                    .agg({
                        "events": "sum",
                        "fatalities": "sum",
                        "population_exposure": "sum",
                    })
                )
                merged = merged.merge(basis, on="admin2_norm", how="left", suffixes=("", "_basis"))
                event_weights = hierarchy.allocation_weights(
                    merged,
                    preferred_cols=[
                        ("events_basis", 0.55),
                        ("fatalities_basis", 0.20),
                        ("population_exposure_basis", 0.15),
                        ("area_sqkm", 0.10),
                    ],
                )
                fatality_weights = hierarchy.allocation_weights(
                    merged,
                    preferred_cols=[
                        ("fatalities_basis", 0.55),
                        ("events_basis", 0.25),
                        ("population_exposure_basis", 0.10),
                        ("area_sqkm", 0.10),
                    ],
                )
                exposure_weights = hierarchy.allocation_weights(
                    merged,
                    preferred_cols=[
                        ("population_exposure_basis", 0.60),
                        ("events_basis", 0.20),
                        ("fatalities_basis", 0.10),
                        ("area_sqkm", 0.10),
                    ],
                )
                merged["events"] = allocate_total_by_weights(parent_values.get("events", 0), event_weights)
                merged["fatalities"] = allocate_total_by_weights(parent_values.get("fatalities", 0), fatality_weights)
                merged["population_exposure"] = allocate_total_by_weights(parent_values.get("population_exposure", 0), exposure_weights)
                estimated_from_basis = True
                basis_label = f"{basis_period['month']} {basis_period['year']}" if basis_period else "the latest observed district period"
                basis_scope = "matching district shares" if basis_kind == _sel_et.lower() else "overall district shares"
                basis_estimate_note = (
                    f"Estimated district breakdown for {selected_month} {selected_year} using {basis_scope} "
                    f"from {basis_label} within {admin1_norm.replace('-', ' ').title()}."
                )
        merged, parent_reconciled = hierarchy.reconcile_children_to_parent(
            merged,
            parent_values,
            ["events", "fatalities", "population_exposure"],
            source_col="acled_data_note",
        )
        parent_reconciled = bool(parent_reconciled or estimated_from_basis)
        merged["has_acled_data"] = (
            (merged["events"] > 0) |
            (merged["fatalities"] > 0) |
            (merged["population_exposure"] > 0)
        )
        if parent_reconciled:
            merged["has_acled_data"] = False
            merged["acled_match_status"] = "Estimated from governorate total"
            merged["acled_data_note"] = "Estimated from governorate total"
        else:
            merged["acled_match_status"] = merged["has_acled_data"].map(
                {True: "Matched admin2 conflict data", False: "No matched events"}
            )
            merged["acled_data_note"] = merged["has_acled_data"].map(
                {True: "Matched admin2 conflict data", False: "No matched events"}
            )
        merged["has_acled_data_label"] = merged["has_acled_data"].map({True: "Yes", False: "No"})
        estimate_note = (
            basis_estimate_note
            if estimated_from_basis else
            f"Estimated district breakdown for {selected_month} {selected_year} from the "
            f"{admin1_norm.replace('-', ' ').title()} governorate total."
            if parent_reconciled else None
        )
        merged["district_estimation_note"] = (
            hierarchy.ESTIMATED_DISTRICT_NOTE if parent_reconciled else ""
        )
        return merged, bool(parent_reconciled), estimate_note

    boundary = country_admin2_boundary[country_admin2_boundary["admin1_norm"] == admin1_norm].copy()
    if boundary.empty:
        return _fill_empty_acled_cols(boundary), False, None

    month_num = MONTH_MAP.get(str(selected_month).strip(), int(selected_month) if str(selected_month).isdigit() else None)
    if month_num is None:
        return _fill_empty_acled_cols(boundary), False, None

    country_norm = canonical_country_norm(selected_country_name)
    event_type_norm = str(selected_event_type or "All").strip().lower()
    detail_rows = load_admin2_conflict_historical().copy()
    detail_rows["event_type_norm"] = detail_rows["event_type"].astype(str).str.strip().str.lower()
    exact = detail_rows[
        (detail_rows["country_norm"] == country_norm) &
        (detail_rows["admin1_norm"] == admin1_norm) &
        (detail_rows["year"] == int(selected_year)) &
        (detail_rows["month_num"] == int(month_num)) &
        (detail_rows["event_type_norm"] == event_type_norm)
    ].copy()

    estimated = False
    estimate_note = None

    if exact.empty:
        total_rows = admin_conflict[
            (admin_conflict["country_norm"] == country_norm) &
            (admin_conflict["admin1_norm"] == admin1_norm) &
            (admin_conflict["year"] == int(selected_year)) &
            (admin_conflict["month_num"] == int(month_num)) &
            (admin_conflict["event_type"].astype(str).str.strip().str.lower() == event_type_norm)
        ].copy()
        if total_rows.empty:
            total_rows = admin_conflict[
                (admin_conflict["country_norm"] == country_norm) &
                (admin_conflict["admin1_norm"] == admin1_norm) &
                (admin_conflict["year"] == int(selected_year)) &
                (admin_conflict["month_num"] == int(month_num)) &
                (admin_conflict["event_type"].astype(str).str.strip().str.lower() == "all")
            ].copy()

        total_events = float(total_rows["events"].sum()) if not total_rows.empty else 0.0
        total_fatalities = float(total_rows["fatalities"].sum()) if not total_rows.empty else 0.0
        total_exposure = float(total_rows["population_exposure"].sum()) if "population_exposure" in total_rows.columns else 0.0

        basis_rows, basis_period, basis_kind = get_country_admin2_basis_rows(
            selected_country_name,
            admin1_norm,
            int(selected_year),
            int(month_num),
            selected_event_type,
        )

        exact = boundary[[col for col in ["admin2_norm", "area_sqkm"] if col in boundary.columns]].drop_duplicates(subset=["admin2_norm"]).copy()
        exact["events"] = 0
        exact["fatalities"] = 0
        exact["population_exposure"] = 0

        if total_events > 0 or total_fatalities > 0 or total_exposure > 0:
            if not basis_rows.empty:
                basis = (
                    basis_rows.groupby("admin2_norm", as_index=False)
                    .agg({
                        "events": "sum",
                        "fatalities": "sum",
                        "population_exposure": "sum",
                    })
                )
                exact = exact.merge(basis, on="admin2_norm", how="left", suffixes=("", "_basis"))
                event_weights = hierarchy.allocation_weights(
                    exact,
                    preferred_cols=[
                        ("events_basis", 0.55),
                        ("fatalities_basis", 0.20),
                        ("population_exposure_basis", 0.15),
                        ("area_sqkm", 0.10),
                    ],
                )
                fatality_weights = hierarchy.allocation_weights(
                    exact,
                    preferred_cols=[
                        ("fatalities_basis", 0.55),
                        ("events_basis", 0.25),
                        ("population_exposure_basis", 0.10),
                        ("area_sqkm", 0.10),
                    ],
                )
                exposure_weights = hierarchy.allocation_weights(
                    exact,
                    preferred_cols=[
                        ("population_exposure_basis", 0.60),
                        ("events_basis", 0.20),
                        ("fatalities_basis", 0.10),
                        ("area_sqkm", 0.10),
                    ],
                )
                basis_label = f"{basis_period['month']} {basis_period['year']}" if basis_period else "the latest observed district period"
                basis_scope = "matching district shares" if basis_kind == event_type_norm else "overall district shares"
                estimate_note = (
                    f"Estimated district breakdown for {selected_month} {selected_year} using {basis_scope} "
                    f"from {basis_label} within {admin1_norm.replace('-', ' ').title()}."
                )
            else:
                event_weights = district_signal_weights(exact)
                fatality_weights = event_weights
                exposure_weights = event_weights
                estimate_note = (
                    f"Estimated district breakdown for {selected_month} {selected_year} using district area or available proxy weights because "
                    f"no district-level basis rows were available within {admin1_norm.replace('-', ' ').title()}."
                )
            exact["events"] = allocate_total_by_weights(total_events, event_weights)
            exact["fatalities"] = allocate_total_by_weights(
                total_fatalities,
                fatality_weights if float(pd.to_numeric(fatality_weights, errors="coerce").fillna(0).sum()) > 0 else event_weights,
            )
            exact["population_exposure"] = allocate_total_by_weights(
                total_exposure,
                exposure_weights if float(pd.to_numeric(exposure_weights, errors="coerce").fillna(0).sum()) > 0 else event_weights,
            )
            exact = exact[["admin2_norm", "events", "fatalities", "population_exposure"]].copy()
            estimated = True

    metric_source = (
        exact.groupby("admin2_norm", as_index=False)
        .agg({
            "events": "sum",
            "fatalities": "sum",
            "population_exposure": "sum",
        })
        if not exact.empty
        else pd.DataFrame(columns=["admin2_norm", "events", "fatalities", "population_exposure"])
    )
    merged = boundary.merge(metric_source, on="admin2_norm", how="left")
    merged = ensure_numeric_columns(merged, ["events", "fatalities", "population_exposure"])
    parent_rows = admin_conflict[
        (admin_conflict["country_norm"] == country_norm) &
        (admin_conflict["admin1_norm"] == admin1_norm) &
        (admin_conflict["year"] == int(selected_year)) &
        (admin_conflict["month_num"] == int(month_num)) &
        (admin_conflict["event_type"].astype(str).str.strip().str.lower() == event_type_norm)
    ].copy()
    if parent_rows.empty:
        parent_rows = admin_conflict[
            (admin_conflict["country_norm"] == country_norm) &
            (admin_conflict["admin1_norm"] == admin1_norm) &
            (admin_conflict["year"] == int(selected_year)) &
            (admin_conflict["month_num"] == int(month_num)) &
            (admin_conflict["event_type"].astype(str).str.strip().str.lower() == "all")
        ].copy()
    parent_values = {
        metric: float(pd.to_numeric(parent_rows[metric], errors="coerce").fillna(0).sum())
        if metric in parent_rows.columns else 0.0
        for metric in ["events", "fatalities", "population_exposure"]
    }
    merged, parent_reconciled = hierarchy.reconcile_children_to_parent(
        merged,
        parent_values,
        ["events", "fatalities", "population_exposure"],
        source_col="acled_data_note",
    )
    if parent_reconciled:
        estimated = True
        if not estimate_note:
            estimate_note = (
                f"Estimated district breakdown for {selected_month} {selected_year} from the "
                f"{admin1_norm.replace('-', ' ').title()} admin1 total."
            )

    if estimated:
        merged["has_acled_data"] = False
        merged["acled_match_status"] = "Estimated from admin1 total"
        merged["acled_data_note"] = "No direct district ACLED data"
        merged["district_estimation_note"] = hierarchy.ESTIMATED_DISTRICT_NOTE
    else:
        merged["has_acled_data"] = (merged["events"] > 0) | (merged["fatalities"] > 0) | (merged["population_exposure"] > 0)
        merged["acled_match_status"] = merged["has_acled_data"].map(
            {True: "Matched admin2 conflict data", False: "No matched events"}
        )
        merged["acled_data_note"] = merged["has_acled_data"].map(
            {True: "Matched admin2 conflict data", False: "No matched events"}
        )
        merged["district_estimation_note"] = ""
    merged["has_acled_data_label"] = merged["has_acled_data"].map({True: "Yes", False: "No"})
    return merged, estimated, estimate_note

def build_country_admin2_priority_view(country_admin2_boundary, selected_country_name, admin1_norm, selected_year, selected_month, admin1_row):
    country_norm = canonical_country_norm(selected_country_name)
    boundary = country_admin2_boundary[country_admin2_boundary["admin1_norm"] == admin1_norm].copy()
    if boundary.empty:
        return boundary, False, None

    def _fill_parent_metric(values, metric, value, reducer="sum"):
        if value is None:
            return
        if isinstance(value, pd.Series):
            numeric = pd.to_numeric(value, errors="coerce").fillna(0)
            filled = float(numeric.mean() if reducer == "mean" else numeric.sum())
        else:
            filled = numeric_value({"value": value}, "value")
        if filled > 0 and numeric_value(values, metric) <= 0:
            values[metric] = filled

    def _supplement_admin1_values(values):
        values = dict(values or {})
        month_num = MONTH_MAP.get(
            str(selected_month).strip(),
            int(selected_month) if str(selected_month).isdigit() else None,
        )
        if month_num is None:
            return values

        pri_rows = admin1_priority[
            (admin1_priority["country_norm"] == country_norm) &
            (admin1_priority["admin1_norm"] == admin1_norm) &
            (admin1_priority["year"] == int(selected_year)) &
            (admin1_priority["month_num"] == int(month_num))
        ].copy()
        if not pri_rows.empty:
            for metric in ["events", "fatalities", "population_exposure", "displaced", "displaced_in"]:
                if metric in pri_rows.columns:
                    _fill_parent_metric(values, metric, pri_rows[metric])
            for metric in ["priority_score_country", "priority_score_global"]:
                if metric in pri_rows.columns:
                    _fill_parent_metric(values, metric, pri_rows[metric], reducer="mean")

        conflict_rows = admin_conflict[
            (admin_conflict["country_norm"] == country_norm) &
            (admin_conflict["admin1_norm"] == admin1_norm) &
            (admin_conflict["year"] == int(selected_year)) &
            (admin_conflict["month_num"] == int(month_num))
        ].copy()
        if not conflict_rows.empty and "event_type" in conflict_rows.columns:
            all_rows = conflict_rows[
                conflict_rows["event_type"].astype(str).str.strip().str.lower() == "all"
            ].copy()
            if not all_rows.empty:
                conflict_rows = all_rows
        if not conflict_rows.empty:
            for metric in ["events", "fatalities", "population_exposure"]:
                if metric in conflict_rows.columns:
                    _fill_parent_metric(values, metric, conflict_rows[metric])

        disp_rows = displacement_dest[
            (displacement_dest["country"] == country_norm) &
            (displacement_dest["admin1_norm"] == admin1_norm) &
            (displacement_dest["year"] == int(selected_year)) &
            (displacement_dest["month_num"] == int(month_num))
        ].copy()
        if not disp_rows.empty and "displaced_in" in disp_rows.columns:
            _fill_parent_metric(values, "displaced_in", disp_rows["displaced_in"])
            _fill_parent_metric(values, "displaced", disp_rows["displaced_in"])
        return values

    conflict_frame, conflict_estimated, conflict_note = build_country_admin2_conflict_view(
        country_admin2_boundary,
        selected_country_name,
        admin1_norm,
        selected_year,
        selected_month,
        "All",
    )
    if conflict_frame.empty:
        exact = boundary[["admin2_norm"]].drop_duplicates().copy()
        exact["events"] = 0
        exact["fatalities"] = 0
        exact["population_exposure"] = 0
        exact["has_acled_data"] = False
        exact["acled_match_status"] = "No matched events"
        exact["acled_data_note"] = "No matched events"
        exact["has_acled_data_label"] = "No"
    else:
        exact = conflict_frame[
            [
                col for col in [
                    "admin2_norm",
                    "events",
                    "fatalities",
                    "population_exposure",
                    "has_acled_data",
                    "acled_match_status",
                    "acled_data_note",
                    "has_acled_data_label",
                ]
                if col in conflict_frame.columns
            ]
        ].copy()
    exact = ensure_numeric_columns(exact, ["events", "fatalities", "population_exposure"])

    merged = boundary.merge(exact, on="admin2_norm", how="left")

    if country_norm == "lebanon":
        static_priority = load_lebanon_admin2_priority().copy()
        if not static_priority.empty:
            month_num = MONTH_MAP.get(str(selected_month).strip(), int(selected_month) if str(selected_month).isdigit() else None)
            period_static = static_priority[
                (static_priority["admin1_norm"] == admin1_norm) &
                (static_priority["year"] == int(selected_year)) &
                (static_priority["month_num"] == int(month_num or 0))
            ].copy()
            if period_static.empty:
                period_static = (
                    static_priority[static_priority["admin1_norm"] == admin1_norm]
                    .sort_values(["year", "month_num"])
                    .drop_duplicates(subset=["admin2_norm"], keep="last")
                    .copy()
                )
            keep_cols = [
                "admin2_norm", "access_risk", "demographic_vulnerability",
                "health_priority_score", "education_priority_score",
            ]
            period_static = period_static[[col for col in keep_cols if col in period_static.columns]].copy()
            if not period_static.empty:
                merged = merged.merge(period_static, on="admin2_norm", how="left", suffixes=("", "_static"))

    merged = ensure_numeric_columns(
        merged,
        [
            "events", "fatalities", "population_exposure", "displaced", "displaced_in",
            "priority_score_country", "priority_score_global", "access_risk",
            "demographic_vulnerability", "health_priority_score", "education_priority_score",
        ],
    )

    admin1_values = _supplement_admin1_values(row_to_values(admin1_row))
    weights = district_signal_weights(merged)
    parent_distributed = False
    for metric in ["events", "fatalities", "population_exposure"]:
        parent_total = numeric_value(admin1_values, metric)
        if parent_total > 0 and float(merged[metric].sum()) <= 0:
            merged[metric] = allocate_total_by_weights(parent_total, weights)
            parent_distributed = True

    weights = district_signal_weights(merged)
    for metric in ["displaced", "displaced_in"]:
        parent_total = numeric_value(admin1_values, metric)
        if parent_total > 0 and float(merged[metric].sum()) <= 0:
            merged[metric] = allocate_total_by_weights(parent_total, weights)
            parent_distributed = True

    weights = district_signal_weights(merged)
    shares = weights / float(weights.sum()) if len(weights) and float(weights.sum()) > 0 else pd.Series(0.0, index=merged.index)
    for metric in ["priority_score_country", "priority_score_global"]:
        parent_value = numeric_value(admin1_values, metric)
        if parent_value > 0 and float(merged[metric].sum()) <= 0:
            merged[metric] = shares * parent_value

    merged, _parent_reconciled = hierarchy.reconcile_children_to_parent(
        merged,
        admin1_values,
        ["events", "fatalities", "population_exposure", "displaced", "displaced_in"],
    )
    parent_distributed = parent_distributed or _parent_reconciled
    if float(merged["displaced"].sum()) <= 0 and float(merged["displaced_in"].sum()) > 0:
        merged["displaced"] = merged["displaced_in"]
        parent_distributed = True
    print(f"[hierarchy validation] Country: {selected_country_name}")
    print(f"[hierarchy validation] Admin1: {admin1_norm}")
    for _metric in ["events", "fatalities", "population_exposure", "displaced", "displaced_in"]:
        _parent_total = numeric_value(admin1_values, _metric)
        _child_total = float(pd.to_numeric(merged[_metric], errors="coerce").fillna(0).sum()) if _metric in merged.columns else 0.0
        print(f"[hierarchy validation] {_metric}: admin1 total={_parent_total:.3f}; admin2 sum={_child_total:.3f}")
    merged = compute_admin2_priority_scores(merged)
    if "has_acled_data" not in merged.columns:
        merged["has_acled_data"] = False
    else:
        merged["has_acled_data"] = merged["has_acled_data"].fillna(False).astype(bool)
    merged["has_acled_data_label"] = merged["has_acled_data"].map({True: "Yes", False: "No"})
    default_status = merged["has_acled_data"].map({True: "Matched admin2 conflict data", False: "No matched events"})
    if "acled_match_status" not in merged.columns:
        merged["acled_match_status"] = default_status
    else:
        merged["acled_match_status"] = merged["acled_match_status"].fillna(default_status)
    if "acled_data_note" not in merged.columns:
        merged["acled_data_note"] = default_status
    else:
        merged["acled_data_note"] = merged["acled_data_note"].fillna(default_status)

    if conflict_estimated or parent_distributed:
        merged["district_value_source"] = "Estimated from admin1 totals"
        merged["district_estimation_note"] = hierarchy.ESTIMATED_DISTRICT_NOTE
    else:
        merged["district_value_source"] = merged["has_acled_data"].map(
            {True: "Matched admin2 data", False: "No matched district data"}
        )
        if "district_estimation_note" not in merged.columns:
            merged["district_estimation_note"] = ""
        else:
            merged["district_estimation_note"] = merged["district_estimation_note"].fillna("")
    merged["displacement_data_note"] = "Displacement estimated from admin1 snapshot totals"

    estimate_bits = []
    if conflict_estimated and conflict_note:
        estimate_bits.append(conflict_note)
    if parent_distributed:
        estimate_bits.append(
            "Some district metrics were estimated from admin1 totals using district conflict, exposure, displacement, or area proxy weights."
        )
    if numeric_value(admin1_values, "displaced") > 0 or numeric_value(admin1_values, "displaced_in") > 0:
        estimate_bits.append("District displacement is estimated from the admin1 snapshot total.")
    estimate_note = " ".join(dict.fromkeys(estimate_bits)) or None
    return merged, bool(conflict_estimated or parent_distributed), estimate_note

def render_lebanon_admin2_drilldown(
    selected_admin1_norm,
    selected_year,
    selected_month,
    country_mode,
    selected_metric,
    selected_event_type=None,
):
    if not selected_admin1_norm:
        return

    boundary = load_lebanon_admin2_boundary()
    admin2_boundary = boundary[boundary["admin1_norm"] == selected_admin1_norm].copy()
    if admin2_boundary.empty:
        return

    selected_admin1_label = admin2_boundary["admin1_name"].astype(str).str.strip().iloc[0]
    header_col, action_col = st.columns([5, 1])
    with header_col:
        st.markdown(
            f'<div class="section-title"><span class="section-dot"></span>{selected_admin1_label} Admin2 Detail</div>',
            unsafe_allow_html=True,
        )
    with action_col:
        if st.button("Back to Admin1", key=f"clear_admin2_{country_mode.lower()}"):
            st.session_state["country_admin1_drilldown"] = None
            st.rerun()

    if country_mode == "Conflict":
        detail_rows = load_lebanon_admin2_conflict()
        detail_rows = detail_rows[
            (detail_rows["admin1_norm"] == selected_admin1_norm) &
            (detail_rows["year"] == selected_year) &
            (detail_rows["month"].str.lower() == str(selected_month).lower())
        ].copy()
        detail_rows = filter_event_type(detail_rows, selected_event_type or "All")
        detail_metric = selected_metric if selected_metric in {"events", "fatalities", "population_exposure"} else "events"
        agg = (
            detail_rows.groupby("admin2_norm", as_index=False)
            .agg({
                "events": "sum",
                "fatalities": "sum",
                "population_exposure": "sum",
            })
            if not detail_rows.empty
            else pd.DataFrame(columns=["admin2_norm", "events", "fatalities", "population_exposure"])
        )
        merged = admin2_boundary.merge(agg, on="admin2_norm", how="left")
        merged = ensure_numeric_columns(merged, ["events", "fatalities", "population_exposure"])

        if detail_rows.empty:
            st.info(
                f"Lebanon admin2 conflict metrics are not available for {selected_month} {selected_year}. "
                f"Showing the districts inside {selected_admin1_label}."
            )

        cscale = SCALE_BLUE if detail_metric == "events" else SCALE_WARM if detail_metric == "fatalities" else SCALE_GOLD
        fig = px.choropleth_mapbox(
            merged,
            geojson=json.loads(merged.to_json()),
            locations="admin2_norm",
            featureidkey="properties.admin2_norm",
            color=detail_metric,
            color_continuous_scale=cscale,
            hover_name="admin2_label",
            hover_data={
                "events": True,
                "fatalities": True,
                "population_exposure": True,
                "admin2_norm": False,
            },
            mapbox_style="carto-positron",
            center=build_mapbox_center(merged),
            zoom=build_mapbox_zoom(merged, base_zoom=6.6, max_zoom=9.8),
            opacity=0.9,
            title=f"{selected_admin1_label} â€” {metric_label(detail_metric)} by Admin2",
        )
        fig.update_layout(**LIGHT_LAYOUT, height=620)
        st.plotly_chart(fig, use_container_width=True, key=f"lbn_admin2_conflict_{selected_admin1_norm}")

        detail_table = (
            merged[["admin2_label", "events", "fatalities", "population_exposure"]]
            .sort_values(detail_metric, ascending=False)
            .rename(columns={
                "admin2_label": "Admin2",
                "events": "Events",
                "fatalities": "Fatalities",
                "population_exposure": "Population Exposure",
            })
            .reset_index(drop=True)
        )
        st.dataframe(detail_table, use_container_width=True, hide_index=True)
        return

    detail_rows = load_lebanon_admin2_priority()
    detail_rows = detail_rows[
        (detail_rows["admin1_norm"] == selected_admin1_norm) &
        (detail_rows["year"] == selected_year) &
        (detail_rows["month"].str.lower() == str(selected_month).lower())
    ].copy()
    detail_metric = selected_metric if selected_metric in {"events", "fatalities"} else "priority_score"
    merged = admin2_boundary.merge(detail_rows, on="admin2_norm", how="left")
    merged = ensure_numeric_columns(
        merged,
        ["events", "fatalities", "priority_score", "priority_rank", "access_risk", "demographic_vulnerability"],
    )

    if detail_rows.empty:
        st.info(
            f"Lebanon admin2 priority metrics are not available for {selected_month} {selected_year}. "
            f"Showing the districts inside {selected_admin1_label}."
        )

    if detail_metric == "priority_score":
        cscale = SCALE_BLUE
    elif detail_metric == "fatalities":
        cscale = SCALE_WARM
    else:
        cscale = SCALE_TEAL

    fig = px.choropleth_mapbox(
        merged,
        geojson=json.loads(merged.to_json()),
        locations="admin2_norm",
        featureidkey="properties.admin2_norm",
        color=detail_metric,
        color_continuous_scale=cscale,
        hover_name="admin2_label",
        hover_data={
            "priority_score": ":.3f",
            "priority_rank": True,
            "events": True,
            "fatalities": True,
            "access_risk": ":.3f",
            "demographic_vulnerability": ":.3f",
            "admin2_norm": False,
        },
        mapbox_style="carto-positron",
        center=build_mapbox_center(merged),
        zoom=build_mapbox_zoom(merged, base_zoom=6.6, max_zoom=9.8),
        opacity=0.9,
        title=f"{selected_admin1_label} â€” {'Priority Score' if detail_metric == 'priority_score' else metric_label(detail_metric)} by Admin2",
    )
    fig.update_layout(**LIGHT_LAYOUT, height=620)
    st.plotly_chart(fig, use_container_width=True, key=f"lbn_admin2_priority_{selected_admin1_norm}")

    detail_table = (
        merged[
            [
                "admin2_label",
                "priority_score",
                "priority_rank",
                "events",
                "fatalities",
                "access_risk",
                "demographic_vulnerability",
            ]
        ]
        .sort_values(detail_metric, ascending=False)
        .rename(columns={
            "admin2_label": "Admin2",
            "priority_score": "Priority Score",
            "priority_rank": "Priority Rank",
            "events": "Events",
            "fatalities": "Fatalities",
            "access_risk": "Access Risk",
            "demographic_vulnerability": "Demographic Vulnerability",
        })
        .reset_index(drop=True)
    )
    detail_table["Priority Score"] = detail_table["Priority Score"].map(lambda value: f"{float(value):.3f}")
    detail_table["Access Risk"] = detail_table["Access Risk"].map(lambda value: f"{float(value):.3f}")
    detail_table["Demographic Vulnerability"] = detail_table["Demographic Vulnerability"].map(lambda value: f"{float(value):.3f}")
    detail_table["Priority Rank"] = detail_table["Priority Rank"].map(lambda value: "â€”" if float(value) <= 0 else str(int(round(float(value)))))
    st.dataframe(detail_table, use_container_width=True, hide_index=True)

# ──────────────────────────────────────────────────
# LOAD DATA
# ──────────────────────────────────────────────────
ensure_required_files()

country_conflict_source = load_country_conflict()
admin_conflict      = load_admin_conflict()
_conflict_metrics = ["events", "fatalities", "population_exposure"]
_conflict_keys = ["country_norm", "year", "month_num", "month", "event_type"]
admin_conflict = hierarchy.reconcile_admin1_with_country_totals(
    admin_conflict,
    country_conflict_source,
    key_cols=_conflict_keys,
    metric_cols=_conflict_metrics,
    admin1_col="admin1_norm",
    admin1_label_col="admin1",
)
country_conflict = hierarchy.aggregate_country_from_admin1(
    admin_conflict,
    key_cols=_conflict_keys,
    metric_cols=_conflict_metrics,
)
_iso_lookup = (
    country_conflict_source[["country_norm", "iso3", "iso_n3", "country"]]
    .drop_duplicates("country_norm")
)
country_conflict = country_conflict.merge(
    _iso_lookup,
    on="country_norm",
    how="left",
    suffixes=("", "_src"),
)
for _col in ["country", "iso3", "iso_n3"]:
    _src = f"{_col}_src"
    if _src in country_conflict.columns:
        if _col in country_conflict.columns:
            country_conflict[_col] = country_conflict[_col].fillna(country_conflict[_src])
        else:
            country_conflict[_col] = country_conflict[_src]
        country_conflict = country_conflict.drop(columns=[_src])
hierarchy.validate_hierarchy_totals(
    country_conflict,
    admin_conflict,
    key_cols=_conflict_keys,
    metric_cols=_conflict_metrics,
    label="country -> admin1 conflict",
)
country_priority    = load_country_priority()
admin1_priority     = load_admin1_priority()
displacement_dest   = load_displacement_dest()
displacement_origin = load_displacement_origin()
world               = load_world()

_priority_metrics = ["events", "fatalities", "population_exposure", "displaced", "displaced_in"]
_priority_keys = ["country_norm", "year", "month_num", "month"]
admin1_priority = hierarchy.reconcile_admin1_with_country_totals(
    admin1_priority,
    country_priority,
    key_cols=_priority_keys,
    metric_cols=_priority_metrics,
    admin1_col="admin1_norm",
    admin1_label_col=None,
)
_country_priority_raw = hierarchy.aggregate_country_from_admin1(
    admin1_priority,
    key_cols=_priority_keys,
    metric_cols=_priority_metrics,
)
country_priority = country_priority.merge(
    _country_priority_raw[_priority_keys + [col for col in _priority_metrics if col in _country_priority_raw.columns]],
    on=_priority_keys,
    how="left",
    suffixes=("", "_hier"),
)
for _metric in _priority_metrics:
    _hier_col = f"{_metric}_hier"
    if _hier_col in country_priority.columns:
        country_priority[_metric] = pd.to_numeric(country_priority[_hier_col], errors="coerce").fillna(
            hierarchy.numeric_series(country_priority, _metric)
        )
        country_priority = country_priority.drop(columns=[_hier_col])
hierarchy.validate_hierarchy_totals(
    country_priority,
    admin1_priority,
    key_cols=_priority_keys,
    metric_cols=[col for col in _priority_metrics if col in country_priority.columns and col in admin1_priority.columns],
    label="country -> admin1 priority inputs",
)

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
    ("country_admin1_drilldown", None),
    ("country_map_level","admin1"),
    ("show_intro", True),
]
for key, default in defaults:
    if key not in st.session_state:
        st.session_state[key] = default

if "world_year" not in st.session_state or "world_month" not in st.session_state:
    y, m = default_latest_period_with_year_bounds(country_conflict)
    st.session_state["world_year"] = y
    st.session_state["world_month"] = m

_intro_query_open = st.query_params.get("open_dashboard", None)
if _intro_query_open in ("1", ["1"]):
    st.session_state["show_intro"] = False
    try:
        del st.query_params["open_dashboard"]
    except Exception:
        pass

_intro_query_app = st.query_params.get("open_app", None)
if _intro_query_app in ("1", ["1"]):
    st.session_state["show_intro"] = False
    try:
        del st.query_params["open_app"]
    except Exception:
        pass
    for page_path in ("scripts/app.py", "app.py", "scripts/pages/dashboard.py", "pages/dashboard.py"):
        try:
            st.switch_page(page_path)
        except Exception:
            continue

# ──────────────────────────────────────────────────
# INTRO SCREEN
# ──────────────────────────────────────────────────
if st.session_state["show_intro"]:
    story_stats = {
        "latest_label": f"{default_latest_period_with_year_bounds(country_conflict)[1]} {default_latest_period_with_year_bounds(country_conflict)[0]}",
        "top_conflict_country": "the world",
        "top_conflict_events": "0",
        "top_conflict_fatalities": "0",
        "priority_country": "the world",
        "priority_score": "0.000",
        "population_exposure": fmt_big(0),
        "health_area": "Lebanon",
        "health_signal": "0.000",
        "total_events": fmt_big(int(country_conflict["events"].sum())),
        "total_fatalities": fmt_big(int(country_conflict["fatalities"].sum())),
        "total_displaced": fmt_big(float(displacement_dest["displaced_in"].sum()) if not displacement_dest.empty else 0.0),
        "country_count": str(int(country_conflict["country"].nunique())),
    }

    intro_year, intro_month = default_latest_period_with_year_bounds(country_conflict)
    story_stats["latest_label"] = f"{intro_month} {intro_year}"

    intro_conflict_latest = country_conflict[
        (country_conflict["year"] == intro_year) &
        (country_conflict["month"].str.lower() == intro_month.lower())
    ].copy()
    if not intro_conflict_latest.empty:
        intro_conflict_latest = (
            intro_conflict_latest.groupby("country", as_index=False)
            .agg({"events": "sum", "fatalities": "sum"})
            .sort_values(["events", "fatalities"], ascending=[False, False])
        )
        story_stats["top_conflict_country"] = str(intro_conflict_latest.iloc[0]["country"])
        story_stats["top_conflict_events"] = fmt_big(intro_conflict_latest.iloc[0]["events"])
        story_stats["top_conflict_fatalities"] = fmt_big(intro_conflict_latest.iloc[0]["fatalities"])

    intro_priority_latest = country_priority[
        (country_priority["year"] == intro_year) &
        (country_priority["month"].str.lower() == intro_month.lower())
    ].copy()
    if not intro_priority_latest.empty:
        intro_priority_scores = (
            intro_priority_latest.groupby("country", as_index=False)
            .agg({"country_priority_score": "mean", "population_exposure": "sum"})
            .sort_values(["country_priority_score", "population_exposure"], ascending=[False, False])
        )
        if not intro_priority_scores.empty:
            story_stats["priority_country"] = str(intro_priority_scores.iloc[0]["country"])
            story_stats["priority_score"] = f"{float(intro_priority_scores.iloc[0]['country_priority_score']):.3f}"
        story_stats["population_exposure"] = fmt_big(float(intro_priority_latest["population_exposure"].sum()))

    intro_health_path = BASE_DIR / "data" / "cleaned" / "lebanon" / "lebanon_priority_admin1_enhanced.csv"
    if intro_health_path.exists():
        intro_health_df = pd.read_csv(intro_health_path)
        for col in ["year", "month_num", "hospital_access_risk", "access_risk"]:
            if col in intro_health_df.columns:
                intro_health_df[col] = pd.to_numeric(intro_health_df[col], errors="coerce")
        intro_health_df = intro_health_df[
            intro_health_df["year"].notna() & intro_health_df["month_num"].notna()
        ].copy()
        if not intro_health_df.empty:
            intro_health_df["year"] = intro_health_df["year"].astype(int)
            intro_health_df["month_num"] = intro_health_df["month_num"].astype(int)
            intro_health_df = intro_health_df.sort_values(["year", "month_num"])
            intro_health_latest = intro_health_df.iloc[-1]
            intro_health_slice = intro_health_df[
                (intro_health_df["year"] == int(intro_health_latest["year"])) &
                (intro_health_df["month_num"] == int(intro_health_latest["month_num"]))
            ].copy()
            intro_health_col = "hospital_access_risk" if "hospital_access_risk" in intro_health_slice.columns else "access_risk"
            if intro_health_col in intro_health_slice.columns and not intro_health_slice.empty:
                intro_health_slice = intro_health_slice.sort_values(intro_health_col, ascending=False)
                story_stats["health_area"] = str(intro_health_slice.iloc[0]["admin1_norm"]).replace("-", " ").title()
                story_stats["health_signal"] = f"{float(intro_health_slice.iloc[0][intro_health_col]):.3f}"

    # Update the asset constants at the top of the file to swap video/images later.
    intro_video_uri = file_to_data_uri(str(INTRO_VIDEO_PATH)) if INTRO_VIDEO_PATH else None
    intro_image_uris = {
        key: file_to_data_uri(str(path))
        for key, path in INTRO_IMAGE_PATHS.items()
    }

    st.markdown("""
<style>
[data-testid="stSidebar"]      { display: none !important; }
[data-testid="stToolbar"]      { display: none !important; }
[data-testid="stDecoration"]   { display: none !important; }
[data-testid="stStatusWidget"] { display: none !important; }
header[data-testid="stHeader"] { display: none !important; }
footer                         { display: none !important; }
#MainMenu                      { display: none !important; }
html, body,
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
section.main,
.main .block-container {
    background: #071627 !important;
    padding: 0 !important;
    max-width: 100% !important;
}
.block-container {
    padding: 0 !important;
}
[data-testid="stVerticalBlock"] > [style*="flex-direction: column;"] > [data-testid="stIFrame"] {
    border: 0 !important;
    box-shadow: none !important;
}
div[data-testid="stButton"] > button {
    background: rgba(255,255,255,0.08) !important;
    border: 1px solid rgba(245,244,239,0.22) !important;
    color: #f5f4ef !important;
    font-family: Inter, "Helvetica Neue", Arial, sans-serif !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    letter-spacing: 0.18em !important;
    text-transform: uppercase !important;
    padding: 17px 32px !important;
                        margin-top: -20px;
    border-radius: 999px !important;
    min-width: 290px !important;
    cursor: pointer !important;
    transition: transform 180ms ease, background 180ms ease, border-color 180ms ease !important;
    box-shadow: none !important;
}
div[data-testid="stButton"] > button:hover {
    background: rgba(255,255,255,0.12) !important;
    border-color: rgba(245,244,239,0.34) !important;
    transform: translateY(-1px) !important;
}
</style>
""", unsafe_allow_html=True)

    components.html(
        build_intro_story_html(intro_video_uri, intro_image_uris, story_stats),
        height=INTRO_STORY_MOTION["component_height_px"],
        scrolling=True,
    )
    st.markdown("<div style='margin-top:8px;'></div>", unsafe_allow_html=True)
    _btn_col = st.columns([3, 2, 3])[1]
    with _btn_col:
        if st.button("Enter Dashboard →", key="enter_dashboard", use_container_width=True):
            st.session_state["show_intro"] = False
            st.rerun()
    st.stop()

if False and st.session_state["show_intro"]:
    _story_total_ev = int(country_conflict["events"].sum())
    _story_total_fat = int(country_conflict["fatalities"].sum())
    _story_total_disp = float(displacement_dest["displaced_in"].sum()) if not displacement_dest.empty else 0.0
    _story_country_count = int(country_conflict["country"].nunique())
    _story_year, _story_month = default_latest_period_with_year_bounds(country_conflict)
    _story_label = f"{_story_month} {_story_year}"

    _story_conflict_latest = country_conflict[
        (country_conflict["year"] == _story_year) &
        (country_conflict["month"].str.lower() == _story_month.lower())
    ].copy()
    _story_conflict_latest = (
        _story_conflict_latest.groupby("country", as_index=False)
        .agg({"events": "sum", "fatalities": "sum"})
        .sort_values(["events", "fatalities"], ascending=[False, False])
    )
    if _story_conflict_latest.empty:
        _story_top_conflict_country = "the world"
        _story_top_conflict_events = 0
        _story_top_conflict_fatalities = 0
    else:
        _story_top_conflict_country = str(_story_conflict_latest.iloc[0]["country"])
        _story_top_conflict_events = int(_story_conflict_latest.iloc[0]["events"])
        _story_top_conflict_fatalities = int(_story_conflict_latest.iloc[0]["fatalities"])

    _story_priority_latest = country_priority[
        (country_priority["year"] == _story_year) &
        (country_priority["month"].str.lower() == _story_month.lower())
    ].copy()
    _story_priority_country = "the world"
    _story_priority_score = 0.0
    _story_population_exposure = 0.0
    if not _story_priority_latest.empty:
        _story_priority_scores = (
            _story_priority_latest.groupby("country", as_index=False)
            .agg({"country_priority_score": "mean", "population_exposure": "sum"})
            .sort_values(["country_priority_score", "population_exposure"], ascending=[False, False])
        )
        if not _story_priority_scores.empty:
            _story_priority_country = str(_story_priority_scores.iloc[0]["country"])
            _story_priority_score = float(_story_priority_scores.iloc[0]["country_priority_score"])
        _story_population_exposure = float(_story_priority_latest["population_exposure"].sum())

    _story_lbn_path = BASE_DIR / "data" / "cleaned" / "lebanon" / "lebanon_priority_admin1_enhanced.csv"
    _story_health_area = "Lebanon"
    _story_health_risk = 0.0
    if _story_lbn_path.exists():
        _story_lbn = pd.read_csv(_story_lbn_path)
        for _col in ["year", "month_num", "hospital_access_risk", "access_risk"]:
            if _col in _story_lbn.columns:
                _story_lbn[_col] = pd.to_numeric(_story_lbn[_col], errors="coerce")
        _story_lbn = _story_lbn[
            _story_lbn["year"].notna() &
            _story_lbn["month_num"].notna()
        ].copy()
        if not _story_lbn.empty:
            _story_lbn["year"] = _story_lbn["year"].astype(int)
            _story_lbn["month_num"] = _story_lbn["month_num"].astype(int)
            _story_lbn = _story_lbn.sort_values(["year", "month_num"])
            _story_lbn_latest = _story_lbn.iloc[-1]
            _story_lbn_slice = _story_lbn[
                (_story_lbn["year"] == int(_story_lbn_latest["year"])) &
                (_story_lbn["month_num"] == int(_story_lbn_latest["month_num"]))
            ].copy()
            _story_health_col = "hospital_access_risk" if "hospital_access_risk" in _story_lbn_slice.columns else "access_risk"
            if _story_health_col in _story_lbn_slice.columns and not _story_lbn_slice.empty:
                _story_lbn_slice = _story_lbn_slice.sort_values(_story_health_col, ascending=False)
                _story_health_area = str(_story_lbn_slice.iloc[0]["admin1_norm"]).replace("-", " ").title()
                _story_health_risk = float(_story_lbn_slice.iloc[0][_story_health_col])

    st.markdown("""
<style>
[data-testid="stSidebar"]      { display: none !important; }
[data-testid="stToolbar"]      { display: none !important; }
[data-testid="stDecoration"]   { display: none !important; }
[data-testid="stStatusWidget"] { display: none !important; }
header[data-testid="stHeader"] { display: none !important; }
footer                         { display: none !important; }
#MainMenu                      { display: none !important; }
html, body,
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
section.main,
.main .block-container {
    background: #ffffff !important;
    padding: 0 !important;
    max-width: 100% !important;
}
.block-container {
    padding: 0 !important;
}
.story-page {
    width: 100%;
    overflow: hidden;
    background: #ffffff;
}
.story-masthead {
    background: #ffffff;
    text-align: center;
    padding: 28px 20px 22px 20px;
    border-bottom: 1px solid rgba(27,34,48,0.08);
}
.story-masthead-title {
    font-family: 'Inter', 'Helvetica Neue', Arial, sans-serif;
    font-size: 18px;
    font-weight: 500;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: #111827;
}
.story-masthead-meta {
    margin-top: 8px;
    font-family: 'Inter', 'Helvetica Neue', Arial, sans-serif;
    font-size: 11px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #7b8190;
}
.story-panel {
    position: relative;
    min-height: 88vh;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 60px 26px;
}
.story-panel-light {
    background:
        radial-gradient(circle at 15% 20%, rgba(44, 74, 110, 0.08), transparent 24%),
        radial-gradient(circle at 85% 30%, rgba(90, 122, 160, 0.08), transparent 28%),
        #ffffff;
    color: #171c24;
}
.story-panel-dark {
    background:
        radial-gradient(circle at 64% 42%, rgba(122, 155, 196, 0.26), transparent 18%),
        radial-gradient(circle at 32% 70%, rgba(44, 74, 110, 0.34), transparent 22%),
        linear-gradient(180deg, #122a45 0%, #163556 55%, #1a3b5f 100%);
    color: #ffffff;
}
.story-panel-inner {
    width: min(1120px, 100%);
}
.story-panel-narrow {
    width: min(900px, 100%);
    margin: 0 auto;
}
.story-kicker {
    font-family: 'Inter', 'Helvetica Neue', Arial, sans-serif;
    font-size: 11px;
    font-weight: 500;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: rgba(255,255,255,0.74);
    margin-bottom: 18px;
}
.story-panel-light .story-kicker {
    color: #2c4a6e;
}
.story-title {
    margin: 0 0 20px 0;
    font-family: 'Inter', 'Helvetica Neue', Arial, sans-serif;
    font-size: clamp(48px, 6vw, 72px);
    font-weight: 500;
    line-height: 1.02;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}
.story-panel-light .story-title {
    color: #171c24;
}
.story-copy {
    max-width: 760px;
    margin: 0;
    font-family: 'Inter', 'Helvetica Neue', Arial, sans-serif;
    font-size: 18px;
    font-weight: 400;
    line-height: 1.8;
    letter-spacing: 0.01em;
    color: rgba(255,255,255,0.72);
}
.story-panel-light .story-copy {
    color: #4f5666;
}
.story-bigline {
    margin: 0 0 18px 0;
    font-family: 'Inter', 'Helvetica Neue', Arial, sans-serif;
    font-size: clamp(34px, 4.6vw, 56px);
    font-weight: 500;
    line-height: 1.08;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}
.story-panel-light .story-bigline {
    color: #111827;
}
.story-metric-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 18px;
    margin-top: 34px;
}
.story-metric-card {
    background: rgba(255,255,255,0.7);
    border: 1px solid rgba(23,28,36,0.08);
    border-radius: 22px;
    padding: 22px 20px;
    box-shadow: 0 10px 28px rgba(26, 33, 48, 0.05);
}
.story-metric-label {
    font-family: 'Inter', 'Helvetica Neue', Arial, sans-serif;
    font-size: 10px;
    font-weight: 500;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: #7b8190;
    margin-bottom: 12px;
}
.story-metric-value {
    font-family: 'Inter', 'Helvetica Neue', Arial, sans-serif;
    font-size: clamp(28px, 3vw, 40px);
    font-weight: 500;
    line-height: 1;
    letter-spacing: 0.02em;
    color: #111827;
}
.story-metric-note {
    margin-top: 8px;
    font-family: 'Inter', 'Helvetica Neue', Arial, sans-serif;
    font-size: 13px;
    line-height: 1.7;
    color: #61697a;
}
.story-quote-box {
    max-width: 900px;
    padding: 46px 48px;
    border: 1px solid rgba(255,255,255,0.08);
    background: rgba(255,255,255,0.03);
    backdrop-filter: blur(8px);
    box-shadow: 0 18px 48px rgba(0, 0, 0, 0.22);
}
.story-quote {
    margin: 0;
    font-family: 'Inter', 'Helvetica Neue', Arial, sans-serif;
    font-size: clamp(28px, 3vw, 40px);
    font-weight: 300;
    line-height: 1.45;
    letter-spacing: 0.03em;
    text-transform: uppercase;
    color: rgba(255,255,255,0.96);
}
.story-quote-source {
    margin-top: 18px;
    font-family: 'Inter', 'Helvetica Neue', Arial, sans-serif;
    font-size: 12px;
    font-weight: 500;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: rgba(255,255,255,0.48);
}
.story-split {
    display: grid;
    grid-template-columns: 1.05fr 0.95fr;
    gap: 34px;
    align-items: center;
}
.story-paint {
    min-height: 340px;
    border-radius: 34px;
    background:
        radial-gradient(circle at 36% 44%, rgba(44, 74, 110, 0.88), transparent 26%),
        radial-gradient(circle at 58% 30%, rgba(90, 122, 160, 0.72), transparent 16%),
        radial-gradient(circle at 52% 56%, rgba(26, 46, 72, 0.78), transparent 14%),
        linear-gradient(135deg, rgba(248, 251, 255, 0.98), rgba(240, 245, 251, 0.92));
    box-shadow: inset 0 0 0 1px rgba(23,28,36,0.05), 0 18px 40px rgba(26, 33, 48, 0.06);
}
.story-narrative-card {
    background: rgba(255,255,255,0.72);
    border: 1px solid rgba(23,28,36,0.08);
    border-radius: 24px;
    padding: 30px 30px 28px 30px;
    box-shadow: 0 14px 34px rgba(26, 33, 48, 0.05);
}
.story-narrative-card h3 {
    margin: 0 0 12px 0;
    font-family: 'Inter', 'Helvetica Neue', Arial, sans-serif;
    font-size: clamp(28px, 3vw, 40px);
    font-weight: 500;
    line-height: 1.08;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #111827;
}
.story-narrative-card p {
    margin: 0;
    font-family: 'Inter', 'Helvetica Neue', Arial, sans-serif;
    font-size: 17px;
    line-height: 1.8;
    color: #4f5666;
}
.story-lens-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 18px;
    margin-top: 34px;
}
.story-lens {
    min-height: 240px;
    padding: 24px 22px;
    border-radius: 24px;
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    box-shadow: 0 16px 38px rgba(0, 0, 0, 0.2);
}
.story-lens-number {
    font-family: 'Inter', 'Helvetica Neue', Arial, sans-serif;
    font-size: 11px;
    font-weight: 500;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: rgba(255,255,255,0.42);
    margin-bottom: 14px;
}
.story-lens h4 {
    margin: 0 0 12px 0;
    font-family: 'Inter', 'Helvetica Neue', Arial, sans-serif;
    font-size: 26px;
    font-weight: 500;
    line-height: 1.08;
    letter-spacing: 0.07em;
    text-transform: uppercase;
    color: #ffffff;
}
.story-lens p {
    margin: 0;
    font-family: 'Inter', 'Helvetica Neue', Arial, sans-serif;
    font-size: 16px;
    line-height: 1.8;
    color: rgba(255,255,255,0.68);
}
.story-lens strong {
    color: #f4f7fb;
}
.story-final-note {
    margin: 28px auto 0 auto;
    max-width: 760px;
    font-family: 'Inter', 'Helvetica Neue', Arial, sans-serif;
    font-size: 17px;
    line-height: 1.8;
    color: rgba(255,255,255,0.74);
}
.story-final-cta {
    display: flex;
    justify-content: center;
    margin-top: 28px;
}
.story-final-button {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 290px;
    padding: 16px 34px;
    border-radius: 999px;
    background: #2c4a6e;
    border: 1px solid #2c4a6e;
    color: #ffffff !important;
    text-decoration: none !important;
    font-family: 'Inter', 'Helvetica Neue', Arial, sans-serif;
    font-size: 13px;
    font-weight: 500;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    box-shadow: 0 14px 28px rgba(26, 46, 72, 0.28);
    transition: all 0.18s ease;
}
.story-final-button:hover {
    background: #1a2e48;
    border-color: #1a2e48;
    transform: translateY(-1px);
}
@media (max-width: 900px) {
    .story-panel {
        min-height: auto;
        padding: 44px 20px;
    }
    .story-metric-grid,
    .story-lens-grid,
    .story-split {
        grid-template-columns: 1fr;
    }
    .story-quote-box,
    .story-narrative-card {
        padding: 24px 22px;
    }
}
</style>
""", unsafe_allow_html=True)

    st.markdown(f"""
<div class="story-page">
  <section class="story-masthead">
    <div class="story-masthead-title">Conflict, Priority, Education &amp; Health</div>
    <div class="story-masthead-meta">Story opening inspired by a scrollytelling structure &middot; Updated April 18, 2026</div>
  </section>

  <section class="story-panel story-panel-dark">
    <div class="story-panel-inner story-panel-narrow">
      <div class="story-kicker">Global Humanitarian Story</div>
      <h1 class="story-title">Conflict does not stop at the frontline.<br>It travels into <em style="color:#8fa7c9;">priority</em>, classrooms, and care.</h1>
      <p class="story-copy">
        This opening page reframes the dashboard as a narrative: violence first appears as events and fatalities,
        then grows into displacement, rising priority, pressure on education, and harder access to health services.
        The data below follows that chain from the global picture to the local choices responders have to make.
      </p>
    </div>
  </section>

  <section class="story-panel story-panel-light">
    <div class="story-panel-inner">
      <p class="story-bigline">Thousands of incidents continue to reshape humanitarian need.</p>
      <p class="story-copy">
        In <strong style="color:#111827;">{_story_label}</strong>, the heaviest concentration of recorded conflict events in the dashboard was
        <strong style="color:#111827;">{_story_top_conflict_country}</strong>, with <strong style="color:#111827;">{fmt_big(_story_top_conflict_events)}</strong> events and
        <strong style="color:#111827;">{fmt_big(_story_top_conflict_fatalities)}</strong> fatalities. But violence is only the first signal.
        Priority grows where conflict overlaps with displacement, exposed populations, and weaker access to essential services.
      </p>
      <div class="story-metric-grid">
        <div class="story-metric-card">
          <div class="story-metric-label">Conflict Events</div>
          <div class="story-metric-value">{fmt_big(_story_total_ev)}</div>
          <div class="story-metric-note">Recorded across {_story_country_count} countries in the current global layer.</div>
        </div>
        <div class="story-metric-card">
          <div class="story-metric-label">Fatalities</div>
          <div class="story-metric-value">{fmt_big(_story_total_fat)}</div>
          <div class="story-metric-note">The most visible and immediate human cost of conflict.</div>
        </div>
        <div class="story-metric-card">
          <div class="story-metric-label">Total Displacement Movements</div>
          <div class="story-metric-value">{fmt_big(_story_total_disp)}</div>
          <div class="story-metric-note">{CUMULATIVE_DISPLACEMENT_NOTE}</div>
        </div>
        <div class="story-metric-card">
          <div class="story-metric-label">Population Exposure</div>
          <div class="story-metric-value">{fmt_big(_story_population_exposure)}</div>
          <div class="story-metric-note">Exposure is a bridge between conflict intensity and service pressure.</div>
        </div>
      </div>
    </div>
  </section>

  <section class="story-panel story-panel-dark">
    <div class="story-panel-inner">
      <div class="story-quote-box">
        <p class="story-quote">
          "Every spike in conflict can ripple outward into displacement, interrupted learning,
          delayed treatment, and new pockets of humanitarian urgency. A useful story has to connect all of those layers, not just count incidents."
        </p>
        <div class="story-quote-source">Project framing</div>
      </div>
    </div>
  </section>

  <section class="story-panel story-panel-light">
    <div class="story-panel-inner">
      <div class="story-split">
        <div class="story-paint"></div>
        <div class="story-narrative-card">
          <div class="story-kicker">Why This First Page Matters</div>
          <h3>A story before the filters</h3>
          <p>
            The reference page you shared works because it opens with feeling, then adds evidence, then invites exploration.
            This version follows the same rhythm for your project: first the scale of conflict, then the logic of priority,
            then the pressure on education and health, and only after that the full interactive dashboard.
          </p>
        </div>
      </div>
    </div>
  </section>

  <section class="story-panel story-panel-dark">
    <div class="story-panel-inner">
      <div class="story-kicker">Four Lenses</div>
      <h2 class="story-title" style="font-size:clamp(34px,4vw,58px);">Telling the story through conflict, priority, education, and health.</h2>
      <div class="story-lens-grid">
        <div class="story-lens">
          <div class="story-lens-number">01 / Conflict</div>
          <h4>Where violence concentrates</h4>
          <p><strong>{_story_top_conflict_country}</strong> leads the latest conflict month in the global layer, reminding us that the story begins with where violence is recorded most intensely.</p>
        </div>
        <div class="story-lens">
          <div class="story-lens-number">02 / Priority</div>
          <h4>Where response becomes urgent</h4>
          <p><strong>{_story_priority_country}</strong> currently carries the highest country priority signal in the monthly layer with a score of <strong>{_story_priority_score:.3f}</strong>.</p>
        </div>
        <div class="story-lens">
          <div class="story-lens-number">03 / Education</div>
          <h4>Where daily life is interrupted</h4>
          <p>When exposed populations rise, schooling is usually one of the first routines to fracture. Here, <strong>{fmt_big(_story_population_exposure)}</strong> exposed people frame the likely pressure on learning continuity in the latest month.</p>
        </div>
        <div class="story-lens">
          <div class="story-lens-number">04 / Health</div>
          <h4>Where access gets harder</h4>
          <p>In the Lebanon service-access layer, <strong>{_story_health_area}</strong> shows the highest latest health-risk signal at <strong>{_story_health_risk:.3f}</strong>, showing how priority is shaped by care access, not only by conflict counts.</p>
        </div>
      </div>
      <p class="story-final-note">
        The guided story sets the frame first. The dashboard comes next, where you can move through countries, months,
        admin1 areas, displacement patterns, and priority rankings in detail.
      </p>
      <div class="story-final-cta">
        <a class="story-final-button" href="?open_dashboard=1">Open the Dashboard</a>
      </div>
    </div>
  </section>
</div>
""", unsafe_allow_html=True)

    st.stop()

    _total_ev   = int(country_conflict["events"].sum())
    _total_fat  = int(country_conflict["fatalities"].sum())
    _total_disp = float(displacement_dest["displaced_in"].sum()) if not displacement_dest.empty else 0.0
    _n_ctry     = int(country_conflict["country"].nunique())

    st.markdown("""
<style>
[data-testid="stSidebar"]            { display: none !important; }
[data-testid="stToolbar"]            { display: none !important; }
[data-testid="stDecoration"]         { display: none !important; }
[data-testid="stStatusWidget"]       { display: none !important; }
header[data-testid="stHeader"]       { display: none !important; }
footer                               { display: none !important; }
#MainMenu                            { display: none !important; }
html, body,
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
section.main,
.main .block-container              {
    background: #000 !important;
    padding: 0 !important;
    max-width: 100% !important;
}
.block-container { padding: 0 !important; }

.intro-wrap {
    position: relative;
    min-height: 100vh;
    width: 100%;
    background: #000;
    display: flex;
    flex-direction: column;
    justify-content: center;
    overflow: hidden;
}
.intro-grid-bg {
    position: absolute;
    inset: 0;
    background-image:
        linear-gradient(rgba(44,74,110,0.07) 1px, transparent 1px),
        linear-gradient(90deg, rgba(44,74,110,0.07) 1px, transparent 1px);
    background-size: 48px 48px;
    z-index: 0;
}
.intro-glow {
    position: absolute;
    width: 700px; height: 700px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(44,74,110,0.18) 0%, transparent 70%);
    top: -180px; left: -180px;
    z-index: 0;
}
.intro-glow2 {
    position: absolute;
    width: 500px; height: 500px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(184,112,58,0.10) 0%, transparent 70%);
    bottom: -120px; right: -120px;
    z-index: 0;
}
.intro-content {
    position: relative;
    z-index: 1;
    max-width: 820px;
    padding: 80px 60px 60px 60px;
}
.intro-eyebrow {
    font-family: 'Inter', sans-serif;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: rgba(44,74,110,0.9);
    margin-bottom: 28px;
    display: flex;
    align-items: center;
    gap: 12px;
}
.intro-eyebrow::before {
    content: '';
    display: inline-block;
    width: 28px; height: 1px;
    background: rgba(44,74,110,0.7);
}
.intro-headline {
    font-family: 'Playfair Display', serif;
    font-size: clamp(38px, 5.5vw, 68px);
    font-weight: 700;
    color: #ffffff;
    line-height: 1.08;
    letter-spacing: -0.025em;
    margin: 0 0 32px 0;
}
.intro-headline em {
    color: #7a9bc4;
    font-style: italic;
}
.intro-lead {
    font-family: 'Inter', sans-serif;
    font-size: 16px;
    font-weight: 400;
    color: rgba(255,255,255,0.55);
    line-height: 1.8;
    max-width: 600px;
    margin: 0 0 52px 0;
}
.intro-stats {
    display: flex;
    gap: 0;
    margin-bottom: 56px;
    border-left: 1px solid rgba(255,255,255,0.08);
}
.intro-stat {
    padding: 0 36px 0 36px;
    border-right: 1px solid rgba(255,255,255,0.08);
}
.intro-stat-val {
    font-family: 'Playfair Display', serif;
    font-size: 32px;
    font-weight: 700;
    color: #ffffff;
    line-height: 1;
    margin-bottom: 8px;
}
.intro-stat-lbl {
    font-family: 'Inter', sans-serif;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: rgba(255,255,255,0.35);
}
.intro-divider {
    width: 56px; height: 1px;
    background: rgba(44,74,110,0.6);
    margin-bottom: 40px;
}

/* Style the Streamlit button as the dark CTA */
div[data-testid="stButton"] > button {
    background: transparent !important;
    border: 1px solid rgba(255,255,255,0.28) !important;
    color: #ffffff !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    letter-spacing: 0.12em !important;
    text-transform: uppercase !important;
    padding: 16px 40px !important;
    border-radius: 3px !important;
    cursor: pointer !important;
    transition: all 0.3s ease !important;
}
div[data-testid="stButton"] > button:hover {
    background: rgba(44,74,110,0.3) !important;
    border-color: rgba(44,74,110,0.9) !important;
    transform: translateY(-2px) !important;
}
</style>
""", unsafe_allow_html=True)

    st.markdown(f"""
<div class="intro-wrap">
  <div class="intro-grid-bg"></div>
  <div class="intro-glow"></div>
  <div class="intro-glow2"></div>
  <div class="intro-content">
    <div class="intro-eyebrow">Conflict & Priority Intelligence &nbsp;·&nbsp; 2024–2026</div>
    <h1 class="intro-headline">
      Millions of people are <em>displaced</em><br>
      by conflict every year.
    </h1>
    <p class="intro-lead">
      This dashboard maps the human cost of armed conflict — tracking displacement flows,
      fatality counts, and humanitarian priority scores across admin1 regions worldwide,
      from January 2024 through 2026.
    </p>
    <div class="intro-stats">
      <div class="intro-stat">
        <div class="intro-stat-val">{fmt_big(_total_ev)}</div>
        <div class="intro-stat-lbl">Conflict Events</div>
      </div>
      <div class="intro-stat">
        <div class="intro-stat-val">{fmt_big(_total_fat)}</div>
        <div class="intro-stat-lbl">Fatalities</div>
      </div>
      <div class="intro-stat">
        <div class="intro-stat-val">{fmt_big(_total_disp)}</div>
        <div class="intro-stat-lbl">Displacement Movements</div>
      </div>
      <div class="intro-stat">
        <div class="intro-stat-val">{_n_ctry}</div>
        <div class="intro-stat-lbl">Countries</div>
      </div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

    if st.button("Explore the Data  →", key="intro_enter"):
        st.session_state["show_intro"] = False
        st.rerun()

    st.stop()

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
            "country_admin1_drilldown": None,
            "country_map_level": "admin1",
        })
        st.rerun()

    base_df = source_df.copy()
    if selected_country != "All":
        cnorm = canonical_country_norm(selected_country)
        base_df = base_df[base_df["country_norm"] == cnorm].copy()

    st.sidebar.markdown('<div class="sidebar-section">Period</div>', unsafe_allow_html=True)
    world_periods = build_available_periods(base_df)
    world_years = sorted(world_periods["year"].dropna().unique().tolist())
    if not world_years:
        st.warning("No years available.")
        st.stop()

    if st.session_state["world_year"] not in world_years:
        latest_year, latest_month = default_latest_period_with_year_bounds(world_periods)
        st.session_state["world_year"] = latest_year
        st.session_state["world_month"] = latest_month

    selected_year = st.sidebar.selectbox(
        "Year",
        world_years,
        index=world_years.index(st.session_state["world_year"])
              if st.session_state["world_year"] in world_years else len(world_years) - 1,
    )
    st.session_state["world_year"] = selected_year

    avail_months = (
        world_periods[world_periods["year"] == selected_year][["month_num","month"]]
        .drop_duplicates()
        .sort_values("month_num")
    )
    month_list = avail_months["month"].tolist()
    if not month_list:
        st.warning("No months available.")
        st.stop()

    if st.session_state["world_month"] not in month_list:
        st.session_state["world_month"] = month_list[-1]

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
                    "country_admin1_drilldown": None,
                    "country_map_level": "admin1",
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
                zoom=build_mapbox_zoom(sgeo, base_zoom=3.2, max_zoom=7.2),
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
                    "country_admin1_drilldown": None,
                    "country_map_level": "admin1",
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
            [
                "country_priority_score",
                "health_priority_score",
                "education_priority_score",
                "events",
                "fatalities",
                "displaced",
                "population_exposure",
            ],
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
                "displaced":"sum",
                "country_priority_score":"mean",
                "country_priority_rank":"min",
                "health_priority_score":"mean",
                "education_priority_score":"mean",
            })
        )
        cname_lk = filtered.groupby("country_norm", as_index=False)["country"].first()
        world_pri = world_pri.merge(cname_lk, how="left", on="country_norm")

        merged_w = world.merge(world_pri, how="left", on="country_norm")
        for col in [
            "events", "fatalities", "population_exposure", "displaced",
            "country_priority_score", "health_priority_score", "education_priority_score",
        ]:
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
            <div class="kpi-label">Displacement Snapshot</div>
            <div class="kpi-value">{fmt_big(total_disp)}</div>
            <div class="kpi-sub">Latest snapshot · {selected_month} {selected_year}</div>
          </div>
          <div class="kpi-card gold">
            <div class="kpi-accent"></div>
            <div class="kpi-label">Priority Countries</div>
            <div class="kpi-value">{ctry_count}</div>
            <div class="kpi-sub">With priority score</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        cscale = SCALE_BLUE if is_score_metric(metric) else SCALE_WARM if metric == "fatalities" else SCALE_TEAL if metric == "displaced" else SCALE_GOLD if metric == "population_exposure" else SCALE_BLUE

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
                    "country_priority_score":":.3f",
                    "health_priority_score":":.3f",
                    "education_priority_score":":.3f",
                    "iso_n3":False,"iso_a3":False
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
                    "country_admin1_drilldown": None,
                    "country_map_level": "admin1",
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
                    "country_priority_score":":.3f",
                    "health_priority_score":":.3f",
                    "education_priority_score":":.3f",
                    "iso_n3":False,"iso_a3":False
                },
                custom_data=["iso_a3","country_name_geo"],
                mapbox_style="carto-positron",
                zoom=build_mapbox_zoom(sgeo, base_zoom=3.2, max_zoom=7.2),
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
                    "country_admin1_drilldown": None,
                    "country_map_level": "admin1",
                })
                st.rerun()

        comparison_source = country_priority[
            (country_priority["year"] == selected_year) &
            (country_priority["month"].str.lower() == selected_month.lower())
        ].copy()
        comparison_source["country"] = comparison_source["country"].astype(str).str.strip()
        world_name_lookup = world.set_index("country_norm")["country_name_geo"].to_dict()
        comparison_source["country_label"] = comparison_source["country_norm"].map(world_name_lookup).fillna(
            comparison_source["country"].astype(str).str.replace("-", " ").str.title()
        )
        comparison_options = (
            comparison_source.sort_values(["country_priority_score", "country_label"], ascending=[False, True])["country_label"]
            .dropna()
            .drop_duplicates()
            .tolist()
        )

        st.markdown(
            '<div class="section-title"><span class="section-dot"></span>Worldwide Country Comparison</div>',
            unsafe_allow_html=True,
        )
        if len(comparison_options) < 2:
            st.info("At least two countries with priority data are needed to build the comparison radar for this period.")
        else:
            current_compare = [
                country for country in st.session_state.get("world_compare_countries", [])
                if country in comparison_options
            ]
            if len(current_compare) < 2:
                current_compare = comparison_options[:min(2, len(comparison_options))]
            st.session_state["world_compare_countries"] = current_compare[:5]

            selected_compare_countries = st.multiselect(
                "Select up to 5 countries to compare",
                comparison_options,
                key="world_compare_countries",
                max_selections=5,
            )

            if len(selected_compare_countries) < 2:
                st.info("Select at least 2 countries to compare.")
            else:
                radar_payload = prepare_radar_comparison_data(
                    comparison_source,
                    selected_year,
                    selected_month,
                    selected_compare_countries,
                    None,
                )
                if radar_payload["wide_df"].empty:
                    st.info("No comparison data is available for the selected countries in this period.")
                else:
                    radar_fig = build_country_comparison_radar(radar_payload["wide_df"], None)
                    st.plotly_chart(
                        radar_fig,
                        use_container_width=True,
                        key=f"world_country_comparison_{selected_year}_{selected_month}",
                    )

        st.markdown(
            f'<div class="section-title"><span class="section-dot"></span>Top 10 by {metric_label(metric)}</div>',
            unsafe_allow_html=True
        )
        top = world_pri.sort_values(metric, ascending=False).head(10).reset_index(drop=True)
        pfmt = lambda v: format_metric_value(metric, v)
        render_top10_grid(top, "country", metric, fmt_fn=pfmt)

# ──────────────────────────────────────────────────
# COUNTRY VIEW
# ──────────────────────────────────────────────────
else:
    selected_iso3 = st.session_state["selected_iso3"]
    selected_country_name = st.session_state["selected_country_name"]
    selected_country_norm = canonical_country_norm(selected_country_name)

    if not selected_iso3 or not selected_country_name:
        st.session_state.update({
            "view": "world",
            "world_country": "All",
            "selected_iso3": None,
            "selected_country_name": None,
            "country_admin1_drilldown": None,
            "country_map_level": "admin1",
        })
        st.rerun()

    st.sidebar.markdown('<div class="sidebar-section">Navigation</div>', unsafe_allow_html=True)
    _in_country_district_view = bool(st.session_state.get("country_admin1_drilldown"))
    if _in_country_district_view:
        if st.sidebar.button(f"← Back to {selected_country_name} Map"):
            st.session_state["country_admin1_drilldown"] = None
            st.session_state["country_map_level"] = "admin1"
            st.rerun()
    else:
        if st.sidebar.button("← Back to World Map"):
            st.session_state.update({
                "view": "world",
                "world_country": "All",
                "selected_iso3": None,
                "selected_country_name": None,
                "country_admin1_drilldown": None,
                "country_map_level": "admin1",
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

    country_admin2_boundary = load_country_admin2_boundary(
        selected_iso3,
        boundary_gdf,
        selected_country_name,
    )
    has_country_admin2 = not country_admin2_boundary.empty
    if not has_country_admin2:
        st.session_state["country_admin1_drilldown"] = None
        st.session_state["country_map_level"] = "admin1"

    country_conflict_rows = get_country_admin_rows(admin_conflict, selected_country_name)
    country_conflict_country_rows = get_country_admin_rows(country_conflict, selected_country_name)
    country_priority_rows = get_country_admin_rows(admin1_priority, selected_country_name)

    if country_conflict_rows.empty and country_conflict_country_rows.empty and country_priority_rows.empty:
        st.warning("No admin-level data found for this country.")
        st.stop()

    st.sidebar.markdown('<div class="sidebar-section">Country View</div>', unsafe_allow_html=True)
    country_mode = st.sidebar.radio("Mode", ["Conflict", "Priority"], horizontal=True)

    selected_country_norm = canonical_country_norm(selected_country_name)
    priority_periods = build_available_periods(
        country_priority_rows,
        displacement_dest[displacement_dest["country"] == selected_country_norm],
        displacement_origin[displacement_origin["country"] == selected_country_norm],
    )
    conflict_periods = build_available_periods(
        country_conflict_rows,
        country_conflict_country_rows,
    )
    available_source = (
        conflict_periods
        if country_mode == "Conflict"
        else priority_periods
    )
    if available_source.empty:
        available_source = (
            conflict_periods
            if not conflict_periods.empty
            else priority_periods
        )
    avail_years = sorted(available_source["year"].dropna().unique().tolist())

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

    month_source = (
        available_source[available_source["year"] == selected_year][["month_num", "month"]]
        .drop_duplicates()
        .sort_values("month_num")
    )
    month_list = month_source["month"].tolist()
    if not month_list:
        st.warning("No months available.")
        st.stop()

    if st.session_state["country_month"] not in month_list:
        st.session_state["country_month"] = month_list[-1]

    selected_month = st.sidebar.selectbox(
        "Month",
        month_list,
        index=month_list.index(st.session_state["country_month"])
              if st.session_state["country_month"] in month_list else len(month_list)-1,
    )
    st.session_state["country_month"] = selected_month

    st.markdown(f"""
    <div class="dash-header">
      <div>
        <div class="dash-title"><span class="accent">{selected_country_name}</span> Admin1 Analysis</div>
        <div class="dash-subtitle">{selected_month} {selected_year} &nbsp;·&nbsp; {country_mode} View</div>
      </div>
      <div class="dash-badge">{selected_iso3}</div>
    </div>
    """, unsafe_allow_html=True)

    selected_country_priority_country_rows = get_country_admin_rows(
        country_priority,
        selected_country_name,
    )
    selected_country_priority_row = get_country_priority_period_row(
        selected_country_priority_country_rows,
        selected_year,
        selected_month,
    )
    selected_country_conflict_country_row = get_country_priority_period_row(
        country_conflict_country_rows,
        selected_year,
        selected_month,
    )

    if country_mode == "Conflict":
        conflict_period_rows = country_conflict_rows[
            (country_conflict_rows["year"] == selected_year) &
            (country_conflict_rows["month"].str.lower() == selected_month.lower())
        ].copy()
        country_conflict_period_rows = country_conflict_country_rows[
            (country_conflict_country_rows["year"] == selected_year) &
            (country_conflict_country_rows["month"].str.lower() == selected_month.lower())
        ].copy()
        event_type_values = []
        for source_df in (conflict_period_rows, country_conflict_period_rows):
            if source_df.empty or "event_type" not in source_df.columns:
                continue
            for event_type in source_df["event_type"].dropna().astype(str).str.strip().tolist():
                if not event_type or event_type.lower() == "nan" or event_type in event_type_values:
                    continue
                event_type_values.append(event_type)
        avail_event_types = ["All"] + sorted([event_type for event_type in event_type_values if event_type != "All"])

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

        if selected_event_type == "All":
            _map_slice = conflict_period_rows[
                conflict_period_rows["event_type"].astype(str).str.strip() == "All"
            ].copy()
            if _map_slice.empty:
                _map_slice = conflict_period_rows.copy()
        else:
            _map_slice = conflict_period_rows[
                conflict_period_rows["event_type"].astype(str).str.strip() == selected_event_type
            ].copy()

        if not _map_slice.empty and "admin1" in _map_slice.columns:
            _map_slice = _map_slice.copy()
            _map_slice["admin1_norm"] = _map_slice.apply(
                lambda r: standardize_admin_name(r["admin1"], r.get("country", "Lebanon")),
                axis=1,
            )
            _map_slice = _map_slice[_map_slice["admin1_norm"].notna()].copy()

        conflict_slice = _map_slice
        country_conflict_period_filtered = filter_event_type(
            country_conflict_period_rows,
            selected_event_type,
        )
        has_admin_conflict_data = not conflict_slice.empty

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

        total_ev = int(conflict_slice["events"].sum()) if not conflict_slice.empty else int(merged["events"].sum())
        total_fat = int(conflict_slice["fatalities"].sum()) if not conflict_slice.empty else int(merged["fatalities"].sum())
        total_exp = float(conflict_slice["population_exposure"].sum()) if not conflict_slice.empty and "population_exposure" in conflict_slice.columns else float(merged["population_exposure"].sum())
        conflict_total_subtitle = "Admin1 aggregation incl. Unknown"

        if not has_admin_conflict_data and not country_conflict_period_filtered.empty:
            total_ev = int(country_conflict_period_filtered["events"].sum())
            total_fat = int(country_conflict_period_filtered["fatalities"].sum())
            total_exp = float(
                country_conflict_period_filtered["population_exposure"].sum()
                if "population_exposure" in country_conflict_period_filtered.columns
                else 0
            )
            conflict_total_subtitle = "Country-level total"

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
            <div class="kpi-sub">{conflict_total_subtitle}</div>
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
            zoom=build_mapbox_zoom(merged, base_zoom=5.0, max_zoom=8.4),
            opacity=0.88,
            title=f"{selected_country_name} — {metric_label(selected_metric)} by {'Governorate' if selected_country_norm == 'lebanon' else 'Admin1'}",
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
        if has_country_admin2:
            _country_drilldown = st.session_state.get("country_admin1_drilldown")
            st.session_state["country_map_level"] = "admin2" if _country_drilldown else "admin1"
            if _country_drilldown:
                _a1_match = country_admin2_boundary[country_admin2_boundary["admin1_norm"] == _country_drilldown]
                _admin1_display = (
                    str(_a1_match["admin1_name"].iloc[0])
                    if not _a1_match.empty
                    else _country_drilldown.replace("-", " ").title()
                )
                st.markdown(
                    f'<div style="font-family:Inter,sans-serif;font-size:13px;color:#5a6577;'
                    f'margin-bottom:10px;padding:8px 14px;background:#eef1f6;border-radius:8px;">'
                    f'Viewing districts inside <strong style="color:#1b2230;">{_admin1_display}</strong></div>',
                    unsafe_allow_html=True,
                )
                _admin2_gdf, _estimated, _estimate_note = build_country_admin2_conflict_view(
                    country_admin2_boundary,
                    selected_country_name,
                    _country_drilldown,
                    selected_year,
                    selected_month,
                    selected_event_type,
                )
                if _estimated and _estimate_note:
                    st.info(_estimate_note)
                if _admin2_gdf.empty:
                    st.warning(f"No admin2 boundary data found for {_admin1_display}.")
                if "district_estimation_note" not in _admin2_gdf.columns:
                    _admin2_gdf["district_estimation_note"] = ""
                else:
                    _admin2_gdf["district_estimation_note"] = _admin2_gdf["district_estimation_note"].fillna("")
                _detail_metric = selected_metric if selected_metric in {"events", "fatalities", "population_exposure"} else "events"
                _detail_scale = SCALE_BLUE if _detail_metric == "events" else SCALE_WARM if _detail_metric == "fatalities" else SCALE_GOLD
                _fig2 = px.choropleth_mapbox(
                    _admin2_gdf,
                    geojson=json.loads(_admin2_gdf.to_json()),
                    locations="admin2_norm",
                    featureidkey="properties.admin2_norm",
                    color=_detail_metric,
                    color_continuous_scale=_detail_scale,
                    hover_name="admin2_label",
                    hover_data={
                        "has_acled_data_label": True,
                        "acled_data_note": True,
                        "acled_match_status": True,
                        "events": True,
                        "fatalities": True,
                        "population_exposure": True,
                        "district_estimation_note": True,
                        "admin2_norm": False,
                    },
                    mapbox_style="carto-positron",
                    center=build_mapbox_center(_admin2_gdf),
                    zoom=build_mapbox_zoom(_admin2_gdf, base_zoom=6.6, max_zoom=9.8),
                    opacity=0.9,
                    labels={
                        "has_acled_data_label": "ACLED District Data",
                        "acled_data_note": "District Data Note",
                        "acled_match_status": "Match Method",
                        "population_exposure": "Population Exposure",
                        "district_estimation_note": "Estimate Note",
                    },
                    title=f"{_admin1_display} — {metric_label(_detail_metric)} by District",
                )
                _fig2.update_layout(
                    **LIGHT_LAYOUT,
                    height=800,
                    coloraxis_colorbar=dict(
                        title=metric_label(_detail_metric),
                        tickfont=dict(family="Inter", size=10, color="#5a6577"),
                        title_font=dict(family="Inter", size=11, color="#1b2230"),
                    ),
                )
                st.plotly_chart(_fig2, use_container_width=True, key="country_conflict_map")
                st.markdown(
                    f'<div class="section-title"><span class="section-dot"></span>Top {_admin1_display} Districts by {metric_label(_detail_metric)}</div>',
                    unsafe_allow_html=True,
                )
                _top_d = (
                    _admin2_gdf[_admin2_gdf[_detail_metric] > 0]
                    .sort_values(_detail_metric, ascending=False)[["admin2_label", _detail_metric]]
                    .head(10)
                    .reset_index(drop=True)
                )
                if _top_d.empty:
                    st.info(f"No districts with {metric_label(_detail_metric).lower()} above 0 for this period.")
                else:
                    render_top10_grid(_top_d, "admin2_label", _detail_metric, fmt_fn=fmt_big)
            else:
                event = st.plotly_chart(
                    fig,
                    use_container_width=True,
                    on_select="rerun",
                    selection_mode=("points",),
                    key="country_conflict_map",
                )
                clicked_admin1 = extract_selected_map_location(event)
                if clicked_admin1 and clicked_admin1 != _country_drilldown:
                    st.session_state["country_admin1_drilldown"] = clicked_admin1
                    st.session_state["country_map_level"] = "admin2"
                    st.rerun()
                st.caption(
                    "Click a governorate to zoom into its admin2 districts."
                    if selected_country_norm == "lebanon"
                    else "Click an admin1 area to zoom into its admin2 districts."
                )
                st.markdown(
                    f'<div class="section-title"><span class="section-dot"></span>'
                    f'{"Top Governorates" if selected_country_norm == "lebanon" else "Top Admin1"} by {metric_label(selected_metric)}</div>',
                    unsafe_allow_html=True
                )
                top_admin = (
                    merged[merged[selected_metric] > 0]
                    .sort_values(selected_metric, ascending=False)[["admin_name", selected_metric]]
                    .head(10)
                    .reset_index(drop=True)
                )
                if top_admin.empty:
                    if not has_admin_conflict_data and selected_country_conflict_country_row is not None:
                        st.info("Admin1 conflict data is unavailable for this period, so no admin-level ranking can be shown yet.")
                    else:
                        st.info(f"No admin areas with {metric_label(selected_metric).lower()} above 0 for this period.")
                else:
                    render_top10_grid(top_admin, "admin_name", selected_metric, fmt_fn=fmt_big)
        else:
            st.plotly_chart(fig, use_container_width=True, key="country_conflict_map")

            st.markdown(
                f'<div class="section-title"><span class="section-dot"></span>Top Admin1 by {metric_label(selected_metric)}</div>',
                unsafe_allow_html=True
            )
            top_admin = (
                merged[merged[selected_metric] > 0]
                .sort_values(selected_metric, ascending=False)[["admin_name", selected_metric]]
                .head(10)
                .reset_index(drop=True)
            )
            if top_admin.empty:
                if not has_admin_conflict_data and selected_country_conflict_country_row is not None:
                    st.info("Admin1 conflict data is unavailable for this period, so no admin-level ranking can be shown yet.")
                else:
                    st.info(f"No admin areas with {metric_label(selected_metric).lower()} above 0 for this period.")
            else:
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

        if "displaced_in_dest" in merged.columns:
            dest_displaced = pd.to_numeric(merged["displaced_in_dest"], errors="coerce").fillna(0)
            base_displaced = (
                pd.to_numeric(merged["displaced_in"], errors="coerce").fillna(0)
                if "displaced_in" in merged.columns
                else pd.Series(0, index=merged.index, dtype="float64")
            )
            merged["displaced_in"] = dest_displaced.where(dest_displaced > 0, base_displaced)
            merged = merged.drop(columns=["displaced_in_dest"])

        for col in ["events","fatalities","displaced","population_exposure","priority_score_country",
                    "priority_score_global","displaced_in"]:
            if col not in merged.columns:
                merged[col] = 0
            merged[col] = pd.to_numeric(merged[col], errors="coerce").fillna(0)
        merged["displaced"] = merged["displaced"].where(merged["displaced"] > 0, merged["displaced_in"])
        priority_fallback = _fallback_priority_score(merged)
        for score_col in ["priority_score_country", "priority_score_global"]:
            score_values = pd.to_numeric(merged[score_col], errors="coerce").fillna(0.0)
            missing_score = score_values <= 0
            merged[score_col] = score_values.where(~missing_score, priority_fallback)

        total_priority = float(merged["priority_score_country"].sum())
        total_disp = float(merged["displaced"].sum())
        total_ev = int(hierarchy.numeric_series(priority_slice, "events").sum())

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
            <div class="kpi-label">Displacement Snapshot</div>
            <div class="kpi-value">{fmt_big(total_disp)}</div>
            <div class="kpi-sub">Latest snapshot · {selected_month} {selected_year}</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-accent"></div>
            <div class="kpi-label">Events</div>
            <div class="kpi-value">{total_ev:,}</div>
            <div class="kpi-sub">{selected_month} {selected_year}</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        render_country_need_detail(selected_country_name, selected_country_priority_row)

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
                "admin_name_norm":False,
            },
            mapbox_style="carto-positron",
            center=build_mapbox_center(merged),
            zoom=build_mapbox_zoom(merged, base_zoom=5.0, max_zoom=8.4),
            opacity=0.88,
            title=f"{selected_country_name} — {metric_label(selected_metric)} by {'Governorate' if selected_country_norm == 'lebanon' else 'Admin1'}",
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
        if has_country_admin2:
            _country_drilldown = st.session_state.get("country_admin1_drilldown")
            st.session_state["country_map_level"] = "admin2" if _country_drilldown else "admin1"
            if _country_drilldown:
                _a1_match = country_admin2_boundary[country_admin2_boundary["admin1_norm"] == _country_drilldown]
                _admin1_display = (
                    str(_a1_match["admin1_name"].iloc[0])
                    if not _a1_match.empty
                    else _country_drilldown.replace("-", " ").title()
                )
                st.markdown(
                    f'<div style="font-family:Inter,sans-serif;font-size:13px;color:#5a6577;'
                    f'margin-bottom:10px;padding:8px 14px;background:#eef1f6;border-radius:8px;">'
                    f'Viewing districts inside <strong style="color:#1b2230;">{_admin1_display}</strong></div>',
                    unsafe_allow_html=True,
                )
                _admin1_row = merged[merged["admin_name_norm"] == _country_drilldown].copy()
                _admin2_gdf, _estimated, _estimate_note = build_country_admin2_priority_view(
                    country_admin2_boundary,
                    selected_country_name,
                    _country_drilldown,
                    selected_year,
                    selected_month,
                    _admin1_row,
                )
                if _estimated and _estimate_note:
                    st.info(_estimate_note)
                if _admin2_gdf.empty:
                    st.warning(f"No admin2 boundary data found for {_admin1_display}.")
                if selected_metric == "priority_score_global" and "priority_score_global" in _admin2_gdf.columns:
                    _detail_metric = "priority_score_global"
                    _detail_scale = SCALE_BLUE
                    _detail_fmt = lambda v: f"{v:.3f}"
                    _detail_label = "Priority Score (Global)"
                elif selected_metric in {"priority_score_country", "priority_score_global"}:
                    _detail_metric = "priority_score"
                    _detail_scale = SCALE_BLUE
                    _detail_fmt = lambda v: f"{v:.3f}"
                    _detail_label = "Priority Score"
                elif selected_metric == "fatalities":
                    _detail_metric = "fatalities"
                    _detail_scale = SCALE_WARM
                    _detail_fmt = fmt_big
                    _detail_label = "Fatalities"
                elif selected_metric == "population_exposure":
                    _detail_metric = "population_exposure"
                    _detail_scale = SCALE_GOLD
                    _detail_fmt = fmt_big
                    _detail_label = "Pop. Exposure"
                elif selected_metric == "displaced" and "displaced_in" in _admin2_gdf.columns:
                    _detail_metric = "displaced_in"
                    _detail_scale = SCALE_TEAL
                    _detail_fmt = fmt_big
                    _detail_label = "Displacement Snapshot"
                else:
                    _detail_metric = "priority_score" if selected_metric == "displaced" else "events"
                    _detail_scale = SCALE_BLUE if _detail_metric == "priority_score" else SCALE_TEAL
                    _detail_fmt = (lambda v: f"{v:.3f}") if _detail_metric == "priority_score" else fmt_big
                    _detail_label = "Priority Score" if _detail_metric == "priority_score" else "Events"
                _admin2_gdf = ensure_numeric_columns(
                    _admin2_gdf,
                    [
                        "priority_score", "priority_score_country", "priority_score_global",
                        "priority_rank", "events", "fatalities", "population_exposure",
                        "displaced", "displaced_in",
                    ],
                )
                if "district_value_source" not in _admin2_gdf.columns:
                    _admin2_gdf["district_value_source"] = "Matched admin2 data"
                else:
                    _admin2_gdf["district_value_source"] = _admin2_gdf["district_value_source"].fillna("Matched admin2 data")
                if "displacement_data_note" not in _admin2_gdf.columns:
                    _admin2_gdf["displacement_data_note"] = "No district displacement estimate"
                else:
                    _admin2_gdf["displacement_data_note"] = _admin2_gdf["displacement_data_note"].fillna("No district displacement estimate")
                if "district_estimation_note" not in _admin2_gdf.columns:
                    _admin2_gdf["district_estimation_note"] = ""
                else:
                    _admin2_gdf["district_estimation_note"] = _admin2_gdf["district_estimation_note"].fillna("")
                _admin2_gdf["displaced"] = _admin2_gdf["displaced"].where(
                    _admin2_gdf["displaced"] > 0,
                    _admin2_gdf["displaced_in"],
                )
                _fig2 = px.choropleth_mapbox(
                    _admin2_gdf,
                    geojson=json.loads(_admin2_gdf.to_json()),
                    locations="admin2_norm",
                    featureidkey="properties.admin2_norm",
                    color=_detail_metric,
                    color_continuous_scale=_detail_scale,
                    hover_name="admin2_label",
                    hover_data={
                        "priority_score": ":.3f",
                        "priority_rank": True,
                        "events": True,
                        "fatalities": True,
                        "population_exposure": True,
                        "displaced": True,
                        "displaced_in": True,
                        "district_estimation_note": True,
                        "admin2_norm": False,
                    },
                    mapbox_style="carto-positron",
                    center=build_mapbox_center(_admin2_gdf),
                    zoom=build_mapbox_zoom(_admin2_gdf, base_zoom=6.6, max_zoom=9.8),
                    opacity=0.9,
                    title=f"{_admin1_display} — {_detail_label} by District",
                )
                _fig2.update_layout(
                    **LIGHT_LAYOUT,
                    height=800,
                    coloraxis_colorbar=dict(
                        title=_detail_label,
                        tickfont=dict(family="Inter", size=10, color="#5a6577"),
                        title_font=dict(family="Inter", size=11, color="#1b2230"),
                    ),
                )
                if _detail_metric in {"priority_score", "priority_score_global"}:
                    _fig2.update_layout(
                        title=dict(
                            text=f"Priority by District in {_admin1_display}",
                            font=dict(family="Playfair Display", size=16, color="#1b2230"),
                            x=0.02,
                            xanchor="left",
                            y=0.97,
                        )
                    )
                st.plotly_chart(_fig2, use_container_width=True, key="country_priority_map")
                st.markdown(
                    f'<div class="section-title"><span class="section-dot"></span>Top {_admin1_display} Districts by {_detail_label}</div>',
                    unsafe_allow_html=True,
                )
                _top_d = (
                    _admin2_gdf[_admin2_gdf[_detail_metric] > 0]
                    .sort_values(_detail_metric, ascending=False)[["admin2_label", _detail_metric]]
                    .head(10)
                    .reset_index(drop=True)
                )
                if _top_d.empty:
                    st.info(f"No districts with {_detail_label.lower()} above 0 for this period.")
                else:
                    render_top10_grid(_top_d, "admin2_label", _detail_metric, fmt_fn=_detail_fmt)
            else:
                event = st.plotly_chart(
                    fig,
                    use_container_width=True,
                    on_select="rerun",
                    selection_mode=("points",),
                    key="country_priority_map",
                )
                clicked_admin1 = extract_selected_map_location(event)
                if clicked_admin1 and clicked_admin1 != _country_drilldown:
                    st.session_state["country_admin1_drilldown"] = clicked_admin1
                    st.session_state["country_map_level"] = "admin2"
                    st.rerun()
                st.caption(
                    "Click a governorate to zoom into its admin2 districts."
                    if selected_country_norm == "lebanon"
                    else "Click an admin1 area to zoom into its admin2 districts."
                )
                st.markdown(
                    f'<div class="section-title"><span class="section-dot"></span>'
                    f'{"Top Governorates" if selected_country_norm == "lebanon" else "Top Admin1"} by {metric_label(selected_metric)}</div>',
                    unsafe_allow_html=True
                )
                top_admin = (
                    merged[merged[selected_metric] > 0]
                    .sort_values(selected_metric, ascending=False)[["admin_name", selected_metric]]
                    .head(10)
                    .reset_index(drop=True)
                )
                if top_admin.empty:
                    st.info(f"No admin areas with {metric_label(selected_metric).lower()} above 0 for this period.")
                else:
                    render_top10_grid(top_admin, "admin_name", selected_metric, fmt_fn=fmt_fn)
        else:
            st.plotly_chart(fig, use_container_width=True, key="country_priority_map")

            st.markdown(
                f'<div class="section-title"><span class="section-dot"></span>Top Admin1 by {metric_label(selected_metric)}</div>',
                unsafe_allow_html=True
            )
            top_admin = (
                merged[merged[selected_metric] > 0]
                .sort_values(selected_metric, ascending=False)[["admin_name", selected_metric]]
                .head(10)
                .reset_index(drop=True)
            )
            if top_admin.empty:
                st.info(f"No admin areas with {metric_label(selected_metric).lower()} above 0 for this period.")
            else:
                render_top10_grid(top_admin, "admin_name", selected_metric, fmt_fn=fmt_fn)

    # ─────────────────────────────────────────────
    # DISPLACEMENT STORY — full period 2024–2026
    # ─────────────────────────────────────────────
    cnorm_story = canonical_country_norm(selected_country_name)
    story_displacement_mode = "latest"
    story_disp_in_rows = displacement_dest[displacement_dest["country"] == cnorm_story].copy()
    story_disp_out_rows = displacement_origin[displacement_origin["country"] == cnorm_story].copy()
    story_arrivals_snapshot, story_arrivals_period = get_latest_displacement_snapshot(
        story_disp_in_rows,
        ["admin1_norm"],
        "displaced_in",
    )
    story_departures_snapshot, story_departures_period = get_latest_displacement_snapshot(
        story_disp_out_rows,
        ["admin1_norm"],
        "displaced_from",
    )
    story_snapshot_period = (
        story_arrivals_period
        or get_latest_period(country_priority_rows)
    )
    story_snapshot_label = format_period_label(story_snapshot_period) or "the latest available month"

    st.markdown(
        f'<div class="section-title" style="margin-top:36px;">'
        f'<span class="section-dot"></span>Displacement Snapshot - {story_snapshot_label}</div>',
        unsafe_allow_html=True,
    )

    tab_overview, tab_bubbles, tab_priority = st.tabs([
        "Overview",
        "Displacement & Pressure",
        "Why Priority Changes",
    ])

    with tab_overview:
        render_displacement_snapshot_overview(
            selected_country_name,
            boundary_gdf,
            story_arrivals_snapshot,
            story_arrivals_period,
            story_departures_snapshot,
            story_departures_period,
            displacement_mode=story_displacement_mode,
        )

    with tab_bubbles:
        st.markdown(f"""
        <div style="padding:20px 0 10px 0;">
          <p style="font-family:'Playfair Display',serif;font-size:22px;font-weight:600;color:#1b2230;line-height:1.4;margin:0 0 10px 0;">
            Where are displaced people concentrated across {selected_country_name}?
          </p>
          <p style="font-family:'Inter',sans-serif;font-size:14px;color:#5a6577;line-height:1.85;margin:0 0 4px 0;max-width:680px;">
            Each circle represents one admin1 area.
            <strong>Size</strong> reflects displaced people in {story_snapshot_label}.
            <strong>Color</strong> shows the priority score for the same snapshot where available.
            Values use that same snapshot month rather than summing all months together.
          </p>
          <p style="font-family:'Inter',sans-serif;font-size:12px;color:#8893a4;line-height:1.6;margin:0;">
            Snapshot month: <strong style="color:#1b2230;">{story_snapshot_label}</strong>.
            Hover any circle for displacement, priority, and conflict context.
          </p>
        </div>
        """, unsafe_allow_html=True)
        render_displacement_snapshot_bubble_story(
            selected_country_name,
            boundary_gdf,
            snapshot_period=story_snapshot_period,
            displacement_mode=story_displacement_mode,
        )

    with tab_priority:
        render_displacement_snapshot_priority_scatter(
            selected_country_name,
            boundary_gdf,
            snapshot_period=story_snapshot_period,
            displacement_mode=story_displacement_mode,
        )
