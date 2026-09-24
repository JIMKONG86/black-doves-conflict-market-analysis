import json
import unittest
from datetime import date
from pathlib import Path

import requests

from src.data_access.crawler import (
    CrawlRequest,
    RetrievalStatus,
    SourceType,
)
from src.data_access.source_registry import SourceRegistry
from src.data_access.usaspending_transaction_adapter import (
    UsaspendingTransactionAdapter,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class FakeResponse:

    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        return self.payload


class FakeSession:

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.responses.pop(0)


class TestUsaspendingTransactionAdapter(unittest.TestCase):

    def setUp(self):
        registry = SourceRegistry.from_json(
            PROJECT_ROOT / "config" / "country_sources.json"
        )
        self.definition = registry.get("US_USASPENDING_CONTRACTS")

    def test_requires_bounded_date_window(self):
        adapter = UsaspendingTransactionAdapter(
            self.definition,
            session=FakeSession([]),
        )

        with self.assertRaisesRegex(ValueError, "requires both"):
            adapter.collect(CrawlRequest(query="*"))

    def test_builds_defense_contract_transaction_request(self):
        session = FakeSession(
            [FakeResponse(self._payload([self._record()], has_next=False))]
        )
        adapter = UsaspendingTransactionAdapter(
            self.definition,
            session=session,
        )

        results = adapter.collect(self._request(query="Lockheed Martin"))

        self.assertEqual(len(results), 1)
        _, call = session.calls[0]
        filters = call["json"]["filters"]
        self.assertEqual(filters["award_type_codes"], ["A", "B", "C", "D"])
        self.assertEqual(
            filters["agencies"][0]["name"],
            "Department of Defense",
        )
        self.assertEqual(
            filters["recipient_search_text"],
            ["Lockheed Martin"],
        )
        self.assertEqual(
            filters["time_period"],
            [{"start_date": "2026-01-01", "end_date": "2026-08-18"}],
        )

    def test_maps_transaction_to_auditable_api_result(self):
        session = FakeSession(
            [FakeResponse(self._payload([self._record()], has_next=False))]
        )
        adapter = UsaspendingTransactionAdapter(
            self.definition,
            session=session,
        )

        result = adapter.collect(self._request())[0]

        self.assertEqual(result.source_type, SourceType.API)
        self.assertEqual(result.source_country_code, "US")
        self.assertEqual(result.date_precision, "date")
        self.assertEqual(result.published_at.date(), date(2026, 8, 18))
        self.assertIn("transaction=12345", result.canonical_url)
        raw_content = json.loads(result.content)
        self.assertEqual(
            raw_content["record"]["Recipient Name"],
            "LOCKHEED MARTIN CORPORATION",
        )
        self.assertEqual(
            raw_content["record"]["Transaction Amount"],
            12500000.0,
        )

    def test_paginates_without_exceeding_requested_maximum(self):
        first = self._record(internal_id=1)
        second = self._record(internal_id=2)
        third = self._record(internal_id=3)
        session = FakeSession(
            [
                FakeResponse(self._payload([first, second], has_next=True)),
                FakeResponse(self._payload([third], has_next=False)),
            ]
        )
        adapter = UsaspendingTransactionAdapter(
            self.definition,
            session=session,
        )

        results = adapter.collect(
            CrawlRequest(
                query="*",
                start_date=date(2026, 1, 1),
                end_date=date(2026, 8, 18),
                max_results=3,
            )
        )

        self.assertEqual(len(results), 3)
        self.assertEqual(len(session.calls), 2)
        self.assertEqual(session.calls[0][1]["json"]["page"], 1)
        self.assertEqual(session.calls[1][1]["json"]["page"], 2)

    def test_deduplicates_repeated_transaction_rows(self):
        record = self._record()
        session = FakeSession(
            [FakeResponse(self._payload([record, record], has_next=False))]
        )
        adapter = UsaspendingTransactionAdapter(
            self.definition,
            session=session,
        )

        results = adapter.collect(self._request())

        self.assertEqual(len(results), 1)

    def test_returns_error_record_for_api_failure(self):
        session = FakeSession([FakeResponse({}, status_code=503)])
        adapter = UsaspendingTransactionAdapter(
            self.definition,
            session=session,
        )

        result = adapter.collect(self._request())[0]

        self.assertEqual(result.retrieval_status, RetrievalStatus.ERROR)
        self.assertEqual(result.http_status, 503)
        self.assertIn("HTTP 503", result.error_message)

    @staticmethod
    def _request(query="*"):
        return CrawlRequest(
            query=query,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 8, 18),
            max_results=10,
        )

    @staticmethod
    def _payload(records, has_next):
        return {
            "limit": 10,
            "results": records,
            "page_metadata": {"page": 1, "hasNext": has_next},
        }

    @staticmethod
    def _record(internal_id=12345):
        return {
            "Award ID": "N0002426C0001",
            "Mod": "P00001",
            "Recipient Name": "LOCKHEED MARTIN CORPORATION",
            "Recipient UEI": "EXAMPLEUEI123",
            "Action Date": "2026-08-18",
            "Transaction Amount": 12500000.0,
            "Transaction Description": "Aircraft systems support",
            "Awarding Agency": "Department of Defense",
            "Awarding Sub Agency": "Department of the Navy",
            "Funding Agency": "Department of Defense",
            "Funding Sub Agency": "Department of the Navy",
            "generated_internal_id": (
                "CONT_AWD_N0002426C0001_9700_-NONE-_-NONE-"
            ),
            "internal_id": internal_id,
        }


if __name__ == "__main__":
    unittest.main()
