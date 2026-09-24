import argparse
import csv
import json

from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

OUTPUT_DIRECTORY = (
    PROJECT_ROOT / "data" / "processed" / "acled"
)

COUNTRY_CODES = {
    "Iran": "IR",
    "Israel": "IL",
}

STATE_ACTOR_PREFIXES = {
    "Military Forces of Iran": "IR",
    "Military Forces of Israel": "IL",
    "Military Forces of the United States": "US",
    "Military Forces of Yemen": "YE",
}

REQUIRED_COLUMNS = {
    "event_id_cnty",
    "country",
    "actor1",
}

ADDED_COLUMNS = [
    "affected_country_code",
    "initiator_country_code",
    "initiator_mapping_method",
]


def calculate_sha256(file_path):
    return sha256(
        file_path.read_bytes()
    ).hexdigest()


def validate_columns(fieldnames):
    if fieldnames is None:
        raise ValueError(
            "The ACLED CSV file has no header."
        )

    missing_columns = (
        REQUIRED_COLUMNS - set(fieldnames)
    )

    if missing_columns:
        missing = ", ".join(
            sorted(missing_columns)
        )
        raise ValueError(
            f"Missing required columns: {missing}"
        )


def map_affected_country(country):
    country_code = COUNTRY_CODES.get(
        country.strip()
    )

    if not country_code:
        raise ValueError(
            f"Unsupported affected country: {country}"
        )

    return country_code


def map_initiator(actor1):
    actor_name = actor1.strip()

    for prefix, country_code in (
        STATE_ACTOR_PREFIXES.items()
    ):
        if actor_name.startswith(prefix):
            return (
                country_code,
                "actor1_state_force_prefix",
            )

    return "", "unmapped_or_non_state_actor"


def prepare_rows(input_file):
    prepared_rows = []
    affected_counts = Counter()
    initiator_counts = Counter()
    unmapped_actor_counts = Counter()

    with input_file.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as csv_file:
        reader = csv.DictReader(csv_file)
        validate_columns(reader.fieldnames)

        original_fields = list(reader.fieldnames)

        for row_number, row in enumerate(
            reader,
            start=2,
        ):
            try:
                affected_code = (
                    map_affected_country(
                        row["country"]
                    )
                )

                (
                    initiator_code,
                    mapping_method,
                ) = map_initiator(row["actor1"])

                row["affected_country_code"] = (
                    affected_code
                )
                row["initiator_country_code"] = (
                    initiator_code
                )
                row["initiator_mapping_method"] = (
                    mapping_method
                )

                affected_counts[affected_code] += 1

                if initiator_code:
                    initiator_counts[
                        initiator_code
                    ] += 1
                else:
                    unmapped_actor_counts[
                        row["actor1"]
                    ] += 1

                prepared_rows.append(row)

            except (AttributeError, ValueError) as error:
                event_id = row.get(
                    "event_id_cnty",
                    "unknown",
                )
                raise ValueError(
                    f"Row {row_number}, "
                    f"event {event_id}: {error}"
                ) from error

    output_fields = (
        original_fields + ADDED_COLUMNS
    )

    return {
        "rows": prepared_rows,
        "fieldnames": output_fields,
        "affected_counts": affected_counts,
        "initiator_counts": initiator_counts,
        "unmapped_actor_counts": (
            unmapped_actor_counts
        ),
    }


def save_prepared_csv(
    output_file,
    fieldnames,
    rows,
):
    OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_file.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def save_metadata(
    metadata_file,
    input_file,
    output_file,
    result,
):
    metadata = {
        "transformation": (
            "ACLED strike import preparation"
        ),
        "transformation_version": "1.0",
        "created_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "input_file": input_file.name,
        "input_sha256": calculate_sha256(
            input_file
        ),
        "output_file": output_file.name,
        "output_sha256": calculate_sha256(
            output_file
        ),
        "record_count": len(result["rows"]),
        "affected_country_mapping": (
            COUNTRY_CODES
        ),
        "state_actor_prefix_mapping": (
            STATE_ACTOR_PREFIXES
        ),
        "affected_country_counts": dict(
            result["affected_counts"]
        ),
        "initiator_country_counts": dict(
            result["initiator_counts"]
        ),
        "unmapped_actor_counts": dict(
            result["unmapped_actor_counts"]
        ),
    }

    metadata_file.write_text(
        json.dumps(
            metadata,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def parse_arguments():
    parser = argparse.ArgumentParser(
        description=(
            "Prepare an ACLED strike CSV "
            "for AcledStrikeImporter."
        )
    )

    parser.add_argument(
        "input_file",
        type=Path,
        help="Path to the raw ACLED CSV file.",
    )

    return parser.parse_args()


def main():
    arguments = parse_arguments()
    input_file = arguments.input_file.resolve()

    if not input_file.is_file():
        raise FileNotFoundError(
            f"Input file not found: {input_file}"
        )

    output_file = (
        OUTPUT_DIRECTORY
        / f"{input_file.stem}_prepared.csv"
    )
    metadata_file = output_file.with_suffix(
        ".metadata.json"
    )

    result = prepare_rows(input_file)

    save_prepared_csv(
        output_file=output_file,
        fieldnames=result["fieldnames"],
        rows=result["rows"],
    )

    save_metadata(
        metadata_file=metadata_file,
        input_file=input_file,
        output_file=output_file,
        result=result,
    )

    print("ACLED preparation completed.")
    print(
        f"Records prepared: "
        f"{len(result['rows'])}"
    )
    print(
        "Affected countries: "
        f"{dict(result['affected_counts'])}"
    )
    print(
        "Mapped initiators: "
        f"{dict(result['initiator_counts'])}"
    )
    print(
        "Unmapped actor groups: "
        f"{len(result['unmapped_actor_counts'])}"
    )
    print(f"CSV: {output_file}")
    print(f"Metadata: {metadata_file}")


if __name__ == "__main__":
    main()