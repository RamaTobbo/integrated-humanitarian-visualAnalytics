from pathlib import Path
import pandas as pd
import unicodedata
import re

BASE_DIR = Path(__file__).resolve().parent.parent

# CHANGE THIS to your actual displacement raw file path
DISPLACEMENT_RAW_PATH = BASE_DIR / "data" / "raw" / "displacement" / "lebanon_displacement_flow.csv"

OUTPUT_DEST_PATH = BASE_DIR / "data" / "cleaned" / "lebanon" / "lebanon_displacement_admin1_destination_monthly.csv"
OUTPUT_ORIGIN_PATH = BASE_DIR / "data" / "cleaned" / "lebanon" / "lebanon_displacement_admin1_origin_monthly.csv"


def normalize_text(value):
    if pd.isna(value):
        return None
    value = str(value).strip().lower()
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.replace("–", "-").replace("—", "-").replace("_", " ")
    value = value.replace("/", " ")
    value = value.replace(",", " ")
    value = re.sub(r"\s+", " ", value).strip()
    return value


def standardize_lebanon_admin1(value):
    value = normalize_text(value)
    if value is None:
        return None

    mapping = {
        "akkar": "akkar",
        "aakkar": "akkar",

        "beirut": "beirut",
        "beyrouth": "beirut",

        "bekaa": "bekaa",
        "beqaa": "bekaa",

        "baalbek-el hermel": "baalbek-hermel",
        "baalbek el hermel": "baalbek-hermel",
        "baalbek-hermel": "baalbek-hermel",

        "mount lebanon": "mount lebanon",
        "mont-liban": "mount lebanon",
        "mont liban": "mount lebanon",

        "north": "north",
        "liban-nord": "north",
        "liban nord": "north",

        "south": "south",
        "liban-sud": "south",
        "liban sud": "south",

        "el nabatieh": "al nabatieh",
        "nabatieh": "al nabatieh",
        "al nabatieh": "al nabatieh",
        "nabatyeh": "al nabatieh",
        "nabatiye": "al nabatieh",
        "nabatîyé": "al nabatieh",
    }

    return mapping.get(value, value)


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


def main():
    df = pd.read_csv(DISPLACEMENT_RAW_PATH)

    # expected columns from your file:
    # admin0Name, admin1Name, admin2Name, idpOriginAdmin1Name,
    # numPresentIdpInd, reportingDate, yearReportingDate, monthReportingDate, displacementReason

    # Lebanon only
    df = df[df["admin0Name"].astype(str).str.strip().str.lower() == "lebanon"].copy()

    # numeric conversions
    df["numPresentIdpInd"] = pd.to_numeric(df["numPresentIdpInd"], errors="coerce").fillna(0)
    df["year"] = pd.to_numeric(df["yearReportingDate"], errors="coerce")
    df["month_num"] = pd.to_numeric(df["monthReportingDate"], errors="coerce")

    df = df[df["year"].notna() & df["month_num"].notna()].copy()
    df["year"] = df["year"].astype(int)
    df["month_num"] = df["month_num"].astype(int)
    df["month"] = df["month_num"].apply(month_num_to_name)

    # destination admin1 = where IDPs are present now
    df["admin1_dest_norm"] = df["admin1Name"].apply(standardize_lebanon_admin1)

    # origin admin1 = where they came from
    df["admin1_origin_norm"] = df["idpOriginAdmin1Name"].apply(standardize_lebanon_admin1)

    # destination aggregation
    dest = (
        df.dropna(subset=["admin1_dest_norm"])
        .groupby(["year", "month_num", "month", "admin1_dest_norm"], as_index=False)["numPresentIdpInd"]
        .sum()
        .rename(columns={
            "admin1_dest_norm": "admin1_norm",
            "numPresentIdpInd": "displaced_in"
        })
    )

    # origin aggregation
    origin = (
        df.dropna(subset=["admin1_origin_norm"])
        .groupby(["year", "month_num", "month", "admin1_origin_norm"], as_index=False)["numPresentIdpInd"]
        .sum()
        .rename(columns={
            "admin1_origin_norm": "admin1_norm",
            "numPresentIdpInd": "displaced_from"
        })
    )

    OUTPUT_DEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    dest.to_csv(OUTPUT_DEST_PATH, index=False)
    origin.to_csv(OUTPUT_ORIGIN_PATH, index=False)

    print("Saved:", OUTPUT_DEST_PATH)
    print("Saved:", OUTPUT_ORIGIN_PATH)
    print("\nDestination sample:")
    print(dest.head())
    print("\nOrigin sample:")
    print(origin.head())


if __name__ == "__main__":
    main()