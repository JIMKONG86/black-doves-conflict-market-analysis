from collections import defaultdict
from datetime import date, datetime

from src.models.weekly_conflict_aggregate import (
    AggregateEventType,
    WeeklyConflictAggregate,
)
from src.models.weekly_conflict_feature import (
    WeeklyConflictFeature,
)


_AIR_DRONE_STRIKE = "Air/drone strike"
_SHELLING_ARTILLERY_MISSILE = (
    "Shelling/artillery/missile attack"
)


class WeeklyConflictFeatureBuilder:
    def __init__(self, aggregate_repository):
        load_all = getattr(
            aggregate_repository,
            "load_all",
            None,
        )

        if not callable(load_all):
            raise TypeError(
                "aggregate_repository must provide "
                "a callable load_all method"
            )

        self.aggregate_repository = (
            aggregate_repository
        )

    def build(
        self,
        source_snapshot_date=None,
        countries=None,
    ):
        snapshot_filter = self._snapshot_date(
            source_snapshot_date
        )
        country_filter = self._countries(countries)
        aggregates = self.aggregate_repository.load_all()

        try:
            aggregate_items = tuple(aggregates)
        except TypeError as error:
            raise TypeError(
                "aggregate_repository.load_all() must "
                "return an iterable"
            ) from error

        selected_aggregates = []

        for aggregate in aggregate_items:
            if not isinstance(
                aggregate,
                WeeklyConflictAggregate,
            ):
                raise TypeError(
                    "aggregate repository must contain "
                    "only WeeklyConflictAggregate objects"
                )

            if (
                snapshot_filter is not None
                and aggregate.source_snapshot_date
                != snapshot_filter
            ):
                continue

            if (
                country_filter is not None
                and aggregate.country_name.casefold()
                not in country_filter
                and (
                    aggregate.country_code is None
                    or aggregate.country_code.casefold()
                    not in country_filter
                )
            ):
                continue

            selected_aggregates.append(aggregate)

        return self.build_from_aggregates(
            selected_aggregates
        )

    @classmethod
    def build_from_aggregates(cls, aggregates):
        try:
            aggregate_items = tuple(aggregates)
        except TypeError as error:
            raise TypeError(
                "aggregates must be an iterable"
            ) from error

        grouped_aggregates = defaultdict(list)

        for aggregate in aggregate_items:
            if not isinstance(
                aggregate,
                WeeklyConflictAggregate,
            ):
                raise TypeError(
                    "aggregates must contain only "
                    "WeeklyConflictAggregate objects"
                )

            if aggregate.country_code is None:
                raise ValueError(
                    "country_code is required for "
                    "country-week analysis"
                )

            key = (
                aggregate.source_snapshot_date,
                aggregate.week_end_date,
                aggregate.country_name,
                aggregate.country_code,
            )
            grouped_aggregates[key].append(aggregate)

        features = [
            cls._build_feature(key, group)
            for key, group in grouped_aggregates.items()
        ]
        features.sort(
            key=lambda feature: (
                feature.source_snapshot_date,
                feature.week_end_date,
                feature.country_code,
                feature.country_name,
            )
        )

        return tuple(features)

    @staticmethod
    def _build_feature(key, aggregates):
        (
            source_snapshot_date,
            week_end_date,
            country_name,
            country_code,
        ) = key
        reviewed_by_values = {
            aggregate.reviewed_by
            for aggregate in aggregates
        }
        source_url_values = {
            aggregate.source_url
            for aggregate in aggregates
        }

        if len(reviewed_by_values) != 1:
            raise ValueError(
                "country-week aggregates must have "
                "one reviewed_by value"
            )

        if len(source_url_values) != 1:
            raise ValueError(
                "country-week aggregates must have "
                "one source_url value"
            )

        air_drone = [
            aggregate
            for aggregate in aggregates
            if aggregate.sub_event_type
            == _AIR_DRONE_STRIKE
        ]
        shelling_artillery_missile = [
            aggregate
            for aggregate in aggregates
            if aggregate.sub_event_type
            == _SHELLING_ARTILLERY_MISSILE
        ]
        political_violence = [
            aggregate
            for aggregate in aggregates
            if aggregate.is_political_violence
        ]
        violence_against_civilians = [
            aggregate
            for aggregate in aggregates
            if aggregate.event_type
            == AggregateEventType.VIOLENCE_AGAINST_CIVILIANS
        ]

        return WeeklyConflictFeature(
            source_snapshot_date=source_snapshot_date,
            week_end_date=week_end_date,
            country_name=country_name,
            country_code=country_code,
            source_row_count=len(aggregates),
            administrative_area_count=len(
                {
                    aggregate.geographic_id
                    for aggregate in aggregates
                }
            ),
            total_events=WeeklyConflictFeatureBuilder._sum(
                aggregates,
                "event_count",
            ),
            total_fatalities=(
                WeeklyConflictFeatureBuilder._sum(
                    aggregates,
                    "fatality_count",
                )
            ),
            political_violence_events=(
                WeeklyConflictFeatureBuilder._sum(
                    political_violence,
                    "event_count",
                )
            ),
            political_violence_fatalities=(
                WeeklyConflictFeatureBuilder._sum(
                    political_violence,
                    "fatality_count",
                )
            ),
            strike_events=(
                WeeklyConflictFeatureBuilder._sum(
                    air_drone,
                    "event_count",
                )
                + WeeklyConflictFeatureBuilder._sum(
                    shelling_artillery_missile,
                    "event_count",
                )
            ),
            strike_fatalities=(
                WeeklyConflictFeatureBuilder._sum(
                    air_drone,
                    "fatality_count",
                )
                + WeeklyConflictFeatureBuilder._sum(
                    shelling_artillery_missile,
                    "fatality_count",
                )
            ),
            air_drone_strike_events=(
                WeeklyConflictFeatureBuilder._sum(
                    air_drone,
                    "event_count",
                )
            ),
            air_drone_strike_fatalities=(
                WeeklyConflictFeatureBuilder._sum(
                    air_drone,
                    "fatality_count",
                )
            ),
            shelling_artillery_missile_events=(
                WeeklyConflictFeatureBuilder._sum(
                    shelling_artillery_missile,
                    "event_count",
                )
            ),
            shelling_artillery_missile_fatalities=(
                WeeklyConflictFeatureBuilder._sum(
                    shelling_artillery_missile,
                    "fatality_count",
                )
            ),
            violence_against_civilians_events=(
                WeeklyConflictFeatureBuilder._sum(
                    violence_against_civilians,
                    "event_count",
                )
            ),
            violence_against_civilians_fatalities=(
                WeeklyConflictFeatureBuilder._sum(
                    violence_against_civilians,
                    "fatality_count",
                )
            ),
            protest_events=(
                WeeklyConflictFeatureBuilder._sum_event_type(
                    aggregates,
                    AggregateEventType.PROTESTS,
                )
            ),
            riot_events=(
                WeeklyConflictFeatureBuilder._sum_event_type(
                    aggregates,
                    AggregateEventType.RIOTS,
                )
            ),
            strategic_development_events=(
                WeeklyConflictFeatureBuilder._sum_event_type(
                    aggregates,
                    AggregateEventType.STRATEGIC_DEVELOPMENTS,
                )
            ),
            reviewed_by=next(iter(reviewed_by_values)),
            source_url=next(iter(source_url_values)),
            created_at=max(
                aggregate.created_at
                for aggregate in aggregates
            ),
        )

    @staticmethod
    def _sum(aggregates, field_name):
        return sum(
            getattr(aggregate, field_name)
            for aggregate in aggregates
        )

    @staticmethod
    def _sum_event_type(aggregates, event_type):
        return sum(
            aggregate.event_count
            for aggregate in aggregates
            if aggregate.event_type == event_type
        )

    @staticmethod
    def _snapshot_date(value):
        if value is None:
            return None

        if (
            isinstance(value, date)
            and not isinstance(value, datetime)
        ):
            return value

        if not isinstance(value, str):
            raise TypeError(
                "source_snapshot_date must be a date, "
                "ISO date string or None"
            )

        try:
            return date.fromisoformat(value.strip())
        except ValueError as error:
            raise ValueError(
                "source_snapshot_date must use YYYY-MM-DD"
            ) from error

    @staticmethod
    def _countries(values):
        if values is None:
            return None

        if isinstance(values, str):
            values = (values,)

        try:
            country_values = tuple(values)
        except TypeError as error:
            raise TypeError(
                "countries must be an iterable of strings"
            ) from error

        normalized_values = set()

        for value in country_values:
            if not isinstance(value, str):
                raise TypeError(
                    "countries must contain only strings"
                )

            normalized = value.strip().casefold()

            if not normalized:
                raise ValueError(
                    "countries must not contain empty values"
                )

            normalized_values.add(normalized)

        return normalized_values
