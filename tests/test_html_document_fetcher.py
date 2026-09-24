import unittest
from types import SimpleNamespace
from unittest.mock import patch

from src.data_access.crawler import CrawlResult, RetrievalStatus, SourceType
from src.data_access.html_document_fetcher import HtmlDocumentFetcher


class TestHtmlDocumentFetcher(unittest.TestCase):

    @patch("src.data_access.html_document_fetcher.requests.get")
    def test_extracts_article_and_canonical_url(self, mock_get):
        html = b"""
        <html><head><link rel="canonical" href="https://example.gov/final"></head>
        <body><nav>Navigation</nav><article><h1>Release</h1><p>Verified text.</p></article></body>
        </html>
        """
        response = SimpleNamespace(
            content=html,
            text=html.decode("utf-8"),
            status_code=200,
            headers={"Content-Type": "text/html; charset=utf-8"},
            url="https://example.gov/redirected",
            raise_for_status=lambda: None,
        )
        mock_get.return_value = response
        result = CrawlResult(
            source_name="Example ministry",
            source_type=SourceType.RSS,
            url="https://example.gov/release",
            content="Feed summary",
        )

        fetched = HtmlDocumentFetcher().fetch(result)

        self.assertEqual(fetched.retrieval_status, RetrievalStatus.SUCCESS)
        self.assertEqual(fetched.canonical_url, "https://example.gov/final")
        self.assertIn("Verified text.", fetched.content)
        self.assertNotIn("Navigation", fetched.content)

    @patch("src.data_access.html_document_fetcher.requests.get")
    def test_uses_largest_semantic_content_container(self, mock_get):
        full_text = " ".join(["Complete ministry article"] * 80)
        html = f"""
        <html><body>
          <article>Short teaser only.</article>
          <main><h1>Release</h1><p>{full_text}</p></main>
        </body></html>
        """.encode("utf-8")
        response = SimpleNamespace(
            content=html,
            text=html.decode("utf-8"),
            status_code=200,
            headers={"Content-Type": "text/html; charset=utf-8"},
            url="https://example.gov/release",
            raise_for_status=lambda: None,
        )
        mock_get.return_value = response
        result = CrawlResult(
            source_name="Example ministry",
            source_type=SourceType.RSS,
            url="https://example.gov/release",
            content="Feed summary",
        )

        fetched = HtmlDocumentFetcher().fetch(result)

        self.assertGreater(len(fetched.content), 1_000)
        self.assertIn("Complete ministry article", fetched.content)
        self.assertNotIn("Short teaser only", fetched.content)

    @patch("src.data_access.html_document_fetcher.requests.get")
    def test_preserves_main_nested_in_malformed_header(self, mock_get):
        html = b"""
        <html><body><form><header>
          <nav>Navigation</nav>
          <main><h1>Official statement</h1><p>Primary evidence text.</p></main>
        </header></form></body></html>
        """
        response = SimpleNamespace(
            content=html,
            text=html.decode("utf-8"),
            status_code=200,
            headers={"Content-Type": "text/html; charset=utf-8"},
            url="https://example.gov/statement",
            raise_for_status=lambda: None,
        )
        mock_get.return_value = response
        result = CrawlResult(
            source_name="Example ministry",
            source_type=SourceType.HTML,
            url="https://example.gov/statement",
        )

        fetched = HtmlDocumentFetcher().fetch(result)

        self.assertEqual(fetched.retrieval_status, RetrievalStatus.SUCCESS)
        self.assertIn("Primary evidence text.", fetched.content)
        self.assertNotIn("Navigation", fetched.content)

    @patch("src.data_access.html_document_fetcher.requests.get")
    def test_extracts_centcom_style_article_body(self, mock_get):
        html = b"""
        <html><body><form><header>
          <nav>Navigation</nav>
          <div class="article-view">
            <div class="article-body">
              <h1>U.S. Successfully Completes New Strikes in Iran</h1>
              <div itemprop="articleBody">
                CENTCOM completed its latest wave of strikes.
              </div>
            </div>
          </div>
        </header></form></body></html>
        """
        response = SimpleNamespace(
            content=html,
            text=html.decode("utf-8"),
            status_code=200,
            headers={"Content-Type": "text/html; charset=utf-8"},
            url="https://www.centcom.mil/release",
            raise_for_status=lambda: None,
        )
        mock_get.return_value = response
        result = CrawlResult(
            source_name="CENTCOM public releases",
            source_type=SourceType.HTML,
            url="https://www.centcom.mil/release",
        )

        fetched = HtmlDocumentFetcher().fetch(result)

        self.assertEqual(fetched.retrieval_status, RetrievalStatus.SUCCESS)
        self.assertIn("latest wave of strikes", fetched.content)
        self.assertNotIn("Navigation", fetched.content)


if __name__ == "__main__":
    unittest.main()
