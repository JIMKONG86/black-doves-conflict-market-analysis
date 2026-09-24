import math

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd

from src.models.procurement_event import ProcurementEvent
from src.services.ols_market_model import (
    MARKET_MODEL_ABNORMAL_RETURN_COLUMN,
    fit_ols_market_model,
)


_MARKET_COLUMNS = {
    "Date",
    "company_return",
    "benchmark_return",
    "abnormal_return",
}


@dataclass(frozen=True)
class ProcurementEventStudySummary:
    event_count: int
    detail_rows: int
    first_event_date: date
    last_event_date: date
    first_market_date: date
    last_market_date: date
    pre_days: int
    post_days: int
    company_ticker: str


class ProcurementEventStudy:
    def analyze(
        self,
        events,
        market_file,
        pre_days=5,
        post_days=10,
    ):
        event_items = self._events(events)
        pre_days = self._non_negative_int(pre_days, "pre_days")
        post_days = self._non_negative_int(post_days, "post_days")
        market = self._market_data(market_file)
        detail_rows = []
        summary_rows = []

        for event in event_items:
            event_detail, event_summary = self._analyze_event(
                event=event,
                market=market,
                pre_days=pre_days,
                post_days=post_days,
            )
            detail_rows.extend(event_detail)
            summary_rows.append(event_summary)

        detail = pd.DataFrame(detail_rows)
        summaries = pd.DataFrame(summary_rows)
        study_summary = ProcurementEventStudySummary(
            event_count=len(event_items),
            detail_rows=len(detail),
            first_event_date=min(
                event.announcement_date for event in event_items
            ),
            last_event_date=max(
                event.announcement_date for event in event_items
            ),
            first_market_date=market["Date"].min().date(),
            last_market_date=market["Date"].max().date(),
            pre_days=pre_days,
            post_days=post_days,
            company_ticker=event_items[0].company_ticker,
        )

        return detail, summaries, study_summary

    @staticmethod
    def export_csv(data, output_file):
        if not isinstance(data, pd.DataFrame):
            raise TypeError("data must be a pandas DataFrame")

        output_path = Path(output_file)

        if output_path.suffix.casefold() != ".csv":
            raise ValueError("Event-study output file must use .csv")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = output_path.with_suffix(".csv.tmp")
        export = data.copy()

        for column_name in (
            "announcement_date",
            "effective_market_date",
            "market_date",
        ):
            if column_name in export.columns:
                export[column_name] = pd.to_datetime(
                    export[column_name]
                ).dt.strftime("%Y-%m-%d")

        export.to_csv(temporary_path, index=False)
        temporary_path.replace(output_path)

        return output_path

    @classmethod
    def _analyze_event(cls, event, market, pre_days, post_days):
        event_timestamp = pd.Timestamp(event.announcement_date)
        positions = market.index[market["Date"] >= event_timestamp]

        if positions.empty:
            raise ValueError(
                "No market observation on or after procurement event "
                f"{event.announcement_date.isoformat()}"
            )

        event_position = int(positions[0])
        start_position = event_position - pre_days
        end_position = event_position + post_days

        if start_position < 0 or end_position >= len(market):
            raise ValueError(
                "Market data does not cover the complete event window "
                f"for {event.announcement_date.isoformat()}"
            )

        window = market.iloc[start_position : end_position + 1].copy()
        window["relative_trading_day"] = range(-pre_days, post_days + 1)
        window["event_window_car"] = window["abnormal_return"].cumsum()

        # Each procurement event has its own announcement date (they span
        # January 2025 through mid-2026 for the same company), so unlike
        # the single-event market-universe study, the OLS market model is
        # fitted separately per event, on trading days strictly before
        # *this* event's own announcement date. Using one shared fit
        # anchored to the conflict's primary event date would either look
        # ahead (for events before it) or ignore closer, more relevant
        # history (for events after it).
        estimation = market[market["Date"] < event_timestamp]
        fit = fit_ols_market_model(
            estimation["company_return"], estimation["benchmark_return"]
        )
        has_ols = fit.status == "ok"

        if has_ols:
            window["market_model_expected_return"] = (
                fit.alpha + fit.beta * window["benchmark_return"]
            )
            window[MARKET_MODEL_ABNORMAL_RETURN_COLUMN] = (
                window["company_return"]
                - window["market_model_expected_return"]
            )
            window["ols_event_window_car"] = window[
                MARKET_MODEL_ABNORMAL_RETURN_COLUMN
            ].cumsum()

        effective_market_date = market.loc[event_position, "Date"]
        event_fields = cls._event_fields(event, effective_market_date)
        detail_rows = []

        for row in window.to_dict(orient="records"):
            detail_row = {
                **event_fields,
                "market_date": row["Date"],
                "relative_trading_day": row[
                    "relative_trading_day"
                ],
                "company_return": row["company_return"],
                "benchmark_return": row["benchmark_return"],
                "abnormal_return": row["abnormal_return"],
                "event_window_car": row["event_window_car"],
            }

            if has_ols:
                detail_row[MARKET_MODEL_ABNORMAL_RETURN_COLUMN] = row[
                    MARKET_MODEL_ABNORMAL_RETURN_COLUMN
                ]
                detail_row["ols_event_window_car"] = row[
                    "ols_event_window_car"
                ]

            detail_rows.append(detail_row)

        summary_row = {
            **event_fields,
            "pre_days": pre_days,
            "post_days": post_days,
            "pre_event_car": cls._car(window, -pre_days, -1),
            "event_day_abnormal_return": cls._car(window, 0, 0),
            "post_event_car_0_1": cls._car(window, 0, 1),
            "post_event_car_0_5": cls._car(window, 0, 5),
            "post_event_car_0_10": cls._car(window, 0, 10),
            "full_window_car": float(window["abnormal_return"].sum()),
            "ols_status": fit.status,
            "ols_estimation_window_observations": (
                fit.estimation_observations
            ),
        }

        if has_ols:
            summary_row.update(
                {
                    "ols_alpha": fit.alpha,
                    "ols_beta": fit.beta,
                    "ols_r_squared": fit.r_squared,
                    "ols_pre_event_car": cls._car(
                        window,
                        -pre_days,
                        -1,
                        column=MARKET_MODEL_ABNORMAL_RETURN_COLUMN,
                    ),
                    "ols_event_day_abnormal_return": cls._car(
                        window, 0, 0, column=MARKET_MODEL_ABNORMAL_RETURN_COLUMN
                    ),
                    "ols_post_event_car_0_1": cls._car(
                        window, 0, 1, column=MARKET_MODEL_ABNORMAL_RETURN_COLUMN
                    ),
                    "ols_post_event_car_0_5": cls._car(
                        window, 0, 5, column=MARKET_MODEL_ABNORMAL_RETURN_COLUMN
                    ),
                    "ols_post_event_car_0_10": cls._car(
                        window,
                        0,
                        10,
                        column=MARKET_MODEL_ABNORMAL_RETURN_COLUMN,
                    ),
                    "ols_full_window_car": float(
                        window[MARKET_MODEL_ABNORMAL_RETURN_COLUMN].sum()
                    ),
                }
            )

        return detail_rows, summary_row

    @staticmethod
    def _event_fields(event, effective_market_date):
        return {
            "event_id": event.event_id,
            "announcement_date": pd.Timestamp(event.announcement_date),
            "effective_market_date": effective_market_date,
            "company_name": event.company_name,
            "company_ticker": event.company_ticker,
            "buyer_name": event.buyer_name,
            "buyer_country_code": event.buyer_country_code,
            "event_type": event.event_type.value,
            "verification_status": event.verification_status.value,
            "is_air_defence": event.is_air_defence,
            "related_initiative": event.related_initiative,
            "title": event.title,
            "systems": " | ".join(event.systems),
            "contract_value_eur": event.contract_value_eur,
            "aggregate_package_value_eur": (
                event.aggregate_package_value_eur
            ),
            "value_description": event.value_description,
            "source_name": event.source_name,
            "source_url": event.source_url,
        }

    @staticmethod
    def _car(window, start_day, end_day, column="abnormal_return"):
        selected = window[
            window["relative_trading_day"].between(
                start_day,
                end_day,
            )
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

        if not all(
            isinstance(event, ProcurementEvent) for event in event_items
        ):
            raise TypeError(
                "events must contain only ProcurementEvent objects"
            )

        identifiers = [event.event_id for event in event_items]

        if len(identifiers) != len(set(identifiers)):
            raise ValueError("events must not contain duplicates")

        tickers = {event.company_ticker for event in event_items}

        if len(tickers) != 1:
            raise ValueError("events must use one company_ticker")

        return tuple(
            sorted(event_items, key=lambda item: item.announcement_date)
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
        market_path = Path(market_file)

        if not market_path.is_file():
            raise FileNotFoundError(
                f"Market comparison CSV not found: {market_path}"
            )

        market = pd.read_csv(market_path)
        missing_columns = _MARKET_COLUMNS - set(market.columns)

        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise ValueError(
                "Market comparison CSV is missing required columns: "
                f"{missing}"
            )

        if market.empty:
            raise ValueError("Market comparison CSV must not be empty")

        result = market.copy()
        result["Date"] = pd.to_datetime(result["Date"], errors="coerce")

        if result["Date"].isna().any():
            raise ValueError("Date must contain only valid dates")

        if result["Date"].duplicated().any():
            raise ValueError("Date must not contain duplicates")

        for column_name in (
            "company_return",
            "benchmark_return",
            "abnormal_return",
        ):
            result[column_name] = pd.to_numeric(
                result[column_name],
                errors="coerce",
            )

            if result[column_name].isna().any():
                raise ValueError(
                    f"{column_name} must contain only numeric values"
                )

            if not result[column_name].map(math.isfinite).all():
                raise ValueError(
                    f"{column_name} must contain only finite values"
                )

        result = result.sort_values("Date").reset_index(drop=True)

        return result
