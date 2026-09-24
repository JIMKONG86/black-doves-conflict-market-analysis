from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from hashlib import sha256

from src.models.candidate_observation import (
    CandidateType,
)


class ReviewDecision(Enum):
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    NEEDS_SOURCE = "needs_source"


class SemanticRole(Enum):
    DOCUMENT_DATE = "document_date"
    EVENT_DATE = "event_date"
    CITED_SOURCE_DATE = "cited_source_date"
    LEGAL_REFERENCE_DATE = (
        "legal_reference_date"
    )

    CONTRACT_AMOUNT = "contract_amount"
    BUDGET_AMOUNT = "budget_amount"
    EXPENDITURE_AMOUNT = (
        "expenditure_amount"
    )

    UNKNOWN = "unknown"


DATE_ROLES = {
    SemanticRole.DOCUMENT_DATE,
    SemanticRole.EVENT_DATE,
    SemanticRole.CITED_SOURCE_DATE,
    SemanticRole.LEGAL_REFERENCE_DATE,
    SemanticRole.UNKNOWN,
}


AMOUNT_ROLES = {
    SemanticRole.CONTRACT_AMOUNT,
    SemanticRole.BUDGET_AMOUNT,
    SemanticRole.EXPENDITURE_AMOUNT,
    SemanticRole.UNKNOWN,
}


@dataclass(frozen=True)
class CandidateReview:
    candidate_id: str
    document_id: str
    candidate_type: CandidateType
    decision: ReviewDecision
    semantic_role: SemanticRole
    reviewed_by: str
    normalized_value: str | None = None
    reviewer_note: str | None = None
    reviewed_at: datetime = field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )
    review_id: str = field(
        init=False
    )

    def __post_init__(self):
        self._validate()

        candidate_id = (
            self.candidate_id.strip()
        )

        document_id = (
            self.document_id.strip()
        )

        reviewed_by = (
            self.reviewed_by.strip()
        )

        normalized_value = (
            self.normalized_value.strip()
            if self.normalized_value
            else None
        )

        reviewer_note = (
            self.reviewer_note.strip()
            if self.reviewer_note
            else None
        )

        object.__setattr__(
            self,
            "candidate_id",
            candidate_id,
        )

        object.__setattr__(
            self,
            "document_id",
            document_id,
        )

        object.__setattr__(
            self,
            "reviewed_by",
            reviewed_by,
        )

        object.__setattr__(
            self,
            "normalized_value",
            normalized_value,
        )

        object.__setattr__(
            self,
            "reviewer_note",
            reviewer_note,
        )

        object.__setattr__(
            self,
            "review_id",
            self._create_review_id(),
        )

    def _validate(self):
        if (
            not isinstance(
                self.candidate_id,
                str,
            )
            or not self.candidate_id.strip()
        ):
            raise ValueError(
                "candidate_id must not be empty"
            )

        if (
            not isinstance(
                self.document_id,
                str,
            )
            or not self.document_id.strip()
        ):
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

        if not isinstance(
            self.decision,
            ReviewDecision,
        ):
            raise TypeError(
                "decision must be "
                "a ReviewDecision"
            )

        if not isinstance(
            self.semantic_role,
            SemanticRole,
        ):
            raise TypeError(
                "semantic_role must be "
                "a SemanticRole"
            )

        if (
            not isinstance(
                self.reviewed_by,
                str,
            )
            or not self.reviewed_by.strip()
        ):
            raise ValueError(
                "reviewed_by must not be empty"
            )

        if (
            self.normalized_value
            is not None
            and not isinstance(
                self.normalized_value,
                str,
            )
        ):
            raise TypeError(
                "normalized_value must be "
                "a string or None"
            )

        if (
            self.reviewer_note
            is not None
            and not isinstance(
                self.reviewer_note,
                str,
            )
        ):
            raise TypeError(
                "reviewer_note must be "
                "a string or None"
            )

        if self.reviewed_at.tzinfo is None:
            raise ValueError(
                "reviewed_at must be "
                "timezone-aware"
            )

        self._validate_decision()
        self._validate_semantic_role()

    def _validate_decision(self):
        if (
            self.decision
            == ReviewDecision.CONFIRMED
            and self.semantic_role
            == SemanticRole.UNKNOWN
        ):
            raise ValueError(
                "A confirmed candidate must "
                "have a semantic role"
            )

        if (
            self.decision
            == ReviewDecision.REJECTED
            and self.normalized_value
            is not None
        ):
            raise ValueError(
                "A rejected candidate must not "
                "have a normalized value"
            )

    def _validate_semantic_role(self):
        if (
            self.candidate_type
            == CandidateType.DATE
            and self.semantic_role
            not in DATE_ROLES
        ):
            raise ValueError(
                "Semantic role is not valid "
                "for a date candidate"
            )

        if (
            self.candidate_type
            == CandidateType.AMOUNT
            and self.semantic_role
            not in AMOUNT_ROLES
        ):
            raise ValueError(
                "Semantic role is not valid "
                "for an amount candidate"
            )

    def _create_review_id(self):
        identity = "|".join(
            [
                self.candidate_id,
                self.document_id,
                self.candidate_type.value,
                self.decision.value,
                self.semantic_role.value,
                self.reviewed_by,
                self.normalized_value or "",
                self.reviewer_note or "",
                self.reviewed_at.isoformat(),
            ]
        )

        return sha256(
            identity.encode("utf-8")
        ).hexdigest()