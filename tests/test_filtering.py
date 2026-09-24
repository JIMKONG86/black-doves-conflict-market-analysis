import unittest
from types import SimpleNamespace

from src.services.filtering import generate_observations_by_status


class TestFiltering(unittest.TestCase):
    def setUp(self):
        self.verified = SimpleNamespace(
            verification_status="verified"
        )
        self.unverified = SimpleNamespace(
            verification_status="unverified"
        )

        self.observations = [
            self.verified,
            self.unverified,
        ]

    def test_returns_matching_observations(self):
        result = list(
            generate_observations_by_status(
                self.observations,
                "unverified",
            )
        )

        self.assertEqual(result, [self.unverified])

    def test_returns_empty_list_when_nothing_matches(self):
        result = list(
            generate_observations_by_status(
                self.observations,
                "rejected",
            )
        )

        self.assertEqual(result, [])

    def test_does_not_change_original_list(self):
        list(
            generate_observations_by_status(
                self.observations,
                "verified",
            )
        )

        self.assertEqual(len(self.observations), 2)


if __name__ == "__main__":
    unittest.main()