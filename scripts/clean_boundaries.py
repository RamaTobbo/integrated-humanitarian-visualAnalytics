import os
import json
import geopandas as gpd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
input_path = os.path.join(
    BASE_DIR,
    "data",
    "raw",
    "boundaries",
    "lbn_admin_boundaries.geojson",
    "lbn_admin2.geojson"
)
output_dir = os.path.join(BASE_DIR, "data", "cleaned", "boundaries")
os.makedirs(output_dir, exist_ok=True)

print("Input path:", input_path)
print("Exists:", os.path.exists(input_path))

with open(input_path, "r", encoding="utf-8") as f:
    geojson_data = json.load(f)

adm2 = gpd.GeoDataFrame.from_features(geojson_data["features"], crs="EPSG:4326")

print(adm2.columns.tolist())
print(adm2.head())
print(adm2.shape)

output_path = os.path.join(output_dir, "lbn_admin2.geojson")
with open(output_path, "w", encoding="utf-8") as f:
    f.write(adm2.to_json())

print("Saved to:", output_path)