import json
import tempfile
import unittest

from src.data_access.candidate_observation_repository import (
    CandidateObservationRepository,
)
from src.models.candidate_observation import (
    CandidateObservation,
    CandidateType,
)


class TestCandidateObservationRepository(
    unittest.TestCase
):

    def setUp(self):
        self.temporary_directory = (
            tempfile.TemporaryDirectory()
        )
        self.addCleanup(
            self.temporary_directory.cleanup
        )

        self.repository = (
            CandidateObservationRepository(
                directory=(
                    self.temporary_directory.name
                )
            )
        )

    def create_candidate(
        self,
        document_id="document-123",
        content_hash="content-hash-123",
        value="25.08.2026",
        candidate_type=CandidateType.DATE,
        start_index=20,
        end_index=30,
    ):
        return CandidateObservation(
            document_id=document_id,
            candidate_type=candidate_type,
            value=value,
            context=(
                "Document context containing "
                f"{value}"
            ),
            start_index=start_index,
            end_index=end_index,
            source_url=(
                "https://example.com/document.pdf"
            ),
            normalized_content_hash=(
                content_hash
            ),
            extraction_method=(
                "regex:test_pattern"
            ),
        )

    def test_saves_candidates(self):
        candidate = self.create_candidate()

        file_path = self.repository.save(
            document_id="document-123",
            normalized_content_hash=(
                "content-hash-123"
            ),
            candidates=[candidate],
        )

        self.assertTrue(file_path.exists())

        with file_path.open(
            "r",
            encoding="utf-8",
        ) as input_file:
            stored_document = json.load(
                input_file
            )

        self.assertEqual(
            stored_document["candidate_count"],
            1,
        )
        self.assertEqual(
            stored_document["candidates"][0][
                "value"
            ],
            "25.08.2026",
        )
        self.assertEqual(
            stored_document["candidates"][0][
                "review_status"
            ],
            "pending",
        )

    def test_saves_empty_candidate_list(self):
        file_path = self.repository.save(
            document_id="document-123",
            normalized_content_hash=(
                "content-hash-123"
            ),
            candidates=[],
        )

        with file_path.open(
            "r",
            encoding="utf-8",
        ) as input_file:
            stored_document = json.load(
                input_file
            )

        self.assertEqual(
            stored_document["candidate_count"],
            0,
        )
        self.assertEqual(
            stored_document["candidates"],
            [],
        )

    def test_does_not_overwrite_by_default(self):
        candidate = self.create_candidate()

        file_path = self.repository.save(
            document_id="document-123",
            normalized_content_hash=(
                "content-hash-123"
            ),
            candidates=[candidate],
        )

        self.repository.save(
            document_id="document-123",
            normalized_content_hash=(
                "content-hash-123"
            ),
            candidates=[],
        )

        with file_path.open(
            "r",
            encoding="utf-8",
        ) as input_file:
            stored_document = json.load(
                input_file
            )

        self.assertEqual(
            stored_document["candidate_count"],
            1,
        )

    def test_overwrites_existing_file(self):
        candidate = self.create_candidate()

        file_path = self.repository.save(
            document_id="document-123",
            normalized_content_hash=(
                "content-hash-123"
            ),
            candidates=[candidate],
        )

        self.repository.save(
            document_id="document-123",
            normalized_content_hash=(
                "content-hash-123"
            ),
            candidates=[],
            overwrite=True,
        )

        with file_path.open(
            "r",
            encoding="utf-8",
        ) as input_file:
            stored_document = json.load(
                input_file
            )

        self.assertEqual(
            stored_document["candidate_count"],
            0,
        )

    def test_rejects_mismatched_document(self):
        candidate = self.create_candidate(
            document_id="different-document"
        )

        with self.assertRaises(ValueError):
            self.repository.save(
                document_id="document-123",
                normalized_content_hash=(
                    "content-hash-123"
                ),
                candidates=[candidate],
            )
    def test_loads_saved_candidates(self):
        candidate = self.create_candidate()

        self.repository.save(
            document_id="document-123",
            normalized_content_hash=(
                "content-hash-123"
            ),
            candidates=[candidate],
        )

        loaded_candidates = (
            self.repository.load(
                "document-123"
            )
        )

        self.assertEqual(
            len(loaded_candidates),
            1,
        )
        self.assertEqual(
            loaded_candidates[0].candidate_id,
            candidate.candidate_id,
        )
        self.assertEqual(
            loaded_candidates[0].value,
            "25.08.2026",
        )

    def test_load_returns_empty_for_missing_file(
        self,
    ):
        loaded_candidates = (
            self.repository.load(
                "missing-document"
            )
        )

        self.assertEqual(
            loaded_candidates,
            [],
        )

    def test_detects_modified_candidate_id(self):
        candidate = self.create_candidate()

        file_path = self.repository.save(
            document_id="document-123",
            normalized_content_hash=(
                "content-hash-123"
            ),
            candidates=[candidate],
        )

        with file_path.open(
            "r",
            encoding="utf-8",
        ) as input_file:
            document = json.load(input_file)

        document["candidates"][0][
            "candidate_id"
        ] = "manipulated-id"

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

        with self.assertRaises(ValueError):
            self.repository.load(
                "document-123"
            )

if __name__ == "__main__":
    unittest.main()