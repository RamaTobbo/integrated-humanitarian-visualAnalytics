import streamlit as st
import streamlit.components.v1 as components

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

#MainMenu, footer { visibility: hidden; }
[data-testid="stToolbar"] { display: none; }
[data-testid="stSidebarNav"] { display: none !important; }
hr { border-color: var(--border) !important; }

/* ── Hero ── */
.home-hero {
    background: linear-gradient(135deg, var(--accent-ink) 0%, var(--accent) 60%, var(--accent-soft) 100%);
    border-radius: 20px;
    padding: 52px 56px 48px 56px;
    margin-bottom: 0px;
    position: relative;
    overflow: hidden;
}
.home-hero::before {
    content: '';
    position: absolute;
    top: -60px; right: -60px;
    width: 260px; height: 260px;
    border-radius: 50%;
    background: rgba(255,255,255,0.04);
}
.home-hero::after {
    content: '';
    position: absolute;
    bottom: -40px; left: 40%;
    width: 180px; height: 180px;
    border-radius: 50%;
    background: rgba(255,255,255,0.03);
}
.hero-eyebrow {
    font-family: 'Inter', sans-serif;
    font-weight: 600;
    font-size: 11px;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: rgba(255,255,255,0.55);
    margin-bottom: 14px;
}
.hero-title {
    font-family: 'Playfair Display', serif;
    font-weight: 700;
    font-size: 44px;
    line-height: 1.08;
    letter-spacing: -0.02em;
    color: #ffffff;
    margin-bottom: 20px;
}
.hero-title em {
    font-style: italic;
    color: rgba(255,255,255,0.75);
}
.hero-desc {
    font-family: 'Inter', sans-serif;
    font-size: 15px;
    font-weight: 400;
    line-height: 1.7;
    color: rgba(255,255,255,0.72);
    max-width: 680px;
}

/* ── Stat chips ── */
.stat-row {
    display: flex;
    gap: 12px;
    margin-top: 32px;
    flex-wrap: wrap;
}
.stat-chip {
    background: rgba(255,255,255,0.10);
    border: 1px solid rgba(255,255,255,0.18);
    border-radius: 40px;
    padding: 8px 18px;
    display: flex;
    align-items: center;
    gap: 8px;
}
.stat-chip .chip-val {
    font-family: 'Playfair Display', serif;
    font-weight: 700;
    font-size: 18px;
    color: #ffffff;
}
.stat-chip .chip-label {
    font-family: 'Inter', sans-serif;
    font-size: 11px;
    font-weight: 500;
    color: rgba(255,255,255,0.60);
    text-transform: uppercase;
    letter-spacing: 0.08em;
}

/* ── CTA button ── */
.cta-wrap {
    display: flex;
    gap: 12px;
    margin-top: 18px;
    margin-bottom: 36px;
}
div[data-testid="stButton"].cta-btn > button {
    background: #ffffff !important;
    color: var(--accent-ink) !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 14px 32px !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 700 !important;
    font-size: 14px !important;
    letter-spacing: 0.02em !important;
    box-shadow: 0 4px 20px rgba(0,0,0,0.18) !important;
    transition: all 0.18s ease !important;
    height: auto !important;
    line-height: 1.4 !important;
}
div[data-testid="stButton"].cta-btn > button:hover {
    background: var(--accent-light) !important;
    color: var(--accent) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 28px rgba(0,0,0,0.22) !important;
}

/* ── Section headers ── */
.section-title {
    font-family: 'Playfair Display', serif;
    font-weight: 600;
    font-size: 22px;
    letter-spacing: -0.01em;
    color: var(--text-primary);
    margin: 0 0 6px 0;
}
.section-sub {
    font-family: 'Inter', sans-serif;
    font-size: 13px;
    color: var(--text-dim);
    margin-bottom: 22px;
    font-weight: 400;
}
.section-divider {
    width: 40px;
    height: 3px;
    background: var(--accent);
    border-radius: 4px;
    margin-bottom: 10px;
    margin-top: 36px;
}

/* ── Nav cards (Story / Dashboard) ── */
.nav-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 28px 28px 24px 28px;
    box-shadow: var(--shadow-sm);
    height: 100%;
    position: relative;
    overflow: hidden;
    transition: transform 0.18s ease, box-shadow 0.18s ease;
}
.nav-card:hover {
    transform: translateY(-3px);
    box-shadow: var(--shadow-lg);
}
.nav-card .card-top-bar {
    height: 4px;
    border-radius: 4px 4px 0 0;
    position: absolute;
    top: 0; left: 0; right: 0;
}
.nav-card.accent-blue  .card-top-bar { background: var(--accent); }
.nav-card.accent-warm  .card-top-bar { background: var(--hl-warm); }
.nav-card .card-icon {
    width: 44px; height: 44px;
    border-radius: 12px;
    display: flex; align-items: center; justify-content: center;
    font-size: 20px;
    margin-bottom: 16px;
}
.nav-card.accent-blue  .card-icon { background: var(--accent-light); }
.nav-card.accent-warm  .card-icon { background: var(--hl-warm-soft); }
.nav-card .card-label {
    font-family: 'Inter', sans-serif;
    font-weight: 600;
    font-size: 10px;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--text-dim);
    margin-bottom: 6px;
}
.nav-card .card-title {
    font-family: 'Playfair Display', serif;
    font-weight: 700;
    font-size: 20px;
    color: var(--text-primary);
    margin-bottom: 10px;
    letter-spacing: -0.01em;
}
.nav-card .card-desc {
    font-family: 'Inter', sans-serif;
    font-size: 13px;
    line-height: 1.65;
    color: var(--text-secondary);
}
.nav-card .card-features {
    margin-top: 16px;
    display: flex;
    flex-direction: column;
    gap: 6px;
}
.nav-card .card-feature {
    font-family: 'Inter', sans-serif;
    font-size: 12px;
    color: var(--text-secondary);
    display: flex;
    align-items: center;
    gap: 8px;
}
.nav-card .card-feature::before {
    content: '';
    width: 5px; height: 5px;
    border-radius: 50%;
    background: var(--accent-soft);
    flex-shrink: 0;
}
.nav-card.accent-warm .card-feature::before { background: var(--hl-warm); }

/* ── Score formula ── */
.formula-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 28px 32px;
    box-shadow: var(--shadow-sm);
}
.formula-intro {
    font-family: 'Inter', sans-serif;
    font-size: 13px;
    line-height: 1.7;
    color: var(--text-secondary);
    margin-bottom: 24px;
}
.formula-row {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 11px 0;
    border-bottom: 1px solid var(--border);
}
.formula-row:last-child { border-bottom: none; }
.formula-pct {
    font-family: 'JetBrains Mono', monospace;
    font-size: 16px;
    font-weight: 500;
    color: var(--accent);
    width: 48px;
    flex-shrink: 0;
    text-align: right;
}
.formula-bar-wrap {
    flex: 1;
    height: 6px;
    background: var(--bg-soft);
    border-radius: 4px;
    overflow: hidden;
}
.formula-bar { height: 100%; border-radius: 4px; }
.formula-name {
    font-family: 'Inter', sans-serif;
    font-size: 13px;
    font-weight: 600;
    color: var(--text-primary);
    width: 160px;
    flex-shrink: 0;
}
.formula-why {
    font-family: 'Inter', sans-serif;
    font-size: 12px;
    color: var(--text-dim);
    flex: 1;
}

/* ── Data source pills ── */
.source-grid {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
}
.source-pill {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 14px 18px;
    box-shadow: var(--shadow-sm);
    min-width: 180px;
    flex: 1;
}
.source-pill .pill-name {
    font-family: 'Inter', sans-serif;
    font-weight: 700;
    font-size: 13px;
    color: var(--accent);
    margin-bottom: 3px;
}
.source-pill .pill-full {
    font-family: 'Inter', sans-serif;
    font-size: 11px;
    font-weight: 500;
    color: var(--text-dim);
    margin-bottom: 6px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}
.source-pill .pill-desc {
    font-family: 'Inter', sans-serif;
    font-size: 12px;
    color: var(--text-secondary);
    line-height: 1.5;
}

/* ── Methodology note ── */
.method-note {
    background: var(--accent-light);
    border: 1px solid var(--border-bright);
    border-left: 4px solid var(--accent);
    border-radius: 10px;
    padding: 16px 20px;
    font-family: 'Inter', sans-serif;
    font-size: 13px;
    line-height: 1.65;
    color: var(--text-secondary);
    margin-top: 20px;
}
.method-note strong { color: var(--accent); font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────
# SIDEBAR BRAND
# ──────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding:22px 4px 18px 4px; border-bottom:1px solid #e4e8ef; margin-bottom:14px; display:flex; align-items:center; gap:12px;">
        <div style="width:38px;height:38px;border-radius:10px;background:linear-gradient(135deg,#2c4a6e,#5a7aa0);display:flex;align-items:center;justify-content:center;color:#fff;font-family:'Playfair Display',serif;font-weight:700;font-size:18px;">C</div>
        <div>
            <div style="font-size:10px;letter-spacing:0.14em;text-transform:uppercase;color:#8893a4;font-weight:500;"></div>
            <div style="font-family:'Playfair Display',serif;font-weight:700;font-size:19px;color:#1b2230;margin-top:3px;">Priority Response</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ──────────────────────────────────────────────────
# HERO
# ──────────────────────────────────────────────────
st.markdown("""
<div class="home-hero">
    <div class="hero-eyebrow">Conflict &amp; Priority Intelligence</div>
    <div class="hero-title">
        Where should humanitarian<br>
        <em>attention go next?</em>
    </div>
    <div class="hero-desc">
        This dashboard translates raw conflict events, displacement figures, and
        access constraints into a single, comparable Priority Score — updated
        monthly, available at the sub-national level, across every conflict-affected
        region in the world.
    </div>
    <div class="stat-row">
        <div class="stat-chip">
            <span class="chip-val">100+</span>
            <span class="chip-label">Countries</span>
        </div>
        <div class="stat-chip">
            <span class="chip-val">2024 – 2026</span>
            <span class="chip-label">Coverage</span>
        </div>
        <div class="stat-chip">
            <span class="chip-val">Monthly</span>
            <span class="chip-label">Updates</span>
        </div>
        <div class="stat-chip">
            <span class="chip-val">Admin 1 &amp; 2</span>
            <span class="chip-label">Resolution</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── CTA button — right below the hero ──


# ──────────────────────────────────────────────────
# WHAT'S INSIDE — navigation cards
# ──────────────────────────────────────────────────
st.markdown("""
<div class="section-divider"></div>
<div class="section-title">What's Inside</div>
<div class="section-sub">Two views, one framework. Start with the Story, dig deeper in the Dashboard.</div>
""", unsafe_allow_html=True)

col1, col2 = st.columns(2, gap="large")

with col1:
    st.markdown("""
    <div class="nav-card accent-blue">
        <div class="card-top-bar"></div>
        <div class="card-icon">&#128506;</div>
        <div class="card-label">Page 1</div>
        <div class="card-title">The Story</div>
        <div class="card-desc">
            A guided narrative view of the conflict landscape. Start here to understand
            which countries and regions are under the most pressure right now, how
            conditions have changed over time, and where displacement is accelerating.
        </div>
        <div class="card-features">
            <div class="card-feature">Global conflict map with monthly snapshots</div>
            <div class="card-feature">Country-level priority ranking &amp; trends</div>
            <div class="card-feature">Displacement flows (IOM DTM + IDMC)</div>
  
        
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="nav-card accent-warm">
        <div class="card-top-bar"></div>
        <div class="card-icon">&#128202;</div>
        <div class="card-label">Page 2</div>
        <div class="card-title">The Dashboard</div>
        <div class="card-desc">
            An interactive exploration tool. Filter by country, region, or time period
            and compare areas side by side using the same priority framework. Designed
            for analysts who need to dig into specific situations.
        </div>
        <div class="card-features">
            <div class="card-feature">Filter by country, region &amp; time period</div>
            <div class="card-feature">Side-by-side country comparison radar</div>
            <div class="card-feature">Admin-1 breakdown within any country</div>
            <div class="card-feature">Export-ready tables</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ──────────────────────────────────────────────────
# PRIORITY SCORE — formula breakdown
# ──────────────────────────────────────────────────
st.markdown("""
<div class="section-divider"></div>
<div class="section-title">How the Priority Score Works</div>
<div class="section-sub">Every area receives a score from 0 to 1. Here is what goes into it.</div>
""", unsafe_allow_html=True)

components.html("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: transparent; font-family: 'Inter', sans-serif; }
  .fc {
    background: #ffffff;
    border: 1px solid #e4e8ef;
    border-radius: 16px;
    padding: 28px 32px;
    box-shadow: 0 2px 8px rgba(20,30,50,0.06);
  }
  .fc-intro {
    font-size: 13px;
    line-height: 1.7;
    color: #5a6577;
    margin-bottom: 24px;
  }
  .fc-row {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 11px 0;
    border-bottom: 1px solid #e4e8ef;
  }
  .fc-row:last-of-type { border-bottom: none; }
  .fc-pct {
    font-family: 'JetBrains Mono', monospace;
    font-size: 15px;
    font-weight: 500;
    color: #2c4a6e;
    width: 48px;
    flex-shrink: 0;
    text-align: right;
  }
  .fc-bar-wrap {
    width: 120px;
    flex-shrink: 0;
    height: 6px;
    background: #eef1f6;
    border-radius: 4px;
    overflow: hidden;
  }
  .fc-bar { height: 100%; border-radius: 4px; }
  .fc-name {
    font-size: 13px;
    font-weight: 600;
    color: #1b2230;
    width: 150px;
    flex-shrink: 0;
  }
  .fc-why {
    font-size: 12px;
    color: #8893a4;
    flex: 1;
  }
  .fc-note {
    background: #e8eef6;
    border-left: 4px solid #2c4a6e;
    border-radius: 10px;
    padding: 14px 18px;
    font-size: 13px;
    line-height: 1.65;
    color: #5a6577;
    margin-top: 20px;
  }
  .fc-note strong { color: #2c4a6e; font-weight: 600; }
</style>
<div class="fc">
  <div class="fc-intro">The Priority Score is a weighted composite of six indicators. Each indicator is normalized (min-max) within the same time period so that areas are always compared against their peers, not against an absolute benchmark. A higher score means the area needs more urgent attention relative to others.</div>
  <div class="fc-row"><div class="fc-pct">30%</div><div class="fc-bar-wrap"><div class="fc-bar" style="width:100%;background:#2c4a6e;"></div></div><div class="fc-name">Conflict Events</div><div class="fc-why">Number of recorded conflict incidents (battles, explosions, attacks on civilians) from ACLED.</div></div>
  <div class="fc-row"><div class="fc-pct">30%</div><div class="fc-bar-wrap"><div class="fc-bar" style="width:100%;background:#2c4a6e;"></div></div><div class="fc-name">Fatalities</div><div class="fc-why">Reported deaths from conflict events. Captures severity, not just frequency.</div></div>
  <div class="fc-row"><div class="fc-pct">20%</div><div class="fc-bar-wrap"><div class="fc-bar" style="width:67%;background:#5a8a82;"></div></div><div class="fc-name">Displacement</div><div class="fc-why">People forced to flee their homes and arrive in this area. A leading indicator of humanitarian load.</div></div>
  <div class="fc-row"><div class="fc-pct">10%</div><div class="fc-bar-wrap"><div class="fc-bar" style="width:33%;background:#a8864a;"></div></div><div class="fc-name">Population Exposure</div><div class="fc-why">Number of people living in proximity to conflict events — scales severity to population size.</div></div>
  <div class="fc-row"><div class="fc-pct">7.5%</div><div class="fc-bar-wrap"><div class="fc-bar" style="width:25%;background:#b8703a;"></div></div><div class="fc-name">Health Need</div><div class="fc-why">Country-level health system capacity score (WHO indicators). Low capacity amplifies conflict impact.</div></div>
  <div class="fc-row"><div class="fc-pct">7.5%</div><div class="fc-bar-wrap"><div class="fc-bar" style="width:25%;background:#b8703a;"></div></div><div class="fc-name">Education Need</div><div class="fc-why">Country-level education access score (UNESCO indicators). Captures longer-term vulnerability.</div></div>
 
</div>
""", height=520)

st.markdown("<br>", unsafe_allow_html=True)

# ──────────────────────────────────────────────────
# DATA SOURCES
# ──────────────────────────────────────────────────
st.markdown("""
<div class="section-divider"></div>
<div class="section-title">Data Sources</div>
<div class="section-sub">All underlying data comes from established open humanitarian and research datasets.</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="source-grid">
    <div class="source-pill">
        <div class="pill-name">ACLED</div>
        <div class="pill-full">Armed Conflict Location &amp; Event Data</div>
        <div class="pill-desc">Weekly conflict events and fatalities at admin-1 level, aggregated to monthly figures.</div>
    </div>
    <div class="source-pill">
        <div class="pill-name">IOM DTM</div>
        <div class="pill-full">Displacement Tracking Matrix</div>
        <div class="pill-desc">Sub-national internal displacement stocks by destination, reported by IOM field missions.</div>
    </div>
    <div class="source-pill">
        <div class="pill-name">IDMC</div>
        <div class="pill-full">Internal Displacement Monitoring Centre</div>
        <div class="pill-desc">Country-level annual displacement figures used as fallback when IOM DTM data is unavailable.</div>
    </div>
    <div class="source-pill">
        <div class="pill-name">WHO</div>
        <div class="pill-full">World Health Organization</div>
        <div class="pill-desc">Health system indicators (hospital beds, physicians) used to build the health need score.</div>
    </div>
    <div class="source-pill">
        <div class="pill-name">UNESCO</div>
        <div class="pill-full">UN Educational, Scientific &amp; Cultural Org.</div>
        <div class="pill-desc">Literacy rates and school enrollment ratios used to build the education need score.</div>
    </div>

</div>
""", unsafe_allow_html=True)
st.markdown(
    """
    <div class="method-note" style="margin-top:4px;">
        <strong>Presentation mode:</strong> A live demo view is now available with slide-style transitions,
        keyboard navigation, and presenter notes for each section.
    </div>
    """,
    unsafe_allow_html=True,
)

left_btn, right_btn = st.columns(2, gap="large")

with right_btn:
    if st.button("Explore the Story →", key="cta_story", use_container_width=True):
        st.switch_page("pages/1_Story.py")
st.markdown("<br><br>", unsafe_allow_html=True)
