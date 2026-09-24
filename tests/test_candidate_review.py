import unittest
from datetime import datetime, timezone

from src.models.candidate_observation import (
    CandidateType,
)
from src.models.candidate_review import (
    CandidateReview,
    ReviewDecision,
    SemanticRole,
)


class TestCandidateReview(unittest.TestCase):

    def setUp(self):
        self.review_time = datetime(
            2026,
            9,
            2,
            10,
            0,
            tzinfo=timezone.utc,
        )

    def create_review(self, **changes):
        values = {
            "candidate_id": "candidate-123",
            "document_id": "document-123",
            "candidate_type": CandidateType.DATE,
            "decision": (
                ReviewDecision.CONFIRMED
            ),
            "semantic_role": (
                SemanticRole.DOCUMENT_DATE
            ),
            "reviewed_by": "manual-review",
            "normalized_value": "2026-08-25",
            "reviewer_note": (
                "Date shown in document header"
            ),
            "reviewed_at": self.review_time,
        }

        values.update(changes)

        return CandidateReview(**values)

    def test_creates_confirmed_review(self):
        review = self.create_review()

        self.assertEqual(
            review.decision,
            ReviewDecision.CONFIRMED,
        )
        self.assertEqual(
            review.semantic_role,
            SemanticRole.DOCUMENT_DATE,
        )
        self.assertEqual(
            review.normalized_value,
            "2026-08-25",
        )
        self.assertEqual(
            len(review.review_id),
            64,
        )

    def test_same_review_has_same_id(self):
        first_review = self.create_review()
        second_review = self.create_review()

        self.assertEqual(
            first_review.review_id,
            second_review.review_id,
        )

    def test_different_time_changes_id(self):
        later_time = datetime(
            2026,
            9,
            2,
            11,
            0,
            tzinfo=timezone.utc,
        )

        first_review = self.create_review()

        second_review = self.create_review(
            reviewed_at=later_time
        )

        self.assertNotEqual(
            first_review.review_id,
            second_review.review_id,
        )

    def test_rejects_confirmed_unknown_role(self):
        with self.assertRaises(ValueError):
            self.create_review(
                semantic_role=(
                    SemanticRole.UNKNOWN
                ),
                normalized_value=None,
            )

    def test_rejects_incompatible_role(self):
        with self.assertRaises(ValueError):
            self.create_review(
                semantic_role=(
                    SemanticRole.CONTRACT_AMOUNT
                )
            )

    def test_rejected_has_no_normalized_value(self):
        with self.assertRaises(ValueError):
            self.create_review(
                decision=ReviewDecision.REJECTED,
                semantic_role=(
                    SemanticRole.UNKNOWN
                ),
                normalized_value="2026-08-25",
            )

    def test_accepts_needs_source(self):
        review = self.create_review(
            decision=(
                ReviewDecision.NEEDS_SOURCE
            ),
            semantic_role=SemanticRole.UNKNOWN,
            normalized_value=None,
            reviewer_note=(
                "Date role cannot yet be verified"
            ),
        )

        self.assertEqual(
            review.decision,
            ReviewDecision.NEEDS_SOURCE,
        )
        self.assertEqual(
            review.semantic_role,
            SemanticRole.UNKNOWN,
        )


if __name__ == "__main__":
    unittest.main()