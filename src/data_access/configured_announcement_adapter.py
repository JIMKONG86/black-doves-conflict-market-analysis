from dataclasses import replace

from src.data_access.crawler import RetrievalStatus, SourceAdapter
from src.data_access.html_document_fetcher import HtmlDocumentFetcher
from src.data_access.html_listing_source_adapter import (
    HtmlListingSourceAdapter,
)
from src.data_access.rss_source_adapter import RssSourceAdapter
from src.data_access.usaspending_transaction_adapter import (
    UsaspendingTransactionAdapter,
)
from src.models.source_definition import SourceDefinition


class ConfiguredAnnouncementAdapter(SourceAdapter):
    """Common adapter boundary for country announcement sources.

    RSS feeds and chronological HTML listings share the same detail-fetching
    and repository boundary.
    """

    def __init__(self, definition, html_fetcher=None):
        if not isinstance(definition, SourceDefinition):
            raise TypeError("definition must be a SourceDefinition")
        if definition.integration_status != "IMPLEMENTED":
            raise NotImplementedError(
                f"Source {definition.source_id} has no implemented adapter"
            )
        self.definition = definition
        self.html_fetcher = html_fetcher or HtmlDocumentFetcher(
            timeout=definition.request_timeout_seconds
        )
        if definition.delivery_method == "RSS_HTML" and definition.feed_url:
            self.discovery_adapter = RssSourceAdapter(
                source_id=definition.source_id,
                source_country_code=definition.country_code,
                source_name=definition.source_name,
                feed_url=definition.feed_url,
                jurisdiction=definition.jurisdiction,
                publication_timezone=definition.publication_timezone,
                publisher=definition.publisher,
            )
        elif definition.delivery_method == "HTML_LISTING":
            self.discovery_adapter = HtmlListingSourceAdapter(definition)
        elif definition.delivery_method == "USASPENDING_API":
            self.discovery_adapter = UsaspendingTransactionAdapter(definition)
        else:
            raise NotImplementedError(
                f"Unsupported delivery method: {definition.delivery_method}"
            )

    @property
    def source_name(self):
        return self.definition.source_name

    def collect(self, request, fetch_details=True):
        if self.definition.delivery_method == "USASPENDING_API":
            return self.discovery_adapter.collect(request)

        fetch_details = (
            fetch_details
            and self.definition.detail_retrieval_enabled
        )
        original_query = request.query
        detail_search = fetch_details and original_query != "*"
        discovery_request = (
            replace(
                request,
                query="*",
                max_results=max(
                    request.max_results,
                    self.definition.discovery_limit,
                ),
            )
            if detail_search
            else request
        )
        results = self.discovery_adapter.collect(discovery_request)
        if not fetch_details:
            return results

        enriched_results = []
        for result in results:
            if result.retrieval_status == RetrievalStatus.SUCCESS:
                fetched = self.html_fetcher.fetch(result)
                fetched = replace(fetched, query=original_query)
                if fetched.retrieval_status != RetrievalStatus.SUCCESS:
                    enriched_results.append(fetched)
                    continue
                if detail_search and not self._matches_query(
                    fetched,
                    original_query,
                ):
                    continue
                enriched_results.append(fetched)
            else:
                enriched_results.append(
                    replace(result, query=original_query)
                )
        return enriched_results[:request.max_results]

    @staticmethod
    def _matches_query(crawl_result, query):
        searchable_text = " ".join(
            value
            for value in (crawl_result.title, crawl_result.content)
            if value
        ).casefold()
        return all(
            term in searchable_text
            for term in query.casefold().split()
        )
