import argparse
from datetime import date
from pathlib import Path

from src.services.narrative_corpus_builder import NarrativeCorpusBuilder


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
        description="Build reviewed state/news/TV narrative datasets"
    )
    parser.add_argument("--start-date", type=parse_date, default=date(2026, 1, 1))
    parser.add_argument("--end-date", type=parse_date, default=date(2026, 8, 18))
    parser.add_argument(
        "--announcements",
        type=Path,
        default=PROJECT_ROOT / "data" / "raw" / "announcements",
    )
    parser.add_argument(
        "--media",
        type=Path,
        default=PROJECT_ROOT / "data" / "raw" / "media",
    )
    parser.add_argument(
        "--media-registry",
        type=Path,
        default=PROJECT_ROOT / "config" / "media_sources.json",
    )
    parser.add_argument(
        "--centcom",
        type=Path,
        default=(
            PROJECT_ROOT
            / "data"
            / "validated"
            / "centcom_us_strike_operation_days.csv"
        ),
    )
    parser.add_argument(
        "--reviews",
        type=Path,
        default=PROJECT_ROOT / "data" / "validated" / "narrative_reviews",
    )
    parser.add_argument(
        "--output-directory",
        type=Path,
        default=PROJECT_ROOT / "data" / "analysis",
    )
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    builder = NarrativeCorpusBuilder()
    try:
        documents = builder.build(
            start_date=args.start_date,
            end_date=args.end_date,
            announcement_directory=args.announcements,
            media_directory=args.media,
            media_registry_file=args.media_registry,
            centcom_file=args.centcom,
            review_directory=args.reviews,
        )
        paths = builder.export(
            documents,
            args.output_directory / "narrative_documents.csv",
            args.output_directory / "narrative_category_summary.csv",
            args.output_directory / "narrative_coverage.csv",
        )
    except (FileNotFoundError, TypeError, ValueError) as error:
        print(f"Narrative corpus failed: {error}")
        return 2
    print(f"Narrative documents: {len(documents)}")
    print(
        "Manually reviewed: "
        + str(
            sum(
                item.classification_status == "MANUALLY_REVIEWED"
                for item in documents
            )
        )
    )
    for path in paths:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
