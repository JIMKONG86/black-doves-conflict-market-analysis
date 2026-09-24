import csv
import re

from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from hashlib import sha256
from pathlib import Path

from src.models.claim_observation import (
    ClaimObservation,
    ClaimStatus,
    CountryLink,
    CountryRole,
    SourceChannel,
)
from src.models.strike_observation import (
    StrikeObservation,
    StrikeType,
)


_REQUIRED_COLUMNS = {
    "event_id_cnty",
    "event_date",
    "sub_event_type",
}

_DRONE_PATTERN = re.compile(
    r"\b(drone|drones|uav|uavs|unmanned aerial)\b",
    re.IGNORECASE,
)

_MISSILE_PATTERN = re.compile(
    r"\b(ballistic missile|cruise missile|missile|missiles|rocket|rockets)\b",
    re.IGNORECASE,
)

_ARTILLERY_PATTERN = re.compile(
    r"\b(artillery|shelling|mortar|mortars|howitzer|howitzers)\b",
    re.IGNORECASE,
)

_NAVAL_PATTERN = re.compile(
    r"\b(naval|warship|warships|sea-launched)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class AcledImportIssue:
    row_number: int
    event_id: str | None
    message: str


@dataclass(frozen=True)
class AcledImportSummary:
    total_rows: int
    strike_rows: int
    saved_strikes: int
    duplicate_strikes: int
    skipped_non_strikes: int
    failed_rows: int
    issues: tuple[AcledImportIssue, ...]


class AcledStrikeImporter:
    def __init__(
        self,
        claim_repository,
        strike_repository,
    ):
        self.claim_repository = claim_repository
        self.strike_repository = strike_repository

    def import_csv(
        self,
        file_path,
        reviewed_by,
        source_url,
        affected_country_code=None,
        initiator_country_code=None,
    ):
        csv_path = Path(file_path)

        if not csv_path.is_file():
            raise FileNotFoundError(
                f"ACLED CSV file not found: {csv_path}"
            )

        reviewed_by = self._required_text(
            reviewed_by,
            "reviewed_by",
        )
        source_url = self._required_text(
            source_url,
            "source_url",
        )
        default_affected_code = self._country_code(
            affected_country_code,
            "affected_country_code",
            required=False,
        )
        default_initiator_code = self._country_code(
            initiator_country_code,
            "initiator_country_code",
            required=False,
        )

        total_rows = 0
        strike_rows = 0
        saved_strikes = 0
        duplicate_strikes = 0
        skipped_non_strikes = 0
        issues = []

        with csv_path.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as csv_file:
            reader = csv.DictReader(csv_file)
            self._validate_header(reader.fieldnames)

            for row_number, row in enumerate(
                reader,
                start=2,
            ):
                total_rows += 1

                strike_type = self._strike_type(row)

                if strike_type is None:
                    skipped_non_strikes += 1
                    continue

                strike_rows += 1

                try:
                    claim, strike = self._build_observations(
                        row=row,
                        strike_type=strike_type,
                        reviewed_by=reviewed_by,
                        source_url=source_url,
                        default_affected_code=(
                            default_affected_code
                        ),
                        default_initiator_code=(
                            default_initiator_code
                        ),
                    )

                    if self.strike_repository.contains(
                        strike.strike_id
                    ):
                        duplicate_strikes += 1
                        continue

                    self._save_claim_if_missing(claim)
                    self.strike_repository.save(strike)
                    saved_strikes += 1
                except (
                    KeyError,
                    TypeError,
                    ValueError,
                ) as error:
                    issues.append(
                        AcledImportIssue(
                            row_number=row_number,
                            event_id=self._optional_text(
                                row.get("event_id_cnty")
                            ),
                            message=str(error),
                        )
                    )

        return AcledImportSummary(
            total_rows=total_rows,
            strike_rows=strike_rows,
            saved_strikes=saved_strikes,
            duplicate_strikes=duplicate_strikes,
            skipped_non_strikes=(
                skipped_non_strikes
            ),
            failed_rows=len(issues),
            issues=tuple(issues),
        )

    def _build_observations(
        self,
        row,
        strike_type,
        reviewed_by,
        source_url,
        default_affected_code,
        default_initiator_code,
    ):
        event_id = self._required_text(
            row.get("event_id_cnty"),
            "event_id_cnty",
        )
        event_date = self._parse_event_date(
            row.get("event_date")
        )
        created_at = self._parse_timestamp(
            row.get("timestamp"),
            event_date,
        )
        affected_code = self._row_country_code(
            row=row,
            row_field_names=(
                "affected_country_code",
                "country_code",
                "iso_alpha2",
            ),
            default_value=default_affected_code,
            field_name="affected_country_code",
            required=True,
        )
        initiator_code = self._row_country_code(
            row=row,
            row_field_names=(
                "initiator_country_code",
                "actor1_country_code",
            ),
            default_value=default_initiator_code,
            field_name="initiator_country_code",
            required=False,
        )
        claim_text = self._claim_text(
            row,
            event_id,
        )
        location = self._location(row)
        weapon_system = self._weapon_system(row)
        version_key = self._version_key(
            event_id,
            created_at,
        )

        candidate_id = self._identifier(
            "acled-candidate",
            version_key,
        )
        document_id = self._identifier(
            "acled-document",
            source_url,
            event_id,
            created_at.isoformat(),
        )
        review_id = self._identifier(
            "acled-import-review-v1",
            version_key,
            reviewed_by,
        )

        country_links = [
            CountryLink(
                country_code=affected_code,
                role=CountryRole.AFFECTED,
            )
        ]

        if (
            initiator_code is not None
            and initiator_code != affected_code
        ):
            country_links.append(
                CountryLink(
                    country_code=initiator_code,
                    role=CountryRole.ALLEGED_ACTOR,
                )
            )

        claim = ClaimObservation(
            candidate_id=candidate_id,
            document_id=document_id,
            review_id=review_id,
            claim_type="strike_event",
            claim_status=ClaimStatus.REPORTED,
            source_channel=SourceChannel.NGO,
            claim_text=claim_text,
            reviewed_by=reviewed_by,
            country_links=tuple(country_links),
            publisher_name="ACLED",
            original_source_name=(
                self._optional_text(row.get("source"))
            ),
            source_url=source_url,
            created_at=created_at,
        )

        strike = StrikeObservation(
            candidate_id=candidate_id,
            document_id=document_id,
            review_id=review_id,
            claim_id=claim.claim_id,
            event_date=event_date,
            strike_type=strike_type,
            claim_status=ClaimStatus.REPORTED,
            source_channel=SourceChannel.NGO,
            affected_country_code=affected_code,
            initiator_country_code=initiator_code,
            location=location,
            weapon_system=weapon_system,
            description=claim_text,
            reviewed_by=reviewed_by,
            source_url=source_url,
            created_at=created_at,
        )

        return claim, strike

    def _save_claim_if_missing(self, claim):
        contains = getattr(
            self.claim_repository,
            "contains",
            None,
        )

        if callable(contains) and contains(
            claim.claim_id
        ):
            return False

        try:
            self.claim_repository.save(claim)
        except ValueError as error:
            message = str(error).casefold()

            if not any(
                marker in message
                for marker in (
                    "already exists",
                    "duplicate",
                )
            ):
                raise

            return False

        return True

    @staticmethod
    def _validate_header(field_names):
        if field_names is None:
            raise ValueError(
                "ACLED CSV file has no header"
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
                "ACLED CSV is missing required "
                f"columns: {missing}"
            )

    @classmethod
    def _strike_type(cls, row):
        sub_event_type = (
            cls._optional_text(
                row.get("sub_event_type")
            )
            or ""
        ).casefold()
        notes = (
            cls._optional_text(row.get("notes"))
            or ""
        )
        searchable_text = " ".join(
            cls._optional_text(row.get(field_name))
            or ""
            for field_name in (
                "sub_event_type",
                "event_type",
                "notes",
            )
        )

        if sub_event_type == "air/drone strike":
            if _DRONE_PATTERN.search(searchable_text):
                return StrikeType.DRONE_STRIKE

            return StrikeType.AIRSTRIKE

        if (
            sub_event_type
            == "shelling/artillery/missile attack"
        ):
            if _MISSILE_PATTERN.search(notes):
                return StrikeType.MISSILE_STRIKE

            if _ARTILLERY_PATTERN.search(notes):
                return StrikeType.ARTILLERY_STRIKE

            return StrikeType.ARTILLERY_STRIKE

        if _NAVAL_PATTERN.search(searchable_text) and (
            "strike" in searchable_text.casefold()
            or "attack" in searchable_text.casefold()
        ):
            return StrikeType.NAVAL_STRIKE

        return None

    @staticmethod
    def _parse_event_date(value):
        text = AcledStrikeImporter._required_text(
            value,
            "event_date",
        )

        try:
            return date.fromisoformat(text)
        except ValueError as error:
            raise ValueError(
                "event_date must use YYYY-MM-DD"
            ) from error

    @staticmethod
    def _parse_timestamp(value, event_date):
        text = AcledStrikeImporter._optional_text(value)

        if text is None:
            return datetime.combine(
                event_date,
                time.min,
                tzinfo=timezone.utc,
            )

        try:
            numeric_timestamp = float(text)

            if numeric_timestamp > 10_000_000_000:
                numeric_timestamp /= 1000

            return datetime.fromtimestamp(
                numeric_timestamp,
                tz=timezone.utc,
            )
        except (OverflowError, ValueError):
            pass

        try:
            parsed = datetime.fromisoformat(
                text.replace("Z", "+00:00")
            )
        except ValueError as error:
            raise ValueError(
                "timestamp must be a Unix timestamp "
                "or ISO-8601 datetime"
            ) from error

        if (
            parsed.tzinfo is None
            or parsed.utcoffset() is None
        ):
            parsed = parsed.replace(
                tzinfo=timezone.utc
            )

        return parsed.astimezone(timezone.utc)

    @classmethod
    def _claim_text(cls, row, event_id):
        notes = cls._optional_text(row.get("notes"))

        if notes is not None:
            return notes

        event_name = (
            cls._optional_text(
                row.get("sub_event_type")
            )
            or cls._optional_text(
                row.get("event_type")
            )
            or "Strike event"
        )
        location = cls._location(row)

        if location is None:
            return f"{event_name}; ACLED event {event_id}."

        return (
            f"{event_name} reported in {location}; "
            f"ACLED event {event_id}."
        )

    @classmethod
    def _location(cls, row):
        for field_name in (
            "location",
            "admin3",
            "admin2",
            "admin1",
            "country",
        ):
            value = cls._optional_text(
                row.get(field_name)
            )

            if value is not None:
                return value

        return None

    @classmethod
    def _weapon_system(cls, row):
        notes = cls._optional_text(row.get("notes")) or ""
        sub_event_type = (
            cls._optional_text(
                row.get("sub_event_type")
            )
            or ""
        )
        searchable_text = f"{notes} {sub_event_type}"

        if _DRONE_PATTERN.search(notes):
            return "Drone/UAV"

        missile_match = _MISSILE_PATTERN.search(
            notes
        )
        if missile_match:
            return missile_match.group(0).title()

        artillery_match = _ARTILLERY_PATTERN.search(
            notes
        )
        if artillery_match:
            return artillery_match.group(0).title()

        if _DRONE_PATTERN.search(searchable_text):
            return "Drone/UAV"

        if _NAVAL_PATTERN.search(searchable_text):
            return "Naval weapon system"

        return None

    @classmethod
    def _row_country_code(
        cls,
        row,
        row_field_names,
        default_value,
        field_name,
        required,
    ):
        for row_field_name in row_field_names:
            value = cls._optional_text(
                row.get(row_field_name)
            )

            if value is not None:
                return cls._country_code(
                    value,
                    field_name,
                    required=required,
                )

        return cls._country_code(
            default_value,
            field_name,
            required=required,
        )

    @staticmethod
    def _country_code(
        value,
        field_name,
        required,
    ):
        if value is None:
            if required:
                raise ValueError(
                    f"{field_name} is required; "
                    "provide it in the CSV or CLI"
                )

            return None

        if not isinstance(value, str):
            raise TypeError(
                f"{field_name} must be a string"
            )

        normalized = value.strip().upper()

        if not re.fullmatch(r"[A-Z]{2}", normalized):
            raise ValueError(
                f"{field_name} must be an ISO "
                "alpha-2 country code"
            )

        return normalized

    @staticmethod
    def _required_text(value, field_name):
        if not isinstance(value, str):
            raise TypeError(
                f"{field_name} must be a string"
            )

        cleaned = value.strip()

        if not cleaned:
            raise ValueError(
                f"{field_name} must not be empty"
            )

        return cleaned

    @staticmethod
    def _optional_text(value):
        if value is None:
            return None

        if not isinstance(value, str):
            return str(value).strip() or None

        return value.strip() or None

    @staticmethod
    def _version_key(event_id, created_at):
        return "|".join(
            [
                event_id.strip(),
                created_at.isoformat(),
            ]
        )

    @staticmethod
    def _identifier(*parts):
        identity = "|".join(parts)
        return sha256(
            identity.encode("utf-8")
        ).hexdigest()