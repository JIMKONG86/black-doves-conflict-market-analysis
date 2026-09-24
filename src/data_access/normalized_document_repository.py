import json
from pathlib import Path

from src.models.normalized_document import (
    NormalizedDocument,
)


class NormalizedDocumentRepository:

    def __init__(
        self,
        directory="data/processed/research",
    ):
        self.directory = Path(directory)

        self.directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    def save(
        self,
        normalized_document,
        overwrite=False,
    ):
        self._validate_document(
            normalized_document
        )

        file_path = self._create_file_path(
            normalized_document
        )

        if file_path.exists() and not overwrite:
            return file_path

        document = self._serialize(
            normalized_document
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
        normalized_documents,
        overwrite=False,
    ):
        file_paths = []

        for normalized_document in (
            normalized_documents
        ):
            file_path = self.save(
                normalized_document,
                overwrite=overwrite,
            )
            file_paths.append(file_path)

        return file_paths

    def contains(self, normalized_document):
        self._validate_document(
            normalized_document
        )

        file_path = self._create_file_path(
            normalized_document
        )

        return file_path.exists()

    def _create_file_path(
        self,
        normalized_document,
    ):
        return (
            self.directory
            / f"{normalized_document.document_id}.json"
        )

    @staticmethod
    def _validate_document(
        normalized_document,
    ):
        if not isinstance(
            normalized_document,
            NormalizedDocument,
        ):
            raise TypeError(
                "normalized_document must be "
                "a NormalizedDocument"
            )

    @staticmethod
    def _serialize(normalized_document):
        return {
            "document_id": (
                normalized_document.document_id
            ),
            "source_name": (
                normalized_document.source_name
            ),
            "source_type": (
                normalized_document.source_type
            ),
            "url": normalized_document.url,
            "canonical_url": (
                normalized_document.canonical_url
            ),
            "query": normalized_document.query,
            "title": normalized_document.title,
            "publisher": (
                normalized_document.publisher
            ),
            "author": normalized_document.author,
            "published_at": (
                normalized_document
                .published_at
                .isoformat()
                if normalized_document.published_at
                else None
            ),
            "language": (
                normalized_document.language
            ),
            "content": normalized_document.content,
            "raw_content_hash": (
                normalized_document
                .raw_content_hash
            ),
            "normalized_content_hash": (
                normalized_document
                .normalized_content_hash
            ),
            "word_count": (
                normalized_document.word_count
            ),
            "character_count": (
                normalized_document
                .character_count
            ),
            "retrieved_at": (
                normalized_document
                .retrieved_at
                .isoformat()
            ),
        }