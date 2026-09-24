import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from src.data_access.crawler import (
    CrawlRequest,
    RetrievalStatus,
    SourceType,
)
from src.data_access.rss_source_adapter import (
    RssSourceAdapter,
)


class TestRssSourceAdapter(unittest.TestCase):

    def setUp(self):
        self.adapter = RssSourceAdapter(
            source_name="Example News",
            feed_url=(
                "https://example.com/feed.xml"
            ),
        )

    @patch(
        "src.data_access.rss_source_adapter."
        "feedparser.parse"
    )
    def test_returns_matching_entry(
        self,
        mock_parse,
    ):
        mock_parse.return_value = SimpleNamespace(
            bozo=False,
            entries=[
                {
                    "title": (
                        "Government signs "
                        "defense contract"
                    ),
                    "summary": (
                        "<p>A company received "
                        "the contract.</p>"
                    ),
                    "link": (
                        "https://example.com/article"
                    ),
                    "published_parsed": time.gmtime(
                        1767225600
                    ),
                },
                {
                    "title": "European heatwave",
                    "summary": (
                        "High temperatures continue."
                    ),
                    "link": (
                        "https://example.com/weather"
                    ),
                },
            ],
            feed={
                "title": "Example News",
                "language": "en",
            },
        )

        request = CrawlRequest(
            query="defense contract"
        )

        results = self.adapter.collect(request)

        self.assertEqual(len(results), 1)
        self.assertEqual(
            results[0].source_type,
            SourceType.RSS,
        )
        self.assertEqual(
            results[0].retrieval_status,
            RetrievalStatus.SUCCESS,
        )
        self.assertEqual(
            results[0].title,
            "Government signs defense contract",
        )
        self.assertEqual(
            results[0].content,
            "A company received the contract.",
        )

    @patch(
        "src.data_access.rss_source_adapter."
        "feedparser.parse"
    )
    def test_returns_error_result(
        self,
        mock_parse,
    ):
        mock_parse.side_effect = RuntimeError(
            "Feed unavailable"
        )

        results = self.adapter.collect(
            CrawlRequest(query="contract")
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(
            results[0].retrieval_status,
            RetrievalStatus.ERROR,
        )
        self.assertEqual(
            results[0].error_message,
            "Feed unavailable",
        )

    @patch(
        "src.data_access.rss_source_adapter."
        "feedparser.parse"
    )
    def test_excludes_undated_entries_for_bounded_collection(
        self,
        mock_parse,
    ):
        mock_parse.return_value = SimpleNamespace(
            bozo=False,
            entries=[{
                "title": "Undated contract",
                "summary": "Contract notice",
                "link": "https://example.com/undated",
            }],
            feed={"title": "Example News"},
        )

        results = self.adapter.collect(
            CrawlRequest(
                query="contract",
                include_undated=False,
            )
        )

        self.assertEqual(results, [])


if __name__ == "__main__":
    unittest.main()
