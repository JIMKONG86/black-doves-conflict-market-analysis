import unittest

from datetime import date, datetime, timezone

from src.models.weekly_conflict_aggregate import (
    AggregateDisorderType,
    AggregateEventType,
    WeeklyConflictAggregate,
)
from src.services.weekly_conflict_feature_builder import (
    WeeklyConflictFeatureBuilder,
)


class MemoryAggregateRepository:
    def __init__(self, items):
        self.items = items

    def load_all(self):
        return list(self.items)


class TestWeeklyConflictFeatureBuilder(
    unittest.TestCase
):
    def _aggregate(self, **overrides):
        arguments = {
            "source_snapshot_date": date(2026, 8, 22),
            "week_end_date": date(2026, 8, 15),
            "region": "Middle East",
            "country_name": "Iran",
            "country_code": "IR",
            "admin1": "Tehran",
            "event_type": (
                AggregateEventType
                .EXPLOSIONS_REMOTE_VIOLENCE
            ),
            "sub_event_type": "Air/drone strike",
            "event_count": 3,
            "fatality_count": 1,
            "population_exposure": 1000,
            "disorder_type": (
                AggregateDisorderType
                .POLITICAL_VIOLENCE
            ),
            "geographic_id": 1,
            "centroid_latitude": 35.7,
            "centroid_longitude": 51.4,
            "reviewed_by": "Markus",
            "source_url": "https://acleddata.com/",
            "created_at": datetime(
                2026,
                9,
                4,
                8,
                tzinfo=timezone.utc,
            ),
        }
        arguments.update(overrides)
        return WeeklyConflictAggregate(**arguments)

    def _iran_week(self):
        return [
            self._aggregate(),
            self._aggregate(
                admin1="Isfahan",
                sub_event_type=(
                    "Shelling/artillery/missile attack"
                ),
                event_count=2,
                fatality_count=2,
                geographic_id=2,
            ),
            self._aggregate(
                event_type=(
                    AggregateEventType
                    .VIOLENCE_AGAINST_CIVILIANS
                ),
                sub_event_type="Attack",
                event_count=4,
                fatality_count=1,
                geographic_id=2,
            ),
            self._aggregate(
                event_type=AggregateEventType.PROTESTS,
                sub_event_type="Peaceful protest",
                event_count=5,
                fatality_count=0,
                disorder_type=(
                    AggregateDisorderType.DEMONSTRATIONS
                ),
            ),
        ]

    def test_builds_exact_country_week_totals(self):
        features = (
            WeeklyConflictFeatureBuilder(
                MemoryAggregateRepository(
                    self._iran_week()
                )
            ).build()
        )

        self.assertEqual(len(features), 1)
        feature = features[0]
        self.assertEqual(feature.source_row_count, 4)
        self.assertEqual(
            feature.administrative_area_count,
            2,
        )
        self.assertEqual(feature.total_events, 14)
        self.assertEqual(feature.total_fatalities, 4)
        self.assertEqual(
            feature.political_violence_events,
            9,
        )
        self.assertEqual(feature.strike_events, 5)
        self.assertEqual(feature.strike_fatalities, 3)
        self.assertEqual(
            feature.air_drone_strike_events,
            3,
        )
        self.assertEqual(
            feature.shelling_artillery_missile_events,
            2,
        )
        self.assertEqual(
            feature.violence_against_civilians_events,
            4,
        )
        self.assertEqual(feature.protest_events, 5)

    def test_keeps_source_snapshots_separate(self):
        aggregates = self._iran_week()
        aggregates.append(
            self._aggregate(
                source_snapshot_date=date(2026, 8, 29),
                week_end_date=date(2026, 8, 15),
                event_count=7,
            )
        )

        features = (
            WeeklyConflictFeatureBuilder(
                MemoryAggregateRepository(aggregates)
            ).build()
        )

        self.assertEqual(len(features), 2)
        self.assertEqual(
            [feature.total_events for feature in features],
            [14, 7],
        )

    def test_filters_snapshot_and_country_code(self):
        aggregates = self._iran_week()
        aggregates.append(
            self._aggregate(
                country_name="Israel",
                country_code="IL",
                admin1="Tel Aviv",
                geographic_id=10,
            )
        )

        features = (
            WeeklyConflictFeatureBuilder(
                MemoryAggregateRepository(aggregates)
            ).build(
                source_snapshot_date="2026-08-22",
                countries=("IL",),
            )
        )

        self.assertEqual(len(features), 1)
        self.assertEqual(features[0].country_name, "Israel")

    def test_rejects_missing_country_code(self):
        with self.assertRaisesRegex(
            ValueError,
            "country_code is required",
        ):
            WeeklyConflictFeatureBuilder.build_from_aggregates(
                (self._aggregate(country_code=None),)
            )

    def test_rejects_inconsistent_provenance(self):
        aggregates = self._iran_week()
        aggregates.append(
            self._aggregate(
                sub_event_type="Armed clash",
                source_url="https://example.com/",
            )
        )

        with self.assertRaisesRegex(
            ValueError,
            "one source_url",
        ):
            (
                WeeklyConflictFeatureBuilder
                .build_from_aggregates(aggregates)
            )


if __name__ == "__main__":
    unittest.main()
