import json
import tempfile
import unittest
from datetime import datetime, timezone
from hashlib import sha256

from src.data_access.normalized_document_repository import (
    NormalizedDocumentRepository,
)
from src.models.normalized_document import (
    NormalizedDocument,
)


class TestNormalizedDocumentRepository(
    unittest.TestCase
):

    def setUp(self):
        self.temporary_directory = (
            tempfile.TemporaryDirectory()
        )
        self.addCleanup(
            self.temporary_directory.cleanup
        )

        self.repository = (
            NormalizedDocumentRepository(
                directory=(
                    self.temporary_directory.name
                )
            )
        )

    def create_document(
        self,
        content="Normalized document content",
    ):
        normalized_hash = sha256(
            content.encode("utf-8")
        ).hexdigest()

        return NormalizedDocument(
            document_id="example-document-id",
            source_name="Example source",
            source_type="rss",
            url="https://example.com/document.pdf",
            canonical_url=(
                "https://example.com/document.pdf"
            ),
            query="government contract",
            title="Example document",
            publisher="Example publisher",
            author=None,
            published_at=None,
            language="en",
            content=content,
            raw_content_hash="raw-content-hash",
            normalized_content_hash=(
                normalized_hash
            ),
            word_count=len(content.split()),
            character_count=len(content),
            retrieved_at=datetime(
                2026,
                8,
                25,
                tzinfo=timezone.utc,
            ),
        )

    def test_saves_normalized_document(self):
        normalized_document = (
            self.create_document()
        )

        file_path = self.repository.save(
            normalized_document
        )

        self.assertTrue(file_path.exists())
        self.assertEqual(file_path.suffix, ".json")

        with file_path.open(
            "r",
            encoding="utf-8",
        ) as input_file:
            stored_document = json.load(
                input_file
            )

        self.assertEqual(
            stored_document["document_id"],
            "example-document-id",
        )
        self.assertEqual(
            stored_document["content"],
            "Normalized document content",
        )
        self.assertEqual(
            stored_document[
                "normalized_content_hash"
            ],
            normalized_document
            .normalized_content_hash,
        )

    def test_recognizes_existing_document(self):
        normalized_document = (
            self.create_document()
        )

        self.repository.save(
            normalized_document
        )

        self.assertTrue(
            self.repository.contains(
                normalized_document
            )
        )

    def test_does_not_overwrite_by_default(self):
        original_document = self.create_document(
            content="Original normalized content"
        )
        updated_document = self.create_document(
            content="Updated normalized content"
        )

        file_path = self.repository.save(
            original_document
        )

        self.repository.save(
            updated_document
        )

        with file_path.open(
            "r",
            encoding="utf-8",
        ) as input_file:
            stored_document = json.load(
                input_file
            )

        self.assertEqual(
            stored_document["content"],
            "Original normalized content",
        )

    def test_overwrites_existing_document(self):
        original_document = self.create_document(
            content="Original normalized content"
        )
        updated_document = self.create_document(
            content="Updated normalized content"
        )

        file_path = self.repository.save(
            original_document
        )

        self.repository.save(
            updated_document,
            overwrite=True,
        )

        with file_path.open(
            "r",
            encoding="utf-8",
        ) as input_file:
            stored_document = json.load(
                input_file
            )

        self.assertEqual(
            stored_document["content"],
            "Updated normalized content",
        )
        self.assertEqual(
            stored_document[
                "normalized_content_hash"
            ],
            updated_document
            .normalized_content_hash,
        )


if __name__ == "__main__":
    unittest.main()