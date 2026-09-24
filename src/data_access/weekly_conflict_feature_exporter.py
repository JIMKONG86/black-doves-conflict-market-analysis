import csv

from pathlib import Path

from src.models.weekly_conflict_feature import (
    WeeklyConflictFeature,
)


_FIELD_NAMES = (
    "feature_id",
    "source_snapshot_date",
    "week_end_date",
    "country_name",
    "country_code",
    "source_row_count",
    "administrative_area_count",
    "total_events",
    "total_fatalities",
    "political_violence_events",
    "political_violence_fatalities",
    "strike_events",
    "strike_fatalities",
    "air_drone_strike_events",
    "air_drone_strike_fatalities",
    "shelling_artillery_missile_events",
    "shelling_artillery_missile_fatalities",
    "violence_against_civilians_events",
    "violence_against_civilians_fatalities",
    "protest_events",
    "riot_events",
    "strategic_development_events",
    "reviewed_by",
    "source_url",
    "created_at",
)


class WeeklyConflictFeatureExporter:
    def export_csv(self, features, file_path):
        try:
            feature_items = tuple(features)
        except TypeError as error:
            raise TypeError(
                "features must be an iterable"
            ) from error

        for feature in feature_items:
            if not isinstance(
                feature,
                WeeklyConflictFeature,
            ):
                raise TypeError(
                    "features must contain only "
                    "WeeklyConflictFeature objects"
                )

        output_path = Path(file_path)

        if output_path.suffix.casefold() != ".csv":
            raise ValueError(
                "feature export file must use .csv"
            )

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        temporary_path = output_path.with_suffix(
            ".csv.tmp"
        )

        with temporary_path.open(
            "w",
            encoding="utf-8",
            newline="",
        ) as csv_file:
            writer = csv.DictWriter(
                csv_file,
                fieldnames=_FIELD_NAMES,
            )
            writer.writeheader()
            writer.writerows(
                self._serialize(feature)
                for feature in feature_items
            )

        temporary_path.replace(output_path)

        return output_path

    @staticmethod
    def _serialize(feature):
        return {
            field_name: (
                value.isoformat()
                if field_name
                in {
                    "source_snapshot_date",
                    "week_end_date",
                    "created_at",
                }
                else value
            )
            for field_name, value in (
                (field_name, getattr(feature, field_name))
                for field_name in _FIELD_NAMES
            )
        }
