import tempfile
import unittest

from datetime import date
from pathlib import Path

import pandas as pd

from src.models.procurement_event import (
    ProcurementEvent,
    ProcurementEventType,
    ProcurementVerificationStatus,
)
from src.services.procurement_event_study import ProcurementEventStudy


class TestProcurementEventStudy(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary_directory.name)
        self.market_file = self.directory / "market.csv"
        self.study = ProcurementEventStudy()
        self._write_market()

    def tearDown(self):
        self.temporary_directory.cleanup()

    def _write_market(self, overrides=None):
        dates = pd.bdate_range("2025-01-01", periods=30)
        data = pd.DataFrame(
            {
                "Date": dates,
                "company_return": [
                    0.002 * index for index in range(30)
                ],
                "benchmark_return": [
                    0.001 * index for index in range(30)
                ],
                "abnormal_return": [
                    0.001 * index for index in range(30)
                ],
            }
        )

        if overrides is not None:
            data = overrides(data)

        data.to_csv(self.market_file, index=False)

    @staticmethod
    def _event(**overrides):
        values = {
            "announcement_date": date(2025, 1, 11),
            "company_name": "Rheinmetall AG",
            "company_ticker": "RHM.DE",
            "buyer_name": "Test buyer",
            "buyer_country_code": "DE",
            "event_type": ProcurementEventType.ORDER_AWARD,
            "title": "Test order",
            "systems": ("Skyranger 30",),
            "source_name": "Primary source",
            "source_url": "https://example.com/order",
            "contract_value_eur": 100_000_000,
            "aggregate_package_value_eur": None,
            "value_description": "EUR 100m",
            "is_air_defence": True,
            "verification_status": (
                ProcurementVerificationStatus.PRIMARY_SOURCE_CONFIRMED
            ),
            "related_initiative": "ESSI",
            "reviewed_by": "Markus",
            "notes": None,
        }
        values.update(overrides)
        return ProcurementEvent(**values)

    def test_computes_per_event_ols_market_model_with_enough_history(self):
        # 70 pre-event trading days (>= the 30-observation minimum) with an
        # exact, noise-free linear relationship so alpha/beta are known
        # precisely: company_return = 1.5 * benchmark_return.
        dates = pd.bdate_range("2025-01-01", periods=90)
        benchmark = [0.0005 * ((index % 7) - 3) for index in range(90)]
        company = [1.5 * value for value in benchmark]
        # The event day (index 70) and a few days after deliberately break
        # the pre-event relationship so the OLS abnormal return is
        # non-zero and independently checkable.
        for offset in range(0, 5):
            company[70 + offset] += 0.02

        data = pd.DataFrame(
            {
                "Date": dates,
                "company_return": company,
                "benchmark_return": benchmark,
                "abnormal_return": [
                    c - b for c, b in zip(company, benchmark)
                ],
            }
        )
        self._write_market(overrides=lambda _: data)

        detail, summaries, _ = self.study.analyze(
            events=(self._event(announcement_date=dates[70].date()),),
            market_file=self.market_file,
        )

        self.assertIn("market_model_abnormal_return", detail.columns)
        self.assertIn("ols_event_window_car", detail.columns)
        self.assertIn("ols_alpha", summaries.columns)
        self.assertIn("ols_beta", summaries.columns)

        summary_row = summaries.iloc[0]
        self.assertEqual(summary_row["ols_status"], "ok")
        self.assertAlmostEqual(summary_row["ols_alpha"], 0.0, places=8)
        self.assertAlmostEqual(summary_row["ols_beta"], 1.5, places=8)

        event_day = detail[detail["relative_trading_day"] == 0].iloc[0]
        expected_ols_abnormal_return = company[70] - (
            summary_row["ols_alpha"] + summary_row["ols_beta"] * benchmark[70]
        )
        self.assertAlmostEqual(
            event_day["market_model_abnormal_return"],
            expected_ols_abnormal_return,
        )
        self.assertAlmostEqual(expected_ols_abnormal_return, 0.02, places=8)

    def test_omits_ols_columns_when_not_enough_pre_event_history(self):
        detail, summaries, _ = self.study.analyze(
            events=(self._event(),),
            market_file=self.market_file,
        )

        self.assertNotIn("market_model_abnormal_return", detail.columns)
        self.assertEqual(
            summaries.iloc[0]["ols_status"],
            "insufficient_estimation_window",
        )
        self.assertNotIn("ols_alpha", summaries.columns)

    def test_aligns_weekend_to_next_trading_day(self):
        detail, summaries, summary = self.study.analyze(
            events=(self._event(),),
            market_file=self.market_file,
            pre_days=2,
            post_days=3,
        )

        self.assertEqual(summary.event_count, 1)
        self.assertEqual(summary.detail_rows, 6)
        self.assertEqual(
            summaries.loc[0, "effective_market_date"].date(),
            date(2025, 1, 13),
        )
        event_day = detail[
            detail["relative_trading_day"] == 0
        ].iloc[0]
        self.assertEqual(event_day["market_date"].date(), date(2025, 1, 13))

    def test_calculates_event_window_cars(self):
        detail, summaries, summary = self.study.analyze(
            events=(self._event(),),
            market_file=self.market_file,
            pre_days=2,
            post_days=10,
        )
        event_summary = summaries.iloc[0]

        self.assertAlmostEqual(event_summary["pre_event_car"], 0.013)
        self.assertAlmostEqual(
            event_summary["event_day_abnormal_return"],
            0.008,
        )
        self.assertAlmostEqual(
            event_summary["post_event_car_0_1"],
            0.017,
        )
        self.assertAlmostEqual(
            event_summary["post_event_car_0_5"],
            sum(0.001 * index for index in range(8, 14)),
        )
        self.assertAlmostEqual(
            detail.iloc[-1]["event_window_car"],
            event_summary["full_window_car"],
        )

    def test_creates_one_summary_per_event(self):
        second = self._event(
            announcement_date=date(2025, 1, 20),
            title="Second order",
            source_url="https://example.com/second-order",
        )
        detail, summaries, summary = self.study.analyze(
            events=(second, self._event()),
            market_file=self.market_file,
            pre_days=1,
            post_days=1,
        )

        self.assertEqual(len(summaries), 2)
        self.assertEqual(len(detail), 6)
        self.assertEqual(summary.first_event_date, date(2025, 1, 11))
        self.assertEqual(summary.last_event_date, date(2025, 1, 20))

    def test_rejects_incomplete_event_window(self):
        early_event = self._event(
            announcement_date=date(2025, 1, 1)
        )

        with self.assertRaisesRegex(ValueError, "complete event window"):
            self.study.analyze(
                events=(early_event,),
                market_file=self.market_file,
                pre_days=1,
                post_days=1,
            )

    def test_rejects_duplicate_market_date(self):
        def duplicate_first(data):
            return pd.concat([data, data.iloc[[0]]], ignore_index=True)

        self._write_market(duplicate_first)

        with self.assertRaisesRegex(ValueError, "duplicates"):
            self.study.analyze(
                events=(self._event(),),
                market_file=self.market_file,
            )

    def test_rejects_mixed_company_tickers(self):
        other = self._event(
            company_ticker="OTHER",
            title="Other company order",
            source_url="https://example.com/other-order",
        )

        with self.assertRaisesRegex(ValueError, "one company_ticker"):
            self.study.analyze(
                events=(self._event(), other),
                market_file=self.market_file,
            )

    def test_rejects_non_finite_market_return(self):
        def make_infinite(data):
            data.loc[0, "abnormal_return"] = float("inf")
            return data

        self._write_market(make_infinite)

        with self.assertRaisesRegex(ValueError, "finite values"):
            self.study.analyze(
                events=(self._event(),),
                market_file=self.market_file,
            )

    def test_exports_iso_dates(self):
        detail, summaries, summary = self.study.analyze(
            events=(self._event(),),
            market_file=self.market_file,
            pre_days=1,
            post_days=1,
        )
        output_file = self.directory / "detail.csv"

        result_path = self.study.export_csv(detail, output_file)
        exported = pd.read_csv(result_path)

        self.assertEqual(exported.loc[0, "announcement_date"], "2025-01-11")
        self.assertEqual(
            exported.loc[1, "effective_market_date"],
            "2025-01-13",
        )

    def test_rejects_negative_window(self):
        with self.assertRaisesRegex(ValueError, "must not be negative"):
            self.study.analyze(
                events=(self._event(),),
                market_file=self.market_file,
                pre_days=-1,
            )


if __name__ == "__main__":
    unittest.main()
