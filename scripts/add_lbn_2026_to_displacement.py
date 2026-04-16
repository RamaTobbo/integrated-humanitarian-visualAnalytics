from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent

# main file already used by your app
main_path = BASE_DIR / "data" / "cleaned" / "global" / "displacement_admin1_destination_monthly_2024_2026.csv"

# your new Lebanon 2026 file
lbn_2026_path = BASE_DIR / "data" / "cleaned" / "global" / "lebanon_displacement_2026_from_events.csv"

main_df = pd.read_csv(main_path)
lbn_df = pd.read_csv(lbn_2026_path)

# rename columns from your Lebanon file
lbn_df = lbn_df.rename(columns={
    "month": "month_num",
    "displaced_country": "displaced_in"
})

# add month names
month_name_map = {
    1: "January", 2: "February", 3: "March", 4: "April",
    5: "May", 6: "June", 7: "July", 8: "August",
    9: "September", 10: "October", 11: "November", 12: "December"
}
lbn_df["month"] = lbn_df["month_num"].map(month_name_map)

# add country_name column
lbn_df["country_name"] = "Lebanon"

# keep same columns as main file
needed_cols = ["country", "country_name", "year", "month_num", "month", "admin1_norm", "displaced_in"]

for col in needed_cols:
    if col not in lbn_df.columns:
        lbn_df[col] = None

lbn_df = lbn_df[needed_cols].copy()

# keep only same columns from main too
main_df = main_df[needed_cols].copy()

# remove any old Lebanon 2026 rows first
main_df = main_df[~((main_df["country"] == "lebanon") & (main_df["year"] == 2026))].copy()

# append the new Lebanon 2026 rows
final_df = pd.concat([main_df, lbn_df], ignore_index=True)

# save back
final_df.to_csv(main_path, index=False)

print("Done.")
print("Saved to:", main_path)
print("Lebanon 2026 rows added:", len(lbn_df))