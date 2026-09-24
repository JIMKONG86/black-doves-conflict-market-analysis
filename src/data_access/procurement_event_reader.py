import csv

from datetime import date
from pathlib import Path

from src.models.procurement_event import (
    ProcurementEvent,
    ProcurementEventType,
    ProcurementVerificationStatus,
)


_REQUIRED_COLUMNS = {
    "announcement_date",
    "company_name",
    "company_ticker",
    "buyer_name",
    "buyer_country_code",
    "event_type",
    "title",
    "systems",
    "source_name",
    "source_url",
    "contract_value_eur",
    "aggregate_package_value_eur",
    "value_description",
    "is_air_defence",
    "verification_status",
    "related_initiative",
    "reviewed_by",
    "notes",
}


class ProcurementEventReader:
    def read(self, input_file):
        input_path = Path(input_file)

        if not input_path.is_file():
            raise FileNotFoundError(
                f"Procurement event CSV not found: {input_path}"
            )

        with input_path.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as file_handle:
            reader = csv.DictReader(file_handle)
            fieldnames = set(reader.fieldnames or ())
            missing_columns = _REQUIRED_COLUMNS - fieldnames

            if missing_columns:
                missing = ", ".join(sorted(missing_columns))
                raise ValueError(
                    "Procurement event CSV is missing required "
                    f"columns: {missing}"
                )

            events = []

            for row_number, row in enumerate(reader, start=2):
                try:
                    events.append(self._event(row))
                except (TypeError, ValueError) as error:
                    raise ValueError(
                        f"Invalid procurement event row {row_number}: "
                        f"{error}"
                    ) from error

        if not events:
            raise ValueError(
                "Procurement event CSV must contain at least one event"
            )

        identifiers = [event.event_id for event in events]

        if len(identifiers) != len(set(identifiers)):
            raise ValueError(
                "Procurement event CSV contains duplicate events"
            )

        return tuple(sorted(events, key=lambda item: item.announcement_date))

    @classmethod
    def _event(cls, row):
        try:
            announcement_date = date.fromisoformat(
                row["announcement_date"].strip()
            )
        except (AttributeError, ValueError) as error:
            raise ValueError(
                "announcement_date must use YYYY-MM-DD"
            ) from error

        try:
            event_type = ProcurementEventType(
                row["event_type"].strip().casefold()
            )
        except (AttributeError, ValueError) as error:
            allowed = ", ".join(
                event.value for event in ProcurementEventType
            )
            raise ValueError(
                f"event_type must be one of: {allowed}"
            ) from error

        try:
            verification_status = ProcurementVerificationStatus(
                row["verification_status"].strip().casefold()
            )
        except (AttributeError, ValueError) as error:
            allowed = ", ".join(
                status.value
                for status in ProcurementVerificationStatus
            )
            raise ValueError(
                "verification_status must be one of: "
                f"{allowed}"
            ) from error

        systems = tuple(
            value.strip()
            for value in row["systems"].split("|")
            if value.strip()
        )

        return ProcurementEvent(
            announcement_date=announcement_date,
            company_name=row["company_name"],
            company_ticker=row["company_ticker"],
            buyer_name=row["buyer_name"],
            buyer_country_code=cls._optional_text(
                row["buyer_country_code"]
            ),
            event_type=event_type,
            title=row["title"],
            systems=systems,
            source_name=row["source_name"],
            source_url=row["source_url"],
            contract_value_eur=cls._optional_float(
                row["contract_value_eur"],
                "contract_value_eur",
            ),
            aggregate_package_value_eur=cls._optional_float(
                row["aggregate_package_value_eur"],
                "aggregate_package_value_eur",
            ),
            value_description=row["value_description"],
            is_air_defence=cls._boolean(row["is_air_defence"]),
            verification_status=verification_status,
            related_initiative=cls._optional_text(
                row["related_initiative"]
            ),
            reviewed_by=row["reviewed_by"],
            notes=cls._optional_text(row["notes"]),
        )

    @staticmethod
    def _optional_text(value):
        normalized = value.strip()
        return normalized or None

    @staticmethod
    def _optional_float(value, field_name):
        normalized = value.strip()

        if not normalized:
            return None

        try:
            return float(normalized)
        except ValueError as error:
            raise ValueError(f"{field_name} must be numeric") from error

    @staticmethod
    def _boolean(value):
        normalized = value.strip().casefold()

        if normalized == "true":
            return True

        if normalized == "false":
            return False

        raise ValueError("is_air_defence must be true or false")
