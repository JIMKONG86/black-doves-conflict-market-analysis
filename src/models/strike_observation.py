import re

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from enum import Enum
from hashlib import sha256
from urllib.parse import urlparse

from src.models.claim_observation import (
    ClaimStatus,
    SourceChannel,
)


_IDENTIFIER_PATTERN = re.compile(
    r"[a-f0-9]{64}"
)

_COUNTRY_CODE_PATTERN = re.compile(
    r"[A-Z]{2}"
)


class StrikeType(Enum):
    AIRSTRIKE = "airstrike"
    MISSILE_STRIKE = "missile_strike"
    DRONE_STRIKE = "drone_strike"
    ARTILLERY_STRIKE = "artillery_strike"
    NAVAL_STRIKE = "naval_strike"
    GROUND_STRIKE = "ground_strike"
    OTHER = "other"
    UNKNOWN = "unknown"


def _normalize_identifier(
    value,
    field_name,
):
    if not isinstance(value, str):
        raise TypeError(
            f"{field_name} must be a string"
        )

    normalized_value = (
        value.strip().lower()
    )

    if not _IDENTIFIER_PATTERN.fullmatch(
        normalized_value
    ):
        raise ValueError(
            f"{field_name} must be "
            "a 64-character hexadecimal ID"
        )

    return normalized_value


def _normalize_country_code(
    value,
    field_name,
    required,
):
    if value is None:
        if required:
            raise ValueError(
                f"{field_name} must not be empty"
            )

        return None

    if not isinstance(value, str):
        raise TypeError(
            f"{field_name} must be "
            "a string or None"
        )

    normalized_value = (
        value.strip().upper()
    )

    if not _COUNTRY_CODE_PATTERN.fullmatch(
        normalized_value
    ):
        raise ValueError(
            f"{field_name} must be "
            "an ISO alpha-2 country code"
        )

    return normalized_value


def _normalize_required_text(
    value,
    field_name,
):
    if not isinstance(value, str):
        raise TypeError(
            f"{field_name} must be a string"
        )

    normalized_value = value.strip()

    if not normalized_value:
        raise ValueError(
            f"{field_name} must not be empty"
        )

    return normalized_value


def _normalize_optional_text(
    value,
    field_name,
):
    if value is None:
        return None

    if not isinstance(value, str):
        raise TypeError(
            f"{field_name} must be "
            "a string or None"
        )

    return value.strip() or None


def _normalize_source_url(
    value,
):
    source_url = _normalize_required_text(
        value,
        "source_url",
    )

    parsed_url = urlparse(
        source_url
    )

    if (
        parsed_url.scheme
        not in {"http", "https"}
        or not parsed_url.netloc
    ):
        raise ValueError(
            "source_url must be "
            "a valid HTTP or HTTPS URL"
        )

    return source_url


@dataclass(frozen=True)
class StrikeObservation:
    candidate_id: str
    document_id: str
    review_id: str
    claim_id: str
    event_date: date
    strike_type: StrikeType
    claim_status: ClaimStatus
    source_channel: SourceChannel
    affected_country_code: str
    description: str
    reviewed_by: str
    source_url: str
    initiator_country_code: str | None = None
    location: str | None = None
    weapon_system: str | None = None
    created_at: datetime = field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )
    strike_id: str = field(
        init=False
    )

    def __post_init__(self):
        candidate_id = _normalize_identifier(
            self.candidate_id,
            "candidate_id",
        )

        document_id = _normalize_identifier(
            self.document_id,
            "document_id",
        )

        review_id = _normalize_identifier(
            self.review_id,
            "review_id",
        )

        claim_id = _normalize_identifier(
            self.claim_id,
            "claim_id",
        )

        if (
            not isinstance(
                self.event_date,
                date,
            )
            or isinstance(
                self.event_date,
                datetime,
            )
        ):
            raise TypeError(
                "event_date must be a date"
            )

        if not isinstance(
            self.strike_type,
            StrikeType,
        ):
            raise TypeError(
                "strike_type must be "
                "a StrikeType"
            )

        if not isinstance(
            self.claim_status,
            ClaimStatus,
        ):
            raise TypeError(
                "claim_status must be "
                "a ClaimStatus"
            )

        if not isinstance(
            self.source_channel,
            SourceChannel,
        ):
            raise TypeError(
                "source_channel must be "
                "a SourceChannel"
            )

        affected_country_code = (
            _normalize_country_code(
                self.affected_country_code,
                "affected_country_code",
                required=True,
            )
        )

        initiator_country_code = (
            _normalize_country_code(
                self.initiator_country_code,
                "initiator_country_code",
                required=False,
            )
        )

        description = (
            _normalize_required_text(
                self.description,
                "description",
            )
        )

        reviewed_by = (
            _normalize_required_text(
                self.reviewed_by,
                "reviewed_by",
            )
        )

        source_url = _normalize_source_url(
            self.source_url
        )

        location = _normalize_optional_text(
            self.location,
            "location",
        )

        weapon_system = (
            _normalize_optional_text(
                self.weapon_system,
                "weapon_system",
            )
        )

        if not isinstance(
            self.created_at,
            datetime,
        ):
            raise TypeError(
                "created_at must be a datetime"
            )

        if (
            self.created_at.tzinfo is None
            or self.created_at.utcoffset()
            is None
        ):
            raise ValueError(
                "created_at must be "
                "timezone-aware"
            )

        created_at = self.created_at.astimezone(
            timezone.utc
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
            "review_id",
            review_id,
        )

        object.__setattr__(
            self,
            "claim_id",
            claim_id,
        )

        object.__setattr__(
            self,
            "affected_country_code",
            affected_country_code,
        )

        object.__setattr__(
            self,
            "initiator_country_code",
            initiator_country_code,
        )

        object.__setattr__(
            self,
            "description",
            description,
        )

        object.__setattr__(
            self,
            "reviewed_by",
            reviewed_by,
        )

        object.__setattr__(
            self,
            "source_url",
            source_url,
        )

        object.__setattr__(
            self,
            "location",
            location,
        )

        object.__setattr__(
            self,
            "weapon_system",
            weapon_system,
        )

        object.__setattr__(
            self,
            "created_at",
            created_at,
        )

        object.__setattr__(
            self,
            "strike_id",
            self._create_strike_id(),
        )

    def _create_strike_id(self):
        identity = "|".join(
            [
                self.candidate_id,
                self.document_id,
                self.review_id,
                self.claim_id,
                self.event_date.isoformat(),
                self.strike_type.value,
                self.claim_status.value,
                self.source_channel.value,
                self.affected_country_code,
                (
                    self.initiator_country_code
                    or ""
                ),
                self.location or "",
                self.weapon_system or "",
                self.description,
                self.reviewed_by,
                self.source_url,
                self.created_at.isoformat(),
            ]
        )

        return sha256(
            identity.encode("utf-8")
        ).hexdigest()