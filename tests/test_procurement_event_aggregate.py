import tempfile
import unittest

from pathlib import Path

import pandas as pd

from src.services.procurement_event_aggregate import (
    ProcurementEventAggregateAnalyzer,
)


class TestProcurementEventAggregateAnalyzer(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary_directory.name)
        self.input_file = self.directory / "event_window.csv"
        self.analyzer = ProcurementEventAggregateAnalyzer()

    def tearDown(self):
        self.temporary_directory.cleanup()

    @staticmethod
    def _rows():
        returns = {
            "event-a": (0.01, 0.02, 0.03),
            "event-b": (-0.01, 0.00, 0.01),
        }
        rows = []

        for event_id, abnormal_returns in returns.items():
            for relative_day, abnormal_return in zip(
                (-1, 0, 1),
                abnormal_returns,
            ):
                rows.append(
                    {
                        "event_id": event_id,
                        "announcement_date": "2025-01-15",
                        "effective_market_date": "2025-01-15",
                        "buyer_name": f"Buyer {event_id}",
                        "title": f"Order {event_id}",
                        "systems": "Skynex",
                        "relative_trading_day": relative_day,
                        "abnormal_return": abnormal_return,
                    }
                )

        return rows

    def _write(self, rows=None):
        if rows is None:
            rows = self._rows()

        pd.DataFrame(rows).to_csv(self.input_file, index=False)

    def test_calculates_aar_and_caar(self):
        self._write()

        detail, aggregate, summary = self.analyzer.analyze(
            self.input_file
        )

        self.assertEqual(summary.event_count, 2)
        self.assertEqual(summary.event_time_rows, 3)
        self.assertEqual(summary.first_relative_day, -1)
        self.assertEqual(summary.last_relative_day, 1)
        self.assertAlmostEqual(
            aggregate.loc[0, "average_abnormal_return"],
            0.0,
        )
        self.assertAlmostEqual(
            aggregate.loc[1, "average_abnormal_return"],
            0.01,
        )
        self.assertAlmostEqual(
            aggregate.loc[2, "cumulative_average_abnormal_return"],
            0.03,
        )

    def test_calculates_individual_event_car(self):
        self._write()

        detail, aggregate, summary = self.analyzer.analyze(
            self.input_file
        )
        event_a = detail[detail["event_id"] == "event-a"]

        self.assertEqual(
            list(event_a["event_car"].round(6)),
            [0.01, 0.03, 0.06],
        )

    def test_calculates_positive_event_share(self):
        self._write()

        detail, aggregate, summary = self.analyzer.analyze(
            self.input_file
        )

        self.assertEqual(
            list(aggregate["positive_abnormal_share"]),
            [0.5, 0.5, 1.0],
        )

    def test_rejects_duplicate_event_day(self):
        rows = self._rows()
        rows.append(dict(rows[0]))
        self._write(rows)

        with self.assertRaisesRegex(ValueError, "duplicate event-day"):
            self.analyzer.analyze(self.input_file)

    def test_rejects_unbalanced_event_windows(self):
        rows = [
            row
            for row in self._rows()
            if not (
                row["event_id"] == "event-b"
                and row["relative_trading_day"] == -1
            )
        ]
        self._write(rows)

        with self.assertRaisesRegex(ValueError, "same complete"):
            self.analyzer.analyze(self.input_file)

    def test_rejects_inconsistent_event_metadata(self):
        rows = self._rows()
        rows[1]["buyer_name"] = "Different buyer"
        self._write(rows)

        with self.assertRaisesRegex(ValueError, "constant"):
            self.analyzer.analyze(self.input_file)

    def test_calculates_ols_aar_and_caar_when_column_present(self):
        rows = self._rows()
        ols_returns = {
            "event-a": (0.02, 0.04, 0.06),
            "event-b": (-0.02, 0.00, 0.02),
        }
        for row in rows:
            offset = (-1, 0, 1).index(row["relative_trading_day"])
            row["market_model_abnormal_return"] = ols_returns[
                row["event_id"]
            ][offset]
        self._write(rows)

        detail, aggregate, summary = self.analyzer.analyze(
            self.input_file
        )

        self.assertIn("ols_event_car", detail.columns)
        self.assertIn("average_ols_abnormal_return", aggregate.columns)
        self.assertIn(
            "cumulative_average_ols_abnormal_return", aggregate.columns
        )
        self.assertAlmostEqual(
            aggregate.loc[0, "average_ols_abnormal_return"], 0.0
        )
        self.assertAlmostEqual(
            aggregate.loc[1, "average_ols_abnormal_return"], 0.02
        )
        self.assertAlmostEqual(
            aggregate.loc[2, "cumulative_average_ols_abnormal_return"],
            0.06,
        )

    def test_omits_ols_columns_when_column_absent(self):
        self._write()

        detail, aggregate, summary = self.analyzer.analyze(
            self.input_file
        )

        self.assertNotIn("ols_event_car", detail.columns)
        self.assertNotIn("average_ols_abnormal_return", aggregate.columns)

    def test_exports_aggregate_csv(self):
        self._write()
        detail, aggregate, summary = self.analyzer.analyze(
            self.input_file
        )
        output_file = self.directory / "aggregate.csv"

        result_path = self.analyzer.export_csv(
            aggregate,
            output_file,
        )

        self.assertTrue(result_path.is_file())
        self.assertEqual(len(pd.read_csv(result_path)), 3)


if __name__ == "__main__":
    unittest.main()
