import csv
import tempfile
import unittest
from pathlib import Path

from src.visualize_media_positioning import create_media_positioning_chart


class TestMediaPositioningVisualization(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary_directory.name)
        self.document_file = self.directory / "documents.csv"
        rows = [
            {
                "document_id": "doc-1",
                "published_at": "2026-03-23T20:19:00+08:00",
                "country_code": "CN",
                "target_country_codes": "",
                "source_id": "CN_CGTN_TRANSCRIPT_SECTION",
                "publisher": "CGTN",
                "source_layer": "TELEVISION",
                "broadcaster_control": "STATE_CONTROLLED",
                "company_ids": "",
                "medium": "TV_TRANSCRIPT",
                "title": "China urges ceasefire",
                "content": "Paraphrased summary.",
                "url": "https://news.cgtn.com/example",
                "categories": "DIPLOMACY_MEDIATION_DEESCALATION",
                "framing_codes": "DE_ESCALATION",
                "classification_status": "AUTO_SUGGESTED",
                "verification_status": "PARTIALLY_VERIFIED",
                "reviewer": "",
                "reviewed_at": "",
            },
            {
                "document_id": "doc-2",
                "published_at": "2026-08-26T00:00:00+03:30",
                "country_code": "IR",
                "target_country_codes": "",
                "source_id": "IR_PRESSTV_RSS",
                "publisher": "Press TV",
                "source_layer": "NEWS",
                "broadcaster_control": "STATE_CONTROLLED",
                "company_ids": "",
                "medium": "ONLINE_NEWS",
                "title": "Doctrine shift",
                "content": "Paraphrased summary.",
                "url": "https://www.presstv.co.uk/example",
                "categories": "MILITARY_OPERATIONS_SECURITY",
                "framing_codes": "ESCALATION",
                "classification_status": "AUTO_SUGGESTED",
                "verification_status": "PARTIALLY_VERIFIED",
                "reviewer": "",
                "reviewed_at": "",
            },
            {
                "document_id": "doc-3",
                "published_at": "2026-09-13T00:00:00-04:00",
                "country_code": "US",
                "target_country_codes": "IR",
                "source_id": "US_CBS_NEWS_RSS",
                "publisher": "CBS News",
                "source_layer": "NEWS",
                "broadcaster_control": "PRIVATE_INDEPENDENT",
                "company_ids": "CMP027",
                "medium": "ONLINE_NEWS",
                "title": "Missile crisis coverage",
                "content": "Paraphrased summary.",
                "url": "https://www.cbsnews.com/example",
                "categories": "PROCUREMENT_MILITARY_CAPABILITY",
                "framing_codes": "",
                "classification_status": "AUTO_SUGGESTED",
                "verification_status": "PARTIALLY_VERIFIED",
                "reviewer": "",
                "reviewed_at": "",
            },
        ]
        with self.document_file.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_creates_chart_with_pilot_sample_caveat_and_company_linkage(self):
        output = self.directory / "media_positioning.html"

        result_path, total_documents, media_documents = (
            create_media_positioning_chart(
                document_file=self.document_file,
                output_path=output,
            )
        )

        self.assertTrue(result_path.exists())
        self.assertEqual(total_documents, 3)
        self.assertEqual(media_documents, 3)

        html = result_path.read_text(encoding="utf-8")
        self.assertIn("Pilot sample, not a comprehensive media corpus", html)
        self.assertIn("STATE_CONTROLLED", html)
        self.assertIn("CMP027", html)
        self.assertIn("Linked companies", html)

    def test_rejects_non_html_output_path(self):
        with self.assertRaises(ValueError):
            create_media_positioning_chart(
                document_file=self.document_file,
                output_path=self.directory / "chart.png",
            )

    def test_handles_missing_broadcaster_control_as_unknown(self):
        rows = list(csv.DictReader(self.document_file.open(encoding="utf-8")))
        for row in rows:
            row["broadcaster_control"] = ""
        with self.document_file.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

        output = self.directory / "media_positioning.html"
        result_path, total_documents, _ = create_media_positioning_chart(
            document_file=self.document_file,
            output_path=output,
        )

        html = result_path.read_text(encoding="utf-8")
        self.assertEqual(total_documents, 3)
        self.assertIn("Control type not documented", html)


if __name__ == "__main__":
    unittest.main()
