
from pathlib import Path
import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_DIR / "data" / "raw"

REQUIRED_COLUMNS = {
    "Rental Id",
    "Duration",
    "Bike Id",
    "End Date",
    "EndStation Id",
    "EndStation Name",
    "Start Date",
    "StartStation Id",
    "StartStation Name",
}


def main():
    files = sorted(RAW_DIR.glob("*.csv"))

    if not files:
        print(f"No CSV files found in: {RAW_DIR}")
        return

    print(f"CSV files found: {len(files)}")
    print(f"Raw data directory: {RAW_DIR}")

    for file in files:
        print("\n" + "=" * 70)
        print(f"FILE: {file.name}")
        print(f"SIZE: {file.stat().st_size / (1024 ** 2):.2f} MiB")

        try:
            # Read only five rows, not the full file.
            sample = pd.read_csv(file, nrows=5)

            # Normalise accidental spaces in column names.
            sample.columns = sample.columns.str.strip()

            print("\nCOLUMNS:")
            print(sample.columns.tolist())

            missing = REQUIRED_COLUMNS - set(sample.columns)
            if missing:
                print(f"\nSCHEMA CHECK: REVIEW — missing {sorted(missing)}")
            else:
                print("\nSCHEMA CHECK: PASSED")

            print("\nSAMPLE (first 2 rows):")
            print(sample.head(2).to_string(index=False))

        except Exception as exc:
            print(f"\nERROR reading file: {exc}")


if __name__ == "__main__":
    main()
