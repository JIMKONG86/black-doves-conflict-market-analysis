import tempfile
import unittest

from pathlib import Path

import pandas as pd

from src.visualize_market_universe_event_study import (
    _company_ranking,
    _role_ranking,
    _select_event,
    create_market_universe_event_study_chart,
)


class TestMarketUniverseEventStudyVisualization(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary_directory.name)
        self.detail_file = self.directory / "detail.csv"
        self.company_file = self.directory / "companies.csv"
        self.sample_file = self.directory / "samples.csv"
        self._write_inputs()

    def tearDown(self):
        self.temporary_directory.cleanup()

    def _write_inputs(self):
        companies = [
            (
                "CMP001",
                "Alpha Defence",
                "ALP",
                "CONFIRMATORY",
                "Defence Contractor",
                True,
                (0.02, 0.03, 0.04),
            ),
            (
                "CMP002",
                "Beta Energy",
                "BET",
                "EXPLORATORY",
                "Raw Materials & Energy",
                False,
                (0.01, 0.02, 0.03),
            ),
            (
                "CMP003",
                "Volkswagen AG",
                "VOW3.DE",
                "POST_HOC_EXPLORATORY",
                "Automotive Manufacturer",
                False,
                (-0.01, -0.02, -0.03),
            ),
        ]
        detail_rows = []
        company_rows = []
        sample_rows = []

        for (
            company_id,
            company_name,
            ticker,
            sample_group,
            role,
            confirmatory,
            abnormal_returns,
        ) in companies:
            cumulative = 0.0

            for relative_day, abnormal_return in zip(
                (-1, 0, 1), abnormal_returns
            ):
                cumulative += abnormal_return
                detail_rows.append(
                    {
                        "event_id": "event-1",
                        "event_calendar_date": "2026-03-01",
                        "effective_market_date": "2026-03-02",
                        "event_title": "Illustrative event",
                        "company_id": company_id,
                        "company_name": company_name,
                        "analysis_tier": "PRIMARY_DIRECT",
                        "role_category": role,
                        "is_confirmatory": confirmatory,
                        "sample_group": sample_group,
                        "market_date": (
                            pd.Timestamp("2026-03-02")
                            + pd.offsets.BDay(relative_day)
                        ),
                        "relative_trading_day": relative_day,
                        "abnormal_return": abnormal_return,
                        "event_window_car": cumulative,
                    }
                )

            company_rows.append(
                {
                    "event_id": "event-1",
                    "event_calendar_date": "2026-03-01",
                    "effective_market_date": "2026-03-02",
                    "event_title": "Illustrative event",
                    "company_id": company_id,
                    "company_name": company_name,
                    "market_data_ticker": ticker,
                    "benchmark_ticker": "^GSPC",
                    "analysis_tier": "PRIMARY_DIRECT",
                    "role_category": role,
                    "is_confirmatory": confirmatory,
                    "sample_group": sample_group,
                    "event_day_abnormal_return": abnormal_returns[1],
                    "post_event_car_0_1": sum(abnormal_returns[1:]),
                    "post_event_car_0_5": sum(abnormal_returns[1:]),
                    "post_event_car_0_10": sum(abnormal_returns[1:]),
                }
            )

        for sample_group in (
            "CONFIRMATORY",
            "EXPLORATORY",
            "POST_HOC_EXPLORATORY",
        ):
            group_rows = [
                row
                for row in detail_rows
                if row["sample_group"] == sample_group
            ]
            cumulative = 0.0

            for relative_day in (-1, 0, 1):
                aar = next(
                    row["abnormal_return"]
                    for row in group_rows
                    if row["relative_trading_day"] == relative_day
                )
                cumulative += aar
                sample_rows.append(
                    {
                        "event_id": "event-1",
                        "event_calendar_date": "2026-03-01",
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

    def test_creates_complete_interactive_html(self):
        output_file = self.directory / "dashboard.html"

        result = create_market_universe_event_study_chart(
            detail_file=self.detail_file,
            company_summary_file=self.company_file,
            sample_summary_file=self.sample_file,
            output_path=output_file,
        )

        document = result.read_text(encoding="utf-8")
        self.assertTrue(result.is_file())
        self.assertIn("BLACK DOVES", document)
        self.assertIn("All companies", document)
        self.assertIn("Company roles", document)
        self.assertIn("Volkswagen AG", document)
        self.assertIn('"height":676', document)

    def test_rejects_non_html_output(self):
        with self.assertRaisesRegex(ValueError, "use .html"):
            create_market_universe_event_study_chart(
                detail_file=self.detail_file,
                company_summary_file=self.company_file,
                sample_summary_file=self.sample_file,
                output_path=self.directory / "dashboard.txt",
            )

    def test_company_ranking_orders_ten_day_car(self):
        companies = pd.read_csv(self.company_file)

        ranking = _company_ranking(companies)

        self.assertEqual(ranking.iloc[0]["company_name"], "Volkswagen AG")
        self.assertEqual(ranking.iloc[-1]["company_name"], "Alpha Defence")
        self.assertEqual(
            ranking.iloc[-1]["sample_label"],
            "Confirmatory",
        )

    def test_role_ranking_calculates_counts_and_positive_share(self):
        companies = pd.read_csv(self.company_file)

        roles = _role_ranking(companies)
        defence = roles[
            roles["role_category"] == "Defence Contractor"
        ].iloc[0]

        self.assertEqual(defence["company_count"], 1)
        self.assertEqual(defence["positive_share"], 1.0)

    def test_requires_event_choice_for_multiple_events(self):
        frame = pd.DataFrame({"event_id": ["event-1", "event-2"]})

        with self.assertRaisesRegex(ValueError, "use --event-id"):
            _select_event((frame, frame.copy(), frame.copy()), None)


if __name__ == "__main__":
    unittest.main()
