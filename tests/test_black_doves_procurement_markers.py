import tempfile
import unittest

from pathlib import Path

import pandas as pd

from src.black_doves_visualization import (
    _load_procurement_markers,
)


class TestBlackDovesProcurementMarkers(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary_directory.name)
        self.input_file = self.directory / "summary.csv"
        self.market_data = pd.DataFrame(
            {
                "week_end_date": pd.to_datetime(
                    ["2025-01-11", "2025-01-18"]
                ),
                "company_cumulative_return": [0.10, 0.20],
            }
        )

    def tearDown(self):
        self.temporary_directory.cleanup()

    @staticmethod
    def _row():
        return {
            "event_id": "event-a",
            "announcement_date": "2025-01-15",
            "effective_market_date": "2025-01-15",
            "buyer_name": "Italian Army",
            "title": "Italy orders Skynex",
            "systems": "Skynex",
            "event_day_abnormal_return": 0.01,
        }

    def test_aligns_marker_to_nearest_market_week(self):
        pd.DataFrame([self._row()]).to_csv(
            self.input_file,
            index=False,
        )

        result = _load_procurement_markers(
            self.input_file,
            self.market_data,
        )

        self.assertEqual(result.loc[0, "marker_y"], 0.20)
        self.assertEqual(
            result.loc[0, "announcement_label"],
            "15 Jan 2025",
        )

    def test_rejects_duplicate_events(self):
        row = self._row()
        pd.DataFrame([row, row]).to_csv(
            self.input_file,
            index=False,
        )

        with self.assertRaisesRegex(ValueError, "duplicate events"):
            _load_procurement_markers(
                self.input_file,
                self.market_data,
            )

    def test_rejects_missing_required_column(self):
        row = self._row()
        row.pop("systems")
        pd.DataFrame([row]).to_csv(
            self.input_file,
            index=False,
        )

        with self.assertRaisesRegex(ValueError, "systems"):
            _load_procurement_markers(
                self.input_file,
                self.market_data,
            )


if __name__ == "__main__":
    unittest.main()
