from dataclasses import dataclass
import re
from urllib.parse import urlparse
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


@dataclass(frozen=True)
class SourceDefinition:
    """Machine-readable definition of an official country source."""

    source_id: str
    country_code: str
    country_name: str
    jurisdiction: str
    publisher: str
    source_name: str
    entrypoint_url: str
    source_type: str
    delivery_method: str
    primary_language: str
    publication_timezone: str
    supported_categories: tuple[str, ...]
    source_priority: int
    automation_tier: str
    timestamp_quality: str
    archive_stability: str
    verification_role: str
    integration_status: str
    feed_url: str | None = None
    access_constraints: str | None = None
    notes: str | None = None
    active: bool = True
    listing_page_url_template: str | None = None
    detail_url_prefixes: tuple[str, ...] = ()
    max_listing_pages: int = 1
    discovery_limit: int = 50
    request_timeout_seconds: int = 30
    detail_url_id_pattern: str | None = None
    detail_url_template: str | None = None
    detail_retrieval_enabled: bool = True
    awarding_agency_name: str | None = None

    def __post_init__(self):
        if not self.source_id.strip():
            raise ValueError("source_id must not be empty")

        country_code = self.country_code.strip().upper()
        if len(country_code) != 2 or not country_code.isalpha():
            raise ValueError("country_code must be an ISO alpha-2 code")
        object.__setattr__(self, "country_code", country_code)

        self._validate_url(self.entrypoint_url, "entrypoint_url")
        if self.feed_url:
            self._validate_url(self.feed_url, "feed_url")
        if self.listing_page_url_template:
            try:
                sample_listing_url = self.listing_page_url_template.format(
                    page=2
                )
            except (KeyError, IndexError, ValueError) as error:
                raise ValueError(
                    "listing_page_url_template must support {page}"
                ) from error
            self._validate_url(
                sample_listing_url,
                "listing_page_url_template",
            )

        if bool(self.detail_url_id_pattern) != bool(self.detail_url_template):
            raise ValueError(
                "detail_url_id_pattern and detail_url_template must be set together"
            )
        if self.detail_url_id_pattern:
            try:
                pattern = re.compile(self.detail_url_id_pattern)
            except re.error as error:
                raise ValueError("detail_url_id_pattern must be valid regex") from error
            if "id" not in pattern.groupindex:
                raise ValueError(
                    "detail_url_id_pattern must define a named id group"
                )
            try:
                sample_detail_url = self.detail_url_template.format(id="123")
            except (KeyError, IndexError, ValueError) as error:
                raise ValueError(
                    "detail_url_template must support {id}"
                ) from error
            self._validate_url(sample_detail_url, "detail_url_template")

        if any(
            not prefix.startswith("/")
            for prefix in self.detail_url_prefixes
        ):
            raise ValueError(
                "detail_url_prefixes must contain absolute URL paths"
            )

        if self.source_priority <= 0:
            raise ValueError("source_priority must be greater than zero")

        if self.max_listing_pages <= 0:
            raise ValueError("max_listing_pages must be greater than zero")

        if self.discovery_limit <= 0:
            raise ValueError("discovery_limit must be greater than zero")

        if self.request_timeout_seconds <= 0:
            raise ValueError("request_timeout_seconds must be greater than zero")

        if not self.supported_categories:
            raise ValueError("supported_categories must not be empty")

        if not isinstance(self.detail_retrieval_enabled, bool):
            raise ValueError("detail_retrieval_enabled must be a boolean")

        try:
            ZoneInfo(self.publication_timezone)
        except ZoneInfoNotFoundError as error:
            raise ValueError(
                "publication_timezone must be a valid IANA timezone"
            ) from error

    @classmethod
    def from_mapping(cls, values):
        data = dict(values)
        data["supported_categories"] = tuple(
            data.get("supported_categories", ())
        )
        data["detail_url_prefixes"] = tuple(
            data.get("detail_url_prefixes", ())
        )
        return cls(**data)

    @staticmethod
    def _validate_url(value, field_name):
        parsed = urlparse(value.strip())
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError(f"{field_name} must be an absolute HTTP(S) URL")
