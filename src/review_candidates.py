import argparse

from collections.abc import Sequence
from pathlib import Path

from src.data_access.candidate_observation_repository import (
    CandidateObservationRepository,
)
from src.data_access.candidate_review_repository import (
    CandidateReviewRepository,
)
from src.data_access.claim_observation_repository import (
    ClaimObservationRepository,
)
from src.data_access.strike_observation_repository import (
    StrikeObservationRepository,
)
from src.models.candidate_observation import (
    CandidateObservation,
)
from src.services.candidate_review_queue import (
    CandidateReviewQueue,
)


DEFAULT_CANDIDATE_DIRECTORY = Path(
    "data/processed/candidates"
)


def discover_document_ids(
    candidate_directory: Path,
) -> list[str]:
    if not candidate_directory.exists():
        return []

    candidate_files = sorted(
        candidate_directory.glob("*.json")
    )

    return [
        file_path.stem
        for file_path in candidate_files
        if file_path.is_file()
    ]


def load_candidates(
    repository: CandidateObservationRepository,
    document_ids: Sequence[str],
) -> list[CandidateObservation]:
    candidates = []

    for document_id in document_ids:
        document_candidates = (
            repository.load(
                document_id
            )
        )

        candidates.extend(
            document_candidates
        )

    return candidates


def create_argument_parser(
) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Review extracted "
            "candidate observations."
        )
    )

    parser.add_argument(
        "--reviewer",
        required=True,
        help=(
            "Name or identifier "
            "of the reviewer."
        ),
    )

    parser.add_argument(
        "--document-id",
        action="append",
        dest="document_ids",
        help=(
            "Review one specific document. "
            "May be supplied multiple times."
        ),
    )

    parser.add_argument(
        "--review-existing",
        action="store_true",
        help=(
            "Include candidates that already "
            "have a stored review."
        ),
    )

    return parser


def main(
    arguments: Sequence[str] | None = None,
) -> int:
    parser = create_argument_parser()

    parsed_arguments = parser.parse_args(
        arguments
    )

    candidate_repository = (
        CandidateObservationRepository()
    )

    review_repository = (
        CandidateReviewRepository()
    )

    claim_repository = (
        ClaimObservationRepository()
    )

    strike_repository = (
        StrikeObservationRepository()
    )

    document_ids = (
        parsed_arguments.document_ids
    )

    if not document_ids:
        document_ids = discover_document_ids(
            DEFAULT_CANDIDATE_DIRECTORY
        )

    if not document_ids:
        print(
            "No stored candidate "
            "documents found."
        )
        return 0

    print(
        "Candidate documents found:",
        len(document_ids),
    )

    try:
        candidates = load_candidates(
            repository=candidate_repository,
            document_ids=document_ids,
        )
    except (
        OSError,
        TypeError,
        ValueError,
    ) as exception:
        print(
            "Candidate data could "
            "not be loaded:"
        )
        print(exception)
        return 1

    if not candidates:
        print(
            "No candidate observations found."
        )
        return 0

    print(
        "Candidate observations loaded:",
        len(candidates),
    )

    review_queue = CandidateReviewQueue(
        repository=review_repository,
        claim_repository=claim_repository,
        strike_repository=strike_repository,
    )

    try:
        saved_reviews = review_queue.run(
            candidates=candidates,
            reviewed_by=(
                parsed_arguments.reviewer
            ),
            review_existing=(
                parsed_arguments.review_existing
            ),
        )
    except (
        OSError,
        TypeError,
        ValueError,
    ) as exception:
        print(
            "\nReview could not be saved:"
        )
        print(exception)
        return 1

    print(
        "\nReview session completed."
    )

    print(
        "New reviews:",
        len(saved_reviews),
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )