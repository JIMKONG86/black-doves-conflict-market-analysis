import csv

from datetime import date
from pathlib import Path

from src.models.market_event import MarketEvent


_REQUIRED_COLUMNS = {
    "event_id",
    "event_date",
    "title",
    "event_type",
    "affected_country_codes",
    "verification_status",
    "source_name",
    "source_url",
    "notes",
}


def load_market_events(file_path):
    path = Path(file_path)

    if not path.is_file():
        raise FileNotFoundError(f"Market-event file not found: {path}")

    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = _REQUIRED_COLUMNS - set(reader.fieldnames or ())

        if missing:
            raise ValueError(
                "Market-event file is missing required columns: "
                + ", ".join(sorted(missing))
            )

        events = tuple(_event(row, row_number) for row_number, row in enumerate(reader, 2))

    if not events:
        raise ValueError("Market-event file must contain at least one row")

    identifiers = [event.event_id for event in events]

    if len(identifiers) != len(set(identifiers)):
        raise ValueError("Market-event file contains duplicate event_id")

    return tuple(sorted(events, key=lambda event: (event.event_date, event.event_id)))


def _event(row, row_number):
    values = {key: (row.get(key) or "").strip() for key in _REQUIRED_COLUMNS}
    required_values = _REQUIRED_COLUMNS - {"notes"}
    blank = sorted(key for key in required_values if not values[key])

    if blank:
        raise ValueError(
            f"Market-event row {row_number} has blank fields: "
            + ", ".join(blank)
        )

    try:
        event_date = date.fromisoformat(values["event_date"])
    except ValueError as error:
        raise ValueError(
            f"Market-event row {row_number} has invalid event_date: "
            f"{values['event_date']}"
        ) from error

    country_codes = tuple(
        code.strip().upper()
        for code in values["affected_country_codes"].split("|")
        if code.strip()
    )

    if not country_codes:
        raise ValueError(
            f"Market-event row {row_number} has no affected country codes"
        )

    return MarketEvent(
        event_id=values["event_id"],
        event_date=event_date,
        title=values["title"],
        event_type=values["event_type"],
        affected_country_codes=country_codes,
        verification_status=values["verification_status"],
        source_name=values["source_name"],
        source_url=values["source_url"],
        notes=values["notes"],
    )
