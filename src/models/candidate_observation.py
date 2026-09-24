from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from hashlib import sha256


class CandidateType(Enum):
    DATE = "date"
    AMOUNT = "amount"
    PERSON = "person"
    ORGANIZATION = "organization"
    COUNTRY = "country"
    CONTRACT_REFERENCE = "contract_reference"
    LEGAL_REFERENCE = "legal_reference"
    OTHER = "other"


class ReviewStatus(Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"


@dataclass(frozen=True)
class CandidateObservation:
    document_id: str
    candidate_type: CandidateType
    value: str
    context: str
    start_index: int
    end_index: int
    source_url: str
    normalized_content_hash: str
    extraction_method: str
    review_status: ReviewStatus = (
        ReviewStatus.PENDING
    )
    created_at: datetime = field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )
    candidate_id: str = field(
        init=False
    )

    def __post_init__(self):
        self._validate()

        normalized_value = " ".join(
            self.value.split()
        )

        normalized_context = self.context.strip()

        normalized_method = (
            self.extraction_method.strip()
        )

        object.__setattr__(
            self,
            "value",
            normalized_value,
        )
        object.__setattr__(
            self,
            "context",
            normalized_context,
        )
        object.__setattr__(
            self,
            "extraction_method",
            normalized_method,
        )

        candidate_id = self._create_candidate_id()

        object.__setattr__(
            self,
            "candidate_id",
            candidate_id,
        )

    def _validate(self):
        if not self.document_id.strip():
            raise ValueError(
                "document_id must not be empty"
            )

        if not isinstance(
            self.candidate_type,
            CandidateType,
        ):
            raise TypeError(
                "candidate_type must be "
                "a CandidateType"
            )

        if not self.value.strip():
            raise ValueError(
                "value must not be empty"
            )

        if not self.context.strip():
            raise ValueError(
                "context must not be empty"
            )

        if self.start_index < 0:
            raise ValueError(
                "start_index must not be negative"
            )

        if self.end_index <= self.start_index:
            raise ValueError(
                "end_index must be greater "
                "than start_index"
            )

        if not self.source_url.strip():
            raise ValueError(
                "source_url must not be empty"
            )

        if not self.normalized_content_hash.strip():
            raise ValueError(
                "normalized_content_hash "
                "must not be empty"
            )

        if not self.extraction_method.strip():
            raise ValueError(
                "extraction_method "
                "must not be empty"
            )

        if not isinstance(
            self.review_status,
            ReviewStatus,
        ):
            raise TypeError(
                "review_status must be "
                "a ReviewStatus"
            )

        if self.created_at.tzinfo is None:
            raise ValueError(
                "created_at must be "
                "timezone-aware"
            )

    def _create_candidate_id(self):
        identity = "|".join(
            [
                self.document_id,
                self.candidate_type.value,
                str(self.start_index),
                str(self.end_index),
                self.value,
            ]
        )

        return sha256(
            identity.encode("utf-8")
        ).hexdigest()