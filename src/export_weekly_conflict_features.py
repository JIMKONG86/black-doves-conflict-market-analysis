import argparse
import sys

from pathlib import Path

from src.data_access.weekly_conflict_aggregate_repository import (
    WeeklyConflictAggregateRepository,
)
from src.data_access.weekly_conflict_feature_exporter import (
    WeeklyConflictFeatureExporter,
)
from src.services.weekly_conflict_feature_builder import (
    WeeklyConflictFeatureBuilder,
)


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Create an analysis-ready country-week CSV "
            "from validated ACLED weekly aggregates."
        )
    )
    parser.add_argument(
        "output_file",
        type=Path,
        help="Destination .csv file.",
    )
    parser.add_argument(
        "--aggregate-directory",
        type=Path,
        help=(
            "Validated weekly aggregate directory. "
            "The repository default is used when omitted."
        ),
    )
    parser.add_argument(
        "--snapshot-date",
        help=(
            "Optional source snapshot in YYYY-MM-DD format."
        ),
    )
    parser.add_argument(
        "--country",
        action="append",
        dest="countries",
        help=(
            "Country name or ISO alpha-2 code to include. "
            "May be repeated."
        ),
    )
    return parser


def _repository(directory):
    if directory is None:
        return WeeklyConflictAggregateRepository()

    return WeeklyConflictAggregateRepository(directory)


def main(arguments=None):
    parser = build_parser()
    options = parser.parse_args(arguments)
    builder = WeeklyConflictFeatureBuilder(
        _repository(options.aggregate_directory)
    )

    try:
        features = builder.build(
            source_snapshot_date=options.snapshot_date,
            countries=options.countries,
        )
        output_path = (
            WeeklyConflictFeatureExporter().export_csv(
                features,
                options.output_file,
            )
        )
    except (TypeError, ValueError) as error:
        parser.error(str(error))

    print("\nWeekly conflict feature export completed.")
    print(f"Country-week rows: {len(features)}")
    print(
        "Total events: "
        f"{sum(feature.total_events for feature in features)}"
    )
    print(
        "Strike events: "
        f"{sum(feature.strike_events for feature in features)}"
    )
    print(
        "Total fatalities: "
        f"{sum(feature.total_fatalities for feature in features)}"
    )
    print(f"CSV file: {output_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
