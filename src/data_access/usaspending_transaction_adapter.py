import json
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

from src.data_access.crawler import (
    CrawlResult,
    RetrievalStatus,
    SourceAdapter,
    SourceType,
)
from src.models.source_definition import SourceDefinition


class UsaspendingTransactionAdapter(SourceAdapter):
    """Collect bounded federal contract transactions from USAspending V2."""

    CONTRACT_AWARD_TYPE_CODES = ("A", "B", "C", "D")
    FIELDS = (
        "Award ID",
        "Mod",
        "Recipient Name",
        "Recipient UEI",
        "Action Date",
        "Transaction Amount",
        "Transaction Description",
        "Awarding Agency",
        "Awarding Sub Agency",
        "Funding Agency",
        "Funding Sub Agency",
        "generated_internal_id",
        "internal_id",
    )
    MAX_PAGE_SIZE = 100

    def __init__(self, definition, session=None):
        if not isinstance(definition, SourceDefinition):
            raise TypeError("definition must be a SourceDefinition")
        if definition.delivery_method != "USASPENDING_API":
            raise ValueError(
                "definition delivery_method must be USASPENDING_API"
            )
        if not definition.awarding_agency_name:
            raise ValueError("awarding_agency_name must be configured")

        self.definition = definition
        self.session = session or requests.Session()

    @property
    def source_name(self):
        return self.definition.source_name

    def collect(self, request):
        if request.start_date is None or request.end_date is None:
            raise ValueError(
                "USAspending collection requires both start_date and end_date"
            )

        filters = self._build_filters(request)
        page_size = min(self.MAX_PAGE_SIZE, request.max_results)
        results = []
        seen_transactions = set()
        page = 1

        while len(results) < request.max_results:
            response = None
            payload = {
                "filters": filters,
                "fields": list(self.FIELDS),
                "page": page,
                "limit": page_size,
                "sort": "Action Date",
                "order": "desc",
            }

            try:
                response = self.session.post(
                    self.definition.entrypoint_url,
                    json=payload,
                    headers={
                        "Accept": "application/json",
                        "User-Agent": (
                            "BLACK-DOVES-academic-research/1.0"
                        ),
                    },
                    timeout=self.definition.request_timeout_seconds,
                )
                response.raise_for_status()
                response_payload = response.json()
            except (requests.RequestException, ValueError) as error:
                results.append(
                    self._error_result(
                        request,
                        error,
                        getattr(response, "status_code", None),
                    )
                )
                break

            records = response_payload.get("results")
            if not isinstance(records, list):
                results.append(
                    self._error_result(
                        request,
                        ValueError(
                            "USAspending response does not contain a results list"
                        ),
                        response.status_code,
                    )
                )
                break

            for record in records:
                transaction_key = self._transaction_key(record)
                if transaction_key in seen_transactions:
                    continue
                seen_transactions.add(transaction_key)
                results.append(
                    self._to_crawl_result(
                        request,
                        record,
                        response.status_code,
                        filters,
                    )
                )
                if len(results) >= request.max_results:
                    break

            page_metadata = response_payload.get("page_metadata") or {}
            if not records or not page_metadata.get("hasNext"):
                break
            page += 1

        return results

    def _build_filters(self, request):
        filters = {
            "time_period": [
                {
                    "start_date": request.start_date.isoformat(),
                    "end_date": request.end_date.isoformat(),
                }
            ],
            "award_type_codes": list(self.CONTRACT_AWARD_TYPE_CODES),
            "agencies": [
                {
                    "type": "awarding",
                    "tier": "toptier",
                    "name": self.definition.awarding_agency_name,
                }
            ],
        }
        if request.query != "*":
            filters["recipient_search_text"] = [request.query]
        return filters

    def _to_crawl_result(self, request, record, http_status, filters):
        action_date = self._parse_action_date(record.get("Action Date"))
        generated_id = str(
            record.get("generated_internal_id") or "unknown-award"
        )
        transaction_id = str(
            record.get("internal_id")
            or self._transaction_key(record)
        )
        award_url = (
            "https://www.usaspending.gov/award/"
            f"{generated_id}/?transaction={transaction_id}"
        )
        recipient = record.get("Recipient Name") or "Unknown recipient"
        award_id = record.get("Award ID") or "Unknown award"
        modification = record.get("Mod")
        title = f"{recipient} — {award_id}"
        if modification not in (None, ""):
            title += f" / modification {modification}"

        raw_record = {
            "source_endpoint": self.definition.entrypoint_url,
            "request_filters": filters,
            "record": record,
        }

        return CrawlResult(
            source_id=self.definition.source_id,
            source_country_code=self.definition.country_code,
            source_name=self.definition.source_name,
            source_type=SourceType.API,
            url=award_url,
            canonical_url=award_url,
            query=request.query,
            title=title,
            publisher=self.definition.publisher,
            author=record.get("Awarding Agency"),
            published_at=action_date,
            publication_timezone=self.definition.publication_timezone,
            date_precision="date" if action_date else None,
            jurisdiction=self.definition.jurisdiction,
            language=self.definition.primary_language,
            content=json.dumps(
                raw_record,
                ensure_ascii=False,
                sort_keys=True,
            ),
            http_status=http_status,
        )

    def _error_result(self, request, error, http_status=None):
        return CrawlResult(
            source_id=self.definition.source_id,
            source_country_code=self.definition.country_code,
            source_name=self.definition.source_name,
            source_type=SourceType.API,
            url=self.definition.entrypoint_url,
            canonical_url=self.definition.entrypoint_url,
            query=request.query,
            publisher=self.definition.publisher,
            publication_timezone=self.definition.publication_timezone,
            jurisdiction=self.definition.jurisdiction,
            language=self.definition.primary_language,
            http_status=http_status,
            error_message=str(error),
            retrieval_status=RetrievalStatus.ERROR,
        )

    def _parse_action_date(self, value):
        if not value:
            return None
        try:
            parsed_date = datetime.strptime(value, "%Y-%m-%d")
        except (TypeError, ValueError):
            return None
        return parsed_date.replace(
            tzinfo=ZoneInfo(self.definition.publication_timezone)
        )

    @staticmethod
    def _transaction_key(record):
        return (
            record.get("generated_internal_id"),
            record.get("internal_id"),
            record.get("Mod"),
            record.get("Action Date"),
        )
