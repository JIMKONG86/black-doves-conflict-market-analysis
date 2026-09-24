import tempfile
import unittest

from pathlib import Path

import pandas as pd

from src.services.weekly_market_conflict_builder import (
    WeeklyMarketConflictBuilder,
)


class TestWeeklyMarketConflictBuilder(
    unittest.TestCase
):
    def setUp(self):
        self.temporary_directory = (
            tempfile.TemporaryDirectory()
        )
        self.directory = Path(
            self.temporary_directory.name
        )
        self.conflict_file = (
            self.directory / "conflict.csv"
        )
        self.market_file = self.directory / "market.csv"
        self.builder = WeeklyMarketConflictBuilder()

    def tearDown(self):
        self.temporary_directory.cleanup()

    @staticmethod
    def _conflict_row(**overrides):
        row = {
            "feature_id": "a" * 64,
            "source_snapshot_date": "2026-08-22",
            "week_end_date": "2025-01-11",
            "country_name": "Iran",
            "country_code": "IR",
            "source_row_count": 3,
            "administrative_area_count": 2,
            "total_events": 10,
            "total_fatalities": 4,
            "strike_events": 6,
            "strike_fatalities": 3,
            "air_drone_strike_events": 4,
            "air_drone_strike_fatalities": 2,
            "shelling_artillery_missile_events": 2,
            "shelling_artillery_missile_fatalities": 1,
            "violence_against_civilians_events": 1,
            "violence_against_civilians_fatalities": 1,
            "protest_events": 2,
            "riot_events": 1,
            "strategic_development_events": 0,
            "reviewed_by": "Markus",
            "source_url": "https://acleddata.com/",
            "created_at": "2026-09-04T08:00:00+00:00",
        }
        row.update(overrides)
        return row

    @staticmethod
    def _market_rows():
        return [
            {
                "Date": "2025-01-09",
                "company_price": 110.0,
                "benchmark_price": 102.0,
                "company_return": 0.10,
                "benchmark_return": 0.02,
                "abnormal_return": 0.08,
                "company_cumulative_return": 0.10,
                "benchmark_cumulative_return": 0.02,
                "cumulative_abnormal_return": 0.08,
            },
            {
                "Date": "2025-01-10",
                "company_price": 104.5,
                "benchmark_price": 103.02,
                "company_return": -0.05,
                "benchmark_return": 0.01,
                "abnormal_return": -0.06,
                "company_cumulative_return": 0.045,
                "benchmark_cumulative_return": 0.0302,
                "cumulative_abnormal_return": 0.02,
            },
        ]

    def _write_files(
        self,
        conflict_rows=None,
        market_rows=None,
    ):
        if conflict_rows is None:
            conflict_rows = [self._conflict_row()]

        if market_rows is None:
            market_rows = self._market_rows()

        pd.DataFrame(conflict_rows).to_csv(
            self.conflict_file,
            index=False,
        )
        pd.DataFrame(market_rows).to_csv(
            self.market_file,
            index=False,
        )

    def test_joins_country_weeks_and_compounds_returns(
        self,
    ):
        conflict_rows = [
            self._conflict_row(),
            self._conflict_row(
                feature_id="b" * 64,
                country_name="Israel",
                country_code="IL",
            ),
            self._conflict_row(
                feature_id="c" * 64,
                week_end_date="2024-12-28",
            ),
        ]
        self._write_files(conflict_rows=conflict_rows)

        data, summary = self.builder.build(
            self.conflict_file,
            self.market_file,
        )

        self.assertEqual(len(data), 2)
        self.assertEqual(summary.conflict_rows, 3)
        self.assertEqual(summary.joined_rows, 2)
        self.assertEqual(summary.joined_weeks, 1)
        self.assertEqual(
            summary.unmatched_conflict_rows,
            1,
        )
        self.assertEqual(
            data.loc[0, "market_date"].date().isoformat(),
            "2025-01-10",
        )
        self.assertAlmostEqual(
            data.loc[0, "company_weekly_return"],
            0.045,
        )
        self.assertAlmostEqual(
            data.loc[0, "benchmark_weekly_return"],
            0.0302,
        )
        self.assertAlmostEqual(
            data.loc[0, "weekly_abnormal_return"],
            0.02,
        )
        self.assertEqual(
            data.loc[0, "market_observation_count"],
            2,
        )
        self.assertEqual(
            len(data.loc[0, "market_conflict_id"]),
            64,
        )

    def test_maps_holiday_week_to_last_trading_day(self):
        self._write_files(
            market_rows=[self._market_rows()[0]]
        )

        data, summary = self.builder.build(
            self.conflict_file,
            self.market_file,
        )

        self.assertEqual(
            data.loc[0, "market_date"].date().isoformat(),
            "2025-01-09",
        )
        self.assertEqual(summary.joined_weeks, 1)

    def test_filters_snapshot_and_country(self):
        self._write_files(
            conflict_rows=[
                self._conflict_row(),
                self._conflict_row(
                    feature_id="b" * 64,
                    country_name="Israel",
                    country_code="IL",
                ),
            ]
        )

        data, summary = self.builder.build(
            self.conflict_file,
            self.market_file,
            source_snapshot_date="2026-08-22",
            countries=("IL",),
        )

        self.assertEqual(summary.conflict_rows, 1)
        self.assertEqual(data.loc[0, "country_code"], "IL")

    def test_rejects_duplicate_market_dates(self):
        market_rows = self._market_rows()
        market_rows.append(dict(market_rows[0]))
        self._write_files(market_rows=market_rows)

        with self.assertRaisesRegex(
            ValueError,
            "duplicate dates",
        ):
            self.builder.build(
                self.conflict_file,
                self.market_file,
            )

    def test_rejects_duplicate_conflict_weeks(self):
        self._write_files(
            conflict_rows=[
                self._conflict_row(),
                self._conflict_row(feature_id="b" * 64),
            ]
        )

        with self.assertRaisesRegex(
            ValueError,
            "duplicate snapshot-country-week",
        ):
            self.builder.build(
                self.conflict_file,
                self.market_file,
            )

    def test_rejects_missing_market_column(self):
        market_rows = self._market_rows()

        for row in market_rows:
            row.pop("abnormal_return")

        self._write_files(market_rows=market_rows)

        with self.assertRaisesRegex(
            ValueError,
            "abnormal_return",
        ):
            self.builder.build(
                self.conflict_file,
                self.market_file,
            )

    def test_exports_dates_as_iso_text(self):
        self._write_files()
        data, summary = self.builder.build(
            self.conflict_file,
            self.market_file,
        )
        output_file = self.directory / "analysis.csv"

        result = self.builder.export_csv(
            data,
            output_file,
        )
        exported = pd.read_csv(result)

        self.assertEqual(
            exported.loc[0, "week_end_date"],
            "2025-01-11",
        )
        self.assertEqual(
            exported.loc[0, "market_date"],
            "2025-01-10",
        )


if __name__ == "__main__":
    unittest.main()
