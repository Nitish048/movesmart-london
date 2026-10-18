from pathlib import Path
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

PROJECT_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_DIR / "data" / "raw"
OUTPUT_DIR = PROJECT_DIR / "data" / "processed"
OUTPUT_FILE = OUTPUT_DIR / "journeys.parquet"
CHUNK_SIZE = 100_000

DATE_FORMAT = "%d/%m/%Y %H:%M"

COLUMNS = [
    "Rental Id", "Duration", "Bike Id", "End Date",
    "EndStation Id", "EndStation Name", "Start Date",
    "StartStation Id", "StartStation Name",
]


def main():
    files = sorted(RAW_DIR.glob("*.csv"))
    if not files:
        raise FileNotFoundError(f"No CSV files found in {RAW_DIR}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if OUTPUT_FILE.exists():
        raise FileExistsError(
            f"{OUTPUT_FILE} already exists. Move it before rerunning."
        )

    writer = None
    total_rows = 0

    try:
        for file in files:
            print(f"Processing: {file.name}", flush=True)

            for chunk in pd.read_csv(
                file, chunksize=CHUNK_SIZE, low_memory=True
            ):
                chunk.columns = chunk.columns.str.strip()
                chunk = chunk[COLUMNS].copy()

                chunk["Start Date"] = pd.to_datetime(
                    chunk["Start Date"],
                    format=DATE_FORMAT,
                    errors="raise",
                )
                chunk["End Date"] = pd.to_datetime(
                    chunk["End Date"],
                    format=DATE_FORMAT,
                    errors="raise",
                )

                for col in [
                    "Rental Id", "Duration", "Bike Id",
                    "StartStation Id", "EndStation Id",
                ]:
                    chunk[col] = pd.to_numeric(
                        chunk[col], errors="raise"
                    ).astype("int64")

                if (chunk["Duration"] <= 0).any():
                    raise ValueError("Non-positive duration detected.")

                if (chunk["End Date"] < chunk["Start Date"]).any():
                    raise ValueError("End date before start date detected.")

                table = pa.Table.from_pandas(
                    chunk, preserve_index=False
                )

                if writer is None:
                    writer = pq.ParquetWriter(
                        OUTPUT_FILE,
                        table.schema,
                        compression="snappy",
                    )

                writer.write_table(table)
                total_rows += len(chunk)

        print("\nINGESTION COMPLETE", flush=True)
        print(f"Files processed: {len(files)}", flush=True)
        print(f"Rows written: {total_rows:,}", flush=True)
        print(f"Output: {OUTPUT_FILE}", flush=True)

    finally:
        if writer is not None:
            writer.close()


if __name__ == "__main__":
    main()
