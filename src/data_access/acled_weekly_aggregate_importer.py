import csv

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlparse

from src.models.weekly_conflict_aggregate import (
    AggregateDisorderType,
    AggregateEventType,
    WeeklyConflictAggregate,
)


_REQUIRED_COLUMNS = {
    "WEEK",
    "REGION",
    "COUNTRY",
    "ADMIN1",
    "EVENT_TYPE",
    "SUB_EVENT_TYPE",
    "EVENTS",
    "FATALITIES",
    "POPULATION_EXPOSURE",
    "DISORDER_TYPE",
    "ID",
    "CENTROID_LATITUDE",
    "CENTROID_LONGITUDE",
}

_COUNTRY_CODES = {
    "bahrain": "BH",
    "iran": "IR",
    "iraq": "IQ",
    "israel": "IL",
    "jordan": "JO",
    "kuwait": "KW",
    "lebanon": "LB",
    "oman": "OM",
    "palestine": "PS",
    "qatar": "QA",
    "saudi arabia": "SA",
    "syria": "SY",
    "turkey": "TR",
    "united arab emirates": "AE",
    "yemen": "YE",
}

_EVENT_TYPES = {
    "battles": AggregateEventType.BATTLES,
    "explosions/remote violence": (
        AggregateEventType
        .EXPLOSIONS_REMOTE_VIOLENCE
    ),
    "protests": AggregateEventType.PROTESTS,
    "riots": AggregateEventType.RIOTS,
    "strategic developments": (
        AggregateEventType
        .STRATEGIC_DEVELOPMENTS
    ),
    "violence against civilians": (
        AggregateEventType
        .VIOLENCE_AGAINST_CIVILIANS
    ),
}

_DISORDER_TYPES = {
    "demonstrations": (
        AggregateDisorderType.DEMONSTRATIONS
    ),
    "political violence": (
        AggregateDisorderType.POLITICAL_VIOLENCE
    ),
    "political violence; demonstrations": (
        AggregateDisorderType
        .POLITICAL_VIOLENCE_DEMONSTRATIONS
    ),
    "strategic developments": (
        AggregateDisorderType
        .STRATEGIC_DEVELOPMENTS
    ),
}

_STRIKE_SUB_EVENT_TYPES = {
    "air/drone strike": "Air/drone strike",
    "shelling/artillery/missile attack": (
        "Shelling/artillery/missile attack"
    ),
}

_MONTH_NUMBERS = {
    "january": 1,
    "januar": 1,
    "february": 2,
    "februar": 2,
    "march": 3,
    "märz": 3,
    "maerz": 3,
    "april": 4,
    "may": 5,
    "mai": 5,
    "june": 6,
    "juni": 6,
    "july": 7,
    "juli": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "oktober": 10,
    "november": 11,
    "december": 12,
    "dezember": 12,
}


@dataclass(frozen=True)
class AcledAggregateImportIssue:
    row_number: int
    week: str | None
    country: str | None
    admin1: str | None
    message: str


@dataclass(frozen=True)
class AcledAggregateImportSummary:
    total_rows: int
    selected_rows: int
    saved_aggregates: int
    duplicate_aggregates: int
    skipped_countries: int
    skipped_non_strikes: int
    failed_rows: int
    issues: tuple[
        AcledAggregateImportIssue,
        ...,
    ]


class AcledWeeklyAggregateImporter:
    def __init__(self, aggregate_repository):
        self.aggregate_repository = (
            aggregate_repository
        )

    def import_csv(
        self,
        file_path,
        reviewed_by,
        source_url,
        source_snapshot_date,
        countries=None,
        strike_only=False,
    ):
        csv_path = Path(file_path)

        if not csv_path.is_file():
            raise FileNotFoundError(
                "ACLED aggregate CSV file not "
                f"found: {csv_path}"
            )

        if not isinstance(strike_only, bool):
            raise TypeError(
                "strike_only must be a boolean"
            )

        reviewed_by = self._required_text(
            reviewed_by,
            "reviewed_by",
        )
        source_url = self._source_url(
            source_url,
        )
        snapshot_date = self._parse_date(
            source_snapshot_date,
            "source_snapshot_date",
        )
        country_filter = self._country_filter(
            countries
        )

        total_rows = 0
        selected_rows = 0
        saved_aggregates = 0
        duplicate_aggregates = 0
        skipped_countries = 0
        skipped_non_strikes = 0
        issues = []
        pending_aggregates = []
        pending_identifiers = set()

        with csv_path.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as csv_file:
            dialect = self._detect_dialect(
                csv_file
            )
            reader = csv.DictReader(
                csv_file,
                dialect=dialect,
            )
            field_names = self._normalize_header(
                reader.fieldnames
            )
            self._validate_header(field_names)

            for row_number, source_row in enumerate(
                reader,
                start=2,
            ):
                total_rows += 1
                row = self._normalize_row(source_row)
                country_name = self._optional_text(
                    row.get("COUNTRY")
                )

                if (
                    country_filter is not None
                    and (
                        country_name is None
                        or country_name.casefold()
                        not in country_filter
                    )
                ):
                    skipped_countries += 1
                    continue

                sub_event_type = self._optional_text(
                    row.get("SUB_EVENT_TYPE")
                )

                if (
                    strike_only
                    and sub_event_type is not None
                    and sub_event_type.casefold()
                    not in _STRIKE_SUB_EVENT_TYPES
                ):
                    skipped_non_strikes += 1
                    continue

                selected_rows += 1

                try:
                    aggregate = self._build_aggregate(
                        row=row,
                        reviewed_by=reviewed_by,
                        source_url=source_url,
                        source_snapshot_date=(
                            snapshot_date
                        ),
                    )

                    if (
                        aggregate.aggregate_id
                        in pending_identifiers
                        or self.aggregate_repository.contains(
                            aggregate.aggregate_id
                        )
                    ):
                        duplicate_aggregates += 1
                        continue

                    pending_aggregates.append(
                        aggregate
                    )
                    pending_identifiers.add(
                        aggregate.aggregate_id
                    )
                except (
                    KeyError,
                    TypeError,
                    ValueError,
                ) as error:
                    issues.append(
                        AcledAggregateImportIssue(
                            row_number=row_number,
                            week=self._optional_text(
                                row.get("WEEK")
                            ),
                            country=country_name,
                            admin1=self._optional_text(
                                row.get("ADMIN1")
                            ),
                            message=str(error),
                        )
                    )

        if pending_aggregates:
            save_many = getattr(
                self.aggregate_repository,
                "save_many",
                None,
            )

            if callable(save_many):
                save_many(pending_aggregates)
            else:
                for aggregate in pending_aggregates:
                    self.aggregate_repository.save(
                        aggregate
                    )

            saved_aggregates = len(
                pending_aggregates
            )

        return AcledAggregateImportSummary(
            total_rows=total_rows,
            selected_rows=selected_rows,
            saved_aggregates=saved_aggregates,
            duplicate_aggregates=(
                duplicate_aggregates
            ),
            skipped_countries=skipped_countries,
            skipped_non_strikes=(
                skipped_non_strikes
            ),
            failed_rows=len(issues),
            issues=tuple(issues),
        )

    def _build_aggregate(
        self,
        row,
        reviewed_by,
        source_url,
        source_snapshot_date,
    ):
        country_name = self._required_text(
            row.get("COUNTRY"),
            "COUNTRY",
        )
        sub_event_type = self._required_text(
            row.get("SUB_EVENT_TYPE"),
            "SUB_EVENT_TYPE",
        )
        canonical_sub_event_type = (
            _STRIKE_SUB_EVENT_TYPES.get(
                sub_event_type.casefold(),
                sub_event_type,
            )
        )

        return WeeklyConflictAggregate(
            source_snapshot_date=(
                source_snapshot_date
            ),
            week_end_date=self._parse_date(
                row.get("WEEK"),
                "WEEK",
            ),
            region=self._required_text(
                row.get("REGION"),
                "REGION",
            ),
            country_name=country_name,
            country_code=_COUNTRY_CODES.get(
                country_name.casefold()
            ),
            admin1=self._required_text(
                row.get("ADMIN1"),
                "ADMIN1",
            ),
            event_type=self._enum_value(
                row.get("EVENT_TYPE"),
                "EVENT_TYPE",
                _EVENT_TYPES,
            ),
            sub_event_type=(
                canonical_sub_event_type
            ),
            event_count=self._integer(
                row.get("EVENTS"),
                "EVENTS",
            ),
            fatality_count=self._integer(
                row.get("FATALITIES"),
                "FATALITIES",
            ),
            population_exposure=(
                self._optional_integer(
                    row.get("POPULATION_EXPOSURE"),
                    "POPULATION_EXPOSURE",
                )
            ),
            disorder_type=self._enum_value(
                row.get("DISORDER_TYPE"),
                "DISORDER_TYPE",
                _DISORDER_TYPES,
            ),
            geographic_id=self._integer(
                row.get("ID"),
                "ID",
            ),
            centroid_latitude=self._number(
                row.get("CENTROID_LATITUDE"),
                "CENTROID_LATITUDE",
            ),
            centroid_longitude=self._number(
                row.get("CENTROID_LONGITUDE"),
                "CENTROID_LONGITUDE",
            ),
            reviewed_by=reviewed_by,
            source_url=source_url,
        )

    @staticmethod
    def _detect_dialect(csv_file):
        sample = csv_file.read(65_536)
        csv_file.seek(0)

        try:
            return csv.Sniffer().sniff(
                sample,
                delimiters=",;\t",
            )
        except csv.Error:
            return csv.excel

    @staticmethod
    def _normalize_header(field_names):
        if field_names is None:
            return None

        return [
            field_name.strip().upper()
            if isinstance(field_name, str)
            else field_name
            for field_name in field_names
        ]

    @staticmethod
    def _normalize_row(source_row):
        return {
            key.strip().upper(): value
            for key, value in source_row.items()
            if isinstance(key, str)
        }

    @staticmethod
    def _validate_header(field_names):
        if field_names is None:
            raise ValueError(
                "ACLED aggregate CSV file has no "
                "header"
            )

        missing_columns = (
            _REQUIRED_COLUMNS
            - set(field_names)
        )

        if missing_columns:
            missing = ", ".join(
                sorted(missing_columns)
            )
            raise ValueError(
                "ACLED aggregate CSV is missing "
                f"required columns: {missing}"
            )

    @classmethod
    def _country_filter(cls, countries):
        if countries is None:
            return None

        if isinstance(countries, str):
            countries = (countries,)

        try:
            normalized = {
                cls._required_text(
                    country,
                    "country",
                ).casefold()
                for country in countries
            }
        except TypeError as error:
            raise TypeError(
                "countries must be an iterable "
                "of country names"
            ) from error

        if not normalized:
            raise ValueError(
                "countries must not be empty"
            )

        return normalized

    @classmethod
    def _enum_value(
        cls,
        value,
        field_name,
        value_map,
    ):
        normalized = cls._required_text(
            value,
            field_name,
        )

        try:
            return value_map[
                normalized.casefold()
            ]
        except KeyError as error:
            raise ValueError(
                f"Unsupported {field_name}: "
                f"{normalized}"
            ) from error

    @staticmethod
    def _parse_date(value, field_name):
        if (
            isinstance(value, date)
            and not isinstance(value, datetime)
        ):
            return value

        if isinstance(value, datetime):
            return value.date()

        text = (
            AcledWeeklyAggregateImporter
            ._required_text(
                value,
                field_name,
            )
        )

        for date_format in (
            "%Y-%m-%d",
            "%Y-%m-%d %H:%M:%S",
            "%d.%m.%Y",
            "%m/%d/%Y",
        ):
            try:
                return datetime.strptime(
                    text,
                    date_format,
                ).date()
            except ValueError:
                continue

        named_date_parts = text.casefold().split("-")

        if len(named_date_parts) == 3:
            day_text, month_text, year_text = (
                named_date_parts
            )
            month_number = _MONTH_NUMBERS.get(
                month_text
            )

            if (
                day_text.isdigit()
                and month_number is not None
                and year_text.isdigit()
            ):
                try:
                    return date(
                        int(year_text),
                        month_number,
                        int(day_text),
                    )
                except ValueError:
                    pass

        raise ValueError(
            f"{field_name} must use YYYY-MM-DD, "
            "DD.MM.YYYY, MM/DD/YYYY or "
            "DD-Month-YYYY"
        )

    @classmethod
    def _integer(cls, value, field_name):
        number = cls._decimal(
            value,
            field_name,
        )

        if number != number.to_integral_value():
            raise ValueError(
                f"{field_name} must be an integer"
            )

        return int(number)

    @classmethod
    def _optional_integer(
        cls,
        value,
        field_name,
    ):
        if cls._optional_text(value) is None:
            return None

        return cls._integer(
            value,
            field_name,
        )

    @classmethod
    def _number(cls, value, field_name):
        return float(
            cls._decimal(
                value,
                field_name,
            )
        )

    @classmethod
    def _decimal(cls, value, field_name):
        text = cls._required_text(
            value,
            field_name,
        ).replace("\u00a0", "").replace(" ", "")

        if "," in text and "." in text:
            if text.rfind(",") > text.rfind("."):
                text = text.replace(".", "")
                text = text.replace(",", ".")
            else:
                text = text.replace(",", "")
        elif "," in text:
            text = text.replace(",", ".")

        try:
            return Decimal(text)
        except InvalidOperation as error:
            raise ValueError(
                f"{field_name} must be numeric"
            ) from error

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

    @staticmethod
    def _optional_text(value):
        if value is None:
            return None

        if not isinstance(value, str):
            return str(value).strip() or None

        return value.strip() or None
