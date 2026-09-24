import csv
import json
import tempfile
import unittest
from pathlib import Path

from src.services.narrative_corpus_builder import NarrativeCorpusBuilder


class TestNarrativeCorpusBuilder(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.announcements = self.root / "announcements"
        document_dir = self.announcements / "IL_SOURCE" / "doc-1"
        document_dir.mkdir(parents=True)
        (document_dir / "v1.json").write_text(
            json.dumps(
                {
                    "document_id": "doc-1",
                    "source_id": "IL_SOURCE",
                    "source_country_code": "IL",
                    "source_name": "Official releases",
                    "publisher": "Ministry",
                    "title": "Defence procurement test",
                    "content": "A new weapon system was acquired.",
                    "url": "https://example.gov/1",
                    "canonical_url": "https://example.gov/1",
                    "published_at": "2026-08-05T00:00:00+03:00",
                    "retrieval_status": "success",
                }
            ),
            encoding="utf-8",
        )
        self.media = self.root / "media"
        self.registry = self.root / "media_sources.json"
        self.registry.write_text(
            json.dumps({"sources": []}), encoding="utf-8"
        )
        self.centcom = self.root / "centcom.csv"
        with self.centcom.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=[
                    "source_release_id",
                    "publication_date",
                    "include_in_core_series",
                    "title",
                    "description",
                    "affected_country_code",
                    "source_url",
                ],
            )
            writer.writeheader()
            writer.writerows(
                [
                    {
                        "source_release_id": "100",
                        "publication_date": "2026-03-01",
                        "include_in_core_series": "true",
                        "title": "U.S. completes strikes",
                        "description": "First operation day",
                        "affected_country_code": "IR",
                        "source_url": "https://example.mil/100",
                    },
                    {
                        "source_release_id": "100",
                        "publication_date": "2026-03-01",
                        "include_in_core_series": "true",
                        "title": "U.S. completes strikes",
                        "description": "Second operation day",
                        "affected_country_code": "IR",
                        "source_url": "https://example.mil/100",
                    },
                ]
            )

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_builds_deduplicated_state_corpus_and_visible_media_gaps(self):
        builder = NarrativeCorpusBuilder()
        documents = builder.build(
            "2026-01-01",
            "2026-08-18",
            self.announcements,
            self.media,
            self.registry,
            self.centcom,
        )
        coverage = {
            row["source_layer"]: row
            for row in builder.coverage_records(documents)
        }

        self.assertEqual(len(documents), 2)
        self.assertEqual(coverage["STATE_ORGAN"]["document_count"], 2)
        self.assertEqual(coverage["NEWS"]["coverage_status"], "MISSING")
        self.assertEqual(coverage["TELEVISION"]["coverage_status"], "MISSING")
        centcom = next(item for item in documents if item.document_id == "CENTCOM-100")
        self.assertIn("First operation day", centcom.content)
        self.assertIn("Second operation day", centcom.content)
        self.assertEqual(centcom.classification_status, "AUTO_SUGGESTED")

    def test_state_organ_documents_are_tagged_state_controlled(self):
        builder = NarrativeCorpusBuilder()
        documents = builder.build(
            "2026-01-01",
            "2026-08-18",
            self.announcements,
            self.media,
            self.registry,
            self.centcom,
        )
        state_document = next(
            item for item in documents if item.document_id == "doc-1"
        )

        self.assertEqual(state_document.broadcaster_control, "STATE_CONTROLLED")

    def test_media_documents_inherit_broadcaster_control_and_keep_company_ids(self):
        self.registry.write_text(
            json.dumps(
                {
                    "sources": [
                        {
                            "source_id": "CN_CGTN_TRANSCRIPTS",
                            "publisher_country_code": "CN",
                            "publisher": "CGTN",
                            "source_name": "CGTN transcript section",
                            "source_layer": "TELEVISION",
                            "medium": "TV_TRANSCRIPT",
                            "delivery_method": "HTML",
                            "primary_language": "en",
                            "publication_timezone": "Asia/Shanghai",
                            "verification_role": "MEDIA_REPORTING",
                            "integration_status": "CONNECTOR_READY",
                            "entrypoint_url": "https://news.cgtn.com/",
                            "active": True,
                            "broadcaster_control": "STATE_CONTROLLED",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        media_document_dir = self.media / "CN_CGTN_TRANSCRIPTS" / "doc-2"
        media_document_dir.mkdir(parents=True)
        (media_document_dir / "v1.json").write_text(
            json.dumps(
                {
                    "document_id": "doc-2",
                    "source_id": "CN_CGTN_TRANSCRIPTS",
                    "title": "Segment about a defence contractor",
                    "content": "Paraphrased summary of the segment.",
                    "url": "https://news.cgtn.com/segment",
                    "canonical_url": "https://news.cgtn.com/segment",
                    "published_at": "2026-06-01T00:00:00+08:00",
                    "retrieval_status": "success",
                    "company_ids": ["cmp032", "cmp032"],
                }
            ),
            encoding="utf-8",
        )

        builder = NarrativeCorpusBuilder()
        documents = builder.build(
            "2026-01-01",
            "2026-08-18",
            self.announcements,
            self.media,
            self.registry,
            self.centcom,
        )
        media_document = next(
            item for item in documents if item.document_id == "doc-2"
        )

        self.assertEqual(media_document.source_layer, "TELEVISION")
        self.assertEqual(media_document.broadcaster_control, "STATE_CONTROLLED")
        self.assertEqual(media_document.company_ids, ("CMP032",))


if __name__ == "__main__":
    unittest.main()
