import pandas as pd
import plotly.graph_objects as go

RADAR_AXIS_SPECS = [
    {"key": "conflict", "label": "Conflict", "source_col": "events_log"},
    {"key": "fatalities", "label": "Fatalities", "source_col": "fatalities_log"},
    {"key": "displacement", "label": "Displacement", "source_col": "displaced_log"},
    {"key": "exposure", "label": "Exposure", "source_col": "exposure_log"},
    {"key": "health_need", "label": "Health Need", "source_col": "health_priority_score"},
    {"key": "education_need", "label": "Education Need", "source_col": "education_priority_score"},
]

RADAR_COLORS = ["#0ea5e9", "#10b981", "#f59e0b", "#8b5cf6", "#f97316"]


def _hex_to_rgba(hex_color, alpha):
    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6:
        return f"rgba(14, 165, 233, {alpha})"
    red = int(hex_color[0:2], 16)
    green = int(hex_color[2:4], 16)
    blue = int(hex_color[4:6], 16)
    return f"rgba({red}, {green}, {blue}, {alpha})"


def _display_country_name(value):
    value = str(value).strip()
    if not value:
        return value
    return value.replace("-", " ").title()


def normalize_radar_values(selected_df, reference_df):
    normalized = selected_df.copy()
    if normalized.empty:
        return normalized

    for spec in RADAR_AXIS_SPECS:
        source_col = spec["source_col"]
        selected_values = pd.to_numeric(normalized.get(source_col, 0), errors="coerce").fillna(0.0)
        reference_values = pd.to_numeric(reference_df.get(source_col, 0), errors="coerce").fillna(0.0)
        max_value = float(reference_values.max()) if not reference_values.empty else 0.0
        if max_value <= 0:
            normalized[spec["key"]] = 0.0
        else:
            normalized[spec["key"]] = (selected_values / max_value).clip(0.0, 1.0)

    return normalized


def prepare_radar_comparison_data(
    country_priority_df,
    selected_year,
    selected_month,
    selected_countries,
    scaling_option=None,
):
    period_df = country_priority_df[
        (country_priority_df["year"] == selected_year) &
        (country_priority_df["month"].astype(str).str.strip().str.lower() == str(selected_month).strip().lower())
    ].copy()
    if period_df.empty:
        return {
            "available_countries": [],
            "selected_countries": [],
            "wide_df": pd.DataFrame(),
            "long_df": pd.DataFrame(),
        }

    period_df["country"] = period_df["country"].astype(str).str.strip()
    if "country_label" not in period_df.columns:
        period_df["country_label"] = period_df["country"].apply(_display_country_name)
    else:
        period_df["country_label"] = period_df["country_label"].astype(str).str.strip()
    period_df = (
        period_df.sort_values(["country", "country_priority_score"], ascending=[True, False])
        .drop_duplicates(subset=["country"], keep="first")
        .reset_index(drop=True)
    )

    available_countries = period_df["country_label"].dropna().tolist()
    selected_countries = [country for country in selected_countries if country in available_countries][:5]
    selected_df = period_df[period_df["country_label"].isin(selected_countries)].copy()
    if selected_df.empty:
        return {
            "available_countries": available_countries,
            "selected_countries": selected_countries,
            "wide_df": pd.DataFrame(),
            "long_df": pd.DataFrame(),
        }

    selected_df["country_label"] = pd.Categorical(selected_df["country_label"], categories=selected_countries, ordered=True)
    selected_df = selected_df.sort_values("country_label").reset_index(drop=True)
    selected_df["country_label"] = selected_df["country_label"].astype(str)

    normalized_df = normalize_radar_values(selected_df, period_df)

    long_df = normalized_df.melt(
        id_vars=["country", "country_label"],
        value_vars=[spec["key"] for spec in RADAR_AXIS_SPECS],
        var_name="axis_key",
        value_name="normalized_value",
    )
    axis_label_lookup = {spec["key"]: spec["label"] for spec in RADAR_AXIS_SPECS}
    long_df["axis_label"] = long_df["axis_key"].map(axis_label_lookup)

    return {
        "available_countries": available_countries,
        "selected_countries": selected_countries,
        "wide_df": normalized_df,
        "long_df": long_df,
    }


def build_country_comparison_radar(radar_df, scaling_option=None):
    fig = go.Figure()
    axis_labels = [spec["label"] for spec in RADAR_AXIS_SPECS]

    for index, (_, row) in enumerate(radar_df.iterrows()):
        color = RADAR_COLORS[index % len(RADAR_COLORS)]
        values = [float(row.get(spec["key"], 0) or 0) for spec in RADAR_AXIS_SPECS]
        fig.add_trace(go.Scatterpolar(
            r=values + values[:1],
            theta=axis_labels + axis_labels[:1],
            mode="lines+markers",
            name=str(row.get("country_label", row["country"])),
            line=dict(color=color, width=2.5),
            marker=dict(size=7, color=color, line=dict(width=1, color="#ffffff")),
            fill="toself",
            fillcolor=_hex_to_rgba(color, 0.16),
            opacity=0.96,
            hovertemplate="<b>%{fullData.name}</b><br>%{theta}: %{r:.3f}<extra></extra>",
        ))

    fig.update_layout(
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        margin=dict(l=30, r=30, t=55, b=25),
        height=560,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.08,
            xanchor="left",
            x=0.0,
            font=dict(family="Inter", size=11, color="#1b2230"),
            bgcolor="rgba(255,255,255,0.88)",
            bordercolor="#e4e8ef",
            borderwidth=1,
        ),
        polar=dict(
            bgcolor="#ffffff",
            radialaxis=dict(
                visible=True,
                range=[0, 1],
                tickmode="array",
                tickvals=[0.2, 0.4, 0.6, 0.8, 1.0],
                tickfont=dict(family="Inter", size=9, color="#8893a4"),
                gridcolor="#eef1f6",
                linecolor="#eef1f6",
            ),
            angularaxis=dict(
                tickfont=dict(family="Inter", size=11, color="#1b2230"),
                gridcolor="#eef1f6",
                linecolor="#eef1f6",
            ),
        ),
        hoverlabel=dict(
            bgcolor="white",
            bordercolor="#e4e8ef",
            font=dict(family="Inter", size=12, color="#1b2230"),
        ),
        title=dict(
            text="Country Comparison Radar",
            x=0.01,
            font=dict(family="Playfair Display", size=22, color="#1b2230"),
        ),
    )
    return fig
