from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd
from scipy.stats import pearsonr, spearmanr


_BASE_COLUMNS = {
    "fuel_observation_date",
    "brent_week_start",
    "brent_week_end",
    "brent_weekly_pct_change",
}

_FUEL_SERIES = {
    ("PETROL", "WITH_TAX"): "petrol_with_tax_eur_per_liter_pct_change",
    ("PETROL", "WITHOUT_TAX"): (
        "petrol_without_tax_eur_per_liter_pct_change"
    ),
    ("DIESEL", "WITH_TAX"): "diesel_with_tax_eur_per_liter_pct_change",
    ("DIESEL", "WITHOUT_TAX"): (
        "diesel_without_tax_eur_per_liter_pct_change"
    ),
}

_DEFAULT_LAGS = tuple(range(9))


@dataclass(frozen=True)
class FuelPriceLagSummary:
    first_fuel_date: date
    last_fuel_date: date
    weekly_observations: int
    result_rows: int
    lags: tuple[int, ...]


class FuelPriceLagAnalyzer:
    """Estimate descriptive lead-lag associations in weekly price changes."""

    def analyze(self, weekly_file, lags=None):
        selected_lags = self._lags(lags)
        data = self._load(weekly_file)
        self._validate_consecutive_weeks(data)
        rows = []

        for (product, tax_basis), response_column in _FUEL_SERIES.items():
            for lag in selected_lags:
                rows.append(
                    self._association_row(
                        data=data,
                        product=product,
                        tax_basis=tax_basis,
                        response_column=response_column,
                        lag=lag,
                    )
                )

        results = pd.DataFrame(rows)
        results["is_strongest_for_series"] = False

        for _, group in results[results["status"] == "ok"].groupby(
            ["product", "tax_basis"]
        ):
            strongest = group["spearman_correlation"].abs().idxmax()
            results.loc[strongest, "is_strongest_for_series"] = True

        summary = FuelPriceLagSummary(
            first_fuel_date=data["fuel_observation_date"].min().date(),
            last_fuel_date=data["fuel_observation_date"].max().date(),
            weekly_observations=len(data),
            result_rows=len(results),
            lags=selected_lags,
        )
        return results, summary

    @staticmethod
    def export_csv(data, output_file):
        if not isinstance(data, pd.DataFrame):
            raise TypeError("data must be a pandas DataFrame")
        output_path = Path(output_file)

        if output_path.suffix.casefold() != ".csv":
            raise ValueError("Fuel-price lag output must use .csv")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        export = data.copy()

        for column_name in (
            "first_brent_week",
            "last_brent_week",
            "first_fuel_date",
            "last_fuel_date",
        ):
            export[column_name] = export[column_name].dt.strftime("%Y-%m-%d")

        temporary_path = output_path.with_suffix(".csv.tmp")
        export.to_csv(temporary_path, index=False)
        temporary_path.replace(output_path)
        return output_path

    @staticmethod
    def _load(weekly_file):
        input_path = Path(weekly_file)
        if not input_path.is_file():
            raise FileNotFoundError(
                f"Energy weekly panel not found: {input_path}"
            )

        data = pd.read_csv(input_path)
        required = _BASE_COLUMNS | set(_FUEL_SERIES.values())
        missing = required - set(data.columns)
        if missing:
            names = ", ".join(sorted(missing))
            raise ValueError(
                f"Energy weekly panel is missing required columns: {names}"
            )
        if data.empty:
            raise ValueError("Energy weekly panel must not be empty")

        result = data.copy()
        for column_name in (
            "fuel_observation_date",
            "brent_week_start",
            "brent_week_end",
        ):
            result[column_name] = pd.to_datetime(
                result[column_name], errors="coerce"
            )
            if result[column_name].isna().any():
                raise ValueError(f"{column_name} must contain valid dates")

        for column_name in (
            "brent_weekly_pct_change",
            *_FUEL_SERIES.values(),
        ):
            result[column_name] = pd.to_numeric(
                result[column_name], errors="coerce"
            )

        if result["fuel_observation_date"].duplicated().any():
            raise ValueError("Energy weekly panel contains duplicate fuel dates")

        return result.sort_values("fuel_observation_date").reset_index(
            drop=True
        )

    @staticmethod
    def _validate_consecutive_weeks(data):
        differences = data["fuel_observation_date"].diff().dropna().dt.days
        if not differences.eq(7).all():
            raise ValueError(
                "Fuel-price lag analysis requires consecutive weekly observations"
            )

    @staticmethod
    def _association_row(
        data,
        product,
        tax_basis,
        response_column,
        lag,
    ):
        paired = pd.DataFrame(
            {
                "brent_week": data["brent_week_start"],
                "fuel_date": data["fuel_observation_date"].shift(-lag),
                "brent_change": data["brent_weekly_pct_change"],
                "fuel_change": data[response_column].shift(-lag),
            }
        ).dropna()
        observations = len(paired)
        status = "ok"
        pearson_value = float("nan")
        pearson_p = float("nan")
        spearman_value = float("nan")
        spearman_p = float("nan")

        if observations < 4:
            status = "insufficient_observations"
        elif paired["brent_change"].nunique() < 2:
            status = "constant_brent_change"
        elif paired["fuel_change"].nunique() < 2:
            status = "constant_fuel_change"
        else:
            pearson_result = pearsonr(
                paired["brent_change"], paired["fuel_change"]
            )
            spearman_result = spearmanr(
                paired["brent_change"], paired["fuel_change"]
            )
            pearson_value = float(pearson_result.statistic)
            pearson_p = float(pearson_result.pvalue)
            spearman_value = float(spearman_result.statistic)
            spearman_p = float(spearman_result.pvalue)

        return {
            "product": product,
            "tax_basis": tax_basis,
            "lag_weeks": lag,
            "lag_definition": (
                "Brent mean in week t versus German Monday fuel-price "
                f"change {lag} week(s) after the immediately following Monday"
            ),
            "observations": observations,
            "pearson_correlation": pearson_value,
            "pearson_p_value": pearson_p,
            "spearman_correlation": spearman_value,
            "spearman_p_value": spearman_p,
            "first_brent_week": paired["brent_week"].min(),
            "last_brent_week": paired["brent_week"].max(),
            "first_fuel_date": paired["fuel_date"].min(),
            "last_fuel_date": paired["fuel_date"].max(),
            "status": status,
        }

    @staticmethod
    def _lags(lags):
        values = _DEFAULT_LAGS if lags is None else tuple(lags)
        if not values:
            raise ValueError("At least one lag must be selected")
        if any(not isinstance(value, int) for value in values):
            raise TypeError("lags must contain integers")
        if any(value < 0 for value in values):
            raise ValueError("lags must not contain negative values")
        if len(set(values)) != len(values):
            raise ValueError("lags must not contain duplicates")
        return tuple(sorted(values))
