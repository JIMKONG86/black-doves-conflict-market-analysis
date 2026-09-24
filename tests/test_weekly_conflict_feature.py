import unittest

from datetime import date, datetime, timezone

from src.models.weekly_conflict_feature import (
    WeeklyConflictFeature,
)


class TestWeeklyConflictFeature(unittest.TestCase):
    def _create_feature(self, **overrides):
        arguments = {
            "source_snapshot_date": date(2026, 8, 22),
            "week_end_date": date(2026, 8, 15),
            "country_name": " Iran ",
            "country_code": "ir",
            "source_row_count": 4,
            "administrative_area_count": 2,
            "total_events": 14,
            "total_fatalities": 4,
            "political_violence_events": 9,
            "political_violence_fatalities": 4,
            "strike_events": 5,
            "strike_fatalities": 3,
            "air_drone_strike_events": 3,
            "air_drone_strike_fatalities": 1,
            "shelling_artillery_missile_events": 2,
            "shelling_artillery_missile_fatalities": 2,
            "violence_against_civilians_events": 4,
            "violence_against_civilians_fatalities": 1,
            "protest_events": 5,
            "riot_events": 0,
            "strategic_development_events": 0,
            "reviewed_by": " Markus ",
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
        return WeeklyConflictFeature(**arguments)

    def test_normalizes_values_and_flags_strike(self):
        feature = self._create_feature()

        self.assertEqual(feature.country_name, "Iran")
        self.assertEqual(feature.country_code, "IR")
        self.assertEqual(feature.reviewed_by, "Markus")
        self.assertTrue(feature.has_strike_activity)
        self.assertEqual(len(feature.feature_id), 64)

    def test_identifier_is_independent_of_review_metadata(self):
        first = self._create_feature()
        second = self._create_feature(
            reviewed_by="Second reviewer",
            created_at=datetime(
                2026,
                9,
                5,
                8,
                tzinfo=timezone.utc,
            ),
        )

        self.assertEqual(first.feature_id, second.feature_id)

    def test_identifier_changes_with_analytical_values(self):
        first = self._create_feature()
        second = self._create_feature(
            total_events=15,
        )

        self.assertNotEqual(first.feature_id, second.feature_id)

    def test_rejects_inconsistent_strike_sum(self):
        with self.assertRaisesRegex(
            ValueError,
            "strike_events must equal",
        ):
            self._create_feature(strike_events=6)

    def test_rejects_subset_above_total(self):
        with self.assertRaisesRegex(
            ValueError,
            "must not exceed",
        ):
            self._create_feature(
                violence_against_civilians_events=15,
            )

    def test_rejects_invalid_source_url(self):
        with self.assertRaisesRegex(
            ValueError,
            "HTTP or HTTPS",
        ):
            self._create_feature(source_url="acleddata.com")


if __name__ == "__main__":
    unittest.main()
