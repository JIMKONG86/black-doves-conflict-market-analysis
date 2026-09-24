import unittest

import numpy as np
import pandas as pd

from src.services.ols_market_model import (
    add_market_model_columns,
    fit_ols_market_model,
)


class TestFitOlsMarketModel(unittest.TestCase):
    def test_recovers_known_alpha_and_beta_without_noise(self):
        rng = np.random.default_rng(42)
        benchmark = rng.normal(0, 0.01, size=200)
        true_alpha = 0.0003
        true_beta = 1.4
        company = true_alpha + true_beta * benchmark

        fit = fit_ols_market_model(company, benchmark)

        self.assertEqual(fit.status, "ok")
        self.assertAlmostEqual(fit.alpha, true_alpha, places=8)
        self.assertAlmostEqual(fit.beta, true_beta, places=8)
        self.assertAlmostEqual(fit.r_squared, 1.0, places=6)
        self.assertEqual(fit.estimation_observations, 200)

    def test_flags_insufficient_estimation_window(self):
        fit = fit_ols_market_model(
            company_returns=[0.01, 0.02, -0.01],
            benchmark_returns=[0.005, 0.01, -0.004],
        )

        self.assertEqual(fit.status, "insufficient_estimation_window")
        self.assertTrue(np.isnan(fit.alpha))
        self.assertTrue(np.isnan(fit.beta))
        self.assertEqual(fit.estimation_observations, 3)

    def test_flags_constant_benchmark_return(self):
        n = 40
        fit = fit_ols_market_model(
            company_returns=np.linspace(-0.01, 0.01, n),
            benchmark_returns=np.zeros(n),
        )

        self.assertEqual(fit.status, "constant_benchmark_return")
        self.assertTrue(np.isnan(fit.beta))

    def test_ignores_non_finite_observations(self):
        company = [0.01, float("nan"), 0.02] * 15
        benchmark = [0.01, 0.02, 0.02] * 15

        fit = fit_ols_market_model(company, benchmark)

        self.assertEqual(fit.estimation_observations, 30)

    def test_rejects_mismatched_shapes(self):
        with self.assertRaises(ValueError):
            fit_ols_market_model([0.01, 0.02], [0.01])


class TestAddMarketModelColumns(unittest.TestCase):
    @staticmethod
    def _comparison(n_pre_event=40, n_post_event=10):
        rng = np.random.default_rng(7)
        dates = pd.bdate_range("2026-01-01", periods=n_pre_event + n_post_event)
        benchmark_return = rng.normal(0, 0.01, size=len(dates))
        company_return = 0.0002 + 1.2 * benchmark_return
        return pd.DataFrame(
            {
                "Date": dates,
                "company_return": company_return,
                "benchmark_return": benchmark_return,
            }
        ), dates[n_pre_event]

    def test_adds_expected_columns_and_fits_on_pre_event_window_only(self):
        comparison, event_date = self._comparison()

        result = add_market_model_columns(comparison, event_date=event_date)

        for column in (
            "ols_status",
            "ols_alpha",
            "ols_beta",
            "ols_r_squared",
            "ols_estimation_window_observations",
            "market_model_expected_return",
            "market_model_abnormal_return",
            "market_model_cumulative_abnormal_return",
        ):
            self.assertIn(column, result.columns)

        self.assertEqual(result["ols_status"].iloc[0], "ok")
        self.assertEqual(
            result["ols_estimation_window_observations"].iloc[0], 40
        )
        # Original columns must be untouched.
        pd.testing.assert_series_equal(
            result["company_return"], comparison["company_return"]
        )

    def test_does_not_use_event_date_or_later_for_the_fit(self):
        comparison, event_date = self._comparison(
            n_pre_event=35, n_post_event=5
        )
        # Corrupt the post-event benchmark data so a look-ahead bug
        # would change the fitted parameters if it existed.
        post_event_mask = comparison["Date"] >= event_date
        comparison.loc[post_event_mask, "benchmark_return"] = 999.0
        comparison.loc[post_event_mask, "company_return"] = -999.0

        result = add_market_model_columns(comparison, event_date=event_date)

        self.assertEqual(result["ols_status"].iloc[0], "ok")
        self.assertLess(abs(result["ols_beta"].iloc[0]), 10)

    def test_raises_on_missing_required_columns(self):
        with self.assertRaises(ValueError):
            add_market_model_columns(
                pd.DataFrame({"Date": ["2026-01-01"]}),
                event_date="2026-02-28",
            )


if __name__ == "__main__":
    unittest.main()
