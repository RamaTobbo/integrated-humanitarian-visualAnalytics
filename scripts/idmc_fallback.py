from pathlib import Path
import re
import unicodedata

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
IDMC_PATH = (
    BASE_DIR / "data" / "cleaned" / "displacement"
    / "IDMC_Internal_Displacement_Conflict-Violence_Disasters.xlsx"
)

# ISO3 → normalized country name matching the pipeline's clean_country_names output.
# Extend this dict whenever IDMC adds a new country.
ISO3_TO_COUNTRY: dict[str, str] = {
    "AFG": "afghanistan",
    "AGO": "angola",
    "ARM": "armenia",
    "AZE": "azerbaijan",
    "BDI": "burundi",
    "BEN": "benin",
    "BGD": "bangladesh",
    "BIH": "bosnia and herzegovina",
    "BFA": "burkina faso",
    "BRA": "brazil",
    "CAF": "central african republic",
    "CMR": "cameroon",
    "COD": "democratic republic of the congo",
    "COG": "republic of congo",
    "COL": "colombia",
    "CYP": "cyprus",
    "DJI": "djibouti",
    "DZA": "algeria",
    "ECU": "ecuador",
    "EGY": "egypt",
    "ERI": "eritrea",
    "ETH": "ethiopia",
    "GTM": "guatemala",
    "HND": "honduras",
    "HTI": "haiti",
    "IDN": "indonesia",
    "IND": "india",
    "IRN": "iran",
    "IRQ": "iraq",
    "KEN": "kenya",
    "KGZ": "kyrgyzstan",
    "LBN": "lebanon",
    "LBY": "libya",
    "LKA": "sri lanka",
    "MDG": "madagascar",
    "MEX": "mexico",
    "MLI": "mali",
    "MMR": "myanmar",
    "MOZ": "mozambique",
    "MRT": "mauritania",
    "NER": "niger",
    "NGA": "nigeria",
    "PAK": "pakistan",
    "PER": "peru",
    "PHL": "philippines",
    "PSE": "palestine",
    "RUS": "russia",
    "SDN": "sudan",
    "SEN": "senegal",
    "SLB": "solomon islands",
    "SLE": "sierra leone",
    "SOM": "somalia",
    "SRB": "serbia",
    "SSD": "south sudan",
    "SYR": "syria",
    "TCD": "chad",
    "TGO": "togo",
    "TZA": "tanzania",
    "UGA": "uganda",
    "UKR": "ukraine",
    "VEN": "venezuela",
    "XKX": "kosovo",
    "YEM": "yemen",
    "ZAF": "south africa",
    "ZMB": "zambia",
    "ZWE": "zimbabwe",
}

# Extra name aliases for countries not in the ISO3 dict above
_NAME_ALIASES: dict[str, str] = {
    "syrian arab republic": "syria",
    "russian federation": "russia",
    "state of palestine": "palestine",
    "democratic republic of congo": "democratic republic of the congo",
    "dr congo": "democratic republic of the congo",
    "congo, dem. rep.": "democratic republic of the congo",
    "lao people's democratic republic": "laos",
    "bolivia (plurinational state of)": "bolivia",
    "iran (islamic republic of)": "iran",
    "united republic of tanzania": "tanzania",
    "republic of moldova": "moldova",
    "venezuela, bolivarian republic of": "venezuela",
    "republic of the congo": "republic of congo",
    "congo rep.": "republic of congo",
}


def _normalize(value: str | None) -> str | None:
    if pd.isna(value):
        return None
    value = str(value).strip().lower()
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = (
        value.replace("–", "-").replace("—", "-")
              .replace("_", " ").replace("/", " ")
              .replace(",", " ").replace("’", "'")
    )
    value = re.sub(r"\s+", " ", value).strip()
    return _NAME_ALIASES.get(value, value) or None


def load_idmc_displacement(
    path: str | Path | None = None,
    years: list[int] | None = None,
) -> pd.DataFrame:
    """
    Load IDMC annual conflict stock displacement data.

    Returns a tidy DataFrame with columns:
        country (str, normalized)  –  matches pipeline country names
        year    (int)
        idmc_displacement_total (float)

    One row per country per year. Rows with zero or NaN displacement are dropped.
    The IDMC file typically contains duplicate rows; dedup is applied on (ISO3, Year).
    """
    path = Path(path or IDMC_PATH)
    if not path.exists():
        return pd.DataFrame(columns=["country", "year", "idmc_displacement_total"])

    df = pd.read_excel(path, sheet_name="1_Displacement_data")
    required = ["ISO3", "Name", "Year", "Conflict Stock Displacement"]
    missing_cols = [c for c in required if c not in df.columns]
    if missing_cols:
        raise ValueError(f"IDMC file is missing columns: {missing_cols}")

    df = df[required].copy()
    df.columns = ["iso3", "country_name", "year", "idmc_displacement_total"]

    df["iso3"] = df["iso3"].astype(str).str.strip().str.upper()
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df["idmc_displacement_total"] = pd.to_numeric(
        df["idmc_displacement_total"], errors="coerce"
    )

    df = df.dropna(subset=["iso3", "year"]).copy()
    df["year"] = df["year"].astype(int)

    # Deduplicate — keep highest value row when duplicates exist
    df = df.sort_values("idmc_displacement_total", ascending=False)
    df = df.drop_duplicates(subset=["iso3", "year"], keep="first")

    if years is not None:
        df = df[df["year"].isin(list(years))].copy()

    # Map ISO3 → normalized country name
    df["country"] = df["iso3"].map(ISO3_TO_COUNTRY)

    # For unmapped ISO3 codes, fall back to normalizing the country_name column
    unmapped = df["country"].isna()
    if unmapped.any():
        df.loc[unmapped, "country"] = (
            df.loc[unmapped, "country_name"].apply(_normalize)
        )

    # Drop rows with no usable country name or zero/missing displacement
    df = df[
        df["country"].notna() & (df["idmc_displacement_total"] > 0)
    ].copy()

    return df[["country", "year", "idmc_displacement_total"]].reset_index(drop=True)


def apply_idmc_fallback(
    country_monthly: pd.DataFrame,
    idmc: pd.DataFrame,
    displaced_col: str = "displaced",
    source_col: str = "displacement_source",
    source_note_col: str = "displacement_source_note",
) -> pd.DataFrame:
    """
    For every country-year-month row where displaced_col == 0,
    look up the IDMC annual stock for that (country, year) and fill it in.

    Sets three tracking columns:
        displacement_source      "event"  – observed IOM DTM data
                                 "idmc"   – filled from IDMC annual stock
                                 "none"   – no data from any source
        displacement_source_note  human-readable explanation

    Rules
    -----
    - Event data (IOM DTM > 0) is never overwritten.
    - IDMC is annual stock; the same figure is used for every month of that year.
    - Countries not in IDMC and not in IOM DTM get "none" — callers should
      treat these as NaN rather than 0 to avoid misleading visualisations.
    """
    df = country_monthly.copy()
    df[displaced_col] = pd.to_numeric(df[displaced_col], errors="coerce").fillna(0)

    if source_col not in df.columns:
        df[source_col] = None
    if source_note_col not in df.columns:
        df[source_note_col] = ""

    # Tag rows that already have observed IOM event data
    has_event = df[displaced_col] > 0
    df.loc[has_event, source_col] = "event"

    # Build two lookups:
    #   exact:  (country, year) → idmc_stock
    #   latest: country → (latest_year, idmc_stock)
    # The latest-year lookup covers years beyond the IDMC release (e.g. 2025/2026
    # when only 2024 data exists) by carrying the most recent known annual stock.
    idmc_lk: dict[tuple[str, int], float] = (
        idmc.set_index(["country", "year"])["idmc_displacement_total"].to_dict()
    )
    latest_lk: dict[str, tuple[int, float]] = {}
    for _, row in idmc.sort_values("year").iterrows():
        c, y, v = row["country"], int(row["year"]), float(row["idmc_displacement_total"])
        if v > 0:
            latest_lk[c] = (y, v)

    # Work only on rows missing event data
    miss_idx = df.index[~has_event]
    if miss_idx.empty:
        return df

    temp = df.loc[miss_idx, ["country", "year"]].copy()
    temp["year"] = pd.to_numeric(temp["year"], errors="coerce").fillna(0).astype(int)

    def _resolve(country: str, year: int) -> tuple[float, int]:
        """Return (idmc_value, idmc_year). Falls back to latest year if exact match missing."""
        exact = idmc_lk.get((country, year))
        if exact and exact > 0:
            return exact, year
        latest = latest_lk.get(country)
        if latest:
            return latest[1], latest[0]
        return 0.0, year

    resolved = temp.apply(lambda r: _resolve(r["country"], r["year"]), axis=1)
    temp["_idmc"] = resolved.apply(lambda t: t[0])
    temp["_idmc_year"] = resolved.apply(lambda t: t[1])

    idmc_fill = temp.index[temp["_idmc"] > 0]
    none_fill = temp.index[temp["_idmc"] <= 0]

    # Apply IDMC values
    df.loc[idmc_fill, displaced_col] = temp.loc[idmc_fill, "_idmc"]
    df.loc[idmc_fill, source_col] = "idmc"
    df.loc[idmc_fill, source_note_col] = temp.loc[idmc_fill].apply(
        lambda r: (
            f"IDMC annual conflict stock displacement ({int(r['_idmc_year'])})."
            + (
                f" Used as latest available estimate for {int(r['year'])}."
                if int(r["_idmc_year"]) != int(r["year"]) else ""
            )
            + " National-level figure — no sub-national breakdown available from this source."
        ),
        axis=1,
    )

    # Mark remaining as "none"
    df.loc[none_fill, source_col] = "none"
    existing_notes = df.loc[none_fill, source_note_col].astype(str).str.strip()
    df.loc[none_fill[existing_notes == ""], source_note_col] = (
        "No displacement data available for this country and period."
    )

    return df
