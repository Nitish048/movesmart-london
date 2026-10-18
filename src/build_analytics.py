
from pathlib import Path
import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parents[1]
INPUT_FILE = PROJECT_DIR / "data" / "processed" / "journeys.parquet"
OUTPUT_DIR = PROJECT_DIR / "data" / "analytics"

OUTPUT_FILE = OUTPUT_DIR / "hourly_station_demand.parquet"
CHUNK_SIZE = 100_000


def main():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Missing input: {INPUT_FILE}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if OUTPUT_FILE.exists():
        raise FileExistsError(
            f"{OUTPUT_FILE} already exists. Move it before rerunning."
        )

    # Aggregate separate departure and arrival measures.
    departure_parts = []
    arrival_parts = []

    for chunk in pd.read_parquet(
        INPUT_FILE,
        engine="pyarrow",
    ).pipe(lambda df: [df.iloc[i:i + CHUNK_SIZE]
                       for i in range(0, len(df), CHUNK_SIZE)]):
        chunk["Start Date"] = pd.to_datetime(chunk["Start Date"])
        chunk["End Date"] = pd.to_datetime(chunk["End Date"])

        departures = chunk.assign(
            Date=chunk["Start Date"].dt.date,
            Hour=chunk["Start Date"].dt.hour,
        ).groupby(
            ["StartStation Id", "StartStation Name", "Date", "Hour"],
            as_index=False,
        ).agg(
            Departures=("Rental Id", "count"),
            AverageTripDurationSeconds=("Duration", "mean"),
        )

        arrivals = chunk.assign(
            Date=chunk["End Date"].dt.date,
            Hour=chunk["End Date"].dt.hour,
        ).groupby(
            ["EndStation Id", "EndStation Name", "Date", "Hour"],
            as_index=False,
        ).agg(
            Arrivals=("Rental Id", "count"),
        ).rename(
            columns={
                "EndStation Id": "Station Id",
                "EndStation Name": "Station Name",
            }
        )

        departures = departures.rename(
            columns={
                "StartStation Id": "Station Id",
                "StartStation Name": "Station Name",
            }
        )

        departure_parts.append(departures)
        arrival_parts.append(arrivals)

    departures = pd.concat(departure_parts, ignore_index=True)
    arrivals = pd.concat(arrival_parts, ignore_index=True)

    keys = ["Station Id", "Station Name", "Date", "Hour"]

    departures = departures.groupby(keys, as_index=False).agg(
        Departures=("Departures", "sum"),
        AverageTripDurationSeconds=(
            "AverageTripDurationSeconds", "mean"
        ),
    )

    arrivals = arrivals.groupby(keys, as_index=False).agg(
        Arrivals=("Arrivals", "sum")
    )

    result = departures.merge(
        arrivals,
        on=keys,
        how="outer",
    )

    result["Departures"] = result["Departures"].fillna(0).astype("int64")
    result["Arrivals"] = result["Arrivals"].fillna(0).astype("int64")

    result["Date"] = pd.to_datetime(result["Date"])
    result["DayOfWeek"] = result["Date"].dt.day_name()
    result["IsWeekend"] = result["Date"].dt.dayofweek >= 5

    result = result.sort_values(keys).reset_index(drop=True)
    result.to_parquet(OUTPUT_FILE, index=False, compression="snappy")

    print("ANALYTICS DATASET CREATED")
    print(f"Rows: {len(result):,}")
    print(f"Unique stations: {result['Station Id'].nunique():,}")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
