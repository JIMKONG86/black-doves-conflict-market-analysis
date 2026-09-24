import tempfile
import unittest

from src.data_access.crawler import CrawlResult, SourceType
from src.data_access.versioned_raw_document_repository import (
    VersionedRawDocumentRepository,
)


class TestVersionedRawDocumentRepository(unittest.TestCase):

    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.repository = VersionedRawDocumentRepository(
            self.temporary_directory.name
        )

    @staticmethod
    def create_result(content):
        return CrawlResult(
            source_id="DE_BMVG_NEWS",
            source_country_code="DE",
            source_name="BMVg press and media releases",
            source_type=SourceType.HTML,
            url="https://example.gov/release/1",
            canonical_url="https://example.gov/release/1",
            content=content,
            publication_timezone="Europe/Berlin",
            jurisdiction="Germany",
        )

    def test_saves_retrievals_as_separate_versions(self):
        first = self.create_result("Initial release")
        second = self.create_result("Corrected release")

        first_path = self.repository.save(first)
        second_path = self.repository.save(second)

        self.assertNotEqual(first_path, second_path)
        self.assertEqual(len(self.repository.versions(first)), 2)
        self.assertIn("DE_BMVG_NEWS", str(first_path))


if __name__ == "__main__":
    unittest.main()
