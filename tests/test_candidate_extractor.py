import unittest
from datetime import datetime, timezone
from hashlib import sha256

from src.models.candidate_observation import (
    CandidateType,
    ReviewStatus,
)
from src.models.normalized_document import (
    NormalizedDocument,
)
from src.services.candidate_extractor import (
    CandidateExtractor,
)


class TestCandidateExtractor(unittest.TestCase):

    def setUp(self):
        self.extractor = CandidateExtractor(
            context_window=20
        )

    def create_document(self, content):
        content_hash = sha256(
            content.encode("utf-8")
        ).hexdigest()

        return NormalizedDocument(
            document_id="document-123",
            source_name="Example source",
            source_type="rss",
            url="https://example.com/document.pdf",
            canonical_url=(
                "https://example.com/document.pdf"
            ),
            query="government contract",
            title="Example document",
            publisher="Example publisher",
            author=None,
            published_at=None,
            language="en",
            content=content,
            raw_content_hash="raw-content-hash",
            normalized_content_hash=content_hash,
            word_count=len(content.split()),
            character_count=len(content),
            retrieved_at=datetime(
                2026,
                8,
                25,
                tzinfo=timezone.utc,
            ),
        )

    def test_extracts_valid_dates(self):
        document = self.create_document(
            "Published on 25.08.2026 and "
            "updated on 2026-08-26."
        )

        candidates = self.extractor.extract(
            document
        )

        date_values = [
            candidate.value
            for candidate in candidates
            if (
                candidate.candidate_type
                == CandidateType.DATE
            )
        ]

        self.assertEqual(
            date_values,
            [
                "25.08.2026",
                "2026-08-26",
            ],
        )

    def test_ignores_invalid_date(self):
        document = self.create_document(
            "Invalid date: 31.02.2026."
        )

        candidates = self.extractor.extract(
            document
        )

        self.assertEqual(candidates, [])

    def test_extracts_amount_with_suffix(self):
        document = self.create_document(
            "The contract has a value of "
            "369,9 Millionen Euro."
        )

        candidates = self.extractor.extract(
            document
        )

        self.assertEqual(len(candidates), 1)
        self.assertEqual(
            candidates[0].candidate_type,
            CandidateType.AMOUNT,
        )
        self.assertEqual(
            candidates[0].value,
            "369,9 Millionen Euro",
        )

    def test_extracts_amount_with_prefix(self):
        document = self.create_document(
            "The approved budget was "
            "$200 million."
        )

        candidates = self.extractor.extract(
            document
        )

        self.assertEqual(len(candidates), 1)
        self.assertEqual(
            candidates[0].value,
            "$200 million",
        )
        self.assertEqual(
            candidates[0].review_status,
            ReviewStatus.PENDING,
        )

    def test_includes_bounded_context(self):
        document = self.create_document(
            "A" * 100
            + "25.08.2026"
            + "B" * 100
        )

        candidates = self.extractor.extract(
            document
        )

        self.assertEqual(len(candidates), 1)
        self.assertIn(
            "25.08.2026",
            candidates[0].context,
        )
        self.assertLessEqual(
            len(candidates[0].context),
            50,
        )

    def test_returns_candidates_in_text_order(self):
        document = self.create_document(
            "€ 5 million was approved "
            "on 25.08.2026."
        )

        candidates = self.extractor.extract(
            document
        )

        self.assertEqual(len(candidates), 2)
        self.assertEqual(
            candidates[0].candidate_type,
            CandidateType.AMOUNT,
        )
        self.assertEqual(
            candidates[1].candidate_type,
            CandidateType.DATE,
        )

    def test_rejects_invalid_input(self):
        with self.assertRaises(TypeError):
            self.extractor.extract(
                "not a normalized document"
            )

        with self.assertRaises(ValueError):
            CandidateExtractor(
                context_window=-1
            )
    def test_extracts_german_text_dates(self):
        document = self.create_document(
            "Published on 25. August 2026 "
            "and updated on 1. März 2025."
        )

        candidates = self.extractor.extract(
            document
        )

        date_values = [
            candidate.value
            for candidate in candidates
            if (
                candidate.candidate_type
                == CandidateType.DATE
            )
        ]

        self.assertEqual(
            date_values,
            [
                "25. August 2026",
                "1. März 2025",
            ],
        )

    def test_ignores_invalid_german_date(self):
        document = self.create_document(
            "Invalid dates: "
            "31. Februar 2026 and "
            "29. Februar 2025."
        )

        candidates = self.extractor.extract(
            document
        )

        self.assertEqual(candidates, [])

if __name__ == "__main__":
    unittest.main()