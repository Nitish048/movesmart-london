
from pathlib import Path

import pandas as pd

routes_path = Path("data/analytics/top_20_routes.parquet")
stations_path = Path("data/processed/station_coordinates_candidates.csv")

output_path = Path("data/analytics/top_20_routes_mapped.csv")
unmatched_path = Path("reports/top_routes_unmatched_coordinates.csv")

routes = pd.read_parquet(routes_path)
stations = pd.read_csv(stations_path)

# Use historical station IDs to attach candidate coordinates.
stations["Station Id"] = stations["Station Id"].astype(str).str.strip()

start_locations = stations[
    ["Station Id", "Latitude", "Longitude"]
].rename(columns={
    "Station Id": "StartStation Id",
    "Latitude": "StartLatitude",
    "Longitude": "StartLongitude",
})

end_locations = stations[
    ["Station Id", "Latitude", "Longitude"]
].rename(columns={
    "Station Id": "EndStation Id",
    "Latitude": "EndLatitude",
    "Longitude": "EndLongitude",
})

routes["StartStation Id"] = routes["StartStation Id"].astype(str).str.strip()
routes["EndStation Id"] = routes["EndStation Id"].astype(str).str.strip()

mapped = routes.merge(
    start_locations,
    on="StartStation Id",
    how="left",
    validate="many_to_one",
)

mapped = mapped.merge(
    end_locations,
    on="EndStation Id",
    how="left",
    validate="many_to_one",
)

coordinate_columns = [
    "StartLatitude",
    "StartLongitude",
    "EndLatitude",
    "EndLongitude",
]

has_coordinates = mapped[coordinate_columns].notna().all(axis=1)

mapped[has_coordinates].to_csv(output_path, index=False)
mapped[~has_coordinates].to_csv(unmatched_path, index=False)

print("Top routes:", len(mapped))
print("Routes with both endpoints mapped:", int(has_coordinates.sum()))
print("Routes missing one or both endpoints:", int((~has_coordinates).sum()))
print("Mapped routes saved to:", output_path)
print("Unmatched routes saved to:", unmatched_path)

print("\nMapped route preview:")
print(
    mapped.loc[
        has_coordinates,
        [
            "Rank",
            "StartStation Name",
            "EndStation Name",
            "TripCount",
            "StartLatitude",
            "StartLongitude",
            "EndLatitude",
            "EndLongitude",
        ],
    ].head(5).to_string(index=False)
)
