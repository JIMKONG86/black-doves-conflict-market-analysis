import unittest

from src.collect_country_announcements import build_parser


class TestCollectCountryAnnouncementsParser(unittest.TestCase):

    def test_accepts_discovery_only_flag(self):
        args = build_parser().parse_args(["--discovery-only"])
        self.assertTrue(args.discovery_only)

    def test_retains_feed_only_as_compatible_alias(self):
        args = build_parser().parse_args(["--feed-only"])
        self.assertTrue(args.discovery_only)


if __name__ == "__main__":
    unittest.main()
