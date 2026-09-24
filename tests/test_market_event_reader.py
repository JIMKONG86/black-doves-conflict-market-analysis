import csv
import tempfile
import unittest

from pathlib import Path

from src.data_access.market_event_reader import load_market_events


class TestMarketEventReader(unittest.TestCase):
    def test_loads_and_sorts_verified_events(self):
        rows = [
            self._row("EVT002", "2026-03-02"),
            self._row("EVT001", "2026-02-28"),
        ]

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.csv"
            self._write(path, rows)
            events = load_market_events(path)

        self.assertEqual(
            [event.event_id for event in events],
            ["EVT001", "EVT002"],
        )
        self.assertEqual(
            events[0].affected_country_codes,
            ("IR", "IL", "US"),
        )

    def test_rejects_duplicate_event_identifier(self):
        rows = [
            self._row("EVT001", "2026-02-28"),
            self._row("EVT001", "2026-03-02"),
        ]

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.csv"
            self._write(path, rows)

            with self.assertRaisesRegex(ValueError, "duplicate event_id"):
                load_market_events(path)

    def test_rejects_invalid_date(self):
        row = self._row("EVT001", "28.02.2026")

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.csv"
            self._write(path, [row])

            with self.assertRaisesRegex(ValueError, "invalid event_date"):
                load_market_events(path)

    @staticmethod
    def _row(event_id, event_date):
        return {
            "event_id": event_id,
            "event_date": event_date,
            "title": "Test event",
            "event_type": "CONFLICT_ONSET",
            "affected_country_codes": "IR|IL|US",
            "verification_status": "PRE_SPECIFIED",
            "source_name": "Test source",
            "source_url": "https://example.com/event",
            "notes": "",
        }

    @staticmethod
    def _write(path, rows):
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)


if __name__ == "__main__":
    unittest.main()
