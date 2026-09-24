import argparse
import sys

from pathlib import Path

from src.services.fuel_price_lag_analysis import FuelPriceLagAnalyzer


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Measure exploratory weekly transmission lags from Brent crude "
            "to German petrol and diesel prices."
        )
    )
    parser.add_argument(
        "--weekly-file",
        type=Path,
        default=Path("data/processed/energy/energy_price_weekly_panel.csv"),
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        default=Path("data/analysis/fuel_price_lag_results.csv"),
    )
    parser.add_argument(
        "--lag",
        action="append",
        dest="lags",
        type=int,
        help="Future German fuel-price lag in weeks; defaults to 0 through 8.",
    )
    return parser


def main(arguments=None):
    parser = build_parser()
    options = parser.parse_args(arguments)
    analyzer = FuelPriceLagAnalyzer()

    try:
        results, summary = analyzer.analyze(
            options.weekly_file, lags=options.lags
        )
        output_path = analyzer.export_csv(results, options.output_file)
    except (FileNotFoundError, TypeError, ValueError) as error:
        parser.error(str(error))

    print("\nBLACK DOVES fuel-price lag analysis completed.")
    print(
        f"Period: {summary.first_fuel_date} to {summary.last_fuel_date}"
    )
    print(f"Weekly observations: {summary.weekly_observations}")
    print(f"Lags: {', '.join(str(value) for value in summary.lags)} weeks")

    strongest = results[results["is_strongest_for_series"]]
    for row in strongest.itertuples(index=False):
        print(
            f"Strongest {row.product.lower()} / "
            f"{row.tax_basis.lower()}: lag {row.lag_weeks}, "
            f"Spearman {row.spearman_correlation:.3f}"
        )

    print(f"Lag results: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
