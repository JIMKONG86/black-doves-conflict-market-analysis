import tempfile
import unittest

from datetime import date
from pathlib import Path

import pandas as pd

from src.models.market_event import MarketEvent
from src.services.market_position_analysis import MarketPositionAnalysis


class TestMarketPositionAnalysis(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary_directory.name)
        self.market_file = self.directory / "market.csv"
        self._market_panel().to_csv(self.market_file, index=False)

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_analyzes_exact_calendar_period(self):
        detail, companies, samples, roles, summary = (
            MarketPositionAnalysis().analyze(
                events=[self._event()],
                market_file=self.market_file,
                analysis_start="2026-01-01",
                analysis_end="2026-08-18",
            )
        )

        expected_days = len(pd.bdate_range("2026-01-01", "2026-08-18"))
        self.assertEqual(summary.company_count, 4)
        self.assertEqual(summary.detail_rows, expected_days * 4)
        self.assertEqual(detail["market_date"].min().date(), date(2026, 1, 1))
        self.assertEqual(detail["market_date"].max().date(), date(2026, 8, 18))
        self.assertEqual(len(companies), 4)
        self.assertFalse(samples.empty)
        self.assertFalse(roles.empty)

    def test_detects_relative_position_shift(self):
        _, companies, _, _, summary = MarketPositionAnalysis().analyze(
            events=[self._event()],
            market_file=self.market_file,
        )
        indexed = companies.set_index("company_id")

        self.assertEqual(indexed.loc["CMP001", "pre_rank"], 1)
        self.assertEqual(indexed.loc["CMP001", "post_rank"], 4)
        self.assertEqual(
            indexed.loc["CMP001", "position_shift"],
            "WEAKENED_QUARTILE",
        )
        self.assertEqual(indexed.loc["CMP004", "pre_rank"], 4)
        self.assertEqual(indexed.loc["CMP004", "post_rank"], 1)
        self.assertEqual(
            indexed.loc["CMP004", "position_shift"],
            "IMPROVED_QUARTILE",
        )
        self.assertEqual(summary.improved_quartile_count, 2)
        self.assertEqual(summary.weakened_quartile_count, 2)

    def test_resets_phase_cumulative_returns_at_event(self):
        detail, _, _, _, _ = MarketPositionAnalysis().analyze(
            events=[self._event()],
            market_file=self.market_file,
        )
        company = detail[detail["company_id"] == "CMP001"]
        event_day = company[company["relative_trading_day"] == 0].iloc[0]

        self.assertAlmostEqual(event_day["phase_car"], -0.01)
        self.assertAlmostEqual(event_day["phase_company_return"], -0.005)
        self.assertAlmostEqual(event_day["phase_benchmark_return"], 0.005)

    def test_rejects_event_outside_period(self):
        with self.assertRaisesRegex(ValueError, "outside the analysis period"):
            MarketPositionAnalysis().analyze(
                events=[self._event()],
                market_file=self.market_file,
                analysis_start="2026-03-10",
                analysis_end="2026-08-18",
            )

    def test_adds_ols_columns_when_market_model_column_present(self):
        panel = self._market_panel()
        panel["market_model_abnormal_return"] = panel["abnormal_return"] * 2.0
        market_file = self.directory / "market_with_ols.csv"
        panel.to_csv(market_file, index=False)

        detail, companies, samples, roles, _ = MarketPositionAnalysis().analyze(
            events=[self._event()],
            market_file=market_file,
        )

        self.assertIn("market_model_abnormal_return", detail.columns)
        self.assertIn("phase_ols_car", detail.columns)
        self.assertIn("pre_ols_car", companies.columns)
        self.assertIn("post_mean_daily_ols_abnormal_return", companies.columns)
        self.assertIn("ols_aar", samples.columns)
        self.assertIn("ols_caar", samples.columns)

        indexed = companies.set_index("company_id")
        self.assertAlmostEqual(
            indexed.loc["CMP001", "pre_ols_car"],
            indexed.loc["CMP001", "pre_car"] * 2.0,
        )

    def test_omits_ols_columns_when_market_model_column_absent(self):
        detail, companies, samples, _, _ = MarketPositionAnalysis().analyze(
            events=[self._event()],
            market_file=self.market_file,
        )

        self.assertNotIn("market_model_abnormal_return", detail.columns)
        self.assertNotIn("pre_ols_car", companies.columns)
        self.assertNotIn("ols_aar", samples.columns)

    @staticmethod
    def _event():
        return MarketEvent(
            event_id="EVT001",
            event_date=date(2026, 2, 28),
            title="Test event",
            event_type="CONFLICT_ONSET",
            affected_country_codes=("IR", "IL", "US"),
            verification_status="PRE_SPECIFIED",
            source_name="Test source",
            source_url="https://example.com/event",
        )

    @staticmethod
    def _market_panel():
        dates = pd.bdate_range("2026-01-01", "2026-08-18")
        definitions = (
            ("CMP001", "Company A", True, "PRIMARY_DIRECT", 0.01, -0.01),
            ("CMP002", "Company B", False, "SECONDARY", 0.005, -0.005),
            ("CMP003", "Company C", False, "SECONDARY", -0.005, 0.005),
            (
                "CMP004",
                "Volkswagen AG",
                False,
                "POST_HOC_EXPLORATORY_ROBUSTNESS_CASE",
                -0.01,
                0.01,
            ),
        )
        frames = []

        for company_id, name, confirmatory, tier, pre_value, post_value in (
            definitions
        ):
            abnormal = [
                pre_value if value < pd.Timestamp("2026-03-02") else post_value
                for value in dates
            ]
            frames.append(
                pd.DataFrame(
                    {
                        "Date": dates,
                        "company_id": company_id,
                        "company_name": name,
                        "market_data_ticker": f"{company_id}.X",
                        "benchmark_ticker": "^INDEX",
                        "trade_currency": "EUR",
                        "primary_listing_exchange": "Test Exchange",
                        "analysis_tier": tier,
                        "role_category": "Defence Contractor",
                        "is_confirmatory": confirmatory,
                        "company_return": [value + 0.005 for value in abnormal],
                        "benchmark_return": 0.005,
                        "abnormal_return": abnormal,
                    }
                )
            )

        return pd.concat(frames, ignore_index=True)


if __name__ == "__main__":
    unittest.main()
