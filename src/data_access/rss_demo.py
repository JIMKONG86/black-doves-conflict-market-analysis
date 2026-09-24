from collections import Counter
from pathlib import Path


from src.data_access.crawler import (
    CrawlRequest,
    RetrievalStatus,
)
from src.data_access.normalized_document_repository import (
    NormalizedDocumentRepository,
)
from src.data_access.pdf_document_fetcher import (
    PdfDocumentFetcher,
)
from src.data_access.configured_announcement_adapter import (
    ConfiguredAnnouncementAdapter,
)
from src.data_access.source_registry import (
    SourceRegistry,
)
from src.data_access.versioned_raw_document_repository import (
    VersionedRawDocumentRepository,
)
from src.services.candidate_extractor import (
    CandidateExtractor,
)
from src.data_access.candidate_observation_repository import (
    CandidateObservationRepository,
)

from src.services.document_normalizer import (
    DocumentNormalizer,
)


def main():
    project_root = Path(__file__).resolve().parents[2]
    registry = SourceRegistry.from_json(
        project_root / "config" / "country_sources.json"
    )
    definition = registry.get("DE_BMVG_NEWS")
    adapter = ConfiguredAnnouncementAdapter(definition)

    request = CrawlRequest(
        query="*",
        max_results=5,
        language="de",
        jurisdiction="Germany",
    )

    raw_repository = VersionedRawDocumentRepository()

    normalized_repository = (
        NormalizedDocumentRepository()
    )
    candidate_repository = (
    CandidateObservationRepository()
)

    pdf_fetcher = PdfDocumentFetcher()
    normalizer = DocumentNormalizer()

    candidate_extractor = CandidateExtractor(
    context_window=500
    )
    results = adapter.collect(request)

    if not results:
        print("No RSS entries found.")
        return

    for crawl_result in results:
        document = crawl_result

        is_pdf = (
            crawl_result.url
            .casefold()
            .endswith(".pdf")
        )

        if (
            crawl_result.retrieval_status
            == RetrievalStatus.SUCCESS
            and is_pdf
        ):
            document = pdf_fetcher.fetch(
                crawl_result
            )

        print(
            "\nStatus:",
            document.retrieval_status.value,
        )
        print("Title:", document.title)
        print("Published:", document.published_at)
        print("Publisher:", document.publisher)
        print("URL:", document.url)
        print("HTTP status:", document.http_status)
        print("Raw hash:", document.content_hash)

        text_length = (
            len(document.content)
            if document.content
            else 0
        )

        print(
            "Extracted characters:",
            text_length,
        )

        if document.error_message:
            print(
                "Message:",
                document.error_message,
            )

        can_normalize = (
            document.retrieval_status
            == RetrievalStatus.SUCCESS
            and document.content is not None
        )

        raw_file_path = raw_repository.save(
            document,
        )

        print(
            "Raw document saved:",
            raw_file_path,
        )

        if not can_normalize:
            continue

        normalized_document = (
            normalizer.normalize(document)
        )

        print(
            "Normalized characters:",
            normalized_document.character_count,
        )
        print(
            "Normalized words:",
            normalized_document.word_count,
        )
        print(
            "Normalized hash:",
            normalized_document
            .normalized_content_hash,
        )

        preview = (
            normalized_document.content[:250]
            .replace("\n", " ")
        )

        print(
            "Text preview:",
            preview,
        )

        normalized_file_path = (
            normalized_repository.save(
                normalized_document,
                overwrite=True,
            )
        )

        print(
            "Normalized document saved:",
            normalized_file_path,
        )

        candidates = candidate_extractor.extract(
            normalized_document
        )

        candidate_counts = Counter(
            candidate.candidate_type.value
            for candidate in candidates
        )

        print(
            "Candidate observations:",
            len(candidates),
        )
        print(
            "Candidate types:",
            dict(candidate_counts),
        )

        candidate_file_path = (
            candidate_repository.save(
                document_id=(
                    normalized_document.document_id
                ),
                normalized_content_hash=(
                    normalized_document
                    .normalized_content_hash
                ),
                candidates=candidates,
                overwrite=True,
            )
        )

        print(
            "Candidate observations saved:",
            candidate_file_path,
        )

        for candidate in candidates[:10]:
            print(
                "\nCandidate type:",
                candidate.candidate_type.value,
            )
            print(
                "Candidate value:",
                candidate.value,
            )
            print(
                "Review status:",
                candidate.review_status.value,
            )
            print(
                "Context:",
                candidate.context,
            )


if __name__ == "__main__":
    main()
