import tempfile
import unittest

from datetime import date
from pathlib import Path

import pandas as pd

from src.models.market_event import MarketEvent
from src.services.market_universe_event_study import (
    MarketUniverseEventStudy,
)


class TestMarketUniverseEventStudy(unittest.TestCase):
    def test_analyzes_all_sample_groups_and_builds_aar_caar(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "market.csv"
            self._market_panel().to_csv(path, index=False)
            (
                detail,
                companies,
                samples,
                roles,
                summary,
            ) = MarketUniverseEventStudy().analyze(
                events=[self._event()],
                market_file=path,
                pre_days=5,
                post_days=10,
            )

        self.assertEqual(summary.event_count, 1)
        self.assertEqual(summary.company_count, 3)
        self.assertEqual(summary.confirmatory_count, 1)
        self.assertEqual(summary.exploratory_count, 1)
        self.assertEqual(summary.post_hoc_count, 1)
        self.assertEqual(summary.detail_rows, 48)
        self.assertEqual(len(companies), 3)
        self.assertEqual(
            set(companies["sample_group"]),
            {
                "CONFIRMATORY",
                "EXPLORATORY",
                "POST_HOC_EXPLORATORY",
            },
        )
        self.assertEqual(
            detail["effective_market_date"].dt.date.unique().tolist(),
            [date(2026, 3, 2)],
        )
        confirmatory_day_zero = samples[
            (samples["sample_group"] == "CONFIRMATORY")
            & (samples["relative_trading_day"] == 0)
        ].iloc[0]
        self.assertAlmostEqual(confirmatory_day_zero["aar"], 0.01)
        self.assertAlmostEqual(confirmatory_day_zero["caar"], 0.06)
        self.assertIn("Defence Contractor", set(roles["role_category"]))

    def test_adds_ols_aar_caar_when_market_model_column_present(self):
        panel = self._market_panel()
        # One deterministic OLS abnormal-return value per company,
        # distinct from the naive abnormal_return so a bug that mixed
        # the two up would be caught by the assertions below.
        ols_value_by_company = {
            "CMP001": 0.03,
            "CMP002": 0.04,
            "CMP003": -0.02,
        }
        panel["market_model_abnormal_return"] = panel["company_id"].map(
            ols_value_by_company
        )

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "market.csv"
            panel.to_csv(path, index=False)
            (
                detail,
                companies,
                samples,
                roles,
                summary,
            ) = MarketUniverseEventStudy().analyze(
                events=[self._event()],
                market_file=path,
                pre_days=5,
                post_days=10,
            )

        self.assertIn("market_model_abnormal_return", detail.columns)
        self.assertIn("ols_event_window_car", detail.columns)
        self.assertIn("ols_pre_event_car", companies.columns)
        self.assertIn("ols_full_window_car", companies.columns)
        self.assertIn("ols_aar", samples.columns)
        self.assertIn("ols_caar", samples.columns)

        confirmatory_day_zero = samples[
            (samples["sample_group"] == "CONFIRMATORY")
            & (samples["relative_trading_day"] == 0)
        ].iloc[0]
        # Only CMP001 (0.03) is CONFIRMATORY in this fixture.
        self.assertAlmostEqual(confirmatory_day_zero["ols_aar"], 0.03)

        cmp001_detail = detail[
            (detail["company_id"] == "CMP001")
            & (detail["relative_trading_day"] == 0)
        ].iloc[0]
        self.assertAlmostEqual(
            cmp001_detail["market_model_abnormal_return"], 0.03
        )

    def test_omits_ols_columns_when_market_model_column_absent(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "market.csv"
            self._market_panel().to_csv(path, index=False)
            (
                detail,
                companies,
                samples,
                roles,
                summary,
            ) = MarketUniverseEventStudy().analyze(
                events=[self._event()],
                market_file=path,
            )

        self.assertNotIn("market_model_abnormal_return", detail.columns)
        self.assertNotIn("ols_aar", samples.columns)
        self.assertNotIn("ols_caar", samples.columns)

    def test_keeps_exchange_specific_effective_dates(self):
        panel = self._market_panel()
        saudi = panel[panel["company_id"] == "CMP002"].copy()
        saudi_dates = pd.to_datetime(saudi["Date"]).tolist()
        event_position = next(
            index
            for index, value in enumerate(saudi_dates)
            if value.date() >= date(2026, 2, 28)
        )
        saudi_dates[event_position] = pd.Timestamp("2026-03-01")
        saudi["Date"] = saudi_dates
        panel = pd.concat(
            [panel[panel["company_id"] != "CMP002"], saudi],
            ignore_index=True,
        )

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "market.csv"
            panel.to_csv(path, index=False)
            _, companies, _, _, _ = MarketUniverseEventStudy().analyze(
                events=[self._event()],
                market_file=path,
            )

        effective = companies.set_index("company_id")[
            "effective_market_date"
        ]
        self.assertEqual(effective["CMP001"].date(), date(2026, 3, 2))
        self.assertEqual(effective["CMP002"].date(), date(2026, 3, 1))

    def test_rejects_duplicate_company_date(self):
        panel = self._market_panel()
        panel = pd.concat([panel, panel.iloc[[0]]], ignore_index=True)

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "market.csv"
            panel.to_csv(path, index=False)

            with self.assertRaisesRegex(ValueError, "duplicate company-date"):
                MarketUniverseEventStudy().analyze(
                    events=[self._event()],
                    market_file=path,
                )

    def test_requires_complete_event_window(self):
        panel = self._market_panel().query("company_id == 'CMP001'")

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "market.csv"
            panel.iloc[:10].to_csv(path, index=False)

            with self.assertRaisesRegex(ValueError, "complete event window"):
                MarketUniverseEventStudy().analyze(
                    events=[self._event()],
                    market_file=path,
                )

    def test_exports_csv_atomically(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "result.csv"
            result = MarketUniverseEventStudy.export_csv(
                pd.DataFrame({"value": [1]}),
                path,
            )

            self.assertEqual(result, path)
            self.assertTrue(path.is_file())
            self.assertFalse(path.with_suffix(".csv.tmp").exists())

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
        dates = pd.bdate_range("2026-02-20", periods=20)
        frames = []
        definitions = (
            (
                "CMP001",
                "Company A",
                True,
                "PRIMARY_DIRECT",
                "Defence Contractor",
                0.01,
            ),
            (
                "CMP002",
                "Company B",
                False,
                "PRIMARY_DIRECT",
                "Defence Contractor",
                0.02,
            ),
            (
                "CMP003",
                "Volkswagen AG",
                False,
                "POST_HOC_EXPLORATORY_ROBUSTNESS_CASE",
                "Automotive Manufacturer",
                -0.01,
            ),
        )

        for company_id, name, confirmatory, tier, role, abnormal in definitions:
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
                        "role_category": role,
                        "is_confirmatory": confirmatory,
                        "company_return": abnormal + 0.005,
                        "benchmark_return": 0.005,
                        "abnormal_return": abnormal,
                    }
                )
            )

        return pd.concat(frames, ignore_index=True)


if __name__ == "__main__":
    unittest.main()
