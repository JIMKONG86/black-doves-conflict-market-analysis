import argparse
import sys

from pathlib import Path

import pandas as pd

from src.black_doves_theme import (
    DARK_BOKEH_HTML_TEMPLATE,
    activate_black_doves_theme,
)
from src.black_doves_visualization import _header_html

_RELATIONSHIP_COLORS = {
    "SELF": "#3B82C4",
    "ADVERSARY": "#B03A2E",
    "THIRD_PARTY_NGO": "#54C98A",
    "UN_AGENCY": "#E9A23B",
    "THIRD_PARTY_OSINT": "#9B7FD4",
}
_RELATIONSHIP_LABELS = {
    "SELF": "Self-reported",
    "ADVERSARY": "Reported by an adversary",
    "THIRD_PARTY_NGO": "Third-party NGO",
    "UN_AGENCY": "UN agency",
    "THIRD_PARTY_OSINT": "Third-party OSINT analysts",
}

_REQUIRED_COLUMNS = {
    "estimate_id",
    "actor_or_country",
    "reporting_party",
    "reporting_party_relationship",
    "military_killed",
    "civilian_killed",
    "unclassified_killed",
    "total_killed",
    "total_injured",
    "facilities_or_equipment_damaged_destroyed",
    "damage_description",
    "source_name",
    "source_url",
    "verification_status",
}


def _load_estimates(path):
    data = pd.read_csv(path)
    missing = _REQUIRED_COLUMNS - set(data.columns)

    if missing:
        raise ValueError(
            "casualty/damage file is missing required columns: "
            + ", ".join(sorted(missing))
        )

    numeric_columns = (
        "military_killed",
        "civilian_killed",
        "unclassified_killed",
        "total_killed",
        "total_injured",
        "facilities_or_equipment_damaged_destroyed",
    )

    for column in numeric_columns:
        data[column] = pd.to_numeric(data[column], errors="coerce")

    if (data["total_killed"] < 0).any():
        raise ValueError("total_killed must not be negative")

    data["damage_description"] = data["damage_description"].fillna("")
    data["row_label"] = data["actor_or_country"] + " \u2014 " + data["reporting_party"]
    return data


def create_casualty_damage_chart(estimates_file, output_path, logo_path=None):
    from bokeh.core.templates import get_env
    from bokeh.layouts import column
    from bokeh.models import ColumnDataSource, Div, HoverTool
    from bokeh.plotting import figure, save
    from bokeh.resources import INLINE

    activate_black_doves_theme()

    output_path = Path(output_path)
    if output_path.suffix.casefold() != ".html":
        raise ValueError("Casualty/damage chart output must use .html")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    data = _load_estimates(estimates_file)
    data = data.sort_values(
        ["actor_or_country", "total_killed"], ascending=[True, True]
    )

    chart = figure(
        title="Reported killed by actor and reporting party (party estimates, not verified)",
        x_axis_label="Reported killed (total)",
        y_range=list(data["row_label"]),
        width=1050,
        height=max(320, 34 * len(data)),
        sizing_mode="stretch_width",
        tools="pan,wheel_zoom,box_zoom,reset,save",
    )

    for relationship in _RELATIONSHIP_COLORS:
        subset = data[data["reporting_party_relationship"] == relationship]
        if subset.empty:
            continue
        source = ColumnDataSource(subset)
        bars = chart.hbar(
            y="row_label",
            right="total_killed",
            height=0.6,
            source=source,
            color=_RELATIONSHIP_COLORS[relationship],
            legend_label=_RELATIONSHIP_LABELS[relationship],
        )
        chart.add_tools(
            HoverTool(
                renderers=[bars],
                tooltips=[
                    ("Actor / country", "@actor_or_country"),
                    ("Reporting party", "@reporting_party"),
                    ("Relationship to actor", "@reporting_party_relationship"),
                    ("Military killed", "@military_killed{0,0}"),
                    ("Civilian killed", "@civilian_killed{0,0}"),
                    ("Unclassified killed", "@unclassified_killed{0,0}"),
                    ("Total killed (reported)", "@total_killed{0,0}"),
                    ("Total injured (reported)", "@total_injured{0,0}"),
                    (
                        "Facilities/equipment damaged or destroyed",
                        "@facilities_or_equipment_damaged_destroyed{0,0}",
                    ),
                    ("Detail", "@damage_description"),
                ],
            )
        )

    chart.legend.location = "bottom_right"
    chart.legend.label_text_font_size = "9pt"
    chart.legend.click_policy = "hide"
    chart.xaxis.formatter.use_scientific = False
    chart.grid.grid_line_alpha = 0.2
    chart.toolbar.logo = None

    def _format_int(value):
        return "" if pd.isna(value) else f"{int(value):,}"

    table_rows = "".join(
        "<tr>"
        f"<td>{row.actor_or_country}</td>"
        f"<td>{row.reporting_party}</td>"
        f"<td>{_RELATIONSHIP_LABELS.get(row.reporting_party_relationship, row.reporting_party_relationship)}</td>"
        f"<td>{_format_int(row.military_killed)}</td>"
        f"<td>{_format_int(row.civilian_killed)}</td>"
        f"<td>{_format_int(row.unclassified_killed)}</td>"
        f"<td>{_format_int(row.total_killed)}</td>"
        f"<td>{_format_int(row.total_injured)}</td>"
        "</tr>"
        for row in data.itertuples()
    )
    table_html = (
        "<div style='overflow-x:auto'><table style='width:100%;border-collapse:collapse;"
        "font-size:12px;color:#D8DEE9'>"
        "<thead><tr style='text-align:left;border-bottom:1px solid #344457'>"
        "<th>Actor/country</th><th>Reporting party</th><th>Relationship</th>"
        "<th>Military killed</th><th>Civilian killed</th><th>Unclassified killed</th>"
        "<th>Total killed</th><th>Total injured</th></tr></thead>"
        f"<tbody>{table_rows}</tbody></table></div>"
    )

    method_note = Div(
        text=(
            "<p style='color:#A9B5C3;font-size:12px'>"
            "<b>Party-reported estimates, not independently verified "
            "figures:</b> every row here is one party's claim about "
            "casualties or damage, sourced via a Wikipedia infobox "
            "compilation (retrieved 2026-09-14) of that article's own "
            "citation trail; the original primary sources (government "
            "statements, HRANA, OCHA, OSINT analysts) were not "
            "individually re-verified in this session. Belligerents "
            "reporting their own losses (SELF) generally have an "
            "incentive to understate them; belligerents reporting an "
            "adversary's losses (ADVERSARY) generally have an incentive "
            "to overstate them. The four rows for Iran illustrate this "
            "directly: Iran's own figure (3,528 total), a third-party "
            "human-rights NGO's figure (3,684, broken into military/"
            "civilian/unclassified), a UN agency's civilian-only figure "
            "(3,400+), and a US/Israeli adversary figure for military "
            "losses alone (6,000+) are all shown side by side rather than "
            "averaged or reconciled into one number, because there is no "
            "defensible way to do that from this data. No destroyed-"
            "facilities data is available for most actors; where present "
            "it is a lower bound ('12+', '228+'), not a complete count. "
            "This is a static compilation for one representative moment, "
            "not a live-updating conflict tracker."
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
        title="BLACK DOVES \u2013 Reported Casualties and Damage",
        resources=INLINE,
        template=get_env().from_string(DARK_BOKEH_HTML_TEMPLATE),
    )

    return output_path, len(data)


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Create the BLACK DOVES party-reported casualty/damage "
            "comparison chart."
        )
    )
    parser.add_argument("estimates_file", type=Path)
    parser.add_argument("output_file", type=Path)
    parser.add_argument("--logo", type=Path)
    return parser


def main(arguments=None):
    parser = build_parser()
    options = parser.parse_args(arguments)

    try:
        output_path, row_count = create_casualty_damage_chart(
            estimates_file=options.estimates_file,
            output_path=options.output_file,
            logo_path=options.logo,
        )
    except (FileNotFoundError, TypeError, ValueError) as error:
        parser.error(str(error))

    print("\nBLACK DOVES casualty/damage visualization completed.")
    print(f"Estimate rows plotted: {row_count}")
    print(f"Chart: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
