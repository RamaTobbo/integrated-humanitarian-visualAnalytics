import pandas as pd


UNKNOWN_ADMIN1_NORM = "unknown"
UNKNOWN_ADMIN1_LABEL = "Unknown"
UNKNOWN_ADMIN2_NORM = "unknown"
UNKNOWN_ADMIN2_LABEL = "Unknown"


def numeric_series(frame, col, default=0.0):
    if col in frame.columns:
        return pd.to_numeric(frame[col], errors="coerce").fillna(default)
    return pd.Series(default, index=frame.index, dtype="float64")


def ensure_numeric_columns(frame, columns, default=0.0):
    out = frame.copy()
    for col in columns:
        out[col] = numeric_series(out, col, default)
    return out


def fill_unknown_admin_levels(
    frame,
    admin1_col="admin1_norm",
    admin2_col=None,
    admin1_label_col=None,
    admin2_label_col=None,
):
    out = frame.copy()
    if admin1_col and admin1_col in out.columns:
        missing = out[admin1_col].isna() | out[admin1_col].astype(str).str.strip().isin(["", "nan", "none"])
        out.loc[missing, admin1_col] = UNKNOWN_ADMIN1_NORM
    if admin1_label_col and admin1_label_col in out.columns:
        missing = out[admin1_label_col].isna() | out[admin1_label_col].astype(str).str.strip().isin(["", "nan", "none"])
        out.loc[missing, admin1_label_col] = UNKNOWN_ADMIN1_LABEL
    if admin2_col and admin2_col in out.columns:
        missing = out[admin2_col].isna() | out[admin2_col].astype(str).str.strip().isin(["", "nan", "none"])
        out.loc[missing, admin2_col] = UNKNOWN_ADMIN2_NORM
    if admin2_label_col and admin2_label_col in out.columns:
        missing = out[admin2_label_col].isna() | out[admin2_label_col].astype(str).str.strip().isin(["", "nan", "none"])
        out.loc[missing, admin2_label_col] = UNKNOWN_ADMIN2_LABEL
    return out


def _metric_columns(frame, candidates):
    return [col for col in candidates if col in frame.columns]


def reconcile_admin1_with_country_totals(
    admin1_frame,
    country_frame,
    key_cols,
    metric_cols,
    admin1_col="admin1_norm",
    admin1_label_col="admin1",
    tolerance=1e-6,
):
    admin1 = fill_unknown_admin_levels(
        admin1_frame,
        admin1_col=admin1_col,
        admin1_label_col=admin1_label_col if admin1_label_col in admin1_frame.columns else None,
    )
    country = country_frame.copy()
    metric_cols = _metric_columns(country, metric_cols)
    admin1 = ensure_numeric_columns(admin1, metric_cols)
    country = ensure_numeric_columns(country, metric_cols)

    group_cols = [col for col in key_cols if col in admin1.columns]
    if admin1_col in admin1.columns:
        group_cols.append(admin1_col)
    if admin1_label_col in admin1.columns and admin1_label_col not in group_cols:
        group_cols.append(admin1_label_col)
    passthrough = [
        col for col in ["iso3", "iso_n3", "country", "country_norm", "year", "month_num", "month", "event_type"]
        if col in admin1.columns and col not in group_cols
    ]
    agg = {col: "sum" for col in metric_cols}
    agg.update({col: "first" for col in passthrough})
    admin1 = admin1.groupby(group_cols, dropna=False, as_index=False).agg(agg)

    admin_sum = (
        admin1.groupby([col for col in key_cols if col in admin1.columns], dropna=False, as_index=False)[metric_cols]
        .sum()
    )
    country_keys = [col for col in key_cols if col in country.columns]
    country_for_delta = country[country_keys + metric_cols + [col for col in country.columns if col not in country_keys + metric_cols]].copy()
    compare = country_for_delta.merge(admin_sum, on=country_keys, how="left", suffixes=("_country", "_admin"))

    unknown_rows = []
    for _, row in compare.iterrows():
        deltas = {}
        has_delta = False
        for metric in metric_cols:
            country_value = float(row.get(f"{metric}_country", row.get(metric, 0)) or 0)
            admin_value = float(row.get(f"{metric}_admin", 0) or 0)
            delta = country_value - admin_value
            deltas[metric] = delta if delta > tolerance else 0.0
            has_delta = has_delta or deltas[metric] > 0
        if not has_delta:
            continue
        unknown = {}
        for col in country_keys:
            unknown[col] = row.get(col)
        for col in ["iso3", "iso_n3", "country", "country_norm", "year", "month_num", "month", "event_type"]:
            if col in country.columns and col not in unknown:
                unknown[col] = row.get(col)
        unknown[admin1_col] = UNKNOWN_ADMIN1_NORM
        if admin1_label_col:
            unknown[admin1_label_col] = UNKNOWN_ADMIN1_LABEL
        for metric, value in deltas.items():
            unknown[metric] = value
        unknown["hierarchy_reconciled"] = True
        unknown["hierarchy_note"] = "Country total remainder assigned to Unknown admin1"
        unknown_rows.append(unknown)

    admin1["hierarchy_reconciled"] = admin1.get("hierarchy_reconciled", False)
    admin1["hierarchy_note"] = admin1.get("hierarchy_note", "")
    if unknown_rows:
        admin1 = pd.concat([admin1, pd.DataFrame(unknown_rows)], ignore_index=True, sort=False)
    return admin1


def aggregate_country_from_admin1(admin1_frame, key_cols, metric_cols):
    admin1 = admin1_frame.copy()
    metric_cols = _metric_columns(admin1, metric_cols)
    admin1 = ensure_numeric_columns(admin1, metric_cols)
    country_cols = [col for col in key_cols if col in admin1.columns and col != "admin1_norm"]
    passthrough = [
        col for col in ["iso3", "iso_n3", "country", "country_norm", "year", "month_num", "month", "event_type"]
        if col in admin1.columns and col not in country_cols
    ]
    agg = {col: "sum" for col in metric_cols}
    agg.update({col: "first" for col in passthrough})
    return admin1.groupby(country_cols, dropna=False, as_index=False).agg(agg)


def validate_hierarchy_totals(parent_frame, child_frame, key_cols, metric_cols, label, tolerance=1e-6):
    parent = ensure_numeric_columns(parent_frame.copy(), metric_cols)
    child = ensure_numeric_columns(child_frame.copy(), metric_cols)
    keys = [col for col in key_cols if col in parent.columns and col in child.columns]
    child_sum = child.groupby(keys, dropna=False, as_index=False)[metric_cols].sum()
    compare = parent[keys + metric_cols].merge(child_sum, on=keys, how="left", suffixes=("_parent", "_child"))
    mismatches = []
    for metric in metric_cols:
        parent_col = f"{metric}_parent"
        child_col = f"{metric}_child"
        compare[child_col] = compare[child_col].fillna(0)
        bad = compare[(compare[parent_col] - compare[child_col]).abs() > tolerance]
        if not bad.empty:
            mismatches.append((metric, bad))
    if mismatches:
        print(f"[hierarchy validation] {label}: {len(mismatches)} metric mismatch group(s)")
        for metric, bad in mismatches[:3]:
            print(f"[hierarchy validation] {label} metric={metric}")
            print(bad.head(10).to_string(index=False))
    else:
        print(f"[hierarchy validation] {label}: OK")
    return not mismatches


ESTIMATED_DISTRICT_NOTE = "Estimated from governorate totals using district-level weights"
INTEGER_RECONCILE_METRICS = {
    "events",
    "fatalities",
    "population_exposure",
    "displaced",
    "displaced_in",
    "displaced_out",
}


def _normalize_positive(series):
    numeric = pd.to_numeric(series, errors="coerce").fillna(0).clip(lower=0)
    max_value = float(numeric.max()) if len(numeric) else 0.0
    if max_value <= 0:
        return pd.Series(0.0, index=numeric.index, dtype="float64")
    return numeric / max_value


def _weighted_signal(frame, candidates, weight):
    signal = pd.Series(0.0, index=frame.index, dtype="float64")
    found = False
    for col in candidates:
        if col not in frame.columns:
            continue
        normalized = _normalize_positive(frame[col])
        if float(normalized.sum()) <= 0:
            continue
        signal = signal + normalized
        found = True
    if not found:
        return pd.Series(0.0, index=frame.index, dtype="float64")
    return weight * _normalize_positive(signal)


def allocation_weights(frame, preferred_cols=None):
    """Build varied district allocation weights from normalized signals.

    Equal split is only used after conflict, fatality, displacement, exposure,
    priority, vulnerability, population, and area proxies are all unavailable.
    """
    if frame is None or len(frame) == 0:
        return pd.Series(dtype="float64")

    if preferred_cols:
        weights = pd.Series(0.0, index=frame.index, dtype="float64")
        for item in preferred_cols:
            if isinstance(item, (tuple, list)) and len(item) == 2:
                col, multiplier = item
            else:
                col, multiplier = item, 1.0
            if col in frame.columns:
                weights = weights + _normalize_positive(frame[col]) * float(multiplier)
        if float(weights.sum()) > 0:
            return weights

    signal_groups = [
        (("events", "events_basis", "conflict_events", "direct_match_count", "spatial_match_count"), 0.40),
        (("fatalities", "fatalities_basis", "fatality_count"), 0.25),
        (("population_exposure", "population_exposure_basis", "population", "population_best"), 0.20),
        (("displaced_in", "displaced", "displaced_basis", "displacement", "idps"), 0.15),
        (
            (
                "priority_score",
                "priority_score_country",
                "priority_score_global",
                "access_risk",
                "demographic_vulnerability",
                "health_priority_score",
                "education_priority_score",
            ),
            0.10,
        ),
    ]
    weights = pd.Series(0.0, index=frame.index, dtype="float64")
    for candidates, weight in signal_groups:
        weights = weights + _weighted_signal(frame, candidates, weight)
    if float(weights.sum()) > 0:
        return weights

    area_signal = _weighted_signal(
        frame,
        ("area_sqkm", "area_km2", "area_weight", "geometry_area", "shape_area"),
        1.0,
    )
    if float(area_signal.sum()) > 0:
        return area_signal

    return pd.Series(1.0, index=frame.index, dtype="float64")


def allocate_total_by_weights(total_value, weights, integer=False):
    weights = pd.to_numeric(weights, errors="coerce").fillna(0).clip(lower=0)
    if len(weights) == 0:
        return weights

    if float(weights.sum()) <= 0:
        weights = pd.Series(1.0, index=weights.index, dtype="float64")
    shares = weights / float(weights.sum())

    if integer:
        total_int = int(round(float(total_value or 0)))
        if total_int <= 0:
            return pd.Series(0, index=weights.index, dtype="int64")
        raw = shares * total_int
        allocated = raw.astype(int)
        remainder = total_int - int(allocated.sum())
        if remainder > 0:
            fractions = (raw - allocated).sort_values(ascending=False)
            for idx in fractions.index[:remainder]:
                allocated.loc[idx] += 1
        return allocated.astype("int64")

    total_float = float(total_value or 0)
    if total_float <= 0:
        return pd.Series(0.0, index=weights.index, dtype="float64")
    return shares * total_float


def _allocate_difference_integer(total_value, current_values, weights):
    total_int = int(round(float(total_value or 0)))
    current = pd.to_numeric(current_values, errors="coerce").fillna(0).clip(lower=0).round().astype("int64")
    if len(current) == 0:
        return current
    if total_int <= 0:
        return pd.Series(0, index=current.index, dtype="int64")

    current_sum = int(current.sum())
    if current_sum == total_int:
        return current
    if current_sum > total_int:
        scale_weights = current if current_sum > 0 else weights
        return allocate_total_by_weights(total_int, scale_weights, integer=True)

    diff = total_int - current_sum
    return (current + allocate_total_by_weights(diff, weights, integer=True)).astype("int64")


def allocate_difference(total_value, current_values, weights, integer=False):
    if integer:
        return _allocate_difference_integer(total_value, current_values, weights)

    total_value = float(total_value or 0)
    current = pd.to_numeric(current_values, errors="coerce").fillna(0).clip(lower=0)
    current_sum = float(current.sum())
    if len(current) == 0:
        return current
    if total_value <= 0:
        return pd.Series(0.0, index=current.index)
    if current_sum > total_value and current_sum > 0:
        return current * (total_value / current_sum)
    diff = total_value - current_sum
    if diff <= 1e-9:
        return current
    weights = pd.to_numeric(weights, errors="coerce").fillna(0).clip(lower=0)
    if float(weights.sum()) <= 0:
        weights = pd.Series(1.0, index=current.index)
    return current + allocate_total_by_weights(diff, weights, integer=False)


def _metric_weight_columns(metric):
    return {
        "events": [
            ("events", 0.45),
            ("events_basis", 0.45),
            ("fatalities", 0.20),
            ("population_exposure", 0.15),
            ("displaced_in", 0.10),
            ("displaced", 0.10),
            ("area_sqkm", 0.05),
        ],
        "fatalities": [
            ("fatalities", 0.45),
            ("fatalities_basis", 0.45),
            ("events", 0.25),
            ("events_basis", 0.25),
            ("population_exposure", 0.15),
            ("area_sqkm", 0.05),
        ],
        "population_exposure": [
            ("population_exposure", 0.45),
            ("population_exposure_basis", 0.45),
            ("population", 0.25),
            ("events", 0.15),
            ("fatalities", 0.10),
            ("area_sqkm", 0.10),
        ],
        "displaced": [
            ("displaced", 0.35),
            ("displaced_in", 0.35),
            ("events", 0.25),
            ("fatalities", 0.20),
            ("population_exposure", 0.15),
            ("area_sqkm", 0.05),
        ],
        "displaced_in": [
            ("displaced_in", 0.35),
            ("displaced", 0.35),
            ("events", 0.25),
            ("fatalities", 0.20),
            ("population_exposure", 0.15),
            ("area_sqkm", 0.05),
        ],
    }.get(metric)


def reconcile_children_to_parent(
    child_frame,
    parent_values,
    metric_cols,
    source_col="district_value_source",
    integer_metrics=None,
):
    out = ensure_numeric_columns(child_frame, metric_cols)
    integer_metrics = set(INTEGER_RECONCILE_METRICS if integer_metrics is None else integer_metrics)
    estimated = False
    for metric in metric_cols:
        parent_total = float(parent_values.get(metric, 0) or 0)
        if parent_total <= 0:
            continue
        before = float(out[metric].sum())
        metric_weights = allocation_weights(out, preferred_cols=_metric_weight_columns(metric))
        out[metric] = allocate_difference(
            parent_total,
            out[metric],
            metric_weights,
            integer=metric in integer_metrics,
        )
        after = float(pd.to_numeric(out[metric], errors="coerce").fillna(0).sum())
        if abs(before - after) > 1e-6:
            estimated = True
    if estimated:
        if source_col not in out.columns:
            out[source_col] = ESTIMATED_DISTRICT_NOTE
        else:
            out[source_col] = out[source_col].fillna(ESTIMATED_DISTRICT_NOTE)
            empty = out[source_col].astype(str).str.strip().eq("")
            out.loc[empty, source_col] = ESTIMATED_DISTRICT_NOTE
        out["district_estimation_note"] = ESTIMATED_DISTRICT_NOTE
    elif "district_estimation_note" not in out.columns:
        out["district_estimation_note"] = ""
    return out, estimated
