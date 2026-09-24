import argparse
import sys

from pathlib import Path

from src.services.black_doves_market_processor import (
    prepare_market_comparison_csv,
)


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Create baseline-normalized company-versus-"
            "benchmark market data for BLACK DOVES."
        )
    )
    parser.add_argument(
        "company_file",
        type=Path,
    )
    parser.add_argument(
        "benchmark_file",
        type=Path,
    )
    parser.add_argument(
        "output_file",
        type=Path,
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
        data, output_path = (
            prepare_market_comparison_csv(
                company_file=options.company_file,
                benchmark_file=options.benchmark_file,
                output_file=options.output_file,
                price_column=options.price_column,
            )
        )
    except (
        FileNotFoundError,
        TypeError,
        ValueError,
    ) as error:
        parser.error(str(error))

    print("\nBLACK DOVES market comparison completed.")
    print(f"Trading days: {len(data)}")
    print(
        "Period: "
        f"{data['Date'].min().date().isoformat()} to "
        f"{data['Date'].max().date().isoformat()}"
    )
    print(f"CSV file: {output_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
