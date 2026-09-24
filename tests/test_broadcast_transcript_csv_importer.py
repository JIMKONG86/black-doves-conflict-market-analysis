import tempfile
import unittest
from datetime import date
from pathlib import Path

from src.data_access.broadcast_transcript_csv_importer import (
    BroadcastTranscriptCsvImporter,
)
from src.data_access.crawler import CrawlRequest, SourceType
from src.models.media_source_definition import MediaSourceDefinition


class TestBroadcastTranscriptCsvImporter(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary_directory.name)
        self.definition = MediaSourceDefinition(
            source_id="DE_TV_TEST",
            publisher_country_code="DE",
            publisher="Test broadcaster",
            source_name="Test programme transcripts",
            source_layer="TELEVISION",
            medium="TV_TRANSCRIPT",
            delivery_method="TRANSCRIPT_CSV",
            primary_language="de",
            publication_timezone="Europe/Berlin",
            verification_role="MEDIA_REPORTING",
            integration_status="TEST",
        )

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_imports_and_filters_auditable_transcript_rows(self):
        path = self.directory / "transcripts.csv"
        path.write_text(
            "published_at,programme,title,transcript,url,presenter\n"
            "2026-03-01T20:00:00+01:00,Evening News,Conflict update,"
            "The report discusses an attack and peace talks.,"
            "https://example.com/1,Presenter A\n"
            "2026-09-01T20:00:00+02:00,Evening News,Later item,Outside window,"
            "https://example.com/2,Presenter B\n",
            encoding="utf-8",
        )
        importer = BroadcastTranscriptCsvImporter(self.definition, path)

        results = importer.collect(
            CrawlRequest(
                query="peace talks",
                start_date=date(2026, 1, 1),
                end_date=date(2026, 8, 18),
                include_undated=False,
            )
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].source_type, SourceType.FILE)
        self.assertEqual(results[0].source_id, "DE_TV_TEST")
        self.assertIn("Programme: Evening News", results[0].content)
        self.assertIsNotNone(results[0].content_hash)


if __name__ == "__main__":
    unittest.main()
