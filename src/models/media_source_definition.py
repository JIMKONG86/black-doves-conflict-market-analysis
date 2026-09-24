from dataclasses import dataclass
from urllib.parse import urlparse
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from src.models.narrative_document import BROADCASTER_CONTROL_TYPES


@dataclass(frozen=True)
class MediaSourceDefinition:
    """Configuration for a news feed or supplied broadcast transcript."""

    source_id: str
    publisher_country_code: str
    publisher: str
    source_name: str
    source_layer: str
    medium: str
    delivery_method: str
    primary_language: str
    publication_timezone: str
    verification_role: str
    integration_status: str
    entrypoint_url: str | None = None
    feed_url: str | None = None
    active: bool = False
    access_constraints: str | None = None
    notes: str | None = None
    broadcaster_control: str = "UNKNOWN"

    def __post_init__(self):
        if not self.source_id.strip():
            raise ValueError("source_id must not be empty")
        country_code = self.publisher_country_code.strip().upper()
        if len(country_code) != 2 or not country_code.isalpha():
            raise ValueError(
                "publisher_country_code must be an ISO alpha-2 code"
            )
        object.__setattr__(self, "publisher_country_code", country_code)

        source_layer = self.source_layer.strip().upper()
        if source_layer not in {"NEWS", "TELEVISION"}:
            raise ValueError("source_layer must be NEWS or TELEVISION")
        object.__setattr__(self, "source_layer", source_layer)

        delivery = self.delivery_method.strip().upper()
        if delivery not in {"RSS", "TRANSCRIPT_CSV", "HTML"}:
            raise ValueError(
                "delivery_method must be RSS, HTML, or TRANSCRIPT_CSV"
            )
        object.__setattr__(self, "delivery_method", delivery)
        if delivery == "RSS" and not self.feed_url:
            raise ValueError("RSS media sources require feed_url")

        for field_name in ("entrypoint_url", "feed_url"):
            value = getattr(self, field_name)
            if value:
                parsed = urlparse(value.strip())
                if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                    raise ValueError(f"{field_name} must be an absolute HTTP(S) URL")

        try:
            ZoneInfo(self.publication_timezone)
        except ZoneInfoNotFoundError as error:
            raise ValueError(
                "publication_timezone must be a valid IANA timezone"
            ) from error

        broadcaster_control = self.broadcaster_control.strip().upper()
        if broadcaster_control not in BROADCASTER_CONTROL_TYPES:
            raise ValueError(
                "broadcaster_control must be STATE_CONTROLLED, "
                "PUBLIC_SERVICE_INDEPENDENT, PRIVATE_INDEPENDENT, or UNKNOWN"
            )
        object.__setattr__(self, "broadcaster_control", broadcaster_control)

    @classmethod
    def from_mapping(cls, values):
        return cls(**dict(values))
