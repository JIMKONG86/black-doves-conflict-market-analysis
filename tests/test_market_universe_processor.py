import tempfile
import unittest

from pathlib import Path

import pandas as pd

from src.data_access.market_reader import market_data_file_path
from src.models.market_universe_entry import (
    MarketUniverseEntry,
)
from src.services.market_universe_processor import (
    process_market_universe,
)


class TestMarketUniverseProcessor(unittest.TestCase):
    def test_builds_individual_and_combined_outputs(self):
        entries = [
            self._entry("CMP001", "AAA", True),
            self._entry("CMP002", "BBB", False),
        ]

        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            raw = directory / "raw"
            self._save_raw(raw, "AAA", [100.0, 110.0])
            self._save_raw(raw, "BBB", [100.0, 90.0])
            self._save_raw(raw, "^INDEX", [100.0, 102.0])

            combined, combined_path, report, report_path = (
                process_market_universe(
                    entries=entries,
                    raw_directory=raw,
                    output_directory=directory / "processed",
                    combined_file=directory / "combined.csv",
                    report_file=directory / "report.csv",
                )
            )

            self.assertEqual(len(combined), 4)
            self.assertTrue(combined_path.is_file())
            self.assertTrue(report_path.is_file())
            self.assertEqual(
                report["status"].tolist(),
                ["PROCESSED", "PROCESSED"],
            )
            self.assertEqual(
                combined["company_id"].unique().tolist(),
                ["CMP001", "CMP002"],
            )
            self.assertEqual(
                combined.loc[
                    combined["company_id"] == "CMP001",
                    "is_confirmatory",
                ].unique().tolist(),
                [True],
            )
            self.assertAlmostEqual(
                combined.loc[
                    (combined["company_id"] == "CMP001")
                    & (combined["Date"] == "2023-01-03"),
                    "abnormal_return",
                ].iloc[0],
                0.08,
            )

    def test_reports_missing_raw_company_without_dropping_it(self):
        entry = self._entry("CMP001", "AAA", True)

        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            raw = directory / "raw"
            self._save_raw(raw, "^INDEX", [100.0, 102.0])

            combined, _, report, _ = process_market_universe(
                entries=[entry],
                raw_directory=raw,
                output_directory=directory / "processed",
                combined_file=directory / "combined.csv",
                report_file=directory / "report.csv",
            )

            self.assertTrue(combined.empty)
            self.assertEqual(
                report.loc[0, "status"],
                "MISSING_RAW_FILE",
            )
            self.assertIn("AAA.csv", report.loc[0, "error"])

    @staticmethod
    def _entry(company_id, ticker, is_confirmatory):
        return MarketUniverseEntry(
            company_id=company_id,
            company_name=f"Company {company_id}",
            market_data_ticker=ticker,
            benchmark_ticker="^INDEX",
            trade_currency="EUR",
            primary_listing_exchange="Test Exchange",
            analysis_tier="PRIMARY_DIRECT",
            role_category="Defence Contractor",
            is_confirmatory=is_confirmatory,
        )

    @staticmethod
    def _save_raw(directory, ticker, prices):
        path = market_data_file_path(ticker, directory)
        path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(
            {
                "Date": ["2023-01-02", "2023-01-03"],
                "Ticker": [ticker, ticker],
                "Adj Close": prices,
            }
        ).to_csv(path, index=False)


if __name__ == "__main__":
    unittest.main()
