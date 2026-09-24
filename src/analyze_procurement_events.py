import argparse
import sys

from pathlib import Path

from src.data_access.procurement_event_reader import (
    ProcurementEventReader,
)
from src.services.procurement_event_study import ProcurementEventStudy


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Create trading-day event windows for verified "
            "Rheinmetall procurement announcements."
        )
    )
    parser.add_argument("event_file", type=Path)
    parser.add_argument("market_file", type=Path)
    parser.add_argument("detail_output_file", type=Path)
    parser.add_argument("summary_output_file", type=Path)
    parser.add_argument("--pre-days", type=int, default=5)
    parser.add_argument("--post-days", type=int, default=10)
    return parser


def main(arguments=None):
    parser = build_parser()
    options = parser.parse_args(arguments)
    reader = ProcurementEventReader()
    study = ProcurementEventStudy()

    try:
        events = reader.read(options.event_file)
        detail, event_summaries, summary = study.analyze(
            events=events,
            market_file=options.market_file,
            pre_days=options.pre_days,
            post_days=options.post_days,
        )
        detail_path = study.export_csv(
            detail,
            options.detail_output_file,
        )
        summary_path = study.export_csv(
            event_summaries,
            options.summary_output_file,
        )
    except (FileNotFoundError, TypeError, ValueError) as error:
        parser.error(str(error))

    print("\nBLACK DOVES procurement event study completed.")
    print(f"Procurement events: {summary.event_count}")
    print(f"Event-window rows: {summary.detail_rows}")
    print(
        "Announcement period: "
        f"{summary.first_event_date.isoformat()} to "
        f"{summary.last_event_date.isoformat()}"
    )
    print(
        "Market coverage: "
        f"{summary.first_market_date.isoformat()} to "
        f"{summary.last_market_date.isoformat()}"
    )
    print(
        "Trading-day window: "
        f"-{summary.pre_days} to +{summary.post_days}"
    )
    print(f"Company ticker: {summary.company_ticker}")
    print(f"Detail CSV: {detail_path}")
    print(f"Summary CSV: {summary_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
