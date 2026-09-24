import argparse
import sys

from pathlib import Path

from src.data_access.company_market_universe import (
    load_company_market_universe,
)
from src.services.market_universe_collector import (
    collect_market_universe,
)


DEFAULT_UNIVERSE_FILE = Path(
    "config/company_market_universe.csv"
)
DEFAULT_OUTPUT_DIRECTORY = Path("data/raw/market/universe")
DEFAULT_REPORT_FILE = Path(
    "data/processed/market/market_download_report.csv"
)


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Download the BLACK DOVES company and benchmark "
            "market-data universe with a resumable audit report."
        )
    )
    parser.add_argument(
        "--universe-file",
        type=Path,
        default=DEFAULT_UNIVERSE_FILE,
    )
    parser.add_argument(
        "--output-directory",
        type=Path,
        default=DEFAULT_OUTPUT_DIRECTORY,
    )
    parser.add_argument(
        "--report-file",
        type=Path,
        default=DEFAULT_REPORT_FILE,
    )
    parser.add_argument(
        "--start-date",
        default="2023-01-01",
        help=(
            "Inclusive start date. The default leaves pre-event "
            "history before the collection envelope."
        ),
    )
    parser.add_argument(
        "--end-date",
        default="2026-09-03",
        help=(
            "Exclusive end date. The default covers +10 trading "
            "days after the final 2026-08-18 collection date."
        ),
    )
    parser.add_argument(
        "--only-confirmatory",
        action="store_true",
        help="Download only the eight pre-specified companies.",
    )
    parser.add_argument(
        "--company-id",
        action="append",
        default=[],
        help=(
            "Limit to one company ID; repeat for multiple IDs. "
            "Required benchmarks are added automatically."
        ),
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Replace market files that already exist.",
    )
    parser.add_argument(
        "--request-delay",
        type=float,
        default=1.0,
        help="Seconds between provider requests (default: 1.0).",
    )
    parser.add_argument(
        "--max-attempts",
        type=int,
        default=2,
        help="Attempts per ticker before recording FAILED.",
    )
    parser.add_argument(
        "--retry-delay",
        type=float,
        default=5.0,
        help=(
            "Base seconds for linear retry backoff "
            "(default: 5.0)."
        ),
    )

    return parser


def main(arguments=None):
    parser = build_parser()
    options = parser.parse_args(arguments)

    try:
        entries = load_company_market_universe(
            options.universe_file
        )
        entries = _select_entries(
            entries,
            company_ids=options.company_id,
            only_confirmatory=options.only_confirmatory,
        )
        report, report_path = collect_market_universe(
            entries=entries,
            start_date=options.start_date,
            end_date=options.end_date,
            output_directory=options.output_directory,
            report_file=options.report_file,
            refresh=options.refresh,
            request_delay=options.request_delay,
            retry_delay=options.retry_delay,
            max_attempts=options.max_attempts,
        )
    except (FileNotFoundError, TypeError, ValueError) as error:
        parser.error(str(error))

    counts = report["status"].value_counts().to_dict()
    failed = int(report["status"].str.startswith("FAILED").sum())

    print("\nBLACK DOVES market-universe collection completed.")
    print(f"Instruments: {len(report)}")
    print(f"Status counts: {counts}")
    print(f"Audit report: {report_path}")

    return 2 if failed else 0


def _select_entries(
    entries,
    company_ids,
    only_confirmatory,
):
    selected = list(entries)

    if only_confirmatory:
        selected = [
            entry
            for entry in selected
            if entry.is_confirmatory
        ]

    if company_ids:
        requested = set(company_ids)
        available = {entry.company_id for entry in entries}
        missing = requested - available

        if missing:
            missing_text = ", ".join(sorted(missing))
            raise ValueError(
                f"Unknown company IDs: {missing_text}"
            )

        selected = [
            entry
            for entry in selected
            if entry.company_id in requested
        ]

    if not selected:
        raise ValueError("Company selection is empty")

    return selected


if __name__ == "__main__":
    sys.exit(main())
