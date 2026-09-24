from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class NormalizedDocument:
    document_id: str
    source_name: str
    source_type: str
    url: str
    canonical_url: str | None
    query: str
    title: str | None
    publisher: str | None
    author: str | None
    published_at: datetime | None
    language: str | None
    content: str
    raw_content_hash: str
    normalized_content_hash: str
    word_count: int
    character_count: int
    retrieved_at: datetime