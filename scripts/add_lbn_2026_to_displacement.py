from pathlib import Path

import pandas as pd

from lebanon_displacement_fallback import (
    DISPLACEMENT_ADJUSTED_FLAG_COL,
    DISPLACEMENT_SOURCE_NOTE_COL,
    apply_lebanon_displacement_fallback,
    ensure_displacement_metadata,
    month_num_to_name,
    summarize_country_months,
)

BASE_DIR = Path(__file__).resolve().parent.parent

main_default_path = BASE_DIR / "data" / "cleaned" / "global" / "displacement_admin1_destination_monthly_2024_2026.csv"
main_override_path = BASE_DIR / "data" / "cleaned" / "global" / "displacement_admin1_destination_monthly_2024_2026_override.csv"
main_path = main_override_path if main_override_path.exists() else main_default_path
lbn_2026_path = BASE_DIR / "data" / "cleaned" / "global" / "lebanon_displacement_2026_from_events.csv"


def prepare_displacement_frame(df):
    out = df.copy()

    if "month_num" not in out.columns and "month" in out.columns:
        month_lookup = {
            "january": 1,
            "february": 2,
            "march": 3,
            "april": 4,
            "may": 5,
            "june": 6,
            "july": 7,
            "august": 8,
            "september": 9,
            "october": 10,
            "november": 11,
            "december": 12,
        }
        out["month_num"] = out["month"].astype(str).str.strip().str.lower().map(month_lookup)

    if "month" not in out.columns:
        out["month"] = pd.to_numeric(out["month_num"], errors="coerce").apply(
            lambda value: month_num_to_name(value) if pd.notna(value) else None
        )

    if "country_name" not in out.columns:
        out["country_name"] = out["country"].astype(str).str.title()

    out["country"] = out["country"].astype(str).str.strip().str.lower()
    out["country_name"] = out["country_name"].astype(str).str.strip()
    out["year"] = pd.to_numeric(out["year"], errors="coerce")
    out["month_num"] = pd.to_numeric(out["month_num"], errors="coerce")
    out["admin1_norm"] = out["admin1_norm"].astype(str).str.strip().str.lower()
    out["displaced_in"] = pd.to_numeric(out["displaced_in"], errors="coerce").fillna(0)

    out = ensure_displacement_metadata(out)
    return out


main_df = prepare_displacement_frame(pd.read_csv(main_path))
lbn_df = prepare_displacement_frame(pd.read_csv(lbn_2026_path))

base_columns = [
    "country",
    "country_name",
    "year",
    "month_num",
    "month",
    "admin1_norm",
    "displaced_in",
    DISPLACEMENT_ADJUSTED_FLAG_COL,
    DISPLACEMENT_SOURCE_NOTE_COL,
]

for col in base_columns:
    if col not in main_df.columns:
        main_df[col] = pd.NA
    if col not in lbn_df.columns:
        lbn_df[col] = pd.NA

main_df = main_df.loc[
    ~(
        main_df["country"].eq("lebanon") &
        (main_df["year"] == 2026)
    )
].copy()

all_columns = list(dict.fromkeys([*main_df.columns.tolist(), *lbn_df.columns.tolist()]))
final_df = pd.concat(
    [main_df.reindex(columns=all_columns), lbn_df.reindex(columns=all_columns)],
    ignore_index=True,
)

final_df = apply_lebanon_displacement_fallback(final_df, value_col="displaced_in")
final_df = final_df.sort_values(["country", "year", "month_num", "admin1_norm"]).reset_index(drop=True)
final_df.to_csv(main_path, index=False)

print("Saved destination displacement file:", main_path)
print("Lebanon 2026 rows written:", int(
    (
        final_df["country"].eq("lebanon") &
        (final_df["year"] == 2026)
    ).sum()
))

summary = summarize_country_months(final_df, country="lebanon", value_col="displaced_in")
print("\nLebanon February and March 2026 destination totals:")
if summary.empty:
    print("No Lebanon February or March 2026 rows found.")
else:
    print(summary.to_string(index=False))
