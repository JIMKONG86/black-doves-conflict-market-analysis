"""Validate and merge auditable company-announcement CSV imports."""

import argparse
import csv
import hashlib
import sys
import tempfile

from datetime import date
from pathlib import Path
from urllib.parse import urlparse


PROJECT_ROOT = Path(__file__).resolve().parents[1]

REGISTRY_COLUMNS = (
    "announcement_id",
    "announcement_date",
    "company_id",
    "company_name",
    "market_data_ticker",
    "announcement_type",
    "title",
    "source_name",
    "source_url",
    "verification_status",
    "coverage_status",
    "record_scope",
    "counterparty_name",
    "counterparty_country_code",
    "systems",
    "contract_value_eur",
    "value_description",
    "reviewed_by",
    "notes",
)

_REQUIRED_IMPORT_COLUMNS = {
    "announcement_date",
    "company_id",
    "announcement_type",
    "title",
    "source_name",
    "source_url",
    "verification_status",
    "coverage_status",
    "record_scope",
}


def merge_company_announcements(
    input_file,
    registry_file=(PROJECT_ROOT / "data" / "reference" / "company_announcements.csv"),
    company_universe_file=(PROJECT_ROOT / "config" / "company_market_universe.csv"),
):
    universe = _load_company_universe(company_universe_file)
    incoming = _load_rows(input_file, universe, allow_empty=False)
    registry_path = Path(registry_file)
    existing = (
        _load_rows(registry_path, universe, allow_empty=True)
        if registry_path.is_file()
        else []
    )
    indexed = {row["announcement_id"]: row for row in existing}
    added = 0

    for row in incoming:
        previous = indexed.get(row["announcement_id"])

        if previous is not None and previous != row:
            raise ValueError(
                "Announcement ID collision with different content: "
                + row["announcement_id"]
            )
        if previous is None:
            indexed[row["announcement_id"]] = row
            added += 1

    rows = sorted(
        indexed.values(),
        key=lambda item: (
            item["announcement_date"],
            item["company_id"],
            item["announcement_id"],
        ),
    )
    _write_registry(registry_path, rows)
    return {
        "input_rows": len(incoming),
        "added_rows": added,
        "registry_rows": len(rows),
        "registry_file": registry_path,
    }


def _load_rows(path, universe, allow_empty):
    input_path = Path(path)

    if not input_path.is_file():
        raise FileNotFoundError(f"Company-announcement CSV not found: {input_path}")

    with input_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        columns = set(reader.fieldnames or ())
        missing = _REQUIRED_IMPORT_COLUMNS - columns

        if missing:
            raise ValueError(
                "Company-announcement CSV is missing columns: "
                + ", ".join(sorted(missing))
            )

        rows = [
            _normalize_row(row, row_number, universe)
            for row_number, row in enumerate(reader, start=2)
        ]

    if not rows and not allow_empty:
        raise ValueError("Company-announcement CSV must contain at least one row")

    ids = [row["announcement_id"] for row in rows]

    if len(ids) != len(set(ids)):
        raise ValueError("Company-announcement CSV contains duplicate IDs")

    return rows


def _normalize_row(row, row_number, universe):
    values = {
        column: str(row.get(column, "") or "").strip()
        for column in REGISTRY_COLUMNS
    }
    company_id = values["company_id"]

    if company_id not in universe:
        raise ValueError(f"Unknown company_id at row {row_number}: {company_id}")

    company = universe[company_id]
    values["company_name"] = values["company_name"] or company["company_name"]
    values["market_data_ticker"] = (
        values["market_data_ticker"] or company["market_data_ticker"]
    )

    if values["company_name"] != company["company_name"]:
        raise ValueError(f"Company-name mismatch at row {row_number}")
    if values["market_data_ticker"] != company["market_data_ticker"]:
        raise ValueError(f"Ticker mismatch at row {row_number}")

    try:
        date.fromisoformat(values["announcement_date"])
    except ValueError as error:
        raise ValueError(
            f"announcement_date must use YYYY-MM-DD at row {row_number}"
        ) from error

    for column in _REQUIRED_IMPORT_COLUMNS - {
        "announcement_date",
        "company_id",
    }:
        if not values[column]:
            raise ValueError(f"{column} must not be blank at row {row_number}")

    parsed_url = urlparse(values["source_url"])

    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        raise ValueError(f"source_url must be HTTP(S) at row {row_number}")

    if values["contract_value_eur"]:
        try:
            number = float(values["contract_value_eur"])
        except ValueError as error:
            raise ValueError(
                f"contract_value_eur must be numeric at row {row_number}"
            ) from error
        if number < 0:
            raise ValueError(
                f"contract_value_eur must not be negative at row {row_number}"
            )

    if not values["announcement_id"]:
        identity = "\x1f".join(
            values[column]
            for column in (
                "company_id",
                "announcement_date",
                "announcement_type",
                "title",
                "source_url",
            )
        )
        values["announcement_id"] = hashlib.sha256(
            identity.encode("utf-8")
        ).hexdigest()

    return values


def _load_company_universe(path):
    input_path = Path(path)

    if not input_path.is_file():
        raise FileNotFoundError(f"Company universe CSV not found: {input_path}")

    with input_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        required = {"company_id", "company_name", "market_data_ticker"}
        missing = required - set(reader.fieldnames or ())

        if missing:
            raise ValueError(
                "Company universe CSV is missing columns: "
                + ", ".join(sorted(missing))
            )
        rows = list(reader)

    universe = {
        row["company_id"].strip(): {
            "company_name": row["company_name"].strip(),
            "market_data_ticker": row["market_data_ticker"].strip(),
        }
        for row in rows
        if row["company_id"].strip()
    }

    if len(universe) != len(rows):
        raise ValueError("Company universe contains blank or duplicate IDs")

    return universe


def _write_registry(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        newline="",
        delete=False,
        dir=path.parent,
        prefix=path.name + ".",
        suffix=".tmp",
    ) as file:
        writer = csv.DictWriter(file, fieldnames=REGISTRY_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
        temporary_path = Path(file.name)

    temporary_path.replace(path)


def build_parser():
    parser = argparse.ArgumentParser(
        description="Validate and merge company-linked announcement rows."
    )
    parser.add_argument("input_file", type=Path)
    parser.add_argument(
        "--registry-file",
        type=Path,
        default=(
            PROJECT_ROOT / "data" / "reference" / "company_announcements.csv"
        ),
    )
    parser.add_argument(
        "--company-universe-file",
        type=Path,
        default=PROJECT_ROOT / "config" / "company_market_universe.csv",
    )
    return parser


def main(arguments=None):
    options = build_parser().parse_args(arguments)

    try:
        result = merge_company_announcements(
            input_file=options.input_file,
            registry_file=options.registry_file,
            company_universe_file=options.company_universe_file,
        )
    except (FileNotFoundError, ValueError) as error:
        raise SystemExit(str(error)) from error

    print(f"Input rows: {result['input_rows']}")
    print(f"Added rows: {result['added_rows']}")
    print(f"Registry rows: {result['registry_rows']}")
    print(result["registry_file"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
