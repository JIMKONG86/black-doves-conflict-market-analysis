"""Connection check and bounded ACLED download for the BLACK DOVES project."""

from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from acled_client import AcledClient, AcledCredentials


STUDY_COUNTRIES = ["Iran", "Israel", "United States", "Germany", "China"]
STUDY_START = "2026-01-01"
STUDY_END = "2026-08-18"
STUDY_FIELDS = [
    "event_id_cnty",
    "event_date",
    "time_precision",
    "disorder_type",
    "event_type",
    "sub_event_type",
    "actor1",
    "assoc_actor_1",
    "actor2",
    "assoc_actor_2",
    "country",
    "admin1",
    "location",
    "latitude",
    "longitude",
    "geo_precision",
    "source",
    "source_scale",
    "notes",
    "fatalities",
    "tags",
    "timestamp",
]


def build_client() -> AcledClient:
    load_dotenv()
    credentials = AcledCredentials(
        username=os.getenv("ACLED_USERNAME"),
        password=os.getenv("ACLED_PASSWORD"),
        access_token=os.getenv("ACLED_ACCESS_TOKEN"),
    )
    return AcledClient(credentials)


def smoke_test(client: AcledClient) -> None:
    rows = list(
        client.iter_events(
            {
                "country": "Israel",
                "year": 2026,
                "fields": "event_id_cnty|event_date|country|event_type|fatalities",
            },
            page_size=1,
            max_rows=1,
        )
    )
    if rows:
        row = rows[0]
        print(
            "Connection successful: "
            f"{row.get('event_id_cnty')} | {row.get('event_date')} | "
            f"{row.get('event_type')}"
        )
    else:
        print("Connection successful; the bounded test query returned zero rows.")


def download_study_data(client: AcledClient, output_path: Path) -> int:
    params = {
        "country": "|".join(STUDY_COUNTRIES),
        "event_date": f"{STUDY_START}|{STUDY_END}",
        "event_date_where": "BETWEEN",
        "fields": "|".join(STUDY_FIELDS),
    }
    rows = client.iter_events(params)
    return write_csv(rows, output_path, STUDY_FIELDS)


def write_csv(rows: Any, output_path: Path, fieldnames: list[str]) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with output_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
            count += 1
    return count


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--smoke-test", action="store_true", help="Request at most one row.")
    mode.add_argument(
        "--download-study-data",
        action="store_true",
        help="Download the frozen country/date sample to CSV.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/acled_events_2026-01-01_to_2026-08-18.csv"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    client = build_client()
    if args.smoke_test:
        smoke_test(client)
        return
    count = download_study_data(client, args.output)
    print(f"Downloaded {count} rows to {args.output}")


if __name__ == "__main__":
    main()
