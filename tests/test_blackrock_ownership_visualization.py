import csv
import tempfile
import unittest
from pathlib import Path

from src.visualize_blackrock_ownership import create_blackrock_ownership_chart


class TestBlackRockOwnershipVisualization(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary_directory.name)
        self.stakes_file = self.directory / "stakes.csv"
        rows = [
            {
                "company_id": "CMP027",
                "company_name": "Lockheed Martin Corporation",
                "ticker": "LMT",
                "war_economy_role": "Defense prime",
                "ownership_percent": "8.18",
                "stake_value_usd_billion": "9.62",
                "filing_period": "Q2 2026",
                "filing_type": "13F",
                "source_name": "Test source",
                "source_url": "https://example.com",
                "notes": "Test note.",
            },
            {
                "company_id": "CMP036",
                "company_name": "RTX Corporation",
                "ticker": "RTX",
                "war_economy_role": "Defense prime",
                "ownership_percent": "",
                "stake_value_usd_billion": "",
                "filing_period": "Q2 2026",
                "filing_type": "13F",
                "source_name": "Test source",
                "source_url": "https://example.com",
                "notes": "Share count only.",
            },
        ]
        with self.stakes_file.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_creates_chart_with_caveat_and_missing_value_handling(self):
        output = self.directory / "blackrock.html"

        result_path, row_count = create_blackrock_ownership_chart(
            stakes_file=self.stakes_file,
            output_path=output,
        )

        self.assertTrue(result_path.exists())
        self.assertEqual(row_count, 2)

        html = result_path.read_text(encoding="utf-8")
        self.assertIn("passive/index-fund manager", html)
        self.assertIn("not specific to war-linked firms", html)
        self.assertIn("share count only", html)

    def test_rejects_non_html_output_path(self):
        with self.assertRaises(ValueError):
            create_blackrock_ownership_chart(
                stakes_file=self.stakes_file,
                output_path=self.directory / "chart.png",
            )

    def test_rejects_missing_required_columns(self):
        broken_file = self.directory / "broken.csv"
        broken_file.write_text("company_name\nTest\n", encoding="utf-8")

        with self.assertRaises(ValueError):
            create_blackrock_ownership_chart(
                stakes_file=broken_file,
                output_path=self.directory / "chart.html",
            )

    def test_rejects_blank_company_name(self):
        rows = list(csv.DictReader(self.stakes_file.open(encoding="utf-8")))
        rows[0]["company_name"] = ""
        with self.stakes_file.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

        with self.assertRaises(ValueError):
            create_blackrock_ownership_chart(
                stakes_file=self.stakes_file,
                output_path=self.directory / "chart.html",
            )


if __name__ == "__main__":
    unittest.main()
