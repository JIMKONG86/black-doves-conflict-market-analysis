import tempfile
import unittest

from pathlib import Path

from src.data_access.centcom_strike_importer import CentcomStrikeImporter
from src.models.claim_observation import ClaimStatus, CountryRole, SourceChannel
from src.models.strike_observation import StrikeType


CSV_HEADER = (
    "source_release_id,event_date,publication_date,initiator_country_code,"
    "affected_country_code,strike_type,operation_day_count,"
    "verification_status,include_in_core_series,counting_unit,title,location,"
    "weapon_system,description,source_id,source_url\n"
)


class MemoryRepository:
    def __init__(self, identifier_name):
        self.identifier_name = identifier_name
        self.items = []

    def contains(self, identifier):
        return any(
            getattr(item, self.identifier_name) == identifier
            for item in self.items
        )

    def save(self, item):
        self.items.append(item)


class TestCentcomStrikeImporter(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.claims = MemoryRepository("candidate_id")
        self.strikes = MemoryRepository("strike_id")
        self.importer = CentcomStrikeImporter(self.claims, self.strikes)

    def tearDown(self):
        self.temporary_directory.cleanup()

    def _write(self, rows):
        path = Path(self.temporary_directory.name) / "centcom.csv"
        path.write_text(CSV_HEADER + rows, encoding="utf-8")
        return path

    @staticmethod
    def _row(status="CONFIRMED", event_date="2026-07-16"):
        return (
            f"4548433,{event_date},2026-07-16,US,IR,other,1,{status},true,"
            "official_release_confirmed_operation_day,U.S. completes strikes,"
            "Iran,Precision munitions,Confirmed strikes against military "
            "targets,US_CENTCOM_PUBLIC_RELEASES,https://www.centcom.mil/"
            "MEDIA/PUBLIC-RELEASES/Article/4548433/example/\n"
        )

    def test_imports_confirmed_government_strike_with_roles(self):
        summary = self.importer.import_csv(
            self._write(self._row()), reviewed_by="Markus"
        )

        self.assertEqual(summary.saved_strikes, 1)
        self.assertEqual(summary.failed_rows, 0)
        strike = self.strikes.items[0]
        self.assertEqual(strike.claim_status, ClaimStatus.CONFIRMED)
        self.assertEqual(strike.source_channel, SourceChannel.GOVERNMENT)
        self.assertEqual(strike.strike_type, StrikeType.OTHER)
        self.assertEqual(strike.initiator_country_code, "US")
        self.assertEqual(strike.affected_country_code, "IR")
        roles = {
            (link.country_code, link.role)
            for link in self.claims.items[0].country_links
        }
        self.assertIn(("US", CountryRole.INITIATOR), roles)
        self.assertIn(("IR", CountryRole.AFFECTED), roles)

    def test_skips_unconfirmed_candidate(self):
        summary = self.importer.import_csv(
            self._write(self._row(status="PENDING")), reviewed_by="Markus"
        )

        self.assertEqual(summary.skipped_unconfirmed, 1)
        self.assertEqual(summary.saved_strikes, 0)

    def test_repeated_import_is_idempotent(self):
        path = self._write(self._row())
        first = self.importer.import_csv(path, reviewed_by="Markus")
        second = self.importer.import_csv(path, reviewed_by="Markus")

        self.assertEqual(first.saved_strikes, 1)
        self.assertEqual(second.duplicate_strikes, 1)
        self.assertEqual(len(self.strikes.items), 1)

    def test_rejects_duplicate_operation_day_for_same_country(self):
        summary = self.importer.import_csv(
            self._write(self._row() + self._row()), reviewed_by="Markus"
        )

        self.assertEqual(summary.saved_strikes, 1)
        self.assertEqual(summary.failed_rows, 1)
        self.assertIn("duplicate", summary.issues[0].message)

    def test_rejects_event_after_publication(self):
        summary = self.importer.import_csv(
            self._write(self._row(event_date="2026-07-17")),
            reviewed_by="Markus",
        )

        self.assertEqual(summary.saved_strikes, 0)
        self.assertEqual(summary.failed_rows, 1)
        self.assertIn("publication_date", summary.issues[0].message)


if __name__ == "__main__":
    unittest.main()
