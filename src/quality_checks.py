
from pathlib import Path
import pandas as pd
import pyarrow.parquet as pq

PROJECT_DIR = Path(__file__).resolve().parents[1]
DATA_FILE = PROJECT_DIR / "data" / "processed" / "journeys.parquet"
BATCH_SIZE = 100_000


def main():
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Dataset not found: {DATA_FILE}")

    parquet = pq.ParquetFile(DATA_FILE)

    total_rows = parquet.metadata.num_rows
    print(f"Dataset: {DATA_FILE.name}")
    print(f"Total rows: {total_rows:,}")
    print(f"Row groups: {parquet.metadata.num_row_groups}")

    seen_ids = set()
    duplicate_ids = 0
    invalid_durations = 0
    end_before_start = 0
    missing_required = 0

    station_names = {}
    station_name_conflicts = 0

    for batch in parquet.iter_batches(
        batch_size=BATCH_SIZE,
        columns=[
            "Rental Id",
            "Duration",
            "Start Date",
            "End Date",
            "StartStation Id",
            "StartStation Name",
            "EndStation Id",
            "EndStation Name",
        ],
    ):
        df = batch.to_pandas()

        # Required values
        required = [
            "Rental Id",
            "Duration",
            "Start Date",
            "End Date",
            "StartStation Id",
            "EndStation Id",
        ]
        missing_required += int(df[required].isna().any(axis=1).sum())

        # Cross-batch and cross-file rental ID uniqueness
        ids = df["Rental Id"].dropna()
        duplicate_ids += int(ids.duplicated().sum())

        for rental_id in ids:
            if rental_id in seen_ids:
                duplicate_ids += 1
            else:
                seen_ids.add(rental_id)

        # Duration validation
        duration = pd.to_numeric(df["Duration"], errors="coerce")
        invalid_durations += int(
            (duration.isna() | (duration <= 0)).sum()
        )

        # Timestamp ordering
        start = pd.to_datetime(df["Start Date"], errors="coerce")
        end = pd.to_datetime(df["End Date"], errors="coerce")
        end_before_start += int((end < start).fillna(False).sum())

        # Station ID-to-name consistency
        for id_col, name_col in [
            ("StartStation Id", "StartStation Name"),
            ("EndStation Id", "EndStation Name"),
        ]:
            pairs = df[[id_col, name_col]].dropna().drop_duplicates()

            for station_id, station_name in pairs.itertuples(
                index=False, name=None
            ):
                key = (id_col, station_id)

                if key in station_names:
                    if station_names[key] != station_name:
                        station_name_conflicts += 1
                else:
                    station_names[key] = station_name

    print("\n" + "=" * 60)
    print("DATA QUALITY RESULTS")
    print("=" * 60)
    print(f"Rows checked: {total_rows:,}")
    print(f"Duplicate rental ID occurrences: {duplicate_ids:,}")
    print(f"Rows with missing required values: {missing_required:,}")
    print(f"Invalid/non-positive durations: {invalid_durations:,}")
    print(f"End timestamps before start: {end_before_start:,}")
    print(f"Station ID/name conflicts detected: {station_name_conflicts:,}")
    print("\nAudit completed. No data was modified.")


if __name__ == "__main__":
    main()
