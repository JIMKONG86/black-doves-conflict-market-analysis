import math

from dataclasses import dataclass
from datetime import date

import pandas as pd

from src.services.market_universe_event_study import (
    MarketUniverseEventStudy,
)
from src.services.ols_market_model import MARKET_MODEL_ABNORMAL_RETURN_COLUMN


@dataclass(frozen=True)
class MarketPositionAnalysisSummary:
    event_count: int
    company_count: int
    detail_rows: int
    analysis_start: date
    analysis_end: date
    improved_quartile_count: int
    unchanged_quartile_count: int
    weakened_quartile_count: int


class MarketPositionAnalysis:
    """Long-horizon descriptive extension of the short event study."""

    def analyze(
        self,
        events,
        market_file,
        analysis_start=date(2026, 1, 1),
        analysis_end=date(2026, 8, 18),
    ):
        event_items = MarketUniverseEventStudy._events(events)
        start = self._date_value(analysis_start, "analysis_start")
        end = self._date_value(analysis_end, "analysis_end")

        if start > end:
            raise ValueError("analysis_start must not be after analysis_end")

        for event in event_items:
            if not start <= event.event_date <= end:
                raise ValueError(
                    f"Event {event.event_id} lies outside the analysis period"
                )

        market = MarketUniverseEventStudy._market_data(market_file)
        details = []
        summaries = []

        for company_id, company_data in market.groupby(
            "company_id", sort=True
        ):
            company = MarketUniverseEventStudy._company_data(
                company_id,
                company_data,
            )

            for event in event_items:
                detail, summary = self._analyze_company_event(
                    event,
                    company,
                    start,
                    end,
                )
                details.extend(detail)
                summaries.append(summary)

        detail_frame = pd.DataFrame(details)
        company_summary = self._add_position_metrics(
            pd.DataFrame(summaries)
        )
        sample_summary = self._aggregate_post_event(
            detail_frame,
            "sample_group",
        )
        role_summary = self._aggregate_post_event(
            detail_frame,
            "role_category",
        )
        shift_counts = company_summary["position_shift"].value_counts()
        run_summary = MarketPositionAnalysisSummary(
            event_count=len(event_items),
            company_count=company_summary["company_id"].nunique(),
            detail_rows=len(detail_frame),
            analysis_start=start,
            analysis_end=end,
            improved_quartile_count=int(
                shift_counts.get("IMPROVED_QUARTILE", 0)
            ),
            unchanged_quartile_count=int(
                shift_counts.get("UNCHANGED_QUARTILE", 0)
            ),
            weakened_quartile_count=int(
                shift_counts.get("WEAKENED_QUARTILE", 0)
            ),
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
        export = data.copy()

        for column in (
            "analysis_start_date",
            "analysis_end_date",
            "pre_start_market_date",
            "pre_end_market_date",
            "post_start_market_date",
            "post_end_market_date",
        ):
            if column in export.columns:
                export[column] = pd.to_datetime(export[column]).dt.strftime(
                    "%Y-%m-%d"
                )

        return MarketUniverseEventStudy.export_csv(export, output_file)

    @classmethod
    def _analyze_company_event(cls, event, company, start, end):
        event_timestamp = pd.Timestamp(event.event_date)
        positions = company.index[company["Date"] >= event_timestamp]

        if positions.empty:
            raise ValueError(
                f"No market observation for {company.loc[0, 'company_id']} "
                f"on or after {event.event_date.isoformat()}"
            )

        effective_position = int(positions[0])
        effective_date = company.loc[effective_position, "Date"]
        period = company[
            company["Date"].between(pd.Timestamp(start), pd.Timestamp(end))
        ].copy()
        pre = period[period["Date"] < effective_date].copy()
        post = period[period["Date"] >= effective_date].copy()

        if pre.empty or post.empty:
            raise ValueError(
                "Market data must contain observations before and after "
                f"the event for {company.loc[0, 'company_id']}"
            )

        pre["relative_trading_day"] = range(-len(pre), 0)
        post["relative_trading_day"] = range(0, len(post))
        pre["phase"] = "PRE_EVENT"
        post["phase"] = "POST_EVENT"
        period = pd.concat([pre, post], ignore_index=True)
        has_ols = MARKET_MODEL_ABNORMAL_RETURN_COLUMN in period.columns

        for column, return_column in (
            ("phase_company_return", "company_return"),
            ("phase_benchmark_return", "benchmark_return"),
        ):
            period[column] = period.groupby("phase", sort=False)[
                return_column
            ].transform(lambda values: (1.0 + values).cumprod() - 1.0)

        # For horizons of several months, the difference between compounded
        # company and benchmark returns is more interpretable than summing
        # daily abnormal returns.  Keep CAR for comparability with the short
        # event study, but expose BHAR as the preferred long-horizon measure.
        period["phase_bhar"] = (
            period["phase_company_return"]
            - period["phase_benchmark_return"]
        )

        period["phase_car"] = period.groupby("phase", sort=False)[
            "abnormal_return"
        ].cumsum()

        if has_ols:
            period["phase_ols_car"] = period.groupby("phase", sort=False)[
                MARKET_MODEL_ABNORMAL_RETURN_COLUMN
            ].cumsum()

        common = MarketUniverseEventStudy._common_fields(
            event,
            company,
            effective_date,
        )
        detail = []

        for row in period.to_dict(orient="records"):
            detail_row = {
                **common,
                "analysis_start_date": pd.Timestamp(start),
                "analysis_end_date": pd.Timestamp(end),
                "market_date": row["Date"],
                "phase": row["phase"],
                "relative_trading_day": row["relative_trading_day"],
                "company_return": row["company_return"],
                "benchmark_return": row["benchmark_return"],
                "abnormal_return": row["abnormal_return"],
                "phase_company_return": row["phase_company_return"],
                "phase_benchmark_return": row["phase_benchmark_return"],
                "phase_bhar": row["phase_bhar"],
                "phase_car": row["phase_car"],
            }

            if has_ols:
                detail_row[MARKET_MODEL_ABNORMAL_RETURN_COLUMN] = row[
                    MARKET_MODEL_ABNORMAL_RETURN_COLUMN
                ]
                detail_row["phase_ols_car"] = row["phase_ols_car"]

            detail.append(detail_row)

        summary = {
            **common,
            "analysis_start_date": pd.Timestamp(start),
            "analysis_end_date": pd.Timestamp(end),
            **cls._phase_statistics(pre, "pre"),
            **cls._phase_statistics(post, "post"),
        }

        if has_ols:
            summary.update(cls._phase_statistics(pre, "pre", ols=True))
            summary.update(cls._phase_statistics(post, "post", ols=True))

        return detail, summary

    @staticmethod
    def _phase_statistics(frame, prefix, ols=False):
        if ols:
            column = MARKET_MODEL_ABNORMAL_RETURN_COLUMN
            return {
                f"{prefix}_ols_car": float(frame[column].sum()),
                f"{prefix}_mean_daily_ols_abnormal_return": float(
                    frame[column].mean()
                ),
                f"{prefix}_ols_abnormal_volatility": float(
                    frame[column].std(ddof=1)
                ),
                f"{prefix}_positive_ols_abnormal_day_share": float(
                    (frame[column] > 0).mean()
                ),
            }

        company_total_return = float(
            (1.0 + frame["company_return"]).prod() - 1.0
        )
        benchmark_total_return = float(
            (1.0 + frame["benchmark_return"]).prod() - 1.0
        )

        return {
            f"{prefix}_start_market_date": frame["Date"].min(),
            f"{prefix}_end_market_date": frame["Date"].max(),
            f"{prefix}_observations": len(frame),
            f"{prefix}_company_total_return": company_total_return,
            f"{prefix}_benchmark_total_return": benchmark_total_return,
            f"{prefix}_bhar": (
                company_total_return - benchmark_total_return
            ),
            f"{prefix}_car": float(frame["abnormal_return"].sum()),
            f"{prefix}_mean_daily_abnormal_return": float(
                frame["abnormal_return"].mean()
            ),
            f"{prefix}_abnormal_volatility": float(
                frame["abnormal_return"].std(ddof=1)
            ),
            f"{prefix}_positive_abnormal_day_share": float(
                (frame["abnormal_return"] > 0).mean()
            ),
        }

    @classmethod
    def _add_position_metrics(cls, summaries):
        result = summaries.copy()
        grouping = ["event_id"]

        for phase in ("pre", "post"):
            metric = f"{phase}_mean_daily_abnormal_return"
            rank = f"{phase}_rank"
            percentile = f"{phase}_percentile"
            quartile = f"{phase}_quartile"
            result[rank] = result.groupby(grouping)[metric].rank(
                method="min",
                ascending=False,
            )
            result[percentile] = result.groupby(grouping)[rank].transform(
                cls._rank_percentile
            )
            result[quartile] = result[percentile].map(cls._quartile)

        result["rank_change"] = result["pre_rank"] - result["post_rank"]
        result["percentile_change"] = (
            result["post_percentile"] - result["pre_percentile"]
        )
        pre_level = result["pre_quartile"].map(cls._quartile_level)
        post_level = result["post_quartile"].map(cls._quartile_level)
        result["quartile_change"] = post_level - pre_level
        result["position_shift"] = result["quartile_change"].map(
            lambda value: (
                "IMPROVED_QUARTILE"
                if value > 0
                else (
                    "WEAKENED_QUARTILE"
                    if value < 0
                    else "UNCHANGED_QUARTILE"
                )
            )
        )
        return result

    @staticmethod
    def _rank_percentile(ranks):
        count = len(ranks)

        if count == 1:
            return pd.Series(1.0, index=ranks.index)

        return (count - ranks) / (count - 1)

    @staticmethod
    def _quartile(percentile):
        if percentile >= 0.75:
            return "TOP_QUARTILE"

        if percentile >= 0.50:
            return "UPPER_MIDDLE"

        if percentile >= 0.25:
            return "LOWER_MIDDLE"

        return "BOTTOM_QUARTILE"

    @staticmethod
    def _quartile_level(quartile):
        return {
            "BOTTOM_QUARTILE": 1,
            "LOWER_MIDDLE": 2,
            "UPPER_MIDDLE": 3,
            "TOP_QUARTILE": 4,
        }[quartile]

    @staticmethod
    def _aggregate_post_event(detail, group_column):
        post = detail[detail["phase"] == "POST_EVENT"].copy()
        has_ols = MARKET_MODEL_ABNORMAL_RETURN_COLUMN in post.columns
        group_columns = [
            "event_id",
            "event_calendar_date",
            "event_title",
            group_column,
            "relative_trading_day",
        ]
        aggregation = {
            "company_count": ("abnormal_return", "count"),
            "aar": ("abnormal_return", "mean"),
            "aar_standard_deviation": ("abnormal_return", "std"),
        }

        if has_ols:
            aggregation.update(
                {
                    "ols_aar": (
                        MARKET_MODEL_ABNORMAL_RETURN_COLUMN,
                        "mean",
                    ),
                    "ols_aar_standard_deviation": (
                        MARKET_MODEL_ABNORMAL_RETURN_COLUMN,
                        "std",
                    ),
                }
            )

        grouped = (
            post.groupby(group_columns, sort=True).agg(**aggregation).reset_index()
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
        base_groups = [
            "event_id",
            "event_calendar_date",
            "event_title",
            group_column,
        ]
        grouped["caar"] = grouped.groupby(base_groups, sort=False)[
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
            grouped["ols_caar"] = grouped.groupby(base_groups, sort=False)[
                "ols_aar"
            ].cumsum()

        return grouped

    @staticmethod
    def _date_value(value, field_name):
        try:
            parsed = pd.Timestamp(value)
        except (TypeError, ValueError) as error:
            raise ValueError(f"{field_name} must be a valid date") from error

        if pd.isna(parsed):
            raise ValueError(f"{field_name} must be a valid date")

        return parsed.date()
