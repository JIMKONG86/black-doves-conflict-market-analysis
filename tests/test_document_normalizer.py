import unittest
from hashlib import sha256

from src.data_access.crawler import (
    CrawlResult,
    RetrievalStatus,
    SourceType,
)
from src.models.normalized_document import (
    NormalizedDocument,
)
from src.services.document_normalizer import (
    DocumentNormalizer,
)


class TestDocumentNormalizer(unittest.TestCase):

    def setUp(self):
        self.normalizer = DocumentNormalizer()

    def create_result(
        self,
        content=(
            "Government\tcontract\r\n\r\n\r\n"
            "awarded."
        ),
        retrieval_status=RetrievalStatus.SUCCESS,
    ):
        return CrawlResult(
            source_name=" Example source ",
            source_type=SourceType.HTML,
            url="https://example.com/document",
            canonical_url=(
                "https://example.com/document"
            ),
            query=" government contract ",
            title=" Example   document ",
            publisher=" Example publisher ",
            language="en",
            content=content,
            retrieval_status=retrieval_status,
        )

    def test_returns_normalized_document(self):
        crawl_result = self.create_result()

        result = self.normalizer.normalize(
            crawl_result
        )

        self.assertIsInstance(
            result,
            NormalizedDocument,
        )
        self.assertEqual(
            result.source_name,
            "Example source",
        )
        self.assertEqual(
            result.query,
            "government contract",
        )
        self.assertEqual(
            result.title,
            "Example document",
        )

    def test_normalizes_document_content(self):
        crawl_result = self.create_result(
            content=(
                "\u00a0Government\tcontract"
                "\r\n\r\n\r\nawarded. "
                "\ufb01nance"
            )
        )

        result = self.normalizer.normalize(
            crawl_result
        )

        expected_content = (
            "Government contract\n\n"
            "awarded. finance"
        )

        self.assertEqual(
            result.content,
            expected_content,
        )

    def test_calculates_document_statistics(self):
        crawl_result = self.create_result(
            content="Government contract awarded."
        )

        result = self.normalizer.normalize(
            crawl_result
        )

        expected_hash = sha256(
            result.content.encode("utf-8")
        ).hexdigest()

        self.assertEqual(result.word_count, 3)
        self.assertEqual(
            result.character_count,
            len(result.content),
        )
        self.assertEqual(
            result.normalized_content_hash,
            expected_hash,
        )
        self.assertEqual(
            result.raw_content_hash,
            crawl_result.content_hash,
        )

    def test_rejects_unsuccessful_result(self):
        crawl_result = self.create_result(
            content=None,
            retrieval_status=RetrievalStatus.ERROR,
        )

        with self.assertRaises(ValueError):
            self.normalizer.normalize(crawl_result)

    def test_rejects_empty_content(self):
        crawl_result = self.create_result(
            content="   "
        )

        with self.assertRaises(ValueError):
            self.normalizer.normalize(crawl_result)


if __name__ == "__main__":
    unittest.main()