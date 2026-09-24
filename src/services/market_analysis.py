from pathlib import Path
import pandas as pd


def calculate_daily_returns(
    market_data,
    price_column="Adj Close",
):
    required_columns = {"Date", price_column}
    missing_columns = required_columns - set(market_data.columns)

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    result = market_data.copy()
    result["Date"] = pd.to_datetime(result["Date"])
    result = result.sort_values("Date")

    result["daily_return"] = (
        result[price_column].pct_change()
    )

    return result


def compare_market_returns(
    company_data,
    benchmark_data,
    price_column="Adj Close",
):
    company_prices = company_data[
        ["Date", price_column]
    ].copy()

    benchmark_prices = benchmark_data[
        ["Date", price_column]
    ].copy()

    company_prices["Date"] = pd.to_datetime(
        company_prices["Date"]
    )
    benchmark_prices["Date"] = pd.to_datetime(
        benchmark_prices["Date"]
    )

    company_prices = company_prices.rename(
        columns={price_column: "company_price"}
    )
    benchmark_prices = benchmark_prices.rename(
        columns={price_column: "benchmark_price"}
    )

    comparison = pd.merge(
        company_prices,
        benchmark_prices,
        on="Date",
        how="inner",
    ).sort_values("Date")

    comparison["company_return"] = (
        comparison["company_price"].pct_change()
    )

    comparison["benchmark_return"] = (
        comparison["benchmark_price"].pct_change()
    )

    comparison["abnormal_return"] = (
        comparison["company_return"]
        - comparison["benchmark_return"]
    )

    comparison["company_cumulative_return"] = (
        (1 + comparison["company_return"]).cumprod() - 1
    )

    comparison["benchmark_cumulative_return"] = (
        (1 + comparison["benchmark_return"]).cumprod() - 1
    )

    comparison["cumulative_abnormal_return"] = (
        comparison["abnormal_return"].cumsum()
    )

    return comparison.dropna().reset_index(drop=True)

if __name__ == "__main__":
    rheinmetall_data = pd.read_csv(
        "data/raw/market/RHM_DE.csv"
    )

    dax_data = pd.read_csv(
        "data/raw/market/GDAXI.csv"
    )

    result = compare_market_returns(
        company_data=rheinmetall_data,
        benchmark_data=dax_data,
    )

    output_directory = Path(
        "data/processed/market"
    )
    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_file = (
        output_directory / "RHM_DE_vs_GDAXI.csv"
    )

    result.to_csv(
        output_file,
        index=False,
    )

    print(result.head())
    print("Analysis saved to:", output_file)