import unittest

from datetime import date
from types import SimpleNamespace

from src.models.candidate_observation import (
    CandidateType,
)
from src.models.candidate_review import (
    ReviewDecision,
    SemanticRole,
)
from src.models.claim_observation import (
    ClaimStatus,
    CountryRole,
    SourceChannel,
)
from src.models.strike_observation import (
    StrikeType,
)
from src.services.candidate_review_queue import (
    CandidateReviewQueue,
)


class FakeCandidateReviewRepository:
    def __init__(self):
        self.saved_reviews = []
        self.latest_reviews = {}

    def save(
        self,
        review,
    ):
        self.saved_reviews.append(
            review
        )

    def get_latest_review(
        self,
        candidate_id,
    ):
        return self.latest_reviews.get(
            candidate_id
        )


class FakeClaimObservationRepository:
    def __init__(self):
        self.saved_claims = []

    def save(
        self,
        claim,
    ):
        self.saved_claims.append(
            claim
        )


class FakeStrikeObservationRepository:
    def __init__(self):
        self.saved_strikes = []

    def save(
        self,
        strike,
    ):
        self.saved_strikes.append(
            strike
        )


class TestCandidateReviewQueue(
    unittest.TestCase
):
    def setUp(self):
        self.repository = (
            FakeCandidateReviewRepository()
        )

        self.output_messages = []

        self.candidate = SimpleNamespace(
            candidate_id="a" * 64,
            document_id="b" * 64,
            candidate_type=CandidateType.DATE,
            value="25.08.2026",
            context=(
                "Published on 25.08.2026."
            ),
            source_url=(
                "https://example.com/"
                "document.pdf"
            ),
            extraction_method=(
                "regex:date_dmy"
            ),
        )

    def create_queue(
        self,
        input_values,
    ):
        input_iterator = iter(
            input_values
        )

        def input_function(
            _prompt,
        ):
            return next(
                input_iterator
            )

        return CandidateReviewQueue(
            repository=self.repository,
            input_function=input_function,
            output_function=(
                self.output_messages.append
            ),
        )

    def test_confirms_candidate(
        self,
    ):
        queue = self.create_queue(
            [
                "c",
                "1",
                "2026-08-25",
                "Document date.",
            ]
        )

        reviews = queue.run(
            candidates=[
                self.candidate
            ],
            reviewed_by="Markus",
        )

        self.assertEqual(
            len(reviews),
            1,
        )

        review = reviews[0]

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
            review.reviewer_note,
            "Document date.",
        )

        self.assertEqual(
            self.repository.saved_reviews,
            reviews,
        )

    def test_rejects_candidate(
        self,
    ):
        queue = self.create_queue(
            [
                "r",
                "Not relevant.",
            ]
        )

        reviews = queue.run(
            candidates=[
                self.candidate
            ],
            reviewed_by="Markus",
        )

        self.assertEqual(
            len(reviews),
            1,
        )

        review = reviews[0]

        self.assertEqual(
            review.decision,
            ReviewDecision.REJECTED,
        )

        self.assertEqual(
            review.semantic_role,
            SemanticRole.UNKNOWN,
        )

        self.assertIsNone(
            review.normalized_value
        )

        self.assertEqual(
            review.reviewer_note,
            "Not relevant.",
        )

    def test_quits_review_queue(
        self,
    ):
        queue = self.create_queue(
            [
                "q",
            ]
        )

        reviews = queue.run(
            candidates=[
                self.candidate
            ],
            reviewed_by="Markus",
        )

        self.assertEqual(
            reviews,
            [],
        )

        self.assertEqual(
            self.repository.saved_reviews,
            [],
        )

    def test_skips_existing_review(
        self,
    ):
        self.repository.latest_reviews[
            self.candidate.candidate_id
        ] = {
            "decision": "confirmed",
        }

        queue = self.create_queue(
            []
        )

        reviews = queue.run(
            candidates=[
                self.candidate
            ],
            reviewed_by="Markus",
        )

        self.assertEqual(
            reviews,
            [],
        )

        self.assertEqual(
            self.repository.saved_reviews,
            [],
        )

        self.assertTrue(
            any(
                "Skipping already reviewed"
                in message
                for message
                in self.output_messages
            )
        )

    def test_rejects_empty_reviewer(
        self,
    ):
        queue = self.create_queue(
            []
        )

        with self.assertRaises(
            ValueError
        ):
            queue.run(
                candidates=[
                    self.candidate
                ],
                reviewed_by=" ",
            )

    def test_allows_expenditure_role_for_amount_candidates(
        self,
    ):
        roles = (
            CandidateReviewQueue
            ._allowed_roles(
                CandidateType.AMOUNT
            )
        )

        self.assertEqual(
            roles,
            [
                SemanticRole.CONTRACT_AMOUNT,
                SemanticRole.BUDGET_AMOUNT,
                (
                    SemanticRole
                    .EXPENDITURE_AMOUNT
                ),
                SemanticRole.UNKNOWN,
            ],
        )

    def test_creates_strike_from_event_date_claim(
        self,
    ):
        claim_repository = (
            FakeClaimObservationRepository()
        )

        strike_repository = (
            FakeStrikeObservationRepository()
        )

        input_values = iter(
            [
                "c",
                "2",
                "2026-08-25",
                "Reported event date.",
                "y",
                "drone strike",
                "1",
                "3",
                "News platform",
                "Government spokesperson",
                "Original news agency",
                (
                    "affected=UA, "
                    "alleged_actor=RU"
                ),
                "y",
                "3",
                "",
                "",
                "Kyiv",
                "Drone",
                "",
            ]
        )

        queue = CandidateReviewQueue(
            repository=self.repository,
            claim_repository=(
                claim_repository
            ),
            strike_repository=(
                strike_repository
            ),
            input_function=(
                lambda _prompt: next(
                    input_values
                )
            ),
            output_function=(
                self.output_messages.append
            ),
        )

        reviews = queue.run(
            candidates=[
                self.candidate
            ],
            reviewed_by="Markus",
        )

        self.assertEqual(
            len(reviews),
            1,
        )

        self.assertEqual(
            len(
                claim_repository.saved_claims
            ),
            1,
        )

        self.assertEqual(
            len(
                strike_repository.saved_strikes
            ),
            1,
        )

        claim = (
            claim_repository.saved_claims[0]
        )

        strike = (
            strike_repository.saved_strikes[0]
        )

        self.assertEqual(
            claim.claim_status,
            ClaimStatus.REPORTED,
        )

        self.assertEqual(
            claim.source_channel,
            SourceChannel.NEWS_MEDIA,
        )

        self.assertEqual(
            strike.claim_id,
            claim.claim_id,
        )

        self.assertEqual(
            strike.event_date,
            date(
                2026,
                8,
                25,
            ),
        )

        self.assertEqual(
            strike.strike_type,
            StrikeType.DRONE_STRIKE,
        )

        self.assertEqual(
            strike.affected_country_code,
            "UA",
        )

        self.assertEqual(
            strike.initiator_country_code,
            "RU",
        )

        self.assertEqual(
            strike.location,
            "Kyiv",
        )

        self.assertEqual(
            strike.weapon_system,
            "Drone",
        )

        roles = {
            link.role
            for link in claim.country_links
        }

        self.assertIn(
            CountryRole.AFFECTED,
            roles,
        )

        self.assertIn(
            CountryRole.ALLEGED_ACTOR,
            roles,
        )

    def test_does_not_create_strike_when_declined(
        self,
    ):
        claim_repository = (
            FakeClaimObservationRepository()
        )

        strike_repository = (
            FakeStrikeObservationRepository()
        )

        input_values = iter(
            [
                "c",
                "2",
                "2026-08-25",
                "Reported event date.",
                "y",
                "airspace violation",
                "1",
                "3",
                "",
                "",
                "",
                (
                    "affected=FI, "
                    "alleged_actor=RU"
                ),
                "n",
            ]
        )

        queue = CandidateReviewQueue(
            repository=self.repository,
            claim_repository=(
                claim_repository
            ),
            strike_repository=(
                strike_repository
            ),
            input_function=(
                lambda _prompt: next(
                    input_values
                )
            ),
            output_function=(
                self.output_messages.append
            ),
        )

        reviews = queue.run(
            candidates=[
                self.candidate
            ],
            reviewed_by="Markus",
        )

        self.assertEqual(
            len(reviews),
            1,
        )

        self.assertEqual(
            len(
                claim_repository.saved_claims
            ),
            1,
        )

        self.assertEqual(
            strike_repository.saved_strikes,
            [],
        )


if __name__ == "__main__":
    unittest.main()