import argparse
from datetime import date
from pathlib import Path

from src.data_access.configured_announcement_adapter import (
    ConfiguredAnnouncementAdapter,
)
from src.data_access.crawler import CrawlRequest, RetrievalStatus
from src.data_access.source_registry import SourceRegistry
from src.data_access.versioned_raw_document_repository import (
    VersionedRawDocumentRepository,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def parse_date(value):
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            "Dates must use ISO format YYYY-MM-DD"
        ) from error


def build_parser():
    parser = argparse.ArgumentParser(
        description="Collect official country announcements"
    )
    parser.add_argument("--source-id", default="DE_BMVG_NEWS")
    parser.add_argument("--query", default="*")
    parser.add_argument("--start-date", type=parse_date)
    parser.add_argument("--end-date", type=parse_date)
    parser.add_argument("--max-results", type=int, default=20)
    parser.add_argument(
        "--discovery-only",
        "--feed-only",
        dest="discovery_only",
        action="store_true",
        help="Discover links without fetching their HTML detail pages",
    )
    parser.add_argument(
        "--registry",
        type=Path,
        default=PROJECT_ROOT / "config" / "country_sources.json",
    )
    parser.add_argument(
        "--output-directory",
        type=Path,
        default=None,
    )
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    registry = SourceRegistry.from_json(args.registry)
    definition = registry.get(args.source_id)

    if (
        definition.delivery_method == "RSS_HTML"
        and not definition.detail_retrieval_enabled
        and not args.discovery_only
    ):
        print(
            "NOTICE: This source is configured for official-feed "
            "discovery only; HTML detail retrieval is disabled because "
            "the publisher rejects automated requests."
        )

    try:
        adapter = ConfiguredAnnouncementAdapter(definition)
    except NotImplementedError as error:
        print(f"Not implemented: {error}")
        return 2

    request = CrawlRequest(
        query=args.query,
        start_date=args.start_date,
        end_date=args.end_date,
        max_results=args.max_results,
        language=definition.primary_language,
        jurisdiction=definition.jurisdiction,
        include_undated=(args.start_date is None and args.end_date is None),
    )
    try:
        results = adapter.collect(
            request,
            fetch_details=(
                not args.discovery_only
                and definition.detail_retrieval_enabled
            ),
        )
    except ValueError as error:
        print(f"Invalid collection request: {error}")
        return 2

    output_directory = args.output_directory
    if output_directory is None:
        output_directory = (
            PROJECT_ROOT / "data" / "raw" / "contracts" / "usaspending"
            if definition.delivery_method == "USASPENDING_API"
            else PROJECT_ROOT / "data" / "raw" / "announcements"
        )
    repository = VersionedRawDocumentRepository(output_directory)
    file_paths = repository.save_all(results)

    successful = 0
    for result, file_path in zip(results, file_paths):
        if result.retrieval_status == RetrievalStatus.SUCCESS:
            successful += 1
        print(
            f"{result.retrieval_status.value.upper()}: "
            f"{result.title or result.url} -> {file_path}"
        )

    print(
        f"Collected {len(results)} record(s); "
        f"{successful} successful."
    )
    return 0 if successful else 2


if __name__ == "__main__":
    raise SystemExit(main())
