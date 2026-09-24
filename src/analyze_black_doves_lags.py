import argparse
import sys

from pathlib import Path

from src.services.lagged_conflict_market_analyzer import (
    LaggedConflictMarketAnalyzer,
)


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Measure exploratory same-week and lagged "
            "associations between conflict intensity and "
            "weekly abnormal market returns."
        )
    )
    parser.add_argument(
        "input_file",
        type=Path,
        help="Joined BLACK DOVES country-week CSV.",
    )
    parser.add_argument(
        "output_file",
        type=Path,
        help="Destination lag-analysis CSV.",
    )
    parser.add_argument(
        "--metric",
        action="append",
        dest="metrics",
        help=(
            "Conflict metric to analyze. May be repeated. "
            "Defaults to strike_events and "
            "strike_fatalities."
        ),
    )
    parser.add_argument(
        "--lag",
        action="append",
        dest="lags",
        type=int,
        help=(
            "Future market-response lag in weeks. May be "
            "repeated. Defaults to 0, 1, 2 and 4."
        ),
    )
    return parser


def main(arguments=None):
    parser = build_parser()
    options = parser.parse_args(arguments)
    analyzer = LaggedConflictMarketAnalyzer()

    try:
        results, summary = analyzer.analyze(
            input_file=options.input_file,
            metrics=options.metrics,
            lags=options.lags,
        )
        output_path = analyzer.export_csv(
            results,
            options.output_file,
        )
    except (
        FileNotFoundError,
        TypeError,
        ValueError,
    ) as error:
        parser.error(str(error))

    print("\nBLACK DOVES lag analysis completed.")
    print(f"Input country-week rows: {summary.input_rows}")
    print(f"Weeks analyzed: {summary.week_count}")
    print(f"Scopes analyzed: {summary.scope_count}")
    print(f"Association rows: {summary.result_rows}")
    print(
        "Period: "
        f"{summary.first_week.isoformat()} to "
        f"{summary.last_week.isoformat()}"
    )
    print(
        "Market comparison: "
        f"{summary.company_ticker} versus "
        f"{summary.benchmark_ticker}"
    )

    valid_results = results[
        results["status"] == "ok"
    ].copy()

    if not valid_results.empty:
        strongest_index = (
            valid_results["spearman_correlation"]
            .abs()
            .idxmax()
        )
        strongest = valid_results.loc[
            strongest_index
        ]
        print(
            "Strongest exploratory association: "
            f"{strongest['scope_name']} / "
            f"{strongest['conflict_metric']} / "
            f"lag {strongest['lag_weeks']} week(s) / "
            "Spearman "
            f"{strongest['spearman_correlation']:.3f}"
        )

    print(f"CSV file: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
