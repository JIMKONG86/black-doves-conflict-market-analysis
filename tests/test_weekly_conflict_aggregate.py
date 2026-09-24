import unittest

from datetime import date, datetime, timezone

from src.models.weekly_conflict_aggregate import (
    AggregateDisorderType,
    AggregateEventType,
    WeeklyConflictAggregate,
)


class TestWeeklyConflictAggregate(unittest.TestCase):
    def _create_aggregate(self, **overrides):
        arguments = {
            "source_snapshot_date": date(
                2026,
                8,
                22,
            ),
            "week_end_date": date(
                2026,
                8,
                22,
            ),
            "region": " Middle East ",
            "country_name": " Iran ",
            "country_code": "ir",
            "admin1": " Tehran ",
            "event_type": (
                AggregateEventType
                .EXPLOSIONS_REMOTE_VIOLENCE
            ),
            "sub_event_type": (
                " Air/drone strike "
            ),
            "event_count": 12,
            "fatality_count": 3,
            "population_exposure": 2400,
            "disorder_type": (
                AggregateDisorderType
                .POLITICAL_VIOLENCE
            ),
            "geographic_id": 118,
            "centroid_latitude": 35.7,
            "centroid_longitude": 51.4,
            "reviewed_by": " Markus ",
            "source_url": (
                "https://acleddata.com/"
            ),
            "created_at": datetime(
                2026,
                9,
                3,
                12,
                tzinfo=timezone.utc,
            ),
        }
        arguments.update(overrides)
        return WeeklyConflictAggregate(
            **arguments
        )

    def test_normalizes_values_and_flags_strike(self):
        aggregate = self._create_aggregate()

        self.assertEqual(
            aggregate.country_name,
            "Iran",
        )
        self.assertEqual(
            aggregate.country_code,
            "IR",
        )
        self.assertEqual(
            aggregate.admin1,
            "Tehran",
        )
        self.assertTrue(aggregate.is_strike)
        self.assertTrue(
            aggregate.is_political_violence
        )
        self.assertEqual(
            len(aggregate.aggregate_id),
            64,
        )

    def test_identifier_is_independent_of_import_time(self):
        first = self._create_aggregate()
        second = self._create_aggregate(
            created_at=datetime(
                2026,
                9,
                4,
                12,
                tzinfo=timezone.utc,
            )
        )

        self.assertEqual(
            first.aggregate_id,
            second.aggregate_id,
        )

    def test_identifier_changes_with_source_values(self):
        first = self._create_aggregate()
        second = self._create_aggregate(
            event_count=13
        )

        self.assertNotEqual(
            first.aggregate_id,
            second.aggregate_id,
        )

    def test_rejects_week_after_snapshot(self):
        with self.assertRaisesRegex(
            ValueError,
            "must not be after",
        ):
            self._create_aggregate(
                week_end_date=date(
                    2026,
                    8,
                    29,
                )
            )

    def test_rejects_negative_event_count(self):
        with self.assertRaisesRegex(
            ValueError,
            "must not be negative",
        ):
            self._create_aggregate(
                event_count=-1
            )

    def test_rejects_invalid_coordinate(self):
        with self.assertRaisesRegex(
            ValueError,
            "between -90 and 90",
        ):
            self._create_aggregate(
                centroid_latitude=91
            )

    def test_rejects_naive_created_at(self):
        with self.assertRaisesRegex(
            ValueError,
            "timezone-aware",
        ):
            self._create_aggregate(
                created_at=datetime(
                    2026,
                    9,
                    3,
                    12,
                )
            )


if __name__ == "__main__":
    unittest.main()
