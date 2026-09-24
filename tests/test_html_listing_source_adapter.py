import unittest
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from src.data_access.crawler import CrawlRequest, RetrievalStatus
from src.data_access.html_listing_source_adapter import (
    HtmlListingSourceAdapter,
)
from src.data_access.source_registry import SourceRegistry


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class TestHtmlListingSourceAdapter(unittest.TestCase):

    def setUp(self):
        self.registry = SourceRegistry.from_json(
            PROJECT_ROOT / "config" / "country_sources.json"
        )

    @patch("src.data_access.html_listing_source_adapter.requests.get")
    def test_discovers_israel_release_with_local_date(self, mock_get):
        mock_get.return_value = self.response("""
        <html><body><main>
          <section class="card">
            <time>16/8/2026</time>
            <h3>Israel and Honduras Sign Memorandum of Understanding</h3>
            <a href="/en/press-releases/press-room/israel-honduras">Read More</a>
          </section>
        </main></body></html>
        """)
        adapter = HtmlListingSourceAdapter(
            self.registry.get("IL_IMOD_PRESS")
        )

        results = adapter.collect(CrawlRequest(query="*"))

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].source_country_code, "IL")
        self.assertEqual(results[0].published_at.date(), date(2026, 8, 16))
        self.assertEqual(
            results[0].title,
            "Israel and Honduras Sign Memorandum of Understanding",
        )
        self.assertEqual(results[0].publication_timezone, "Asia/Jerusalem")

    @patch("src.data_access.html_listing_source_adapter.requests.get")
    def test_uses_numbered_china_archive_pages(self, mock_get):
        first_page = self.response("""
        <html><body><ul><li>
          <h3><a href="/news/202609/11/content_current.html">Current story</a></h3>
          <span>2026/09/11</span>
        </li></ul></body></html>
        """)
        second_page = self.response("""
        <html><body><ul><li>
          <h3><a href="/news/202608/20/content_energy.html">Energy cooperation policy</a></h3>
          <span>2026/08/20</span>
        </li></ul></body></html>
        """)
        mock_get.side_effect = [first_page, second_page]
        adapter = HtmlListingSourceAdapter(
            self.registry.get("CN_STATE_COUNCIL")
        )

        results = adapter.collect(CrawlRequest(
            query="*",
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 31),
            max_results=1,
            include_undated=False,
        ))

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "Energy cooperation policy")
        self.assertEqual(results[0].published_at.date(), date(2026, 8, 20))
        self.assertEqual(
            mock_get.call_args_list[1].args[0],
            "https://english.www.gov.cn/news/page_2.html",
        )

    @patch("src.data_access.html_listing_source_adapter.requests.get")
    def test_discovers_iran_statement_and_rejects_external_link(self, mock_get):
        mock_get.return_value = self.response("""
        <html><body><main>
          <article>
            <h2><a href="/portal/newsview/794103/official-mfa-statement">Official MFA statement</a></h2>
            <p>2026/09/09</p>
          </article>
          <article>
            <h2><a href="https://example.com/portal/newsview/1">External copy</a></h2>
            <p>2026/09/09</p>
          </article>
        </main></body></html>
        """)
        adapter = HtmlListingSourceAdapter(
            self.registry.get("IR_MFA_STATEMENTS")
        )

        results = adapter.collect(CrawlRequest(query="*"))

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].source_country_code, "IR")
        self.assertEqual(results[0].title, "Official MFA statement")
        self.assertEqual(results[0].publication_timezone, "Asia/Tehran")
        self.assertEqual(
            results[0].url,
            "https://en.mfa.gov.ir/portal/newsview/794103",
        )

    @patch("src.data_access.html_listing_source_adapter.requests.get")
    def test_discovers_centcom_release_with_english_month_date(self, mock_get):
        mock_get.return_value = self.response("""
        <html><body><article>
          <time>July 16, 2026</time>
          <h3><a href="/MEDIA/PUBLIC-RELEASES/Article/4548433/example/">
            U.S. Successfully Completes New Strikes in Iran
          </a></h3>
        </article></body></html>
        """)
        adapter = HtmlListingSourceAdapter(
            self.registry.get("US_CENTCOM_PUBLIC_RELEASES")
        )

        results = adapter.collect(CrawlRequest(
            query="*",
            start_date=date(2026, 7, 16),
            end_date=date(2026, 7, 16),
            include_undated=False,
        ))

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].source_country_code, "US")
        self.assertEqual(results[0].published_at.date(), date(2026, 7, 16))
        self.assertEqual(
            results[0].url,
            "https://www.centcom.mil/MEDIA/PUBLIC-RELEASES/"
            "Article/4548433/example/",
        )

    def test_parses_abbreviated_centcom_date(self):
        adapter = HtmlListingSourceAdapter(
            self.registry.get("US_CENTCOM_PUBLIC_RELEASES")
        )

        parsed = adapter._parse_date("Public Releases | Feb. 28, 2026")

        self.assertEqual(parsed.date(), date(2026, 2, 28))

    @patch("src.data_access.html_listing_source_adapter.requests.get")
    def test_excludes_undated_item_from_bounded_run(self, mock_get):
        mock_get.return_value = self.response("""
        <html><body><article>
          <h2><a href="/portal/newsview/794103">Undated statement</a></h2>
        </article></body></html>
        """)
        adapter = HtmlListingSourceAdapter(
            self.registry.get("IR_MFA_STATEMENTS")
        )

        results = adapter.collect(CrawlRequest(
            query="*",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 8, 31),
            include_undated=False,
        ))

        self.assertEqual(results, [])

    @patch("src.data_access.html_listing_source_adapter.requests.get")
    def test_reports_listing_http_error(self, mock_get):
        import requests

        mock_get.side_effect = requests.RequestException("Source unavailable")
        adapter = HtmlListingSourceAdapter(
            self.registry.get("IL_IMOD_PRESS")
        )

        results = adapter.collect(CrawlRequest(query="*"))

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].retrieval_status, RetrievalStatus.ERROR)
        self.assertEqual(results[0].error_message, "Source unavailable")

    @staticmethod
    def response(html):
        body = html.encode("utf-8")
        return SimpleNamespace(
            content=body,
            text=html,
            status_code=200,
            headers={"Content-Type": "text/html; charset=utf-8"},
            raise_for_status=lambda: None,
        )


if __name__ == "__main__":
    unittest.main()
