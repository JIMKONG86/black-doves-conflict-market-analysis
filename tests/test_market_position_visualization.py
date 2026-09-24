import tempfile
import unittest

from pathlib import Path

import pandas as pd

from src.visualize_market_position_analysis import (
    _dashboard_company_data,
    _filter_callback_code,
    _interpretation_guide_html,
    _load_detail,
    _month_axis_values,
    _responsive_callback_code,
    create_market_position_dashboard,
)


class TestMarketPositionVisualization(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary_directory.name)
        self.detail_file = self.directory / "detail.csv"
        self.company_file = self.directory / "companies.csv"
        self.sample_file = self.directory / "samples.csv"
        self._write_inputs()

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_creates_long_horizon_dashboard(self):
        output_file = self.directory / "dashboard.html"

        result = create_market_position_dashboard(
            detail_file=self.detail_file,
            company_file=self.company_file,
            sample_file=self.sample_file,
            output_path=output_file,
        )

        document = result.read_text(encoding="utf-8")
        self.assertTrue(result.is_file())
        self.assertIn("BLACK DOVES", document)
        self.assertIn("Position map", document)
        self.assertIn("Rank shifts", document)
        self.assertIn("Volkswagen AG", document)
        self.assertIn("How to read this dashboard", document)
        self.assertIn("Confirmatory (n=8)", document)
        self.assertIn("Post-hoc exploratory", document)
        self.assertIn("Abnormal return (AR)", document)
        self.assertIn('name="viewport"', document)
        self.assertIn("width=device-width", document)
        self.assertIn("overflow-x: hidden", document)
        self.assertNotIn("https://cdn.bokeh.org", document)

    def test_mobile_callback_changes_chart_heights_and_toolbar_position(self):
        callback = _responsive_callback_code()

        self.assertIn("window.innerWidth <= 600", callback)
        self.assertIn("sample_chart.height", callback)
        self.assertIn("sharedChartHeight", callback)
        self.assertIn("chart.toolbar_location", callback)
        self.assertIn('window.addEventListener("resize"', callback)

    def test_dashboard_contains_client_side_filters(self):
        output_file = self.directory / "dashboard.html"

        result = create_market_position_dashboard(
            detail_file=self.detail_file,
            company_file=self.company_file,
            sample_file=self.sample_file,
            output_path=output_file,
        )

        document = result.read_text(encoding="utf-8")
        self.assertIn("Filter dashboard data", document)
        self.assertIn("Sample classification", document)
        self.assertIn("Company role", document)
        self.assertIn("Reset filters", document)
        self.assertIn("const selectedIds", document)
        self.assertIn("flex-wrap: wrap", document)
        self.assertIn(".bk-btn-default", document)
        self.assertIn(".bk-tab.bk-active", document)
        self.assertIn("background-color: #1B2735", document)

    def test_filter_callback_recalculates_group_caar(self):
        callback = _filter_callback_code()

        self.assertIn("selectedIds", callback)
        self.assertIn("abnormalReturn", callback)
        self.assertIn("cumulative += average", callback)
        self.assertIn("sample_sources[groupIndex].data", callback)

    def test_filter_callback_recalculates_ols_caar_alongside_naive(self):
        callback = _filter_callback_code()

        self.assertIn("hasOls", callback)
        self.assertIn("market_model_abnormal_return", callback)
        self.assertIn("nextData.ols_aar", callback)
        self.assertIn("nextData.ols_caar", callback)

    def test_filter_callback_syncs_sample_and_role_to_selected_company(self):
        callback = _filter_callback_code()

        self.assertIn("cb_obj === company_filter", callback)
        self.assertIn("sample_filter.value = matchedSample", callback)
        self.assertIn("role_filter.value = matchedRole", callback)

    def test_filter_callback_flags_empty_combination(self):
        callback = _filter_callback_code()

        self.assertIn("matching.length === 0", callback)
        self.assertIn("Reset filters", callback)

    def test_mobile_axis_labels_prefer_compact_tickers(self):
        companies = pd.read_csv(self.company_file)

        dashboard_data = _dashboard_company_data(companies)

        self.assertEqual(
            dashboard_data["axis_label"].tolist(),
            ["ALP", "BET", "VOW3.DE"],
        )

    def test_interpretation_guide_defines_scope_and_limits(self):
        guide = _interpretation_guide_html()

        self.assertIn("hypothesis-generating", guide)
        self.assertIn("selection bias", guide)
        self.assertIn("not product-market share", guide)
        self.assertIn("do not establish", guide)

    def test_rejects_non_html_output(self):
        with self.assertRaisesRegex(ValueError, "use .html"):
            create_market_position_dashboard(
                detail_file=self.detail_file,
                company_file=self.company_file,
                sample_file=self.sample_file,
                output_path=self.directory / "dashboard.txt",
            )

    def test_builds_month_axis_from_actual_market_dates(self):
        detail = _load_detail(self.detail_file)

        ticks, labels = _month_axis_values(detail)

        self.assertEqual(ticks, [0])
        self.assertEqual(labels, {0: "Mar 2026"})

    def test_rejects_missing_phase(self):
        detail = pd.read_csv(self.detail_file)
        detail = detail[detail["phase"] == "POST_EVENT"]
        detail.to_csv(self.detail_file, index=False)

        with self.assertRaisesRegex(ValueError, "PRE_EVENT and POST_EVENT"):
            create_market_position_dashboard(
                detail_file=self.detail_file,
                company_file=self.company_file,
                sample_file=self.sample_file,
                output_path=self.directory / "dashboard.html",
            )

    def _write_inputs(self):
        definitions = (
            (
                "CMP001",
                "Alpha Defence",
                "ALP",
                "CONFIRMATORY",
                True,
                "IMPROVED_QUARTILE",
                3,
                1,
                0.0,
                1.0,
                -0.01,
                0.05,
            ),
            (
                "CMP002",
                "Beta Energy",
                "BET",
                "EXPLORATORY",
                False,
                "UNCHANGED_QUARTILE",
                2,
                2,
                0.5,
                0.5,
                0.00,
                0.02,
            ),
            (
                "CMP003",
                "Volkswagen AG",
                "VOW3.DE",
                "POST_HOC_EXPLORATORY",
                False,
                "WEAKENED_QUARTILE",
                1,
                3,
                1.0,
                0.0,
                0.02,
                -0.04,
            ),
        )
        company_rows = []
        detail_rows = []
        sample_rows = []

        for (
            company_id,
            company_name,
            ticker,
            sample_group,
            confirmatory,
            shift,
            pre_rank,
            post_rank,
            pre_percentile,
            post_percentile,
            pre_car,
            post_car,
        ) in definitions:
            company_rows.append(
                {
                    "event_id": "event-1",
                    "event_calendar_date": "2026-02-28",
                    "event_title": "Illustrative event",
                    "analysis_start_date": "2026-01-01",
                    "analysis_end_date": "2026-08-18",
                    "company_id": company_id,
                    "company_name": company_name,
                    "market_data_ticker": ticker,
                    "benchmark_ticker": "^INDEX",
                    "role_category": "Defence Contractor",
                    "sample_group": sample_group,
                    "pre_car": pre_car,
                    "post_car": post_car,
                    "pre_company_total_return": pre_car + 0.01,
                    "pre_benchmark_total_return": 0.01,
                    "post_company_total_return": post_car + 0.02,
                    "post_benchmark_total_return": 0.02,
                    "pre_mean_daily_abnormal_return": pre_car / 2,
                    "post_mean_daily_abnormal_return": post_car / 2,
                    "pre_rank": pre_rank,
                    "post_rank": post_rank,
                    "rank_change": pre_rank - post_rank,
                    "pre_percentile": pre_percentile,
                    "post_percentile": post_percentile,
                    "percentile_change": (
                        post_percentile - pre_percentile
                    ),
                    "pre_quartile": "TOP_QUARTILE",
                    "post_quartile": "TOP_QUARTILE",
                    "position_shift": shift,
                }
            )

            for relative_day, phase, abnormal_return in (
                (-2, "PRE_EVENT", pre_car / 2),
                (-1, "PRE_EVENT", pre_car / 2),
                (0, "POST_EVENT", post_car / 2),
                (1, "POST_EVENT", post_car / 2),
            ):
                detail_rows.append(
                    {
                        "event_id": "event-1",
                        "event_calendar_date": "2026-02-28",
                        "event_title": "Illustrative event",
                        "company_id": company_id,
                        "company_name": company_name,
                        "is_confirmatory": confirmatory,
                        "sample_group": sample_group,
                        "market_date": (
                            pd.Timestamp("2026-03-02")
                            + pd.offsets.BDay(relative_day)
                        ),
                        "phase": phase,
                        "relative_trading_day": relative_day,
                        "abnormal_return": abnormal_return,
                        "phase_car": (
                            abnormal_return
                            if relative_day in (-2, 0)
                            else abnormal_return * 2
                        ),
                    }
                )

            cumulative = 0.0

            for relative_day in (0, 1):
                aar = post_car / 2
                cumulative += aar
                sample_rows.append(
                    {
                        "event_id": "event-1",
                        "event_calendar_date": "2026-02-28",
                        "event_title": "Illustrative event",
                        "sample_group": sample_group,
                        "relative_trading_day": relative_day,
                        "company_count": 1,
                        "aar": aar,
                        "caar": cumulative,
                    }
                )

        pd.DataFrame(detail_rows).to_csv(self.detail_file, index=False)
        pd.DataFrame(company_rows).to_csv(self.company_file, index=False)
        pd.DataFrame(sample_rows).to_csv(self.sample_file, index=False)


if __name__ == "__main__":
    unittest.main()
