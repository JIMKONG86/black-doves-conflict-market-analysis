import json
import math
import re

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from enum import Enum
from hashlib import sha256
from urllib.parse import urlparse


_COUNTRY_CODE_PATTERN = re.compile(
    r"[A-Z]{2}"
)


class AggregateEventType(Enum):
    BATTLES = "battles"
    EXPLOSIONS_REMOTE_VIOLENCE = (
        "explosions_remote_violence"
    )
    PROTESTS = "protests"
    RIOTS = "riots"
    STRATEGIC_DEVELOPMENTS = (
        "strategic_developments"
    )
    VIOLENCE_AGAINST_CIVILIANS = (
        "violence_against_civilians"
    )


class AggregateDisorderType(Enum):
    DEMONSTRATIONS = "demonstrations"
    POLITICAL_VIOLENCE = "political_violence"
    POLITICAL_VIOLENCE_DEMONSTRATIONS = (
        "political_violence_demonstrations"
    )
    STRATEGIC_DEVELOPMENTS = (
        "strategic_developments"
    )


@dataclass(frozen=True)
class WeeklyConflictAggregate:
    source_snapshot_date: date
    week_end_date: date
    region: str
    country_name: str
    admin1: str
    event_type: AggregateEventType
    sub_event_type: str
    event_count: int
    fatality_count: int
    disorder_type: AggregateDisorderType
    geographic_id: int
    centroid_latitude: float
    centroid_longitude: float
    reviewed_by: str
    source_url: str
    country_code: str | None = None
    population_exposure: int | None = None
    created_at: datetime = field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )
    aggregate_id: str = field(
        init=False
    )

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

        region = self._required_text(
            self.region,
            "region",
        )
        country_name = self._required_text(
            self.country_name,
            "country_name",
        )
        admin1 = self._required_text(
            self.admin1,
            "admin1",
        )
        sub_event_type = self._required_text(
            self.sub_event_type,
            "sub_event_type",
        )
        reviewed_by = self._required_text(
            self.reviewed_by,
            "reviewed_by",
        )
        source_url = self._source_url(
            self.source_url
        )

        if not isinstance(
            self.event_type,
            AggregateEventType,
        ):
            raise TypeError(
                "event_type must be an "
                "AggregateEventType"
            )

        if not isinstance(
            self.disorder_type,
            AggregateDisorderType,
        ):
            raise TypeError(
                "disorder_type must be an "
                "AggregateDisorderType"
            )

        event_count = self._non_negative_int(
            self.event_count,
            "event_count",
        )
        fatality_count = self._non_negative_int(
            self.fatality_count,
            "fatality_count",
        )
        geographic_id = self._non_negative_int(
            self.geographic_id,
            "geographic_id",
        )

        population_exposure = self.population_exposure

        if population_exposure is not None:
            population_exposure = (
                self._non_negative_int(
                    population_exposure,
                    "population_exposure",
                )
            )

        centroid_latitude = self._coordinate(
            self.centroid_latitude,
            "centroid_latitude",
            minimum=-90,
            maximum=90,
        )
        centroid_longitude = self._coordinate(
            self.centroid_longitude,
            "centroid_longitude",
            minimum=-180,
            maximum=180,
        )
        country_code = self._country_code(
            self.country_code
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
                "created_at must be timezone-aware"
            )

        created_at = self.created_at.astimezone(
            timezone.utc
        )

        normalized_values = {
            "source_snapshot_date": (
                source_snapshot_date
            ),
            "week_end_date": week_end_date,
            "region": region,
            "country_name": country_name,
            "country_code": country_code,
            "admin1": admin1,
            "sub_event_type": sub_event_type,
            "event_count": event_count,
            "fatality_count": fatality_count,
            "geographic_id": geographic_id,
            "population_exposure": (
                population_exposure
            ),
            "centroid_latitude": (
                centroid_latitude
            ),
            "centroid_longitude": (
                centroid_longitude
            ),
            "reviewed_by": reviewed_by,
            "source_url": source_url,
            "created_at": created_at,
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
            "aggregate_id",
            self._create_aggregate_id(),
        )

    @property
    def is_strike(self):
        return self.sub_event_type in {
            "Air/drone strike",
            "Shelling/artillery/missile attack",
        }

    @property
    def is_political_violence(self):
        return self.disorder_type in {
            AggregateDisorderType.POLITICAL_VIOLENCE,
            (
                AggregateDisorderType
                .POLITICAL_VIOLENCE_DEMONSTRATIONS
            ),
        }

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

    @staticmethod
    def _coordinate(
        value,
        field_name,
        minimum,
        maximum,
    ):
        if (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
        ):
            raise TypeError(
                f"{field_name} must be numeric"
            )

        normalized = float(value)

        if (
            not math.isfinite(normalized)
            or not minimum <= normalized <= maximum
        ):
            raise ValueError(
                f"{field_name} must be between "
                f"{minimum} and {maximum}"
            )

        return normalized

    @staticmethod
    def _country_code(value):
        if value is None:
            return None

        if not isinstance(value, str):
            raise TypeError(
                "country_code must be a string or None"
            )

        normalized = value.strip().upper()

        if not _COUNTRY_CODE_PATTERN.fullmatch(
            normalized
        ):
            raise ValueError(
                "country_code must be an ISO "
                "alpha-2 country code"
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

    def _create_aggregate_id(self):
        payload = {
            "source_snapshot_date": (
                self.source_snapshot_date.isoformat()
            ),
            "week_end_date": (
                self.week_end_date.isoformat()
            ),
            "region": self.region,
            "country_name": self.country_name,
            "country_code": self.country_code,
            "admin1": self.admin1,
            "event_type": self.event_type.value,
            "sub_event_type": self.sub_event_type,
            "event_count": self.event_count,
            "fatality_count": self.fatality_count,
            "population_exposure": (
                self.population_exposure
            ),
            "disorder_type": (
                self.disorder_type.value
            ),
            "geographic_id": self.geographic_id,
            "centroid_latitude": (
                self.centroid_latitude
            ),
            "centroid_longitude": (
                self.centroid_longitude
            ),
            "source_url": self.source_url,
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
