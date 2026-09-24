from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd

from src.data_access.market_reader import market_data_file_path
from src.services.black_doves_market_processor import (
    compare_market_returns_with_market_model,
)


@dataclass(frozen=True)
class MarketProcessingResult:
    company_id: str
    company_name: str
    market_data_ticker: str
    benchmark_ticker: str
    analysis_tier: str
    is_confirmatory: bool
    status: str
    row_count: int = 0
    first_date: str = ""
    last_date: str = ""
    output_file: str = ""
    error: str = ""


REPORT_COLUMNS = tuple(
    MarketProcessingResult.__dataclass_fields__.keys()
)


def process_market_universe(
    entries,
    raw_directory,
    output_directory,
    combined_file,
    report_file,
    price_column="Adj Close",
):
    output_directory = Path(output_directory)
    frames = []
    results = []

    for entry in entries:
        company_file = market_data_file_path(
            entry.market_data_ticker,
            raw_directory,
        )
        benchmark_file = market_data_file_path(
            entry.benchmark_ticker,
            raw_directory,
        )

        missing = [
            str(path)
            for path in (company_file, benchmark_file)
            if not path.is_file()
        ]

        if missing:
            results.append(
                _result(
                    entry,
                    status="MISSING_RAW_FILE",
                    error="; ".join(missing),
                )
            )
            continue

        try:
            comparison = compare_market_returns_with_market_model(
                company_data=pd.read_csv(company_file),
                benchmark_data=pd.read_csv(benchmark_file),
                price_column=price_column,
            )
            enriched = _add_company_metadata(
                comparison,
                entry,
            )
            output_path = _comparison_file_path(
                entry,
                output_directory,
            )
            _write_csv(enriched, output_path)
            frames.append(enriched)
            results.append(
                _result(
                    entry,
                    status="PROCESSED",
                    row_count=len(enriched),
                    first_date=(
                        enriched["Date"].min().date().isoformat()
                    ),
                    last_date=(
                        enriched["Date"].max().date().isoformat()
                    ),
                    output_file=str(output_path),
                )
            )
        except Exception as error:
            results.append(
                _result(
                    entry,
                    status="FAILED",
                    error=str(error),
                )
            )

    combined = _combine_frames(frames)
    combined_path = _write_csv(combined, combined_file)
    report = pd.DataFrame(
        [asdict(result) for result in results],
        columns=REPORT_COLUMNS,
    )
    report_path = _write_csv(report, report_file)

    return combined, combined_path, report, report_path


def _add_company_metadata(comparison, entry):
    enriched = comparison.copy()
    metadata = (
        ("company_id", entry.company_id),
        ("company_name", entry.company_name),
        ("market_data_ticker", entry.market_data_ticker),
        ("benchmark_ticker", entry.benchmark_ticker),
        ("trade_currency", entry.trade_currency),
        (
            "primary_listing_exchange",
            entry.primary_listing_exchange,
        ),
        ("analysis_tier", entry.analysis_tier),
        ("role_category", entry.role_category),
        ("is_confirmatory", entry.is_confirmatory),
    )

    for position, (column, value) in enumerate(metadata):
        enriched.insert(position, column, value)

    return enriched


def _combine_frames(frames):
    if not frames:
        return pd.DataFrame()

    return pd.concat(frames, ignore_index=True).sort_values(
        ["company_id", "Date"]
    ).reset_index(drop=True)


def _comparison_file_path(entry, output_directory):
    company_stem = market_data_file_path(
        entry.market_data_ticker,
        ".",
    ).stem
    benchmark_stem = market_data_file_path(
        entry.benchmark_ticker,
        ".",
    ).stem

    return Path(output_directory) / (
        f"{entry.company_id}_{company_stem}_vs_{benchmark_stem}.csv"
    )


def _result(
    entry,
    status,
    row_count=0,
    first_date="",
    last_date="",
    output_file="",
    error="",
):
    return MarketProcessingResult(
        company_id=entry.company_id,
        company_name=entry.company_name,
        market_data_ticker=entry.market_data_ticker,
        benchmark_ticker=entry.benchmark_ticker,
        analysis_tier=entry.analysis_tier,
        is_confirmatory=entry.is_confirmatory,
        status=status,
        row_count=row_count,
        first_date=first_date,
        last_date=last_date,
        output_file=output_file,
        error=error,
    )


def _write_csv(data, file_path):
    path = Path(file_path)

    if path.suffix.casefold() != ".csv":
        raise ValueError(f"CSV output required: {path}")

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(".csv.tmp")
    data.to_csv(temporary_path, index=False)
    temporary_path.replace(path)

    return path
