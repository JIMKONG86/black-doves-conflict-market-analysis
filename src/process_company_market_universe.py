import argparse
import sys

from pathlib import Path

from src.data_access.company_market_universe import (
    load_company_market_universe,
)
from src.services.market_universe_processor import (
    process_market_universe,
)


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Create company-versus-local-benchmark return series "
            "for the BLACK DOVES market universe."
        )
    )
    parser.add_argument(
        "--universe-file",
        type=Path,
        default=Path("config/company_market_universe.csv"),
    )
    parser.add_argument(
        "--raw-directory",
        type=Path,
        default=Path("data/raw/market/universe"),
    )
    parser.add_argument(
        "--output-directory",
        type=Path,
        default=Path("data/processed/market/universe"),
    )
    parser.add_argument(
        "--combined-file",
        type=Path,
        default=Path(
            "data/processed/market/"
            "company_benchmark_returns.csv"
        ),
    )
    parser.add_argument(
        "--report-file",
        type=Path,
        default=Path(
            "data/processed/market/"
            "market_processing_report.csv"
        ),
    )
    parser.add_argument(
        "--price-column",
        default="Adj Close",
    )

    return parser


def main(arguments=None):
    parser = build_parser()
    options = parser.parse_args(arguments)

    try:
        entries = load_company_market_universe(
            options.universe_file
        )
        combined, combined_path, report, report_path = (
            process_market_universe(
                entries=entries,
                raw_directory=options.raw_directory,
                output_directory=options.output_directory,
                combined_file=options.combined_file,
                report_file=options.report_file,
                price_column=options.price_column,
            )
        )
    except (FileNotFoundError, TypeError, ValueError) as error:
        parser.error(str(error))

    counts = report["status"].value_counts().to_dict()
    incomplete = int((report["status"] != "PROCESSED").sum())

    print("\nBLACK DOVES market-universe processing completed.")
    print(f"Companies: {len(report)}")
    print(f"Combined rows: {len(combined)}")
    print(f"Status counts: {counts}")
    print(f"Combined CSV: {combined_path}")
    print(f"Audit report: {report_path}")

    return 2 if incomplete else 0


if __name__ == "__main__":
    sys.exit(main())
