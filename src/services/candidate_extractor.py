import re
from datetime import datetime

from src.models.candidate_observation import (
    CandidateObservation,
    CandidateType,
)
from src.models.normalized_document import (
    NormalizedDocument,
)

GERMAN_MONTH_PATTERN = (
    r"(?:"
    r"Januar"
    r"|Februar"
    r"|März"
    r"|Maerz"
    r"|April"
    r"|Mai"
    r"|Juni"
    r"|Juli"
    r"|August"
    r"|September"
    r"|Oktober"
    r"|November"
    r"|Dezember"
    r")"
)
DATE_PATTERNS = (
    (
        "date_dmy",
        re.compile(
            r"(?<!\d)"
            r"(?:0?[1-9]|[12]\d|3[01])"
            r"[./-]"
            r"(?:0?[1-9]|1[0-2])"
            r"[./-]"
            r"(?:19|20)\d{2}"
            r"(?!\d)"
        ),
    ),
    (
        "date_iso",
        re.compile(
            r"(?<!\d)"
            r"(?:19|20)\d{2}"
            r"-"
            r"(?:0[1-9]|1[0-2])"
            r"-"
            r"(?:0[1-9]|[12]\d|3[01])"
            r"(?!\d)"
        ),
    ),
    (
        "date_german_text",
        re.compile(
            r"(?<!\w)"
            r"(?:0?[1-9]|[12]\d|3[01])"
            r"\.\s+"
            rf"{GERMAN_MONTH_PATTERN}"
            r"\s+"
            r"(?:19|20)\d{2}"
            r"(?!\d)",
            re.IGNORECASE,
        ),
    ),
)


NUMBER_PATTERN = (
    r"(?:"
    r"\d{1,3}(?:[.\s]\d{3})*(?:,\d+)?"
    r"|"
    r"\d+(?:[.,]\d+)?"
    r")"
)

SCALE_PATTERN = (
    r"(?:"
    r"Tausend"
    r"|Million(?:en)?"
    r"|Milliard(?:e|en)?"
    r"|Billion(?:en)?"
    r"|Mio\.?"
    r"|Mrd\.?"
    r"|thousand"
    r"|million"
    r"|billion"
    r"|trillion"
    r"|bn"
    r")"
)

CURRENCY_PATTERN = (
    r"(?:"
    r"Euro"
    r"|EUR"
    r"|US[- ]?Dollar"
    r"|Dollar"
    r"|USD"
    r"|€"
    r"|\$"
    r"|£"
    r")"
)


AMOUNT_PATTERNS = (
    (
        "amount_suffix",
        re.compile(
            rf"(?<!\w)"
            rf"{NUMBER_PATTERN}"
            rf"\s*"
            rf"(?:{SCALE_PATTERN}\s*)?"
            rf"{CURRENCY_PATTERN}"
            rf"(?!\w)",
            re.IGNORECASE,
        ),
    ),
    (
        "amount_prefix",
        re.compile(
            rf"(?<!\w)"
            rf"{CURRENCY_PATTERN}"
            rf"\s*"
            rf"{NUMBER_PATTERN}"
            rf"(?:\s*{SCALE_PATTERN})?"
            rf"(?!\w)",
            re.IGNORECASE,
        ),
    ),
)


class CandidateExtractor:

    def __init__(self, context_window=120):
        if (
            not isinstance(context_window, int)
            or isinstance(context_window, bool)
        ):
            raise TypeError(
                "context_window must be an integer"
            )

        if context_window < 0:
            raise ValueError(
                "context_window must not be negative"
            )

        self.context_window = context_window

    def extract(self, normalized_document):
        self._validate_document(
            normalized_document
        )

        candidates = []

        candidates.extend(
            self._extract_dates(
                normalized_document
            )
        )

        candidates.extend(
            self._extract_amounts(
                normalized_document
            )
        )

        unique_candidates = {
            candidate.candidate_id: candidate
            for candidate in candidates
        }

        return sorted(
            unique_candidates.values(),
            key=lambda candidate: (
                candidate.start_index,
                candidate.end_index,
                candidate.candidate_type.value,
            ),
        )

    def _extract_dates(
        self,
        normalized_document,
    ):
        candidates = []

        for pattern_name, pattern in DATE_PATTERNS:
            for match in pattern.finditer(
                normalized_document.content
            ):
                if not self._is_valid_date(
                    match.group()
                ):
                    continue

                candidate = self._create_candidate(
                    normalized_document=(
                        normalized_document
                    ),
                    candidate_type=(
                        CandidateType.DATE
                    ),
                    match=match,
                    extraction_method=(
                        f"regex:{pattern_name}"
                    ),
                )

                candidates.append(candidate)

        return candidates

    def _extract_amounts(
        self,
        normalized_document,
    ):
        candidates = []

        for pattern_name, pattern in (
            AMOUNT_PATTERNS
        ):
            for match in pattern.finditer(
                normalized_document.content
            ):
                candidate = self._create_candidate(
                    normalized_document=(
                        normalized_document
                    ),
                    candidate_type=(
                        CandidateType.AMOUNT
                    ),
                    match=match,
                    extraction_method=(
                        f"regex:{pattern_name}"
                    ),
                )

                candidates.append(candidate)

        return candidates

    def _create_candidate(
        self,
        normalized_document,
        candidate_type,
        match,
        extraction_method,
    ):
        context_start = max(
            0,
            match.start() - self.context_window,
        )

        context_end = min(
            len(normalized_document.content),
            match.end() + self.context_window,
        )

        context = normalized_document.content[
            context_start:context_end
        ]

        context = " ".join(context.split())

        return CandidateObservation(
            document_id=(
                normalized_document.document_id
            ),
            candidate_type=candidate_type,
            value=match.group(),
            context=context,
            start_index=match.start(),
            end_index=match.end(),
            source_url=normalized_document.url,
            normalized_content_hash=(
                normalized_document
                .normalized_content_hash
            ),
            extraction_method=(
                extraction_method
            ),
        )


    @staticmethod
    def _is_valid_date(value):
        normalized_value = " ".join(
            value.split()
        )

        numeric_date_formats = (
            "%d.%m.%Y",
            "%d/%m/%Y",
            "%d-%m-%Y",
            "%Y-%m-%d",
        )

        for date_format in numeric_date_formats:
            try:
                datetime.strptime(
                    normalized_value,
                    date_format,
                )
                return True
            except ValueError:
                continue

        month_numbers = {
            "januar": 1,
            "februar": 2,
            "märz": 3,
            "maerz": 3,
            "april": 4,
            "mai": 5,
            "juni": 6,
            "juli": 7,
            "august": 8,
            "september": 9,
            "oktober": 10,
            "november": 11,
            "dezember": 12,
        }

        text_date_match = re.fullmatch(
            r"(?P<day>\d{1,2})"
            r"\.\s+"
            rf"(?P<month>{GERMAN_MONTH_PATTERN})"
            r"\s+"
            r"(?P<year>\d{4})",
            normalized_value,
            re.IGNORECASE,
        )

        if text_date_match is None:
            return False

        day = int(
            text_date_match.group("day")
        )
        year = int(
            text_date_match.group("year")
        )

        month_name = (
            text_date_match
            .group("month")
            .casefold()
        )

        month = month_numbers[month_name]

        try:
            datetime(
                year=year,
                month=month,
                day=day,
            )
            return True
        except ValueError:
            return False

    @staticmethod
    def _validate_document(
        normalized_document,
    ):
        if not isinstance(
            normalized_document,
            NormalizedDocument,
        ):
            raise TypeError(
                "normalized_document must be "
                "a NormalizedDocument"
            )