import time

from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd

from src.data_access.market_reader import (
    download_market_data,
    market_data_file_path,
    save_market_data,
)


@dataclass(frozen=True)
class MarketInstrument:
    instrument_type: str
    ticker: str
    company_id: str = ""
    company_name: str = ""
    analysis_tier: str = ""
    is_confirmatory: bool = False
    benchmark_for_count: int = 0


REPORT_COLUMNS = (
    "instrument_type",
    "ticker",
    "company_id",
    "company_name",
    "analysis_tier",
    "is_confirmatory",
    "benchmark_for_count",
    "status",
    "attempts",
    "row_count",
    "first_date",
    "last_date",
    "file_path",
    "error",
)


def build_market_instruments(entries):
    companies = [
        MarketInstrument(
            instrument_type="COMPANY",
            ticker=entry.market_data_ticker,
            company_id=entry.company_id,
            company_name=entry.company_name,
            analysis_tier=entry.analysis_tier,
            is_confirmatory=entry.is_confirmatory,
        )
        for entry in entries
    ]

    benchmark_counts = {}

    for entry in entries:
        benchmark_counts[entry.benchmark_ticker] = (
            benchmark_counts.get(entry.benchmark_ticker, 0)
            + 1
        )

    benchmarks = [
        MarketInstrument(
            instrument_type="BENCHMARK",
            ticker=ticker,
            benchmark_for_count=count,
        )
        for ticker, count in sorted(benchmark_counts.items())
    ]

    return companies + benchmarks


def collect_market_universe(
    entries,
    start_date,
    end_date,
    output_directory,
    report_file,
    refresh=False,
    request_delay=1.0,
    retry_delay=5.0,
    max_attempts=2,
    download_function=download_market_data,
    sleep_function=time.sleep,
):
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")

    if request_delay < 0:
        raise ValueError("request_delay cannot be negative")

    if retry_delay < 0:
        raise ValueError("retry_delay cannot be negative")

    instruments = build_market_instruments(entries)
    results = []

    for position, instrument in enumerate(instruments):
        output_path = market_data_file_path(
            ticker=instrument.ticker,
            output_directory=output_directory,
        )

        if output_path.is_file() and not refresh:
            results.append(
                _result_from_existing(instrument, output_path)
            )
            continue

        result = _download_one(
            instrument=instrument,
            start_date=start_date,
            end_date=end_date,
            output_directory=output_directory,
            max_attempts=max_attempts,
            download_function=download_function,
            sleep_function=sleep_function,
            retry_delay=retry_delay,
        )
        results.append(result)

        if (
            request_delay
            and position < len(instruments) - 1
        ):
            sleep_function(request_delay)

    report = pd.DataFrame(results, columns=REPORT_COLUMNS)
    report_path = _write_report(report, report_file)

    return report, report_path


def _download_one(
    instrument,
    start_date,
    end_date,
    output_directory,
    max_attempts,
    download_function,
    sleep_function,
    retry_delay,
):
    error = None

    for attempt in range(1, max_attempts + 1):
        try:
            data = download_function(
                ticker=instrument.ticker,
                start_date=start_date,
                end_date=end_date,
            )
            output_path = save_market_data(
                market_data=data,
                ticker=instrument.ticker,
                output_directory=output_directory,
            )

            return _result_from_data(
                instrument=instrument,
                data=data,
                output_path=output_path,
                status="DOWNLOADED",
                attempts=attempt,
            )
        except Exception as caught_error:
            error = caught_error

            if attempt < max_attempts and retry_delay:
                sleep_function(retry_delay * attempt)

    return _base_result(
        instrument,
        status="FAILED",
        attempts=max_attempts,
        error=str(error),
    )


def _result_from_existing(instrument, output_path):
    try:
        data = pd.read_csv(output_path)
        result = _result_from_data(
            instrument=instrument,
            data=data,
            output_path=output_path,
            status="SKIPPED_EXISTING",
            attempts=0,
        )
    except Exception as error:
        result = _base_result(
            instrument,
            status="FAILED_EXISTING_FILE",
            attempts=0,
            file_path=str(output_path),
            error=str(error),
        )

    return result


def _result_from_data(
    instrument,
    data,
    output_path,
    status,
    attempts,
):
    if "Date" not in data.columns:
        raise ValueError("Market data is missing required Date column")

    dates = pd.to_datetime(data["Date"], errors="coerce")

    if dates.isna().any():
        raise ValueError("Market data contains invalid Date values")

    return _base_result(
        instrument,
        status=status,
        attempts=attempts,
        row_count=len(data),
        first_date=dates.min().date().isoformat(),
        last_date=dates.max().date().isoformat(),
        file_path=str(output_path),
    )


def _base_result(
    instrument,
    status,
    attempts,
    row_count=0,
    first_date="",
    last_date="",
    file_path="",
    error="",
):
    result = asdict(instrument)
    result.update(
        {
            "status": status,
            "attempts": attempts,
            "row_count": row_count,
            "first_date": first_date,
            "last_date": last_date,
            "file_path": file_path,
            "error": error,
        }
    )

    return result


def _write_report(report, report_file):
    report_path = Path(report_file)

    if report_path.suffix.casefold() != ".csv":
        raise ValueError("Market download report must use .csv")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = report_path.with_suffix(".csv.tmp")
    report.to_csv(temporary_path, index=False)
    temporary_path.replace(report_path)

    return report_path
