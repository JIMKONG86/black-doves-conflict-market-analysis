import csv
import tempfile
import unittest

from datetime import date, datetime, timezone
from pathlib import Path

from src.data_access.weekly_conflict_feature_exporter import (
    WeeklyConflictFeatureExporter,
)
from src.models.weekly_conflict_feature import (
    WeeklyConflictFeature,
)


class TestWeeklyConflictFeatureExporter(
    unittest.TestCase
):
    def setUp(self):
        self.temporary_directory = (
            tempfile.TemporaryDirectory()
        )

    def tearDown(self):
        self.temporary_directory.cleanup()

    @staticmethod
    def _feature():
        return WeeklyConflictFeature(
            source_snapshot_date=date(2026, 8, 22),
            week_end_date=date(2026, 8, 15),
            country_name="Iran",
            country_code="IR",
            source_row_count=2,
            administrative_area_count=1,
            total_events=5,
            total_fatalities=3,
            political_violence_events=5,
            political_violence_fatalities=3,
            strike_events=5,
            strike_fatalities=3,
            air_drone_strike_events=3,
            air_drone_strike_fatalities=1,
            shelling_artillery_missile_events=2,
            shelling_artillery_missile_fatalities=2,
            violence_against_civilians_events=0,
            violence_against_civilians_fatalities=0,
            protest_events=0,
            riot_events=0,
            strategic_development_events=0,
            reviewed_by="Markus",
            source_url="https://acleddata.com/",
            created_at=datetime(
                2026,
                9,
                4,
                8,
                tzinfo=timezone.utc,
            ),
        )

    def test_exports_analysis_ready_csv(self):
        file_path = Path(
            self.temporary_directory.name
        ) / "weekly_features.csv"

        result = (
            WeeklyConflictFeatureExporter().export_csv(
                (self._feature(),),
                file_path,
            )
        )

        self.assertEqual(result, file_path)
        with file_path.open(
            "r",
            encoding="utf-8",
            newline="",
        ) as csv_file:
            rows = list(csv.DictReader(csv_file))

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["country_code"], "IR")
        self.assertEqual(rows[0]["strike_events"], "5")
        self.assertEqual(
            rows[0]["week_end_date"],
            "2026-08-15",
        )
        self.assertEqual(
            len(rows[0]["feature_id"]),
            64,
        )

    def test_writes_header_for_empty_export(self):
        file_path = Path(
            self.temporary_directory.name
        ) / "empty.csv"

        WeeklyConflictFeatureExporter().export_csv(
            (),
            file_path,
        )

        self.assertEqual(
            file_path.read_text(
                encoding="utf-8"
            ).count("\n"),
            1,
        )

    def test_rejects_non_csv_destination(self):
        file_path = Path(
            self.temporary_directory.name
        ) / "features.xlsx"

        with self.assertRaisesRegex(
            ValueError,
            "must use .csv",
        ):
            WeeklyConflictFeatureExporter().export_csv(
                (self._feature(),),
                file_path,
            )


if __name__ == "__main__":
    unittest.main()
