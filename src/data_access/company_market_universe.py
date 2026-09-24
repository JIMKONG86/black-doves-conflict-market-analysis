import csv

from pathlib import Path

from src.models.market_universe_entry import (
    MarketUniverseEntry,
)


REQUIRED_COLUMNS = (
    "company_id",
    "company_name",
    "market_data_ticker",
    "benchmark_ticker",
    "trade_currency",
    "primary_listing_exchange",
    "analysis_tier",
    "role_category",
    "is_confirmatory",
)


def load_company_market_universe(file_path):
    path = Path(file_path)

    if not path.is_file():
        raise FileNotFoundError(
            f"Company market universe not found: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file_handle:
        reader = csv.DictReader(file_handle)
        _validate_header(reader.fieldnames)
        rows = list(reader)

    if not rows:
        raise ValueError(
            "Company market universe must contain at least one row"
        )

    entries = [
        _parse_entry(row, row_number=index + 2)
        for index, row in enumerate(rows)
    ]
    _validate_unique(entries, "company_id")
    _validate_unique(entries, "market_data_ticker")

    return entries


def _validate_header(fieldnames):
    available = set(fieldnames or ())
    missing = set(REQUIRED_COLUMNS) - available

    if missing:
        missing_text = ", ".join(sorted(missing))
        raise ValueError(
            "Company market universe is missing required "
            f"columns: {missing_text}"
        )


def _parse_entry(row, row_number):
    values = {}

    for column in REQUIRED_COLUMNS:
        value = (row.get(column) or "").strip()

        if not value:
            raise ValueError(
                f"Row {row_number} has an empty {column}"
            )

        values[column] = value

    flag = values.pop("is_confirmatory").casefold()

    if flag not in {"yes", "no"}:
        raise ValueError(
            f"Row {row_number} is_confirmatory must be YES or NO"
        )

    return MarketUniverseEntry(
        **values,
        is_confirmatory=flag == "yes",
    )


def _validate_unique(entries, attribute):
    seen = set()
    duplicates = set()

    for entry in entries:
        value = getattr(entry, attribute)

        if value in seen:
            duplicates.add(value)

        seen.add(value)

    if duplicates:
        duplicate_text = ", ".join(sorted(duplicates))
        raise ValueError(
            f"Company market universe contains duplicate "
            f"{attribute} values: {duplicate_text}"
        )
