import unittest

from src.models.candidate_observation import (
    CandidateObservation,
    CandidateType,
    ReviewStatus,
)


class TestCandidateObservation(unittest.TestCase):

    def create_candidate(self, **changes):
        values = {
            "document_id": "document-123",
            "candidate_type": CandidateType.DATE,
            "value": "25.08.2026",
            "context": (
                "21. Wahlperiode 25.08.2026 "
                "Antwort der Bundesregierung"
            ),
            "start_index": 20,
            "end_index": 30,
            "source_url": (
                "https://example.com/document.pdf"
            ),
            "normalized_content_hash": (
                "normalized-content-hash"
            ),
            "extraction_method": (
                "regular_expression"
            ),
        }

        values.update(changes)

        return CandidateObservation(**values)

    def test_creates_pending_candidate(self):
        candidate = self.create_candidate()

        self.assertEqual(
            candidate.value,
            "25.08.2026",
        )
        self.assertEqual(
            candidate.review_status,
            ReviewStatus.PENDING,
        )
        self.assertEqual(
            len(candidate.candidate_id),
            64,
        )

    def test_same_observation_has_same_id(self):
        first_candidate = self.create_candidate()
        second_candidate = self.create_candidate()

        self.assertEqual(
            first_candidate.candidate_id,
            second_candidate.candidate_id,
        )

    def test_different_position_changes_id(self):
        first_candidate = self.create_candidate(
            start_index=20,
            end_index=30,
        )
        second_candidate = self.create_candidate(
            start_index=40,
            end_index=50,
        )

        self.assertNotEqual(
            first_candidate.candidate_id,
            second_candidate.candidate_id,
        )

    def test_rejects_invalid_index_range(self):
        invalid_ranges = [
            (-1, 10),
            (10, 10),
            (20, 10),
        ]

        for start_index, end_index in (
            invalid_ranges
        ):
            with self.subTest(
                start_index=start_index,
                end_index=end_index,
            ):
                with self.assertRaises(
                    ValueError
                ):
                    self.create_candidate(
                        start_index=start_index,
                        end_index=end_index,
                    )

    def test_rejects_invalid_candidate_type(self):
        with self.assertRaises(TypeError):
            self.create_candidate(
                candidate_type="date"
            )


if __name__ == "__main__":
    unittest.main()