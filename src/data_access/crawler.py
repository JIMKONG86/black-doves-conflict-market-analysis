from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from enum import Enum
from hashlib import sha256


class SourceType(Enum):
    API = "api"
    RSS = "rss"
    HTML = "html"
    FILE = "file"


class RetrievalStatus(Enum):
    SUCCESS = "success"
    EMPTY = "empty"
    BLOCKED = "blocked"
    ERROR = "error"


@dataclass
class CrawlRequest:
    query: str
    start_date: date | None = None
    end_date: date | None = None
    max_results: int = 50
    language: str | None = None
    jurisdiction: str | None = None
    include_undated: bool = True

    def __post_init__(self):
        self.query = self.query.strip()

        if not self.query:
            raise ValueError("Crawl query must not be empty")

        if self.max_results <= 0:
            raise ValueError(
                "max_results must be greater than zero"
            )

        if (
            self.start_date is not None
            and self.end_date is not None
            and self.start_date > self.end_date
        ):
            raise ValueError(
                "start_date must not be after end_date"
            )


@dataclass
class CrawlResult:
    source_name: str
    source_type: SourceType
    url: str
    source_id: str | None = None
    source_country_code: str | None = None
    query: str | None = None
    canonical_url: str | None = None
    title: str | None = None
    publisher: str | None = None
    author: str | None = None
    published_at: datetime | None = None
    publication_timezone: str | None = None
    date_precision: str | None = None
    jurisdiction: str | None = None
    language: str | None = None
    content: str | None = None
    http_status: int | None = None
    error_message: str | None = None
    retrieval_status: RetrievalStatus = (
        RetrievalStatus.SUCCESS
    )
    retrieved_at: datetime = field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )
    content_hash: str | None = field(
        init=False,
        default=None,
    )

    def __post_init__(self):
        self.source_name = self.source_name.strip()
        self.url = self.url.strip()

        if not self.source_name:
            raise ValueError(
                "source_name must not be empty"
            )

        if not self.url:
            raise ValueError("url must not be empty")

        if self.source_country_code:
            self.source_country_code = (
                self.source_country_code.strip().upper()
            )
            if (
                len(self.source_country_code) != 2
                or not self.source_country_code.isalpha()
            ):
                raise ValueError(
                    "source_country_code must be an ISO alpha-2 code"
                )

        if self.content:
            normalized_content = " ".join(
                self.content.split()
            )

            self.content_hash = sha256(
                normalized_content.encode("utf-8")
            ).hexdigest()


class SourceAdapter(ABC):

    @property
    @abstractmethod
    def source_name(self):
        """Return the name of the connected source."""

    @abstractmethod
    def collect(self, request):
        """Collect and return CrawlResult objects."""
