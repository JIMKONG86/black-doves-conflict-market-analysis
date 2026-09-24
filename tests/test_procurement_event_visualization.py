import tempfile
import unittest

from pathlib import Path

import pandas as pd

from src.visualize_procurement_event_study import (
    _add_outside_legend,
    create_procurement_event_study_chart,
)


class TestProcurementEventVisualization(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary_directory.name)
        self.input_file = self.directory / "event_window.csv"
        rows = []

        for event_index in range(2):
            for relative_day in (-1, 0, 1):
                rows.append(
                    {
                        "event_id": f"event-{event_index}",
                        "announcement_date": (
                            f"2025-01-{15 + event_index:02d}"
                        ),
                        "effective_market_date": (
                            f"2025-01-{15 + event_index:02d}"
                        ),
                        "buyer_name": f"Buyer {event_index}",
                        "title": f"Order {event_index}",
                        "systems": "Skynex",
                        "relative_trading_day": relative_day,
                        "abnormal_return": (
                            0.01 * (event_index + relative_day)
                        ),
                    }
                )

        pd.DataFrame(rows).to_csv(self.input_file, index=False)

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_creates_html_chart_and_aggregate_csv(self):
        aggregate_file = self.directory / "aggregate.csv"
        chart_file = self.directory / "chart.html"

        result_path, result_aggregate, summary = (
            create_procurement_event_study_chart(
                input_file=self.input_file,
                aggregate_output_file=aggregate_file,
                output_path=chart_file,
            )
        )

        self.assertTrue(result_path.is_file())
        self.assertTrue(result_aggregate.is_file())
        self.assertIn(
            "BLACK DOVES",
            result_path.read_text(encoding="utf-8"),
        )
        self.assertEqual(summary.event_count, 2)

    def test_rejects_non_html_output(self):
        with self.assertRaisesRegex(ValueError, "use .html"):
            create_procurement_event_study_chart(
                input_file=self.input_file,
                aggregate_output_file=(
                    self.directory / "aggregate.csv"
                ),
                output_path=self.directory / "chart.txt",
            )

    def test_adds_event_legend_to_right_side(self):
        from bokeh.plotting import figure

        chart = figure()
        line = chart.line(
            [0, 1],
            [0.0, 0.1],
        )

        legend = _add_outside_legend(
            chart,
            [("Italian Army", [line])],
        )

        self.assertIn(legend, chart.right)
        self.assertNotIn(legend, chart.center)
        self.assertEqual(
            legend.title,
            "Procurement announcements",
        )
        self.assertEqual(legend.click_policy, "hide")


if __name__ == "__main__":
    unittest.main()
