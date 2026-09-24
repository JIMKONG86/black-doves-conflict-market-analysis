import tempfile
import unittest

from pathlib import Path

import pandas as pd

from src.visualize_fuel_price_lags import (
    _aggregate_centcom_weeks,
    _load_centcom,
    _load_conflict,
    _validate_tax_price_order,
    create_fuel_price_lag_dashboard,
)


class TestFuelPriceLagVisualization(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary_directory.name)

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_creates_self_contained_responsive_dashboard(self):
        dates, timeline_file, weekly_file, lag_file, conflict_file, centcom_file = (
            self._write_inputs()
        )
        output = self.directory / "dashboard.html"

        result = create_fuel_price_lag_dashboard(
            timeline_file,
            weekly_file,
            lag_file,
            output,
            conflict_file=conflict_file,
            centcom_file=centcom_file,
        )

        html = result.read_text(encoding="utf-8")
        self.assertIn("viewport-fit=cover", html)
        self.assertIn("Fuel product", html)
        self.assertIn("How to read the charts", html)
        self.assertIn("multiple-comparison", html)
        self.assertIn("Conflict role / series", html)
        self.assertIn("Conflict metric", html)
        self.assertIn("affected country (ACLED)", html)
        self.assertIn("United States (initiator)", html)
        self.assertIn("confirmed U.S. strike-operation", html)
        self.assertIn("nested definitions", html)
        self.assertIn("German fuel price levels in EUR per litre", html)
        self.assertIn("index, not absolute price", html)
        self.assertIn("setVisible", html)
        self.assertIn("flex-wrap: wrap", html)
        self.assertIn("background-color: #1B2735", html)
        self.assertIn("border: 1px solid #52667B", html)
        self.assertIn("Bokeh", html)
        self.assertIn("Read this before comparing lines", html)
        self.assertIn("taxed fuel is always more expensive", html)

    def test_filters_are_disabled_when_irrelevant_to_the_active_tab(self):
        # Regression test: filters that cannot change anything on the
        # active tab (e.g. "Lag statistic", "Conflict role / series" and
        # "Conflict metric" while the Index tab is showing) must be
        # visibly disabled, not left looking equally interactive as the
        # filters that do apply. Also regression-guards the underlying
        # cause of a real bug: a Python dict with integer keys serializes
        # to an EMPTY object in Bokeh's CustomJS args (confirmed with a
        # live headless-Chromium session), silently disabling every
        # filter regardless of the active tab. String keys are required.
        dates, timeline_file, weekly_file, lag_file, conflict_file, centcom_file = (
            self._write_inputs()
        )
        output = self.directory / "dashboard.html"

        result = create_fuel_price_lag_dashboard(
            timeline_file,
            weekly_file,
            lag_file,
            output,
            conflict_file=conflict_file,
            centcom_file=centcom_file,
        )

        html = result.read_text(encoding="utf-8")
        self.assertIn("relevance_by_tab", html)
        self.assertIn('"0"', html)
        self.assertNotIn("relevance_by_tab={}", html)
        self.assertIn("cb_obj.active", html)

    def test_exposes_violence_against_civilians_as_a_conflict_metric(self):
        # Regression test: real ACLED civilian-targeted-violence fatality
        # and event counts already existed in the input data but were not
        # selectable in the chart, so the metric silently went unused.
        dates, timeline_file, weekly_file, lag_file, conflict_file, centcom_file = (
            self._write_inputs()
        )
        output = self.directory / "dashboard.html"

        result = create_fuel_price_lag_dashboard(
            timeline_file,
            weekly_file,
            lag_file,
            output,
            conflict_file=conflict_file,
            centcom_file=centcom_file,
        )

        html = result.read_text(encoding="utf-8")
        self.assertIn("Violence against civilians (events)", html)
        self.assertIn("Violence against civilians (fatalities)", html)
        self.assertIn("All conflict fatalities (ACLED total)", html)
        self.assertIn(
            "not a comprehensive civilian-casualty count", html
        )
        self.assertIn("No destroyed-facilities data", html)

    def test_rejects_inconsistent_strike_total(self):
        dates = pd.date_range("2026-02-23", periods=2, freq="7D")
        conflict_file = self._write_conflict(dates)
        conflict = pd.read_csv(conflict_file)
        conflict.loc[0, "strike_events"] += 1
        conflict.to_csv(conflict_file, index=False)

        with self.assertRaisesRegex(ValueError, "two strike-event components"):
            _load_conflict(conflict_file)

    def test_rejects_swapped_tax_price_order(self):
        weekly = pd.DataFrame(
            {
                "petrol_with_tax_eur_per_liter": [1.80],
                "petrol_without_tax_eur_per_liter": [0.80],
                "diesel_with_tax_eur_per_liter": [0.75],
                "diesel_without_tax_eur_per_liter": [1.70],
            }
        )
        with self.assertRaisesRegex(ValueError, "including taxes must exceed"):
            _validate_tax_price_order(weekly)

    def test_centcom_loader_excludes_out_of_scope_operation(self):
        path = self._write_centcom(include_iraq=True)

        data = _load_centcom(path)

        self.assertEqual(len(data), 1)
        self.assertEqual(set(data["affected_country_code"]), {"IR"})

    def test_centcom_aggregation_counts_distinct_days_not_releases(self):
        data = _load_centcom(self._write_centcom(second_day=True))

        weekly = _aggregate_centcom_weeks(
            data,
            pd.Timestamp("2026-02-28"),
            pd.Timestamp("2026-03-07"),
        )

        self.assertEqual(weekly["operation_day_count"].tolist(), [1, 1])
        self.assertEqual(weekly["release_count"].tolist(), [1, 1])

    def _write_inputs(self):
        dates = pd.date_range("2026-02-23", periods=4, freq="7D")
        timeline_rows = []
        series = [
            ("BRENT", "Brent crude", "ALL", "NOT_APPLICABLE", "USD/barrel"),
            ("PETROL_WITH_TAX", "Petrol incl. taxes", "PETROL", "WITH_TAX", "EUR/litre"),
            ("PETROL_WITHOUT_TAX", "Petrol excl. taxes", "PETROL", "WITHOUT_TAX", "EUR/litre"),
            ("DIESEL_WITH_TAX", "Diesel incl. taxes", "DIESEL", "WITH_TAX", "EUR/litre"),
            ("DIESEL_WITHOUT_TAX", "Diesel excl. taxes", "DIESEL", "WITHOUT_TAX", "EUR/litre"),
        ]
        for series_id, label, product, tax_basis, unit in series:
            for index, date_value in enumerate(dates):
                timeline_rows.append(
                    {
                        "observation_date": date_value,
                        "series_id": series_id,
                        "series_label": label,
                        "product": product,
                        "tax_basis": tax_basis,
                        "value": 70 + index,
                        "indexed_value": 100 + index,
                        "unit": unit,
                    }
                )
        timeline_file = self.directory / "timeline.csv"
        pd.DataFrame(timeline_rows).to_csv(timeline_file, index=False)

        weekly = pd.DataFrame({"fuel_observation_date": dates})
        weekly["petrol_with_tax_eur_per_liter"] = [1.80, 1.85, 1.90, 1.88]
        weekly["petrol_without_tax_eur_per_liter"] = [0.80, 0.84, 0.88, 0.86]
        weekly["diesel_with_tax_eur_per_liter"] = [1.70, 1.78, 1.84, 1.80]
        weekly["diesel_without_tax_eur_per_liter"] = [0.75, 0.82, 0.88, 0.84]
        for column_name in (
            "brent_weekly_pct_change",
            "petrol_with_tax_eur_per_liter_pct_change",
            "petrol_without_tax_eur_per_liter_pct_change",
            "diesel_with_tax_eur_per_liter_pct_change",
            "diesel_without_tax_eur_per_liter_pct_change",
        ):
            weekly[column_name] = [0.01, -0.02, 0.03, 0.01]
        weekly_file = self.directory / "weekly.csv"
        weekly.to_csv(weekly_file, index=False)

        lag_rows = []
        for product in ("PETROL", "DIESEL"):
            for tax_basis in ("WITH_TAX", "WITHOUT_TAX"):
                for lag in (0, 1):
                    lag_rows.append(
                        {
                            "product": product,
                            "tax_basis": tax_basis,
                            "lag_weeks": lag,
                            "observations": 20 - lag,
                            "pearson_correlation": 0.1 + lag / 10,
                            "pearson_p_value": 0.4,
                            "spearman_correlation": 0.2 + lag / 10,
                            "spearman_p_value": 0.3,
                            "status": "ok",
                        }
                    )
        lag_file = self.directory / "lags.csv"
        pd.DataFrame(lag_rows).to_csv(lag_file, index=False)
        conflict_file = self._write_conflict(dates)
        centcom_file = self._write_centcom()
        return dates, timeline_file, weekly_file, lag_file, conflict_file, centcom_file

    def _write_conflict(self, dates):
        rows = []
        for country_name, country_code, multiplier in (
            ("Iran", "IR", 3),
            ("Israel", "IL", 1),
        ):
            for index, date_value in enumerate(dates):
                air_events = multiplier * (index + 1)
                shell_events = multiplier * index
                air_fatalities = multiplier * index
                shell_fatalities = index
                rows.append(
                    {
                        "week_end_date": date_value,
                        "country_name": country_name,
                        "country_code": country_code,
                        "total_events": air_events + shell_events + 5,
                        "total_fatalities": (
                            air_fatalities + shell_fatalities
                        ),
                        "strike_events": air_events + shell_events,
                        "strike_fatalities": (
                            air_fatalities + shell_fatalities
                        ),
                        "air_drone_strike_events": air_events,
                        "air_drone_strike_fatalities": air_fatalities,
                        "shelling_artillery_missile_events": shell_events,
                        "shelling_artillery_missile_fatalities": (
                            shell_fatalities
                        ),
                        "violence_against_civilians_events": index,
                        "violence_against_civilians_fatalities": index,
                    }
                )
        path = self.directory / "conflict.csv"
        pd.DataFrame(rows).to_csv(path, index=False)
        return path

    def _write_centcom(self, include_iraq=False, second_day=False):
        rows = [
            {
                "source_release_id": "4418396",
                "event_date": "2026-02-28",
                "publication_date": "2026-02-28",
                "initiator_country_code": "US",
                "affected_country_code": "IR",
                "strike_type": "other",
                "operation_day_count": 1,
                "verification_status": "CONFIRMED",
                "include_in_core_series": True,
                "counting_unit": "official_release_confirmed_operation_day",
                "title": "U.S. Forces Launch Operation Epic Fury",
                "location": "Iran",
                "weapon_system": "Precision munitions",
                "description": "U.S. and partner forces began strikes.",
                "source_id": "US_CENTCOM_PUBLIC_RELEASES",
                "source_url": (
                    "https://www.centcom.mil/MEDIA/PUBLIC-RELEASES/"
                    "Article/4418396/example/"
                ),
            }
        ]
        if second_day:
            rows.append(
                rows[0]
                | {
                    "source_release_id": "4418500",
                    "event_date": "2026-03-01",
                    "publication_date": "2026-03-01",
                    "source_url": (
                        "https://www.centcom.mil/MEDIA/PUBLIC-RELEASES/"
                        "Article/4418500/example/"
                    ),
                }
            )
        if include_iraq:
            rows.append(
                rows[0]
                | {
                    "source_release_id": "4558191",
                    "event_date": "2026-03-02",
                    "publication_date": "2026-03-02",
                    "affected_country_code": "IQ",
                    "include_in_core_series": False,
                    "source_url": (
                        "https://www.centcom.mil/MEDIA/PUBLIC-RELEASES/"
                        "Article/4558191/example/"
                    ),
                }
            )
        path = self.directory / "centcom.csv"
        pd.DataFrame(rows).to_csv(path, index=False)
        return path


if __name__ == "__main__":
    unittest.main()
