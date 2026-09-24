"""Robustness helpers for the written-assignment analysis.

The functions in this module deliberately avoid causal language.  Bootstrap
intervals describe cross-company uncertainty in the selected sample, while
Holm adjustment controls the family-wise error rate across the nine tested
lags within each fuel-price series.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


EVENT_STUDY_METRICS = {
    "event_day_abnormal_return": "Event-day abnormal return",
    "post_event_car_0_10": "CAR [0,+10] (market-adjusted)",
    "ols_post_event_car_0_10": "CAR [0,+10] (OLS market model)",
}


def holm_adjust(p_values):
    """Return Holm-adjusted p-values in the original order.

    Missing p-values stay missing and do not count towards the family size.
    """

    values = np.asarray(p_values, dtype=float)
    adjusted = np.full(values.shape, np.nan, dtype=float)
    valid_indices = np.flatnonzero(np.isfinite(values))
    if len(valid_indices) == 0:
        return adjusted

    ordered = valid_indices[np.argsort(values[valid_indices])]
    family_size = len(ordered)
    running_maximum = 0.0

    for rank, original_index in enumerate(ordered):
        candidate = (family_size - rank) * values[original_index]
        running_maximum = max(running_maximum, candidate)
        adjusted[original_index] = min(running_maximum, 1.0)

    return adjusted


def percentile_bootstrap_mean(
    values,
    *,
    confidence_level=0.95,
    resamples=50_000,
    seed=20260914,
):
    """Estimate a mean and deterministic percentile-bootstrap interval."""

    sample = _finite_values(values)
    _validate_bootstrap_arguments(confidence_level, resamples)
    generator = np.random.default_rng(seed)
    indices = generator.integers(
        0,
        len(sample),
        size=(resamples, len(sample)),
    )
    estimates = sample[indices].mean(axis=1)
    lower_probability = (1.0 - confidence_level) / 2.0
    lower, upper = np.quantile(
        estimates,
        [lower_probability, 1.0 - lower_probability],
    )
    return float(sample.mean()), float(lower), float(upper)


def percentile_bootstrap_difference(
    first,
    second,
    *,
    confidence_level=0.95,
    resamples=50_000,
    seed=20260914,
):
    """Bootstrap the difference between two independent sample means."""

    first_sample = _finite_values(first)
    second_sample = _finite_values(second)
    _validate_bootstrap_arguments(confidence_level, resamples)
    generator = np.random.default_rng(seed)
    first_indices = generator.integers(
        0,
        len(first_sample),
        size=(resamples, len(first_sample)),
    )
    second_indices = generator.integers(
        0,
        len(second_sample),
        size=(resamples, len(second_sample)),
    )
    estimates = (
        first_sample[first_indices].mean(axis=1)
        - second_sample[second_indices].mean(axis=1)
    )
    lower_probability = (1.0 - confidence_level) / 2.0
    lower, upper = np.quantile(
        estimates,
        [lower_probability, 1.0 - lower_probability],
    )
    point_estimate = first_sample.mean() - second_sample.mean()
    return float(point_estimate), float(lower), float(upper)


def event_study_bootstrap_table(
    company_summary,
    *,
    confidence_level=0.95,
    resamples=50_000,
    seed=20260914,
):
    """Build intervals for both samples and their mean difference."""

    if not isinstance(company_summary, pd.DataFrame):
        raise TypeError("company_summary must be a pandas DataFrame")
    required = {"sample_group", *EVENT_STUDY_METRICS}
    missing = required - set(company_summary.columns)
    if missing:
        names = ", ".join(sorted(missing))
        raise ValueError(f"Company summary is missing columns: {names}")

    confirmatory = company_summary[
        company_summary["sample_group"] == "CONFIRMATORY"
    ]
    exploratory = company_summary[
        company_summary["sample_group"] == "EXPLORATORY"
    ]
    if confirmatory.empty or exploratory.empty:
        raise ValueError(
            "Both CONFIRMATORY and EXPLORATORY samples are required"
        )

    rows = []
    for offset, (metric, label) in enumerate(EVENT_STUDY_METRICS.items()):
        metric_seed = seed + offset * 100
        for group_offset, (group_name, group_data) in enumerate(
            (
                ("CONFIRMATORY", confirmatory),
                ("EXPLORATORY", exploratory),
            )
        ):
            estimate, lower, upper = percentile_bootstrap_mean(
                group_data[metric],
                confidence_level=confidence_level,
                resamples=resamples,
                seed=metric_seed + group_offset,
            )
            rows.append(
                _bootstrap_row(
                    metric,
                    label,
                    "MEAN",
                    group_name,
                    "",
                    len(group_data),
                    0,
                    estimate,
                    lower,
                    upper,
                    confidence_level,
                    resamples,
                    metric_seed + group_offset,
                )
            )

        estimate, lower, upper = percentile_bootstrap_difference(
            confirmatory[metric],
            exploratory[metric],
            confidence_level=confidence_level,
            resamples=resamples,
            seed=metric_seed + 2,
        )
        rows.append(
            _bootstrap_row(
                metric,
                label,
                "DIFFERENCE_IN_MEANS",
                "CONFIRMATORY",
                "EXPLORATORY",
                len(confirmatory),
                len(exploratory),
                estimate,
                lower,
                upper,
                confidence_level,
                resamples,
                metric_seed + 2,
            )
        )

    return pd.DataFrame(rows)


def adjust_lag_p_values(lag_results, *, alpha=0.05):
    """Add Holm-adjusted Pearson and Spearman p-values by price series."""

    if not isinstance(lag_results, pd.DataFrame):
        raise TypeError("lag_results must be a pandas DataFrame")
    required = {
        "product",
        "tax_basis",
        "status",
        "pearson_p_value",
        "spearman_p_value",
    }
    missing = required - set(lag_results.columns)
    if missing:
        names = ", ".join(sorted(missing))
        raise ValueError(f"Lag results are missing columns: {names}")
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must lie strictly between zero and one")

    result = lag_results.copy()
    result["pearson_p_value_holm"] = np.nan
    result["spearman_p_value_holm"] = np.nan

    for _, group in result.groupby(["product", "tax_basis"], sort=False):
        valid = group["status"] == "ok"
        indices = group.index[valid]
        result.loc[indices, "pearson_p_value_holm"] = holm_adjust(
            group.loc[indices, "pearson_p_value"]
        )
        result.loc[indices, "spearman_p_value_holm"] = holm_adjust(
            group.loc[indices, "spearman_p_value"]
        )

    result["pearson_significant_holm_0_05"] = (
        result["pearson_p_value_holm"] < alpha
    )
    result["spearman_significant_holm_0_05"] = (
        result["spearman_p_value_holm"] < alpha
    )
    return result


def export_csv(data, output_file):
    """Atomically export a robustness table."""

    if not isinstance(data, pd.DataFrame):
        raise TypeError("data must be a pandas DataFrame")
    output_path = Path(output_file)
    if output_path.suffix.casefold() != ".csv":
        raise ValueError("Robustness output must use .csv")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(".csv.tmp")
    data.to_csv(temporary_path, index=False)
    temporary_path.replace(output_path)
    return output_path


def _finite_values(values):
    sample = np.asarray(values, dtype=float)
    sample = sample[np.isfinite(sample)]
    if len(sample) < 2:
        raise ValueError("Bootstrap samples require at least two finite values")
    return sample


def _validate_bootstrap_arguments(confidence_level, resamples):
    if not 0.0 < confidence_level < 1.0:
        raise ValueError(
            "confidence_level must lie strictly between zero and one"
        )
    if not isinstance(resamples, int) or resamples < 100:
        raise ValueError("resamples must be an integer of at least 100")


def _bootstrap_row(
    metric,
    label,
    estimator,
    group_a,
    group_b,
    n_a,
    n_b,
    estimate,
    lower,
    upper,
    confidence_level,
    resamples,
    seed,
):
    return {
        "metric": metric,
        "metric_label": label,
        "estimator": estimator,
        "group_a": group_a,
        "group_b": group_b,
        "n_group_a": n_a,
        "n_group_b": n_b,
        "estimate": estimate,
        "ci_lower": lower,
        "ci_upper": upper,
        "confidence_level": confidence_level,
        "resamples": resamples,
        "seed": seed,
        "interval_method": "PERCENTILE_BOOTSTRAP",
        "interpretation": (
            "INTERVAL_EXCLUDES_ZERO"
            if lower > 0.0 or upper < 0.0
            else "INTERVAL_INCLUDES_ZERO"
        ),
    }
