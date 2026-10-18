
from pathlib import Path
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
INPUT_FILE = ROOT / "data" / "analytics" / "hourly_station_demand.parquet"
REPORT_DIR = ROOT / "reports"


def main():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    parquet = pq.ParquetFile(INPUT_FILE)
    frames = []

    for batch in parquet.iter_batches(batch_size=100_000):
        frames.append(batch.to_pandas())

    df = pd.concat(frames, ignore_index=True)

    # 1. Top stations by departures
    top_stations = (
        df.groupby(["Station Id", "Station Name"], as_index=False)
        .agg(
            Departures=("Departures", "sum"),
            Arrivals=("Arrivals", "sum"),
        )
        .sort_values("Departures", ascending=False)
        .head(15)
    )

    # 2. Demand by hour
    hourly = (
        df.groupby("Hour", as_index=False)
        .agg(
            Departures=("Departures", "sum"),
            Arrivals=("Arrivals", "sum"),
        )
        .sort_values("Hour")
    )

    # 3. Weekday vs weekend
    day_type = (
        df.groupby("IsWeekend", as_index=False)
        .agg(
            Departures=("Departures", "sum"),
            Arrivals=("Arrivals", "sum"),
            StationHourRecords=("Station Id", "size"),
        )
    )
    day_type["DayType"] = day_type["IsWeekend"].map(
        {False: "Weekday", True: "Weekend"}
    )

    # 4. Departure-arrival balance by station
    balance = (
        df.groupby(["Station Id", "Station Name"], as_index=False)
        .agg(
            Departures=("Departures", "sum"),
            Arrivals=("Arrivals", "sum"),
        )
    )
    balance["NetDepartures"] = (
        balance["Departures"] - balance["Arrivals"]
    )

    highest_outflow = balance.sort_values(
        "NetDepartures", ascending=False
    ).head(10)

    highest_inflow = balance.sort_values(
        "NetDepartures", ascending=True
    ).head(10)

    # Save detailed tables for review and later Power BI use.
    top_stations.to_csv(
        REPORT_DIR / "top_departure_stations.csv", index=False
    )
    hourly.to_csv(
        REPORT_DIR / "hourly_demand.csv", index=False
    )
    day_type.to_csv(
        REPORT_DIR / "weekday_weekend_demand.csv", index=False
    )
    balance.to_csv(
        REPORT_DIR / "station_demand_balance.csv", index=False
    )

    print("\nTOP 15 DEPARTURE STATIONS")
    print(top_stations.to_string(index=False))

    print("\nDEMAND BY HOUR")
    print(hourly.to_string(index=False))

    print("\nWEEKDAY VS WEEKEND")
    print(day_type.to_string(index=False))

    print("\n10 HIGHEST NET DEPARTURE STATIONS")
    print(highest_outflow.to_string(index=False))

    print("\n10 HIGHEST NET ARRIVAL STATIONS")
    print(highest_inflow.to_string(index=False))

    print(f"\nReports saved to: {REPORT_DIR}")


if __name__ == "__main__":
    main()
