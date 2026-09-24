from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class MarketEvent:
    event_id: str
    event_date: date
    title: str
    event_type: str
    affected_country_codes: tuple[str, ...]
    verification_status: str
    source_name: str
    source_url: str
    notes: str = ""
