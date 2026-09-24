import unittest
from datetime import date

from src.data_access.crawler import (
    CrawlRequest,
    CrawlResult,
    RetrievalStatus,
    SourceAdapter,
    SourceType,
)


class DummySourceAdapter(SourceAdapter):

    @property
    def source_name(self):
        return "Dummy source"

    def collect(self, request):
        return [
            CrawlResult(
                source_name=self.source_name,
                source_type=SourceType.API,
                url="https://example.com/document",
                query=request.query,
                title="Example document",
                content="Validated example content",
                retrieval_status=(
                    RetrievalStatus.SUCCESS
                ),
            )
        ]


class TestCrawlRequest(unittest.TestCase):

    def test_accepts_valid_request(self):
        request = CrawlRequest(
            query="government contract",
            start_date=date(2025, 1, 1),
            end_date=date(2026, 1, 1),
        )

        self.assertEqual(
            request.query,
            "government contract",
        )

    def test_rejects_empty_query(self):
        with self.assertRaises(ValueError):
            CrawlRequest(query="   ")

    def test_rejects_invalid_date_range(self):
        with self.assertRaises(ValueError):
            CrawlRequest(
                query="government contract",
                start_date=date(2026, 1, 1),
                end_date=date(2025, 1, 1),
            )

    def test_rejects_invalid_result_limit(self):
        with self.assertRaises(ValueError):
            CrawlRequest(
                query="government contract",
                max_results=0,
            )


class TestCrawlResult(unittest.TestCase):

    def test_creates_content_hash(self):
        result = CrawlResult(
            source_name="Example source",
            source_type=SourceType.HTML,
            url="https://example.com/article",
            content="Example article content",
        )

        self.assertIsNotNone(result.content_hash)

    def test_normalizes_content_before_hashing(self):
        first_result = CrawlResult(
            source_name="Example source",
            source_type=SourceType.HTML,
            url="https://example.com/first",
            content="Example   article\ncontent",
        )

        second_result = CrawlResult(
            source_name="Example source",
            source_type=SourceType.HTML,
            url="https://example.com/second",
            content="Example article content",
        )

        self.assertEqual(
            first_result.content_hash,
            second_result.content_hash,
        )

    def test_adapter_returns_crawl_result(self):
        adapter = DummySourceAdapter()
        request = CrawlRequest(
            query="government contract"
        )

        results = adapter.collect(request)

        self.assertEqual(len(results), 1)
        self.assertIsInstance(
            results[0],
            CrawlResult,
        )


if __name__ == "__main__":
    unittest.main()