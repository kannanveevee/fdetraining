"""Command-line tool that loads the diabetic dataset (CSV) into PostgreSQL.

Usage:   python data_loader.py diabetic_data.csv

It can be run again and again: rows are matched on encounter_id, so existing
encounters are updated instead of being duplicated.
"""

import argparse
import csv
from collections.abc import Iterator, Mapping
from pathlib import Path

from database import connect
from repository import load_encounters

# Columns that must contain whole numbers.
NUMERIC_COLUMNS = (
    "encounter_id",
    "patient_nbr",
    "time_in_hospital",
    "number_inpatient",
    "number_emergency",
    "number_outpatient",
    "num_medications",
    "num_lab_procedures",
    "discharge_disposition_id",
    "admission_type_id",
)

# Every column the CSV must have: the numeric ones plus two text columns.
REQUIRED_COLUMNS = frozenset((*NUMERIC_COLUMNS, "age", "readmitted"))


def parse_row(
    row: Mapping[str, str | None], line_number: int
) -> dict[str, object]:
    """Convert one raw CSV row (all text) into clean values ready for the database.

    - Numeric columns become int; blank or "?" becomes None (stored as NULL).
    - age and readmitted stay as text; blank or "?" becomes None.
    - line_number is only used to make error messages point at the right CSV line.
    """
    parsed: dict[str, object] = {}

    for column in NUMERIC_COLUMNS:
        value = (row.get(column) or "").strip()

        # Missing value. encounter_id is the key of the table, so it can never be missing.
        if value in ("", "?"):
            if column == "encounter_id":
                raise ValueError(f"CSV line {line_number}: encounter_id is required.")
            parsed[column] = None
            continue

        try:
            parsed[column] = int(value)
        except ValueError as exc:
            raise ValueError(
                f"CSV line {line_number}: {column} must be an integer or missing."
            ) from exc

    age = (row.get("age") or "").strip()
    parsed["age"] = None if age in ("", "?") else age

    outcome = (row.get("readmitted") or "").strip()
    parsed["readmitted"] = None if outcome in ("", "?") else outcome

    return parsed


def read_encounters(
    path: Path, batch_size: int = 1000
) -> Iterator[list[dict[str, object]]]:
    """Read the CSV and hand back the rows in batches (lists of up to batch_size rows).

    Working in batches keeps memory low for a big file. This is a generator:
    each `yield` returns one batch to the caller.
    """
    # utf-8-sig quietly removes the invisible BOM mark some Excel files start with.
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)

        # ---- Check the header line before reading any data ----
        if reader.fieldnames is None:
            raise ValueError("The CSV file is empty or has no header row.")
        headers = {header.strip() for header in reader.fieldnames if header}
        missing = sorted(REQUIRED_COLUMNS - headers)
        if missing:
            raise ValueError(
                "The CSV is missing required columns: " + ", ".join(missing)
            )

        # ---- Read the data rows ----
        batch: list[dict[str, object]] = []
        # Line 1 is the header, so the first data row is line 2.
        for line_number, row in enumerate(reader, start=2):
            # Remove stray spaces around the column names.
            normalized = {
                (key.strip() if key is not None else ""): value
                for key, value in row.items()
            }
            batch.append(parse_row(normalized, line_number))

            if len(batch) == batch_size:
                yield batch
                batch = []

        # Whatever is left over (a last, smaller batch).
        if batch:
            yield batch


def load_csv(path: Path) -> int:
    """Load the whole CSV into the database and return how many rows were processed."""
    if not path.is_file():
        raise FileNotFoundError(f"Dataset CSV not found: {path}")

    loaded = 0
    # One connection for the whole load; it commits when the `with` block ends.
    with connect() as conn:
        for batch in read_encounters(path):
            load_encounters(conn, batch)
            loaded += len(batch)
    return loaded


def main() -> None:
    """Read the CSV path from the command line and run the load."""
    parser = argparse.ArgumentParser(
        description=(
            "Idempotently load encounter fields into the existing "
            "diabetic_patient table."
        )
    )
    parser.add_argument(
        "csv_path",
        type=Path,
        help="Path to the supplied diabetic dataset CSV.",
    )
    args = parser.parse_args()
    print(f"Loaded or updated {load_csv(args.csv_path)} encounter rows.")


if __name__ == "__main__":
    main()
