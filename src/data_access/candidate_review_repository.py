import json
import re
from pathlib import Path

from src.models.candidate_review import (
    CandidateReview,
)


class CandidateReviewRepository:

    def __init__(
        self,
        directory="data/validated/reviews",
    ):
        self.directory = Path(directory)

        self.directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    def save(self, review):
        self._validate_review(review)

        file_path = self._create_file_path(
            review.candidate_id
        )

        if file_path.exists():
            document = self._load_file(
                file_path
            )

            self._validate_existing_document(
                document,
                review,
            )
        else:
            document = {
                "candidate_id": (
                    review.candidate_id
                ),
                "document_id": (
                    review.document_id
                ),
                "candidate_type": (
                    review.candidate_type.value
                ),
                "review_count": 0,
                "latest_decision": None,
                "reviews": [],
            }

        existing_review_ids = {
            stored_review["review_id"]
            for stored_review
            in document["reviews"]
        }

        if review.review_id not in (
            existing_review_ids
        ):
            document["reviews"].append(
                self._serialize_review(review)
            )

        document["reviews"].sort(
            key=lambda stored_review: (
                stored_review["reviewed_at"],
                stored_review["review_id"],
            )
        )

        document["review_count"] = len(
            document["reviews"]
        )

        if document["reviews"]:
            document["latest_decision"] = (
                document["reviews"][-1][
                    "decision"
                ]
            )

        self._write_file(
            file_path,
            document,
        )

        return file_path

    def contains(self, candidate_id):
        self._validate_candidate_id(
            candidate_id
        )

        return self._create_file_path(
            candidate_id
        ).exists()

    def load_reviews(self, candidate_id):
        self._validate_candidate_id(
            candidate_id
        )

        file_path = self._create_file_path(
            candidate_id
        )

        if not file_path.exists():
            return []

        document = self._load_file(file_path)

        return list(document["reviews"])

    def get_latest_review(
        self,
        candidate_id,
    ):
        reviews = self.load_reviews(
            candidate_id
        )

        if not reviews:
            return None

        return reviews[-1]

    def _create_file_path(
        self,
        candidate_id,
    ):
        return (
            self.directory
            / f"{candidate_id}.json"
        )

    @staticmethod
    def _validate_review(review):
        if not isinstance(
            review,
            CandidateReview,
        ):
            raise TypeError(
                "review must be "
                "a CandidateReview"
            )

    @staticmethod
    def _validate_candidate_id(
        candidate_id,
    ):
        if not isinstance(candidate_id, str):
            raise TypeError(
                "candidate_id must be a string"
            )

        if not re.fullmatch(
            r"[A-Za-z0-9_-]+",
            candidate_id,
        ):
            raise ValueError(
                "candidate_id contains "
                "invalid characters"
            )

    @staticmethod
    def _validate_existing_document(
        document,
        review,
    ):
        if (
            document["candidate_id"]
            != review.candidate_id
        ):
            raise ValueError(
                "Candidate ID does not match"
            )

        if (
            document["document_id"]
            != review.document_id
        ):
            raise ValueError(
                "Document ID does not match"
            )

        if (
            document["candidate_type"]
            != review.candidate_type.value
        ):
            raise ValueError(
                "Candidate type does not match"
            )

    @staticmethod
    def _serialize_review(review):
        return {
            "review_id": review.review_id,
            "decision": review.decision.value,
            "semantic_role": (
                review.semantic_role.value
            ),
            "normalized_value": (
                review.normalized_value
            ),
            "reviewer_note": (
                review.reviewer_note
            ),
            "reviewed_by": (
                review.reviewed_by
            ),
            "reviewed_at": (
                review.reviewed_at.isoformat()
            ),
        }

    @staticmethod
    def _load_file(file_path):
        with file_path.open(
            "r",
            encoding="utf-8",
        ) as input_file:
            return json.load(input_file)

    @staticmethod
    def _write_file(
        file_path,
        document,
    ):
        temporary_path = (
            file_path.with_suffix(".tmp")
        )

        with temporary_path.open(
            "w",
            encoding="utf-8",
        ) as output_file:
            json.dump(
                document,
                output_file,
                ensure_ascii=False,
                indent=2,
            )

        temporary_path.replace(file_path)