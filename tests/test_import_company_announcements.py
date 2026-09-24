import csv
import tempfile
import unittest

from pathlib import Path

from src.import_company_announcements import merge_company_announcements


class TestImportCompanyAnnouncements(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary_directory.name)
        self.universe = self.directory / "companies.csv"
        self.input_file = self.directory / "input.csv"
        self.registry = self.directory / "registry.csv"
        self._write_csv(
            self.universe,
            [
                ["company_id", "company_name", "market_data_ticker"],
                ["CMP001", "Alpha Defence", "ALP"],
            ],
        )

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_merges_and_autofills_company_metadata_and_id(self):
        self._write_import()

        result = merge_company_announcements(
            self.input_file,
            self.registry,
            self.universe,
        )

        self.assertEqual(result["added_rows"], 1)
        with self.registry.open("r", encoding="utf-8", newline="") as file:
            rows = list(csv.DictReader(file))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["company_name"], "Alpha Defence")
        self.assertEqual(rows[0]["market_data_ticker"], "ALP")
        self.assertEqual(len(rows[0]["announcement_id"]), 64)

    def test_repeat_import_is_idempotent(self):
        self._write_import()

        merge_company_announcements(self.input_file, self.registry, self.universe)
        result = merge_company_announcements(
            self.input_file,
            self.registry,
            self.universe,
        )

        self.assertEqual(result["added_rows"], 0)
        self.assertEqual(result["registry_rows"], 1)

    def test_rejects_unknown_company(self):
        self._write_import(company_id="CMP999")

        with self.assertRaisesRegex(ValueError, "Unknown company_id"):
            merge_company_announcements(
                self.input_file,
                self.registry,
                self.universe,
            )

    def _write_import(self, company_id="CMP001"):
        self._write_csv(
            self.input_file,
            [
                [
                    "announcement_date",
                    "company_id",
                    "announcement_type",
                    "title",
                    "source_name",
                    "source_url",
                    "verification_status",
                    "coverage_status",
                    "record_scope",
                ],
                [
                    "2026-03-10",
                    company_id,
                    "order_award",
                    "Verified order",
                    "Company release",
                    "https://example.com/order",
                    "primary_source_confirmed",
                    "PARTIAL_CURATED",
                    "PROCUREMENT",
                ],
            ],
        )

    @staticmethod
    def _write_csv(path, rows):
        with path.open("w", encoding="utf-8", newline="") as file:
            csv.writer(file).writerows(rows)


if __name__ == "__main__":
    unittest.main()
