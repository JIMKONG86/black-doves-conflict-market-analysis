import logging
import re
from pathlib import Path


logger = logging.getLogger(__name__)


def download_market_data(ticker, start_date, end_date):
    try:
        import yfinance as yf
    except ImportError as error:
        raise RuntimeError(
            "yfinance is required for live market downloads"
        ) from error

    logger.info(
        "Downloading market data for %s from %s to %s",
        ticker,
        start_date,
        end_date,
    )

    market_data = yf.download(
        ticker,
        start=start_date,
        end=end_date,
        auto_adjust=False,
        progress=False,
        multi_level_index=False,
    )

    if market_data.empty:
        raise ValueError(
            f"No market data returned for ticker '{ticker}'"
        )

    market_data = market_data.reset_index()
    market_data.insert(1, "Ticker", ticker)

    return market_data


def save_market_data(
    market_data,
    ticker,
    output_directory="data/raw/market",
):
    file_path = market_data_file_path(
        ticker=ticker,
        output_directory=output_directory,
    )
    file_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = file_path.with_suffix(".csv.tmp")

    market_data.to_csv(
        temporary_path,
        index=False,
    )
    temporary_path.replace(file_path)

    logger.info(
        "Saved market data for %s to %s",
        ticker,
        file_path,
    )

    return file_path


def market_data_file_path(
    ticker,
    output_directory="data/raw/market",
):
    ticker_text = str(ticker).strip()

    if not ticker_text:
        raise ValueError("ticker cannot be empty")

    safe_ticker = re.sub(
        r"[^A-Za-z0-9_-]+",
        "_",
        ticker_text.lstrip("^"),
    ).strip("_")

    if not safe_ticker:
        raise ValueError(
            f"ticker does not contain a safe filename: {ticker}"
        )

    return Path(output_directory) / f"{safe_ticker}.csv"


if __name__ == "__main__":
    for ticker_symbol in ("RHM.DE", "^GDAXI"):
        data = download_market_data(
            ticker=ticker_symbol,
            start_date="2025-01-01",
            end_date="2026-08-24",
        )

        print(f"\nMarket data for {ticker_symbol}:")
        print(data.head())

        file_path = save_market_data(
            market_data=data,
            ticker=ticker_symbol,
        )

        print("Saved to:", file_path)
