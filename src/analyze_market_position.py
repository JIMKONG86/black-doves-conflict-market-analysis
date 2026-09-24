import argparse
import sys

from pathlib import Path

from src.data_access.market_event_reader import load_market_events
from src.services.market_position_analysis import MarketPositionAnalysis


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Analyze long-horizon returns and relative capital-market "
            "position shifts in the BLACK DOVES company universe."
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
    parser.add_argument("--analysis-start", default="2026-01-01")
    parser.add_argument("--analysis-end", default="2026-08-18")
    parser.add_argument(
        "--detail-output",
        type=Path,
        default=Path(
            "data/analysis/market_position_full_period_detail.csv"
        ),
    )
    parser.add_argument(
        "--company-output",
        type=Path,
        default=Path(
            "data/analysis/market_position_company_summary.csv"
        ),
    )
    parser.add_argument(
        "--sample-output",
        type=Path,
        default=Path(
            "data/analysis/market_position_sample_aar_caar.csv"
        ),
    )
    parser.add_argument(
        "--role-output",
        type=Path,
        default=Path(
            "data/analysis/market_position_role_aar_caar.csv"
        ),
    )
    return parser


def main(arguments=None):
    parser = build_parser()
    options = parser.parse_args(arguments)
    analysis = MarketPositionAnalysis()

    try:
        events = load_market_events(options.event_file)
        (
            detail,
            companies,
            samples,
            roles,
            summary,
        ) = analysis.analyze(
            events=events,
            market_file=options.market_file,
            analysis_start=options.analysis_start,
            analysis_end=options.analysis_end,
        )
        detail_path = analysis.export_csv(detail, options.detail_output)
        company_path = analysis.export_csv(companies, options.company_output)
        sample_path = analysis.export_csv(samples, options.sample_output)
        role_path = analysis.export_csv(roles, options.role_output)
    except (FileNotFoundError, TypeError, ValueError) as error:
        parser.error(str(error))

    print("\nBLACK DOVES full-period market-position analysis completed.")
    print(f"Analysis period: {summary.analysis_start} to {summary.analysis_end}")
    print(f"Events: {summary.event_count}")
    print(f"Companies: {summary.company_count}")
    print(f"Detail rows: {summary.detail_rows}")
    print(
        "Quartile shifts: "
        f"{summary.improved_quartile_count} improved, "
        f"{summary.unchanged_quartile_count} unchanged, "
        f"{summary.weakened_quartile_count} weakened"
    )
    print(f"Full-period detail: {detail_path}")
    print(f"Company positioning: {company_path}")
    print(f"Sample AAR/CAAR: {sample_path}")
    print(f"Role AAR/CAAR: {role_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
