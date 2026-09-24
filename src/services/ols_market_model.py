"""Ordinary-least-squares single-factor market model for event studies.

The written assignment lists Ordinary Least Squares (OLS) among the
intended technical methods and requires abnormal returns for the
selected defence and energy companies to be estimated against a
suitable national market benchmark. Prior to this module, every
"abnormal_return" figure in the codebase was in fact a naive
market-adjusted return (``company_return - benchmark_return``), not an
OLS-based expected-return deviation. Both quantities are legitimate and
common in event-study practice, but they are not the same thing and the
proposal specifically calls for the OLS variant.

This module adds the missing OLS market-model estimation without
removing or renaming the existing naive columns, so nothing that
already consumes ``abnormal_return`` breaks. It is intentionally
implemented with plain NumPy linear algebra (closed-form OLS via the
normal equations) rather than an additional dependency such as
statsmodels or scikit-learn, in line with the assignment's instruction
not to introduce methodological expansion beyond what is already
justified by the research question.

Definitions
-----------
Estimation window:
    All available trading days strictly before ``event_date``. Using
    only pre-event data avoids look-ahead bias: the model that
    "expects" a return on or after the event date must not itself be
    fitted on data from the event or post-event period.

Market model:
    company_return_t = alpha + beta * benchmark_return_t + error_t

Expected return:
    expected_return_t = alpha + beta * benchmark_return_t
    (evaluated for every date, including the estimation window itself
    and the full event/post-event period)

Market-model abnormal return:
    market_model_abnormal_return_t = company_return_t - expected_return_t

A minimum number of estimation-window observations is required before a
model is fitted; if the requirement is not met, alpha/beta/expected
return/abnormal return are reported as NaN together with an explicit
``ols_status`` flag rather than silently producing a fit on too little
data.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

MINIMUM_ESTIMATION_OBSERVATIONS = 30

# Canonical column name for the OLS market-model abnormal return, shared
# by every module that consumes it (market_universe_event_study.py,
# market_position_analysis.py, procurement_event_study.py) so there is a
# single source of truth instead of independently repeated string literals.
MARKET_MODEL_ABNORMAL_RETURN_COLUMN = "market_model_abnormal_return"


@dataclass(frozen=True)
class OlsMarketModelFit:
    alpha: float
    beta: float
    r_squared: float
    estimation_observations: int
    status: str


def fit_ols_market_model(
    company_returns,
    benchmark_returns,
    minimum_observations=MINIMUM_ESTIMATION_OBSERVATIONS,
):
    """Fit company_return ~ alpha + beta * benchmark_return via OLS.

    Parameters are 1-D array-likes restricted to the estimation window
    only (the caller is responsible for excluding the event date and
    everything after it). Returns an ``OlsMarketModelFit``.
    """
    company = np.asarray(company_returns, dtype=float)
    benchmark = np.asarray(benchmark_returns, dtype=float)

    if company.shape != benchmark.shape:
        raise ValueError(
            "company_returns and benchmark_returns must have the same shape"
        )

    mask = np.isfinite(company) & np.isfinite(benchmark)
    company = company[mask]
    benchmark = benchmark[mask]
    n = company.shape[0]

    if n < minimum_observations:
        return OlsMarketModelFit(
            alpha=float("nan"),
            beta=float("nan"),
            r_squared=float("nan"),
            estimation_observations=n,
            status="insufficient_estimation_window",
        )

    if np.allclose(benchmark, benchmark[0]):
        return OlsMarketModelFit(
            alpha=float("nan"),
            beta=float("nan"),
            r_squared=float("nan"),
            estimation_observations=n,
            status="constant_benchmark_return",
        )

    design = np.column_stack([np.ones(n), benchmark])
    # Closed-form OLS via the normal equations: beta_hat = (X'X)^-1 X'y
    coefficients, _residuals, _rank, _singular_values = np.linalg.lstsq(
        design, company, rcond=None
    )
    alpha, beta = coefficients

    fitted = design @ coefficients
    residuals = company - fitted
    ss_residual = float(np.sum(residuals**2))
    ss_total = float(np.sum((company - company.mean()) ** 2))
    r_squared = (
        1.0 - ss_residual / ss_total if ss_total > 0 else float("nan")
    )

    return OlsMarketModelFit(
        alpha=float(alpha),
        beta=float(beta),
        r_squared=float(r_squared),
        estimation_observations=n,
        status="ok",
    )


def add_market_model_columns(
    comparison,
    event_date,
    minimum_observations=MINIMUM_ESTIMATION_OBSERVATIONS,
):
    """Add OLS market-model columns to a company/benchmark comparison.

    ``comparison`` must contain ``Date``, ``company_return`` and
    ``benchmark_return`` columns, e.g. the output of
    ``compare_market_returns_with_baseline`` /
    ``compare_market_returns_with_baseline``. The existing columns are
    left untouched; this function only appends new ones so it is safe
    to call on data that other code already depends on.
    """
    required = {"Date", "company_return", "benchmark_return"}
    missing = required - set(comparison.columns)
    if missing:
        raise ValueError(
            "comparison is missing required columns: "
            + ", ".join(sorted(missing))
        )

    result = comparison.copy()
    result["Date"] = pd.to_datetime(result["Date"])
    event_timestamp = pd.Timestamp(event_date)

    estimation_mask = result["Date"] < event_timestamp
    fit = fit_ols_market_model(
        result.loc[estimation_mask, "company_return"],
        result.loc[estimation_mask, "benchmark_return"],
        minimum_observations=minimum_observations,
    )

    result["ols_event_date"] = event_timestamp
    result["ols_estimation_window_observations"] = (
        fit.estimation_observations
    )
    result["ols_status"] = fit.status
    result["ols_alpha"] = fit.alpha
    result["ols_beta"] = fit.beta
    result["ols_r_squared"] = fit.r_squared

    if fit.status == "ok":
        result["market_model_expected_return"] = (
            fit.alpha + fit.beta * result["benchmark_return"]
        )
        result[MARKET_MODEL_ABNORMAL_RETURN_COLUMN] = (
            result["company_return"] - result["market_model_expected_return"]
        )
    else:
        result["market_model_expected_return"] = float("nan")
        result[MARKET_MODEL_ABNORMAL_RETURN_COLUMN] = float("nan")

    result["market_model_cumulative_abnormal_return"] = (
        result[MARKET_MODEL_ABNORMAL_RETURN_COLUMN].cumsum()
    )

    return result
