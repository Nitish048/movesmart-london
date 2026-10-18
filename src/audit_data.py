
from pathlib import Path
import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_DIR / "data" / "raw"

DATE_FORMAT = "%d/%m/%Y %H:%M"

REQUIRED_COLUMNS = [
    "Rental Id",
    "Duration",
    "Bike Id",
    "End Date",
    "EndStation Id",
    "EndStation Name",
    "Start Date",
    "StartStation Id",
    "StartStation Name",
]

MISSING_CHECK_COLUMNS = [
    "Rental Id",
    "Duration",
    "Bike Id",
    "Start Date",
    "End Date",
    "StartStation Id",
    "EndStation Id",
]


def audit_file(file_path):
    print("\n" + "=" * 75)
    print(f"FILE: {file_path.name}")

    total_rows = 0
    missing_counts = {column: 0 for column in MISSING_CHECK_COLUMNS}
    invalid_start_dates = 0
    invalid_end_dates = 0
    invalid_durations = 0
    duplicate_ids = 0
    seen_ids = set()
    earliest_start = None
    latest_start = None

    # Read in chunks so the complete file is never loaded into RAM.
    for chunk in pd.read_csv(
        file_path,
        chunksize=100_000,
        low_memory=True,
    ):
        chunk.columns = chunk.columns.str.strip()

        missing_columns = set(REQUIRED_COLUMNS) - set(chunk.columns)
        if missing_columns:
            raise ValueError(
                f"Missing required columns: {sorted(missing_columns)}"
            )

        total_rows += len(chunk)

        for column in MISSING_CHECK_COLUMNS:
            missing_counts[column] += int(chunk[column].isna().sum())

        start_dates = pd.to_datetime(
            chunk["Start Date"],
            format=DATE_FORMAT,
            errors="coerce",
        )
        end_dates = pd.to_datetime(
            chunk["End Date"],
            format=DATE_FORMAT,
            errors="coerce",
        )

        invalid_start_dates += int(start_dates.isna().sum())
        invalid_end_dates += int(end_dates.isna().sum())

        valid_starts = start_dates.dropna()
        if not valid_starts.empty:
            chunk_earliest = valid_starts.min()
            chunk_latest = valid_starts.max()

            if earliest_start is None or chunk_earliest < earliest_start:
                earliest_start = chunk_earliest

            if latest_start is None or chunk_latest > latest_start:
                latest_start = chunk_latest

        duration = pd.to_numeric(chunk["Duration"], errors="coerce")
        invalid_durations += int(
            (duration.isna() | (duration <= 0)).sum()
        )

        # Check repeated rental IDs, including across chunk boundaries.
        for rental_id in chunk["Rental Id"].dropna().unique():
            if rental_id in seen_ids:
                duplicate_ids += int(
                    (chunk["Rental Id"] == rental_id).sum()
                )
            else:
                seen_ids.add(rental_id)

    print(f"Rows: {total_rows:,}")
    print(f"Start-date coverage: {earliest_start} to {latest_start}")
    print(f"Invalid start dates: {invalid_start_dates:,}")
    print(f"Invalid end dates: {invalid_end_dates:,}")
    print(f"Invalid/non-positive durations: {invalid_durations:,}")
    print(f"Repeated rental-ID occurrences: {duplicate_ids:,}")

    print("\nMissing values:")
    for column, count in missing_counts.items():
        print(f"  {column}: {count:,} ({count / max(total_rows, 1):.3%})")


def main():
    files = sorted(RAW_DIR.glob("*.csv"))

    if not files:
        print(f"No CSV files found in {RAW_DIR}")
        return

    print(f"Auditing {len(files)} CSV files in chunks...")

    for file_path in files:
        audit_file(file_path)

    print("\nAudit completed.")
    print("No data has been modified.")


if __name__ == "__main__":
    main()
