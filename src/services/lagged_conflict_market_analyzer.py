from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd


_BASE_REQUIRED_COLUMNS = {
    "source_snapshot_date",
    "week_end_date",
    "country_name",
    "country_code",
    "company_ticker",
    "benchmark_ticker",
}

_DEFAULT_METRICS = (
    "strike_events",
    "strike_fatalities",
)

_DEFAULT_LAGS = (0, 1, 2, 4)


@dataclass(frozen=True)
class LaggedAnalysisSummary:
    input_rows: int
    week_count: int
    scope_count: int
    result_rows: int
    first_week: date
    last_week: date
    metrics: tuple[str, ...]
    lags: tuple[int, ...]
    company_ticker: str
    benchmark_ticker: str


class LaggedConflictMarketAnalyzer:
    def analyze(
        self,
        input_file,
        metrics=None,
        lags=None,
        response_metric="weekly_abnormal_return",
    ):
        metrics = self._metrics(metrics)
        lags = self._lags(lags)
        response_metric = self._required_text(
            response_metric,
            "response_metric",
        )
        data = self._load_data(
            input_file=input_file,
            metrics=metrics,
            response_metric=response_metric,
        )
        company_ticker = self._one_value(
            data,
            "company_ticker",
        )
        benchmark_ticker = self._one_value(
            data,
            "benchmark_ticker",
        )
        self._one_value(data, "source_snapshot_date")
        self._validate_market_response(
            data,
            response_metric,
        )

        scopes = self._scope_frames(
            data=data,
            metrics=metrics,
            response_metric=response_metric,
        )
        result_rows = []

        for scope_type, scope_name, scope_data in scopes:
            self._validate_consecutive_weeks(
                scope_data,
                scope_name,
            )

            for metric in metrics:
                for lag in lags:
                    result_rows.append(
                        self._association_row(
                            scope_type=scope_type,
                            scope_name=scope_name,
                            data=scope_data,
                            conflict_metric=metric,
                            response_metric=response_metric,
                            lag=lag,
                        )
                    )

        results = pd.DataFrame(result_rows)
        summary = LaggedAnalysisSummary(
            input_rows=len(data),
            week_count=data["week_end_date"].nunique(),
            scope_count=len(scopes),
            result_rows=len(results),
            first_week=data["week_end_date"].min().date(),
            last_week=data["week_end_date"].max().date(),
            metrics=metrics,
            lags=lags,
            company_ticker=company_ticker,
            benchmark_ticker=benchmark_ticker,
        )

        return results, summary

    @staticmethod
    def export_csv(data, output_file):
        if not isinstance(data, pd.DataFrame):
            raise TypeError(
                "data must be a pandas DataFrame"
            )

        output_path = Path(output_file)

        if output_path.suffix.casefold() != ".csv":
            raise ValueError(
                "Lag analysis output file must use .csv"
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
            "first_conflict_week",
            "last_conflict_week",
            "first_response_week",
            "last_response_week",
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

    @classmethod
    def _load_data(
        cls,
        input_file,
        metrics,
        response_metric,
    ):
        input_path = Path(input_file)

        if not input_path.is_file():
            raise FileNotFoundError(
                "BLACK DOVES analysis CSV not found: "
                f"{input_path}"
            )

        data = pd.read_csv(input_path)
        required_columns = (
            _BASE_REQUIRED_COLUMNS
            | set(metrics)
            | {response_metric}
        )
        missing_columns = required_columns - set(
            data.columns
        )

        if missing_columns:
            missing = ", ".join(
                sorted(missing_columns)
            )
            raise ValueError(
                "BLACK DOVES analysis CSV is missing "
                f"required columns: {missing}"
            )

        if data.empty:
            raise ValueError(
                "BLACK DOVES analysis CSV must not be empty"
            )

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

        for column_name in (*metrics, response_metric):
            result[column_name] = pd.to_numeric(
                result[column_name],
                errors="coerce",
            )

            if result[column_name].isna().any():
                raise ValueError(
                    f"{column_name} must contain only "
                    "numeric values"
                )

        for metric in metrics:
            if (result[metric] < 0).any():
                raise ValueError(
                    f"{metric} must not contain "
                    "negative values"
                )

        for column_name in (
            "country_name",
            "country_code",
            "company_ticker",
            "benchmark_ticker",
        ):
            result[column_name] = (
                result[column_name]
                .astype(str)
                .str.strip()
            )

            if (result[column_name] == "").any():
                raise ValueError(
                    f"{column_name} must not contain "
                    "empty values"
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
                "Analysis data contains duplicate "
                "snapshot-country-week rows"
            )

        return result.sort_values(
            ["week_end_date", "country_code"]
        ).reset_index(drop=True)

    @staticmethod
    def _validate_market_response(data, response_metric):
        values_per_week = data.groupby(
            "week_end_date"
        )[response_metric].nunique(dropna=False)

        if (values_per_week != 1).any():
            raise ValueError(
                f"{response_metric} must have exactly "
                "one value per market week"
            )

    @staticmethod
    def _scope_frames(
        data,
        metrics,
        response_metric,
    ):
        countries = sorted(
            data["country_name"].unique()
        )
        aggregations = {
            metric: "sum"
            for metric in metrics
        }
        aggregations[response_metric] = "first"
        combined = (
            data.groupby(
                "week_end_date",
                as_index=False,
                sort=True,
            )
            .agg(aggregations)
        )
        scopes = [
            (
                "combined",
                " + ".join(countries),
                combined,
            )
        ]

        for country_name in countries:
            country_data = (
                data[
                    data["country_name"] == country_name
                ][
                    [
                        "week_end_date",
                        *metrics,
                        response_metric,
                    ]
                ]
                .sort_values("week_end_date")
                .reset_index(drop=True)
            )
            scopes.append(
                (
                    "country",
                    country_name,
                    country_data,
                )
            )

        return tuple(scopes)

    @staticmethod
    def _validate_consecutive_weeks(data, scope_name):
        week_differences = (
            data["week_end_date"]
            .sort_values()
            .diff()
            .dropna()
            .dt.days
        )

        if not week_differences.eq(7).all():
            raise ValueError(
                "Lag analysis requires consecutive "
                f"weekly observations for {scope_name}"
            )

    @staticmethod
    def _association_row(
        scope_type,
        scope_name,
        data,
        conflict_metric,
        response_metric,
        lag,
    ):
        paired = data[
            [
                "week_end_date",
                conflict_metric,
                response_metric,
            ]
        ].copy()
        paired["response_week"] = paired[
            "week_end_date"
        ].shift(-lag)
        paired["future_response"] = paired[
            response_metric
        ].shift(-lag)
        paired = paired.dropna(
            subset=["response_week", "future_response"]
        )
        observations = len(paired)
        conflict_values = paired[conflict_metric]
        response_values = paired["future_response"]
        status = "ok"
        pearson = None
        spearman = None

        if observations < 3:
            status = "insufficient_observations"
        elif conflict_values.nunique() < 2:
            status = "constant_conflict_metric"
        elif response_values.nunique() < 2:
            status = "constant_market_response"
        else:
            pearson = float(
                conflict_values.corr(response_values)
            )
            spearman = float(
                conflict_values.rank(
                    method="average"
                ).corr(
                    response_values.rank(
                        method="average"
                    )
                )
            )

        return {
            "scope_type": scope_type,
            "scope_name": scope_name,
            "conflict_metric": conflict_metric,
            "lag_weeks": lag,
            "market_response": response_metric,
            "observations": observations,
            "pearson_correlation": pearson,
            "spearman_correlation": spearman,
            "status": status,
            "first_conflict_week": (
                paired["week_end_date"].min()
                if observations
                else pd.NaT
            ),
            "last_conflict_week": (
                paired["week_end_date"].max()
                if observations
                else pd.NaT
            ),
            "first_response_week": (
                paired["response_week"].min()
                if observations
                else pd.NaT
            ),
            "last_response_week": (
                paired["response_week"].max()
                if observations
                else pd.NaT
            ),
        }

    @classmethod
    def _metrics(cls, values):
        if values is None:
            return _DEFAULT_METRICS

        if isinstance(values, str):
            values = (values,)

        try:
            candidate_values = tuple(values)
        except TypeError as error:
            raise TypeError(
                "metrics must be an iterable of strings"
            ) from error

        if not candidate_values:
            raise ValueError(
                "metrics must contain at least one value"
            )

        metrics = []

        for value in candidate_values:
            metric = cls._required_text(
                value,
                "metric",
            )

            if metric not in metrics:
                metrics.append(metric)

        return tuple(metrics)

    @staticmethod
    def _lags(values):
        if values is None:
            return _DEFAULT_LAGS

        if isinstance(values, int) and not isinstance(
            values,
            bool,
        ):
            values = (values,)

        try:
            candidate_values = tuple(values)
        except TypeError as error:
            raise TypeError(
                "lags must be an iterable of integers"
            ) from error

        if not candidate_values:
            raise ValueError(
                "lags must contain at least one value"
            )

        lags = []

        for value in candidate_values:
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
            ):
                raise TypeError(
                    "lags must contain only integers"
                )

            if value < 0:
                raise ValueError(
                    "lags must not contain negative values"
                )

            if value not in lags:
                lags.append(value)

        return tuple(sorted(lags))

    @staticmethod
    def _one_value(data, column_name):
        values = {
            str(value).strip()
            for value in data[column_name]
            if str(value).strip()
        }

        if len(values) != 1:
            raise ValueError(
                f"{column_name} must contain exactly "
                "one value"
            )

        return next(iter(values))

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
