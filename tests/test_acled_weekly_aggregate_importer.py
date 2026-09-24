import tempfile
import unittest

from pathlib import Path

from src.data_access.acled_weekly_aggregate_importer import (
    AcledWeeklyAggregateImporter,
)
from src.models.weekly_conflict_aggregate import (
    AggregateDisorderType,
    AggregateEventType,
)


CSV_HEADER = (
    "WEEK,REGION,COUNTRY,ADMIN1,EVENT_TYPE,"
    "SUB_EVENT_TYPE,EVENTS,FATALITIES,"
    "POPULATION_EXPOSURE,DISORDER_TYPE,ID,"
    "CENTROID_LATITUDE,CENTROID_LONGITUDE\n"
)


class MemoryAggregateRepository:
    def __init__(self):
        self.items = []

    def contains(self, aggregate_id):
        return any(
            item.aggregate_id == aggregate_id
            for item in self.items
        )

    def save(self, aggregate):
        if self.contains(aggregate.aggregate_id):
            raise ValueError(
                "Weekly aggregate already exists"
            )

        self.items.append(aggregate)


class TestAcledWeeklyAggregateImporter(
    unittest.TestCase
):
    def setUp(self):
        self.temporary_directory = (
            tempfile.TemporaryDirectory()
        )
        self.repository = (
            MemoryAggregateRepository()
        )
        self.importer = (
            AcledWeeklyAggregateImporter(
                self.repository
            )
        )

    def tearDown(self):
        self.temporary_directory.cleanup()

    def _write_csv(self, content):
        file_path = Path(
            self.temporary_directory.name
        ) / "weekly.csv"
        file_path.write_text(
            content,
            encoding="utf-8",
        )
        return file_path

    def _import(self, file_path, **overrides):
        arguments = {
            "file_path": file_path,
            "reviewed_by": "Markus",
            "source_url": (
                "https://acleddata.com/"
            ),
            "source_snapshot_date": (
                "2026-08-22"
            ),
        }
        arguments.update(overrides)
        return self.importer.import_csv(
            **arguments
        )

    def test_imports_selected_countries(self):
        file_path = self._write_csv(
            CSV_HEADER
            + (
                "2026-08-22,Middle East,Iran,"
                "Tehran,Explosions/Remote violence,"
                "Air/drone strike,12,3,2400,"
                "Political violence,118,35.7,51.4\n"
            )
            + (
                "2026-08-22,Middle East,Israel,"
                "Tel Aviv,Explosions/Remote violence,"
                "Shelling/artillery/missile attack,"
                "4,0,1200,Political violence,119,"
                "32.1,34.8\n"
            )
            + (
                "2026-08-22,Middle East,Bahrain,"
                "Capital,Protests,Peaceful protest,"
                "2,0,900,Demonstrations,120,26.1,"
                "50.5\n"
            )
        )

        summary = self._import(
            file_path,
            countries=("Iran", "Israel"),
        )

        self.assertEqual(summary.total_rows, 3)
        self.assertEqual(summary.selected_rows, 2)
        self.assertEqual(summary.saved_aggregates, 2)
        self.assertEqual(summary.skipped_countries, 1)
        self.assertEqual(summary.failed_rows, 0)

        iran = self.repository.items[0]
        israel = self.repository.items[1]

        self.assertEqual(iran.country_code, "IR")
        self.assertEqual(israel.country_code, "IL")
        self.assertEqual(
            iran.event_type,
            (
                AggregateEventType
                .EXPLOSIONS_REMOTE_VIOLENCE
            ),
        )
        self.assertEqual(
            iran.disorder_type,
            AggregateDisorderType.POLITICAL_VIOLENCE,
        )
        self.assertTrue(iran.is_strike)

    def test_repeated_import_is_idempotent(self):
        file_path = self._write_csv(
            CSV_HEADER
            + (
                "2026-08-22,Middle East,Iran,"
                "Tehran,Explosions/Remote violence,"
                "Air/drone strike,12,3,2400,"
                "Political violence,118,35.7,51.4\n"
            )
        )

        first = self._import(file_path)
        second = self._import(file_path)

        self.assertEqual(first.saved_aggregates, 1)
        self.assertEqual(second.saved_aggregates, 0)
        self.assertEqual(
            second.duplicate_aggregates,
            1,
        )
        self.assertEqual(len(self.repository.items), 1)

    def test_strike_only_skips_other_subtypes(self):
        file_path = self._write_csv(
            CSV_HEADER
            + (
                "2026-08-22,Middle East,Iran,"
                "Tehran,Protests,Peaceful protest,"
                "2,0,900,Demonstrations,118,35.7,"
                "51.4\n"
            )
            + (
                "2026-08-22,Middle East,Iran,"
                "Tehran,Explosions/Remote violence,"
                "Air/drone strike,12,3,2400,"
                "Political violence,118,35.7,51.4\n"
            )
        )

        summary = self._import(
            file_path,
            strike_only=True,
        )

        self.assertEqual(summary.total_rows, 2)
        self.assertEqual(summary.selected_rows, 1)
        self.assertEqual(
            summary.skipped_non_strikes,
            1,
        )
        self.assertEqual(summary.saved_aggregates, 1)

    def test_reads_german_csv_format(self):
        file_path = self._write_csv(
            (
                "WEEK;REGION;COUNTRY;ADMIN1;EVENT_TYPE;"
                "SUB_EVENT_TYPE;EVENTS;FATALITIES;"
                "POPULATION_EXPOSURE;DISORDER_TYPE;ID;"
                "CENTROID_LATITUDE;CENTROID_LONGITUDE\n"
                "22.08.2026;Middle East;Iran;Tehran;"
                "Explosions/Remote violence;Air/drone "
                "strike;12;3;2400;Political violence;"
                "118;35,7;51,4\n"
            )
        )

        summary = self._import(file_path)

        self.assertEqual(summary.saved_aggregates, 1)
        aggregate = self.repository.items[0]
        self.assertEqual(
            aggregate.week_end_date.isoformat(),
            "2026-08-22",
        )
        self.assertEqual(
            aggregate.centroid_latitude,
            35.7,
        )

    def test_reads_us_excel_date_format(self):
        file_path = self._write_csv(
            CSV_HEADER
            + (
                "08/22/2026,Middle East,Iran,"
                "Tehran,Explosions/Remote violence,"
                "Air/drone strike,12,3,2400,"
                "Political violence,118,35.7,51.4\n"
            )
        )

        summary = self._import(file_path)

        self.assertEqual(summary.saved_aggregates, 1)
        self.assertEqual(
            (
                self.repository.items[0]
                .week_end_date
                .isoformat()
            ),
            "2026-08-22",
        )

    def test_reports_invalid_source_row(self):
        file_path = self._write_csv(
            CSV_HEADER
            + (
                "2026-08-22,Middle East,Iran,"
                "Tehran,Unknown category,"
                "Air/drone strike,12,3,2400,"
                "Political violence,118,35.7,51.4\n"
            )
        )

        summary = self._import(file_path)

        self.assertEqual(summary.saved_aggregates, 0)
        self.assertEqual(summary.failed_rows, 1)
        self.assertIn(
            "Unsupported EVENT_TYPE",
            summary.issues[0].message,
        )

    def test_rejects_missing_required_header(self):
        file_path = self._write_csv(
            "WEEK,COUNTRY,EVENTS\n"
        )

        with self.assertRaisesRegex(
            ValueError,
            "SUB_EVENT_TYPE",
        ):
            self._import(file_path)

    def test_rejects_invalid_source_url(self):
        file_path = self._write_csv(
            CSV_HEADER
        )

        with self.assertRaisesRegex(
            ValueError,
            "valid HTTP or HTTPS URL",
        ):
            self._import(
                file_path,
                source_url="acleddata.com",
            )


if __name__ == "__main__":
    unittest.main()
