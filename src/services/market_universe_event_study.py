import math

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd

from src.models.market_event import MarketEvent
from src.services.ols_market_model import MARKET_MODEL_ABNORMAL_RETURN_COLUMN


_REQUIRED_MARKET_COLUMNS = {
    "Date",
    "company_id",
    "company_name",
    "market_data_ticker",
    "benchmark_ticker",
    "trade_currency",
    "primary_listing_exchange",
    "analysis_tier",
    "role_category",
    "is_confirmatory",
    "company_return",
    "benchmark_return",
    "abnormal_return",
}

_METADATA_COLUMNS = (
    "company_id",
    "company_name",
    "market_data_ticker",
    "benchmark_ticker",
    "trade_currency",
    "primary_listing_exchange",
    "analysis_tier",
    "role_category",
    "is_confirmatory",
)

# Optional column produced by src.services.ols_market_model. When present
# in the market panel, the event study additionally reports OLS
# market-model-based abnormal returns/CAR/AAR/CAAR alongside the naive
# market-adjusted ones, without requiring or breaking panels that do not
# have it (e.g. older exports or unit-test fixtures).
_OLS_ABNORMAL_RETURN_COLUMN = MARKET_MODEL_ABNORMAL_RETURN_COLUMN

# Company-level diagnostics produced by the pre-event OLS market model.  They
# are optional so legacy panels remain valid, but when present they are carried
# into the event-study exports.  Keeping beta and R-squared beside the CARs is
# important for interpretation: a low beta is not evidence of low conflict
# sensitivity, and a low R-squared warns that the single benchmark explains
# little of the company's return variation.
_OLS_DIAGNOSTIC_COLUMNS = (
    "ols_estimation_window_observations",
    "ols_status",
    "ols_alpha",
    "ols_beta",
    "ols_r_squared",
)


@dataclass(frozen=True)
class MarketUniverseEventStudySummary:
    event_count: int
    company_count: int
    confirmatory_count: int
    exploratory_count: int
    post_hoc_count: int
    detail_rows: int
    first_market_date: date
    last_market_date: date
    pre_days: int
    post_days: int


class MarketUniverseEventStudy:
    def analyze(self, events, market_file, pre_days=5, post_days=10):
        event_items = self._events(events)
        pre_days = self._non_negative_int(pre_days, "pre_days")
        post_days = self._non_negative_int(post_days, "post_days")
        market = self._market_data(market_file)
        details = []
        summaries = []

        for company_id, company_data in market.groupby(
            "company_id", sort=True
        ):
            company = self._company_data(company_id, company_data)

            for event in event_items:
                detail, summary = self._analyze_company_event(
                    event=event,
                    company=company,
                    pre_days=pre_days,
                    post_days=post_days,
                )
                details.extend(detail)
                summaries.append(summary)

        detail_frame = pd.DataFrame(details)
        company_summary = pd.DataFrame(summaries)
        sample_summary = self._aggregate(
            detail_frame,
            group_columns=[
                "event_id",
                "event_calendar_date",
                "event_title",
                "sample_group",
            ],
        )
        role_summary = self._aggregate(
            detail_frame,
            group_columns=[
                "event_id",
                "event_calendar_date",
                "event_title",
                "role_category",
            ],
        )
        company_groups = company_summary.drop_duplicates("company_id")
        counts = company_groups["sample_group"].value_counts()
        run_summary = MarketUniverseEventStudySummary(
            event_count=len(event_items),
            company_count=company_summary["company_id"].nunique(),
            confirmatory_count=int(counts.get("CONFIRMATORY", 0)),
            exploratory_count=int(counts.get("EXPLORATORY", 0)),
            post_hoc_count=int(counts.get("POST_HOC_EXPLORATORY", 0)),
            detail_rows=len(detail_frame),
            first_market_date=market["Date"].min().date(),
            last_market_date=market["Date"].max().date(),
            pre_days=pre_days,
            post_days=post_days,
        )

        return (
            detail_frame,
            company_summary,
            sample_summary,
            role_summary,
            run_summary,
        )

    @staticmethod
    def export_csv(data, output_file):
        if not isinstance(data, pd.DataFrame):
            raise TypeError("data must be a pandas DataFrame")

        path = Path(output_file)

        if path.suffix.casefold() != ".csv":
            raise ValueError(f"CSV output required: {path}")

        path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = path.with_suffix(".csv.tmp")
        export = data.copy()

        for column in (
            "event_calendar_date",
            "effective_market_date",
            "market_date",
        ):
            if column in export.columns:
                export[column] = pd.to_datetime(export[column]).dt.strftime(
                    "%Y-%m-%d"
                )

        export.to_csv(temporary_path, index=False)
        temporary_path.replace(path)
        return path

    @classmethod
    def _analyze_company_event(cls, event, company, pre_days, post_days):
        event_timestamp = pd.Timestamp(event.event_date)
        positions = company.index[company["Date"] >= event_timestamp]

        if positions.empty:
            raise ValueError(
                f"No market observation for {company.loc[0, 'company_id']} "
                f"on or after {event.event_date.isoformat()}"
            )

        event_position = int(positions[0])
        start_position = event_position - pre_days
        end_position = event_position + post_days

        if start_position < 0 or end_position >= len(company):
            raise ValueError(
                "Market data does not cover the complete event window for "
                f"{company.loc[0, 'company_id']} and {event.event_id}"
            )

        window = company.iloc[start_position : end_position + 1].copy()
        window["relative_trading_day"] = range(-pre_days, post_days + 1)
        window["event_window_car"] = window["abnormal_return"].cumsum()
        has_ols = _OLS_ABNORMAL_RETURN_COLUMN in window.columns

        if has_ols:
            window["ols_event_window_car"] = window[
                _OLS_ABNORMAL_RETURN_COLUMN
            ].cumsum()

        effective_date = company.loc[event_position, "Date"]
        common = cls._common_fields(event, company, effective_date)
        detail = []

        for row in window.to_dict(orient="records"):
            detail_row = {
                **common,
                "market_date": row["Date"],
                "relative_trading_day": row["relative_trading_day"],
                "company_return": row["company_return"],
                "benchmark_return": row["benchmark_return"],
                "abnormal_return": row["abnormal_return"],
                "event_window_car": row["event_window_car"],
            }

            if has_ols:
                detail_row[_OLS_ABNORMAL_RETURN_COLUMN] = row[
                    _OLS_ABNORMAL_RETURN_COLUMN
                ]
                detail_row["ols_event_window_car"] = row[
                    "ols_event_window_car"
                ]

            detail.append(detail_row)

        summary = {
            **common,
            "pre_days": pre_days,
            "post_days": post_days,
            "pre_event_car": cls._car(window, -pre_days, -1),
            "event_day_abnormal_return": cls._car(window, 0, 0),
            "post_event_car_0_1": cls._car(window, 0, 1),
            "post_event_car_0_5": cls._car(window, 0, 5),
            "post_event_car_0_10": cls._car(window, 0, 10),
            "full_window_car": float(window["abnormal_return"].sum()),
        }

        if has_ols:
            summary.update(
                {
                    "ols_pre_event_car": cls._car(
                        window,
                        -pre_days,
                        -1,
                        column=_OLS_ABNORMAL_RETURN_COLUMN,
                    ),
                    "ols_event_day_abnormal_return": cls._car(
                        window, 0, 0, column=_OLS_ABNORMAL_RETURN_COLUMN
                    ),
                    "ols_post_event_car_0_1": cls._car(
                        window, 0, 1, column=_OLS_ABNORMAL_RETURN_COLUMN
                    ),
                    "ols_post_event_car_0_5": cls._car(
                        window, 0, 5, column=_OLS_ABNORMAL_RETURN_COLUMN
                    ),
                    "ols_post_event_car_0_10": cls._car(
                        window, 0, 10, column=_OLS_ABNORMAL_RETURN_COLUMN
                    ),
                    "ols_full_window_car": float(
                        window[_OLS_ABNORMAL_RETURN_COLUMN].sum()
                    ),
                }
            )

        return detail, summary

    @staticmethod
    def _common_fields(event, company, effective_date):
        row = company.iloc[0]
        sample_group = _sample_group(
            row["analysis_tier"], row["is_confirmatory"]
        )

        common = {
            "event_id": event.event_id,
            "event_calendar_date": pd.Timestamp(event.event_date),
            "effective_market_date": effective_date,
            "event_date_shift_days": (
                effective_date - pd.Timestamp(event.event_date)
            ).days,
            "event_title": event.title,
            "event_type": event.event_type,
            "affected_country_codes": " | ".join(
                event.affected_country_codes
            ),
            "event_verification_status": event.verification_status,
            "event_source_name": event.source_name,
            "event_source_url": event.source_url,
            "event_notes": event.notes,
            "company_id": row["company_id"],
            "company_name": row["company_name"],
            "market_data_ticker": row["market_data_ticker"],
            "benchmark_ticker": row["benchmark_ticker"],
            "trade_currency": row["trade_currency"],
            "primary_listing_exchange": row["primary_listing_exchange"],
            "analysis_tier": row["analysis_tier"],
            "role_category": row["role_category"],
            "is_confirmatory": bool(row["is_confirmatory"]),
            "sample_group": sample_group,
        }

        for column in _OLS_DIAGNOSTIC_COLUMNS:
            if column in company.columns:
                common[column] = row[column]

        return common

    @staticmethod
    def _aggregate(detail, group_columns):
        has_ols = (
            not detail.empty
            and _OLS_ABNORMAL_RETURN_COLUMN in detail.columns
        )
        columns = [
            *group_columns,
            "relative_trading_day",
            "company_count",
            "aar",
            "aar_standard_deviation",
            "aar_standard_error",
            "caar",
        ]

        if has_ols:
            columns += [
                "ols_aar",
                "ols_aar_standard_deviation",
                "ols_aar_standard_error",
                "ols_caar",
            ]

        if detail.empty:
            return pd.DataFrame(columns=columns)

        aggregation = {
            "company_count": ("abnormal_return", "count"),
            "aar": ("abnormal_return", "mean"),
            "aar_standard_deviation": ("abnormal_return", "std"),
        }

        if has_ols:
            aggregation.update(
                {
                    "ols_aar": (_OLS_ABNORMAL_RETURN_COLUMN, "mean"),
                    "ols_aar_standard_deviation": (
                        _OLS_ABNORMAL_RETURN_COLUMN,
                        "std",
                    ),
                }
            )

        grouped = (
            detail.groupby(
                [*group_columns, "relative_trading_day"],
                sort=True,
            )
            .agg(**aggregation)
            .reset_index()
        )
        grouped["aar_standard_error"] = grouped.apply(
            lambda row: (
                row["aar_standard_deviation"]
                / math.sqrt(row["company_count"])
                if row["company_count"] > 1
                else float("nan")
            ),
            axis=1,
        )
        grouped["caar"] = grouped.groupby(group_columns, sort=False)[
            "aar"
        ].cumsum()

        if has_ols:
            grouped["ols_aar_standard_error"] = grouped.apply(
                lambda row: (
                    row["ols_aar_standard_deviation"]
                    / math.sqrt(row["company_count"])
                    if row["company_count"] > 1
                    else float("nan")
                ),
                axis=1,
            )
            grouped["ols_caar"] = grouped.groupby(
                group_columns, sort=False
            )["ols_aar"].cumsum()

        return grouped[columns]

    @staticmethod
    def _car(window, start_day, end_day, column="abnormal_return"):
        selected = window[
            window["relative_trading_day"].between(start_day, end_day)
        ]

        if selected.empty or end_day > window["relative_trading_day"].max():
            return float("nan")

        return float(selected[column].sum())

    @staticmethod
    def _events(events):
        try:
            event_items = tuple(events)
        except TypeError as error:
            raise TypeError("events must be an iterable") from error

        if not event_items:
            raise ValueError("events must not be empty")

        if not all(isinstance(event, MarketEvent) for event in event_items):
            raise TypeError("events must contain only MarketEvent objects")

        identifiers = [event.event_id for event in event_items]

        if len(identifiers) != len(set(identifiers)):
            raise ValueError("events must not contain duplicate event_id")

        return tuple(
            sorted(
                event_items,
                key=lambda item: (item.event_date, item.event_id),
            )
        )

    @staticmethod
    def _non_negative_int(value, field_name):
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"{field_name} must be an integer")

        if value < 0:
            raise ValueError(f"{field_name} must not be negative")

        return value

    @staticmethod
    def _market_data(market_file):
        path = Path(market_file)

        if not path.is_file():
            raise FileNotFoundError(f"Market panel not found: {path}")

        market = pd.read_csv(path)
        missing = _REQUIRED_MARKET_COLUMNS - set(market.columns)

        if missing:
            raise ValueError(
                "Market panel is missing required columns: "
                + ", ".join(sorted(missing))
            )

        market = market.copy()
        market["Date"] = pd.to_datetime(market["Date"], errors="coerce")

        if market["Date"].isna().any():
            raise ValueError("Market panel contains invalid Date values")

        for column in ("company_return", "benchmark_return", "abnormal_return"):
            market[column] = pd.to_numeric(market[column], errors="coerce")

        if _OLS_ABNORMAL_RETURN_COLUMN in market.columns:
            # NaN is expected and valid here (companies whose OLS
            # estimation window had too few observations), unlike the
            # required return columns below, so it is coerced but not
            # validated against NaN.
            market[_OLS_ABNORMAL_RETURN_COLUMN] = pd.to_numeric(
                market[_OLS_ABNORMAL_RETURN_COLUMN], errors="coerce"
            )

        for column in (
            "ols_estimation_window_observations",
            "ols_alpha",
            "ols_beta",
            "ols_r_squared",
        ):
            if column in market.columns:
                market[column] = pd.to_numeric(
                    market[column], errors="coerce"
                )

        return_columns = [
            "company_return",
            "benchmark_return",
            "abnormal_return",
        ]

        if market[return_columns].isna().any().any():
            raise ValueError("Market panel contains invalid return values")

        market["is_confirmatory"] = market["is_confirmatory"].map(
            _boolean_value
        )

        if market.duplicated(["company_id", "Date"]).any():
            raise ValueError("Market panel contains duplicate company-date rows")

        return market.sort_values(["company_id", "Date"]).reset_index(drop=True)

    @staticmethod
    def _company_data(company_id, company):
        columns_to_check = list(_METADATA_COLUMNS)
        columns_to_check.extend(
            column
            for column in _OLS_DIAGNOSTIC_COLUMNS
            if column in company.columns
        )

        for column in columns_to_check:
            if company[column].nunique(dropna=False) != 1:
                raise ValueError(
                    f"Company {company_id} has inconsistent {column} metadata"
                )

        return company.sort_values("Date").reset_index(drop=True)


def _boolean_value(value):
    if isinstance(value, bool):
        return value

    normalized = str(value).strip().casefold()

    if normalized in {"true", "1", "yes"}:
        return True

    if normalized in {"false", "0", "no"}:
        return False

    raise ValueError(f"Invalid is_confirmatory value: {value}")


def _sample_group(analysis_tier, is_confirmatory):
    if analysis_tier == "POST_HOC_EXPLORATORY_ROBUSTNESS_CASE":
        return "POST_HOC_EXPLORATORY"

    if is_confirmatory:
        return "CONFIRMATORY"

    return "EXPLORATORY"
