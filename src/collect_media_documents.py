import argparse
from datetime import date
from pathlib import Path

from src.data_access.broadcast_transcript_csv_importer import (
    BroadcastTranscriptCsvImporter,
)
from src.data_access.crawler import CrawlRequest, RetrievalStatus
from src.data_access.media_rss_connector import MediaRssConnector
from src.data_access.media_source_registry import MediaSourceRegistry
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
        description="Collect configured news items or import TV transcripts"
    )
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--query", default="*")
    parser.add_argument("--start-date", type=parse_date)
    parser.add_argument("--end-date", type=parse_date)
    parser.add_argument("--max-results", type=int, default=200)
    parser.add_argument(
        "--input-file",
        type=Path,
        help="Required only for TRANSCRIPT_CSV sources",
    )
    parser.add_argument(
        "--registry",
        type=Path,
        default=PROJECT_ROOT / "config" / "media_sources.json",
    )
    parser.add_argument(
        "--output-directory",
        type=Path,
        default=PROJECT_ROOT / "data" / "raw" / "media",
    )
    return parser


def _create_connector(definition, input_file=None):
    if definition.delivery_method == "RSS":
        return MediaRssConnector(definition)
    if definition.delivery_method == "TRANSCRIPT_CSV":
        if input_file is None:
            raise ValueError("--input-file is required for transcript sources")
        return BroadcastTranscriptCsvImporter(definition, input_file)
    raise NotImplementedError(definition.delivery_method)


def main(argv=None):
    args = build_parser().parse_args(argv)
    registry = MediaSourceRegistry.from_json(args.registry)
    definition = registry.get(args.source_id)
    if not definition.active:
        print(
            "NOTICE: Source is configured but inactive. Collection is allowed "
            "only when deliberately addressed by --source-id; inclusion in the "
            "primary comparison still requires documented sampling approval."
        )
    try:
        connector = _create_connector(definition, args.input_file)
        results = connector.collect(
            CrawlRequest(
                query=args.query,
                start_date=args.start_date,
                end_date=args.end_date,
                max_results=args.max_results,
                language=definition.primary_language,
                jurisdiction=definition.publisher_country_code,
                include_undated=False,
            )
        )
    except (FileNotFoundError, TypeError, ValueError) as error:
        print(f"Collection failed: {error}")
        return 2

    repository = VersionedRawDocumentRepository(args.output_directory)
    paths = repository.save_all(results)
    successful = sum(
        result.retrieval_status == RetrievalStatus.SUCCESS for result in results
    )
    for result, path in zip(results, paths):
        print(
            f"{result.retrieval_status.value.upper()}: "
            f"{result.title or result.url} -> {path}"
        )
    print(f"Collected {len(results)} record(s); {successful} successful.")
    return 0 if successful else 2


if __name__ == "__main__":
    raise SystemExit(main())
