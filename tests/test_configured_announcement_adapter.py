import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from src.data_access.configured_announcement_adapter import (
    ConfiguredAnnouncementAdapter,
)
from src.data_access.crawler import CrawlRequest, CrawlResult, SourceType
from src.data_access.source_registry import SourceRegistry


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class FakeHtmlFetcher:

    def __init__(self, content):
        self.content = content
        self.requested_urls = []

    def fetch(self, result):
        self.requested_urls.append(result.url)
        return CrawlResult(
            source_id=result.source_id,
            source_country_code=result.source_country_code,
            source_name=result.source_name,
            source_type=SourceType.HTML,
            url=result.url,
            canonical_url=result.canonical_url,
            query=result.query,
            title=result.title,
            publisher=result.publisher,
            published_at=result.published_at,
            publication_timezone=result.publication_timezone,
            date_precision=result.date_precision,
            jurisdiction=result.jurisdiction,
            language=result.language,
            content=self.content,
        )


class TestConfiguredAnnouncementAdapter(unittest.TestCase):

    def setUp(self):
        registry = SourceRegistry.from_json(
            PROJECT_ROOT / "config" / "country_sources.json"
        )
        self.us_definition = registry.get("US_DOD_CONTRACTS")

    @patch(
        "src.data_access.configured_announcement_adapter."
        "RssSourceAdapter.collect"
    )
    def test_us_adapter_retains_country_metadata(self, mock_collect):
        mock_collect.return_value = [self.create_us_result()]
        adapter = ConfiguredAnnouncementAdapter(
            self.us_definition,
            html_fetcher=FakeHtmlFetcher("Full official contract text"),
        )

        results = adapter.collect(CrawlRequest(query="*"))

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].source_id, "US_DOD_CONTRACTS")
        self.assertEqual(results[0].source_country_code, "US")
        self.assertEqual(
            results[0].publication_timezone,
            "America/New_York",
        )

    @patch(
        "src.data_access.configured_announcement_adapter."
        "RssSourceAdapter.collect"
    )
    def test_us_discovery_mode_does_not_fetch_blocked_detail_page(self, mock_collect):
        mock_collect.return_value = [self.create_us_result()]
        fetcher = FakeHtmlFetcher(
            "Lockheed Martin received an official contract award."
        )
        adapter = ConfiguredAnnouncementAdapter(
            self.us_definition,
            html_fetcher=fetcher,
        )

        results = adapter.collect(CrawlRequest(query="*", max_results=5))

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].content, "Feed summary")
        self.assertEqual(fetcher.requested_urls, [])

    @patch(
        "src.data_access.configured_announcement_adapter."
        "RssSourceAdapter.collect"
    )
    def test_detail_capability_flag_is_applied_even_when_fetch_requested(
        self,
        mock_collect,
    ):
        discovered = self.create_us_result()
        mock_collect.return_value = [discovered]
        fetcher = FakeHtmlFetcher("Full official contract text")
        adapter = ConfiguredAnnouncementAdapter(
            self.us_definition,
            html_fetcher=fetcher,
        )

        results = adapter.collect(CrawlRequest(query="*"))

        self.assertEqual(fetcher.requested_urls, [])
        self.assertEqual(results[0].url, discovered.url)
        self.assertEqual(
            results[0].canonical_url,
            discovered.canonical_url,
        )

    @patch(
        "src.data_access.configured_announcement_adapter."
        "RssSourceAdapter.collect"
    )
    def test_discovery_query_is_forwarded_to_rss_adapter(self, mock_collect):
        mock_collect.return_value = [self.create_us_result()]
        adapter = ConfiguredAnnouncementAdapter(
            self.us_definition,
            html_fetcher=FakeHtmlFetcher("Unrelated contract award."),
        )

        results = adapter.collect(CrawlRequest(query="Lockheed Martin"))

        self.assertEqual(len(results), 1)
        discovery_request = mock_collect.call_args.args[0]
        self.assertEqual(discovery_request.query, "Lockheed Martin")

    def create_us_result(self):
        return CrawlResult(
            source_id="US_DOD_CONTRACTS",
            source_country_code="US",
            source_name="Daily defense contracts",
            source_type=SourceType.RSS,
            url=(
                "https://www.war.gov/News/Contracts/Contract/Article/"
                "4594054/contracts-for-sept-9-2026/"
            ),
            canonical_url=(
                "https://www.war.gov/News/Contracts/Contract/Article/"
                "4594054/contracts-for-sept-9-2026/"
            ),
            title="Contracts for Sept. 9, 2026",
            publisher="U.S. Department of War",
            published_at=datetime(2026, 9, 9, tzinfo=timezone.utc),
            publication_timezone="America/New_York",
            date_precision="datetime",
            jurisdiction="United States",
            language="en",
            content="Feed summary",
        )


if __name__ == "__main__":
    unittest.main()
