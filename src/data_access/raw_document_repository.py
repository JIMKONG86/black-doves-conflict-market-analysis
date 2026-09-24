import json
from hashlib import sha256
from pathlib import Path

from src.data_access.crawler import CrawlResult


class RawDocumentRepository:

    def __init__(
        self,
        directory="data/raw/research",
    ):
        self.directory = Path(directory)

        self.directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    def save(
        self,
        crawl_result,
        overwrite=False,
    ):
        self._validate_result(crawl_result)

        document_id = self._create_document_id(
            crawl_result
        )

        file_path = (
            self.directory / f"{document_id}.json"
        )

        if file_path.exists() and not overwrite:
            return file_path

        document = self._serialize(
            crawl_result=crawl_result,
            document_id=document_id,
        )

        with file_path.open(
            "w",
            encoding="utf-8",
        ) as output_file:
            json.dump(
                document,
                output_file,
                ensure_ascii=False,
                indent=2,
            )

        return file_path

    def save_all(
        self,
        crawl_results,
        overwrite=False,
    ):
        file_paths = []

        for crawl_result in crawl_results:
            file_path = self.save(
                crawl_result,
                overwrite=overwrite,
            )
            file_paths.append(file_path)

        return file_paths

    def contains(self, crawl_result):
        self._validate_result(crawl_result)

        document_id = self._create_document_id(
            crawl_result
        )

        file_path = (
            self.directory / f"{document_id}.json"
        )

        return file_path.exists()

    @staticmethod
    def _validate_result(crawl_result):
        if not isinstance(crawl_result, CrawlResult):
            raise TypeError(
                "crawl_result must be a CrawlResult"
            )

    @staticmethod
    def _create_document_id(crawl_result):
        document_url = (
            crawl_result.canonical_url
            or crawl_result.url
        )

        return sha256(
            document_url.encode("utf-8")
        ).hexdigest()

    @staticmethod
    def _serialize(
        crawl_result,
        document_id,
    ):
        return {
            "document_id": document_id,
            "source_id": crawl_result.source_id,
            "source_country_code": (
                crawl_result.source_country_code
            ),
            "source_name": crawl_result.source_name,
            "source_type": (
                crawl_result.source_type.value
            ),
            "url": crawl_result.url,
            "canonical_url": (
                crawl_result.canonical_url
            ),
            "query": crawl_result.query,
            "title": crawl_result.title,
            "publisher": crawl_result.publisher,
            "author": crawl_result.author,
            "published_at": (
                crawl_result.published_at.isoformat()
                if crawl_result.published_at
                else None
            ),
            "publication_timezone": (
                crawl_result.publication_timezone
            ),
            "date_precision": (
                crawl_result.date_precision
            ),
            "jurisdiction": (
                crawl_result.jurisdiction
            ),
            "language": crawl_result.language,
            "content": crawl_result.content,
            "content_hash": (
                crawl_result.content_hash
            ),
            "http_status": (
                crawl_result.http_status
            ),
            "error_message": (
                crawl_result.error_message
            ),
            "retrieval_status": (
                crawl_result.retrieval_status.value
            ),
            "retrieved_at": (
                crawl_result.retrieved_at.isoformat()
                if crawl_result.retrieved_at
                else None
            ),
        }
