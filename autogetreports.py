import requests
import csv

url = "https://api.reliefweb.int/v2/reports"

params = [
    ("appname", "rama-dv-projectO6psRrKLDsTUVEJcs24xDS"),
    ("limit", 50),
    ("filter[field]", "format.name"),
    ("filter[value]", "Situation Report"),
    ("fields[include][]", "title"),
    ("fields[include][]", "date"),
    ("fields[include][]", "country"),
    ("fields[include][]", "source"),
    ("fields[include][]", "url"),
]

res = requests.get(url, params=params)

print("Status code:", res.status_code)
print("Final URL:", res.url)
print("Response preview:")
print(res.text[:500])

if res.status_code != 200:
    print("Request failed")
    raise SystemExit

data = res.json()

if "data" not in data:
    print("ERROR: API did not return expected data")
    raise SystemExit

rows = []

for item in data["data"]:
    fields = item.get("fields", {})

    date_info = fields.get("date", {})
    report_date = (
        date_info.get("created", "")
        or date_info.get("original", "")
        or date_info.get("changed", "")
    )

    source_list = fields.get("source", [])
    source_name = source_list[0].get("name", "") if source_list else ""

    country_list = fields.get("country", [])
    country_name = country_list[0].get("name", "") if country_list else "Unknown"

    rows.append({
        "date": report_date,
        "country": country_name,
        "source": source_name,
        "title": fields.get("title", ""),
        "source_url": fields.get("url", "")
    })

with open("reliefweb_global.csv", "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=["date", "country", "source", "title", "source_url"]
    )
    writer.writeheader()
    writer.writerows(rows)

print("CSV created successfully: reliefweb_updates.csv")