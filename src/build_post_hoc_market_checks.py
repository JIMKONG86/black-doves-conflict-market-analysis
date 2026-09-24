"""Build transparent post-hoc market checks for two later news anchors.

The checks deliberately use complete comparison groups instead of selecting
only companies whose return moved in the expected direction.  They are
descriptive extensions and are not part of the pre-specified 28 February
event study.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MARKET_FILE = (
    ROOT / "data" / "processed" / "market" / "company_benchmark_returns.csv"
)
OUTPUT_FILE = ROOT / "data" / "analysis" / "post_hoc_market_checks.csv"


@dataclass(frozen=True)
class CheckDefinition:
    event_id: str
    event_label: str
    information_date: str
    market_start: str
    market_end: str
    source_name: str
    source_url: str
    interpretation_boundary: str


CHECKS = (
    CheckDefinition(
        event_id="PHM_RHEINMETALL_JULY",
        event_label="Rheinmetall Skynex announcement and sector-wide July run",
        information_date="2026-07-02",
        market_start="2026-07-01",
        market_end="2026-07-02",
        source_name="Rheinmetall AG",
        source_url=(
            "https://www.rheinmetall.com/en/media/news-watch/news/2026/07/"
            "2026-07-02-rheinmetall-is-supplying-four-skynex-systems-to-an-"
            "international-customer"
        ),
        interpretation_boundary=(
            "The window was selected after inspecting the later news record. "
            "Day -1 is included to test whether the two-day movement was "
            "company-specific or sector-wide; no causal attribution is made."
        ),
    ),
    CheckDefinition(
        event_id="PHM_PENTAGON_PRODUCTION",
        event_label="Pentagon production-acceleration report",
        information_date="2026-08-09",
        market_start="2026-08-10",
        market_end="2026-08-10",
        source_name="Associated Press",
        source_url=(
            "https://apnews.com/article/"
            "c98e042bfd0fd22cd97d15b1fffa322c"
        ),
        interpretation_boundary=(
            "Sunday-to-Monday timing is clean, but the event was selected "
            "post hoc and concurrent news is uncontrolled. Group comparisons "
            "test specificity, not causality."
        ),
    ),
)


class PostHocMarketCheckBuilder:
    REQUIRED_COLUMNS = {
        "Date",
        "company_id",
        "company_name",
        "benchmark_ticker",
        "analysis_tier",
        "role_category",
        "abnormal_return",
        "market_model_abnormal_return",
    }

    def build(self, market_file: Path | str = MARKET_FILE) -> pd.DataFrame:
        panel = self._load_panel(market_file)
        rows: list[dict] = []

        for check in CHECKS:
            window = panel[
                panel["Date"].between(
                    pd.Timestamp(check.market_start),
                    pd.Timestamp(check.market_end),
                )
            ].copy()
            if window.empty:
                raise ValueError(f"No observations for {check.event_id}")

            company_window = (
                window.groupby(
                    [
                        "company_id",
                        "company_name",
                        "benchmark_ticker",
                        "analysis_tier",
                        "role_category",
                    ],
                    as_index=False,
                    dropna=False,
                )
                .agg(
                    market_adjusted_return=("abnormal_return", "sum"),
                    ols_market_model_return=(
                        "market_model_abnormal_return",
                        "sum",
                    ),
                    market_observations=("Date", "count"),
                    positive_market_days=(
                        "abnormal_return",
                        lambda values: int((values > 0).sum()),
                    ),
                )
            )

            for group_id, group_label, mask in self._groups(
                check.event_id, company_window
            ):
                selected = company_window.loc[mask].copy()
                if selected.empty:
                    raise ValueError(
                        f"No companies for {check.event_id}/{group_id}"
                    )
                rows.append(
                    self._summary_row(
                        check, group_id, group_label, selected
                    )
                )

        return pd.DataFrame(rows).sort_values(
            ["event_id", "group_order", "group_id"]
        ).reset_index(drop=True)

    @staticmethod
    def export(data: pd.DataFrame, output_file: Path | str = OUTPUT_FILE):
        if not isinstance(data, pd.DataFrame):
            raise TypeError("data must be a pandas DataFrame")
        path = Path(output_file)
        if path.suffix.casefold() != ".csv":
            raise ValueError(f"CSV output required: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".csv.tmp")
        data.to_csv(temporary, index=False)
        temporary.replace(path)
        return path

    @classmethod
    def _load_panel(cls, market_file):
        path = Path(market_file)
        if not path.is_file():
            raise FileNotFoundError(f"Market panel not found: {path}")
        panel = pd.read_csv(path)
        missing = cls.REQUIRED_COLUMNS - set(panel.columns)
        if missing:
            raise ValueError(
                "Market panel is missing required columns: "
                + ", ".join(sorted(missing))
            )
        panel = panel.copy()
        panel["Date"] = pd.to_datetime(panel["Date"], errors="coerce")
        if panel["Date"].isna().any():
            raise ValueError("Market panel contains invalid dates")
        if panel.duplicated(["company_id", "Date"]).any():
            raise ValueError("Market panel contains duplicate company-date rows")
        for column in ("abnormal_return", "market_model_abnormal_return"):
            panel[column] = pd.to_numeric(panel[column], errors="coerce")
        if panel[["abnormal_return"]].isna().any().any():
            raise ValueError("Market panel contains invalid abnormal returns")
        return panel

    @staticmethod
    def _groups(event_id, companies):
        defence = companies["role_category"].eq("Defence Contractor")
        if event_id == "PHM_RHEINMETALL_JULY":
            rheinmetall = companies["company_id"].eq("CMP035")
            return (
                (1, "RHEINMETALL", rheinmetall),
                (2, "DEFENCE_PEERS", defence & ~rheinmetall),
                (3, "ALL_DEFENCE", defence),
                (4, "ALL_NON_DEFENCE", ~defence),
            )

        us_sp500 = companies["benchmark_ticker"].eq("^GSPC")
        definitions = [
            (1, "LOCKHEED_MARTIN", companies["company_id"].eq("CMP027")),
            (2, "NORTHROP_GRUMMAN", companies["company_id"].eq("CMP030")),
            (3, "GENERAL_DYNAMICS", companies["company_id"].eq("CMP022")),
            (4, "RTX", companies["company_id"].eq("CMP036")),
            (5, "US_DEFENCE_SP500", defence & us_sp500),
            (6, "US_NON_DEFENCE_SP500", ~defence & us_sp500),
            (7, "ALL_DEFENCE", defence),
            (8, "ALL_NON_DEFENCE", ~defence),
        ]
        return tuple(definitions)

    @staticmethod
    def _summary_row(check, group_order, group_id, selected):
        adjusted = selected["market_adjusted_return"]
        ols = selected["ols_market_model_return"]
        company_names = " | ".join(selected["company_name"].sort_values())
        return {
            "event_id": check.event_id,
            "event_label": check.event_label,
            "information_date": check.information_date,
            "market_start": check.market_start,
            "market_end": check.market_end,
            "group_order": group_order,
            "group_id": group_id,
            "company_count": len(selected),
            "positive_company_count": int((adjusted > 0).sum()),
            "positive_every_market_day_count": int(
                (
                    selected["positive_market_days"]
                    == selected["market_observations"]
                ).sum()
            ),
            "mean_market_adjusted_return": float(adjusted.mean()),
            "median_market_adjusted_return": float(adjusted.median()),
            "mean_ols_market_model_return": float(ols.mean()),
            "company_names": company_names,
            "source_name": check.source_name,
            "source_url": check.source_url,
            "selection_status": "POST_HOC_DESCRIPTIVE_NOT_CAUSAL",
            "interpretation_boundary": check.interpretation_boundary,
        }


def main():
    builder = PostHocMarketCheckBuilder()
    path = builder.export(builder.build())
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
