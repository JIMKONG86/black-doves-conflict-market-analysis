import re
import unicodedata
from hashlib import sha256

from src.data_access.crawler import (
    CrawlResult,
    RetrievalStatus,
)
from src.models.normalized_document import (
    NormalizedDocument,
)


class DocumentNormalizer:

    def normalize(self, crawl_result):
        self._validate(crawl_result)

        normalized_content = self._normalize_text(
            crawl_result.content
        )

        normalized_content_hash = sha256(
            normalized_content.encode("utf-8")
        ).hexdigest()

        document_id = self._create_document_id(
            crawl_result
        )

        return NormalizedDocument(
            document_id=document_id,
            source_name=self._normalize_metadata(
                crawl_result.source_name
            ),
            source_type=(
                crawl_result.source_type.value
            ),
            url=crawl_result.url,
            canonical_url=(
                crawl_result.canonical_url
            ),
            query=self._normalize_metadata(
                crawl_result.query
            ),
            title=self._normalize_optional_metadata(
                crawl_result.title
            ),
            publisher=(
                self._normalize_optional_metadata(
                    crawl_result.publisher
                )
            ),
            author=self._normalize_optional_metadata(
                crawl_result.author
            ),
            published_at=crawl_result.published_at,
            language=crawl_result.language,
            content=normalized_content,
            raw_content_hash=(
                crawl_result.content_hash
            ),
            normalized_content_hash=(
                normalized_content_hash
            ),
            word_count=len(
                normalized_content.split()
            ),
            character_count=len(
                normalized_content
            ),
            retrieved_at=crawl_result.retrieved_at,
        )

    @staticmethod
    def _validate(crawl_result):
        if not isinstance(crawl_result, CrawlResult):
            raise TypeError(
                "crawl_result must be a CrawlResult"
            )

        if (
            crawl_result.retrieval_status
            != RetrievalStatus.SUCCESS
        ):
            raise ValueError(
                "Only successful crawl results "
                "can be normalized"
            )

        if (
            not isinstance(crawl_result.content, str)
            or not crawl_result.content.strip()
        ):
            raise ValueError(
                "crawl_result must contain text"
            )

        if not crawl_result.content_hash:
            raise ValueError(
                "crawl_result must have a content hash"
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

    @classmethod
    def _normalize_optional_metadata(
        cls,
        value,
    ):
        if value is None:
            return None

        normalized_value = (
            cls._normalize_metadata(value)
        )

        return normalized_value or None

    @classmethod
    def _normalize_metadata(cls, value):
        normalized_value = cls._normalize_text(
            value
        )

        return " ".join(
            normalized_value.split()
        )

    @staticmethod
    def _normalize_text(value):
        normalized_value = unicodedata.normalize(
            "NFKC",
            value,
        )

        normalized_value = (
            normalized_value
            .replace("\r\n", "\n")
            .replace("\r", "\n")
            .replace("\t", " ")
            .replace("\f", " ")
            .replace("\v", " ")
        )

        normalized_value = "".join(
            character
            for character in normalized_value
            if (
                character == "\n"
                or not unicodedata
                .category(character)
                .startswith("C")
            )
        )

        normalized_value = re.sub(
            r"[^\S\n]+",
            " ",
            normalized_value,
        )

        normalized_value = re.sub(
            r" *\n *",
            "\n",
            normalized_value,
        )

        normalized_value = re.sub(
            r"\n{3,}",
            "\n\n",
            normalized_value,
        )

        return normalized_value.strip()