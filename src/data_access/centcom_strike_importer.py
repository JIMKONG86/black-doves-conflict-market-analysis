import csv
import re

from dataclasses import dataclass
from datetime import date, datetime, time
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from src.models.claim_observation import (
    ClaimObservation,
    ClaimStatus,
    CountryLink,
    CountryRole,
    SourceChannel,
)
from src.models.strike_observation import StrikeObservation, StrikeType


CENTCOM_SOURCE_ID = "US_CENTCOM_PUBLIC_RELEASES"
CENTCOM_COUNTING_UNIT = "official_release_confirmed_operation_day"

_REQUIRED_COLUMNS = {
    "source_release_id",
    "event_date",
    "publication_date",
    "initiator_country_code",
    "affected_country_code",
    "strike_type",
    "operation_day_count",
    "verification_status",
    "counting_unit",
    "title",
    "description",
    "source_id",
    "source_url",
}
_COUNTRY_CODE_PATTERN = re.compile(r"[A-Z]{2}")


@dataclass(frozen=True)
class CentcomImportIssue:
    row_number: int
    source_release_id: str | None
    message: str


@dataclass(frozen=True)
class CentcomImportSummary:
    total_rows: int
    confirmed_rows: int
    saved_strikes: int
    duplicate_strikes: int
    skipped_unconfirmed: int
    failed_rows: int
    issues: tuple[CentcomImportIssue, ...]


class CentcomStrikeImporter:
    """Import manually verified CENTCOM strike-operation days.

    One row represents one distinct calendar day on which a CENTCOM release
    affirmatively says U.S. forces executed strikes. It never represents a
    target, munition, sortie or publication count.
    """

    def __init__(self, claim_repository, strike_repository):
        self.claim_repository = claim_repository
        self.strike_repository = strike_repository

    def import_csv(self, file_path, reviewed_by):
        csv_path = Path(file_path)
        if not csv_path.is_file():
            raise FileNotFoundError(
                f"CENTCOM strike CSV file not found: {csv_path}"
            )
        reviewer = self._required_text(reviewed_by, "reviewed_by")

        total_rows = 0
        confirmed_rows = 0
        saved_strikes = 0
        duplicate_strikes = 0
        skipped_unconfirmed = 0
        issues = []
        seen_operation_days = set()

        with csv_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
            reader = csv.DictReader(csv_file)
            self._validate_header(reader.fieldnames)

            for row_number, row in enumerate(reader, start=2):
                total_rows += 1
                release_id = self._optional_text(row.get("source_release_id"))
                status = (row.get("verification_status") or "").strip().upper()
                if status != "CONFIRMED":
                    skipped_unconfirmed += 1
                    continue

                confirmed_rows += 1
                try:
                    claim, strike, operation_key = self._build_observations(
                        row=row,
                        reviewed_by=reviewer,
                    )
                    if operation_key in seen_operation_days:
                        raise ValueError(
                            "duplicate CENTCOM operation day and affected country"
                        )
                    seen_operation_days.add(operation_key)

                    if self.strike_repository.contains(strike.strike_id):
                        duplicate_strikes += 1
                        continue

                    self._save_claim_if_missing(claim)
                    self.strike_repository.save(strike)
                    saved_strikes += 1
                except (KeyError, TypeError, ValueError) as error:
                    issues.append(
                        CentcomImportIssue(
                            row_number=row_number,
                            source_release_id=release_id,
                            message=str(error),
                        )
                    )

        return CentcomImportSummary(
            total_rows=total_rows,
            confirmed_rows=confirmed_rows,
            saved_strikes=saved_strikes,
            duplicate_strikes=duplicate_strikes,
            skipped_unconfirmed=skipped_unconfirmed,
            failed_rows=len(issues),
            issues=tuple(issues),
        )

    def _build_observations(self, row, reviewed_by):
        release_id = self._required_text(
            row.get("source_release_id"), "source_release_id"
        )
        event_date = self._date(row.get("event_date"), "event_date")
        publication_date = self._date(
            row.get("publication_date"), "publication_date"
        )
        if event_date > publication_date:
            raise ValueError("event_date must not be after publication_date")

        source_id = self._required_text(row.get("source_id"), "source_id")
        if source_id != CENTCOM_SOURCE_ID:
            raise ValueError(f"source_id must be {CENTCOM_SOURCE_ID}")

        counting_unit = self._required_text(
            row.get("counting_unit"), "counting_unit"
        )
        if counting_unit != CENTCOM_COUNTING_UNIT:
            raise ValueError(
                f"counting_unit must be {CENTCOM_COUNTING_UNIT}"
            )
        if self._integer(row.get("operation_day_count")) != 1:
            raise ValueError("operation_day_count must equal 1")

        initiator_code = self._country_code(
            row.get("initiator_country_code"), "initiator_country_code"
        )
        if initiator_code != "US":
            raise ValueError("initiator_country_code must be US")
        affected_code = self._country_code(
            row.get("affected_country_code"), "affected_country_code"
        )

        source_url = self._centcom_url(row.get("source_url"))
        title = self._required_text(row.get("title"), "title")
        description = self._required_text(row.get("description"), "description")
        strike_type = self._strike_type(row.get("strike_type"))
        location = self._optional_text(row.get("location"))
        weapon_system = self._optional_text(row.get("weapon_system"))
        created_at = datetime.combine(
            publication_date,
            time.min,
            tzinfo=ZoneInfo("America/New_York"),
        )

        document_id = self._identifier(source_url)
        candidate_id = self._identifier(
            "centcom-strike-candidate-v1",
            release_id,
            event_date.isoformat(),
            affected_code,
        )
        review_id = self._identifier(
            "centcom-strike-review-v1",
            release_id,
            event_date.isoformat(),
            reviewed_by,
        )
        country_links = (
            CountryLink("US", CountryRole.PUBLISHER),
            CountryLink("US", CountryRole.INITIATOR),
            CountryLink(affected_code, CountryRole.AFFECTED),
        )
        claim_text = f"{title}. {description}"

        claim = ClaimObservation(
            candidate_id=candidate_id,
            document_id=document_id,
            review_id=review_id,
            claim_type="strike_event",
            claim_status=ClaimStatus.CONFIRMED,
            source_channel=SourceChannel.GOVERNMENT,
            claim_text=claim_text,
            reviewed_by=reviewed_by,
            country_links=country_links,
            publisher_name="U.S. Central Command",
            statement_author="USCENTCOM",
            original_source_name="CENTCOM public release",
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
            claim_status=ClaimStatus.CONFIRMED,
            source_channel=SourceChannel.GOVERNMENT,
            affected_country_code=affected_code,
            initiator_country_code="US",
            location=location,
            weapon_system=weapon_system,
            description=description,
            reviewed_by=reviewed_by,
            source_url=source_url,
            created_at=created_at,
        )
        return claim, strike, (event_date, affected_code)

    def _save_claim_if_missing(self, claim):
        contains = getattr(self.claim_repository, "contains", None)
        if callable(contains) and contains(claim.candidate_id):
            return False
        try:
            self.claim_repository.save(claim)
        except ValueError as error:
            if not any(
                marker in str(error).casefold()
                for marker in ("already", "duplicate")
            ):
                raise
            return False
        return True

    @staticmethod
    def _validate_header(field_names):
        if field_names is None:
            raise ValueError("CENTCOM strike CSV file has no header")
        missing = _REQUIRED_COLUMNS - set(field_names)
        if missing:
            raise ValueError(
                "CENTCOM strike CSV is missing required columns: "
                + ", ".join(sorted(missing))
            )

    @staticmethod
    def _date(value, field_name):
        text = CentcomStrikeImporter._required_text(value, field_name)
        try:
            return date.fromisoformat(text)
        except ValueError as error:
            raise ValueError(f"{field_name} must use YYYY-MM-DD") from error

    @staticmethod
    def _integer(value):
        text = CentcomStrikeImporter._required_text(
            value, "operation_day_count"
        )
        if not re.fullmatch(r"\d+", text):
            raise ValueError("operation_day_count must be an integer")
        return int(text)

    @staticmethod
    def _country_code(value, field_name):
        code = CentcomStrikeImporter._required_text(value, field_name).upper()
        if not _COUNTRY_CODE_PATTERN.fullmatch(code):
            raise ValueError(f"{field_name} must be an ISO alpha-2 code")
        return code

    @staticmethod
    def _strike_type(value):
        text = CentcomStrikeImporter._required_text(value, "strike_type")
        try:
            return StrikeType(text.casefold())
        except ValueError as error:
            allowed = ", ".join(item.value for item in StrikeType)
            raise ValueError(f"strike_type must be one of: {allowed}") from error

    @staticmethod
    def _centcom_url(value):
        url = CentcomStrikeImporter._required_text(value, "source_url")
        parsed = urlparse(url)
        if (
            parsed.scheme != "https"
            or parsed.netloc.casefold() != "www.centcom.mil"
            or not parsed.path.startswith("/MEDIA/PUBLIC-RELEASES/Article/")
        ):
            raise ValueError("source_url must be an official CENTCOM release URL")
        return url

    @staticmethod
    def _identifier(*parts):
        payload = "|".join(parts)
        return sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def _required_text(value, field_name):
        if not isinstance(value, str):
            raise TypeError(f"{field_name} must be a string")
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError(f"{field_name} must not be empty")
        return normalized

    @staticmethod
    def _optional_text(value):
        if value is None:
            return None
        if not isinstance(value, str):
            raise TypeError("optional text values must be strings or None")
        return " ".join(value.split()) or None
