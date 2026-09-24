import unittest
from types import SimpleNamespace

from src.services.calculations import (
    calculate_total_reported_deaths,
    calculate_total_reported_destroyed_facilities,
)


class TestCalculations(unittest.TestCase):
    def setUp(self):
        self.observations = [
            SimpleNamespace(
                reported_civilian_deaths=10,
                reported_military_deaths=5,
                reported_civilian_facilities_destroyed=2,
                reported_military_facilities_destroyed=1,
            ),
            SimpleNamespace(
                reported_civilian_deaths=None,
                reported_military_deaths=3,
                reported_civilian_facilities_destroyed=None,
                reported_military_facilities_destroyed=4,
            ),
        ]

    def test_calculates_total_reported_deaths(self):
        result = calculate_total_reported_deaths(self.observations)

        self.assertEqual(result, 18)

    def test_calculates_total_destroyed_facilities(self):
        result = calculate_total_reported_destroyed_facilities(
            self.observations
        )

        self.assertEqual(result, 7)

    def test_empty_list_returns_zero_deaths(self):
        result = calculate_total_reported_deaths([])

        self.assertEqual(result, 0)

    def test_empty_list_returns_zero_facilities(self):
        result = calculate_total_reported_destroyed_facilities([])

        self.assertEqual(result, 0)


if __name__ == "__main__":
    unittest.main()