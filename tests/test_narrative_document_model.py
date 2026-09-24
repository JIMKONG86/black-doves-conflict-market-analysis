import unittest

from datetime import datetime, timezone

from src.models.narrative_document import NarrativeDocument


class TestNarrativeDocumentBroadcasterControl(unittest.TestCase):
    @staticmethod
    def _base_kwargs(**overrides):
        values = {
            "document_id": "doc-1",
            "published_at": datetime(2026, 3, 1, tzinfo=timezone.utc),
            "country_code": "cn",
            "source_id": "CN_CGTN_TRANSCRIPTS",
            "publisher": "CGTN",
            "source_layer": "TELEVISION",
            "medium": "TV_TRANSCRIPT",
            "title": "Example segment",
            "content": "Example paraphrased summary.",
            "url": "https://example.com/segment",
        }
        values.update(overrides)
        return values

    def test_defaults_to_unknown_broadcaster_control_and_no_companies(self):
        document = NarrativeDocument(**self._base_kwargs())

        self.assertEqual(document.broadcaster_control, "UNKNOWN")
        self.assertEqual(document.company_ids, ())

    def test_normalizes_broadcaster_control_case(self):
        document = NarrativeDocument(
            **self._base_kwargs(broadcaster_control="state_controlled")
        )

        self.assertEqual(document.broadcaster_control, "STATE_CONTROLLED")

    def test_rejects_unknown_broadcaster_control(self):
        with self.assertRaisesRegex(ValueError, "broadcaster_control"):
            NarrativeDocument(
                **self._base_kwargs(broadcaster_control="PROPAGANDA_LEVEL_5")
            )

    def test_deduplicates_and_upper_cases_company_ids(self):
        document = NarrativeDocument(
            **self._base_kwargs(company_ids=("cmp032", "CMP032", "cmp044"))
        )

        self.assertEqual(document.company_ids, ("CMP032", "CMP044"))

    def test_ignores_blank_company_ids(self):
        document = NarrativeDocument(
            **self._base_kwargs(company_ids=("cmp032", "  ", ""))
        )

        self.assertEqual(document.company_ids, ("CMP032",))


if __name__ == "__main__":
    unittest.main()
