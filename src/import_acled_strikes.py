import argparse
import sys

from pathlib import Path

from src.data_access.acled_strike_importer import (
    AcledStrikeImporter,
)
from src.data_access.claim_observation_repository import (
    ClaimObservationRepository,
)
from src.data_access.strike_observation_repository import (
    StrikeObservationRepository,
)


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Import strike events from an ACLED CSV "
            "export into validated claim and strike "
            "repositories."
        )
    )
    parser.add_argument(
        "csv_file",
        type=Path,
        help="Path to the downloaded ACLED CSV file.",
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
            "Public ACLED page or non-secret export URL "
            "used as provenance. Do not include tokens."
        ),
    )
    parser.add_argument(
        "--affected-country-code",
        help=(
            "Default ISO alpha-2 code for all rows, for "
            "example IR. Not needed when the CSV contains "
            "affected_country_code, country_code or "
            "iso_alpha2."
        ),
    )
    parser.add_argument(
        "--initiator-country-code",
        help=(
            "Optional default ISO alpha-2 code for the "
            "alleged initiating country."
        ),
    )
    parser.add_argument(
        "--claim-directory",
        type=Path,
        help=(
            "Optional claim repository directory. The "
            "repository default is used when omitted."
        ),
    )
    parser.add_argument(
        "--strike-directory",
        type=Path,
        help=(
            "Optional strike repository directory. The "
            "repository default is used when omitted."
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


def _claim_repository(directory):
    if directory is None:
        return ClaimObservationRepository()

    return ClaimObservationRepository(directory)


def _strike_repository(directory):
    if directory is None:
        return StrikeObservationRepository()

    return StrikeObservationRepository(directory)


def main(arguments=None):
    parser = build_parser()
    options = parser.parse_args(arguments)

    importer = AcledStrikeImporter(
        claim_repository=_claim_repository(
            options.claim_directory
        ),
        strike_repository=_strike_repository(
            options.strike_directory
        ),
    )

    try:
        summary = importer.import_csv(
            file_path=options.csv_file,
            reviewed_by=options.reviewed_by,
            source_url=options.source_url,
            affected_country_code=(
                options.affected_country_code
            ),
            initiator_country_code=(
                options.initiator_country_code
            ),
        )
    except (
        FileNotFoundError,
        TypeError,
        ValueError,
    ) as error:
        parser.error(str(error))

    print("\nACLED strike import completed.")
    print(f"Rows read: {summary.total_rows}")
    print(f"Strike rows: {summary.strike_rows}")
    print(f"Saved strikes: {summary.saved_strikes}")
    print(
        "Duplicate strikes: "
        f"{summary.duplicate_strikes}"
    )
    print(
        "Skipped non-strikes: "
        f"{summary.skipped_non_strikes}"
    )
    print(f"Failed rows: {summary.failed_rows}")

    for issue in summary.issues:
        event_label = issue.event_id or "unknown event"
        print(
            f"Row {issue.row_number} ({event_label}): "
            f"{issue.message}"
        )

    if options.strict and summary.failed_rows:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
