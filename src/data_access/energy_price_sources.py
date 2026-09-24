from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd
import requests


EIA_BRENT_URL = (
    "https://www.eia.gov/dnav/pet/hist_xls/RBRTEd.xls"
)
EU_FUEL_URL = (
    "https://energy.ec.europa.eu/document/download/"
    "906e60ca-8b6a-44e7-8589-652854d2fd3f_en"
    "?filename=Weekly_Oil_Bulletin_Prices_History_maticni_4web.xlsx"
)
EIA_SOURCE_NAME = "U.S. Energy Information Administration"
EU_SOURCE_NAME = "European Commission Weekly Oil Bulletin"

_GERMAN_FUEL_COLUMNS = {
    "Prices with taxes": {
        "petrol_with_tax_eur_per_liter": (
            "DE_price_with_tax_euro95"
        ),
        "diesel_with_tax_eur_per_liter": (
            "DE_price_with_tax_diesel"
        ),
    },
    "Prices wo taxes": {
        "petrol_without_tax_eur_per_liter": (
            "DE_price_wo_tax_euro95"
        ),
        "diesel_without_tax_eur_per_liter": (
            "DE_price_wo_tax_diesel"
        ),
    },
}


@dataclass(frozen=True)
class EnergyPriceCollectionSummary:
    start_date: date
    end_date: date
    brent_daily_rows: int
    fuel_weekly_rows: int
    aligned_weekly_rows: int
    timeline_rows: int


class EnergyPriceSourceProcessor:
    """Parse and align official Brent and German motor-fuel prices."""

    def collect(
        self,
        brent_file,
        fuel_file,
        start_date,
        end_date,
    ):
        start = self._date_value(start_date, "start_date")
        end = self._date_value(end_date, "end_date")

        if start > end:
            raise ValueError("start_date must not be after end_date")

        brent = self.parse_brent(brent_file)
        fuels = self.parse_german_fuels(fuel_file)
        weekly = self._weekly_panel(brent, fuels)
        timeline = self._timeline(brent, fuels, start, end)
        weekly = weekly[
            weekly["fuel_observation_date"].between(start, end)
        ].reset_index(drop=True)

        if timeline.empty or weekly.empty:
            raise ValueError(
                "The selected date range does not contain aligned energy prices"
            )

        summary = EnergyPriceCollectionSummary(
            start_date=start.date(),
            end_date=end.date(),
            brent_daily_rows=int(
                brent["market_date"].between(start, end).sum()
            ),
            fuel_weekly_rows=int(
                fuels["fuel_observation_date"].between(start, end).sum()
            ),
            aligned_weekly_rows=len(weekly),
            timeline_rows=len(timeline),
        )
        return timeline, weekly, summary

    @staticmethod
    def download(
        url,
        destination,
        session=None,
        refresh=False,
        timeout_seconds=120,
    ):
        destination = Path(destination)

        if destination.is_file() and not refresh:
            return destination, "SKIPPED_EXISTING"

        destination.parent.mkdir(parents=True, exist_ok=True)
        client = session or requests.Session()
        response = client.get(
            url,
            headers={
                "Accept": (
                    "application/vnd.ms-excel,application/vnd.openxmlformats-"
                    "officedocument.spreadsheetml.sheet,*/*"
                ),
                "User-Agent": "BLACK-DOVES-academic-research/1.0",
            },
            timeout=timeout_seconds,
        )
        response.raise_for_status()

        if not response.content:
            raise ValueError(f"Downloaded source is empty: {url}")

        temporary_path = destination.with_suffix(
            destination.suffix + ".part"
        )
        temporary_path.write_bytes(response.content)
        temporary_path.replace(destination)
        return destination, "DOWNLOADED"

    @staticmethod
    def parse_brent(input_file):
        input_path = Path(input_file)

        if not input_path.is_file():
            raise FileNotFoundError(
                f"EIA Brent workbook not found: {input_path}"
            )

        raw = pd.read_excel(
            input_path,
            sheet_name="Data 1",
            header=None,
            skiprows=3,
            usecols=[0, 1],
            names=["market_date", "brent_usd_per_barrel"],
        )
        result = raw.copy()
        result["market_date"] = pd.to_datetime(
            result["market_date"], errors="coerce"
        )
        result["brent_usd_per_barrel"] = pd.to_numeric(
            result["brent_usd_per_barrel"], errors="coerce"
        )
        result = result.dropna().sort_values("market_date")

        if result.empty:
            raise ValueError("EIA Brent workbook contains no usable observations")
        if (result["brent_usd_per_barrel"] <= 0).any():
            raise ValueError("Brent prices must be positive")
        if result["market_date"].duplicated().any():
            raise ValueError("EIA Brent workbook contains duplicate dates")

        return result.reset_index(drop=True)

    @classmethod
    def parse_german_fuels(cls, input_file):
        input_path = Path(input_file)

        if not input_path.is_file():
            raise FileNotFoundError(
                f"EU Weekly Oil Bulletin workbook not found: {input_path}"
            )

        frames = []

        for sheet_name, column_map in _GERMAN_FUEL_COLUMNS.items():
            raw = pd.read_excel(input_path, sheet_name=sheet_name, header=0)
            date_column = raw.columns[0]
            missing = set(column_map.values()) - set(raw.columns)

            if missing:
                names = ", ".join(sorted(missing))
                raise ValueError(
                    f"EU workbook sheet {sheet_name!r} is missing columns: {names}"
                )

            selected = raw[[date_column, *column_map.values()]].copy()
            selected.columns = [
                "fuel_observation_date",
                *column_map.keys(),
            ]
            selected["fuel_observation_date"] = pd.to_datetime(
                selected["fuel_observation_date"],
                errors="coerce",
                format="mixed",
            )

            for column_name in column_map:
                selected[column_name] = (
                    pd.to_numeric(selected[column_name], errors="coerce")
                    / 1000.0
                )

            selected = selected.dropna(
                subset=["fuel_observation_date", *column_map.keys()]
            )
            frames.append(selected)

        result = frames[0].merge(
            frames[1], on="fuel_observation_date", how="inner", validate="1:1"
        )
        result = result.sort_values("fuel_observation_date")

        if result.empty:
            raise ValueError(
                "EU Weekly Oil Bulletin contains no usable German fuel prices"
            )
        value_columns = [
            column
            for column in result.columns
            if column.endswith("_eur_per_liter")
        ]
        if (result[value_columns] <= 0).any().any():
            raise ValueError("German fuel prices must be positive")
        if result["fuel_observation_date"].duplicated().any():
            raise ValueError("German fuel data contains duplicate dates")

        return result.reset_index(drop=True)

    @classmethod
    def export_csv(cls, data, output_file):
        if not isinstance(data, pd.DataFrame):
            raise TypeError("data must be a pandas DataFrame")

        output_path = Path(output_file)
        if output_path.suffix.casefold() != ".csv":
            raise ValueError("Energy price output must use .csv")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        export = data.copy()

        for column_name in export.columns:
            if column_name.endswith("_date") or column_name.endswith(
                "_week_start"
            ) or column_name.endswith("_week_end"):
                if pd.api.types.is_datetime64_any_dtype(export[column_name]):
                    export[column_name] = export[column_name].dt.strftime(
                        "%Y-%m-%d"
                    )

        temporary_path = output_path.with_suffix(".csv.tmp")
        export.to_csv(temporary_path, index=False)
        temporary_path.replace(output_path)
        return output_path

    @staticmethod
    def _weekly_panel(brent, fuels):
        weekly_brent = brent.copy()
        weekly_brent["brent_week_start"] = (
            weekly_brent["market_date"]
            - pd.to_timedelta(weekly_brent["market_date"].dt.weekday, unit="D")
        )
        weekly_brent = (
            weekly_brent.groupby("brent_week_start", as_index=False)
            .agg(
                brent_usd_per_barrel=("brent_usd_per_barrel", "mean"),
                brent_observations=("brent_usd_per_barrel", "size"),
            )
            .sort_values("brent_week_start")
        )
        weekly_brent["brent_week_end"] = (
            weekly_brent["brent_week_start"] + pd.Timedelta(days=6)
        )
        weekly_brent["fuel_observation_date"] = (
            weekly_brent["brent_week_start"] + pd.Timedelta(days=7)
        )
        weekly_brent["brent_weekly_pct_change"] = weekly_brent[
            "brent_usd_per_barrel"
        ].pct_change(fill_method=None)

        fuel = fuels.copy().sort_values("fuel_observation_date")
        fuel_columns = [
            column
            for column in fuel.columns
            if column.endswith("_eur_per_liter")
        ]
        for column_name in fuel_columns:
            fuel[f"{column_name}_pct_change"] = fuel[column_name].pct_change(
                fill_method=None
            )

        panel = weekly_brent.merge(
            fuel, on="fuel_observation_date", how="inner", validate="1:1"
        )
        panel["brent_source_name"] = EIA_SOURCE_NAME
        panel["brent_source_url"] = EIA_BRENT_URL
        panel["fuel_source_name"] = EU_SOURCE_NAME
        panel["fuel_source_url"] = EU_FUEL_URL
        return panel.sort_values("fuel_observation_date").reset_index(drop=True)

    @staticmethod
    def _timeline(brent, fuels, start, end):
        rows = []
        definitions = [
            (
                "BRENT",
                "Brent crude",
                "ALL",
                "NOT_APPLICABLE",
                brent,
                "market_date",
                "brent_usd_per_barrel",
                "USD/barrel",
                EIA_SOURCE_NAME,
                EIA_BRENT_URL,
            ),
            (
                "PETROL_WITH_TAX",
                "Petrol Euro 95 incl. taxes",
                "PETROL",
                "WITH_TAX",
                fuels,
                "fuel_observation_date",
                "petrol_with_tax_eur_per_liter",
                "EUR/litre",
                EU_SOURCE_NAME,
                EU_FUEL_URL,
            ),
            (
                "PETROL_WITHOUT_TAX",
                "Petrol Euro 95 excl. taxes",
                "PETROL",
                "WITHOUT_TAX",
                fuels,
                "fuel_observation_date",
                "petrol_without_tax_eur_per_liter",
                "EUR/litre",
                EU_SOURCE_NAME,
                EU_FUEL_URL,
            ),
            (
                "DIESEL_WITH_TAX",
                "Diesel incl. taxes",
                "DIESEL",
                "WITH_TAX",
                fuels,
                "fuel_observation_date",
                "diesel_with_tax_eur_per_liter",
                "EUR/litre",
                EU_SOURCE_NAME,
                EU_FUEL_URL,
            ),
            (
                "DIESEL_WITHOUT_TAX",
                "Diesel excl. taxes",
                "DIESEL",
                "WITHOUT_TAX",
                fuels,
                "fuel_observation_date",
                "diesel_without_tax_eur_per_liter",
                "EUR/litre",
                EU_SOURCE_NAME,
                EU_FUEL_URL,
            ),
        ]

        for (
            series_id,
            label,
            product,
            tax_basis,
            frame,
            date_column,
            value_column,
            unit,
            source_name,
            source_url,
        ) in definitions:
            selected = frame[
                frame[date_column].between(start, end)
            ][[date_column, value_column]].dropna()
            if selected.empty:
                continue
            baseline = float(selected[value_column].iloc[0])
            for observation_date, value in selected.itertuples(index=False):
                rows.append(
                    {
                        "observation_date": observation_date,
                        "series_id": series_id,
                        "series_label": label,
                        "product": product,
                        "tax_basis": tax_basis,
                        "value": float(value),
                        "indexed_value": float(value) / baseline * 100.0,
                        "unit": unit,
                        "source_name": source_name,
                        "source_url": source_url,
                    }
                )

        return pd.DataFrame(rows).sort_values(
            ["series_id", "observation_date"]
        ).reset_index(drop=True)

    @staticmethod
    def _date_value(value, name):
        parsed = pd.to_datetime(value, errors="coerce")
        if pd.isna(parsed):
            raise ValueError(f"{name} must be a valid date")
        return parsed.normalize()
