import tempfile
import unittest

from datetime import (
    date,
    datetime,
    timedelta,
    timezone,
)
from pathlib import Path

from src.data_access.strike_observation_repository import (
    StrikeObservationRepository,
)
from src.models.claim_observation import (
    ClaimStatus,
    SourceChannel,
)
from src.models.strike_observation import (
    StrikeObservation,
    StrikeType,
)


FIXED_TIME = datetime(
    2026,
    9,
    3,
    10,
    0,
    tzinfo=timezone.utc,
)


def create_strike(
    **overrides,
):
    values = {
        "candidate_id": "a" * 64,
        "document_id": "b" * 64,
        "review_id": "c" * 64,
        "claim_id": "d" * 64,
        "event_date": date(
            2026,
            8,
            31,
        ),
        "strike_type": (
            StrikeType.DRONE_STRIKE
        ),
        "claim_status": (
            ClaimStatus.REPORTED
        ),
        "source_channel": (
            SourceChannel.NEWS_MEDIA
        ),
        "affected_country_code": "UA",
        "description": (
            "Reported drone strike "
            "affecting Ukrainian territory."
        ),
        "reviewed_by": "Markus",
        "source_url": (
            "https://example.com/"
            "reported-strike"
        ),
        "initiator_country_code": "RU",
        "location": "Kyiv",
        "weapon_system": "Drone",
        "created_at": FIXED_TIME,
    }

    values.update(
        overrides
    )

    return StrikeObservation(
        **values
    )


class TestStrikeObservation(
    unittest.TestCase
):
    def test_creates_and_normalizes_strike(
        self,
    ):
        strike = create_strike(
            affected_country_code=" ua ",
            initiator_country_code=" ru ",
            location=" Kyiv ",
            weapon_system=" Drone ",
            description=(
                " Reported drone strike "
                "affecting Ukrainian "
                "territory. "
            ),
            reviewed_by=" Markus ",
            source_url=(
                " https://example.com/"
                "reported-strike "
            ),
        )

        self.assertEqual(
            strike.affected_country_code,
            "UA",
        )
        self.assertEqual(
            strike.initiator_country_code,
            "RU",
        )
        self.assertEqual(
            strike.location,
            "Kyiv",
        )
        self.assertEqual(
            strike.weapon_system,
            "Drone",
        )
        self.assertEqual(
            strike.reviewed_by,
            "Markus",
        )
        self.assertEqual(
            len(strike.strike_id),
            64,
        )

    def test_same_strike_has_same_id(
        self,
    ):
        first = create_strike()
        second = create_strike()

        self.assertEqual(
            first.strike_id,
            second.strike_id,
        )

    def test_changed_status_changes_id(
        self,
    ):
        reported = create_strike()

        disputed = create_strike(
            claim_status=(
                ClaimStatus.DISPUTED
            )
        )

        self.assertNotEqual(
            reported.strike_id,
            disputed.strike_id,
        )

    def test_rejects_invalid_country_code(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            create_strike(
                affected_country_code="UKR"
            )

    def test_rejects_naive_created_at(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            create_strike(
                created_at=datetime(
                    2026,
                    9,
                    3,
                    10,
                    0,
                )
            )


class TestStrikeObservationRepository(
    unittest.TestCase
):
    def setUp(self):
        self.temporary_directory = (
            tempfile.TemporaryDirectory()
        )

        self.repository = (
            StrikeObservationRepository(
                Path(
                    self.temporary_directory.name
                )
            )
        )

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_saves_and_loads_strike(
        self,
    ):
        strike = create_strike()

        self.repository.save(
            strike
        )

        loaded_strikes = (
            self.repository.load_strikes(
                strike.claim_id
            )
        )

        self.assertEqual(
            len(loaded_strikes),
            1,
        )
        self.assertEqual(
            loaded_strikes[0],
            strike,
        )

    def test_appends_and_returns_latest_strike(
        self,
    ):
        first = create_strike()

        second = create_strike(
            claim_status=(
                ClaimStatus.CONFIRMED
            ),
            created_at=(
                FIXED_TIME
                + timedelta(
                    minutes=5
                )
            ),
        )

        self.repository.save(
            first
        )
        self.repository.save(
            second
        )

        loaded_strikes = (
            self.repository.load_strikes(
                first.claim_id
            )
        )

        latest = (
            self.repository
            .get_latest_strike(
                first.claim_id
            )
        )

        self.assertEqual(
            len(loaded_strikes),
            2,
        )
        self.assertIsNotNone(
            latest
        )
        self.assertEqual(
            latest.strike_id,
            second.strike_id,
        )

    def test_rejects_duplicate_strike(
        self,
    ):
        strike = create_strike()

        self.repository.save(
            strike
        )

        with self.assertRaises(
            ValueError
        ):
            self.repository.save(
                strike
            )


if __name__ == "__main__":
    unittest.main()