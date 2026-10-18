
import json
from pathlib import Path

import pandas as pd

analytics_path = Path("data/analytics/hourly_station_demand.parquet")
locations_path = Path("data/raw/tfl_bikepoint_locations.json")
output_path = Path("data/processed/station_coordinates_candidates.csv")

historical = (
    pd.read_parquet(analytics_path)[["Station Id", "Station Name"]]
    .drop_duplicates()
    .copy()
)

historical["Station Id"] = historical["Station Id"].astype(str).str.strip()
historical["Station Name"] = historical["Station Name"].astype(str).str.strip()

with locations_path.open("r", encoding="utf-8") as file:
    current_json = json.load(file)

current = pd.DataFrame([
    {
        "CurrentID": str(s.get("id", "")).replace("BikePoints_", ""),
        "CurrentName": s.get("commonName"),
        "Latitude": s.get("lat"),
        "Longitude": s.get("lon"),
    }
    for s in current_json
])

current["CurrentID"] = current["CurrentID"].astype(str).str.strip()

def normalize(value):
    return " ".join(str(value).casefold().split()).replace(" ,", ",")

historical["NameKey"] = historical["Station Name"].map(normalize)
current["NameKey"] = current["CurrentName"].map(normalize)

# Accept only rows where both ID and normalized name match.
candidates = historical.merge(
    current,
    left_on=["Station Id", "NameKey"],
    right_on=["CurrentID", "NameKey"],
    how="inner",
)

# Reject missing or invalid coordinates.
candidates = candidates.dropna(subset=["Latitude", "Longitude"])
candidates = candidates[
    candidates["Latitude"].between(51.0, 52.0)
    & candidates["Longitude"].between(-1.0, 0.5)
]

result = candidates[
    ["Station Id", "Station Name", "Latitude", "Longitude"]
].drop_duplicates(subset=["Station Id"])

output_path.parent.mkdir(parents=True, exist_ok=True)
result.to_csv(output_path, index=False)

print("Candidate coordinate records:", len(result))
print("Historical stations:", len(historical))
print("Stations without candidate coordinates:", len(historical) - len(result))
print("Saved to:", output_path)
print("\nSample:")
print(result.head(10).to_string(index=False))
