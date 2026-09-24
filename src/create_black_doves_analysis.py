import argparse
import sys

from pathlib import Path

from src.services.weekly_market_conflict_builder import (
    WeeklyMarketConflictBuilder,
)


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Join analysis-ready ACLED country-week data "
            "to daily company and benchmark returns."
        )
    )
    parser.add_argument(
        "conflict_file",
        type=Path,
        help="Analysis-ready weekly conflict CSV.",
    )
    parser.add_argument(
        "market_file",
        type=Path,
        help="Daily company-versus-benchmark CSV.",
    )
    parser.add_argument(
        "output_file",
        type=Path,
        help="Destination country-week-market CSV.",
    )
    parser.add_argument(
        "--company-ticker",
        default="RHM.DE",
    )
    parser.add_argument(
        "--benchmark-ticker",
        default="^GDAXI",
    )
    parser.add_argument(
        "--market-source-url",
        default="https://finance.yahoo.com/",
    )
    parser.add_argument(
        "--snapshot-date",
        help="Optional ACLED snapshot in YYYY-MM-DD format.",
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


def main(arguments=None):
    parser = build_parser()
    options = parser.parse_args(arguments)
    builder = WeeklyMarketConflictBuilder()

    try:
        data, summary = builder.build(
            conflict_file=options.conflict_file,
            market_file=options.market_file,
            company_ticker=options.company_ticker,
            benchmark_ticker=options.benchmark_ticker,
            market_source_url=options.market_source_url,
            source_snapshot_date=options.snapshot_date,
            countries=options.countries,
        )
        output_path = builder.export_csv(
            data,
            options.output_file,
        )
    except (
        FileNotFoundError,
        TypeError,
        ValueError,
    ) as error:
        parser.error(str(error))

    print("\nBLACK DOVES analysis table completed.")
    print(f"Selected conflict rows: {summary.conflict_rows}")
    print(f"Market trading days: {summary.market_daily_rows}")
    print(f"Joined country-week rows: {summary.joined_rows}")
    print(f"Joined weeks: {summary.joined_weeks}")
    print(
        "Unmatched conflict rows: "
        f"{summary.unmatched_conflict_rows}"
    )
    print(
        "Joined period: "
        f"{summary.first_joined_week.isoformat()} to "
        f"{summary.last_joined_week.isoformat()}"
    )
    print(f"CSV file: {output_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
