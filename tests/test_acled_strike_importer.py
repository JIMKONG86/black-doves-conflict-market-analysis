import tempfile
import unittest

from pathlib import Path

from src.data_access.acled_strike_importer import (
    AcledStrikeImporter,
)
from src.models.claim_observation import (
    CountryRole,
    SourceChannel,
)
from src.models.strike_observation import (
    StrikeType,
)


CSV_HEADER = (
    "event_id_cnty,event_date,event_type,"
    "sub_event_type,actor1,actor2,country,"
    "admin1,location,source,notes,timestamp\n"
)


class MemoryClaimRepository:
    def __init__(self):
        self.items = []

    def contains(self, claim_id):
        return any(
            claim.claim_id == claim_id
            for claim in self.items
        )

    def save(self, claim):
        if self.contains(claim.claim_id):
            raise ValueError(
                "Claim observation already exists"
            )

        self.items.append(claim)


class MemoryStrikeRepository:
    def __init__(self):
        self.items = []

    def contains(self, strike_id):
        return any(
            strike.strike_id == strike_id
            for strike in self.items
        )

    def save(self, strike):
        if self.contains(strike.strike_id):
            raise ValueError(
                "Strike observation already exists"
            )

        self.items.append(strike)


class TestAcledStrikeImporter(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = (
            tempfile.TemporaryDirectory()
        )
        self.claim_repository = (
            MemoryClaimRepository()
        )
        self.strike_repository = (
            MemoryStrikeRepository()
        )
        self.importer = AcledStrikeImporter(
            claim_repository=(
                self.claim_repository
            ),
            strike_repository=(
                self.strike_repository
            ),
        )

    def tearDown(self):
        self.temporary_directory.cleanup()

    def _write_csv(self, content):
        file_path = Path(
            self.temporary_directory.name
        ) / "acled.csv"
        file_path.write_text(
            content,
            encoding="utf-8",
        )
        return file_path

    def test_imports_strikes_and_skips_other_events(
        self,
    ):
        file_path = self._write_csv(
            CSV_HEADER
            + (
                "IRN1,2026-09-03,Explosions/Remote "
                "violence,Air/drone strike,Military "
                "Forces,Military Forces,Iran,Tehran,"
                "Tehran,Example source,Authorities "
                "reported a drone strike,1788451200\n"
            )
            + (
                "IRN2,2026-09-03,Protests,Peaceful "
                "protest,Protesters,,Iran,Tehran,"
                "Tehran,Example source,Peaceful "
                "demonstration,1788451200\n"
            )
            + (
                "IRN3,2026-09-03,Explosions/Remote "
                "violence,Shelling/artillery/missile "
                "attack,Military Forces,Military "
                "Forces,Iran,Khuzestan,Ahvaz,Example "
                "source,Artillery shelling was "
                "reported,1788451200\n"
            )
        )

        summary = self.importer.import_csv(
            file_path=file_path,
            reviewed_by="Markus",
            source_url=(
                "https://acleddata.com/"
                "api-documentation/acled-endpoint"
            ),
            affected_country_code="IR",
        )

        self.assertEqual(summary.total_rows, 3)
        self.assertEqual(summary.strike_rows, 2)
        self.assertEqual(summary.saved_strikes, 2)
        self.assertEqual(summary.duplicate_strikes, 0)
        self.assertEqual(summary.skipped_non_strikes, 1)
        self.assertEqual(summary.failed_rows, 0)
        self.assertEqual(
            len(self.claim_repository.items),
            2,
        )
        self.assertEqual(
            len(self.strike_repository.items),
            2,
        )

        drone_strike = self.strike_repository.items[0]
        artillery_strike = (
            self.strike_repository.items[1]
        )

        self.assertEqual(
            drone_strike.strike_type,
            StrikeType.DRONE_STRIKE,
        )
        self.assertEqual(
            drone_strike.weapon_system,
            "Drone/UAV",
        )
        self.assertEqual(
            artillery_strike.strike_type,
            StrikeType.ARTILLERY_STRIKE,
        )
        self.assertEqual(
            drone_strike.source_channel,
            SourceChannel.NGO,
        )

        affected_links = [
            link
            for link in (
                self.claim_repository
                .items[0]
                .country_links
            )
            if link.role == CountryRole.AFFECTED
        ]
        self.assertEqual(
            affected_links[0].country_code,
            "IR",
        )

    def test_repeated_import_is_idempotent(self):
        file_path = self._write_csv(
            CSV_HEADER
            + (
                "IRN1,2026-09-03,Explosions/Remote "
                "violence,Air/drone strike,Military "
                "Forces,,Iran,Tehran,Tehran,Example "
                "source,A drone strike was reported,"
                "1788451200\n"
            )
        )
        arguments = {
            "file_path": file_path,
            "reviewed_by": "Markus",
            "source_url": "https://acleddata.com/",
            "affected_country_code": "IR",
        }

        first = self.importer.import_csv(**arguments)
        second = self.importer.import_csv(**arguments)

        self.assertEqual(first.saved_strikes, 1)
        self.assertEqual(second.saved_strikes, 0)
        self.assertEqual(second.duplicate_strikes, 1)
        self.assertEqual(
            len(self.claim_repository.items),
            1,
        )
        self.assertEqual(
            len(self.strike_repository.items),
            1,
        )

    def test_uses_country_codes_from_csv(self):
        file_path = self._write_csv(
            CSV_HEADER.replace(
                "timestamp",
                "timestamp,affected_country_code,"
                "initiator_country_code",
            )
            + (
                "UKR1,2026-09-03,Explosions/Remote "
                "violence,Shelling/artillery/missile "
                "attack,Military Forces,,Ukraine,"
                "Kyiv,Kyiv,Example source,A missile "
                "strike was reported,1788451200,UA,RU\n"
            )
        )

        summary = self.importer.import_csv(
            file_path=file_path,
            reviewed_by="Markus",
            source_url="https://acleddata.com/",
        )

        self.assertEqual(summary.saved_strikes, 1)
        strike = self.strike_repository.items[0]
        self.assertEqual(
            strike.strike_type,
            StrikeType.MISSILE_STRIKE,
        )
        self.assertEqual(
            strike.affected_country_code,
            "UA",
        )
        self.assertEqual(
            strike.initiator_country_code,
            "RU",
        )

    def test_reports_invalid_event_date(self):
        file_path = self._write_csv(
            CSV_HEADER
            + (
                "IRN1,03.09.2026,Explosions/Remote "
                "violence,Air/drone strike,Military "
                "Forces,,Iran,Tehran,Tehran,Example "
                "source,A drone strike was reported,"
                "1788451200\n"
            )
        )

        summary = self.importer.import_csv(
            file_path=file_path,
            reviewed_by="Markus",
            source_url="https://acleddata.com/",
            affected_country_code="IR",
        )

        self.assertEqual(summary.saved_strikes, 0)
        self.assertEqual(summary.failed_rows, 1)
        self.assertIn(
            "YYYY-MM-DD",
            summary.issues[0].message,
        )

    def test_rejects_missing_required_header(self):
        file_path = self._write_csv(
            "event_id_cnty,event_date,notes\n"
        )

        with self.assertRaisesRegex(
            ValueError,
            "sub_event_type",
        ):
            self.importer.import_csv(
                file_path=file_path,
                reviewed_by="Markus",
                source_url="https://acleddata.com/",
                affected_country_code="IR",
            )


if __name__ == "__main__":
    unittest.main()