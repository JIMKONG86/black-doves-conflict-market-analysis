import csv
import tempfile
import unittest
from pathlib import Path

from src.visualize_german_financial_channels import (
    create_german_financial_channels_chart,
)


class TestGermanFinancialChannelsVisualization(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary_directory.name)
        self.observations_file = self.directory / "observations.csv"
        rows = [
            {
                "observation_id": "T-1",
                "observation_date": "2026-08-04",
                "metric": "DAX",
                "value": "26202.35",
                "unit": "index_points",
                "point_type": "CLOSE",
                "context_note": "Record close on Iran hope and falling oil prices.",
                "source_name": "Handelsblatt",
                "source_url": "https://example.com/a",
            },
            {
                "observation_id": "T-2",
                "observation_date": "2026-08-19",
                "metric": "BUND_10Y_YIELD",
                "value": "3.33",
                "unit": "percent",
                "point_type": "INTRADAY_HIGH",
                "context_note": "Highest since May 2011.",
                "source_name": "kagels-trading.de",
                "source_url": "https://example.com/b",
            },
        ]
        with self.observations_file.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_creates_chart_with_both_panels_and_caveat(self):
        output = self.directory / "de_channels.html"

        result_path, dax_count, bund_count = (
            create_german_financial_channels_chart(
                observations_file=self.observations_file,
                output_path=output,
            )
        )

        self.assertTrue(result_path.exists())
        self.assertEqual(dax_count, 1)
        self.assertEqual(bund_count, 1)

        html = result_path.read_text(encoding="utf-8")
        self.assertIn("not a continuous daily time series", html)

    def test_rejects_non_html_output_path(self):
        with self.assertRaises(ValueError):
            create_german_financial_channels_chart(
                observations_file=self.observations_file,
                output_path=self.directory / "chart.png",
            )

    def test_rejects_missing_required_columns(self):
        broken_file = self.directory / "broken.csv"
        broken_file.write_text("observation_date\n2026-08-04\n", encoding="utf-8")

        with self.assertRaises(ValueError):
            create_german_financial_channels_chart(
                observations_file=broken_file,
                output_path=self.directory / "chart.html",
            )

    def test_rejects_non_numeric_value(self):
        rows = list(csv.DictReader(self.observations_file.open(encoding="utf-8")))
        rows[0]["value"] = "not-a-number"
        with self.observations_file.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

        with self.assertRaises(ValueError):
            create_german_financial_channels_chart(
                observations_file=self.observations_file,
                output_path=self.directory / "chart.html",
            )


if __name__ == "__main__":
    unittest.main()
