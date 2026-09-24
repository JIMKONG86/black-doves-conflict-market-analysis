from dataclasses import dataclass, field
from datetime import datetime


SOURCE_LAYERS = frozenset({
    "STATE_ORGAN",
    "NEWS",
    "TELEVISION",
})

CLASSIFICATION_STATUSES = frozenset({
    "UNCLASSIFIED",
    "AUTO_SUGGESTED",
    "MANUALLY_REVIEWED",
})

VERIFICATION_STATUSES = frozenset({
    "VERIFIED",
    "VERIFIED_WITH_CHANGE",
    "PARTIALLY_VERIFIED",
    "METHOD_DECISION",
    "REVIEW_REQUIRED_NOT_USED",
    "DESCRIPTIVE_ONLY",
    "TEST_BLOCKED",
})

# Who edits the outlet's content, not what it says. Kept separate from
# categories/framing_codes for the same reason source_layer is kept
# separate: conflating "who controls this broadcaster" with "what does
# this item argue" would silently launder state-directed messaging as
# ordinary independent reporting, or dismiss state media as irrelevant
# when it is often the most direct signal of how a government is
# steering domestic public opinion (its explicit analytical purpose
# here for Iran and China, where independent broadcast media barely
# exists).
BROADCASTER_CONTROL_TYPES = frozenset({
    "STATE_CONTROLLED",
    "PUBLIC_SERVICE_INDEPENDENT",
    "PRIVATE_INDEPENDENT",
    "UNKNOWN",
})


@dataclass(frozen=True)
class NarrativeDocument:
    """One comparable state, news, or television document.

    ``source_layer`` describes who communicated the item. ``categories`` and
    ``framing_codes`` describe what the item communicates. Keeping these
    dimensions separate prevents publisher type from being mistaken for
    message content.
    """

    document_id: str
    published_at: datetime
    country_code: str
    source_id: str
    publisher: str
    source_layer: str
    medium: str
    title: str
    content: str
    url: str
    categories: tuple[str, ...] = field(default_factory=tuple)
    framing_codes: tuple[str, ...] = field(default_factory=tuple)
    classification_status: str = "UNCLASSIFIED"
    verification_status: str = "PARTIALLY_VERIFIED"
    reviewer: str | None = None
    reviewed_at: datetime | None = None
    target_country_codes: tuple[str, ...] = field(default_factory=tuple)
    broadcaster_control: str = "UNKNOWN"
    company_ids: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self):
        for field_name in (
            "document_id",
            "source_id",
            "publisher",
            "medium",
            "title",
            "url",
        ):
            if not getattr(self, field_name).strip():
                raise ValueError(f"{field_name} must not be empty")

        if not isinstance(self.published_at, datetime):
            raise TypeError("published_at must be a datetime")

        country_code = self.country_code.strip().upper()
        if len(country_code) != 2 or not country_code.isalpha():
            raise ValueError("country_code must be an ISO alpha-2 code")
        object.__setattr__(self, "country_code", country_code)

        source_layer = self.source_layer.strip().upper()
        if source_layer not in SOURCE_LAYERS:
            raise ValueError(
                "source_layer must be STATE_ORGAN, NEWS, or TELEVISION"
            )
        object.__setattr__(self, "source_layer", source_layer)

        status = self.classification_status.strip().upper()
        if status not in CLASSIFICATION_STATUSES:
            raise ValueError("Unknown classification_status")
        object.__setattr__(self, "classification_status", status)

        verification = self.verification_status.strip().upper()
        if verification not in VERIFICATION_STATUSES:
            raise ValueError("Unknown verification_status")
        object.__setattr__(self, "verification_status", verification)

        object.__setattr__(
            self,
            "categories",
            tuple(dict.fromkeys(value.strip().upper() for value in self.categories)),
        )
        object.__setattr__(
            self,
            "framing_codes",
            tuple(
                dict.fromkeys(value.strip().upper() for value in self.framing_codes)
            ),
        )
        object.__setattr__(
            self,
            "target_country_codes",
            tuple(
                dict.fromkeys(
                    value.strip().upper() for value in self.target_country_codes
                )
            ),
        )

        broadcaster_control = self.broadcaster_control.strip().upper()
        if broadcaster_control not in BROADCASTER_CONTROL_TYPES:
            raise ValueError(
                "broadcaster_control must be STATE_CONTROLLED, "
                "PUBLIC_SERVICE_INDEPENDENT, PRIVATE_INDEPENDENT, or UNKNOWN"
            )
        object.__setattr__(self, "broadcaster_control", broadcaster_control)

        object.__setattr__(
            self,
            "company_ids",
            tuple(
                dict.fromkeys(
                    value.strip().upper() for value in self.company_ids if value.strip()
                )
            ),
        )
