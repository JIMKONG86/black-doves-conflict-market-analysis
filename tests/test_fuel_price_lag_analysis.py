import tempfile
import unittest

from pathlib import Path

import pandas as pd

from src.services.fuel_price_lag_analysis import FuelPriceLagAnalyzer


class TestFuelPriceLagAnalyzer(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary_directory.name)
        self.input_file = self.directory / "weekly.csv"
        self.analyzer = FuelPriceLagAnalyzer()
        self._write_panel()

    def tearDown(self):
        self.temporary_directory.cleanup()

    def _write_panel(self, omit_index=None):
        dates = pd.date_range("2026-01-05", periods=14, freq="7D")
        brent = [0.03, -0.01, 0.05, 0.00, -0.04, 0.02, 0.08,
                 -0.03, 0.01, 0.06, -0.02, 0.04, -0.05, 0.07]
        fuel = [0.4, -0.2] + brent[:-2]
        frame = pd.DataFrame(
            {
                "fuel_observation_date": dates,
                "brent_week_start": dates - pd.Timedelta(days=7),
                "brent_week_end": dates - pd.Timedelta(days=1),
                "brent_weekly_pct_change": brent,
                "petrol_with_tax_eur_per_liter_pct_change": fuel,
                "petrol_without_tax_eur_per_liter_pct_change": fuel,
                "diesel_with_tax_eur_per_liter_pct_change": fuel,
                "diesel_without_tax_eur_per_liter_pct_change": fuel,
            }
        )
        if omit_index is not None:
            frame = frame.drop(index=omit_index)
        frame.to_csv(self.input_file, index=False)

    def test_identifies_two_week_transmission(self):
        results, summary = self.analyzer.analyze(
            self.input_file, lags=(0, 1, 2, 3)
        )
        diesel = results[
            (results["product"] == "DIESEL")
            & (results["tax_basis"] == "WITH_TAX")
        ]
        strongest = diesel[diesel["is_strongest_for_series"]].iloc[0]

        self.assertEqual(summary.weekly_observations, 14)
        self.assertEqual(strongest["lag_weeks"], 2)
        self.assertAlmostEqual(strongest["pearson_correlation"], 1.0)
        self.assertAlmostEqual(strongest["spearman_correlation"], 1.0)
        self.assertEqual(strongest["observations"], 12)

    def test_rejects_missing_calendar_week(self):
        self._write_panel(omit_index=4)
        with self.assertRaisesRegex(ValueError, "consecutive weekly"):
            self.analyzer.analyze(self.input_file)

    def test_rejects_negative_lag(self):
        with self.assertRaisesRegex(ValueError, "negative"):
            self.analyzer.analyze(self.input_file, lags=(-1,))

    def test_exports_iso_dates(self):
        results, _ = self.analyzer.analyze(self.input_file, lags=(2,))
        output = self.analyzer.export_csv(
            results, self.directory / "lags.csv"
        )
        exported = pd.read_csv(output)
        self.assertRegex(exported.loc[0, "first_brent_week"], r"^2025-12-29$")
        self.assertRegex(exported.loc[0, "first_fuel_date"], r"^2026-01-19$")


if __name__ == "__main__":
    unittest.main()
