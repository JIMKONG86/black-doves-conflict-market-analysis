import json
import math
import re

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from enum import Enum
from hashlib import sha256
from urllib.parse import urlparse


_COUNTRY_CODE_PATTERN = re.compile(r"[A-Z]{2}")


class ProcurementEventType(Enum):
    ORDER_AWARD = "order_award"
    OPTION_EXERCISE = "option_exercise"
    CONTRACT_AMENDMENT = "contract_amendment"


class ProcurementVerificationStatus(Enum):
    PRIMARY_SOURCE_CONFIRMED = "primary_source_confirmed"
    CORROBORATED = "corroborated"
    UNVERIFIED = "unverified"


@dataclass(frozen=True)
class ProcurementEvent:
    announcement_date: date
    company_name: str
    company_ticker: str
    buyer_name: str
    event_type: ProcurementEventType
    title: str
    systems: tuple[str, ...]
    source_name: str
    source_url: str
    value_description: str
    is_air_defence: bool
    verification_status: ProcurementVerificationStatus
    reviewed_by: str
    buyer_country_code: str | None = None
    contract_value_eur: float | None = None
    aggregate_package_value_eur: float | None = None
    related_initiative: str | None = None
    notes: str | None = None
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    event_id: str = field(init=False)

    def __post_init__(self):
        if (
            not isinstance(self.announcement_date, date)
            or isinstance(self.announcement_date, datetime)
        ):
            raise TypeError("announcement_date must be a date")

        if not isinstance(self.event_type, ProcurementEventType):
            raise TypeError(
                "event_type must be a ProcurementEventType"
            )

        if not isinstance(
            self.verification_status,
            ProcurementVerificationStatus,
        ):
            raise TypeError(
                "verification_status must be a "
                "ProcurementVerificationStatus"
            )

        if not isinstance(self.is_air_defence, bool):
            raise TypeError("is_air_defence must be a bool")

        normalized_text = {}

        for field_name in (
            "company_name",
            "company_ticker",
            "buyer_name",
            "title",
            "source_name",
            "source_url",
            "value_description",
            "reviewed_by",
        ):
            normalized_text[field_name] = self._required_text(
                getattr(self, field_name),
                field_name,
            )

        parsed_url = urlparse(normalized_text["source_url"])

        if (
            parsed_url.scheme not in {"http", "https"}
            or not parsed_url.netloc
        ):
            raise ValueError(
                "source_url must be an absolute HTTP or HTTPS URL"
            )

        if isinstance(self.systems, (str, bytes)):
            raise TypeError("systems must be an iterable of strings")

        try:
            systems = tuple(
                self._required_text(value, "systems item")
                for value in self.systems
            )
        except TypeError as error:
            raise TypeError("systems must be an iterable") from error

        if not systems:
            raise ValueError("systems must not be empty")

        if len(systems) != len(set(systems)):
            raise ValueError("systems must not contain duplicates")

        buyer_country_code = self._optional_country_code(
            self.buyer_country_code
        )
        contract_value_eur = self._optional_positive_number(
            self.contract_value_eur,
            "contract_value_eur",
        )
        aggregate_package_value_eur = (
            self._optional_positive_number(
                self.aggregate_package_value_eur,
                "aggregate_package_value_eur",
            )
        )
        related_initiative = self._optional_text(
            self.related_initiative,
            "related_initiative",
        )
        notes = self._optional_text(self.notes, "notes")

        if not isinstance(self.created_at, datetime):
            raise TypeError("created_at must be a datetime")

        if (
            self.created_at.tzinfo is None
            or self.created_at.utcoffset() is None
        ):
            raise ValueError("created_at must be timezone-aware")

        normalized_values = {
            **normalized_text,
            "systems": systems,
            "buyer_country_code": buyer_country_code,
            "contract_value_eur": contract_value_eur,
            "aggregate_package_value_eur": (
                aggregate_package_value_eur
            ),
            "related_initiative": related_initiative,
            "notes": notes,
            "created_at": self.created_at.astimezone(timezone.utc),
        }

        for field_name, value in normalized_values.items():
            object.__setattr__(self, field_name, value)

        object.__setattr__(self, "event_id", self._create_event_id())

    @property
    def has_exact_contract_value(self):
        return self.contract_value_eur is not None

    def _create_event_id(self):
        identity = {
            "announcement_date": self.announcement_date.isoformat(),
            "company_name": self.company_name,
            "company_ticker": self.company_ticker,
            "buyer_name": self.buyer_name,
            "buyer_country_code": self.buyer_country_code,
            "event_type": self.event_type.value,
            "title": self.title,
            "systems": self.systems,
            "source_name": self.source_name,
            "source_url": self.source_url,
            "contract_value_eur": self.contract_value_eur,
            "aggregate_package_value_eur": (
                self.aggregate_package_value_eur
            ),
            "value_description": self.value_description,
            "is_air_defence": self.is_air_defence,
            "related_initiative": self.related_initiative,
        }
        canonical = json.dumps(
            identity,
            sort_keys=True,
            separators=(",", ":"),
        )

        return sha256(canonical.encode("utf-8")).hexdigest()

    @staticmethod
    def _required_text(value, field_name):
        if not isinstance(value, str):
            raise TypeError(f"{field_name} must be a string")

        normalized = value.strip()

        if not normalized:
            raise ValueError(f"{field_name} must not be empty")

        return normalized

    @classmethod
    def _optional_text(cls, value, field_name):
        if value is None:
            return None

        return cls._required_text(value, field_name)

    @classmethod
    def _optional_country_code(cls, value):
        if value is None:
            return None

        code = cls._required_text(
            value,
            "buyer_country_code",
        ).upper()

        if not _COUNTRY_CODE_PATTERN.fullmatch(code):
            raise ValueError(
                "buyer_country_code must be a two-letter ISO code"
            )

        return code

    @staticmethod
    def _optional_positive_number(value, field_name):
        if value is None:
            return None

        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"{field_name} must be a number")

        number = float(value)

        if not math.isfinite(number) or number <= 0:
            raise ValueError(f"{field_name} must be positive and finite")

        return number
