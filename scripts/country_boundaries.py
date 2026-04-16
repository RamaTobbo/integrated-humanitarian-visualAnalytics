from pathlib import Path
import time
import requests
import pandas as pd

# ==========================================
# PATHS
# ==========================================
BASE_DIR = Path(__file__).resolve().parent.parent 
ACLED_COUNTRY_PATH = BASE_DIR / "data" / "cleaned" / "global" / "conflict_country_monthlybytype.csv"
OUTPUT_DIR = BASE_DIR / "data" / "cleaned" / "boundaries" / "countries"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ==========================================
# CONFIG
# ==========================================
RELEASE_TYPE = "gbOpen"   # geoBoundaries open release
BOUNDARY_TYPE = "ADM1"    # country drilldown level
TIMEOUT = 60
SLEEP_SECONDS = 0.2       # small pause between requests

# ==========================================
# HELPERS
# ==========================================
def get_iso3_list_from_acled(csv_path: Path) -> list[str]:
    df = pd.read_csv(csv_path)

    if "iso3" not in df.columns:
        raise ValueError("ACLED file must contain an 'iso3' column.")

    # In your file, iso3 is numeric UN code. Convert to zero-padded iso_n3 first.
    iso_n3_values = (
        pd.to_numeric(df["iso3"], errors="coerce")
        .dropna()
        .astype(int)
        .astype(str)
        .str.zfill(3)
        .unique()
        .tolist()
    )

    return sorted(iso_n3_values)


def load_world_iso_mapping(world_geojson_path: Path) -> dict[str, str]:
    import geopandas as gpd

    world = gpd.read_file(world_geojson_path)

    world["iso_n3"] = world["iso_n3"].astype(str).str.strip().str.zfill(3)
    world["iso_a3"] = world["iso_a3"].astype(str).str.strip().str.upper()

    mapping = {}
    for _, row in world.iterrows():
        iso_n3 = row.get("iso_n3")
        iso_a3 = row.get("iso_a3")
        if iso_n3 and iso_a3 and iso_a3 != "-99":
            mapping[iso_n3] = iso_a3

    return mapping


def get_geoboundaries_metadata(iso3: str, boundary_type: str = "ADM1", release_type: str = "gbOpen") -> dict:
    url = f"https://www.geoboundaries.org/api/current/{release_type}/{iso3}/{boundary_type}/"
    response = requests.get(url, timeout=TIMEOUT)
    response.raise_for_status()
    return response.json()


def extract_geojson_url(metadata: dict) -> str | None:
    # Official metadata commonly exposes gjDownloadURL
    if isinstance(metadata, dict):
        return metadata.get("gjDownloadURL")
    return None


def download_file(url: str, output_path: Path) -> None:
    response = requests.get(url, timeout=TIMEOUT)
    response.raise_for_status()
    output_path.write_bytes(response.content)


def download_country_boundary(iso3: str, boundary_type: str = "ADM1") -> bool:
    try:
        metadata = get_geoboundaries_metadata(iso3, boundary_type=boundary_type, release_type=RELEASE_TYPE)
        geojson_url = extract_geojson_url(metadata)

        if not geojson_url:
            print(f"[SKIP] No gjDownloadURL for {iso3} {boundary_type}")
            return False

        output_path = OUTPUT_DIR / f"{iso3}_{boundary_type.lower()}.geojson"

        if output_path.exists():
            print(f"[EXISTS] {output_path.name}")
            return True

        download_file(geojson_url, output_path)
        print(f"[OK] Saved {output_path.name}")
        return True

    except Exception as e:
        print(f"[FAIL] {iso3} {boundary_type}: {e}")
        return False


# ==========================================
# MAIN
# ==========================================
if __name__ == "__main__":
    world_geojson_path = BASE_DIR / "data" / "raw" / "boundaries" / "world_countries.geojson"

    if not ACLED_COUNTRY_PATH.exists():
        raise FileNotFoundError(f"Missing ACLED file: {ACLED_COUNTRY_PATH}")

    if not world_geojson_path.exists():
        raise FileNotFoundError(f"Missing world boundaries file: {world_geojson_path}")

    iso_n3_list = get_iso3_list_from_acled(ACLED_COUNTRY_PATH)
    iso_mapping = load_world_iso_mapping(world_geojson_path)

    iso3_list = []
    for iso_n3 in iso_n3_list:
        iso3 = iso_mapping.get(iso_n3)
        if iso3:
            iso3_list.append(iso3)
        else:
            print(f"[WARN] No iso_a3 mapping found for iso_n3={iso_n3}")

    iso3_list = sorted(set(iso3_list))

    print(f"Found {len(iso3_list)} countries to download.")

    success_count = 0
    fail_count = 0

    for iso3 in iso3_list:
        ok = download_country_boundary(iso3, boundary_type=BOUNDARY_TYPE)
        if ok:
            success_count += 1
        else:
            fail_count += 1
        time.sleep(SLEEP_SECONDS)

    print("\nDone.")
    print(f"Success: {success_count}")
    print(f"Failed : {fail_count}")