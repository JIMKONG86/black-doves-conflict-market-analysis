import json
import re
from datetime import datetime
from pathlib import Path

from src.models.candidate_observation import (
    CandidateObservation,
    CandidateType,
    ReviewStatus,
)


class CandidateObservationRepository:

    def __init__(
        self,
        directory="data/processed/candidates",
    ):
        self.directory = Path(directory)

        self.directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    def save(
        self,
        document_id,
        normalized_content_hash,
        candidates,
        overwrite=False,
    ):
        self._validate_metadata(
            document_id,
            normalized_content_hash,
        )

        candidate_list = list(candidates)

        self._validate_candidates(
            document_id=document_id,
            normalized_content_hash=(
                normalized_content_hash
            ),
            candidates=candidate_list,
        )

        candidate_list = sorted(
            candidate_list,
            key=lambda candidate: (
                candidate.start_index,
                candidate.end_index,
                candidate.candidate_id,
            ),
        )

        file_path = self._create_file_path(
            document_id
        )

        if file_path.exists() and not overwrite:
            return file_path

        document = {
            "document_id": document_id,
            "normalized_content_hash": (
                normalized_content_hash
            ),
            "candidate_count": len(
                candidate_list
            ),
            "candidates": [
                self._serialize_candidate(
                    candidate
                )
                for candidate in candidate_list
            ],
        }

        with file_path.open(
            "w",
            encoding="utf-8",
        ) as output_file:
            json.dump(
                document,
                output_file,
                ensure_ascii=False,
                indent=2,
            )

        return file_path

    def load(self, document_id):
        self._validate_document_id(
            document_id
        )

        file_path = self._create_file_path(
            document_id
        )

        if not file_path.exists():
            return []

        with file_path.open(
            "r",
            encoding="utf-8",
        ) as input_file:
            document = json.load(input_file)

        self._validate_stored_document(
            document,
            document_id,
        )

        candidates = []

        for stored_candidate in (
            document["candidates"]
        ):
            candidate = (
                self._deserialize_candidate(
                    document_id=document_id,
                    stored_candidate=(
                        stored_candidate
                    ),
                )
            )

            if (
                candidate.candidate_id
                != stored_candidate[
                    "candidate_id"
                ]
            ):
                raise ValueError(
                    "Stored candidate ID "
                    "failed integrity check"
                )

            if (
                candidate
                .normalized_content_hash
                != document[
                    "normalized_content_hash"
                ]
            ):
                raise ValueError(
                    "Stored content hash "
                    "does not match document"
                )

            candidates.append(candidate)

        return candidates

    def contains(self, document_id):
        self._validate_document_id(
            document_id
        )

        return self._create_file_path(
            document_id
        ).exists()

    def _create_file_path(
        self,
        document_id,
    ):
        return (
            self.directory
            / f"{document_id}.json"
        )

    @classmethod
    def _validate_metadata(
        cls,
        document_id,
        normalized_content_hash,
    ):
        cls._validate_document_id(
            document_id
        )

        if not isinstance(
            normalized_content_hash,
            str,
        ):
            raise TypeError(
                "normalized_content_hash "
                "must be a string"
            )

        if not normalized_content_hash.strip():
            raise ValueError(
                "normalized_content_hash "
                "must not be empty"
            )

    @staticmethod
    def _validate_document_id(document_id):
        if not isinstance(document_id, str):
            raise TypeError(
                "document_id must be a string"
            )

        if not document_id.strip():
            raise ValueError(
                "document_id must not be empty"
            )

        if not re.fullmatch(
            r"[A-Za-z0-9_-]+",
            document_id,
        ):
            raise ValueError(
                "document_id contains "
                "invalid characters"
            )

    @staticmethod
    def _validate_candidates(
        document_id,
        normalized_content_hash,
        candidates,
    ):
        for candidate in candidates:
            if not isinstance(
                candidate,
                CandidateObservation,
            ):
                raise TypeError(
                    "Every candidate must be a "
                    "CandidateObservation"
                )

            if candidate.document_id != document_id:
                raise ValueError(
                    "Candidate document_id "
                    "does not match"
                )

            if (
                candidate.normalized_content_hash
                != normalized_content_hash
            ):
                raise ValueError(
                    "Candidate content hash "
                    "does not match"
                )

    @staticmethod
    def _validate_stored_document(
        document,
        expected_document_id,
    ):
        if (
            document.get("document_id")
            != expected_document_id
        ):
            raise ValueError(
                "Stored document ID "
                "does not match"
            )

        stored_candidates = document.get(
            "candidates"
        )

        if not isinstance(
            stored_candidates,
            list,
        ):
            raise ValueError(
                "Stored candidates must "
                "be a list"
            )

        if (
            document.get("candidate_count")
            != len(stored_candidates)
        ):
            raise ValueError(
                "Stored candidate count "
                "does not match"
            )

    @staticmethod
    def _deserialize_candidate(
        document_id,
        stored_candidate,
    ):
        return CandidateObservation(
            document_id=document_id,
            candidate_type=CandidateType(
                stored_candidate[
                    "candidate_type"
                ]
            ),
            value=stored_candidate["value"],
            context=stored_candidate["context"],
            start_index=stored_candidate[
                "start_index"
            ],
            end_index=stored_candidate[
                "end_index"
            ],
            source_url=stored_candidate[
                "source_url"
            ],
            normalized_content_hash=(
                stored_candidate[
                    "normalized_content_hash"
                ]
            ),
            extraction_method=(
                stored_candidate[
                    "extraction_method"
                ]
            ),
            review_status=ReviewStatus(
                stored_candidate[
                    "review_status"
                ]
            ),
            created_at=datetime.fromisoformat(
                stored_candidate[
                    "created_at"
                ]
            ),
        )

    @staticmethod
    def _serialize_candidate(candidate):
        return {
            "candidate_id": candidate.candidate_id,
            "candidate_type": (
                candidate.candidate_type.value
            ),
            "value": candidate.value,
            "context": candidate.context,
            "start_index": candidate.start_index,
            "end_index": candidate.end_index,
            "source_url": candidate.source_url,
            "normalized_content_hash": (
                candidate.normalized_content_hash
            ),
            "extraction_method": (
                candidate.extraction_method
            ),
            "review_status": (
                candidate.review_status.value
            ),
            "created_at": (
                candidate.created_at.isoformat()
            ),
        }