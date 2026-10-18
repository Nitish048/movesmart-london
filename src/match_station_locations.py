
import json
import re
from pathlib import Path

import pandas as pd

analytics_path = Path("data/analytics/hourly_station_demand.parquet")
locations_path = Path("data/raw/tfl_bikepoint_locations.json")
output_path = Path("reports/station_matching_diagnostics.csv")

# Get the historical station list.
historical = (
    pd.read_parquet(analytics_path)[["Station Id", "Station Name"]]
    .drop_duplicates()
    .copy()
)

historical["Station Id"] = historical["Station Id"].astype(str).str.strip()


def normalize_name(value):
    """Normalize spacing and capitalization, but preserve name meaning."""
    if pd.isna(value):
        return ""
    value = re.sub(r"\s+", " ", str(value).strip())
    value = re.sub(r"\s*,\s*", ", ", value)
    return value.casefold()


historical["NameKey"] = historical["Station Name"].map(normalize_name)

# Load the current TfL station records.
with locations_path.open("r", encoding="utf-8") as file:
    current_json = json.load(file)

current = pd.DataFrame([
    {
        "CurrentID": str(station.get("id", "")).replace("BikePoints_", ""),
        "CurrentName": station.get("commonName"),
        "Latitude": station.get("lat"),
        "Longitude": station.get("lon"),
    }
    for station in current_json
])

current["CurrentID"] = current["CurrentID"].astype(str).str.strip()
current["NameKey"] = current["CurrentName"].map(normalize_name)

# Exact ID match.
by_id = historical.merge(
    current,
    left_on="Station Id",
    right_on="CurrentID",
    how="left",
)

# Exact normalized-name match.
by_name = historical.merge(
    current,
    on="NameKey",
    how="left",
    suffixes=("_historical", "_current"),
)

id_matches = by_id.set_index("Station Id")
name_matches = by_name.set_index("Station Id")

diagnostics = historical.copy()
diagnostics["ID_Match"] = diagnostics["Station Id"].isin(
    by_id.loc[by_id["Latitude"].notna(), "Station Id"]
)
diagnostics["Name_Match"] = diagnostics["Station Id"].isin(
    by_name.loc[by_name["Latitude"].notna(), "Station Id"]
)

diagnostics["CurrentName_ByID"] = diagnostics["Station Id"].map(
    id_matches["CurrentName"]
)
diagnostics["CurrentID_ByName"] = diagnostics["Station Id"].map(
    name_matches["CurrentID"]
)
diagnostics["Latitude_ByName"] = diagnostics["Station Id"].map(
    name_matches["Latitude"]
)
diagnostics["Longitude_ByName"] = diagnostics["Station Id"].map(
    name_matches["Longitude"]
)

def classify(row):
    id_match = row["ID_Match"]
    name_match = row["Name_Match"]

    if id_match and name_match:
        return "ID_AND_NAME_MATCH"
    if name_match:
        return "NAME_ONLY_MATCH"
    if id_match:
        return "ID_ONLY_REVIEW_REQUIRED"
    return "NO_MATCH_REVIEW_REQUIRED"


diagnostics["MatchStatus"] = diagnostics.apply(classify, axis=1)

output_path.parent.mkdir(parents=True, exist_ok=True)
diagnostics.to_csv(output_path, index=False)

print("HISTORICAL STATION MATCHING DIAGNOSTICS")
print("Historical stations:", len(diagnostics))
print("\nMatch status counts:")
print(diagnostics["MatchStatus"].value_counts().to_string())
print("\nSaved report:", output_path)
print("\nSample stations requiring review:")
print(
    diagnostics.loc[
        diagnostics["MatchStatus"].isin(
            ["ID_ONLY_REVIEW_REQUIRED", "NO_MATCH_REVIEW_REQUIRED"]
        ),
        ["Station Id", "Station Name", "CurrentName_ByID", "MatchStatus"],
    ]
    .head(15)
    .to_string(index=False)
)
