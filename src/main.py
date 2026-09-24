import logging

from src.data_access.csv_reader import (
    generate_impact_observations,
)
from src.models.company import Company
from src.models.conflict_event import ConflictEvent
from src.models.country import Country
from src.models.observations import (
    PriceObservation,
    RoleObservation,
)
from src.models.source import DataSource
from src.services.calculations import (
    calculate_total_reported_deaths,
    calculate_total_reported_destroyed_facilities,
)
from src.services.filtering import (
    generate_observations_by_status,
)


logging.basicConfig(
    filename="app.log",
    level=logging.INFO,
    format=(
        "%(asctime)s | %(levelname)s | "
        "%(name)s | %(message)s"
    ),
)

logger = logging.getLogger(__name__)


def main():
    logger.info(
        "Application started"
    )

    # Country and role observation
    china = Country(
        1,
        "China",
        "CHN",
    )

    role_source = DataSource(
        source_id=1,
        name="Example government source",
        source_type="government",
        url=(
            "https://example.com/"
            "government-source"
        ),
        publication_date="2026-02-28",
    )

    role_observation_1 = RoleObservation(
        observation_date="2026-02-28",
        role="economic partner",
        action=(
            "public expression of concern"
        ),
        target_country="Iran",
        source=role_source,
        verification_status="unverified",
    )

    china.add_role_observation(
        role_observation_1
    )

    for observation in (
        china.generate_role_history()
    ):
        print(
            china.name,
            observation.observation_date,
            observation.role,
            observation.action,
            observation.source.name,
        )

    # Company and price observation
    rheinmetall = Company(
        actor_id=2,
        name="Rheinmetall",
        ticker="RHM.DE",
        sector="defence",
        home_country="Germany",
    )

    price_source = DataSource(
        source_id=2,
        name="Example market source",
        source_type="stock exchange",
        url=(
            "https://example.com/"
            "market-source"
        ),
        publication_date="2026-02-28",
    )

    price_observation_1 = PriceObservation(
        observation_date="2026-02-28",
        closing_price=1500.00,
        currency="EUR",
        trading_volume=100000,
        source=price_source,
        verification_status="unverified",
    )

    rheinmetall.add_price_observation(
        price_observation_1
    )

    for observation in (
        rheinmetall.generate_price_history()
    ):
        print(
            rheinmetall.name,
            rheinmetall.ticker,
            rheinmetall.sector,
            rheinmetall.home_country,
            observation.observation_date,
            observation.closing_price,
            observation.currency,
            observation.trading_volume,
            observation.source.name,
        )

    # Conflict event
    event_source = DataSource(
        source_id=3,
        name="Example conflict report",
        source_type="news agency",
        url=(
            "https://example.com/"
            "conflict-report"
        ),
        publication_date="2026-02-28",
    )

    conflict_event_1 = ConflictEvent(
        event_id=1,
        observation_date="2026-02-28",
        event_type="military strike",
        initiator_country="Israel",
        target_country="Iran",
        description=(
            "Illustrative conflict event"
        ),
        source=event_source,
        verification_status="unverified",
    )

    print(
        conflict_event_1.event_id,
        conflict_event_1.observation_date,
        conflict_event_1.event_type,
        conflict_event_1.initiator_country,
        conflict_event_1.target_country,
        conflict_event_1.description,
        conflict_event_1.source.name,
        conflict_event_1.verification_status,
    )

    # Import impact observations from CSV
    imported_impacts = (
        generate_impact_observations(
            "data/impact_observations.csv"
        )
    )

    for imported_impact in imported_impacts:
        conflict_event_1.add_impact_observation(
            imported_impact
        )

    # Filter and display imported impacts
    impact_history = (
        conflict_event_1
        .generate_impact_history()
    )

    unverified_impacts = (
        generate_observations_by_status(
            impact_history,
            "unverified",
        )
    )

    for impact in unverified_impacts:
        print(
            impact.observation_date,
            impact.affected_country,
            impact.reported_civilian_deaths,
            impact.reported_military_deaths,
            (
                impact
                .reported_civilian_facilities_destroyed
            ),
            (
                impact
                .reported_military_facilities_destroyed
            ),
            impact.source.name,
            impact.verification_status,
        )

    total_reported_deaths = (
        calculate_total_reported_deaths(
            conflict_event_1
            .generate_impact_history()
        )
    )

    total_reported_destroyed_facilities = (
        calculate_total_reported_destroyed_facilities(
            conflict_event_1
            .generate_impact_history()
        )
    )

    print(
        "Total reported deaths:",
        total_reported_deaths,
    )

    print(
        "Total reported destroyed facilities:",
        total_reported_destroyed_facilities,
    )

    logger.info(
        "Application finished successfully"
    )


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logger.exception(
            "Application stopped because "
            "of an unexpected error"
        )
        raise
