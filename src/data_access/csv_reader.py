import csv
import logging


from src.models.observations import (
    ImpactObservation,
)
from src.models.source import DataSource


logger = logging.getLogger(__name__)


def parse_optional_integer(value):
    if value is None or str(value).strip() == "":
        return None

    return int(value)


def generate_csv_rows(file_path):
    with open(
        file_path,
        mode="r",
        encoding="utf-8",
        newline="",
    ) as csv_file:
        reader = csv.DictReader(csv_file)

        for row in reader:
            yield row


def generate_impact_observations(file_path):
    for line_number, row in enumerate(
        generate_csv_rows(file_path),
        start=2,
    ):
        try:
            source = DataSource(
                source_id=int(row["source_id"]),
                name=row["source_name"],
                source_type=row["source_type"],
                url=row["source_url"],
                publication_date=row["publication_date"],
            )

            impact = ImpactObservation(
                observation_date=row["observation_date"],
                affected_country=row["affected_country"],
                reported_civilian_deaths=parse_optional_integer(
                    row["reported_civilian_deaths"]
                ),
                reported_military_deaths=parse_optional_integer(
                    row["reported_military_deaths"]
                ),
                reported_civilian_facilities_destroyed=parse_optional_integer(
                    row["reported_civilian_facilities_destroyed"]
                ),
                reported_military_facilities_destroyed=parse_optional_integer(
                    row["reported_military_facilities_destroyed"]
                ),
                source=source,
                verification_status=row["verification_status"],
            )

        except (KeyError, TypeError, ValueError) as error:
            logger.error(
                "Skipping invalid CSV row %s: %s",
                line_number,
                error,
            )
            continue

        yield impact