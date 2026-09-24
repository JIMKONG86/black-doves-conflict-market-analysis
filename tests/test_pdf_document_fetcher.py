import unittest
from unittest.mock import Mock, patch

import requests

from src.data_access.crawler import (
    CrawlResult,
    RetrievalStatus,
    SourceType,
)
from src.data_access.pdf_document_fetcher import (
    PdfDocumentFetcher,
)


class TestPdfDocumentFetcher(
    unittest.TestCase
):

    def setUp(self):
        self.fetcher = PdfDocumentFetcher()

        self.crawl_result = CrawlResult(
            source_name="Deutscher Bundestag",
            source_type=SourceType.RSS,
            url=(
                "https://example.com/"
                "document.pdf"
            ),
            title="Example document",
        )

    def test_extracts_text_from_pdf(self):
        response = Mock()
        response.status_code = 200
        response.content = b"%PDF example"
        response.headers = {
            "Content-Type": "application/pdf"
        }

        page = Mock()
        page.extract_text.return_value = (
            "Extracted document text"
        )

        reader = Mock()
        reader.pages = [page]

        with patch(
            "src.data_access."
            "pdf_document_fetcher.requests.get",
            return_value=response,
        ), patch(
            "src.data_access."
            "pdf_document_fetcher.PdfReader",
            return_value=reader,
        ):
            result = self.fetcher.fetch(
                self.crawl_result
            )

        self.assertEqual(
            result.retrieval_status,
            RetrievalStatus.SUCCESS,
        )
        self.assertEqual(
            result.content,
            "Extracted document text",
        )
        self.assertIsNotNone(
            result.content_hash
        )
        self.assertEqual(
            result.http_status,
            200,
        )

    def test_handles_download_error(self):
        with patch(
            "src.data_access."
            "pdf_document_fetcher.requests.get",
            side_effect=requests.RequestException(
                "Download unavailable"
            ),
        ):
            result = self.fetcher.fetch(
                self.crawl_result
            )

        self.assertEqual(
            result.retrieval_status,
            RetrievalStatus.ERROR,
        )
        self.assertEqual(
            result.error_message,
            "Download unavailable",
        )


if __name__ == "__main__":
    unittest.main()