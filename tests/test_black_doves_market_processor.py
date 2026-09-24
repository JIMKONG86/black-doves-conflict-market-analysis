import tempfile
import unittest

from pathlib import Path

import pandas as pd

from src.services.black_doves_market_processor import (
    compare_market_returns_with_baseline,
    prepare_market_comparison_csv,
)


class TestBlackDovesMarketProcessor(
    unittest.TestCase
):
    @staticmethod
    def _company_data():
        return pd.DataFrame(
            {
                "Date": [
                    "2025-01-02",
                    "2025-01-03",
                    "2025-01-06",
                ],
                "Adj Close": [100.0, 110.0, 104.5],
            }
        )

    @staticmethod
    def _benchmark_data():
        return pd.DataFrame(
            {
                "Date": [
                    "2025-01-02",
                    "2025-01-03",
                    "2025-01-06",
                ],
                "Adj Close": [100.0, 102.0, 103.02],
            }
        )

    def test_starts_both_cumulative_series_at_zero(self):
        result = compare_market_returns_with_baseline(
            self._company_data(),
            self._benchmark_data(),
        )

        self.assertEqual(result.loc[0, "company_return"], 0)
        self.assertEqual(
            result.loc[0, "benchmark_return"],
            0,
        )
        self.assertEqual(
            result.loc[0, "company_cumulative_return"],
            0,
        )
        self.assertEqual(
            result.loc[0, "cumulative_abnormal_return"],
            0,
        )

    def test_calculates_returns_and_abnormal_return(self):
        result = compare_market_returns_with_baseline(
            self._company_data(),
            self._benchmark_data(),
        )

        self.assertAlmostEqual(
            result.loc[1, "company_return"],
            0.10,
        )
        self.assertAlmostEqual(
            result.loc[1, "benchmark_return"],
            0.02,
        )
        self.assertAlmostEqual(
            result.loc[1, "abnormal_return"],
            0.08,
        )
        self.assertAlmostEqual(
            result.loc[2, "company_cumulative_return"],
            0.045,
        )
        self.assertAlmostEqual(
            result.loc[2, "cumulative_abnormal_return"],
            0.02,
        )

    def test_uses_only_shared_trading_dates(self):
        benchmark = self._benchmark_data().iloc[1:].copy()

        result = compare_market_returns_with_baseline(
            self._company_data(),
            benchmark,
        )

        self.assertEqual(len(result), 2)
        self.assertEqual(
            result.loc[0, "Date"].date().isoformat(),
            "2025-01-03",
        )
        self.assertEqual(result.loc[0, "company_return"], 0)

    def test_rejects_duplicate_dates(self):
        company = pd.concat(
            [
                self._company_data(),
                self._company_data().iloc[[0]],
            ],
            ignore_index=True,
        )

        with self.assertRaisesRegex(
            ValueError,
            "duplicate dates",
        ):
            compare_market_returns_with_baseline(
                company,
                self._benchmark_data(),
            )

    def test_writes_processed_csv(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            company_file = directory / "company.csv"
            benchmark_file = directory / "benchmark.csv"
            output_file = directory / "comparison.csv"
            self._company_data().to_csv(
                company_file,
                index=False,
            )
            self._benchmark_data().to_csv(
                benchmark_file,
                index=False,
            )

            data, path = prepare_market_comparison_csv(
                company_file,
                benchmark_file,
                output_file,
            )

            self.assertEqual(path, output_file)
            self.assertEqual(len(data), 3)
            exported = pd.read_csv(output_file)
            self.assertEqual(
                exported.loc[0, "company_return"],
                0,
            )


if __name__ == "__main__":
    unittest.main()
