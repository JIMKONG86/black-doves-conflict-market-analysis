import json
import re

from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

from src.models.weekly_conflict_aggregate import (
    AggregateDisorderType,
    AggregateEventType,
    WeeklyConflictAggregate,
)


class WeeklyConflictAggregateRepository:
    def __init__(
        self,
        directory=Path(
            "data/validated/"
            "weekly_conflict_aggregates"
        ),
    ):
        self.directory = Path(directory)
        self._identifier_index = None

    def save(self, aggregate):
        file_paths = self.save_many(
            (aggregate,)
        )

        return file_paths[0]

    def save_many(self, aggregates):
        try:
            aggregate_items = tuple(aggregates)
        except TypeError as error:
            raise TypeError(
                "aggregates must be an iterable"
            ) from error

        if not aggregate_items:
            return ()

        for aggregate in aggregate_items:
            if not isinstance(
                aggregate,
                WeeklyConflictAggregate,
            ):
                raise TypeError(
                    "aggregates must contain only "
                    "WeeklyConflictAggregate objects"
                )

        identifiers = [
            aggregate.aggregate_id
            for aggregate in aggregate_items
        ]

        if len(identifiers) != len(
            set(identifiers)
        ):
            raise ValueError(
                "Weekly aggregate batch contains "
                "duplicates"
            )

        self.directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        grouped_aggregates = defaultdict(list)

        for aggregate in aggregate_items:
            grouped_aggregates[
                self._file_path(aggregate)
            ].append(aggregate)

        pending_writes = []

        for file_path, new_aggregates in (
            grouped_aggregates.items()
        ):
            first_aggregate = new_aggregates[0]

            if file_path.exists():
                payload = self._read_file(
                    file_path
                )
                self._validate_payload_group(
                    payload,
                    first_aggregate,
                )
            else:
                payload = self._new_payload(
                    first_aggregate
                )

            stored_aggregates = payload.get(
                "aggregates"
            )

            if not isinstance(
                stored_aggregates,
                list,
            ):
                raise ValueError(
                    "Stored aggregates must be a list"
                )

            stored_identifiers = {
                stored_aggregate.get(
                    "aggregate_id"
                )
                for stored_aggregate
                in stored_aggregates
                if isinstance(
                    stored_aggregate,
                    dict,
                )
            }
            new_identifiers = {
                aggregate.aggregate_id
                for aggregate in new_aggregates
            }

            if (
                stored_identifiers
                & new_identifiers
            ):
                raise ValueError(
                    "Weekly conflict aggregate "
                    "already exists"
                )

            stored_aggregates.extend(
                self._serialize_aggregate(
                    aggregate
                )
                for aggregate in new_aggregates
            )
            stored_aggregates.sort(
                key=self._stored_sort_key
            )
            pending_writes.append(
                (file_path, payload)
            )

        for file_path, payload in pending_writes:
            self._write_file(
                file_path=file_path,
                payload=payload,
            )

        if self._identifier_index is not None:
            self._identifier_index.update(
                identifiers
            )

        return tuple(
            file_path
            for file_path, payload
            in pending_writes
        )

    def load_all(self):
        if not self.directory.exists():
            return []

        aggregates = []

        for file_path in sorted(
            self.directory.glob("*.json")
        ):
            payload = self._read_file(file_path)
            stored_aggregates = payload.get(
                "aggregates"
            )

            if not isinstance(
                stored_aggregates,
                list,
            ):
                raise ValueError(
                    "Stored aggregates must be a list"
                )

            aggregates.extend(
                self._deserialize_aggregate(
                    stored_aggregate
                )
                for stored_aggregate
                in stored_aggregates
            )

        return aggregates

    def contains(self, aggregate_id):
        normalized_identifier = (
            self._validate_identifier(
                aggregate_id,
                "aggregate_id",
            )
        )
        self._ensure_identifier_index()

        return (
            normalized_identifier
            in self._identifier_index
        )

    def _ensure_identifier_index(self):
        if self._identifier_index is not None:
            return

        identifier_index = set()

        if self.directory.exists():
            for file_path in self.directory.glob(
                "*.json"
            ):
                payload = self._read_file(
                    file_path
                )
                stored_aggregates = payload.get(
                    "aggregates"
                )

                if not isinstance(
                    stored_aggregates,
                    list,
                ):
                    raise ValueError(
                        "Stored aggregates must be "
                        "a list"
                    )

                for stored_aggregate in (
                    stored_aggregates
                ):
                    if not isinstance(
                        stored_aggregate,
                        dict,
                    ):
                        raise ValueError(
                            "Stored aggregate must be "
                            "an object"
                        )

                    aggregate_id = (
                        self._validate_identifier(
                            stored_aggregate.get(
                                "aggregate_id"
                            ),
                            "aggregate_id",
                        )
                    )

                    if aggregate_id in identifier_index:
                        raise ValueError(
                            "Stored aggregate identifier "
                            "is duplicated"
                        )

                    identifier_index.add(
                        aggregate_id
                    )

        self._identifier_index = identifier_index

    def _file_path(self, aggregate):
        if aggregate.country_code is not None:
            country_key = aggregate.country_code
        else:
            country_key = self._slug(
                aggregate.country_name
            )

        return self.directory / (
            f"{country_key}_"
            f"{aggregate.source_snapshot_date.isoformat()}"
            ".json"
        )

    @staticmethod
    def _slug(value):
        slug = re.sub(
            r"[^a-z0-9]+",
            "_",
            value.casefold(),
        ).strip("_")

        if not slug:
            raise ValueError(
                "country_name cannot create an "
                "empty file key"
            )

        return slug

    @staticmethod
    def _new_payload(aggregate):
        return {
            "country_name": aggregate.country_name,
            "country_code": aggregate.country_code,
            "source_snapshot_date": (
                aggregate
                .source_snapshot_date
                .isoformat()
            ),
            "aggregates": [],
        }

    @staticmethod
    def _validate_payload_group(
        payload,
        aggregate,
    ):
        expected_values = {
            "country_name": aggregate.country_name,
            "country_code": aggregate.country_code,
            "source_snapshot_date": (
                aggregate
                .source_snapshot_date
                .isoformat()
            ),
        }

        for field_name, expected_value in (
            expected_values.items()
        ):
            if payload.get(field_name) != expected_value:
                raise ValueError(
                    f"Stored {field_name} does not "
                    "match the aggregate group"
                )

    @staticmethod
    def _stored_sort_key(stored_aggregate):
        if not isinstance(stored_aggregate, dict):
            raise ValueError(
                "Stored aggregate must be an object"
            )

        return (
            stored_aggregate.get(
                "week_end_date",
                "",
            ),
            stored_aggregate.get("admin1", ""),
            stored_aggregate.get(
                "event_type",
                "",
            ),
            stored_aggregate.get(
                "sub_event_type",
                "",
            ),
            stored_aggregate.get(
                "aggregate_id",
                "",
            ),
        )

    @staticmethod
    def _validate_identifier(
        value,
        field_name,
    ):
        if not isinstance(value, str):
            raise TypeError(
                f"{field_name} must be a string"
            )

        normalized_value = value.strip().lower()

        if not re.fullmatch(
            r"[a-f0-9]{64}",
            normalized_value,
        ):
            raise ValueError(
                f"{field_name} must be a "
                "64-character hexadecimal ID"
            )

        return normalized_value

    @staticmethod
    def _read_file(file_path):
        with file_path.open(
            "r",
            encoding="utf-8",
        ) as file:
            payload = json.load(file)

        if not isinstance(payload, dict):
            raise ValueError(
                "Stored weekly aggregate data "
                "must be an object"
            )

        return payload

    @staticmethod
    def _write_file(
        file_path,
        payload,
    ):
        temporary_path = file_path.with_suffix(
            ".json.tmp"
        )

        with temporary_path.open(
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                payload,
                file,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )

        temporary_path.replace(file_path)

    @staticmethod
    def _serialize_aggregate(aggregate):
        return {
            "aggregate_id": aggregate.aggregate_id,
            "source_snapshot_date": (
                aggregate
                .source_snapshot_date
                .isoformat()
            ),
            "week_end_date": (
                aggregate.week_end_date.isoformat()
            ),
            "region": aggregate.region,
            "country_name": aggregate.country_name,
            "country_code": aggregate.country_code,
            "admin1": aggregate.admin1,
            "event_type": aggregate.event_type.value,
            "sub_event_type": (
                aggregate.sub_event_type
            ),
            "event_count": aggregate.event_count,
            "fatality_count": (
                aggregate.fatality_count
            ),
            "population_exposure": (
                aggregate.population_exposure
            ),
            "disorder_type": (
                aggregate.disorder_type.value
            ),
            "geographic_id": aggregate.geographic_id,
            "centroid_latitude": (
                aggregate.centroid_latitude
            ),
            "centroid_longitude": (
                aggregate.centroid_longitude
            ),
            "reviewed_by": aggregate.reviewed_by,
            "source_url": aggregate.source_url,
            "created_at": (
                aggregate.created_at.isoformat()
            ),
        }

    @staticmethod
    def _deserialize_aggregate(stored_aggregate):
        if not isinstance(stored_aggregate, dict):
            raise ValueError(
                "Stored aggregate must be an object"
            )

        aggregate = WeeklyConflictAggregate(
            source_snapshot_date=date.fromisoformat(
                stored_aggregate[
                    "source_snapshot_date"
                ]
            ),
            week_end_date=date.fromisoformat(
                stored_aggregate[
                    "week_end_date"
                ]
            ),
            region=stored_aggregate["region"],
            country_name=(
                stored_aggregate["country_name"]
            ),
            country_code=stored_aggregate.get(
                "country_code"
            ),
            admin1=stored_aggregate["admin1"],
            event_type=AggregateEventType(
                stored_aggregate["event_type"]
            ),
            sub_event_type=(
                stored_aggregate[
                    "sub_event_type"
                ]
            ),
            event_count=stored_aggregate[
                "event_count"
            ],
            fatality_count=(
                stored_aggregate[
                    "fatality_count"
                ]
            ),
            population_exposure=(
                stored_aggregate.get(
                    "population_exposure"
                )
            ),
            disorder_type=AggregateDisorderType(
                stored_aggregate["disorder_type"]
            ),
            geographic_id=stored_aggregate[
                "geographic_id"
            ],
            centroid_latitude=(
                stored_aggregate[
                    "centroid_latitude"
                ]
            ),
            centroid_longitude=(
                stored_aggregate[
                    "centroid_longitude"
                ]
            ),
            reviewed_by=stored_aggregate[
                "reviewed_by"
            ],
            source_url=stored_aggregate[
                "source_url"
            ],
            created_at=datetime.fromisoformat(
                stored_aggregate["created_at"]
            ),
        )

        stored_identifier = stored_aggregate.get(
            "aggregate_id"
        )

        if aggregate.aggregate_id != stored_identifier:
            raise ValueError(
                "Stored aggregate_id is invalid"
            )

        return aggregate
