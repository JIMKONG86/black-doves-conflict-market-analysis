import tempfile
import unittest

from pathlib import Path

import pandas as pd

from src.black_doves_visualization import (
    _header_html,
    _load_analysis_data,
    _one_value,
    create_black_doves_chart,
)


class TestBlackDovesVisualization(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = (
            tempfile.TemporaryDirectory()
        )
        self.directory = Path(
            self.temporary_directory.name
        )

    def tearDown(self):
        self.temporary_directory.cleanup()

    @staticmethod
    def _analysis_row():
        return {
            "week_end_date": "2025-01-11",
            "market_date": "2025-01-10",
            "country_name": "Iran",
            "strike_events": 6,
            "strike_fatalities": 3,
            "company_ticker": "RHM.DE",
            "benchmark_ticker": "^GDAXI",
            "company_cumulative_return": 0.10,
            "benchmark_cumulative_return": 0.03,
            "weekly_abnormal_return": 0.02,
        }

    def test_loads_and_parses_analysis_data(self):
        file_path = self.directory / "analysis.csv"
        pd.DataFrame(
            [self._analysis_row()]
        ).to_csv(file_path, index=False)

        data = _load_analysis_data(file_path)

        self.assertTrue(
            pd.api.types.is_datetime64_any_dtype(
                data["week_end_date"]
            )
        )
        self.assertEqual(data.loc[0, "strike_events"], 6)

    def test_rejects_missing_required_column(self):
        row = self._analysis_row()
        row.pop("strike_fatalities")
        file_path = self.directory / "analysis.csv"
        pd.DataFrame([row]).to_csv(file_path, index=False)

        with self.assertRaisesRegex(
            ValueError,
            "strike_fatalities",
        ):
            _load_analysis_data(file_path)

    def test_requires_one_ticker_value(self):
        data = pd.DataFrame(
            {"company_ticker": ["RHM.DE", "LMT"]}
        )

        with self.assertRaisesRegex(
            ValueError,
            "exactly one value",
        ):
            _one_value(data, "company_ticker")

    def test_embeds_png_logo(self):
        logo_path = self.directory / "logo.png"
        logo_path.write_bytes(b"example-png-bytes")

        result = _header_html(logo_path)

        self.assertIn("data:image/png;base64,", result)
        self.assertIn("BLACK DOVES", result)

    def test_creates_dark_self_contained_company_conflict_report(self):
        input_file = self.directory / "analysis.csv"
        output_file = self.directory / "report.html"
        pd.DataFrame([self._analysis_row()]).to_csv(input_file, index=False)

        result = create_black_doves_chart(input_file, output_file)

        document = result.read_text(encoding="utf-8")
        self.assertIn("Rheinmetall conflict case", document)
        self.assertIn("color-scheme: dark", document)
        self.assertIn("#151E29", document)
        self.assertNotIn("https://cdn.bokeh.org", document)


if __name__ == "__main__":
    unittest.main()
