import logging
from dataclasses import replace
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

from src.data_access.crawler import CrawlResult, RetrievalStatus


logger = logging.getLogger(__name__)


class HtmlDocumentFetcher:
    """Downloads an official detail page and extracts its readable text."""

    def __init__(self, timeout=30, max_file_size=5_000_000):
        if timeout <= 0:
            raise ValueError("timeout must be greater than zero")
        if max_file_size <= 0:
            raise ValueError("max_file_size must be greater than zero")

        self.timeout = timeout
        self.max_file_size = max_file_size

    def fetch(self, crawl_result):
        if not isinstance(crawl_result, CrawlResult):
            raise TypeError("crawl_result must be a CrawlResult")

        try:
            response = requests.get(
                crawl_result.url,
                timeout=self.timeout,
                headers={
                    "User-Agent": (
                        "ConflictMarketAnalysis/0.2 "
                        "AcademicResearchCrawler"
                    )
                },
            )
            response.raise_for_status()

            if len(response.content) > self.max_file_size:
                return self._error(
                    crawl_result,
                    response.status_code,
                    "HTML document exceeds maximum file size",
                )

            content_type = response.headers.get("Content-Type", "").casefold()
            if "html" not in content_type:
                return self._error(
                    crawl_result,
                    response.status_code,
                    "Downloaded document is not HTML",
                )

            soup = BeautifulSoup(response.text, "html.parser")
            canonical = soup.select_one('link[rel="canonical"]')
            canonical_url = (
                canonical.get("href")
                if canonical and canonical.get("href")
                else getattr(response, "url", None)
                or crawl_result.canonical_url
                or crawl_result.url
            )

            for element in soup.select(
                "script, style, noscript"
            ):
                element.decompose()

            content_candidates = soup.select(
                "main, article, [itemprop='articleBody'], .article-body"
            )
            if content_candidates:
                content_root = max(
                    content_candidates,
                    key=lambda element: len(
                        element.get_text(" ", strip=True)
                    ),
                )
                for element in content_root.select("nav, footer, header, form"):
                    element.decompose()
            else:
                for element in soup.select("nav, footer, header, form"):
                    element.decompose()
                content_root = soup.body
            extracted_text = (
                content_root.get_text("\n", strip=True)
                if content_root
                else ""
            )

            if not extracted_text:
                return replace(
                    crawl_result,
                    canonical_url=canonical_url,
                    content=None,
                    http_status=response.status_code,
                    retrieval_status=RetrievalStatus.EMPTY,
                    error_message="HTML contains no extractable text",
                    retrieved_at=datetime.now(timezone.utc),
                )

            return replace(
                crawl_result,
                canonical_url=canonical_url,
                content=extracted_text,
                http_status=response.status_code,
                retrieval_status=RetrievalStatus.SUCCESS,
                error_message=None,
                retrieved_at=datetime.now(timezone.utc),
            )

        except requests.RequestException as error:
            logger.error("HTML download failed: %s", error)
            return self._error(crawl_result, None, str(error))
        except Exception as error:
            logger.exception("HTML extraction failed")
            return self._error(crawl_result, None, str(error))

    @staticmethod
    def _error(crawl_result, http_status, error_message):
        return replace(
            crawl_result,
            content=None,
            http_status=http_status,
            retrieval_status=RetrievalStatus.ERROR,
            error_message=error_message,
            retrieved_at=datetime.now(timezone.utc),
        )
