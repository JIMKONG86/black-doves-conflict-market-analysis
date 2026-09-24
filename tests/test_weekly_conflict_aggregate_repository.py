import json
import tempfile
import unittest

from datetime import date, datetime, timezone
from pathlib import Path

from src.data_access.weekly_conflict_aggregate_repository import (
    WeeklyConflictAggregateRepository,
)
from src.models.weekly_conflict_aggregate import (
    AggregateDisorderType,
    AggregateEventType,
    WeeklyConflictAggregate,
)


class TestWeeklyConflictAggregateRepository(
    unittest.TestCase
):
    def setUp(self):
        self.temporary_directory = (
            tempfile.TemporaryDirectory()
        )
        self.directory = Path(
            self.temporary_directory.name
        ) / "aggregates"
        self.repository = (
            WeeklyConflictAggregateRepository(
                self.directory
            )
        )

    def tearDown(self):
        self.temporary_directory.cleanup()

    @staticmethod
    def _aggregate(
        country_name="Iran",
        country_code="IR",
        admin1="Tehran",
        geographic_id=118,
    ):
        return WeeklyConflictAggregate(
            source_snapshot_date=date(
                2026,
                8,
                22,
            ),
            week_end_date=date(
                2026,
                8,
                22,
            ),
            region="Middle East",
            country_name=country_name,
            country_code=country_code,
            admin1=admin1,
            event_type=(
                AggregateEventType
                .EXPLOSIONS_REMOTE_VIOLENCE
            ),
            sub_event_type="Air/drone strike",
            event_count=12,
            fatality_count=3,
            population_exposure=2400,
            disorder_type=(
                AggregateDisorderType
                .POLITICAL_VIOLENCE
            ),
            geographic_id=geographic_id,
            centroid_latitude=35.7,
            centroid_longitude=51.4,
            reviewed_by="Markus",
            source_url="https://acleddata.com/",
            created_at=datetime(
                2026,
                9,
                3,
                tzinfo=timezone.utc,
            ),
        )

    def test_save_many_groups_and_loads_aggregates(
        self,
    ):
        iran_one = self._aggregate()
        iran_two = self._aggregate(
            admin1="Fars",
            geographic_id=119,
        )
        israel = self._aggregate(
            country_name="Israel",
            country_code="IL",
            admin1="Tel Aviv",
            geographic_id=120,
        )

        paths = self.repository.save_many(
            (iran_one, iran_two, israel)
        )

        self.assertEqual(len(paths), 2)
        self.assertEqual(
            {path.name for path in paths},
            {
                "IR_2026-08-22.json",
                "IL_2026-08-22.json",
            },
        )
        loaded = self.repository.load_all()
        self.assertEqual(len(loaded), 3)
        self.assertEqual(
            {item.aggregate_id for item in loaded},
            {
                iran_one.aggregate_id,
                iran_two.aggregate_id,
                israel.aggregate_id,
            },
        )

    def test_save_contains_and_rejects_duplicate(
        self,
    ):
        aggregate = self._aggregate()

        path = self.repository.save(aggregate)

        self.assertEqual(
            path.name,
            "IR_2026-08-22.json",
        )
        self.assertTrue(
            self.repository.contains(
                aggregate.aggregate_id.upper()
            )
        )

        with self.assertRaisesRegex(
            ValueError,
            "already exists",
        ):
            self.repository.save(aggregate)

    def test_empty_repository_and_empty_batch(self):
        self.assertEqual(
            self.repository.load_all(),
            [],
        )
        self.assertFalse(
            self.repository.contains("a" * 64)
        )
        self.assertEqual(
            self.repository.save_many(()),
            (),
        )

    def test_rejects_invalid_batch(self):
        aggregate = self._aggregate()

        with self.assertRaisesRegex(
            TypeError,
            "WeeklyConflictAggregate",
        ):
            self.repository.save_many(
                (aggregate, object())
            )

        with self.assertRaisesRegex(
            ValueError,
            "batch contains duplicates",
        ):
            self.repository.save_many(
                (aggregate, aggregate)
            )

    def test_detects_tampered_identifier(self):
        aggregate = self._aggregate()
        path = self.repository.save(aggregate)
        payload = json.loads(
            path.read_text(encoding="utf-8")
        )
        payload["aggregates"][0][
            "aggregate_id"
        ] = "f" * 64
        path.write_text(
            json.dumps(payload),
            encoding="utf-8",
        )

        with self.assertRaisesRegex(
            ValueError,
            "aggregate_id is invalid",
        ):
            self.repository.load_all()


if __name__ == "__main__":
    unittest.main()
