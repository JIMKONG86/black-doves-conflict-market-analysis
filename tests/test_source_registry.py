import unittest
from pathlib import Path

from src.data_access.source_registry import SourceRegistry
from src.models.source_definition import SourceDefinition


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class TestSourceDefinition(unittest.TestCase):

    def create_definition(self, source_id="DE_TEST"):
        return SourceDefinition(
            source_id=source_id,
            country_code="de",
            country_name="Germany",
            jurisdiction="Germany",
            publisher="Example ministry",
            source_name="Example releases",
            entrypoint_url="https://example.gov/releases",
            source_type="government_release",
            delivery_method="HTML",
            primary_language="de",
            publication_timezone="Europe/Berlin",
            supported_categories=("procurement",),
            source_priority=1,
            automation_tier="STRUCTURED_HTML",
            timestamp_quality="DATE_ONLY",
            archive_stability="STABLE_URL",
            verification_role="PRIMARY_OFFICIAL",
            integration_status="VALIDATED_PENDING_ADAPTER",
        )

    def test_normalizes_country_code(self):
        definition = self.create_definition()
        self.assertEqual(definition.country_code, "DE")

    def test_rejects_invalid_timezone(self):
        values = self.create_definition().__dict__ | {
            "publication_timezone": "Berlin/local"
        }
        with self.assertRaises(ValueError):
            SourceDefinition(**values)

    def test_rejects_duplicate_source_ids(self):
        definition = self.create_definition()
        with self.assertRaises(ValueError):
            SourceRegistry([definition, definition])


class TestProjectSourceRegistry(unittest.TestCase):

    def setUp(self):
        self.registry = SourceRegistry.from_json(
            PROJECT_ROOT / "config" / "country_sources.json"
        )

    def test_contains_reference_sources_for_all_project_countries(self):
        self.assertEqual(len(self.registry), 7)
        for country_code in ("DE", "IL", "CN", "IR"):
            self.assertEqual(
                len(self.registry.for_country(country_code)),
                1,
            )
        self.assertEqual(len(self.registry.for_country("US")), 3)

    def test_all_country_sources_are_marked_implemented(self):
        automated = self.registry.automated()
        self.assertEqual(
            [definition.source_id for definition in automated],
            [
                "DE_BMVG_NEWS",
                "US_DOD_CONTRACTS",
                "IL_IMOD_PRESS",
                "US_USASPENDING_CONTRACTS",
                "US_CENTCOM_PUBLIC_RELEASES",
                "CN_STATE_COUNCIL",
                "IR_MFA_STATEMENTS",
            ],
        )

    def test_us_contracts_uses_official_contract_rss(self):
        definition = self.registry.get("US_DOD_CONTRACTS")
        self.assertEqual(definition.delivery_method, "RSS_HTML")
        self.assertIn("ContentType=400", definition.feed_url)
        self.assertEqual(definition.publication_timezone, "America/New_York")

    def test_iran_mfa_uses_statements_endpoint(self):
        definition = self.registry.get("IR_MFA_STATEMENTS")
        self.assertEqual(
            definition.entrypoint_url,
            "https://en.mfa.gov.ir/portal/newsagencyshow/699",
        )

    def test_html_sources_define_official_detail_paths(self):
        expected_paths = {
            "IL_IMOD_PRESS": "/en/press-releases/press-room/",
            "CN_STATE_COUNCIL": "/news/20",
            "IR_MFA_STATEMENTS": "/portal/newsview/",
            "US_CENTCOM_PUBLIC_RELEASES": "/MEDIA/PUBLIC-RELEASES/Article/",
        }
        for source_id, path_prefix in expected_paths.items():
            definition = self.registry.get(source_id)
            self.assertEqual(definition.delivery_method, "HTML_LISTING")
            self.assertIn(path_prefix, definition.detail_url_prefixes)

    def test_china_defines_numbered_archive_pages(self):
        definition = self.registry.get("CN_STATE_COUNCIL")
        self.assertEqual(
            definition.listing_page_url_template.format(page=30),
            "https://english.www.gov.cn/news/page_30.html",
        )
        self.assertEqual(definition.request_timeout_seconds, 90)

    def test_iran_normalizes_detail_url_to_numeric_identifier(self):
        definition = self.registry.get("IR_MFA_STATEMENTS")
        self.assertEqual(
            definition.detail_url_template.format(id="794103"),
            "https://en.mfa.gov.ir/portal/newsview/794103",
        )

    def test_us_is_explicitly_limited_to_feed_discovery(self):
        definition = self.registry.get("US_DOD_CONTRACTS")

        self.assertFalse(definition.detail_retrieval_enabled)
        self.assertEqual(definition.automation_tier, "RSS_DISCOVERY_ONLY")

    def test_usaspending_is_a_separate_official_api_source(self):
        definition = self.registry.get("US_USASPENDING_CONTRACTS")

        self.assertEqual(definition.delivery_method, "USASPENDING_API")
        self.assertEqual(
            definition.awarding_agency_name,
            "Department of Defense",
        )
        self.assertEqual(definition.timestamp_quality, "DATE_ONLY")

    def test_centcom_uses_paginated_official_release_archive(self):
        definition = self.registry.get("US_CENTCOM_PUBLIC_RELEASES")

        self.assertEqual(definition.delivery_method, "HTML_LISTING")
        self.assertEqual(
            definition.listing_page_url_template.format(page=6),
            "https://www.centcom.mil/MEDIA/PUBLIC-RELEASES/?Page=6",
        )
        self.assertIn("strike_event", definition.supported_categories)


if __name__ == "__main__":
    unittest.main()
