import tempfile
import unittest

from pathlib import Path
from types import SimpleNamespace

from src.review_candidates import (
    create_argument_parser,
    discover_document_ids,
    load_candidates,
)


class FakeCandidateRepository:
    def __init__(self, documents):
        self.documents = documents
        self.loaded_document_ids = []

    def load(self, document_id):
        self.loaded_document_ids.append(
            document_id
        )

        return self.documents.get(
            document_id,
            [],
        )


class TestReviewCandidates(unittest.TestCase):
    def test_discovers_document_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            candidate_directory = Path(directory)

            (
                candidate_directory
                / "document-b.json"
            ).write_text(
                "{}",
                encoding="utf-8",
            )

            (
                candidate_directory
                / "document-a.json"
            ).write_text(
                "{}",
                encoding="utf-8",
            )

            (
                candidate_directory
                / "notes.txt"
            ).write_text(
                "not a candidate file",
                encoding="utf-8",
            )

            document_ids = (
                discover_document_ids(
                    candidate_directory
                )
            )

        self.assertEqual(
            document_ids,
            [
                "document-a",
                "document-b",
            ],
        )

    def test_returns_empty_for_missing_directory(
        self,
    ):
        candidate_directory = Path(
            "directory-that-does-not-exist"
        )

        document_ids = discover_document_ids(
            candidate_directory
        )

        self.assertEqual(
            document_ids,
            [],
        )

    def test_loads_candidates_from_documents(
        self,
    ):
        first_candidate = SimpleNamespace(
            candidate_id="candidate-1"
        )

        second_candidate = SimpleNamespace(
            candidate_id="candidate-2"
        )

        repository = FakeCandidateRepository(
            {
                "document-a": [
                    first_candidate,
                ],
                "document-b": [
                    second_candidate,
                ],
            }
        )

        candidates = load_candidates(
            repository=repository,
            document_ids=[
                "document-a",
                "document-b",
            ],
        )

        self.assertEqual(
            candidates,
            [
                first_candidate,
                second_candidate,
            ],
        )

        self.assertEqual(
            repository.loaded_document_ids,
            [
                "document-a",
                "document-b",
            ],
        )

    def test_parses_multiple_document_ids(self):
        parser = create_argument_parser()

        arguments = parser.parse_args(
            [
                "--reviewer",
                "Markus",
                "--document-id",
                "document-a",
                "--document-id",
                "document-b",
                "--review-existing",
            ]
        )

        self.assertEqual(
            arguments.reviewer,
            "Markus",
        )
        self.assertEqual(
            arguments.document_ids,
            [
                "document-a",
                "document-b",
            ],
        )
        self.assertTrue(
            arguments.review_existing
        )


if __name__ == "__main__":
    unittest.main()