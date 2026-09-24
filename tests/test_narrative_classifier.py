import unittest
from datetime import datetime, timezone

from src.models.narrative_document import NarrativeDocument
from src.services.narrative_classifier import NarrativeClassifier


class TestNarrativeClassifier(unittest.TestCase):
    def setUp(self):
        self.classifier = NarrativeClassifier()

    @staticmethod
    def document(text):
        return NarrativeDocument(
            document_id="doc-1",
            published_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
            country_code="US",
            source_id="SOURCE",
            publisher="Publisher",
            source_layer="STATE_ORGAN",
            medium="OFFICIAL_RELEASE",
            title="Statement",
            content=text,
            url="https://example.com/doc-1",
        )

    def test_suggests_multiple_categories_without_marking_reviewed(self):
        result = self.classifier.suggest(
            self.document(
                "A military operation was followed by peace talks and sanctions."
            )
        )

        self.assertEqual(result.classification_status, "AUTO_SUGGESTED")
        self.assertIn("MILITARY_OPERATIONS_SECURITY", result.categories)
        self.assertIn("DIPLOMACY_MEDIATION_DEESCALATION", result.categories)
        self.assertIn("SANCTIONS_ECONOMIC_MEASURES", result.categories)
        self.assertIsNone(result.reviewer)

    def test_manual_confirmation_is_a_separate_auditable_step(self):
        suggested = self.classifier.suggest(
            self.document("Self-defence strikes were completed.")
        )
        reviewed = self.classifier.confirm(
            suggested,
            categories=("MILITARY_OPERATIONS_SECURITY",),
            framing_codes=("SELF_DEFENCE_LEGITIMACY",),
            reviewer="MN",
        )

        self.assertEqual(reviewed.classification_status, "MANUALLY_REVIEWED")
        self.assertEqual(reviewed.reviewer, "MN")
        self.assertIsNotNone(reviewed.reviewed_at)


if __name__ == "__main__":
    unittest.main()
