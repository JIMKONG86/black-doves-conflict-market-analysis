from collections.abc import Callable, Iterable
from datetime import date, datetime

from src.data_access.candidate_review_repository import (
    CandidateReviewRepository,
)
from src.data_access.claim_observation_repository import (
    ClaimObservationRepository,
)
from src.data_access.strike_observation_repository import (
    StrikeObservationRepository,
)
from src.models.candidate_observation import (
    CandidateObservation,
    CandidateType,
)
from src.models.candidate_review import (
    CandidateReview,
    ReviewDecision,
    SemanticRole,
)
from src.models.claim_observation import (
    ClaimObservation,
    ClaimStatus,
    CountryLink,
    CountryRole,
    SourceChannel,
)
from src.models.strike_observation import (
    StrikeObservation,
    StrikeType,
)


class CandidateReviewQueue:
    _DECISIONS = {
        "c": ReviewDecision.CONFIRMED,
        "r": ReviewDecision.REJECTED,
        "n": ReviewDecision.NEEDS_SOURCE,
    }

    _CLAIM_STATUSES = [
        ClaimStatus.REPORTED,
        ClaimStatus.ALLEGED,
        ClaimStatus.CONFIRMED,
        ClaimStatus.DISPUTED,
        ClaimStatus.DENIED,
        ClaimStatus.UNVERIFIED,
    ]

    _SOURCE_CHANNELS = [
        SourceChannel.PARLIAMENT,
        SourceChannel.GOVERNMENT,
        SourceChannel.NEWS_MEDIA,
        SourceChannel.NGO,
        SourceChannel.COMPANY,
        SourceChannel.SOCIAL_MEDIA,
        SourceChannel.OTHER,
    ]

    _STRIKE_TYPES = [
        StrikeType.AIRSTRIKE,
        StrikeType.MISSILE_STRIKE,
        StrikeType.DRONE_STRIKE,
        StrikeType.ARTILLERY_STRIKE,
        StrikeType.NAVAL_STRIKE,
        StrikeType.GROUND_STRIKE,
        StrikeType.OTHER,
        StrikeType.UNKNOWN,
    ]

    def __init__(
        self,
        repository: CandidateReviewRepository,
        claim_repository: ClaimObservationRepository | None = None,
        strike_repository: StrikeObservationRepository | None = None,
        input_function: Callable[[str], str] = input,
        output_function: Callable[[str], None] = print,
    ):
        if not callable(input_function):
            raise TypeError(
                "input_function must be callable"
            )

        if not callable(output_function):
            raise TypeError(
                "output_function must be callable"
            )

        self.repository = repository
        self.claim_repository = claim_repository
        self.strike_repository = strike_repository
        self.input_function = input_function
        self.output_function = output_function

    def run(
        self,
        candidates: Iterable[CandidateObservation],
        reviewed_by: str,
        review_existing: bool = False,
    ) -> list[CandidateReview]:
        reviewer = reviewed_by.strip()

        if not reviewer:
            raise ValueError(
                "reviewed_by must not be empty"
            )

        candidate_list = list(candidates)
        saved_reviews = []

        for position, candidate in enumerate(
            candidate_list,
            start=1,
        ):
            latest_review = (
                self.repository.get_latest_review(
                    candidate.candidate_id
                )
            )

            if (
                latest_review is not None
                and not review_existing
            ):
                self._write(
                    "\nSkipping already reviewed candidate: "
                    f"{candidate.candidate_id}"
                )

                if isinstance(
                    latest_review,
                    dict,
                ):
                    latest_decision = (
                        latest_review.get(
                            "decision",
                            "unknown",
                        )
                    )
                else:
                    latest_decision = (
                        latest_review.decision.value
                    )

                self._write(
                    f"Latest decision: {latest_decision}"
                )
                continue

            self._show_candidate(
                candidate=candidate,
                position=position,
                total=len(candidate_list),
            )

            action = self._read_action()

            if action == "q":
                self._write(
                    "\nReview queue stopped."
                )
                break

            if action == "s":
                self._write(
                    "Candidate skipped."
                )
                continue

            decision = self._DECISIONS[action]

            if (
                decision
                == ReviewDecision.REJECTED
            ):
                semantic_role = (
                    SemanticRole.UNKNOWN
                )
                normalized_value = None
            else:
                semantic_role = (
                    self._read_semantic_role(
                        candidate.candidate_type
                    )
                )

                normalized_value = (
                    self._read_optional(
                        "Normalized value "
                        "(optional): "
                    )
                )

            reviewer_note = self._read_optional(
                "Reviewer note (optional): "
            )

            review = CandidateReview(
                candidate_id=(
                    candidate.candidate_id
                ),
                document_id=(
                    candidate.document_id
                ),
                candidate_type=(
                    candidate.candidate_type
                ),
                decision=decision,
                semantic_role=semantic_role,
                reviewed_by=reviewer,
                normalized_value=(
                    normalized_value
                ),
                reviewer_note=reviewer_note,
            )

            claim = self._collect_claim(
                candidate=candidate,
                review=review,
                reviewer=reviewer,
            )

            strike = self._collect_strike(
                candidate=candidate,
                review=review,
                claim=claim,
                reviewer=reviewer,
            )

            self.repository.save(
                review
            )

            saved_reviews.append(
                review
            )

            self._write(
                "Saved review: "
                f"{review.review_id}"
            )

            if (
                claim is not None
                and self.claim_repository
                is not None
            ):
                self.claim_repository.save(
                    claim
                )

                self._write(
                    "Saved claim observation: "
                    f"{claim.claim_id}"
                )

            if (
                strike is not None
                and self.strike_repository
                is not None
            ):
                self.strike_repository.save(
                    strike
                )

                self._write(
                    "Saved strike observation: "
                    f"{strike.strike_id}"
                )

        self._write(
            "\nSaved reviews in this session: "
            f"{len(saved_reviews)}"
        )

        return saved_reviews

    def _collect_claim(
        self,
        candidate: CandidateObservation,
        review: CandidateReview,
        reviewer: str,
    ) -> ClaimObservation | None:
        if self.claim_repository is None:
            return None

        if (
            review.decision
            == ReviewDecision.REJECTED
        ):
            return None

        if (
            review.semantic_role
            != SemanticRole.EVENT_DATE
        ):
            return None

        should_assess = self._read_yes_no(
            "Assess the underlying claim? "
            "[y/N]: "
        )

        if not should_assess:
            return None

        claim_type = self._read_required(
            "Claim type "
            "(e.g. airspace_violation): "
        )

        claim_type = (
            claim_type
            .casefold()
            .replace(
                " ",
                "_",
            )
        )

        claim_status = (
            self._read_claim_status()
        )

        source_channel = (
            self._read_source_channel()
        )

        publisher_name = self._read_optional(
            "Publishing platform "
            "(optional): "
        )

        statement_author = self._read_optional(
            "Statement author "
            "(optional): "
        )

        original_source_name = (
            self._read_optional(
                "Original reporting source "
                "(optional): "
            )
        )

        country_links = (
            self._read_country_links()
        )

        source_url = getattr(
            candidate,
            "source_url",
            None,
        )

        return ClaimObservation(
            candidate_id=(
                candidate.candidate_id
            ),
            document_id=(
                candidate.document_id
            ),
            review_id=review.review_id,
            claim_type=claim_type,
            claim_status=claim_status,
            source_channel=source_channel,
            claim_text=candidate.context,
            reviewed_by=reviewer,
            country_links=country_links,
            publisher_name=publisher_name,
            statement_author=statement_author,
            original_source_name=(
                original_source_name
            ),
            source_url=source_url,
        )

    def _collect_strike(
        self,
        candidate: CandidateObservation,
        review: CandidateReview,
        claim: ClaimObservation | None,
        reviewer: str,
    ) -> StrikeObservation | None:
        if (
            self.strike_repository is None
            or claim is None
        ):
            return None

        should_record = self._read_yes_no(
            "Record a strike observation? "
            "[y/N]: "
        )

        if not should_record:
            return None

        event_date = self._resolve_event_date(
            candidate=candidate,
            review=review,
        )

        strike_type = (
            self._read_strike_type()
        )

        affected_default = (
            self._country_code_for_role(
                claim=claim,
                role=CountryRole.AFFECTED,
            )
        )

        affected_country_code = (
            self._read_country_code(
                label="Affected country code",
                default=affected_default,
                required=True,
            )
        )

        initiator_default = (
            self._country_code_for_role(
                claim=claim,
                role=(
                    CountryRole.ALLEGED_ACTOR
                ),
            )
        )

        initiator_country_code = (
            self._read_country_code(
                label="Initiator country code",
                default=initiator_default,
                required=False,
            )
        )

        location = self._read_optional(
            "Location (optional): "
        )

        weapon_system = (
            self._read_optional(
                "Weapon system (optional): "
            )
        )

        description = self.input_function(
            "Strike description "
            "[Enter = candidate context]: "
        ).strip()

        if not description:
            description = candidate.context

        source_url = (
            claim.source_url
            or getattr(
                candidate,
                "source_url",
                None,
            )
        )

        if not source_url:
            source_url = self._read_required(
                "Source URL: "
            )

        return StrikeObservation(
            candidate_id=(
                candidate.candidate_id
            ),
            document_id=(
                candidate.document_id
            ),
            review_id=review.review_id,
            claim_id=claim.claim_id,
            event_date=event_date,
            strike_type=strike_type,
            claim_status=claim.claim_status,
            source_channel=(
                claim.source_channel
            ),
            affected_country_code=(
                affected_country_code
            ),
            initiator_country_code=(
                initiator_country_code
            ),
            location=location,
            weapon_system=weapon_system,
            description=description,
            reviewed_by=reviewer,
            source_url=source_url,
        )

    def _resolve_event_date(
        self,
        candidate: CandidateObservation,
        review: CandidateReview,
    ) -> date:
        possible_values = (
            review.normalized_value,
            candidate.value,
        )

        for possible_value in possible_values:
            parsed_date = self._parse_date(
                possible_value
            )

            if parsed_date is not None:
                return parsed_date

        while True:
            raw_value = self.input_function(
                "Event date (YYYY-MM-DD): "
            ).strip()

            parsed_date = self._parse_date(
                raw_value
            )

            if parsed_date is not None:
                return parsed_date

            self._write(
                "Invalid event date. "
                "Use YYYY-MM-DD or DD.MM.YYYY."
            )

    @staticmethod
    def _parse_date(
        value: str | None,
    ) -> date | None:
        if not isinstance(
            value,
            str,
        ):
            return None

        normalized_value = value.strip()

        if not normalized_value:
            return None

        for date_format in (
            "%Y-%m-%d",
            "%d.%m.%Y",
            "%d.%m.%y",
        ):
            try:
                return datetime.strptime(
                    normalized_value,
                    date_format,
                ).date()
            except ValueError:
                continue

        return None

    def _read_strike_type(
        self,
    ) -> StrikeType:
        self._write(
            "\nAvailable strike types:"
        )

        for number, strike_type in enumerate(
            self._STRIKE_TYPES,
            start=1,
        ):
            self._write(
                f"{number}: "
                f"{strike_type.value}"
            )

        while True:
            selection = self.input_function(
                "Select strike type: "
            ).strip()

            try:
                selected_index = (
                    int(selection) - 1
                )

                if selected_index < 0:
                    raise IndexError

                return self._STRIKE_TYPES[
                    selected_index
                ]
            except (
                ValueError,
                IndexError,
            ):
                self._write(
                    "Invalid strike type. "
                    "Please try again."
                )

    def _read_country_code(
        self,
        label: str,
        default: str | None,
        required: bool,
    ) -> str | None:
        if default:
            prompt = (
                f"{label} "
                f"[Enter = {default}]: "
            )
        elif required:
            prompt = f"{label}: "
        else:
            prompt = (
                f"{label} (optional): "
            )

        while True:
            value = self.input_function(
                prompt
            ).strip()

            if not value:
                value = default

            if (
                not value
                and not required
            ):
                return None

            if (
                isinstance(
                    value,
                    str,
                )
                and len(value) == 2
                and value.isalpha()
            ):
                return value.upper()

            self._write(
                "Invalid country code. "
                "Use a two-letter "
                "ISO alpha-2 code."
            )

    @staticmethod
    def _country_code_for_role(
        claim: ClaimObservation,
        role: CountryRole,
    ) -> str | None:
        for link in claim.country_links:
            if link.role == role:
                return link.country_code

        return None

    def _show_candidate(
        self,
        candidate: CandidateObservation,
        position: int,
        total: int,
    ):
        source_url = getattr(
            candidate,
            "source_url",
            None,
        )

        extraction_method = getattr(
            candidate,
            "extraction_method",
            None,
        )

        self._write(
            "\n"
            + "=" * 70
        )

        self._write(
            f"Candidate {position} of {total}"
        )

        self._write(
            "Type: "
            f"{candidate.candidate_type.value}"
        )

        self._write(
            f"Value: {candidate.value}"
        )

        self._write(
            f"Context: {candidate.context}"
        )

        self._write(
            "Source: "
            f"{source_url or 'unknown'}"
        )

        self._write(
            "Extraction method: "
            f"{extraction_method or 'unknown'}"
        )

        self._write(
            "Candidate ID: "
            f"{candidate.candidate_id}"
        )

    def _read_action(
        self,
    ) -> str:
        valid_actions = {
            "c",
            "r",
            "n",
            "s",
            "q",
        }

        while True:
            action = self.input_function(
                "\n[c]onfirm, "
                "[r]eject, "
                "[n]eeds source, "
                "[s]kip, "
                "[q]uit: "
            ).strip().casefold()

            if action in valid_actions:
                return action

            self._write(
                "Invalid selection. "
                "Please try again."
            )

    def _read_semantic_role(
        self,
        candidate_type: CandidateType,
    ) -> SemanticRole:
        roles = self._allowed_roles(
            candidate_type
        )

        if len(roles) == 1:
            self._write(
                "Semantic role: "
                f"{roles[0].value}"
            )

            return roles[0]

        self._write(
            "\nAvailable semantic roles:"
        )

        for number, role in enumerate(
            roles,
            start=1,
        ):
            self._write(
                f"{number}: {role.value}"
            )

        while True:
            selection = self.input_function(
                "Select semantic role: "
            ).strip()

            try:
                selected_index = (
                    int(selection) - 1
                )

                if selected_index < 0:
                    raise IndexError

                return roles[
                    selected_index
                ]
            except (
                ValueError,
                IndexError,
            ):
                self._write(
                    "Invalid semantic role. "
                    "Please try again."
                )

    def _read_claim_status(
        self,
    ) -> ClaimStatus:
        self._write(
            "\nAvailable claim statuses:"
        )

        for number, status in enumerate(
            self._CLAIM_STATUSES,
            start=1,
        ):
            self._write(
                f"{number}: {status.value}"
            )

        while True:
            selection = self.input_function(
                "Select claim status: "
            ).strip()

            try:
                selected_index = (
                    int(selection) - 1
                )

                if selected_index < 0:
                    raise IndexError

                return self._CLAIM_STATUSES[
                    selected_index
                ]
            except (
                ValueError,
                IndexError,
            ):
                self._write(
                    "Invalid claim status. "
                    "Please try again."
                )

    def _read_source_channel(
        self,
    ) -> SourceChannel:
        self._write(
            "\nAvailable source channels:"
        )

        for number, channel in enumerate(
            self._SOURCE_CHANNELS,
            start=1,
        ):
            self._write(
                f"{number}: {channel.value}"
            )

        while True:
            selection = self.input_function(
                "Select source channel: "
            ).strip()

            try:
                selected_index = (
                    int(selection) - 1
                )

                if selected_index < 0:
                    raise IndexError

                return self._SOURCE_CHANNELS[
                    selected_index
                ]
            except (
                ValueError,
                IndexError,
            ):
                self._write(
                    "Invalid source channel. "
                    "Please try again."
                )

    def _read_country_links(
        self,
    ) -> tuple[CountryLink, ...]:
        self._write(
            "\nCountry-link roles:"
        )

        for role in CountryRole:
            self._write(
                f"- {role.value}"
            )

        self._write(
            "Format example:"
        )

        self._write(
            "publisher=DE, "
            "original_source=FI, "
            "affected=FI, "
            "alleged_actor=UA"
        )

        while True:
            raw_value = self.input_function(
                "Country links "
                "(optional): "
            ).strip()

            if not raw_value:
                return ()

            try:
                links = []

                for entry in raw_value.split(
                    ","
                ):
                    role_value, country_code = (
                        entry.split(
                            "=",
                            maxsplit=1,
                        )
                    )

                    links.append(
                        CountryLink(
                            country_code=(
                                country_code.strip()
                            ),
                            role=CountryRole(
                                role_value
                                .strip()
                                .casefold()
                            ),
                        )
                    )

                return tuple(
                    links
                )
            except (
                TypeError,
                ValueError,
            ):
                self._write(
                    "Invalid country links. "
                    "Use role=ISO_CODE."
                )

    def _read_yes_no(
        self,
        prompt: str,
    ) -> bool:
        while True:
            value = self.input_function(
                prompt
            ).strip().casefold()

            if value in {
                "",
                "n",
                "no",
            }:
                return False

            if value in {
                "y",
                "yes",
            }:
                return True

            self._write(
                "Please enter y or n."
            )

    def _read_required(
        self,
        prompt: str,
    ) -> str:
        while True:
            value = self.input_function(
                prompt
            ).strip()

            if value:
                return value

            self._write(
                "Value must not be empty."
            )

    @staticmethod
    def _allowed_roles(
        candidate_type: CandidateType,
    ) -> list[SemanticRole]:
        if (
            candidate_type
            == CandidateType.DATE
        ):
            return [
                SemanticRole.DOCUMENT_DATE,
                SemanticRole.EVENT_DATE,
                SemanticRole.CITED_SOURCE_DATE,
                SemanticRole.LEGAL_REFERENCE_DATE,
                SemanticRole.UNKNOWN,
            ]

        if (
            candidate_type
            == CandidateType.AMOUNT
        ):
            return [
                SemanticRole.CONTRACT_AMOUNT,
                SemanticRole.BUDGET_AMOUNT,
                SemanticRole.EXPENDITURE_AMOUNT,
                SemanticRole.UNKNOWN,
            ]

        return [
            SemanticRole.UNKNOWN,
        ]

    def _read_optional(
        self,
        prompt: str,
    ) -> str | None:
        value = self.input_function(
            prompt
        ).strip()

        return value or None

    def _write(
        self,
        message: str,
    ):
        self.output_function(
            message
        )