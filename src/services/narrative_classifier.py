import re
from dataclasses import replace
from datetime import datetime, timezone

from src.models.narrative_document import NarrativeDocument


NARRATIVE_TAXONOMY = {
    "MILITARY_OPERATIONS_SECURITY": {
        "label": "Military operations & security claims",
        "patterns": (
            r"\bstrike(?:s|n)?\b",
            r"\bairstrike(?:s)?\b",
            r"\battack(?:s|ed|ing)?\b",
            r"\bmilitary operation(?:s)?\b",
            r"\bmissile(?:s)?\b",
            r"\bdrohne(?:n)?\b",
            r"\bangriff(?:e|en|s)?\b",
            r"\bmilitär(?:isch(?:e|en|er|es)?)?\b",
        ),
    },
    "DIPLOMACY_MEDIATION_DEESCALATION": {
        "label": "Diplomacy, mediation & de-escalation",
        "patterns": (
            r"\bdiplomac(?:y|tic)\b",
            r"\bmediat(?:e|ion|or)\b",
            r"\bceasefire\b",
            r"\bnegotiat(?:e|ion|ions)\b",
            r"\bpeace talks?\b",
            r"\bdiplomati(?:e|sch(?:e|en|er|es)?)\b",
            r"\bvermittlung\b",
            r"\bwaffenstillstand\b",
            r"\bverhandlung(?:en)?\b",
        ),
    },
    "PROCUREMENT_MILITARY_CAPABILITY": {
        "label": "Procurement & military capability",
        "patterns": (
            r"\bprocurement\b",
            r"\bcontract(?:s|ed)?\b",
            r"\bacquisition\b",
            r"\bweapon system(?:s)?\b",
            r"\bdefen[cs]e industr(?:y|ies)\b",
            r"\bbeschaffung(?:en)?\b",
            r"\brüstungs(?:auftrag|aufträge|industrie|güter)\b",
            r"\bwaffensystem(?:e|en)?\b",
        ),
    },
    "SANCTIONS_ECONOMIC_MEASURES": {
        "label": "Sanctions & economic measures",
        "patterns": (
            r"\bsanction(?:s|ed)?\b",
            r"\bembargo(?:es)?\b",
            r"\btariff(?:s)?\b",
            r"\basset freeze\b",
            r"\bsanktion(?:en|iert)?\b",
            r"\bembargo(?:s)?\b",
            r"\bzoll(?:e|s|politik)?\b",
        ),
    },
    "ENERGY_TRADE_DEPENDENCY": {
        "label": "Energy, trade & dependency",
        "patterns": (
            r"\bcrude oil\b",
            r"\boil price(?:s)?\b",
            r"\benergy suppl(?:y|ies)\b",
            r"\btrade route(?:s)?\b",
            r"\bstrait of hormuz\b",
            r"\bölpreis(?:e)?\b",
            r"\benergieversorgung\b",
            r"\bhandelsroute(?:n)?\b",
            r"\bstraße von hormus\b",
        ),
    },
    "HUMANITARIAN_CIVILIAN_IMPACT": {
        "label": "Humanitarian & civilian impact",
        "patterns": (
            r"\bcivilian(?:s)?\b",
            r"\bcasualt(?:y|ies)\b",
            r"\bhumanitarian\b",
            r"\bdisplaced\b",
            r"\baid delivery\b",
            r"\bzivil(?:ist(?:en|innen)?|bevölkerung)\b",
            r"\bhumanitär(?:e|en|er|es)?\b",
            r"\bvertriebene\b",
        ),
    },
    "DOMESTIC_POLITICS_LAW_BUDGET": {
        "label": "Domestic politics, law & budget",
        "patterns": (
            r"\bparliament\b",
            r"\bcongress\b",
            r"\bdefen[cs]e budget\b",
            r"\blegislation\b",
            r"\bdomestic polic(?:y|ies)\b",
            r"\bbundestag\b",
            r"\bhaushalt(?:s|spolitik)?\b",
            r"\bgesetz(?:e|gebung)?\b",
            r"\binnenpolitik\b",
        ),
    },
}

FRAMING_TAXONOMY = {
    "SELF_DEFENCE_LEGITIMACY": (
        r"\bself[- ]defen[cs]e\b",
        r"\bright to defend\b",
        r"\bselbstverteidigung\b",
    ),
    "RESPONSIBILITY_BLAME": (
        r"\bresponsible for\b",
        r"\bblame(?:s|d)?\b",
        r"\bcondemn(?:s|ed|ation)?\b",
        r"\bverantwortlich\b",
        r"\bverurteilt?\b",
    ),
    "ESCALATION": (
        r"\bescalat(?:e|es|ed|ion)\b",
        r"\bretaliat(?:e|ion|ory)\b",
        r"\beskalation\b",
        r"\bvergeltung\b",
    ),
    "DE_ESCALATION": (
        r"\bde[- ]escalat(?:e|es|ed|ion)\b",
        r"\brestraint\b",
        r"\bdeeskalation\b",
        r"\bzurückhaltung\b",
    ),
    "ECONOMIC_IMPACT": (
        r"\beconomic impact\b",
        r"\bprice(?:s)?\b",
        r"\bsupply chain(?:s)?\b",
        r"\bwirtschaftliche folgen\b",
        r"\bpreis(?:e|entwicklung)\b",
        r"\blieferkette(?:n)?\b",
    ),
    "HUMANITARIAN_CONCERN": (
        r"\bhumanitarian concern\b",
        r"\bprotect civilians\b",
        r"\bhumanitäre sorge\b",
        r"\bschutz der zivilbevölkerung\b",
    ),
}


class NarrativeClassifier:
    """Deterministic coding aid with an explicit manual-review boundary."""

    def suggest(self, document):
        self._validate_document(document)
        searchable = f"{document.title}\n{document.content}".casefold()
        categories = tuple(
            code
            for code, definition in NARRATIVE_TAXONOMY.items()
            if self._matches(searchable, definition["patterns"])
        )
        frames = tuple(
            code
            for code, patterns in FRAMING_TAXONOMY.items()
            if self._matches(searchable, patterns)
        )
        return replace(
            document,
            categories=categories,
            framing_codes=frames,
            classification_status=(
                "AUTO_SUGGESTED" if categories or frames else "UNCLASSIFIED"
            ),
            reviewer=None,
            reviewed_at=None,
        )

    def confirm(
        self,
        document,
        categories,
        framing_codes=(),
        reviewer="MANUAL_REVIEW",
        reviewed_at=None,
    ):
        self._validate_document(document)
        category_values = tuple(categories)
        frame_values = tuple(framing_codes)
        unknown_categories = set(category_values) - set(NARRATIVE_TAXONOMY)
        unknown_frames = set(frame_values) - set(FRAMING_TAXONOMY)
        if unknown_categories:
            raise ValueError(
                f"Unknown narrative categories: {sorted(unknown_categories)}"
            )
        if unknown_frames:
            raise ValueError(f"Unknown framing codes: {sorted(unknown_frames)}")
        if not reviewer.strip():
            raise ValueError("reviewer must not be empty")
        return replace(
            document,
            categories=category_values,
            framing_codes=frame_values,
            classification_status="MANUALLY_REVIEWED",
            reviewer=reviewer.strip(),
            reviewed_at=reviewed_at or datetime.now(timezone.utc),
        )

    @staticmethod
    def _matches(text, patterns):
        return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)

    @staticmethod
    def _validate_document(document):
        if not isinstance(document, NarrativeDocument):
            raise TypeError("document must be a NarrativeDocument")
