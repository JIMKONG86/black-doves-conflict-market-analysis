import json
import re

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from hashlib import sha256


class ClaimStatus(Enum):
    REPORTED = "reported"
    ALLEGED = "alleged"
    CONFIRMED = "confirmed"
    DISPUTED = "disputed"
    DENIED = "denied"
    UNVERIFIED = "unverified"


class SourceChannel(Enum):
    PARLIAMENT = "parliament"
    GOVERNMENT = "government"
    NEWS_MEDIA = "news_media"
    NGO = "ngo"
    COMPANY = "company"
    SOCIAL_MEDIA = "social_media"
    OTHER = "other"


class CountryRole(Enum):
    PUBLISHER = "publisher"
    ORIGINAL_SOURCE = "original_source"
    ALLEGED_ACTOR = "alleged_actor"
    INITIATOR = "initiator"
    AFFECTED = "affected"
    MENTIONED = "mentioned"


@dataclass(frozen=True)
class CountryLink:
    country_code: str
    role: CountryRole

    def __post_init__(self):
        if not isinstance(
            self.country_code,
            str,
        ):
            raise TypeError(
                "country_code must be a string"
            )

        country_code = (
            self.country_code
            .strip()
            .upper()
        )

        if not re.fullmatch(
            r"[A-Z]{2}",
            country_code,
        ):
            raise ValueError(
                "country_code must be an "
                "ISO alpha-2 code"
            )

        if not isinstance(
            self.role,
            CountryRole,
        ):
            raise TypeError(
                "role must be a CountryRole"
            )

        object.__setattr__(
            self,
            "country_code",
            country_code,
        )


@dataclass(frozen=True)
class ClaimObservation:
    candidate_id: str
    document_id: str
    review_id: str
    claim_type: str
    claim_status: ClaimStatus
    source_channel: SourceChannel
    claim_text: str
    reviewed_by: str
    country_links: tuple[CountryLink, ...] = ()
    publisher_name: str | None = None
    statement_author: str | None = None
    original_source_name: str | None = None
    source_url: str | None = None
    created_at: datetime = field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )
    claim_id: str = field(
        init=False
    )

    def __post_init__(self):
        self._validate_required_string(
            self.candidate_id,
            "candidate_id",
        )
        self._validate_required_string(
            self.document_id,
            "document_id",
        )
        self._validate_required_string(
            self.review_id,
            "review_id",
        )
        self._validate_required_string(
            self.claim_text,
            "claim_text",
        )
        self._validate_required_string(
            self.reviewed_by,
            "reviewed_by",
        )

        if not isinstance(
            self.claim_type,
            str,
        ):
            raise TypeError(
                "claim_type must be a string"
            )

        claim_type = (
            self.claim_type
            .strip()
            .casefold()
            .replace(" ", "_")
        )

        if not re.fullmatch(
            r"[a-z0-9_]+",
            claim_type,
        ):
            raise ValueError(
                "claim_type must use lowercase "
                "letters, numbers and underscores"
            )

        if not isinstance(
            self.claim_status,
            ClaimStatus,
        ):
            raise TypeError(
                "claim_status must be a "
                "ClaimStatus"
            )

        if not isinstance(
            self.source_channel,
            SourceChannel,
        ):
            raise TypeError(
                "source_channel must be a "
                "SourceChannel"
            )

        country_links = tuple(
            self.country_links
        )

        for country_link in country_links:
            if not isinstance(
                country_link,
                CountryLink,
            ):
                raise TypeError(
                    "country_links must contain "
                    "CountryLink objects"
                )

        link_keys = {
            (
                link.country_code,
                link.role,
            )
            for link in country_links
        }

        if len(link_keys) != len(
            country_links
        ):
            raise ValueError(
                "country_links must not "
                "contain duplicates"
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

        object.__setattr__(
            self,
            "claim_type",
            claim_type,
        )
        object.__setattr__(
            self,
            "country_links",
            country_links,
        )

        for field_name in (
            "publisher_name",
            "statement_author",
            "original_source_name",
            "source_url",
        ):
            cleaned_value = (
                self._clean_optional_string(
                    getattr(
                        self,
                        field_name,
                    ),
                    field_name,
                )
            )

            object.__setattr__(
                self,
                field_name,
                cleaned_value,
            )

        object.__setattr__(
            self,
            "claim_id",
            self._create_claim_id(),
        )

    @staticmethod
    def _validate_required_string(
        value,
        field_name,
    ):
        if not isinstance(
            value,
            str,
        ):
            raise TypeError(
                f"{field_name} must be a string"
            )

        if not value.strip():
            raise ValueError(
                f"{field_name} must not be empty"
            )

    @staticmethod
    def _clean_optional_string(
        value,
        field_name,
    ):
        if value is None:
            return None

        if not isinstance(
            value,
            str,
        ):
            raise TypeError(
                f"{field_name} must be a "
                "string or None"
            )

        cleaned_value = value.strip()

        return cleaned_value or None

    def _create_claim_id(self) -> str:
        payload = {
            "candidate_id": self.candidate_id,
            "document_id": self.document_id,
            "review_id": self.review_id,
            "claim_type": self.claim_type,
            "claim_status": (
                self.claim_status.value
            ),
            "source_channel": (
                self.source_channel.value
            ),
            "claim_text": self.claim_text,
            "reviewed_by": self.reviewed_by,
            "publisher_name": (
                self.publisher_name
            ),
            "statement_author": (
                self.statement_author
            ),
            "original_source_name": (
                self.original_source_name
            ),
            "source_url": self.source_url,
            "country_links": sorted(
                (
                    link.country_code,
                    link.role.value,
                )
                for link in self.country_links
            ),
        }

        serialized_payload = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
        )

        return sha256(
            serialized_payload.encode(
                "utf-8"
            )
        ).hexdigest()
