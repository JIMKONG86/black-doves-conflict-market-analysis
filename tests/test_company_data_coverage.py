import csv
import unittest

from pathlib import Path


class TestCompanyDataCoverage(unittest.TestCase):
    def test_all_configured_companies_reach_both_company_analyses(self):
        root = Path(__file__).resolve().parents[1]
        configured = self._company_ids(
            root / "config" / "company_market_universe.csv"
        )
        event_study = self._company_ids(
            root / "data" / "analysis" / "market_universe_company_summary.csv"
        )
        market_position = self._company_ids(
            root / "data" / "analysis" / "market_position_company_summary.csv"
        )

        self.assertEqual(len(configured), 46)
        self.assertEqual(event_study, configured)
        self.assertEqual(market_position, configured)

    @staticmethod
    def _company_ids(path):
        with path.open("r", encoding="utf-8-sig", newline="") as file:
            return {
                row["company_id"].strip()
                for row in csv.DictReader(file)
                if row.get("company_id", "").strip()
            }


if __name__ == "__main__":
    unittest.main()
