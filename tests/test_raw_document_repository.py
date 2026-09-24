import json
import tempfile
import unittest
from pathlib import Path

from src.data_access.crawler import (
    CrawlResult,
    RetrievalStatus,
    SourceType,
)
from src.data_access.raw_document_repository import (
    RawDocumentRepository,
)


class TestRawDocumentRepository(unittest.TestCase):

    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)

        self.repository = RawDocumentRepository(
            directory=self.temporary_directory.name
        )

    def create_result(
        self,
        content="Original document content",
    ):
        return CrawlResult(
            source_name="Example source",
            source_type=SourceType.HTML,
            url="https://example.com/document",
            canonical_url="https://example.com/document",
            query="government contract",
            title="Example document",
            publisher="Example publisher",
            language="en",
            content=content,
            retrieval_status=RetrievalStatus.SUCCESS,
        )

    def test_saves_result_as_json(self):
        crawl_result = self.create_result()

        file_path = self.repository.save(crawl_result)

        self.assertTrue(file_path.exists())
        self.assertEqual(file_path.suffix, ".json")

        with file_path.open(
            "r",
            encoding="utf-8",
        ) as input_file:
            stored_document = json.load(input_file)

        self.assertEqual(
            stored_document["source_name"],
            "Example source",
        )
        self.assertEqual(
            stored_document["source_type"],
            "html",
        )
        self.assertEqual(
            stored_document["url"],
            "https://example.com/document",
        )
        self.assertEqual(
            stored_document["content"],
            "Original document content",
        )
        self.assertEqual(
            stored_document["content_hash"],
            crawl_result.content_hash,
        )
        self.assertEqual(
            stored_document["retrieval_status"],
            "success",
        )

    def test_recognizes_existing_document(self):
        crawl_result = self.create_result()

        self.repository.save(crawl_result)

        self.assertTrue(
            self.repository.contains(crawl_result)
        )

    def test_does_not_replace_existing_document_by_default(self):
        original_result = self.create_result(
            content="Original document content"
        )
        updated_result = self.create_result(
            content="Updated document content"
        )

        original_path = self.repository.save(
            original_result
        )
        second_path = self.repository.save(
            updated_result
        )

        self.assertEqual(original_path, second_path)

        with original_path.open(
            "r",
            encoding="utf-8",
        ) as input_file:
            stored_document = json.load(input_file)

        self.assertEqual(
            stored_document["content"],
            "Original document content",
        )
        self.assertEqual(
            stored_document["content_hash"],
            original_result.content_hash,
        )

    def test_overwrites_existing_document(self):
        original_result = self.create_result(
            content="Original document content"
        )
        updated_result = self.create_result(
            content="Updated PDF document content"
        )

        original_path = self.repository.save(
            original_result
        )
        updated_path = self.repository.save(
            updated_result,
            overwrite=True,
        )

        self.assertEqual(original_path, updated_path)

        with updated_path.open(
            "r",
            encoding="utf-8",
        ) as input_file:
            stored_document = json.load(input_file)

        self.assertEqual(
            stored_document["content"],
            "Updated PDF document content",
        )
        self.assertEqual(
            stored_document["content_hash"],
            updated_result.content_hash,
        )
        self.assertNotEqual(
            original_result.content_hash,
            updated_result.content_hash,
        )


if __name__ == "__main__":
    unittest.main()