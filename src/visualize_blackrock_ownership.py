import argparse
import sys

from pathlib import Path

import pandas as pd

from src.black_doves_theme import (
    DARK_BOKEH_HTML_TEMPLATE,
    activate_black_doves_theme,
)
from src.black_doves_visualization import _header_html

_REQUIRED_COLUMNS = {
    "company_id",
    "company_name",
    "ticker",
    "war_economy_role",
    "ownership_percent",
    "stake_value_usd_billion",
    "filing_period",
    "filing_type",
    "source_name",
    "source_url",
    "notes",
}


def _load_stakes(path):
    data = pd.read_csv(path)
    missing = _REQUIRED_COLUMNS - set(data.columns)

    if missing:
        raise ValueError(
            "BlackRock ownership file is missing required columns: "
            + ", ".join(sorted(missing))
        )

    for column in ("ownership_percent", "stake_value_usd_billion"):
        data[column] = pd.to_numeric(data[column], errors="coerce")

    if data["company_name"].isna().any():
        raise ValueError("company_name must not be empty")

    return data


def create_blackrock_ownership_chart(stakes_file, output_path, logo_path=None):
    from bokeh.core.templates import get_env
    from bokeh.layouts import column
    from bokeh.models import ColumnDataSource, Div, HoverTool
    from bokeh.plotting import figure, save
    from bokeh.resources import INLINE

    activate_black_doves_theme()

    output_path = Path(output_path)
    if output_path.suffix.casefold() != ".html":
        raise ValueError("BlackRock ownership chart output must use .html")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    data = _load_stakes(stakes_file)
    value_known = data.dropna(subset=["stake_value_usd_billion"]).sort_values(
        "stake_value_usd_billion"
    )

    chart = figure(
        title=(
            "BlackRock's disclosed stake value in this project's war-economy "
            "companies (Q2 2026 SEC 13F/13G filings)"
        ),
        x_axis_label="Disclosed stake value (USD billion)",
        y_range=list(value_known["company_name"]),
        height=max(280, 60 * len(value_known)),
        sizing_mode="stretch_width",
        tools="pan,wheel_zoom,box_zoom,reset,save",
    )
    source = ColumnDataSource(value_known)
    bars = chart.hbar(
        y="company_name",
        right="stake_value_usd_billion",
        height=0.5,
        source=source,
        color="#E9A23B",
    )
    chart.add_tools(
        HoverTool(
            renderers=[bars],
            tooltips=[
                ("Company", "@company_name (@ticker)"),
                ("Role in this project", "@war_economy_role"),
                ("Disclosed stake value", "$@stake_value_usd_billion{0.00}bn"),
                ("Ownership share", "@ownership_percent{0.00}%"),
                ("Filing period", "@filing_period (@filing_type)"),
                ("Source", "@source_name"),
                ("Detail", "@notes"),
            ],
        )
    )
    chart.xaxis.formatter.use_scientific = False
    chart.grid.grid_line_alpha = 0.2
    chart.toolbar.logo = None

    def _format_row(row):
        value = (
            f"${row.stake_value_usd_billion:.2f}bn"
            if pd.notna(row.stake_value_usd_billion)
            else "n/a (share count only)"
        )
        pct = (
            f"{row.ownership_percent:.2f}%"
            if pd.notna(row.ownership_percent)
            else "not disclosed in source"
        )
        return (
            "<tr>"
            f"<td>{row.company_name} ({row.ticker})</td>"
            f"<td>{row.war_economy_role}</td>"
            f"<td>{pct}</td>"
            f"<td>{value}</td>"
            f"<td>{row.filing_period}</td>"
            f"<td>{row.source_name}</td>"
            "</tr>"
        )

    table_rows = "".join(_format_row(row) for row in data.itertuples())
    table_html = (
        "<div style='overflow-x:auto'><table style='width:100%;border-collapse:collapse;"
        "font-size:12px;color:#D8DEE9'>"
        "<thead><tr style='text-align:left;border-bottom:1px solid #344457'>"
        "<th>Company</th><th>Role</th><th>Ownership %</th>"
        "<th>Disclosed stake value</th><th>Filing period</th><th>Source</th></tr></thead>"
        f"<tbody>{table_rows}</tbody></table></div>"
    )

    method_note = Div(
        text=(
            "<p style='color:#A9B5C3;font-size:12px'>"
            "<b>What this tab is, and is not, showing:</b> these are "
            "BlackRock's own publicly disclosed SEC 13F/13G institutional "
            "holdings in four companies that this project's own tiering "
            "already classifies as PRIMARY_DIRECT to the conflict "
            "(two US defense primes, one Patriot-system manufacturer, "
            "one oil major). BlackRock is overwhelmingly the world's "
            "largest passive/index-fund manager; holding 5&ndash;9% of "
            "nearly every large-cap US company is standard for it and "
            "for its peers Vanguard and State Street, and is not "
            "specific to war-linked firms &mdash; the same three "
            "managers hold comparable stakes in Apple, Coca-Cola or any "
            "S&amp;P 500 constituent. Nothing here shows or claims that "
            "BlackRock influenced conflict outcomes, voted for "
            "escalation, or trades tactically on war news; a passive "
            "index stake tracks the index automatically and generates "
            "no election-style voting behaviour of that kind. What it "
            "does show is a structural fact worth keeping in mind when "
            "reading the rest of this report: the same handful of asset "
            "managers sit as top shareholders on both the "
            "'conflict-exposed' and 'neutral financial-sector "
            "benchmark' sides of this project's own company universe "
            "(BlackRock itself, CMP005, is tagged CONTEXT_FINANCIAL "
            "elsewhere in this report). SEC 13F filings lag by up to 45 "
            "days after quarter-end, so 'Q2 2026' figures were only "
            "public from around mid-August 2026. Two rows show a stake "
            "value or ownership percentage as unavailable because the "
            "source article reported only a share count."
            "</p>"
        ),
        sizing_mode="stretch_width",
    )

    header = Div(text=_header_html(logo_path), sizing_mode="stretch_width")
    dashboard = column(
        header,
        chart,
        Div(text=table_html, sizing_mode="stretch_width"),
        method_note,
        sizing_mode="stretch_width",
        max_width=1100,
    )
    save(
        dashboard,
        filename=str(output_path),
        title="BLACK DOVES \u2013 BlackRock Ownership Stakes",
        resources=INLINE,
        template=get_env().from_string(DARK_BOKEH_HTML_TEMPLATE),
    )

    return output_path, len(data)


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Create the BLACK DOVES chart of BlackRock's disclosed "
            "ownership stakes in this project's war-economy companies."
        )
    )
    parser.add_argument("stakes_file", type=Path)
    parser.add_argument("output_file", type=Path)
    parser.add_argument("--logo", type=Path)
    return parser


def main(arguments=None):
    parser = build_parser()
    options = parser.parse_args(arguments)

    try:
        output_path, row_count = create_blackrock_ownership_chart(
            stakes_file=options.stakes_file,
            output_path=options.output_file,
            logo_path=options.logo,
        )
    except (FileNotFoundError, TypeError, ValueError) as error:
        parser.error(str(error))

    print("\nBLACK DOVES BlackRock ownership visualization completed.")
    print(f"Rows: {row_count}")
    print(f"Chart: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
