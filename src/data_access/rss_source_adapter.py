import calendar
import logging
from datetime import datetime, timezone

import feedparser
from bs4 import BeautifulSoup

from src.data_access.crawler import (
    CrawlRequest,
    CrawlResult,
    RetrievalStatus,
    SourceAdapter,
    SourceType,
)


logger = logging.getLogger(__name__)


class RssSourceAdapter(SourceAdapter):

    def __init__(
        self,
        source_name,
        feed_url,
        source_id=None,
        source_country_code=None,
        jurisdiction=None,
        publication_timezone=None,
        publisher=None,
    ):
        self._source_name = source_name.strip()
        self.feed_url = feed_url.strip()
        self.source_id = (
            source_id.strip()
            if source_id
            else None
        )
        self.source_country_code = (
            source_country_code.strip().upper()
            if source_country_code
            else None
        )
        self.jurisdiction = (
            jurisdiction.strip()
            if jurisdiction
            else None
        )
        self.publication_timezone = (
            publication_timezone.strip()
            if publication_timezone
            else None
        )
        self.publisher = publisher.strip() if publisher else None

        if not self._source_name:
            raise ValueError(
                "source_name must not be empty"
            )

        if not self.feed_url:
            raise ValueError(
                "feed_url must not be empty"
            )

    @property
    def source_name(self):
        return self._source_name

    def collect(self, request):
        logger.info(
            "Collecting RSS results from %s",
            self.feed_url,
        )

        try:
            feed = feedparser.parse(self.feed_url)
        except Exception as error:
            logger.exception(
                "RSS feed could not be loaded"
            )

            return [
                CrawlResult(
                    source_name=self.source_name,
                    source_type=SourceType.RSS,
                    url=self.feed_url,
                    source_id=self.source_id,
                    source_country_code=(
                        self.source_country_code
                    ),
                    query=request.query,
                    publication_timezone=(
                        self.publication_timezone
                    ),
                    jurisdiction=(
                        self.jurisdiction
                        or request.jurisdiction
                    ),
                    retrieval_status=(
                        RetrievalStatus.ERROR
                    ),
                    error_message=str(error),
                )
            ]

        if feed.bozo and not feed.entries:
            return [
                CrawlResult(
                    source_name=self.source_name,
                    source_type=SourceType.RSS,
                    url=self.feed_url,
                    source_id=self.source_id,
                    source_country_code=(
                        self.source_country_code
                    ),
                    query=request.query,
                    publication_timezone=(
                        self.publication_timezone
                    ),
                    jurisdiction=(
                        self.jurisdiction
                        or request.jurisdiction
                    ),
                    retrieval_status=(
                        RetrievalStatus.ERROR
                    ),
                    error_message=str(
                        feed.bozo_exception
                    ),
                )
            ]

        results = []

        collect_all = request.query == "*"

        search_terms = (
            []
            if collect_all
            else request.query.casefold().split()
        )

        for entry in feed.entries:
            title = entry.get("title", "")
            summary = entry.get("summary", "")

            clean_summary = BeautifulSoup(
                summary,
                "html.parser",
            ).get_text(
                " ",
                strip=True,
            )

            searchable_text = (
                f"{title} {clean_summary}"
            ).casefold()

            if (
                not collect_all
                and not all(
                    term in searchable_text
                    for term in search_terms
                )
            ):
                continue

            published_at = self._get_published_at(
                entry
            )

            if not self._matches_date_range(
                published_at,
                request,
            ):
                continue

            results.append(
                CrawlResult(
                    source_name=self.source_name,
                    source_type=SourceType.RSS,
                    url=entry.get(
                        "link",
                        self.feed_url,
                    ),
                    canonical_url=entry.get(
                        "link"
                    ),
                    source_id=self.source_id,
                    source_country_code=(
                        self.source_country_code
                    ),
                    query=request.query,
                    title=title or None,
                    publisher=(
                        self.publisher
                        or feed.feed.get(
                            "title",
                            self.source_name,
                        )
                    ),
                    author=entry.get("author"),
                    published_at=published_at,
                    publication_timezone=(
                        self.publication_timezone
                    ),
                    date_precision=(
                        "datetime"
                        if published_at
                        else None
                    ),
                    jurisdiction=(
                        self.jurisdiction
                        or request.jurisdiction
                    ),
                    language=feed.feed.get(
                        "language",
                        request.language,
                    ),
                    content=clean_summary or None,
                    retrieval_status=(
                        RetrievalStatus.SUCCESS
                    ),
                )
            )

            if len(results) >= request.max_results:
                break

        return results

    @staticmethod
    def _get_published_at(entry):
        parsed_date = (
            entry.get("published_parsed")
            or entry.get("updated_parsed")
        )

        if parsed_date is None:
            return None

        timestamp = calendar.timegm(parsed_date)

        return datetime.fromtimestamp(
            timestamp,
            tz=timezone.utc,
        )

    @staticmethod
    def _matches_date_range(
        published_at,
        request,
    ):
        if published_at is None:
            return request.include_undated

        publication_date = published_at.date()

        if (
            request.start_date is not None
            and publication_date
            < request.start_date
        ):
            return False

        if (
            request.end_date is not None
            and publication_date
            > request.end_date
        ):
            return False

        return True
