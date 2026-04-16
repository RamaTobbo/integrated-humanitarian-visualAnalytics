from pathlib import Path
import requests

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "data" / "cleaned" / "boundaries" / "countries"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

iso3 = "RUS"
url = f"https://www.geoboundaries.org/api/current/gbOpen/{iso3}/ADM1/"

response = requests.get(url, timeout=60)
print("Status code:", response.status_code)
print("Response text:", response.text[:500])

if response.status_code == 200:
    meta = response.json()
    gj_url = meta.get("gjDownloadURL")
    print("GeoJSON URL:", gj_url)

    if gj_url:
        out_path = OUTPUT_DIR / f"{iso3}_adm1.geojson"
        gj = requests.get(gj_url, timeout=60)
        gj.raise_for_status()
        out_path.write_bytes(gj.content)
        print("Saved to:", out_path)
    else:
        print("No gjDownloadURL found.")
else:
    print("Failed to get metadata.")