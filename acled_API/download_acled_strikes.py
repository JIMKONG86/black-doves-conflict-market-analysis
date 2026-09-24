"""Download the bounded ACLED strike dataset with provenance metadata."""

from __future__ import annotations

import csv
import json
import os

from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

from dotenv import load_dotenv

from acled_client import (
    EVENTS_URL,
    AcledClient,
    AcledCredentials,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = Path(__file__).with_name(".env")

OUTPUT_DIRECTORY = (
    PROJECT_ROOT / "data" / "raw" / "acled"
)
OUTPUT_FILE = (
    OUTPUT_DIRECTORY
    / "acled_strikes_2026-01-01_2026-08-18.csv"
)
METADATA_FILE = OUTPUT_FILE.with_suffix(
    ".metadata.json"
)

PAGE_SIZE = 5000

FIELDS = [
    "event_id_cnty",
    "event_date",
    "event_type",
    "sub_event_type",
    "actor1",
    "assoc_actor_1",
    "inter1",
    "actor2",
    "assoc_actor_2",
    "inter2",
    "interaction",
    "country",
    "admin1",
    "admin2",
    "admin3",
    "location",
    "latitude",
    "longitude",
    "source",
    "source_scale",
    "notes",
    "fatalities",
    "timestamp",
]

QUERY_PARAMETERS = {
    "country": "Iran|Israel",
    "event_date": "2026-01-01|2026-08-18",
    "event_date_where": "BETWEEN",
    "sub_event_type": (
        "Air/drone strike|"
        "Shelling/artillery/missile attack"
    ),
    "fields": "|".join(FIELDS),
    "with_total": "true",
}


def build_client():
    load_dotenv(ENV_FILE)

    credentials = AcledCredentials(
        username=os.getenv("ACLED_USERNAME"),
        password=os.getenv("ACLED_PASSWORD"),
        access_token=os.getenv(
            "ACLED_ACCESS_TOKEN"
        ),
    )

    return AcledClient(
        credentials=credentials,
        timeout_seconds=60,
    )


def download_events(client):
    events = list(
        client.iter_events(
            QUERY_PARAMETERS,
            page_size=PAGE_SIZE,
        )
    )

    print(f"Downloaded {len(events)} events.")
    return events


def save_csv(events):
    OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=FIELDS,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(events)


def calculate_sha256(file_path):
    return sha256(
        file_path.read_bytes()
    ).hexdigest()


def save_metadata(record_count):
    metadata = {
        "source": "ACLED",
        "api_endpoint": EVENTS_URL,
        "retrieved_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "query_parameters": (
            QUERY_PARAMETERS
        ),
        "pagination": {
            "method": "cursor",
            "page_size": PAGE_SIZE,
        },
        "record_count": record_count,
        "output_file": OUTPUT_FILE.name,
        "sha256": calculate_sha256(
            OUTPUT_FILE
        ),
    }

    METADATA_FILE.write_text(
        json.dumps(
            metadata,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def main():
    client = build_client()
    events = download_events(client)

    if not events:
        raise RuntimeError(
            "No ACLED events matched the query. "
            "No output files were written."
        )

    save_csv(events)
    save_metadata(len(events))

    print(
        "ACLED download completed successfully."
    )
    print(f"Records saved: {len(events)}")
    print(f"CSV: {OUTPUT_FILE}")
    print(f"Metadata: {METADATA_FILE}")


if __name__ == "__main__":
    main()