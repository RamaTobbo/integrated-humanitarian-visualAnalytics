from pathlib import Path
import re
import unicodedata

import numpy as np
import pandas as pd


COUNTRY_ALIASES = {
    "syrian arab republic": "syria",
    "syria": "syria",
    "turkiye": "turkey",
    "turkey": "turkey",
    "ukraine": "ukraine",
    "russian federation": "russia",
    "russia": "russia",
    "united states of america": "united states of america",
    "united states": "united states of america",
    "usa": "united states of america",
    "czech republic": "czechia",
    "iran (islamic republic of)": "iran",
    "islamic republic of iran": "iran",
    "venezuela, bolivarian republic of": "venezuela",
    "bolivia (plurinational state of)": "bolivia",
    "united republic of tanzania": "tanzania",
    "republic of moldova": "moldova",
    "lao people's democratic republic": "laos",
    "state of palestine": "palestine",
    "democratic republic of congo": "democratic republic of the congo",
    "congo dem. rep.": "democratic republic of the congo",
    "congo, dem. rep.": "democratic republic of the congo",
    "dr congo": "democratic republic of the congo",
    "congo rep.": "republic of the congo",
    "congo, rep.": "republic of the congo",
    "republic of the congo": "republic of the congo",
}

HEALTH_KEYWORDS = (
    "health", "hospital", "physician", "doctor", "doctors",
    "medical", "medicine", "beds", "bed", "nurse", "nurses",
)
EDUCATION_KEYWORDS = (
    "education", "school", "schools", "literacy", "literate",
    "enrollment", "enrolment", "attendance", "completion",
    "dropout", "student", "students", "learning",
)
DIRECT_NEED_KEYWORDS = (
    "mortality", "deaths", "death", "dropout", "out of school",
    "out-of-school", "unmet need", "malnutrition", "risk",
    "deprivation", "poverty", "overcrowding", "hazard",
)
INVERSE_NEED_KEYWORDS = (
    "beds", "bed", "physician", "doctor", "doctors", "nurse", "nurses",
    "literacy", "enrollment", "enrolment", "attendance", "completion",
    "school", "schools", "access", "coverage", "availability",
)
ID_CANDIDATES = {
    "country_name", "country", "country_code", "indicator_name", "indicator_code",
    "series_name", "series_code", "year", "time", "period", "date",
}
ENCODINGS = ("utf-8-sig", "utf-8", "cp1252", "latin1")
SKIPROWS_OPTIONS = (0, 4)
NEED_DIR_CANDIDATES = (
    Path("data/need"),
    Path("data/raw/need"),
    Path("data/cleaned/need"),
)


def normalize_text(value):
    if pd.isna(value):
        return None
    value = str(value).strip().lower()
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.replace("–", "-").replace("—", "-")
    value = value.replace("_", " ").replace("/", " ").replace(",", " ")
    value = value.replace("’", "'")
    value = re.sub(r"\s+", " ", value).strip()
    return value or None


def normalize_column_name(name):
    normalized = normalize_text(name)
    if normalized is None:
        return ""
    normalized = re.sub(r"[^a-z0-9]+", "_", normalized).strip("_")
    return normalized


def clean_country_names(values):
    def _clean_one(value):
        normalized = normalize_text(value)
        if normalized is None:
            return None
        return COUNTRY_ALIASES.get(normalized, normalized)

    if isinstance(values, pd.Series):
        return values.apply(_clean_one)
    return _clean_one(values)


def _choose_need_dir(search_dirs=None):
    search_dirs = search_dirs or NEED_DIR_CANDIDATES
    for path in search_dirs:
        path = Path(path)
        if path.exists() and any(path.glob("*.csv")):
            return path
    return None


def _detect_country_column(columns):
    for candidate in (
        "country_name", "country", "economy_name", "location_name",
        "location", "entity",
    ):
        if candidate in columns:
            return candidate
    return None


def _detect_indicator_column(columns):
    for candidate in ("indicator_name", "series_name", "indicator", "series"):
        if candidate in columns:
            return candidate
    return None


def _detect_indicator_code_column(columns):
    for candidate in ("indicator_code", "series_code", "indicator_id", "series_id"):
        if candidate in columns:
            return candidate
    return None


def _extract_year_from_label(label):
    match = re.search(r"(19|20)\d{2}", str(label))
    return int(match.group(0)) if match else None


def _wide_year_columns(columns):
    year_cols = []
    for col in columns:
        year = _extract_year_from_label(col)
        if year is not None:
            year_cols.append(col)
    return year_cols


def _frame_quality_score(df):
    if df is None or df.empty:
        return -1
    columns = set(df.columns)
    score = 0
    if _detect_country_column(columns):
        score += 4
    year_cols = _wide_year_columns(columns)
    if year_cols:
        score += 4
        score += min(len(year_cols), 10) / 10.0
    if _detect_indicator_column(columns):
        score += 1
    if _detect_indicator_code_column(columns):
        score += 1
    return score


def _read_need_csv(path):
    best_df = None
    best_score = -1
    for encoding in ENCODINGS:
        for skiprows in SKIPROWS_OPTIONS:
            try:
                df = pd.read_csv(path, encoding=encoding, skiprows=skiprows)
            except Exception:
                continue
            df.columns = [normalize_column_name(col) for col in df.columns]
            score = _frame_quality_score(df)
            if score > best_score:
                best_df = df
                best_score = score
    return best_df if best_score >= 4 else None


def _classify_dataset(path, df):
    columns = " ".join(df.columns)
    sample_text = " ".join(
        str(value)
        for value in df.head(3).fillna("").astype(str).values.flatten().tolist()
    )
    combined = normalize_text(f"{path.name} {columns} {sample_text}") or ""
    if any(keyword in combined for keyword in HEALTH_KEYWORDS):
        return "health"
    if any(keyword in combined for keyword in EDUCATION_KEYWORDS):
        return "education"
    return None


def _prepare_need_long(path, df, dataset_kind, valid_countries=None):
    columns = set(df.columns)
    country_col = _detect_country_column(columns)
    if country_col is None:
        return pd.DataFrame(columns=["country", "indicator", "indicator_code", "year", "value", "dataset_kind", "source_file"])

    indicator_col = _detect_indicator_column(columns)
    indicator_code_col = _detect_indicator_code_column(columns)
    country_code_col = "country_code" if "country_code" in columns else None
    year_cols = _wide_year_columns(columns)

    if not year_cols:
        return pd.DataFrame(columns=["country", "indicator", "indicator_code", "year", "value", "dataset_kind", "source_file"])

    id_cols = [country_col]
    for optional_col in (country_code_col, indicator_col, indicator_code_col):
        if optional_col and optional_col not in id_cols:
            id_cols.append(optional_col)

    long_df = df.melt(
        id_vars=id_cols,
        value_vars=year_cols,
        var_name="year_label",
        value_name="value",
    )
    long_df["year"] = long_df["year_label"].apply(_extract_year_from_label)
    long_df["value"] = pd.to_numeric(long_df["value"], errors="coerce")
    long_df["country"] = clean_country_names(long_df[country_col])
    long_df["indicator"] = (
        long_df[indicator_col].astype(str).str.strip()
        if indicator_col
        else path.stem
    )
    if indicator_code_col:
        long_df["indicator_code"] = long_df[indicator_code_col].astype(str).str.strip()
    else:
        long_df["indicator_code"] = normalize_column_name(path.stem)
    long_df["dataset_kind"] = dataset_kind
    long_df["source_file"] = path.name

    long_df = long_df[
        long_df["country"].notna() &
        long_df["year"].notna() &
        long_df["value"].notna()
    ].copy()
    long_df["year"] = long_df["year"].astype(int)

    if valid_countries is not None:
        long_df = long_df[long_df["country"].isin(valid_countries)].copy()

    return long_df[["country", "indicator", "indicator_code", "year", "value", "dataset_kind", "source_file"]]


def load_need_data(valid_countries=None, search_dirs=None):
    need_dir = _choose_need_dir(search_dirs=search_dirs)
    empty_frame = pd.DataFrame(columns=["country", "indicator", "indicator_code", "year", "value", "dataset_kind", "source_file"])
    if need_dir is None:
        return {
            "need_dir": None,
            "health": empty_frame.copy(),
            "education": empty_frame.copy(),
        }

    valid_country_set = set(valid_countries or [])
    if not valid_country_set:
        valid_country_set = None

    grouped_frames = {"health": [], "education": []}
    for path in sorted(need_dir.glob("*.csv")):
        if "metadata" in normalize_text(path.name or ""):
            continue
        raw_df = _read_need_csv(path)
        if raw_df is None:
            continue
        dataset_kind = _classify_dataset(path, raw_df)
        if dataset_kind is None:
            continue
        long_df = _prepare_need_long(path, raw_df, dataset_kind, valid_countries=valid_country_set)
        if not long_df.empty:
            grouped_frames[dataset_kind].append(long_df)

    return {
        "need_dir": need_dir,
        "health": pd.concat(grouped_frames["health"], ignore_index=True) if grouped_frames["health"] else empty_frame.copy(),
        "education": pd.concat(grouped_frames["education"], ignore_index=True) if grouped_frames["education"] else empty_frame.copy(),
    }


def _scale_series(series, neutral_value=0.5):
    numeric = pd.to_numeric(series, errors="coerce")
    result = pd.Series(np.nan, index=series.index, dtype=float)
    valid = numeric.dropna()
    if valid.empty:
        return result
    if float(valid.max()) == float(valid.min()):
        result.loc[valid.index] = neutral_value
        return result
    result.loc[valid.index] = (valid - valid.min()) / (valid.max() - valid.min())
    return result


def _indicator_priority_direction(indicator_text):
    normalized = normalize_text(indicator_text) or ""
    if any(keyword in normalized for keyword in DIRECT_NEED_KEYWORDS):
        return "direct"
    if any(keyword in normalized for keyword in INVERSE_NEED_KEYWORDS):
        return "inverse"
    return "inverse"


def _build_priority_score(dataset_df, score_prefix):
    empty = pd.DataFrame(
        columns=[
            "country",
            f"{score_prefix}_priority_score",
            f"{score_prefix}_source_year",
            f"{score_prefix}_indicator_count",
            f"{score_prefix}_data_available",
        ]
    )
    if dataset_df is None or dataset_df.empty:
        return empty

    latest = (
        dataset_df.sort_values(["country", "indicator", "year"])
        .groupby(["country", "indicator"], as_index=False)
        .tail(1)
        .copy()
    )

    latest["priority_component"] = np.nan
    for indicator, index in latest.groupby("indicator").groups.items():
        scaled = _scale_series(latest.loc[index, "value"])
        if _indicator_priority_direction(indicator) == "inverse":
            scaled = 1 - scaled
        latest.loc[index, "priority_component"] = scaled

    scores = (
        latest.groupby("country", as_index=False)
        .agg({
            "priority_component": "mean",
            "year": "max",
            "indicator": "nunique",
        })
        .rename(columns={
            "priority_component": f"{score_prefix}_priority_score",
            "year": f"{score_prefix}_source_year",
            "indicator": f"{score_prefix}_indicator_count",
        })
    )
    scores[f"{score_prefix}_data_available"] = 1
    return scores


def build_health_score(health_df):
    return _build_priority_score(health_df, "health")


def build_education_score(education_df):
    return _build_priority_score(education_df, "education")


def merge_need_scores(country_df, health_scores, education_scores):
    merged = country_df.copy()
    if "country" in merged.columns:
        merged["country"] = clean_country_names(merged["country"])

    for score_df in (health_scores, education_scores):
        if score_df is not None and not score_df.empty:
            merged = merged.merge(score_df, how="left", on="country")

    defaults = {
        "health_priority_score": 0.0,
        "education_priority_score": 0.0,
        "health_source_year": pd.NA,
        "education_source_year": pd.NA,
        "health_indicator_count": 0,
        "education_indicator_count": 0,
        "health_data_available": 0,
        "education_data_available": 0,
    }

    for col, default in defaults.items():
        if col not in merged.columns:
            merged[col] = default

    for score_col in ("health_priority_score", "education_priority_score"):
        score_series = pd.to_numeric(merged[score_col], errors="coerce")
        fill_value = float(score_series.dropna().median()) if score_series.notna().any() else 0.0
        merged[score_col] = score_series.fillna(fill_value).clip(0.0, 1.0)

    for year_col in ("health_source_year", "education_source_year"):
        merged[year_col] = pd.to_numeric(merged[year_col], errors="coerce").astype("Int64")

    for count_col in ("health_indicator_count", "education_indicator_count", "health_data_available", "education_data_available"):
        merged[count_col] = pd.to_numeric(merged[count_col], errors="coerce").fillna(0).astype(int)

    return merged
