import pandas as pd


CUMULATIVE_DISPLACEMENT_NOTE = (
    "Values represent cumulative displacement movements, not unique individuals."
)

DISPLACEMENT_AGGREGATION_LABELS = {
    "latest": "Latest displacement snapshot",
    "peak": "Peak displacement snapshot",
    "cumulative": "Total displacement movements",
}


def _empty_period_frame(year_col="year", month_num_col="month_num", month_col="month"):
    return pd.DataFrame(columns=[year_col, month_num_col, month_col])


def _normalize_period_frame(frame, year_col="year", month_num_col="month_num", month_col="month"):
    if frame is None or frame.empty:
        return _empty_period_frame(year_col, month_num_col, month_col)

    required = {year_col, month_num_col}
    if not required.issubset(frame.columns):
        return _empty_period_frame(year_col, month_num_col, month_col)

    cols = [year_col, month_num_col]
    if month_col in frame.columns:
        cols.append(month_col)
    period = frame[cols].copy()
    period[year_col] = pd.to_numeric(period[year_col], errors="coerce")
    period[month_num_col] = pd.to_numeric(period[month_num_col], errors="coerce")
    if month_col not in period.columns:
        period[month_col] = ""
    period[month_col] = period[month_col].astype(str).str.strip()
    period = period[
        period[year_col].notna() &
        period[month_num_col].notna() &
        period[month_col].ne("nan")
    ].copy()
    if period.empty:
        return _empty_period_frame(year_col, month_num_col, month_col)

    period[year_col] = period[year_col].astype(int)
    period[month_num_col] = period[month_num_col].astype(int)
    return (
        period[[year_col, month_num_col, month_col]]
        .drop_duplicates()
        .sort_values([year_col, month_num_col, month_col])
        .reset_index(drop=True)
    )


def build_available_periods(
    *frames,
    intersection=False,
    year_col="year",
    month_num_col="month_num",
    month_col="month",
):
    period_frames = [
        _normalize_period_frame(
            frame,
            year_col=year_col,
            month_num_col=month_num_col,
            month_col=month_col,
        )
        for frame in frames
    ]
    period_frames = [frame for frame in period_frames if not frame.empty]

    if not period_frames:
        return _empty_period_frame(year_col, month_num_col, month_col)

    if not intersection:
        return (
            pd.concat(period_frames, ignore_index=True)
            .drop_duplicates(subset=[year_col, month_num_col])
            .sort_values([year_col, month_num_col, month_col])
            .reset_index(drop=True)
        )

    shared = period_frames[0][[year_col, month_num_col]].drop_duplicates()
    for frame in period_frames[1:]:
        shared = shared.merge(
            frame[[year_col, month_num_col]].drop_duplicates(),
            on=[year_col, month_num_col],
            how="inner",
        )
        if shared.empty:
            return _empty_period_frame(year_col, month_num_col, month_col)

    month_lookup = (
        pd.concat(period_frames, ignore_index=True)
        .drop_duplicates(subset=[year_col, month_num_col, month_col])
        .sort_values([year_col, month_num_col, month_col])
    )
    return (
        shared.merge(
            month_lookup[[year_col, month_num_col, month_col]],
            on=[year_col, month_num_col],
            how="left",
        )
        .drop_duplicates(subset=[year_col, month_num_col])
        .sort_values([year_col, month_num_col, month_col])
        .reset_index(drop=True)
    )


def get_latest_period(
    *frames,
    intersection=False,
    year_col="year",
    month_num_col="month_num",
    month_col="month",
):
    periods = build_available_periods(
        *frames,
        intersection=intersection,
        year_col=year_col,
        month_num_col=month_num_col,
        month_col=month_col,
    )
    if periods.empty:
        return None

    last = periods.iloc[-1]
    return {
        "year": int(last[year_col]),
        "month_num": int(last[month_num_col]),
        "month": str(last.get(month_col, "")).strip(),
    }


def format_period_label(period):
    if not period:
        return ""

    month = str(period.get("month", "")).strip()
    year = period.get("year")
    if year in (None, ""):
        return month
    if month:
        return f"{month} {int(year)}"
    return str(int(year))


def filter_to_period(frame, period, year_col="year", month_num_col="month_num"):
    if frame is None:
        return pd.DataFrame()
    if not period:
        return frame.iloc[0:0].copy()

    filtered = frame.copy()
    filtered[year_col] = pd.to_numeric(filtered[year_col], errors="coerce")
    filtered[month_num_col] = pd.to_numeric(filtered[month_num_col], errors="coerce")
    return filtered[
        (filtered[year_col] == int(period["year"])) &
        (filtered[month_num_col] == int(period["month_num"]))
    ].copy()


def _empty_group_frame(group_cols, value_col):
    return pd.DataFrame(columns=[*group_cols, value_col])


def aggregate_displacement(
    frame,
    group_cols,
    value_col,
    mode="latest",
    period=None,
    year_col="year",
    month_num_col="month_num",
    month_col="month",
):
    if frame is None or frame.empty or value_col not in frame.columns:
        return _empty_group_frame(group_cols, value_col), None

    work = frame.copy()
    work[value_col] = pd.to_numeric(work[value_col], errors="coerce").fillna(0)

    if mode == "cumulative":
        grouped = (
            work.groupby(list(group_cols), as_index=False)[value_col]
            .sum()
            .sort_values(list(group_cols))
            .reset_index(drop=True)
        )
        return grouped, None

    if mode == "peak":
        monthly = (
            work.groupby([*group_cols, year_col, month_num_col], as_index=False)[value_col]
            .sum()
        )
        if monthly.empty:
            return _empty_group_frame(group_cols, value_col), None
        monthly = monthly.sort_values(
            [value_col, year_col, month_num_col],
            ascending=[False, False, False],
        )
        peak = (
            monthly.drop_duplicates(subset=list(group_cols), keep="first")
            [[*group_cols, value_col]]
            .sort_values(list(group_cols))
            .reset_index(drop=True)
        )
        return peak, None

    snapshot_period = period or get_latest_period(
        work,
        year_col=year_col,
        month_num_col=month_num_col,
        month_col=month_col,
    )
    snapshot = filter_to_period(
        work,
        snapshot_period,
        year_col=year_col,
        month_num_col=month_num_col,
    )
    if snapshot.empty:
        return _empty_group_frame(group_cols, value_col), snapshot_period

    grouped = (
        snapshot.groupby(list(group_cols), as_index=False)[value_col]
        .sum()
        .sort_values(list(group_cols))
        .reset_index(drop=True)
    )
    return grouped, snapshot_period


def get_latest_displacement_snapshot(frame, group_cols, value_col, period=None):
    return aggregate_displacement(
        frame,
        group_cols=group_cols,
        value_col=value_col,
        mode="latest",
        period=period,
    )


def get_peak_displacement(frame, group_cols, value_col):
    grouped, _ = aggregate_displacement(
        frame,
        group_cols=group_cols,
        value_col=value_col,
        mode="peak",
    )
    return grouped


def describe_displacement_aggregation(mode="latest", period=None):
    label = DISPLACEMENT_AGGREGATION_LABELS.get(mode, mode.title())
    if mode == "latest":
        period_label = format_period_label(period)
        if period_label:
            return f"{label} ({period_label})"
    return label
