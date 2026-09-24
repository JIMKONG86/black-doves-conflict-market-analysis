import logging
from dataclasses import replace
from datetime import datetime, timezone
from io import BytesIO

import requests
from pypdf import PdfReader

from src.data_access.crawler import (
    CrawlResult,
    RetrievalStatus,
)


logger = logging.getLogger(__name__)


class PdfDocumentFetcher:

    def __init__(
        self,
        timeout=30,
        max_file_size=25_000_000,
    ):
        if timeout <= 0:
            raise ValueError(
                "timeout must be greater than zero"
            )

        if max_file_size <= 0:
            raise ValueError(
                "max_file_size must be greater "
                "than zero"
            )

        self.timeout = timeout
        self.max_file_size = max_file_size

    def fetch(self, crawl_result):
        if not isinstance(
            crawl_result,
            CrawlResult,
        ):
            raise TypeError(
                "crawl_result must be a CrawlResult"
            )

        logger.info(
            "Downloading PDF document from %s",
            crawl_result.url,
        )

        try:
            response = requests.get(
                crawl_result.url,
                timeout=self.timeout,
                headers={
                    "User-Agent": (
                        "ConflictMarketAnalysis/"
                        "0.1 Research Crawler"
                    )
                },
            )

            response.raise_for_status()

            if (
                len(response.content)
                > self.max_file_size
            ):
                return self._create_error_result(
                    crawl_result,
                    response.status_code,
                    (
                        "PDF exceeds maximum "
                        "file size"
                    ),
                )

            content_type = response.headers.get(
                "Content-Type",
                "",
            ).casefold()

            is_pdf = (
                "application/pdf" in content_type
                or response.content.startswith(
                    b"%PDF"
                )
            )

            if not is_pdf:
                return self._create_error_result(
                    crawl_result,
                    response.status_code,
                    "Downloaded document is not a PDF",
                )

            reader = PdfReader(
                BytesIO(response.content)
            )

            extracted_pages = []

            for page in reader.pages:
                page_text = page.extract_text()

                if page_text:
                    extracted_pages.append(
                        page_text.strip()
                    )

            extracted_text = "\n\n".join(
                extracted_pages
            ).strip()

            if not extracted_text:
                return replace(
                    crawl_result,
                    content=None,
                    http_status=response.status_code,
                    retrieval_status=(
                        RetrievalStatus.EMPTY
                    ),
                    error_message=(
                        "PDF contains no "
                        "extractable text"
                    ),
                    retrieved_at=datetime.now(
                        timezone.utc
                    ),
                )

            return replace(
                crawl_result,
                content=extracted_text,
                http_status=response.status_code,
                retrieval_status=(
                    RetrievalStatus.SUCCESS
                ),
                error_message=None,
                retrieved_at=datetime.now(
                    timezone.utc
                ),
            )

        except requests.RequestException as error:
            logger.error(
                "PDF download failed: %s",
                error,
            )

            return self._create_error_result(
                crawl_result,
                None,
                str(error),
            )

        except Exception as error:
            logger.exception(
                "PDF extraction failed"
            )

            return self._create_error_result(
                crawl_result,
                None,
                str(error),
            )

    @staticmethod
    def _create_error_result(
        crawl_result,
        http_status,
        error_message,
    ):
        return replace(
            crawl_result,
            content=None,
            http_status=http_status,
            retrieval_status=(
                RetrievalStatus.ERROR
            ),
            error_message=error_message,
            retrieved_at=datetime.now(
                timezone.utc
            ),
        )