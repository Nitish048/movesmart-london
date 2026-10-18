
from pathlib import Path

import pandas as pd

INPUT_FILE = Path("data/processed/journeys.parquet")
OUTPUT_DIR = Path("data/analytics")
OUTPUT_FILE = OUTPUT_DIR / "top_20_routes.parquet"
CSV_FILE = Path("reports/top_20_routes.csv")

print("Loading journey data...")

columns = [
    "Rental Id",
    "StartStation Id",
    "StartStation Name",
    "EndStation Id",
    "EndStation Name",
    "Duration",
]

journeys = pd.read_parquet(INPUT_FILE, columns=columns)

print(f"Journeys loaded: {len(journeys):,}")

# Each route is a directed journey:
# A -> B is different from B -> A.
routes = (
    journeys.groupby(
        [
            "StartStation Id",
            "StartStation Name",
            "EndStation Id",
            "EndStation Name",
        ],
        dropna=False,
    )
    .agg(
        TripCount=("Rental Id", "count"),
        AverageDurationSeconds=("Duration", "mean"),
    )
    .reset_index()
)

# Exclude records without valid station identifiers.
routes = routes.dropna(
    subset=["StartStation Id", "EndStation Id"]
)

routes = routes[
    routes["StartStation Id"] != routes["EndStation Id"]
].copy()

routes["AverageDurationMinutes"] = (
    routes["AverageDurationSeconds"] / 60
).round(2)

routes = routes.sort_values(
    ["TripCount", "StartStation Id", "EndStation Id"],
    ascending=[False, True, True],
).reset_index(drop=True)

routes.insert(0, "Rank", range(1, len(routes) + 1))

top_routes = routes.head(20).copy()

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
CSV_FILE.parent.mkdir(parents=True, exist_ok=True)

top_routes.to_parquet(OUTPUT_FILE, index=False)
top_routes.to_csv(CSV_FILE, index=False)

print("\nTOP 20 MOST-TRAVELLED ROUTES")
print(
    top_routes[
        [
            "Rank",
            "StartStation Name",
            "EndStation Name",
            "TripCount",
            "AverageDurationMinutes",
        ]
    ].to_string(index=False)
)

print("\nTotal journeys represented by top 20 routes:",
      f"{top_routes['TripCount'].sum():,}")
print("Parquet saved to:", OUTPUT_FILE)
print("CSV saved to:", CSV_FILE)
