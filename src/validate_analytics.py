
from pathlib import Path
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "processed" / "journeys.parquet"
ANALYTICS = ROOT / "data" / "analytics" / "hourly_station_demand.parquet"


def main():
    source = pq.ParquetFile(SOURCE)
    analytics = pq.ParquetFile(ANALYTICS)

    print(f"Source journeys: {source.metadata.num_rows:,}")
    print(f"Analytics rows: {analytics.metadata.num_rows:,}")

    departures = 0
    arrivals = 0
    negative_counts = 0

    for batch in analytics.iter_batches(
        batch_size=100_000,
        columns=["Departures", "Arrivals"],
    ):
        df = batch.to_pandas()
        departures += int(df["Departures"].sum())
        arrivals += int(df["Arrivals"].sum())
        negative_counts += int(
            (df["Departures"] < 0).sum()
            + (df["Arrivals"] < 0).sum()
        )

    expected = source.metadata.num_rows

    print(f"Total departures: {departures:,}")
    print(f"Total arrivals: {arrivals:,}")
    print(f"Departure difference: {departures - expected:,}")
    print(f"Arrival difference: {arrivals - expected:,}")
    print(f"Negative count cells: {negative_counts}")

    if departures == expected and arrivals == expected:
        print("RECONCILIATION: PASSED")
    else:
        print("RECONCILIATION: FAILED — investigate before proceeding")


if __name__ == "__main__":
    main()
