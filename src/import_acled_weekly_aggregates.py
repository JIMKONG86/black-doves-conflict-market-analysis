import argparse
import sys

from pathlib import Path

from src.data_access.acled_weekly_aggregate_importer import (
    AcledWeeklyAggregateImporter,
)
from src.data_access.weekly_conflict_aggregate_repository import (
    WeeklyConflictAggregateRepository,
)


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Import ACLED weekly conflict aggregates "
            "from a CSV file into the validated "
            "aggregate repository."
        )
    )
    parser.add_argument(
        "csv_file",
        type=Path,
        help=(
            "Path to the UTF-8 CSV exported from the "
            "ACLED aggregate workbook."
        ),
    )
    parser.add_argument(
        "--reviewed-by",
        required=True,
        help=(
            "Name of the person accepting responsibility "
            "for this import."
        ),
    )
    parser.add_argument(
        "--source-url",
        required=True,
        help=(
            "Public ACLED page used as provenance. "
            "Do not include tokens."
        ),
    )
    parser.add_argument(
        "--snapshot-date",
        required=True,
        help=(
            "Date of the ACLED data snapshot in "
            "YYYY-MM-DD format."
        ),
    )
    parser.add_argument(
        "--country",
        action="append",
        dest="countries",
        help=(
            "Country to import. Repeat this option for "
            "multiple countries. All countries are "
            "imported when omitted."
        ),
    )
    parser.add_argument(
        "--strike-only",
        action="store_true",
        help=(
            "Import only air/drone and shelling/"
            "artillery/missile aggregate rows."
        ),
    )
    parser.add_argument(
        "--aggregate-directory",
        type=Path,
        help=(
            "Optional repository directory. The default "
            "is used when omitted."
        ),
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help=(
            "Return exit code 1 when one or more rows "
            "could not be imported."
        ),
    )
    return parser


def _repository(directory):
    if directory is None:
        return WeeklyConflictAggregateRepository()

    return WeeklyConflictAggregateRepository(
        directory
    )


def main(arguments=None):
    parser = build_parser()
    options = parser.parse_args(arguments)
    importer = AcledWeeklyAggregateImporter(
        _repository(options.aggregate_directory)
    )

    try:
        summary = importer.import_csv(
            file_path=options.csv_file,
            reviewed_by=options.reviewed_by,
            source_url=options.source_url,
            source_snapshot_date=(
                options.snapshot_date
            ),
            countries=options.countries,
            strike_only=options.strike_only,
        )
    except (
        FileNotFoundError,
        TypeError,
        ValueError,
    ) as error:
        parser.error(str(error))

    print("\nACLED weekly aggregate import completed.")
    print(f"Rows read: {summary.total_rows}")
    print(f"Selected rows: {summary.selected_rows}")
    print(
        "Saved aggregates: "
        f"{summary.saved_aggregates}"
    )
    print(
        "Duplicate aggregates: "
        f"{summary.duplicate_aggregates}"
    )
    print(
        "Skipped countries: "
        f"{summary.skipped_countries}"
    )
    print(
        "Skipped non-strikes: "
        f"{summary.skipped_non_strikes}"
    )
    print(f"Failed rows: {summary.failed_rows}")

    for issue in summary.issues:
        location = "/".join(
            value
            for value in (
                issue.country,
                issue.admin1,
            )
            if value is not None
        ) or "unknown location"
        week = issue.week or "unknown week"
        print(
            f"Row {issue.row_number} "
            f"({location}, {week}): "
            f"{issue.message}"
        )

    if options.strict and summary.failed_rows:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
