import json
import tempfile
import unittest
from datetime import datetime, timezone

from src.data_access.candidate_review_repository import (
    CandidateReviewRepository,
)
from src.models.candidate_observation import (
    CandidateType,
)
from src.models.candidate_review import (
    CandidateReview,
    ReviewDecision,
    SemanticRole,
)


class TestCandidateReviewRepository(
    unittest.TestCase
):

    def setUp(self):
        self.temporary_directory = (
            tempfile.TemporaryDirectory()
        )
        self.addCleanup(
            self.temporary_directory.cleanup
        )

        self.repository = (
            CandidateReviewRepository(
                directory=(
                    self.temporary_directory.name
                )
            )
        )

    def create_review(
        self,
        decision=ReviewDecision.NEEDS_SOURCE,
        semantic_role=SemanticRole.UNKNOWN,
        normalized_value=None,
        reviewed_at=None,
        document_id="document-123",
    ):
        if reviewed_at is None:
            reviewed_at = datetime(
                2026,
                9,
                2,
                10,
                0,
                tzinfo=timezone.utc,
            )

        return CandidateReview(
            candidate_id="candidate-123",
            document_id=document_id,
            candidate_type=CandidateType.DATE,
            decision=decision,
            semantic_role=semantic_role,
            reviewed_by="reviewer-001",
            normalized_value=normalized_value,
            reviewer_note="Manual review",
            reviewed_at=reviewed_at,
        )

    def test_saves_first_review(self):
        review = self.create_review()

        file_path = self.repository.save(
            review
        )

        self.assertTrue(file_path.exists())

        with file_path.open(
            "r",
            encoding="utf-8",
        ) as input_file:
            document = json.load(input_file)

        self.assertEqual(
            document["review_count"],
            1,
        )
        self.assertEqual(
            document["latest_decision"],
            "needs_source",
        )

    def test_appends_review_history(self):
        first_review = self.create_review()

        second_review = self.create_review(
            decision=ReviewDecision.CONFIRMED,
            semantic_role=(
                SemanticRole.DOCUMENT_DATE
            ),
            normalized_value="2026-08-25",
            reviewed_at=datetime(
                2026,
                9,
                2,
                11,
                0,
                tzinfo=timezone.utc,
            ),
        )

        self.repository.save(first_review)
        file_path = self.repository.save(
            second_review
        )

        with file_path.open(
            "r",
            encoding="utf-8",
        ) as input_file:
            document = json.load(input_file)

        self.assertEqual(
            document["review_count"],
            2,
        )
        self.assertEqual(
            document["latest_decision"],
            "confirmed",
        )

    def test_does_not_duplicate_review(self):
        review = self.create_review()

        self.repository.save(review)
        file_path = self.repository.save(
            review
        )

        with file_path.open(
            "r",
            encoding="utf-8",
        ) as input_file:
            document = json.load(input_file)

        self.assertEqual(
            document["review_count"],
            1,
        )

    def test_returns_latest_review(self):
        first_review = self.create_review()

        second_review = self.create_review(
            decision=ReviewDecision.CONFIRMED,
            semantic_role=(
                SemanticRole.DOCUMENT_DATE
            ),
            normalized_value="2026-08-25",
            reviewed_at=datetime(
                2026,
                9,
                2,
                11,
                0,
                tzinfo=timezone.utc,
            ),
        )

        self.repository.save(first_review)
        self.repository.save(second_review)

        latest_review = (
            self.repository.get_latest_review(
                "candidate-123"
            )
        )

        self.assertEqual(
            latest_review["decision"],
            "confirmed",
        )
        self.assertEqual(
            latest_review["normalized_value"],
            "2026-08-25",
        )

    def test_rejects_document_mismatch(self):
        first_review = self.create_review()

        mismatched_review = self.create_review(
            document_id="different-document"
        )

        self.repository.save(first_review)

        with self.assertRaises(ValueError):
            self.repository.save(
                mismatched_review
            )


if __name__ == "__main__":
    unittest.main()