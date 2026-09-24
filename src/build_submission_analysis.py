"""Create the robustness tables used by the submission report."""

from pathlib import Path

import pandas as pd

from src.services.statistical_robustness import (
    adjust_lag_p_values,
    event_study_bootstrap_table,
    export_csv,
)


ROOT = Path(__file__).resolve().parents[1]


def main():
    analysis_directory = ROOT / "data" / "analysis"
    company_summary = pd.read_csv(
        analysis_directory / "market_universe_company_summary.csv"
    )
    lag_results = pd.read_csv(
        analysis_directory / "fuel_price_lag_results.csv"
    )

    bootstrap = event_study_bootstrap_table(company_summary)
    adjusted_lags = adjust_lag_p_values(lag_results)

    bootstrap_path = export_csv(
        bootstrap,
        analysis_directory / "event_study_bootstrap_summary.csv",
    )
    lag_path = export_csv(
        adjusted_lags,
        analysis_directory / "fuel_price_lag_adjusted.csv",
    )
    print(f"Bootstrap summary: {bootstrap_path}")
    print(f"Multiplicity-adjusted lags: {lag_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
