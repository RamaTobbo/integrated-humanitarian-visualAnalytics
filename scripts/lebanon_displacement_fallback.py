import pandas as pd


OBSERVED_DISPLACEMENT_SOURCE_NOTE = "Observed displacement source data."

DISPLACEMENT_ADJUSTED_FLAG_COL = "displacement_adjusted_flag"
DISPLACEMENT_SOURCE_NOTE_COL = "displacement_source_note"

LEBANON_COUNTRY_FALLBACK_RULES = [
    {
        "year": 2026,
        "month_num": 2,
        "target_total": 970_443,
        "apply_below_ratio": 0.999,
        "admin1_shares": {
            "al nabatieh": 0.32,
            "south": 0.31,
            "bekaa": 0.12,
            "baalbek-hermel": 0.10,
            "beirut": 0.09,
            "mount lebanon": 0.04,
            "north": 0.01,
            "akkar": 0.01,
        },
        "note": (
            "Adjusted fallback using a Lebanon admin1 displacement profile that "
            "prioritizes the main conflict-origin and reception pressure areas in "
            "South, Al Nabatieh, Bekaa, Baalbek-Hermel, and Beirut because "
            "February 2026 is missing in the source dataset."
        ),
    },
    {
        "year": 2026,
        "month_num": 3,
        "target_total": 1_200_000,
        "apply_below_ratio": 0.90,
        "admin1_shares": {
            "al nabatieh": 0.32,
            "south": 0.31,
            "bekaa": 0.12,
            "baalbek-hermel": 0.10,
            "beirut": 0.09,
            "mount lebanon": 0.04,
            "north": 0.01,
            "akkar": 0.01,
        },
        "note": (
            "Adjusted fallback using a Lebanon March 2026 country estimate of about "
            "1.2 million, distributed across admin1 using an explicit Lebanon 2026 "
            "profile that emphasizes South, Al Nabatieh, Bekaa, Baalbek-Hermel, "
            "and Beirut over Mount Lebanon because the source dataset is missing "
            "or undercounting that month."
        ),
    },
]


def month_num_to_name(month_num):
    month_map = {
        1: "January",
        2: "February",
        3: "March",
        4: "April",
        5: "May",
        6: "June",
        7: "July",
        8: "August",
        9: "September",
        10: "October",
        11: "November",
        12: "December",
    }
    return month_map.get(int(month_num), None)


def _normalize_adjusted_flag(series):
    truthy = {"true", "1", "yes", "y", "t"}
    return series.apply(
        lambda value: value
        if isinstance(value, bool)
        else str(value).strip().lower() in truthy
        if pd.notna(value)
        else False
    )


def ensure_displacement_metadata(df):
    out = df.copy()

    if DISPLACEMENT_ADJUSTED_FLAG_COL not in out.columns:
        out[DISPLACEMENT_ADJUSTED_FLAG_COL] = False
    out[DISPLACEMENT_ADJUSTED_FLAG_COL] = _normalize_adjusted_flag(
        out[DISPLACEMENT_ADJUSTED_FLAG_COL]
    )

    if DISPLACEMENT_SOURCE_NOTE_COL not in out.columns:
        out[DISPLACEMENT_SOURCE_NOTE_COL] = OBSERVED_DISPLACEMENT_SOURCE_NOTE

    out[DISPLACEMENT_SOURCE_NOTE_COL] = (
        out[DISPLACEMENT_SOURCE_NOTE_COL]
        .fillna("")
        .astype(str)
        .str.strip()
    )
    out.loc[
        (~out[DISPLACEMENT_ADJUSTED_FLAG_COL]) &
        (out[DISPLACEMENT_SOURCE_NOTE_COL] == ""),
        DISPLACEMENT_SOURCE_NOTE_COL,
    ] = OBSERVED_DISPLACEMENT_SOURCE_NOTE

    return out


def combine_unique_text(values):
    unique_values = []
    for value in values:
        text = str(value).strip()
        if not text or text == "nan" or text in unique_values:
            continue
        unique_values.append(text)
    return " | ".join(unique_values)


def _allocate_total_from_shares(total_value, share_frame, value_col):
    total_value = int(round(float(total_value)))
    if total_value < 0:
        total_value = 0

    shares = share_frame["share"].astype(float).fillna(0.0)
    raw = shares * total_value
    allocated = raw.apply(lambda value: int(value)).astype(int)
    remainder = total_value - int(allocated.sum())

    if remainder > 0:
        order = (raw - allocated).sort_values(ascending=False).index.tolist()
        for idx in order[:remainder]:
            allocated.loc[idx] += 1

    result = share_frame.copy()
    result[value_col] = allocated.astype(int)
    return result


def _latest_positive_share_frame(df, value_col, year, month_num):
    earlier_rows = df[
        (df["country"].astype(str).str.strip().str.lower() == "lebanon") &
        (
            (df["year"] < year) |
            ((df["year"] == year) & (df["month_num"] < month_num))
        ) &
        (pd.to_numeric(df[value_col], errors="coerce").fillna(0) > 0)
    ].copy()

    if earlier_rows.empty:
        return pd.DataFrame(columns=["admin1_norm", "share"]), None

    if DISPLACEMENT_ADJUSTED_FLAG_COL in earlier_rows.columns:
        observed_rows = earlier_rows[~_normalize_adjusted_flag(earlier_rows[DISPLACEMENT_ADJUSTED_FLAG_COL])].copy()
        if not observed_rows.empty:
            earlier_rows = observed_rows

    earlier_rows["year"] = pd.to_numeric(earlier_rows["year"], errors="coerce")
    earlier_rows["month_num"] = pd.to_numeric(earlier_rows["month_num"], errors="coerce")
    latest_period = (
        earlier_rows[["year", "month_num", "month"]]
        .drop_duplicates()
        .sort_values(["year", "month_num"])
        .iloc[-1]
    )

    basis_rows = earlier_rows[
        (earlier_rows["year"] == int(latest_period["year"])) &
        (earlier_rows["month_num"] == int(latest_period["month_num"]))
    ].copy()

    basis_rows[value_col] = pd.to_numeric(basis_rows[value_col], errors="coerce").fillna(0)
    basis_rows = (
        basis_rows.groupby("admin1_norm", as_index=False)[value_col]
        .sum()
        .sort_values(["admin1_norm"])
        .reset_index(drop=True)
    )
    total_basis = float(basis_rows[value_col].sum())
    if total_basis <= 0:
        return pd.DataFrame(columns=["admin1_norm", "share"]), None

    basis_rows["share"] = basis_rows[value_col] / total_basis
    basis_period = {
        "year": int(latest_period["year"]),
        "month_num": int(latest_period["month_num"]),
        "month": str(latest_period.get("month", "")).strip() or month_num_to_name(latest_period["month_num"]),
    }
    return basis_rows[["admin1_norm", "share"]], basis_period


def _share_frame_from_rule(rule):
    admin1_shares = rule.get("admin1_shares") or {}
    if not admin1_shares:
        return pd.DataFrame(columns=["admin1_norm", "share"]), None

    share_frame = (
        pd.Series(admin1_shares, dtype="float64")
        .rename_axis("admin1_norm")
        .reset_index(name="share")
    )
    share_frame["admin1_norm"] = share_frame["admin1_norm"].astype(str).str.strip()
    share_frame["share"] = pd.to_numeric(share_frame["share"], errors="coerce").fillna(0.0)
    share_frame = share_frame[share_frame["share"] > 0].copy()
    total_share = float(share_frame["share"].sum())
    if total_share <= 0:
        return pd.DataFrame(columns=["admin1_norm", "share"]), None
    share_frame["share"] = share_frame["share"] / total_share
    return share_frame[["admin1_norm", "share"]], {
        "label": "custom Lebanon 2026 profile",
    }


def apply_lebanon_displacement_fallback(df, value_col="displaced_in"):
    out = ensure_displacement_metadata(df)

    if value_col not in out.columns:
        return out

    if "country" not in out.columns or "admin1_norm" not in out.columns:
        return out

    out["country"] = out["country"].astype(str).str.strip().str.lower()
    out["admin1_norm"] = out["admin1_norm"].astype(str).str.strip()
    out["year"] = pd.to_numeric(out["year"], errors="coerce")
    out["month_num"] = pd.to_numeric(out["month_num"], errors="coerce")
    out[value_col] = pd.to_numeric(out[value_col], errors="coerce").fillna(0)

    if "month" not in out.columns:
        out["month"] = out["month_num"].apply(month_num_to_name)
    else:
        out["month"] = out["month"].fillna("").astype(str).str.strip()

    if "displaced_from" in out.columns:
        out["displaced_from"] = pd.to_numeric(out["displaced_from"], errors="coerce").fillna(0)

    if "country_name" in out.columns:
        out["country_name"] = out["country_name"].fillna("").astype(str).str.strip()

    for rule in LEBANON_COUNTRY_FALLBACK_RULES:
        year = int(rule["year"])
        month_num = int(rule["month_num"])
        target_total = int(rule["target_total"])
        apply_below = float(rule["apply_below_ratio"])

        month_mask = (
            out["country"].eq("lebanon") &
            (out["year"] == year) &
            (out["month_num"] == month_num)
        )
        current_total = float(out.loc[month_mask, value_col].sum())
        existing_adjusted = bool(
            month_mask.any() and
            DISPLACEMENT_ADJUSTED_FLAG_COL in out.columns and
            _normalize_adjusted_flag(out.loc[month_mask, DISPLACEMENT_ADJUSTED_FLAG_COL]).any()
        )
        threshold = target_total * apply_below
        should_apply = out.loc[month_mask].empty or current_total < threshold or existing_adjusted

        if not should_apply:
            continue

        share_frame, basis_period = _share_frame_from_rule(rule)
        if share_frame.empty:
            share_frame, basis_period = _latest_positive_share_frame(out, value_col, year, month_num)
        if share_frame.empty:
            continue

        replacement = _allocate_total_from_shares(target_total, share_frame, value_col)
        replacement["country"] = "lebanon"
        replacement["year"] = year
        replacement["month_num"] = month_num
        replacement["month"] = month_num_to_name(month_num)

        if "country_name" in out.columns:
            replacement["country_name"] = "Lebanon"
        if "displaced_from" in out.columns:
            replacement["displaced_from"] = 0

        if basis_period and basis_period.get("label"):
            basis_label = basis_period["label"]
        elif basis_period:
            basis_label = f"{basis_period['month']} {basis_period['year']}"
        else:
            basis_label = "the latest observed period"
        replacement[DISPLACEMENT_ADJUSTED_FLAG_COL] = True
        replacement[DISPLACEMENT_SOURCE_NOTE_COL] = (
            f"{rule['note']} Basis period: {basis_label}. "
            f"Original total before adjustment: {current_total:,.0f}. "
            f"Adjusted total: {target_total:,.0f}."
        )

        missing_columns = [col for col in out.columns if col not in replacement.columns]
        for col in missing_columns:
            if col == DISPLACEMENT_ADJUSTED_FLAG_COL:
                replacement[col] = True
            elif col == DISPLACEMENT_SOURCE_NOTE_COL:
                replacement[col] = replacement[DISPLACEMENT_SOURCE_NOTE_COL]
            else:
                replacement[col] = pd.NA

        replacement = replacement[out.columns]
        out = out.loc[~month_mask].copy()
        out = pd.concat([out, replacement], ignore_index=True)

    out = ensure_displacement_metadata(out)
    return (
        out.sort_values(
            [col for col in ["country", "year", "month_num", "admin1_norm"] if col in out.columns]
        )
        .reset_index(drop=True)
    )


def summarize_country_months(df, country="lebanon", value_col="displaced_in", months=None):
    if months is None:
        months = [(2026, 2), (2026, 3)]

    if value_col not in df.columns or "country" not in df.columns:
        return pd.DataFrame(columns=["country", "year", "month_num", "month", value_col])

    work = ensure_displacement_metadata(df)
    work["country"] = work["country"].astype(str).str.strip().str.lower()
    work["year"] = pd.to_numeric(work["year"], errors="coerce")
    work["month_num"] = pd.to_numeric(work["month_num"], errors="coerce")
    work[value_col] = pd.to_numeric(work[value_col], errors="coerce").fillna(0)

    month_pairs = {(int(year), int(month_num)) for year, month_num in months}
    summary = work[
        work["country"].eq(country.lower()) &
        work.apply(lambda row: (int(row["year"]), int(row["month_num"])) in month_pairs, axis=1)
    ].copy()

    if summary.empty:
        return pd.DataFrame(
            columns=[
                "country",
                "year",
                "month_num",
                "month",
                value_col,
                DISPLACEMENT_ADJUSTED_FLAG_COL,
                DISPLACEMENT_SOURCE_NOTE_COL,
            ]
        )

    return (
        summary.groupby(["country", "year", "month_num", "month"], as_index=False)
        .agg({
            value_col: "sum",
            DISPLACEMENT_ADJUSTED_FLAG_COL: "max",
            DISPLACEMENT_SOURCE_NOTE_COL: combine_unique_text,
        })
        .sort_values(["year", "month_num"])
        .reset_index(drop=True)
    )
