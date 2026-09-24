import logging
import re
from datetime import datetime
from urllib.parse import urljoin, urlparse
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

from src.data_access.crawler import (
    CrawlResult,
    RetrievalStatus,
    SourceAdapter,
    SourceType,
)
from src.models.source_definition import SourceDefinition


logger = logging.getLogger(__name__)


class HtmlListingSourceAdapter(SourceAdapter):
    """Discovers official releases from a chronological HTML listing.

    Country-specific URL paths and pagination stay in the source registry;
    the extraction and evidence metadata remain shared and testable.
    """

    _GENERIC_LINK_TEXT = {
        "read more",
        "full article",
        "more",
        "קרא עוד",
        "לכתבה המלאה",
    }
    _DATE_PATTERNS = (
        re.compile(r"(?<!\d)(20\d{2})[/-](\d{1,2})[/-](\d{1,2})(?!\d)"),
        re.compile(r"(?<!\d)(\d{1,2})[./-](\d{1,2})[./-](20\d{2})(?!\d)"),
    )
    _ENGLISH_MONTH_DATE_PATTERN = re.compile(
        r"\b("
        r"Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|"
        r"Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|"
        r"Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?"
        r")\.?\s+(\d{1,2}),\s+(20\d{2})\b",
        re.IGNORECASE,
    )
    _MONTH_NUMBERS = {
        "jan": 1,
        "feb": 2,
        "mar": 3,
        "apr": 4,
        "may": 5,
        "jun": 6,
        "jul": 7,
        "aug": 8,
        "sep": 9,
        "oct": 10,
        "nov": 11,
        "dec": 12,
    }

    def __init__(self, definition, timeout=None, max_file_size=5_000_000):
        if not isinstance(definition, SourceDefinition):
            raise TypeError("definition must be a SourceDefinition")
        if definition.delivery_method != "HTML_LISTING":
            raise ValueError("definition must use HTML_LISTING delivery")
        if not definition.detail_url_prefixes:
            raise ValueError("HTML_LISTING requires detail_url_prefixes")
        resolved_timeout = timeout or definition.request_timeout_seconds
        if resolved_timeout <= 0:
            raise ValueError("timeout must be greater than zero")
        if max_file_size <= 0:
            raise ValueError("max_file_size must be greater than zero")

        self.definition = definition
        self.timeout = resolved_timeout
        self.max_file_size = max_file_size

    @property
    def source_name(self):
        return self.definition.source_name

    def collect(self, request):
        results = []
        seen_urls = set()

        for page_number in range(1, self.definition.max_listing_pages + 1):
            page_url = self._page_url(page_number)
            page_results = self._collect_page(
                page_url,
                request,
                seen_urls,
            )

            if self._is_error_page(page_results):
                if not results:
                    return page_results
                logger.warning(
                    "Stopping %s pagination after page error: %s",
                    self.definition.source_id,
                    page_url,
                )
                break

            if not page_results:
                break

            matching_results = [
                result
                for result in page_results
                if self._matches_request(result, request)
            ]
            results.extend(matching_results)

            if len(results) >= request.max_results:
                return results[:request.max_results]

            if self._page_is_older_than_start(page_results, request):
                break

            if not self.definition.listing_page_url_template:
                break

        return results[:request.max_results]

    def _collect_page(self, page_url, request, seen_urls):
        try:
            response = requests.get(
                page_url,
                timeout=self.timeout,
                headers={
                    "User-Agent": (
                        "ConflictMarketAnalysis/0.3 "
                        "AcademicResearchCrawler"
                    )
                },
            )
            response.raise_for_status()

            if len(response.content) > self.max_file_size:
                return [self._error_result(
                    page_url,
                    request,
                    "HTML listing exceeds maximum file size",
                    response.status_code,
                )]

            content_type = response.headers.get("Content-Type", "").casefold()
            if "html" not in content_type:
                return [self._error_result(
                    page_url,
                    request,
                    "Downloaded listing is not HTML",
                    response.status_code,
                )]

            soup = BeautifulSoup(response.text, "html.parser")
            discovered = []

            for anchor in soup.find_all("a", href=True):
                absolute_url = urljoin(page_url, anchor.get("href"))
                if not self._is_detail_url(absolute_url):
                    continue
                absolute_url = self._normalize_detail_url(absolute_url)
                if absolute_url in seen_urls:
                    continue

                title = self._extract_title(anchor)
                if not title:
                    continue

                seen_urls.add(absolute_url)
                published_at = self._extract_published_at(anchor)
                summary = self._extract_summary(anchor, title)
                discovered.append(CrawlResult(
                    source_name=self.source_name,
                    source_type=SourceType.HTML,
                    url=absolute_url,
                    canonical_url=absolute_url,
                    source_id=self.definition.source_id,
                    source_country_code=self.definition.country_code,
                    query=request.query,
                    title=title,
                    publisher=self.definition.publisher,
                    published_at=published_at,
                    publication_timezone=self.definition.publication_timezone,
                    date_precision="date" if published_at else None,
                    jurisdiction=(
                        self.definition.jurisdiction
                        or request.jurisdiction
                    ),
                    language=(
                        request.language
                        or self.definition.primary_language
                    ),
                    content=summary,
                    http_status=response.status_code,
                    retrieval_status=RetrievalStatus.SUCCESS,
                ))

            return discovered
        except requests.RequestException as error:
            logger.error("HTML listing download failed: %s", error)
            return [self._error_result(page_url, request, str(error))]
        except Exception as error:
            logger.exception("HTML listing extraction failed")
            return [self._error_result(page_url, request, str(error))]

    def _page_url(self, page_number):
        if page_number == 1 or not self.definition.listing_page_url_template:
            return self.definition.entrypoint_url
        return self.definition.listing_page_url_template.format(
            page=page_number
        )

    def _is_detail_url(self, url):
        parsed = urlparse(url)
        entrypoint = urlparse(self.definition.entrypoint_url)
        if parsed.scheme not in {"http", "https"}:
            return False
        if parsed.netloc.casefold() != entrypoint.netloc.casefold():
            return False
        return any(
            parsed.path.startswith(prefix)
            and parsed.path.rstrip("/") != prefix.rstrip("/")
            for prefix in self.definition.detail_url_prefixes
        )

    def _normalize_detail_url(self, url):
        pattern_text = self.definition.detail_url_id_pattern
        template = self.definition.detail_url_template
        if not pattern_text or not template:
            return url
        match = re.search(pattern_text, urlparse(url).path)
        if not match:
            return url
        return template.format(id=match.group("id"))

    def _extract_title(self, anchor):
        link_text = anchor.get_text(" ", strip=True)
        if self._is_meaningful_title(link_text):
            return link_text

        node = anchor
        for _ in range(6):
            node = node.parent
            if node is None:
                break
            heading = node.find(["h1", "h2", "h3", "h4"])
            if heading:
                candidate = heading.get_text(" ", strip=True)
                if self._is_meaningful_title(candidate):
                    return candidate

        return None

    def _extract_published_at(self, anchor):
        node = anchor
        for _ in range(6):
            if node is None:
                break
            text = node.get_text(" ", strip=True)
            parsed_date = self._parse_date(text)
            if parsed_date:
                return parsed_date
            node = node.parent
        return None

    def _parse_date(self, text):
        timezone = ZoneInfo(self.definition.publication_timezone)
        for index, pattern in enumerate(self._DATE_PATTERNS):
            match = pattern.search(text)
            if not match:
                continue
            try:
                if index == 0:
                    year, month, day = map(int, match.groups())
                else:
                    day, month, year = map(int, match.groups())
                return datetime(year, month, day, tzinfo=timezone)
            except ValueError:
                continue

        english_match = self._ENGLISH_MONTH_DATE_PATTERN.search(text)
        if english_match:
            month_name, day, year = english_match.groups()
            try:
                return datetime(
                    int(year),
                    self._MONTH_NUMBERS[month_name[:3].casefold()],
                    int(day),
                    tzinfo=timezone,
                )
            except ValueError:
                pass
        return None

    @staticmethod
    def _extract_summary(anchor, title):
        node = anchor.parent
        if node is None:
            return None
        text = node.get_text(" ", strip=True)
        if text == title or len(text) > 2_000:
            return None
        return text or None

    def _is_meaningful_title(self, value):
        normalized = " ".join(value.split())
        return (
            len(normalized) >= 8
            and normalized.casefold() not in self._GENERIC_LINK_TEXT
        )

    @staticmethod
    def _matches_request(result, request):
        if not HtmlListingSourceAdapter._matches_date_range(result, request):
            return False
        if request.query == "*":
            return True
        searchable = " ".join(
            value for value in (result.title, result.content) if value
        ).casefold()
        return all(
            term in searchable
            for term in request.query.casefold().split()
        )

    @staticmethod
    def _matches_date_range(result, request):
        if result.published_at is None:
            return request.include_undated
        publication_date = result.published_at.date()
        if request.start_date and publication_date < request.start_date:
            return False
        if request.end_date and publication_date > request.end_date:
            return False
        return True

    @staticmethod
    def _page_is_older_than_start(page_results, request):
        if request.start_date is None:
            return False
        dated_results = [
            result for result in page_results if result.published_at
        ]
        return bool(dated_results) and max(
            result.published_at.date() for result in dated_results
        ) < request.start_date

    @staticmethod
    def _is_error_page(page_results):
        return (
            len(page_results) == 1
            and page_results[0].retrieval_status == RetrievalStatus.ERROR
        )

    def _error_result(self, page_url, request, message, http_status=None):
        return CrawlResult(
            source_name=self.source_name,
            source_type=SourceType.HTML,
            url=page_url,
            source_id=self.definition.source_id,
            source_country_code=self.definition.country_code,
            query=request.query,
            publisher=self.definition.publisher,
            publication_timezone=self.definition.publication_timezone,
            jurisdiction=(
                self.definition.jurisdiction
                or request.jurisdiction
            ),
            language=(
                request.language
                or self.definition.primary_language
            ),
            http_status=http_status,
            retrieval_status=RetrievalStatus.ERROR,
            error_message=message,
        )
