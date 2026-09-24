import json
import re

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from hashlib import sha256
from urllib.parse import urlparse


_COUNTRY_CODE_PATTERN = re.compile(
    r"[A-Z]{2}"
)


@dataclass(frozen=True)
class WeeklyConflictFeature:
    source_snapshot_date: date
    week_end_date: date
    country_name: str
    country_code: str
    source_row_count: int
    administrative_area_count: int
    total_events: int
    total_fatalities: int
    political_violence_events: int
    political_violence_fatalities: int
    strike_events: int
    strike_fatalities: int
    air_drone_strike_events: int
    air_drone_strike_fatalities: int
    shelling_artillery_missile_events: int
    shelling_artillery_missile_fatalities: int
    violence_against_civilians_events: int
    violence_against_civilians_fatalities: int
    protest_events: int
    riot_events: int
    strategic_development_events: int
    reviewed_by: str
    source_url: str
    created_at: datetime = field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )
    feature_id: str = field(init=False)

    def __post_init__(self):
        source_snapshot_date = self._date(
            self.source_snapshot_date,
            "source_snapshot_date",
        )
        week_end_date = self._date(
            self.week_end_date,
            "week_end_date",
        )

        if week_end_date > source_snapshot_date:
            raise ValueError(
                "week_end_date must not be after "
                "source_snapshot_date"
            )

        country_name = self._required_text(
            self.country_name,
            "country_name",
        )
        country_code = self._country_code(
            self.country_code
        )
        reviewed_by = self._required_text(
            self.reviewed_by,
            "reviewed_by",
        )
        source_url = self._source_url(
            self.source_url
        )

        positive_fields = (
            "source_row_count",
            "administrative_area_count",
        )
        non_negative_fields = (
            "total_events",
            "total_fatalities",
            "political_violence_events",
            "political_violence_fatalities",
            "strike_events",
            "strike_fatalities",
            "air_drone_strike_events",
            "air_drone_strike_fatalities",
            "shelling_artillery_missile_events",
            "shelling_artillery_missile_fatalities",
            "violence_against_civilians_events",
            "violence_against_civilians_fatalities",
            "protest_events",
            "riot_events",
            "strategic_development_events",
        )
        normalized_numbers = {}

        for field_name in positive_fields:
            normalized_numbers[field_name] = (
                self._positive_int(
                    getattr(self, field_name),
                    field_name,
                )
            )

        for field_name in non_negative_fields:
            normalized_numbers[field_name] = (
                self._non_negative_int(
                    getattr(self, field_name),
                    field_name,
                )
            )

        if (
            normalized_numbers[
                "air_drone_strike_events"
            ]
            + normalized_numbers[
                "shelling_artillery_missile_events"
            ]
            != normalized_numbers["strike_events"]
        ):
            raise ValueError(
                "strike_events must equal the sum "
                "of its strike-type event counts"
            )

        if (
            normalized_numbers[
                "air_drone_strike_fatalities"
            ]
            + normalized_numbers[
                "shelling_artillery_missile_fatalities"
            ]
            != normalized_numbers["strike_fatalities"]
        ):
            raise ValueError(
                "strike_fatalities must equal the sum "
                "of its strike-type fatality counts"
            )

        for subset_field, total_field in (
            ("political_violence_events", "total_events"),
            (
                "political_violence_fatalities",
                "total_fatalities",
            ),
            ("strike_events", "total_events"),
            ("strike_fatalities", "total_fatalities"),
            (
                "violence_against_civilians_events",
                "total_events",
            ),
            (
                "violence_against_civilians_fatalities",
                "total_fatalities",
            ),
        ):
            if (
                normalized_numbers[subset_field]
                > normalized_numbers[total_field]
            ):
                raise ValueError(
                    f"{subset_field} must not exceed "
                    f"{total_field}"
                )

        if not isinstance(self.created_at, datetime):
            raise TypeError(
                "created_at must be a datetime"
            )

        if (
            self.created_at.tzinfo is None
            or self.created_at.utcoffset() is None
        ):
            raise ValueError(
                "created_at must be timezone-aware"
            )

        normalized_values = {
            "source_snapshot_date": (
                source_snapshot_date
            ),
            "week_end_date": week_end_date,
            "country_name": country_name,
            "country_code": country_code,
            "reviewed_by": reviewed_by,
            "source_url": source_url,
            "created_at": self.created_at.astimezone(
                timezone.utc
            ),
            **normalized_numbers,
        }

        for field_name, value in (
            normalized_values.items()
        ):
            object.__setattr__(
                self,
                field_name,
                value,
            )

        object.__setattr__(
            self,
            "feature_id",
            self._create_feature_id(),
        )

    @property
    def has_strike_activity(self):
        return self.strike_events > 0

    @staticmethod
    def _date(value, field_name):
        if (
            not isinstance(value, date)
            or isinstance(value, datetime)
        ):
            raise TypeError(
                f"{field_name} must be a date"
            )

        return value

    @staticmethod
    def _required_text(value, field_name):
        if not isinstance(value, str):
            raise TypeError(
                f"{field_name} must be a string"
            )

        normalized = value.strip()

        if not normalized:
            raise ValueError(
                f"{field_name} must not be empty"
            )

        return normalized

    @staticmethod
    def _country_code(value):
        country_code = (
            WeeklyConflictFeature._required_text(
                value,
                "country_code",
            )
            .upper()
        )

        if not _COUNTRY_CODE_PATTERN.fullmatch(
            country_code
        ):
            raise ValueError(
                "country_code must be an ISO "
                "alpha-2 country code"
            )

        return country_code

    @staticmethod
    def _non_negative_int(value, field_name):
        if (
            not isinstance(value, int)
            or isinstance(value, bool)
        ):
            raise TypeError(
                f"{field_name} must be an integer"
            )

        if value < 0:
            raise ValueError(
                f"{field_name} must not be negative"
            )

        return value

    @classmethod
    def _positive_int(cls, value, field_name):
        normalized = cls._non_negative_int(
            value,
            field_name,
        )

        if normalized == 0:
            raise ValueError(
                f"{field_name} must be positive"
            )

        return normalized

    @classmethod
    def _source_url(cls, value):
        source_url = cls._required_text(
            value,
            "source_url",
        )
        parsed_url = urlparse(source_url)

        if (
            parsed_url.scheme
            not in {"http", "https"}
            or not parsed_url.netloc
        ):
            raise ValueError(
                "source_url must be a valid "
                "HTTP or HTTPS URL"
            )

        return source_url

    def _create_feature_id(self):
        payload = {
            field_name: (
                value.isoformat()
                if isinstance(value, date)
                else value
            )
            for field_name, value in (
                (field_name, getattr(self, field_name))
                for field_name in (
                    "source_snapshot_date",
                    "week_end_date",
                    "country_name",
                    "country_code",
                    "source_row_count",
                    "administrative_area_count",
                    "total_events",
                    "total_fatalities",
                    "political_violence_events",
                    "political_violence_fatalities",
                    "strike_events",
                    "strike_fatalities",
                    "air_drone_strike_events",
                    "air_drone_strike_fatalities",
                    (
                        "shelling_artillery_"
                        "missile_events"
                    ),
                    (
                        "shelling_artillery_"
                        "missile_fatalities"
                    ),
                    (
                        "violence_against_"
                        "civilians_events"
                    ),
                    (
                        "violence_against_"
                        "civilians_fatalities"
                    ),
                    "protest_events",
                    "riot_events",
                    "strategic_development_events",
                    "source_url",
                )
            )
        }
        serialized_payload = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

        return sha256(
            serialized_payload.encode("utf-8")
        ).hexdigest()
