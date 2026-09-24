import io
import tempfile
import unittest

from contextlib import redirect_stdout
from pathlib import Path

from src.data_access.weekly_conflict_aggregate_repository import (
    WeeklyConflictAggregateRepository,
)
from src.import_acled_weekly_aggregates import main


CSV_HEADER = (
    "WEEK,REGION,COUNTRY,ADMIN1,EVENT_TYPE,"
    "SUB_EVENT_TYPE,EVENTS,FATALITIES,"
    "POPULATION_EXPOSURE,DISORDER_TYPE,ID,"
    "CENTROID_LATITUDE,CENTROID_LONGITUDE\n"
)


class TestImportAcledWeeklyAggregates(
    unittest.TestCase
):
    def setUp(self):
        self.temporary_directory = (
            tempfile.TemporaryDirectory()
        )
        self.base_path = Path(
            self.temporary_directory.name
        )
        self.csv_path = self.base_path / "weekly.csv"
        self.repository_path = (
            self.base_path / "validated"
        )

    def tearDown(self):
        self.temporary_directory.cleanup()

    def _arguments(self):
        return [
            str(self.csv_path),
            "--reviewed-by",
            "Markus",
            "--source-url",
            "https://acleddata.com/",
            "--snapshot-date",
            "2026-08-22",
            "--country",
            "Iran",
            "--aggregate-directory",
            str(self.repository_path),
            "--strict",
        ]

    def test_imports_selected_country(self):
        self.csv_path.write_text(
            CSV_HEADER
            + (
                "2026-08-22,Middle East,Iran,"
                "Tehran,Explosions/Remote violence,"
                "Air/drone strike,12,3,2400,"
                "Political violence,118,35.7,51.4\n"
            )
            + (
                "2026-08-22,Middle East,Israel,"
                "Tel Aviv,Protests,Peaceful protest,"
                "2,0,100,Demonstrations,119,32.1,"
                "34.8\n"
            ),
            encoding="utf-8",
        )
        output = io.StringIO()

        with redirect_stdout(output):
            exit_code = main(self._arguments())

        self.assertEqual(exit_code, 0)
        self.assertIn(
            "Saved aggregates: 1",
            output.getvalue(),
        )
        repository = (
            WeeklyConflictAggregateRepository(
                self.repository_path
            )
        )
        loaded = repository.load_all()
        self.assertEqual(len(loaded), 1)
        self.assertEqual(
            loaded[0].country_name,
            "Iran",
        )

    def test_strict_mode_returns_one_for_bad_row(
        self,
    ):
        self.csv_path.write_text(
            CSV_HEADER
            + (
                "2026-08-22,Middle East,Iran,"
                "Tehran,Unsupported event,"
                "Air/drone strike,12,3,2400,"
                "Political violence,118,35.7,51.4\n"
            ),
            encoding="utf-8",
        )
        output = io.StringIO()

        with redirect_stdout(output):
            exit_code = main(self._arguments())

        self.assertEqual(exit_code, 1)
        self.assertIn(
            "Failed rows: 1",
            output.getvalue(),
        )


if __name__ == "__main__":
    unittest.main()
