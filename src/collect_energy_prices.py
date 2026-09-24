import argparse
import sys

from pathlib import Path

import requests

from src.data_access.energy_price_sources import (
    EIA_BRENT_URL,
    EU_FUEL_URL,
    EnergyPriceSourceProcessor,
)


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Download and align official Brent and German motor-fuel prices."
        )
    )
    parser.add_argument("--start-date", default="2026-01-01")
    parser.add_argument("--end-date", default="2026-08-18")
    parser.add_argument(
        "--brent-file",
        type=Path,
        default=Path("data/raw/energy/eia_brent_daily.xls"),
    )
    parser.add_argument(
        "--fuel-file",
        type=Path,
        default=Path("data/raw/energy/eu_weekly_oil_bulletin.xlsx"),
    )
    parser.add_argument(
        "--timeline-output",
        type=Path,
        default=Path("data/processed/energy/energy_price_timeline.csv"),
    )
    parser.add_argument(
        "--weekly-output",
        type=Path,
        default=Path("data/processed/energy/energy_price_weekly_panel.csv"),
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Replace existing raw source workbooks.",
    )
    return parser


def main(arguments=None):
    parser = build_parser()
    options = parser.parse_args(arguments)
    processor = EnergyPriceSourceProcessor()

    try:
        brent_path, brent_status = processor.download(
            EIA_BRENT_URL,
            options.brent_file,
            refresh=options.refresh,
        )
        fuel_path, fuel_status = processor.download(
            EU_FUEL_URL,
            options.fuel_file,
            refresh=options.refresh,
        )
        timeline, weekly, summary = processor.collect(
            brent_file=brent_path,
            fuel_file=fuel_path,
            start_date=options.start_date,
            end_date=options.end_date,
        )
        timeline_path = processor.export_csv(
            timeline, options.timeline_output
        )
        weekly_path = processor.export_csv(weekly, options.weekly_output)
    except (
        FileNotFoundError,
        KeyError,
        TypeError,
        ValueError,
        OSError,
        requests.RequestException,
    ) as error:
        parser.error(str(error))

    print("\nBLACK DOVES energy-price collection completed.")
    print(f"Period: {summary.start_date} to {summary.end_date}")
    print(f"Brent source: {brent_status}")
    print(f"EU fuel source: {fuel_status}")
    print(f"Brent daily observations: {summary.brent_daily_rows}")
    print(f"German weekly observations: {summary.fuel_weekly_rows}")
    print(f"Aligned weekly observations: {summary.aligned_weekly_rows}")
    print(f"Timeline: {timeline_path}")
    print(f"Weekly panel: {weekly_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
