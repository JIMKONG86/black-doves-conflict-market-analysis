import argparse
import sys

from pathlib import Path

from src.data_access.centcom_strike_importer import CentcomStrikeImporter
from src.data_access.claim_observation_repository import (
    ClaimObservationRepository,
)
from src.data_access.strike_observation_repository import (
    StrikeObservationRepository,
)


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Import reviewed CENTCOM strike-operation days into validated "
            "claim and strike repositories."
        )
    )
    parser.add_argument(
        "csv_file",
        type=Path,
        nargs="?",
        default=Path("data/validated/centcom_us_strike_operation_days.csv"),
    )
    parser.add_argument(
        "--reviewed-by",
        required=True,
        help="Name of the person accepting responsibility for the import.",
    )
    parser.add_argument("--claim-directory", type=Path)
    parser.add_argument("--strike-directory", type=Path)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return exit code 1 when one or more confirmed rows fail.",
    )
    return parser


def main(arguments=None):
    options = build_parser().parse_args(arguments)
    claim_repository = ClaimObservationRepository(
        options.claim_directory or "data/validated/claims"
    )
    strike_repository = StrikeObservationRepository(
        options.strike_directory or "data/validated/strikes"
    )
    importer = CentcomStrikeImporter(claim_repository, strike_repository)

    try:
        summary = importer.import_csv(
            file_path=options.csv_file,
            reviewed_by=options.reviewed_by,
        )
    except (FileNotFoundError, TypeError, ValueError) as error:
        parser.error(str(error))

    print("\nCENTCOM strike import completed.")
    print(f"Rows read: {summary.total_rows}")
    print(f"Confirmed rows: {summary.confirmed_rows}")
    print(f"Saved strikes: {summary.saved_strikes}")
    print(f"Duplicate strikes: {summary.duplicate_strikes}")
    print(f"Skipped unconfirmed rows: {summary.skipped_unconfirmed}")
    print(f"Failed rows: {summary.failed_rows}")
    for issue in summary.issues:
        release = issue.source_release_id or "unknown release"
        print(f"Row {issue.row_number} ({release}): {issue.message}")

    if options.strict and summary.failed_rows:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
