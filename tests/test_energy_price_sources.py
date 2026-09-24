import tempfile
import unittest

from pathlib import Path
from unittest.mock import Mock

import pandas as pd

from src.data_access.energy_price_sources import EnergyPriceSourceProcessor


class TestEnergyPriceSourceProcessor(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary_directory.name)
        self.brent_file = self.directory / "brent.xlsx"
        self.fuel_file = self.directory / "fuels.xlsx"
        self.processor = EnergyPriceSourceProcessor()
        self._write_brent()
        self._write_fuels()

    def tearDown(self):
        self.temporary_directory.cleanup()

    def _write_brent(self):
        rows = [
            ["Data 1: Europe Brent Spot Price", None],
            ["Sourcekey", "RBRTE"],
            ["Date", "Europe Brent Spot Price"],
        ]
        dates = pd.date_range("2025-12-29", "2026-01-16", freq="B")
        rows.extend(
            [[value, 60.0 + index] for index, value in enumerate(dates)]
        )
        with pd.ExcelWriter(self.brent_file, engine="openpyxl") as writer:
            pd.DataFrame(rows).to_excel(
                writer, sheet_name="Data 1", header=False, index=False
            )

    def _write_fuels(self):
        dates = pd.date_range("2026-01-05", periods=2, freq="7D")
        definitions = {
            "Prices with taxes": (
                "Consumer prices of petroleum products inclusive of duties and taxes",
                "DE_price_with_tax_euro95",
                "DE_price_with_tax_diesel",
                [1800, 1818],
                [1700, 1734],
            ),
            "Prices wo taxes": (
                "Consumer prices of petroleum products net of duties and taxes",
                "DE_price_wo_tax_euro95",
                "DE_price_wo_tax_diesel",
                [900, 909],
                [1000, 1020],
            ),
        }
        with pd.ExcelWriter(self.fuel_file, engine="openpyxl") as writer:
            for sheet, values in definitions.items():
                date_header, petrol_header, diesel_header, petrol, diesel = values
                rows = [
                    [date_header, petrol_header, diesel_header],
                    [None, "Euro-super 95", "Dieselkraftstoff"],
                    ["Date", "1000 l", "1000 l"],
                ]
                rows.extend(
                    [
                        [date_value, petrol[index], diesel[index]]
                        for index, date_value in enumerate(dates)
                    ]
                )
                pd.DataFrame(rows).to_excel(
                    writer, sheet_name=sheet, header=False, index=False
                )

    def test_parses_units_and_aligns_prior_brent_week(self):
        timeline, weekly, summary = self.processor.collect(
            self.brent_file,
            self.fuel_file,
            "2026-01-01",
            "2026-01-12",
        )

        self.assertEqual(summary.fuel_weekly_rows, 2)
        self.assertEqual(summary.aligned_weekly_rows, 2)
        self.assertEqual(
            weekly.loc[0, "brent_week_start"].date().isoformat(),
            "2025-12-29",
        )
        self.assertAlmostEqual(
            weekly.loc[0, "petrol_with_tax_eur_per_liter"], 1.8
        )
        self.assertAlmostEqual(
            weekly.loc[1, "diesel_with_tax_eur_per_liter_pct_change"],
            0.02,
        )
        first_petrol = timeline[
            timeline["series_id"] == "PETROL_WITH_TAX"
        ].iloc[0]
        self.assertEqual(first_petrol["unit"], "EUR/litre")
        self.assertEqual(first_petrol["indexed_value"], 100.0)

    def test_rejects_reversed_date_range(self):
        with self.assertRaisesRegex(ValueError, "must not be after"):
            self.processor.collect(
                self.brent_file,
                self.fuel_file,
                "2026-02-01",
                "2026-01-01",
            )

    def test_download_skips_existing_file(self):
        destination = self.directory / "source.xls"
        destination.write_bytes(b"existing")
        session = Mock()

        path, status = self.processor.download(
            "https://example.test/source.xls",
            destination,
            session=session,
        )

        self.assertEqual(path, destination)
        self.assertEqual(status, "SKIPPED_EXISTING")
        session.get.assert_not_called()


if __name__ == "__main__":
    unittest.main()
