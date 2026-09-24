import json
import re
from datetime import timezone
from pathlib import Path

from src.data_access.crawler import CrawlResult
from src.data_access.raw_document_repository import RawDocumentRepository


class VersionedRawDocumentRepository:
    """Append-only raw storage for reproducible source revisions."""

    def __init__(self, directory="data/raw/announcements"):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)

    def save(self, crawl_result):
        if not isinstance(crawl_result, CrawlResult):
            raise TypeError("crawl_result must be a CrawlResult")

        document_id = RawDocumentRepository._create_document_id(crawl_result)
        source_key = self._safe_source_key(
            crawl_result.source_id or crawl_result.source_name
        )
        version_directory = self.directory / source_key / document_id
        version_directory.mkdir(parents=True, exist_ok=True)

        timestamp = crawl_result.retrieved_at.astimezone(timezone.utc).strftime(
            "%Y%m%dT%H%M%S%f%z"
        )
        fingerprint = (
            crawl_result.content_hash[:12]
            if crawl_result.content_hash
            else crawl_result.retrieval_status.value
        )
        version_id = f"{timestamp}_{fingerprint}"
        file_path = version_directory / f"{version_id}.json"

        suffix = 1
        while file_path.exists():
            file_path = version_directory / f"{version_id}_{suffix}.json"
            suffix += 1

        document = RawDocumentRepository._serialize(
            crawl_result=crawl_result,
            document_id=document_id,
        )
        document["version_id"] = file_path.stem

        with file_path.open("x", encoding="utf-8") as output_file:
            json.dump(document, output_file, ensure_ascii=False, indent=2)

        return file_path

    def save_all(self, crawl_results):
        return [self.save(result) for result in crawl_results]

    def versions(self, crawl_result):
        if not isinstance(crawl_result, CrawlResult):
            raise TypeError("crawl_result must be a CrawlResult")
        document_id = RawDocumentRepository._create_document_id(crawl_result)
        source_key = self._safe_source_key(
            crawl_result.source_id or crawl_result.source_name
        )
        version_directory = self.directory / source_key / document_id
        if not version_directory.exists():
            return []
        return sorted(version_directory.glob("*.json"))

    @staticmethod
    def _safe_source_key(value):
        normalized = re.sub(r"[^A-Za-z0-9_-]+", "_", value.strip())
        return normalized.strip("_") or "unknown_source"
