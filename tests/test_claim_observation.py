import tempfile
import unittest
from pathlib import Path

from src.data_access.claim_observation_repository import (
    ClaimObservationRepository,
)
from src.models.claim_observation import (
    ClaimObservation,
    ClaimStatus,
    CountryLink,
    CountryRole,
    SourceChannel,
)


class TestClaimObservation(unittest.TestCase):
    def create_claim(self):
        return ClaimObservation(
            candidate_id="a" * 64,
            document_id="b" * 64,
            review_id="c" * 64,
            claim_type="airspace_violation",
            claim_status=ClaimStatus.ALLEGED,
            source_channel=(
                SourceChannel.PARLIAMENT
            ),
            claim_text=(
                "There is a suspicion that "
                "two drones violated Finnish "
                "airspace."
            ),
            reviewed_by="Markus",
            publisher_name=(
                "Deutscher Bundestag"
            ),
            statement_author=(
                "Bundesregierung"
            ),
            original_source_name=(
                "Finnish Border Guard"
            ),
            source_url=(
                "https://example.com/document"
            ),
            country_links=(
                CountryLink(
                    country_code="de",
                    role=CountryRole.PUBLISHER,
                ),
                CountryLink(
                    country_code="fi",
                    role=(
                        CountryRole
                        .ORIGINAL_SOURCE
                    ),
                ),
                CountryLink(
                    country_code="fi",
                    role=CountryRole.AFFECTED,
                ),
                CountryLink(
                    country_code="ua",
                    role=(
                        CountryRole
                        .ALLEGED_ACTOR
                    ),
                ),
            ),
        )

    def test_normalizes_country_codes(self):
        claim = self.create_claim()

        self.assertEqual(
            claim.country_links[0].country_code,
            "DE",
        )

    def test_rejects_invalid_country_code(self):
        with self.assertRaises(ValueError):
            CountryLink(
                country_code="Germany",
                role=CountryRole.PUBLISHER,
            )

    def test_rejects_duplicate_links(self):
        duplicate_link = CountryLink(
            country_code="DE",
            role=CountryRole.PUBLISHER,
        )

        with self.assertRaises(ValueError):
            ClaimObservation(
                candidate_id="a" * 64,
                document_id="b" * 64,
                review_id="c" * 64,
                claim_type="test_claim",
                claim_status=(
                    ClaimStatus.UNVERIFIED
                ),
                source_channel=(
                    SourceChannel.OTHER
                ),
                claim_text="Test claim",
                reviewed_by="Markus",
                country_links=(
                    duplicate_link,
                    duplicate_link,
                ),
            )

    def test_repository_saves_claim(self):
        with tempfile.TemporaryDirectory() as directory:
            repository = (
                ClaimObservationRepository(
                    storage_directory=directory
                )
            )

            claim = self.create_claim()
            file_path = repository.save(claim)

            self.assertTrue(
                Path(file_path).exists()
            )

            stored_claims = (
                repository.load_claims(
                    claim.candidate_id
                )
            )

            self.assertEqual(
                len(stored_claims),
                1,
            )
            self.assertEqual(
                stored_claims[0][
                    "claim_status"
                ],
                "alleged",
            )
            self.assertEqual(
                stored_claims[0][
                    "country_links"
                ][3]["country_code"],
                "UA",
            )

    def test_repository_rejects_duplicate(
        self,
    ):
        with tempfile.TemporaryDirectory() as directory:
            repository = (
                ClaimObservationRepository(
                    storage_directory=directory
                )
            )

            claim = self.create_claim()
            repository.save(claim)

            with self.assertRaises(ValueError):
                repository.save(claim)


if __name__ == "__main__":
    unittest.main()