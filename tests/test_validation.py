import unittest

from src.services.validation import validate_reported_count


class TestValidateReportedCount(unittest.TestCase):
    def test_accepts_positive_integer(self):
        self.assertTrue(validate_reported_count(10, "deaths"))

    def test_accepts_zero(self):
        self.assertTrue(validate_reported_count(0, "deaths"))

    def test_accepts_none(self):
        self.assertTrue(validate_reported_count(None, "deaths"))

    def test_rejects_negative_integer(self):
        with self.assertRaises(ValueError):
            validate_reported_count(-1, "deaths")

    def test_rejects_string(self):
        with self.assertRaises(TypeError):
            validate_reported_count("10", "deaths")

    def test_rejects_boolean(self):
        with self.assertRaises(TypeError):
            validate_reported_count(True, "deaths")


if __name__ == "__main__":
    unittest.main()