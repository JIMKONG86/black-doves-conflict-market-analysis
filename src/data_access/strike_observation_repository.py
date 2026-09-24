import json
import re

from datetime import date, datetime
from pathlib import Path

from src.models.claim_observation import (
    ClaimStatus,
    SourceChannel,
)
from src.models.strike_observation import (
    StrikeObservation,
    StrikeType,
)


class StrikeObservationRepository:
    def __init__(
        self,
        directory=Path(
            "data/validated/strikes"
        ),
    ):
        self.directory = Path(
            directory
        )

    def save(
        self,
        strike,
    ):
        if not isinstance(
            strike,
            StrikeObservation,
        ):
            raise TypeError(
                "strike must be "
                "a StrikeObservation"
            )

        self.directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        file_path = self._file_path(
            strike.claim_id
        )

        if file_path.exists():
            payload = self._read_file(
                file_path
            )
        else:
            payload = {
                "claim_id": strike.claim_id,
                "strikes": [],
            }

        if (
            payload.get("claim_id")
            != strike.claim_id
        ):
            raise ValueError(
                "Stored claim_id does not "
                "match the strike"
            )

        stored_strikes = payload.get(
            "strikes"
        )

        if not isinstance(
            stored_strikes,
            list,
        ):
            raise ValueError(
                "Stored strikes must be a list"
            )

        if any(
            stored_strike.get("strike_id")
            == strike.strike_id
            for stored_strike
            in stored_strikes
        ):
            raise ValueError(
                "Strike observation "
                "already exists"
            )

        stored_strikes.append(
            self._serialize_strike(
                strike
            )
        )

        self._write_file(
            file_path=file_path,
            payload=payload,
        )

        return file_path

    def load_strikes(
        self,
        claim_id,
    ):
        normalized_claim_id = (
            self._validate_identifier(
                claim_id,
                "claim_id",
            )
        )

        file_path = self._file_path(
            normalized_claim_id
        )

        if not file_path.exists():
            return []

        payload = self._read_file(
            file_path
        )

        if (
            payload.get("claim_id")
            != normalized_claim_id
        ):
            raise ValueError(
                "Stored claim_id does not "
                "match the requested claim"
            )

        stored_strikes = payload.get(
            "strikes"
        )

        if not isinstance(
            stored_strikes,
            list,
        ):
            raise ValueError(
                "Stored strikes must be a list"
            )

        return [
            self._deserialize_strike(
                stored_strike
            )
            for stored_strike
            in stored_strikes
        ]

    def get_latest_strike(
        self,
        claim_id,
    ):
        strikes = self.load_strikes(
            claim_id
        )

        if not strikes:
            return None

        return strikes[-1]

    def contains(
        self,
        strike_id,
    ):
        normalized_strike_id = (
            self._validate_identifier(
                strike_id,
                "strike_id",
            )
        )

        if not self.directory.exists():
            return False

        for file_path in (
            self.directory.glob("*.json")
        ):
            payload = self._read_file(
                file_path
            )

            stored_strikes = payload.get(
                "strikes",
                [],
            )

            if any(
                stored_strike.get(
                    "strike_id"
                )
                == normalized_strike_id
                for stored_strike
                in stored_strikes
            ):
                return True

        return False

    def _file_path(
        self,
        claim_id,
    ):
        return self.directory / (
            f"{claim_id}.json"
        )

    @staticmethod
    def _validate_identifier(
        value,
        field_name,
    ):
        if not isinstance(value, str):
            raise TypeError(
                f"{field_name} must be a string"
            )

        normalized_value = value.strip().lower()

        if not re.fullmatch(
            r"[a-f0-9]{64}",
            normalized_value,
        ):
            raise ValueError(
                f"{field_name} must be "
                "a 64-character hexadecimal ID"
            )

        return normalized_value

    @staticmethod
    def _read_file(
        file_path,
    ):
        with file_path.open(
            "r",
            encoding="utf-8",
        ) as file:
            payload = json.load(
                file
            )

        if not isinstance(payload, dict):
            raise ValueError(
                "Stored strike data "
                "must be an object"
            )

        return payload

    @staticmethod
    def _write_file(
        file_path,
        payload,
    ):
        temporary_path = (
            file_path.with_suffix(
                ".json.tmp"
            )
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
                sort_keys=True,
            )

        temporary_path.replace(
            file_path
        )

    @staticmethod
    def _serialize_strike(
        strike,
    ):
        return {
            "strike_id": strike.strike_id,
            "candidate_id": (
                strike.candidate_id
            ),
            "document_id": (
                strike.document_id
            ),
            "review_id": strike.review_id,
            "claim_id": strike.claim_id,
            "event_date": (
                strike.event_date.isoformat()
            ),
            "strike_type": (
                strike.strike_type.value
            ),
            "claim_status": (
                strike.claim_status.value
            ),
            "source_channel": (
                strike.source_channel.value
            ),
            "affected_country_code": (
                strike.affected_country_code
            ),
            "initiator_country_code": (
                strike.initiator_country_code
            ),
            "location": strike.location,
            "weapon_system": (
                strike.weapon_system
            ),
            "description": (
                strike.description
            ),
            "reviewed_by": (
                strike.reviewed_by
            ),
            "source_url": strike.source_url,
            "created_at": (
                strike.created_at.isoformat()
            ),
        }

    @staticmethod
    def _deserialize_strike(
        stored_strike,
    ):
        if not isinstance(
            stored_strike,
            dict,
        ):
            raise ValueError(
                "Stored strike must be "
                "an object"
            )

        strike = StrikeObservation(
            candidate_id=(
                stored_strike[
                    "candidate_id"
                ]
            ),
            document_id=(
                stored_strike[
                    "document_id"
                ]
            ),
            review_id=(
                stored_strike[
                    "review_id"
                ]
            ),
            claim_id=(
                stored_strike[
                    "claim_id"
                ]
            ),
            event_date=date.fromisoformat(
                stored_strike[
                    "event_date"
                ]
            ),
            strike_type=StrikeType(
                stored_strike[
                    "strike_type"
                ]
            ),
            claim_status=ClaimStatus(
                stored_strike[
                    "claim_status"
                ]
            ),
            source_channel=SourceChannel(
                stored_strike[
                    "source_channel"
                ]
            ),
            affected_country_code=(
                stored_strike[
                    "affected_country_code"
                ]
            ),
            initiator_country_code=(
                stored_strike.get(
                    "initiator_country_code"
                )
            ),
            location=stored_strike.get(
                "location"
            ),
            weapon_system=(
                stored_strike.get(
                    "weapon_system"
                )
            ),
            description=(
                stored_strike[
                    "description"
                ]
            ),
            reviewed_by=(
                stored_strike[
                    "reviewed_by"
                ]
            ),
            source_url=(
                stored_strike[
                    "source_url"
                ]
            ),
            created_at=(
                datetime.fromisoformat(
                    stored_strike[
                        "created_at"
                    ]
                )
            ),
        )

        stored_strike_id = (
            stored_strike.get(
                "strike_id"
            )
        )

        if (
            strike.strike_id
            != stored_strike_id
        ):
            raise ValueError(
                "Stored strike_id is invalid"
            )

        return strike