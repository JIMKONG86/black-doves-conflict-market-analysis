import tempfile
import unittest

from datetime import date, datetime, timezone
from pathlib import Path

from src.data_access.procurement_event_reader import (
    ProcurementEventReader,
)
from src.models.procurement_event import (
    ProcurementEvent,
    ProcurementEventType,
    ProcurementVerificationStatus,
)


class TestProcurementEvent(unittest.TestCase):
    @staticmethod
    def _values(**overrides):
        values = {
            "announcement_date": date(2025, 1, 15),
            "company_name": " Rheinmetall AG ",
            "company_ticker": "RHM.DE",
            "buyer_name": "Italian Army",
            "buyer_country_code": "it",
            "event_type": ProcurementEventType.ORDER_AWARD,
            "title": "Italy orders Skynex",
            "systems": ("Skynex",),
            "source_name": "Rheinmetall AG",
            "source_url": "https://www.rheinmetall.com/news",
            "contract_value_eur": 73_000_000,
            "aggregate_package_value_eur": None,
            "value_description": "EUR 73m awarded",
            "is_air_defence": True,
            "verification_status": (
                ProcurementVerificationStatus.PRIMARY_SOURCE_CONFIRMED
            ),
            "related_initiative": None,
            "reviewed_by": "Markus",
            "notes": None,
        }
        values.update(overrides)
        return values

    def test_normalizes_values_and_marks_exact_value(self):
        event = ProcurementEvent(**self._values())

        self.assertEqual(event.company_name, "Rheinmetall AG")
        self.assertEqual(event.buyer_country_code, "IT")
        self.assertEqual(event.contract_value_eur, 73_000_000.0)
        self.assertTrue(event.has_exact_contract_value)
        self.assertEqual(len(event.event_id), 64)

    def test_identifier_is_independent_of_review_metadata(self):
        first = ProcurementEvent(
            **self._values(
                reviewed_by="Reviewer A",
                created_at=datetime(2025, 1, 16, tzinfo=timezone.utc),
            )
        )
        second = ProcurementEvent(
            **self._values(
                reviewed_by="Reviewer B",
                created_at=datetime(2026, 1, 16, tzinfo=timezone.utc),
            )
        )

        self.assertEqual(first.event_id, second.event_id)

    def test_identifier_changes_with_source_fact(self):
        first = ProcurementEvent(**self._values())
        second = ProcurementEvent(
            **self._values(contract_value_eur=74_000_000)
        )

        self.assertNotEqual(first.event_id, second.event_id)

    def test_rejects_invalid_source_url(self):
        with self.assertRaisesRegex(ValueError, "absolute HTTP"):
            ProcurementEvent(
                **self._values(source_url="rheinmetall.com/news")
            )

    def test_rejects_invalid_country_code(self):
        with self.assertRaisesRegex(ValueError, "two-letter ISO"):
            ProcurementEvent(
                **self._values(buyer_country_code="Italy")
            )

    def test_rejects_naive_created_at(self):
        with self.assertRaisesRegex(ValueError, "timezone-aware"):
            ProcurementEvent(
                **self._values(created_at=datetime(2025, 1, 15))
            )

    def test_rejects_duplicate_systems(self):
        with self.assertRaisesRegex(ValueError, "duplicates"):
            ProcurementEvent(
                **self._values(systems=("Skynex", "Skynex"))
            )

    def test_rejects_systems_as_one_string(self):
        with self.assertRaisesRegex(TypeError, "iterable of strings"):
            ProcurementEvent(**self._values(systems="Skynex"))


class TestProcurementEventReader(unittest.TestCase):
    HEADER = (
        "announcement_date,company_name,company_ticker,buyer_name,"
        "buyer_country_code,event_type,title,systems,source_name,"
        "source_url,contract_value_eur,aggregate_package_value_eur,"
        "value_description,is_air_defence,related_initiative,"
        "verification_status,reviewed_by,notes\n"
    )
    ROW = (
        "2025-01-15,Rheinmetall AG,RHM.DE,Italian Army,IT,"
        "order_award,Italy orders Skynex,Skynex|Radar,Rheinmetall AG,"
        "https://www.rheinmetall.com/news,73000000,,EUR 73m,true,,"
        "primary_source_confirmed,Markus,Primary source\n"
    )

    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary_directory.name)
        self.input_file = self.directory / "events.csv"
        self.reader = ProcurementEventReader()

    def tearDown(self):
        self.temporary_directory.cleanup()

    def _write(self, content):
        self.input_file.write_text(content, encoding="utf-8")

    def test_reads_procurement_event(self):
        self._write(self.HEADER + self.ROW)

        events = self.reader.read(self.input_file)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].systems, ("Skynex", "Radar"))
        self.assertEqual(
            events[0].event_type,
            ProcurementEventType.ORDER_AWARD,
        )

    def test_rejects_duplicate_event(self):
        self._write(self.HEADER + self.ROW + self.ROW)

        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.reader.read(self.input_file)

    def test_reports_invalid_row_number(self):
        invalid = self.ROW.replace("2025-01-15", "15.01.2025")
        self._write(self.HEADER + invalid)

        with self.assertRaisesRegex(ValueError, "row 2"):
            self.reader.read(self.input_file)

    def test_rejects_missing_header(self):
        self._write("announcement_date,title\n2025-01-15,Order\n")

        with self.assertRaisesRegex(ValueError, "missing required"):
            self.reader.read(self.input_file)


if __name__ == "__main__":
    unittest.main()
