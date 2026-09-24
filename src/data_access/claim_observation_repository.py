import json
import re

from pathlib import Path

from src.models.claim_observation import (
    ClaimObservation,
)


class ClaimObservationRepository:
    def __init__(
        self,
        storage_directory=(
            "data/validated/claims"
        ),
    ):
        self.storage_directory = Path(
            storage_directory
        )

        self.storage_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    def save(
        self,
        claim: ClaimObservation,
    ) -> Path:
        if not isinstance(
            claim,
            ClaimObservation,
        ):
            raise TypeError(
                "claim must be a "
                "ClaimObservation"
            )

        file_path = self._create_file_path(
            claim.candidate_id
        )

        if file_path.exists():
            payload = self._load_payload(
                file_path
            )
        else:
            payload = {
                "candidate_id": (
                    claim.candidate_id
                ),
                "document_id": (
                    claim.document_id
                ),
                "claims": [],
            }

        if (
            payload.get("candidate_id")
            != claim.candidate_id
        ):
            raise ValueError(
                "Stored candidate_id does "
                "not match claim"
            )

        if (
            payload.get("document_id")
            != claim.document_id
        ):
            raise ValueError(
                "Stored document_id does "
                "not match claim"
            )

        stored_claims = payload.get(
            "claims"
        )

        if not isinstance(
            stored_claims,
            list,
        ):
            raise ValueError(
                "Stored claims must be a list"
            )

        if any(
            stored_claim.get("claim_id")
            == claim.claim_id
            for stored_claim in stored_claims
        ):
            raise ValueError(
                "Claim has already been stored"
            )

        stored_claims.append(
            self._serialize_claim(claim)
        )

        temporary_path = (
            file_path.with_suffix(".tmp")
        )

        with temporary_path.open(
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                payload,
                file,
                ensure_ascii=False,
                indent=2,
            )

        temporary_path.replace(
            file_path
        )

        return file_path

    def load_claims(
        self,
        candidate_id: str,
    ) -> list[dict]:
        file_path = self._create_file_path(
            candidate_id
        )

        if not file_path.exists():
            return []

        payload = self._load_payload(
            file_path
        )

        if (
            payload.get("candidate_id")
            != candidate_id
        ):
            raise ValueError(
                "Stored candidate_id mismatch"
            )

        claims = payload.get(
            "claims"
        )

        if not isinstance(
            claims,
            list,
        ):
            raise ValueError(
                "Stored claims must be a list"
            )

        return claims

    def get_latest_claim(
        self,
        candidate_id: str,
    ) -> dict | None:
        claims = self.load_claims(
            candidate_id
        )

        if not claims:
            return None

        return claims[-1]

    def contains(
        self,
        candidate_id: str,
    ) -> bool:
        return self._create_file_path(
            candidate_id
        ).exists()

    def _create_file_path(
        self,
        candidate_id: str,
    ) -> Path:
        self._validate_candidate_id(
            candidate_id
        )

        return (
            self.storage_directory
            / f"{candidate_id}.json"
        )

    @staticmethod
    def _validate_candidate_id(
        candidate_id,
    ):
        if not isinstance(
            candidate_id,
            str,
        ):
            raise TypeError(
                "candidate_id must be a string"
            )

        if not re.fullmatch(
            r"[a-fA-F0-9]{64}",
            candidate_id,
        ):
            raise ValueError(
                "candidate_id must be a "
                "64-character hexadecimal hash"
            )

    @staticmethod
    def _load_payload(
        file_path: Path,
    ) -> dict:
        try:
            with file_path.open(
                "r",
                encoding="utf-8",
            ) as file:
                payload = json.load(file)
        except json.JSONDecodeError as exception:
            raise ValueError(
                "Stored claim data is not "
                "valid JSON"
            ) from exception

        if not isinstance(
            payload,
            dict,
        ):
            raise ValueError(
                "Stored claim data must be "
                "a JSON object"
            )

        return payload

    @staticmethod
    def _serialize_claim(
        claim: ClaimObservation,
    ) -> dict:
        return {
            "claim_id": claim.claim_id,
            "candidate_id": (
                claim.candidate_id
            ),
            "document_id": (
                claim.document_id
            ),
            "review_id": claim.review_id,
            "claim_type": claim.claim_type,
            "claim_status": (
                claim.claim_status.value
            ),
            "source_channel": (
                claim.source_channel.value
            ),
            "claim_text": claim.claim_text,
            "reviewed_by": (
                claim.reviewed_by
            ),
            "publisher_name": (
                claim.publisher_name
            ),
            "statement_author": (
                claim.statement_author
            ),
            "original_source_name": (
                claim.original_source_name
            ),
            "source_url": claim.source_url,
            "country_links": [
                {
                    "country_code": (
                        link.country_code
                    ),
                    "role": link.role.value,
                }
                for link in claim.country_links
            ],
            "created_at": (
                claim.created_at.isoformat()
            ),
        }