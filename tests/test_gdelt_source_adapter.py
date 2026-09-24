import unittest
from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from src.data_access.crawler import CrawlRequest, RetrievalStatus, SourceType
from src.data_access.gdelt_source_adapter import GdeltSourceAdapter


def _response(payload, status_code=200):
    return SimpleNamespace(
        status_code=status_code,
        json=lambda: payload,
        raise_for_status=lambda: None,
    )


class TestGdeltSourceAdapter(unittest.TestCase):
    def setUp(self):
        self.adapter = GdeltSourceAdapter(source_id="GDELT_GLOBAL")

    @patch("src.data_access.gdelt_source_adapter.requests.get")
    def test_parses_articles_into_crawl_results(self, mock_get):
        mock_get.return_value = _response(
            {
                "articles": [
                    {
                        "url": "https://news.cgtn.com/example",
                        "title": "China urges ceasefire",
                        "seendate": "20260323T201900Z",
                        "domain": "news.cgtn.com",
                        "language": "English",
                        "sourcecountry": "China",
                    },
                    {
                        "url": "https://www.presstv.ir/example",
                        "title": "Iran statement",
                        "seendate": "20260826T000000Z",
                        "domain": "presstv.ir",
                        "language": "English",
                        "sourcecountry": "Iran",
                    },
                ]
            }
        )
        request = CrawlRequest(
            query="Iran Israel conflict",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 8, 18),
        )

        results = self.adapter.collect(request)

        self.assertEqual(len(results), 2)
        first, second = results
        self.assertEqual(first.retrieval_status, RetrievalStatus.SUCCESS)
        self.assertEqual(first.source_type, SourceType.API)
        self.assertEqual(first.url, "https://news.cgtn.com/example")
        self.assertEqual(first.source_country_code, "CN")
        self.assertEqual(
            first.published_at,
            datetime(2026, 3, 23, 20, 19, 0, tzinfo=timezone.utc),
        )
        self.assertEqual(second.source_country_code, "IR")

    @patch("src.data_access.gdelt_source_adapter.requests.get")
    def test_builds_country_and_date_range_query_params(self, mock_get):
        mock_get.return_value = _response({"articles": []})
        request = CrawlRequest(
            query="defence contractor",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 8, 18),
            jurisdiction="IR",
            max_results=10,
        )

        self.adapter.collect(request)

        _, kwargs = mock_get.call_args
        params = kwargs["params"]
        self.assertIn('sourcecountry:"Iran"', params["query"])
        self.assertEqual(params["startdatetime"], "20260101000000")
        self.assertEqual(params["enddatetime"], "20260818235959")
        self.assertEqual(params["maxrecords"], 10)
        self.assertEqual(params["format"], "json")

    @patch("src.data_access.gdelt_source_adapter.requests.get")
    def test_caps_maxrecords_at_api_limit(self, mock_get):
        mock_get.return_value = _response({"articles": []})
        request = CrawlRequest(query="*", max_results=10_000)

        self.adapter.collect(request)

        _, kwargs = mock_get.call_args
        self.assertEqual(kwargs["params"]["maxrecords"], 250)

    @patch("src.data_access.gdelt_source_adapter.requests.get")
    def test_returns_empty_status_when_no_articles(self, mock_get):
        mock_get.return_value = _response({"articles": []})
        request = CrawlRequest(query="a very specific query with no hits")

        results = self.adapter.collect(request)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].retrieval_status, RetrievalStatus.EMPTY)

    @patch("src.data_access.gdelt_source_adapter.requests.get")
    def test_returns_error_status_on_request_failure(self, mock_get):
        mock_get.side_effect = ConnectionError("network unreachable")
        request = CrawlRequest(query="Iran Israel conflict")

        results = self.adapter.collect(request)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].retrieval_status, RetrievalStatus.ERROR)
        self.assertIn("network unreachable", results[0].error_message)

    @patch("src.data_access.gdelt_source_adapter.requests.get")
    def test_skips_articles_without_a_url(self, mock_get):
        mock_get.return_value = _response(
            {
                "articles": [
                    {"title": "No URL here", "sourcecountry": "Germany"},
                    {
                        "url": "https://www.zdf.de/example",
                        "title": "Has a URL",
                        "sourcecountry": "Germany",
                        "seendate": "20260825T090000Z",
                    },
                ]
            }
        )
        request = CrawlRequest(query="*")

        results = self.adapter.collect(request)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].url, "https://www.zdf.de/example")

    @patch("src.data_access.gdelt_source_adapter.requests.get")
    def test_unmapped_source_country_leaves_code_unset(self, mock_get):
        mock_get.return_value = _response(
            {
                "articles": [
                    {
                        "url": "https://example.com/a",
                        "title": "Somewhere else",
                        "sourcecountry": "Brazil",
                    }
                ]
            }
        )
        request = CrawlRequest(query="*")

        results = self.adapter.collect(request)

        self.assertIsNone(results[0].source_country_code)

    def test_rejects_blank_source_name(self):
        with self.assertRaises(ValueError):
            GdeltSourceAdapter(source_name="   ")

    def test_rejects_non_positive_timeout(self):
        with self.assertRaises(ValueError):
            GdeltSourceAdapter(timeout=0)


if __name__ == "__main__":
    unittest.main()
