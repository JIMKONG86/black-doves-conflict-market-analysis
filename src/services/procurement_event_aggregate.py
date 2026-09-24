import math

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


_REQUIRED_COLUMNS = {
    "event_id",
    "announcement_date",
    "effective_market_date",
    "buyer_name",
    "title",
    "systems",
    "relative_trading_day",
    "abnormal_return",
}

# Optional column produced by src.services.ols_market_model via
# ProcurementEventStudy. When present, this analyzer additionally reports
# OLS market-model-based event CAR/AAR/CAAR alongside the naive
# market-adjusted ones, without requiring it or breaking inputs that
# don't have it.
_OLS_ABNORMAL_RETURN_COLUMN = "market_model_abnormal_return"


@dataclass(frozen=True)
class ProcurementEventAggregateSummary:
    event_count: int
    event_time_rows: int
    first_relative_day: int
    last_relative_day: int


class ProcurementEventAggregateAnalyzer:
    def analyze(self, input_file):
        detail = self.load(input_file)
        has_ols = _OLS_ABNORMAL_RETURN_COLUMN in detail.columns
        detail["event_car"] = detail.groupby(
            "event_id",
            sort=False,
        )["abnormal_return"].cumsum()

        if has_ols:
            detail["ols_event_car"] = detail.groupby(
                "event_id",
                sort=False,
            )[_OLS_ABNORMAL_RETURN_COLUMN].cumsum()

        grouped = detail.groupby(
            "relative_trading_day",
            sort=True,
        )
        aggregation = {
            "event_count": ("event_id", "nunique"),
            "average_abnormal_return": ("abnormal_return", "mean"),
            "median_abnormal_return": ("abnormal_return", "median"),
            "abnormal_return_std": ("abnormal_return", "std"),
            "cumulative_average_abnormal_return": ("event_car", "mean"),
            "event_car_std": ("event_car", "std"),
        }

        if has_ols:
            aggregation.update(
                {
                    "average_ols_abnormal_return": (
                        _OLS_ABNORMAL_RETURN_COLUMN,
                        "mean",
                    ),
                    "ols_abnormal_return_std": (
                        _OLS_ABNORMAL_RETURN_COLUMN,
                        "std",
                    ),
                    "cumulative_average_ols_abnormal_return": (
                        "ols_event_car",
                        "mean",
                    ),
                    "ols_event_car_std": ("ols_event_car", "std"),
                }
            )

        aggregate = grouped.agg(**aggregation).reset_index()
        positive_share = grouped["abnormal_return"].apply(
            lambda values: float((values > 0).mean())
        )
        aggregate["positive_abnormal_share"] = (
            aggregate["relative_trading_day"].map(positive_share)
        )
        square_root_count = aggregate["event_count"].map(math.sqrt)
        aggregate["aar_standard_error"] = (
            aggregate["abnormal_return_std"] / square_root_count
        )
        aggregate["caar_standard_error"] = (
            aggregate["event_car_std"] / square_root_count
        )
        columns = [
            "relative_trading_day",
            "event_count",
            "average_abnormal_return",
            "median_abnormal_return",
            "positive_abnormal_share",
            "abnormal_return_std",
            "aar_standard_error",
            "cumulative_average_abnormal_return",
            "event_car_std",
            "caar_standard_error",
        ]

        if has_ols:
            aggregate["ols_aar_standard_error"] = (
                aggregate["ols_abnormal_return_std"] / square_root_count
            )
            aggregate["ols_caar_standard_error"] = (
                aggregate["ols_event_car_std"] / square_root_count
            )
            columns += [
                "average_ols_abnormal_return",
                "ols_abnormal_return_std",
                "ols_aar_standard_error",
                "cumulative_average_ols_abnormal_return",
                "ols_event_car_std",
                "ols_caar_standard_error",
            ]

        aggregate = aggregate[columns]
        summary = ProcurementEventAggregateSummary(
            event_count=detail["event_id"].nunique(),
            event_time_rows=len(aggregate),
            first_relative_day=int(
                aggregate["relative_trading_day"].min()
            ),
            last_relative_day=int(
                aggregate["relative_trading_day"].max()
            ),
        )

        return detail, aggregate, summary

    @staticmethod
    def export_csv(data, output_file):
        if not isinstance(data, pd.DataFrame):
            raise TypeError("data must be a pandas DataFrame")

        output_path = Path(output_file)

        if output_path.suffix.casefold() != ".csv":
            raise ValueError("Aggregate output file must use .csv")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = output_path.with_suffix(".csv.tmp")
        data.to_csv(temporary_path, index=False)
        temporary_path.replace(output_path)

        return output_path

    @classmethod
    def load(cls, input_file):
        input_path = Path(input_file)

        if not input_path.is_file():
            raise FileNotFoundError(
                f"Procurement event-window CSV not found: {input_path}"
            )

        data = pd.read_csv(input_path)
        missing_columns = _REQUIRED_COLUMNS - set(data.columns)

        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise ValueError(
                "Procurement event-window CSV is missing required "
                f"columns: {missing}"
            )

        if data.empty:
            raise ValueError(
                "Procurement event-window CSV must not be empty"
            )

        result = data.copy()

        for column_name in (
            "announcement_date",
            "effective_market_date",
        ):
            result[column_name] = pd.to_datetime(
                result[column_name],
                errors="coerce",
            )

            if result[column_name].isna().any():
                raise ValueError(
                    f"{column_name} must contain only valid dates"
                )

        relative_days = pd.to_numeric(
            result["relative_trading_day"],
            errors="coerce",
        )

        if relative_days.isna().any() or not (
            relative_days == relative_days.astype(int)
        ).all():
            raise ValueError(
                "relative_trading_day must contain only integers"
            )

        result["relative_trading_day"] = relative_days.astype(int)
        result["abnormal_return"] = pd.to_numeric(
            result["abnormal_return"],
            errors="coerce",
        )

        if result["abnormal_return"].isna().any():
            raise ValueError(
                "abnormal_return must contain only numeric values"
            )

        if not result["abnormal_return"].map(math.isfinite).all():
            raise ValueError(
                "abnormal_return must contain only finite values"
            )

        if _OLS_ABNORMAL_RETURN_COLUMN in result.columns:
            # NaN is valid here (events whose OLS estimation window had
            # too few pre-event observations), unlike abnormal_return
            # above, so this is coerced but not validated against NaN.
            result[_OLS_ABNORMAL_RETURN_COLUMN] = pd.to_numeric(
                result[_OLS_ABNORMAL_RETURN_COLUMN], errors="coerce"
            )

        for column_name in (
            "event_id",
            "buyer_name",
            "title",
            "systems",
        ):
            result[column_name] = (
                result[column_name].astype(str).str.strip()
            )

            if (result[column_name] == "").any():
                raise ValueError(
                    f"{column_name} must not contain empty values"
                )

        if result.duplicated(
            subset=["event_id", "relative_trading_day"]
        ).any():
            raise ValueError(
                "Procurement event-window CSV contains duplicate "
                "event-day rows"
            )

        cls._validate_balanced_window(result)
        cls._validate_event_metadata(result)

        return result.sort_values(
            [
                "announcement_date",
                "event_id",
                "relative_trading_day",
            ]
        ).reset_index(drop=True)

    @staticmethod
    def _validate_balanced_window(data):
        expected_days = None

        for event_id, event_data in data.groupby("event_id"):
            days = tuple(sorted(event_data["relative_trading_day"]))

            if 0 not in days:
                raise ValueError(
                    f"Event {event_id} has no event day zero"
                )

            consecutive = tuple(range(days[0], days[-1] + 1))

            if days != consecutive:
                raise ValueError(
                    f"Event {event_id} has an incomplete event window"
                )

            if expected_days is None:
                expected_days = days
            elif days != expected_days:
                raise ValueError(
                    "All procurement events must use the same "
                    "complete event window"
                )

    @staticmethod
    def _validate_event_metadata(data):
        columns = (
            "announcement_date",
            "effective_market_date",
            "buyer_name",
            "title",
            "systems",
        )

        for column_name in columns:
            counts = data.groupby("event_id")[column_name].nunique(
                dropna=False
            )

            if (counts != 1).any():
                raise ValueError(
                    f"{column_name} must be constant within each event"
                )
