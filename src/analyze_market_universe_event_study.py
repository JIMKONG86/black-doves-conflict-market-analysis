import argparse
import sys

from pathlib import Path

from src.data_access.market_event_reader import load_market_events
from src.services.market_universe_event_study import (
    MarketUniverseEventStudy,
)


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Create company-level event windows and descriptive AAR/CAAR "
            "series for the complete BLACK DOVES market universe."
        )
    )
    parser.add_argument(
        "--event-file",
        type=Path,
        default=Path("data/reference/black_doves_market_events.csv"),
    )
    parser.add_argument(
        "--market-file",
        type=Path,
        default=Path(
            "data/processed/market/company_benchmark_returns.csv"
        ),
    )
    parser.add_argument(
        "--detail-output",
        type=Path,
        default=Path(
            "data/analysis/market_universe_event_window.csv"
        ),
    )
    parser.add_argument(
        "--company-summary-output",
        type=Path,
        default=Path(
            "data/analysis/market_universe_company_summary.csv"
        ),
    )
    parser.add_argument(
        "--sample-summary-output",
        type=Path,
        default=Path(
            "data/analysis/market_universe_sample_aar_caar.csv"
        ),
    )
    parser.add_argument(
        "--role-summary-output",
        type=Path,
        default=Path(
            "data/analysis/market_universe_role_aar_caar.csv"
        ),
    )
    parser.add_argument("--pre-days", type=int, default=5)
    parser.add_argument("--post-days", type=int, default=10)
    return parser


def main(arguments=None):
    parser = build_parser()
    options = parser.parse_args(arguments)
    study = MarketUniverseEventStudy()

    try:
        events = load_market_events(options.event_file)
        (
            detail,
            company_summary,
            sample_summary,
            role_summary,
            summary,
        ) = study.analyze(
            events=events,
            market_file=options.market_file,
            pre_days=options.pre_days,
            post_days=options.post_days,
        )
        detail_path = study.export_csv(detail, options.detail_output)
        company_path = study.export_csv(
            company_summary,
            options.company_summary_output,
        )
        sample_path = study.export_csv(
            sample_summary,
            options.sample_summary_output,
        )
        role_path = study.export_csv(
            role_summary,
            options.role_summary_output,
        )
    except (FileNotFoundError, TypeError, ValueError) as error:
        parser.error(str(error))

    print("\nBLACK DOVES market-universe event study completed.")
    print(f"Events: {summary.event_count}")
    print(f"Companies: {summary.company_count}")
    print(f"Confirmatory companies: {summary.confirmatory_count}")
    print(f"Exploratory companies: {summary.exploratory_count}")
    print(f"Post-hoc companies: {summary.post_hoc_count}")
    print(f"Event-window rows: {summary.detail_rows}")
    print(
        "Market coverage: "
        f"{summary.first_market_date.isoformat()} to "
        f"{summary.last_market_date.isoformat()}"
    )
    print(
        "Trading-day window: "
        f"-{summary.pre_days} to +{summary.post_days}"
    )
    print(f"Detail CSV: {detail_path}")
    print(f"Company summary: {company_path}")
    print(f"Sample AAR/CAAR: {sample_path}")
    print(f"Role AAR/CAAR: {role_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
