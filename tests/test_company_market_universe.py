import csv
import tempfile
import unittest

from pathlib import Path

from src.data_access.company_market_universe import (
    load_company_market_universe,
)


class TestCompanyMarketUniverse(unittest.TestCase):
    def test_project_universe_has_expected_scope(self):
        entries = load_company_market_universe(
            "config/company_market_universe.csv"
        )

        self.assertEqual(len(entries), 46)
        self.assertEqual(
            len({entry.market_data_ticker for entry in entries}),
            46,
        )
        self.assertEqual(
            len({entry.benchmark_ticker for entry in entries}),
            15,
        )
        self.assertEqual(
            sum(entry.is_confirmatory for entry in entries),
            8,
        )

    def test_rejects_duplicate_market_ticker(self):
        rows = [
            self._row("CMP001", "AAA"),
            self._row("CMP002", "AAA"),
        ]

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "universe.csv"
            self._write_rows(path, rows)

            with self.assertRaisesRegex(
                ValueError,
                "duplicate market_data_ticker",
            ):
                load_company_market_universe(path)

    def test_uses_provider_symbols_for_specialized_benchmarks(self):
        entries = load_company_market_universe(
            "config/company_market_universe.csv"
        )
        by_id = {entry.company_id: entry for entry in entries}

        self.assertEqual(
            by_id["CMP009"].benchmark_ticker,
            "000300.SS",
        )
        self.assertEqual(
            by_id["CMP018"].benchmark_ticker,
            "OBX.OL",
        )

    def test_rejects_invalid_confirmatory_flag(self):
        row = self._row("CMP001", "AAA")
        row["is_confirmatory"] = "TRUE"

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "universe.csv"
            self._write_rows(path, [row])

            with self.assertRaisesRegex(
                ValueError,
                "must be YES or NO",
            ):
                load_company_market_universe(path)

    @staticmethod
    def _row(company_id, ticker):
        return {
            "company_id": company_id,
            "company_name": f"Company {company_id}",
            "market_data_ticker": ticker,
            "benchmark_ticker": "^INDEX",
            "trade_currency": "EUR",
            "primary_listing_exchange": "Test Exchange",
            "analysis_tier": "PRIMARY_DIRECT",
            "role_category": "Defence Contractor",
            "is_confirmatory": "NO",
        }

    @staticmethod
    def _write_rows(path, rows):
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=rows[0].keys(),
            )
            writer.writeheader()
            writer.writerows(rows)


if __name__ == "__main__":
    unittest.main()
