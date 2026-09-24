from pathlib import Path

import pandas as pd

from src.services.ols_market_model import add_market_model_columns

# Fixed primary event date of the written assignment
# ("Tracing the Economic Effects of the 2026 Israel-Iran-United States
# Conflict"). Kept as a constant so every OLS market-model estimation
# window is defined identically across all companies, instead of
# implicitly depending on whichever date happens to be passed in.
ASSIGNMENT_PRIMARY_EVENT_DATE = "2026-02-28"


def compare_market_returns_with_baseline(
    company_data,
    benchmark_data,
    price_column="Adj Close",
):
    company_prices = _prepare_prices(
        company_data,
        price_column,
        "company",
    ).rename(
        columns={price_column: "company_price"}
    )
    benchmark_prices = _prepare_prices(
        benchmark_data,
        price_column,
        "benchmark",
    ).rename(
        columns={price_column: "benchmark_price"}
    )

    comparison = pd.merge(
        company_prices,
        benchmark_prices,
        on="Date",
        how="inner",
        validate="one_to_one",
    ).sort_values("Date").reset_index(drop=True)

    if comparison.empty:
        raise ValueError(
            "Company and benchmark data have no "
            "overlapping trading dates"
        )

    comparison["company_return"] = (
        comparison["company_price"]
        .pct_change()
        .fillna(0.0)
    )
    comparison["benchmark_return"] = (
        comparison["benchmark_price"]
        .pct_change()
        .fillna(0.0)
    )
    comparison["abnormal_return"] = (
        comparison["company_return"]
        - comparison["benchmark_return"]
    )
    comparison["company_cumulative_return"] = (
        (1.0 + comparison["company_return"]).cumprod()
        - 1.0
    )
    comparison["benchmark_cumulative_return"] = (
        (1.0 + comparison["benchmark_return"]).cumprod()
        - 1.0
    )
    comparison["cumulative_abnormal_return"] = (
        comparison["abnormal_return"].cumsum()
    )

    return comparison


def compare_market_returns_with_market_model(
    company_data,
    benchmark_data,
    price_column="Adj Close",
    event_date=ASSIGNMENT_PRIMARY_EVENT_DATE,
):
    """Naive market-adjusted comparison plus an OLS market model.

    This wraps ``compare_market_returns_with_baseline`` (which computes
    ``abnormal_return = company_return - benchmark_return``, kept
    unchanged for backward compatibility) and adds an OLS single-factor
    market model (``market_model_abnormal_return``) fitted on the
    trading days strictly before ``event_date``. See
    ``src.services.ols_market_model`` for the full definitions and the
    rationale for keeping both quantities side by side rather than
    replacing one with the other.
    """
    comparison = compare_market_returns_with_baseline(
        company_data=company_data,
        benchmark_data=benchmark_data,
        price_column=price_column,
    )
    return add_market_model_columns(comparison, event_date=event_date)


def prepare_market_comparison_csv(
    company_file,
    benchmark_file,
    output_file,
    price_column="Adj Close",
):
    company_path = Path(company_file)
    benchmark_path = Path(benchmark_file)

    for path, label in (
        (company_path, "Company"),
        (benchmark_path, "Benchmark"),
    ):
        if not path.is_file():
            raise FileNotFoundError(
                f"{label} market CSV not found: {path}"
            )

    result = compare_market_returns_with_baseline(
        company_data=pd.read_csv(company_path),
        benchmark_data=pd.read_csv(benchmark_path),
        price_column=price_column,
    )
    output_path = Path(output_file)

    if output_path.suffix.casefold() != ".csv":
        raise ValueError(
            "Market comparison output must use .csv"
        )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    temporary_path = output_path.with_suffix(
        ".csv.tmp"
    )
    result.to_csv(
        temporary_path,
        index=False,
    )
    temporary_path.replace(output_path)

    return result, output_path


def _prepare_prices(
    market_data,
    price_column,
    label,
):
    if not isinstance(market_data, pd.DataFrame):
        raise TypeError(
            f"{label}_data must be a pandas DataFrame"
        )

    required_columns = {"Date", price_column}
    missing_columns = required_columns - set(
        market_data.columns
    )

    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(
            f"{label.capitalize()} data is missing "
            f"required columns: {missing}"
        )

    result = market_data[["Date", price_column]].copy()
    result["Date"] = pd.to_datetime(
        result["Date"],
        errors="coerce",
    )

    if result["Date"].isna().any():
        raise ValueError(
            f"{label.capitalize()} Date must contain "
            "only valid dates"
        )

    if result["Date"].duplicated().any():
        raise ValueError(
            f"{label.capitalize()} data contains "
            "duplicate dates"
        )

    result[price_column] = pd.to_numeric(
        result[price_column],
        errors="coerce",
    )

    if result[price_column].isna().any():
        raise ValueError(
            f"{label.capitalize()} {price_column} must "
            "contain only numeric values"
        )

    if (result[price_column] <= 0).any():
        raise ValueError(
            f"{label.capitalize()} {price_column} must "
            "contain only positive values"
        )

    return result.sort_values("Date").reset_index(drop=True)
