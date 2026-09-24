import logging
from datetime import datetime, timezone

import requests

from src.data_access.crawler import (
    CrawlResult,
    RetrievalStatus,
    SourceAdapter,
    SourceType,
)

logger = logging.getLogger(__name__)

GDELT_DOC_API_URL = "https://api.gdeltproject.org/api/v2/doc/doc"

# GDELT's "sourcecountry" field is the country's full English name (as
# assigned by GDELT's own source-country classifier), not an ISO code,
# and is not guaranteed to match any particular standard. This project
# focuses on exactly five countries, so a small explicit mapping here is
# more auditable than pulling in a general country-name library that
# would introduce many names this project never uses.
GDELT_COUNTRY_NAMES_BY_ISO = {
    "US": "United States",
    "IL": "Israel",
    "IR": "Iran",
    "DE": "Germany",
    "CN": "China",
}
ISO_BY_GDELT_COUNTRY_NAME = {
    name: code for code, name in GDELT_COUNTRY_NAMES_BY_ISO.items()
}

_MAX_RECORDS_PER_REQUEST = 250


class GdeltSourceAdapter(SourceAdapter):
    """Discovers article metadata from the free GDELT 2.0 DOC API.

    Unlike the RSS-based adapters in this codebase (RssSourceAdapter),
    GDELT's DOC API supports genuine historical date-range queries
    (startdatetime/enddatetime), so it can retroactively cover a fixed
    study window such as 1 Jan-18 Aug 2026 instead of only whatever
    happens to still be present in a live, rolling feed.

    GDELT itself returns only article metadata (title, url, domain,
    published date, source country, language), never full article text.
    Use HtmlDocumentFetcher on the returned CrawlResult URLs to retrieve
    full content, the same two-stage discover-then-fetch pattern already
    used for the state-organ sources in this project.

    IMPORTANT: this adapter has been implemented and unit-tested against
    mocked HTTP responses, but has never been executed against the real
    GDELT API, because the environment that wrote it has no outbound
    network access. Treat it as CONNECTOR_READY, not CONNECTOR_VERIFIED,
    until someone with network access runs it once and confirms the
    live response shape still matches what is parsed here.
    """

    def __init__(
        self,
        source_name="GDELT 2.0 DOC API",
        api_url=GDELT_DOC_API_URL,
        source_id=None,
        timeout=30,
    ):
        self._source_name = source_name.strip()
        self.api_url = api_url.strip()
        self.source_id = source_id.strip() if source_id else None

        if timeout <= 0:
            raise ValueError("timeout must be greater than zero")
        self.timeout = timeout

        if not self._source_name:
            raise ValueError("source_name must not be empty")
        if not self.api_url:
            raise ValueError("api_url must not be empty")

    @property
    def source_name(self):
        return self._source_name

    def collect(self, request):
        params = self._build_params(request)
        logger.info("Querying GDELT DOC API with params %s", params)

        try:
            response = requests.get(
                self.api_url,
                params=params,
                timeout=self.timeout,
                headers={
                    "User-Agent": (
                        "ConflictMarketAnalysis/0.2 "
                        "AcademicResearchCrawler"
                    )
                },
            )
            response.raise_for_status()
            payload = response.json()
        except Exception as error:
            logger.exception("GDELT DOC API request failed")
            return [
                self._result(
                    request,
                    retrieval_status=RetrievalStatus.ERROR,
                    error_message=str(error),
                )
            ]

        articles = payload.get("articles") or []

        if not articles:
            return [
                self._result(
                    request,
                    retrieval_status=RetrievalStatus.EMPTY,
                )
            ]

        results = []

        for article in articles[: request.max_results]:
            published_at = self._parse_seendate(article.get("seendate"))
            country_name = article.get("sourcecountry")
            url = article.get("url")

            if not url:
                continue

            results.append(
                CrawlResult(
                    source_name=self.source_name,
                    source_type=SourceType.API,
                    url=url,
                    canonical_url=url,
                    source_id=self.source_id,
                    source_country_code=ISO_BY_GDELT_COUNTRY_NAME.get(
                        country_name
                    ),
                    query=request.query,
                    title=article.get("title") or None,
                    publisher=article.get("domain") or None,
                    published_at=published_at,
                    date_precision="datetime" if published_at else None,
                    jurisdiction=request.jurisdiction,
                    language=article.get("language") or request.language,
                    retrieval_status=RetrievalStatus.SUCCESS,
                )
            )

        if not results:
            return [
                self._result(
                    request,
                    retrieval_status=RetrievalStatus.EMPTY,
                )
            ]

        return results

    def _result(self, request, retrieval_status, error_message=None):
        return CrawlResult(
            source_name=self.source_name,
            source_type=SourceType.API,
            url=self.api_url,
            source_id=self.source_id,
            query=request.query,
            jurisdiction=request.jurisdiction,
            retrieval_status=retrieval_status,
            error_message=error_message,
        )

    def _build_params(self, request):
        query = request.query.strip()

        if request.jurisdiction:
            country_name = GDELT_COUNTRY_NAMES_BY_ISO.get(
                request.jurisdiction.strip().upper()
            )
            if country_name:
                query = f'{query} sourcecountry:"{country_name}"'

        params = {
            "query": query,
            "mode": "artlist",
            "format": "json",
            "maxrecords": min(request.max_results, _MAX_RECORDS_PER_REQUEST),
            "sort": "dateasc",
        }

        if request.start_date is not None:
            params["startdatetime"] = self._format_datetime(
                request.start_date, end_of_day=False
            )

        if request.end_date is not None:
            params["enddatetime"] = self._format_datetime(
                request.end_date, end_of_day=True
            )

        return params

    @staticmethod
    def _format_datetime(value, end_of_day):
        time_part = "235959" if end_of_day else "000000"
        return f"{value.strftime('%Y%m%d')}{time_part}"

    @staticmethod
    def _parse_seendate(value):
        if not value:
            return None

        try:
            return datetime.strptime(
                value, "%Y%m%dT%H%M%SZ"
            ).replace(tzinfo=timezone.utc)
        except ValueError:
            return None
