import csv
import tempfile
import unittest
from pathlib import Path

from src.visualize_casualty_damage import create_casualty_damage_chart


class TestCasualtyDamageVisualization(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary_directory.name)
        self.estimates_file = self.directory / "estimates.csv"
        rows = [
            {
                "estimate_id": "CDE-001",
                "actor_or_country": "Iran",
                "reporting_party": "Iran",
                "reporting_party_relationship": "SELF",
                "military_killed": "",
                "civilian_killed": "",
                "unclassified_killed": 100,
                "total_killed": 100,
                "total_injured": 500,
                "facilities_or_equipment_damaged_destroyed": "",
                "damage_description": "Self-reported total.",
                "as_of_note": "test",
                "source_name": "Test source",
                "source_url": "https://example.com",
                "verification_status": "SELF_OR_ADVERSARY_REPORTED_NOT_INDEPENDENTLY_VERIFIED",
                "notes": "",
            },
            {
                "estimate_id": "CDE-002",
                "actor_or_country": "Iran",
                "reporting_party": "United States and Israel",
                "reporting_party_relationship": "ADVERSARY",
                "military_killed": 300,
                "civilian_killed": "",
                "unclassified_killed": 0,
                "total_killed": 300,
                "total_injured": 900,
                "facilities_or_equipment_damaged_destroyed": 5,
                "damage_description": "Adversary-reported military figure.",
                "as_of_note": "test",
                "source_name": "Test source",
                "source_url": "https://example.com",
                "verification_status": "SELF_OR_ADVERSARY_REPORTED_NOT_INDEPENDENTLY_VERIFIED",
                "notes": "",
            },
        ]
        with self.estimates_file.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_creates_chart_with_party_comparison_and_caveat(self):
        output = self.directory / "casualty_damage.html"

        result_path, row_count = create_casualty_damage_chart(
            estimates_file=self.estimates_file,
            output_path=output,
        )

        self.assertTrue(result_path.exists())
        self.assertEqual(row_count, 2)

        html = result_path.read_text(encoding="utf-8")
        self.assertIn(
            "Party-reported estimates, not independently verified", html
        )
        self.assertIn("Self-reported", html)
        self.assertIn("Reported by an adversary", html)
        self.assertIn("300", html)

    def test_rejects_non_html_output_path(self):
        with self.assertRaises(ValueError):
            create_casualty_damage_chart(
                estimates_file=self.estimates_file,
                output_path=self.directory / "chart.png",
            )

    def test_rejects_missing_required_columns(self):
        broken_file = self.directory / "broken.csv"
        with broken_file.open("w", encoding="utf-8") as file:
            file.write("actor_or_country\nIran\n")

        with self.assertRaises(ValueError):
            create_casualty_damage_chart(
                estimates_file=broken_file,
                output_path=self.directory / "chart.html",
            )

    def test_rejects_negative_total_killed(self):
        rows = list(csv.DictReader(self.estimates_file.open(encoding="utf-8")))
        rows[0]["total_killed"] = "-5"
        with self.estimates_file.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

        with self.assertRaises(ValueError):
            create_casualty_damage_chart(
                estimates_file=self.estimates_file,
                output_path=self.directory / "chart.html",
            )


if __name__ == "__main__":
    unittest.main()
