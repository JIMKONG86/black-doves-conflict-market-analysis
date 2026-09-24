import hashlib

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd


_CONFLICT_REQUIRED_COLUMNS = {
    "feature_id",
    "source_snapshot_date",
    "week_end_date",
    "country_name",
    "country_code",
    "total_events",
    "total_fatalities",
    "strike_events",
    "strike_fatalities",
    "air_drone_strike_events",
    "air_drone_strike_fatalities",
    "shelling_artillery_missile_events",
    "shelling_artillery_missile_fatalities",
}

_MARKET_REQUIRED_COLUMNS = {
    "Date",
    "company_price",
    "benchmark_price",
    "company_return",
    "benchmark_return",
    "abnormal_return",
    "company_cumulative_return",
    "benchmark_cumulative_return",
    "cumulative_abnormal_return",
}

_MARKET_NUMERIC_COLUMNS = tuple(
    sorted(_MARKET_REQUIRED_COLUMNS - {"Date"})
)


@dataclass(frozen=True)
class WeeklyMarketConflictSummary:
    conflict_rows: int
    conflict_weeks: int
    market_daily_rows: int
    market_weeks: int
    joined_rows: int
    joined_weeks: int
    unmatched_conflict_rows: int
    first_joined_week: date
    last_joined_week: date


class WeeklyMarketConflictBuilder:
    def build(
        self,
        conflict_file,
        market_file,
        company_ticker="RHM.DE",
        benchmark_ticker="^GDAXI",
        market_source_url="https://finance.yahoo.com/",
        source_snapshot_date=None,
        countries=None,
    ):
        company_ticker = self._required_text(
            company_ticker,
            "company_ticker",
        )
        benchmark_ticker = self._required_text(
            benchmark_ticker,
            "benchmark_ticker",
        )
        market_source_url = self._source_url(
            market_source_url
        )
        snapshot_filter = self._optional_date(
            source_snapshot_date,
            "source_snapshot_date",
        )
        country_filter = self._countries(countries)

        conflict_data = self._read_csv(
            conflict_file,
            "weekly conflict feature",
        )
        market_data = self._read_csv(
            market_file,
            "market comparison",
        )

        self._required_columns(
            conflict_data,
            _CONFLICT_REQUIRED_COLUMNS,
            "weekly conflict feature",
        )
        self._required_columns(
            market_data,
            _MARKET_REQUIRED_COLUMNS,
            "market comparison",
        )

        conflict_data = self._prepare_conflict_data(
            conflict_data,
            snapshot_filter,
            country_filter,
        )
        market_data = self._prepare_market_data(
            market_data
        )
        weekly_market = self._aggregate_market_weeks(
            market_data
        )
        joined = conflict_data.merge(
            weekly_market,
            on="week_end_date",
            how="inner",
            validate="many_to_one",
        )

        if joined.empty:
            raise ValueError(
                "Conflict and market data have no "
                "overlapping weeks"
            )

        joined.insert(
            joined.columns.get_loc("market_date") + 1,
            "company_ticker",
            company_ticker,
        )
        joined.insert(
            joined.columns.get_loc("company_ticker") + 1,
            "benchmark_ticker",
            benchmark_ticker,
        )
        joined["market_source_url"] = market_source_url
        joined["market_conflict_id"] = joined.apply(
            lambda row: self._identifier(
                row["feature_id"],
                row["market_date"].date().isoformat(),
                company_ticker,
                benchmark_ticker,
                market_source_url,
            ),
            axis=1,
        )
        joined = joined.sort_values(
            [
                "source_snapshot_date",
                "week_end_date",
                "country_code",
            ]
        ).reset_index(drop=True)

        summary = WeeklyMarketConflictSummary(
            conflict_rows=len(conflict_data),
            conflict_weeks=(
                conflict_data["week_end_date"].nunique()
            ),
            market_daily_rows=len(market_data),
            market_weeks=(
                weekly_market["week_end_date"].nunique()
            ),
            joined_rows=len(joined),
            joined_weeks=joined["week_end_date"].nunique(),
            unmatched_conflict_rows=(
                len(conflict_data) - len(joined)
            ),
            first_joined_week=(
                joined["week_end_date"].min().date()
            ),
            last_joined_week=(
                joined["week_end_date"].max().date()
            ),
        )

        return joined, summary

    @staticmethod
    def export_csv(data, output_file):
        if not isinstance(data, pd.DataFrame):
            raise TypeError(
                "data must be a pandas DataFrame"
            )

        output_path = Path(output_file)

        if output_path.suffix.casefold() != ".csv":
            raise ValueError(
                "analysis output file must use .csv"
            )

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        temporary_path = output_path.with_suffix(
            ".csv.tmp"
        )
        export_data = data.copy()

        for column_name in (
            "source_snapshot_date",
            "week_end_date",
            "market_date",
        ):
            if column_name in export_data.columns:
                export_data[column_name] = (
                    export_data[column_name]
                    .dt.strftime("%Y-%m-%d")
                )

        export_data.to_csv(
            temporary_path,
            index=False,
        )
        temporary_path.replace(output_path)

        return output_path

    @staticmethod
    def _read_csv(file_path, label):
        path = Path(file_path)

        if not path.is_file():
            raise FileNotFoundError(
                f"{label.capitalize()} CSV file "
                f"not found: {path}"
            )

        return pd.read_csv(path)

    @staticmethod
    def _required_columns(data, required, label):
        missing_columns = required - set(data.columns)

        if missing_columns:
            missing = ", ".join(
                sorted(missing_columns)
            )
            raise ValueError(
                f"{label.capitalize()} CSV is missing "
                f"required columns: {missing}"
            )

    @classmethod
    def _prepare_conflict_data(
        cls,
        data,
        snapshot_filter,
        country_filter,
    ):
        result = data.copy()

        for column_name in (
            "source_snapshot_date",
            "week_end_date",
        ):
            result[column_name] = pd.to_datetime(
                result[column_name],
                errors="coerce",
            )

            if result[column_name].isna().any():
                raise ValueError(
                    f"{column_name} must contain only "
                    "valid dates"
                )

        if snapshot_filter is not None:
            result = result[
                result["source_snapshot_date"]
                == pd.Timestamp(snapshot_filter)
            ]

        if country_filter is not None:
            names = (
                result["country_name"]
                .astype(str)
                .str.strip()
                .str.casefold()
            )
            codes = (
                result["country_code"]
                .astype(str)
                .str.strip()
                .str.casefold()
            )
            result = result[
                names.isin(country_filter)
                | codes.isin(country_filter)
            ]

        if result.empty:
            raise ValueError(
                "No weekly conflict rows match the filters"
            )

        duplicate_mask = result.duplicated(
            subset=[
                "source_snapshot_date",
                "week_end_date",
                "country_code",
            ],
            keep=False,
        )

        if duplicate_mask.any():
            raise ValueError(
                "Weekly conflict features contain "
                "duplicate snapshot-country-week rows"
            )

        return result

    @classmethod
    def _prepare_market_data(cls, data):
        result = data.copy()
        result["Date"] = pd.to_datetime(
            result["Date"],
            errors="coerce",
        )

        if result["Date"].isna().any():
            raise ValueError(
                "Date must contain only valid dates"
            )

        if result["Date"].duplicated().any():
            raise ValueError(
                "Market comparison data contains "
                "duplicate dates"
            )

        for column_name in _MARKET_NUMERIC_COLUMNS:
            result[column_name] = pd.to_numeric(
                result[column_name],
                errors="coerce",
            )

            if result[column_name].isna().any():
                raise ValueError(
                    f"{column_name} must contain only "
                    "numeric values"
                )

        return result.sort_values("Date").reset_index(
            drop=True
        )

    @staticmethod
    def _aggregate_market_weeks(data):
        result = data.copy()
        days_until_saturday = (
            5 - result["Date"].dt.weekday
        ) % 7
        result["week_end_date"] = (
            result["Date"]
            + pd.to_timedelta(
                days_until_saturday,
                unit="D",
            )
        )

        return (
            result.groupby(
                "week_end_date",
                as_index=False,
                sort=True,
            )
            .agg(
                market_date=("Date", "max"),
                market_observation_count=(
                    "Date",
                    "size",
                ),
                company_price=("company_price", "last"),
                benchmark_price=(
                    "benchmark_price",
                    "last",
                ),
                company_weekly_return=(
                    "company_return",
                    WeeklyMarketConflictBuilder
                    ._compound_returns,
                ),
                benchmark_weekly_return=(
                    "benchmark_return",
                    WeeklyMarketConflictBuilder
                    ._compound_returns,
                ),
                weekly_abnormal_return=(
                    "abnormal_return",
                    "sum",
                ),
                company_cumulative_return=(
                    "company_cumulative_return",
                    "last",
                ),
                benchmark_cumulative_return=(
                    "benchmark_cumulative_return",
                    "last",
                ),
                cumulative_abnormal_return=(
                    "cumulative_abnormal_return",
                    "last",
                ),
            )
        )

    @staticmethod
    def _compound_returns(values):
        return (1.0 + values).prod() - 1.0

    @staticmethod
    def _required_text(value, field_name):
        if not isinstance(value, str):
            raise TypeError(
                f"{field_name} must be a string"
            )

        normalized = value.strip()

        if not normalized:
            raise ValueError(
                f"{field_name} must not be empty"
            )

        return normalized

    @classmethod
    def _source_url(cls, value):
        source_url = cls._required_text(
            value,
            "market_source_url",
        )
        parsed_url = urlparse(source_url)

        if (
            parsed_url.scheme not in {"http", "https"}
            or not parsed_url.netloc
        ):
            raise ValueError(
                "market_source_url must be a valid "
                "HTTP or HTTPS URL"
            )

        return source_url

    @staticmethod
    def _optional_date(value, field_name):
        if value is None:
            return None

        if (
            isinstance(value, date)
            and not isinstance(value, datetime)
        ):
            return value

        if not isinstance(value, str):
            raise TypeError(
                f"{field_name} must be a date, "
                "ISO date string or None"
            )

        try:
            return date.fromisoformat(value.strip())
        except ValueError as error:
            raise ValueError(
                f"{field_name} must use YYYY-MM-DD"
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

        result = set()

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

            result.add(normalized)

        return result

    @staticmethod
    def _identifier(*values):
        identity = "|".join(values)
        return hashlib.sha256(
            identity.encode("utf-8")
        ).hexdigest()
