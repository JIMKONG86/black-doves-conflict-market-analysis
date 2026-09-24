import tempfile
import unittest

from pathlib import Path

import pandas as pd

from src.models.market_universe_entry import (
    MarketUniverseEntry,
)
from src.services.market_universe_collector import (
    build_market_instruments,
    collect_market_universe,
)


class TestMarketUniverseCollector(unittest.TestCase):
    def test_deduplicates_shared_benchmark(self):
        instruments = build_market_instruments(
            [self._entry("CMP001", "AAA"), self._entry("CMP002", "BBB")]
        )

        self.assertEqual(len(instruments), 3)
        self.assertEqual(
            [item.ticker for item in instruments],
            ["AAA", "BBB", "^INDEX"],
        )
        self.assertEqual(instruments[-1].benchmark_for_count, 2)

    def test_collects_every_instrument_and_writes_report(self):
        calls = []

        def fake_download(ticker, start_date, end_date):
            calls.append((ticker, start_date, end_date))
            return self._market_data(ticker)

        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            report, report_path = collect_market_universe(
                entries=[self._entry("CMP001", "AAA")],
                start_date="2023-01-01",
                end_date="2026-09-03",
                output_directory=directory / "raw",
                report_file=directory / "report.csv",
                request_delay=0,
                retry_delay=0,
                max_attempts=1,
                download_function=fake_download,
            )

            self.assertEqual(
                [call[0] for call in calls],
                ["AAA", "^INDEX"],
            )
            self.assertEqual(
                report["status"].tolist(),
                ["DOWNLOADED", "DOWNLOADED"],
            )
            self.assertTrue(report_path.is_file())
            self.assertTrue((directory / "raw" / "AAA.csv").is_file())
            self.assertTrue((directory / "raw" / "INDEX.csv").is_file())

    def test_records_failure_without_stopping_other_tickers(self):
        def fake_download(ticker, start_date, end_date):
            if ticker == "AAA":
                raise ValueError("provider unavailable")

            return self._market_data(ticker)

        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            report, _ = collect_market_universe(
                entries=[self._entry("CMP001", "AAA")],
                start_date="2023-01-01",
                end_date="2026-09-03",
                output_directory=directory / "raw",
                report_file=directory / "report.csv",
                request_delay=0,
                retry_delay=0,
                max_attempts=2,
                download_function=fake_download,
            )

            self.assertEqual(
                report["status"].tolist(),
                ["FAILED", "DOWNLOADED"],
            )
            self.assertEqual(report.loc[0, "attempts"], 2)
            self.assertIn(
                "provider unavailable",
                report.loc[0, "error"],
            )

    def test_resume_skips_existing_file(self):
        def unexpected_download(ticker, start_date, end_date):
            raise AssertionError("download must not be called")

        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            raw_directory = directory / "raw"
            raw_directory.mkdir()
            self._market_data("AAA").to_csv(
                raw_directory / "AAA.csv",
                index=False,
            )
            self._market_data("^INDEX").to_csv(
                raw_directory / "INDEX.csv",
                index=False,
            )

            report, _ = collect_market_universe(
                entries=[self._entry("CMP001", "AAA")],
                start_date="2023-01-01",
                end_date="2026-09-03",
                output_directory=raw_directory,
                report_file=directory / "report.csv",
                request_delay=0,
                retry_delay=0,
                download_function=unexpected_download,
            )

            self.assertEqual(
                report["status"].tolist(),
                ["SKIPPED_EXISTING", "SKIPPED_EXISTING"],
            )

    @staticmethod
    def _entry(company_id, ticker):
        return MarketUniverseEntry(
            company_id=company_id,
            company_name=f"Company {company_id}",
            market_data_ticker=ticker,
            benchmark_ticker="^INDEX",
            trade_currency="EUR",
            primary_listing_exchange="Test Exchange",
            analysis_tier="PRIMARY_DIRECT",
            role_category="Defence Contractor",
            is_confirmatory=company_id == "CMP001",
        )

    @staticmethod
    def _market_data(ticker):
        return pd.DataFrame(
            {
                "Date": ["2023-01-02", "2023-01-03"],
                "Ticker": [ticker, ticker],
                "Adj Close": [100.0, 101.0],
            }
        )


if __name__ == "__main__":
    unittest.main()
