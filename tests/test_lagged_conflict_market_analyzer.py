import tempfile
import unittest

from pathlib import Path

import pandas as pd

from src.services.lagged_conflict_market_analyzer import (
    LaggedConflictMarketAnalyzer,
)


class TestLaggedConflictMarketAnalyzer(
    unittest.TestCase
):
    def setUp(self):
        self.temporary_directory = (
            tempfile.TemporaryDirectory()
        )
        self.directory = Path(
            self.temporary_directory.name
        )
        self.input_file = self.directory / "analysis.csv"
        self.analyzer = LaggedConflictMarketAnalyzer()

    def tearDown(self):
        self.temporary_directory.cleanup()

    @staticmethod
    def _rows():
        weeks = pd.date_range(
            "2025-01-04",
            periods=6,
            freq="7D",
        )
        responses = [9.0, 0.0, 2.0, 4.0, 6.0, 8.0]
        rows = []

        for index, week in enumerate(weeks):
            for country_name, country_code in (
                ("Iran", "IR"),
                ("Israel", "IL"),
            ):
                rows.append(
                    {
                        "source_snapshot_date": (
                            "2026-08-22"
                        ),
                        "week_end_date": (
                            week.strftime("%Y-%m-%d")
                        ),
                        "country_name": country_name,
                        "country_code": country_code,
                        "company_ticker": "RHM.DE",
                        "benchmark_ticker": "^GDAXI",
                        "strike_events": index,
                        "strike_fatalities": index * 2,
                        "weekly_abnormal_return": (
                            responses[index]
                        ),
                    }
                )

        return rows

    def _write_rows(self, rows=None):
        if rows is None:
            rows = self._rows()

        pd.DataFrame(rows).to_csv(
            self.input_file,
            index=False,
        )

    def test_creates_combined_and_country_scopes(self):
        self._write_rows()

        results, summary = self.analyzer.analyze(
            self.input_file,
            metrics=("strike_events",),
            lags=(0, 1),
        )

        self.assertEqual(summary.input_rows, 12)
        self.assertEqual(summary.week_count, 6)
        self.assertEqual(summary.scope_count, 3)
        self.assertEqual(summary.result_rows, 6)
        self.assertEqual(
            set(results["scope_name"]),
            {"Iran + Israel", "Iran", "Israel"},
        )

    def test_positive_lag_uses_future_market_week(self):
        self._write_rows()

        results, summary = self.analyzer.analyze(
            self.input_file,
            metrics=("strike_events",),
            lags=(1,),
        )
        iran = results[
            results["scope_name"] == "Iran"
        ].iloc[0]

        self.assertEqual(iran["observations"], 5)
        self.assertAlmostEqual(
            iran["pearson_correlation"],
            1.0,
        )
        self.assertAlmostEqual(
            iran["spearman_correlation"],
            1.0,
        )
        self.assertEqual(
            iran["first_conflict_week"].date().isoformat(),
            "2025-01-04",
        )
        self.assertEqual(
            iran["first_response_week"].date().isoformat(),
            "2025-01-11",
        )

    def test_marks_constant_metric_without_correlation(self):
        rows = self._rows()

        for row in rows:
            row["strike_events"] = 0

        self._write_rows(rows)

        results, summary = self.analyzer.analyze(
            self.input_file,
            metrics=("strike_events",),
            lags=(0,),
        )

        self.assertTrue(
            (
                results["status"]
                == "constant_conflict_metric"
            ).all()
        )
        self.assertTrue(
            results["pearson_correlation"].isna().all()
        )

    def test_rejects_inconsistent_market_response(self):
        rows = self._rows()
        rows[1]["weekly_abnormal_return"] = 99.0
        self._write_rows(rows)

        with self.assertRaisesRegex(
            ValueError,
            "one value per market week",
        ):
            self.analyzer.analyze(self.input_file)

    def test_rejects_duplicate_country_week(self):
        rows = self._rows()
        rows.append(dict(rows[0]))
        self._write_rows(rows)

        with self.assertRaisesRegex(
            ValueError,
            "duplicate snapshot-country-week",
        ):
            self.analyzer.analyze(self.input_file)

    def test_rejects_missing_calendar_week(self):
        rows = [
            row
            for row in self._rows()
            if row["week_end_date"] != "2025-01-18"
        ]
        self._write_rows(rows)

        with self.assertRaisesRegex(
            ValueError,
            "consecutive weekly observations",
        ):
            self.analyzer.analyze(self.input_file)

    def test_rejects_negative_lag(self):
        self._write_rows()

        with self.assertRaisesRegex(
            ValueError,
            "negative",
        ):
            self.analyzer.analyze(
                self.input_file,
                lags=(-1,),
            )

    def test_exports_iso_dates(self):
        self._write_rows()
        results, summary = self.analyzer.analyze(
            self.input_file,
            metrics=("strike_events",),
            lags=(1,),
        )
        output_file = self.directory / "lag_analysis.csv"

        result_path = self.analyzer.export_csv(
            results,
            output_file,
        )
        exported = pd.read_csv(result_path)

        self.assertEqual(
            exported.loc[0, "first_conflict_week"],
            "2025-01-04",
        )
        self.assertEqual(
            exported.loc[0, "first_response_week"],
            "2025-01-11",
        )


if __name__ == "__main__":
    unittest.main()
