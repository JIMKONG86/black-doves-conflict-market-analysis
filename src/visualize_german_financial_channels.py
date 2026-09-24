import argparse
import sys

from pathlib import Path

import pandas as pd

from src.black_doves_theme import (
    DARK_BOKEH_HTML_TEMPLATE,
    activate_black_doves_theme,
)
from src.black_doves_visualization import _header_html

_POINT_TYPE_MARKERS = {
    "CLOSE": "circle",
    "CLOSE_APPROX": "circle",
    "INTRADAY_HIGH": "triangle",
    "INTRADAY_LOW": "inverted_triangle",
    "LEVEL": "circle",
    "MONTHLY_TOP_APPROX": "square",
}

_REQUIRED_COLUMNS = {
    "observation_id",
    "observation_date",
    "metric",
    "value",
    "unit",
    "point_type",
    "context_note",
    "source_name",
    "source_url",
}


def _load_observations(path):
    data = pd.read_csv(path)
    missing = _REQUIRED_COLUMNS - set(data.columns)

    if missing:
        raise ValueError(
            "German financial channels file is missing required columns: "
            + ", ".join(sorted(missing))
        )

    data["observation_date"] = pd.to_datetime(
        data["observation_date"], errors="coerce"
    )
    if data["observation_date"].isna().any():
        raise ValueError("observation_date contains unparseable dates")

    data["value"] = pd.to_numeric(data["value"], errors="coerce")
    if data["value"].isna().any():
        raise ValueError("value must be numeric for every row")

    data["marker"] = data["point_type"].map(_POINT_TYPE_MARKERS).fillna("circle")
    return data


def create_german_financial_channels_chart(
    observations_file, output_path, logo_path=None
):
    from bokeh.core.templates import get_env
    from bokeh.layouts import column
    from bokeh.models import ColumnDataSource, Div, HoverTool, Span
    from bokeh.plotting import figure, save
    from bokeh.resources import INLINE

    activate_black_doves_theme()

    output_path = Path(output_path)
    if output_path.suffix.casefold() != ".html":
        raise ValueError(
            "German financial channels chart output must use .html"
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)

    data = _load_observations(observations_file)

    dax = data[data["metric"] == "DAX"].sort_values("observation_date")
    bund = data[data["metric"] == "BUND_10Y_YIELD"].sort_values(
        "observation_date"
    )

    event_date = pd.Timestamp("2026-02-28")

    dax_chart = figure(
        title="DAX \u2014 real, individually sourced closing/intraday levels (not a continuous daily series)",
        x_axis_type="datetime",
        x_axis_label="Date",
        y_axis_label="DAX (index points)",
        height=320,
        sizing_mode="stretch_width",
        tools="pan,wheel_zoom,box_zoom,reset,save",
    )
    dax_source = ColumnDataSource(dax)
    dax_line = dax_chart.line(
        "observation_date", "value", source=dax_source, color="#54C98A",
        line_width=2, alpha=0.6,
    )
    dax_points = dax_chart.scatter(
        "observation_date", "value", source=dax_source, size=10,
        color="#54C98A", marker="marker",
    )
    dax_chart.add_tools(
        HoverTool(
            renderers=[dax_points],
            tooltips=[
                ("Date", "@observation_date{%F}"),
                ("DAX", "@value{0,0.00}"),
                ("Point type", "@point_type"),
                ("Context", "@context_note"),
                ("Source", "@source_name"),
            ],
            formatters={"@observation_date": "datetime"},
        )
    )
    dax_chart.add_layout(
        Span(
            location=event_date.timestamp() * 1000,
            dimension="height",
            line_color="#E9A23B",
            line_dash="dashed",
            line_width=2,
        )
    )

    bund_chart = figure(
        title="German 10-year Bund yield \u2014 real, individually sourced levels (not a continuous daily series)",
        x_axis_type="datetime",
        x_axis_label="Date",
        y_axis_label="10Y Bund yield (%)",
        height=320,
        sizing_mode="stretch_width",
        x_range=dax_chart.x_range,
        tools="pan,wheel_zoom,box_zoom,reset,save",
    )
    bund_source = ColumnDataSource(bund)
    bund_chart.line(
        "observation_date", "value", source=bund_source, color="#E9A23B",
        line_width=2, alpha=0.6,
    )
    bund_points = bund_chart.scatter(
        "observation_date", "value", source=bund_source, size=10,
        color="#E9A23B", marker="marker",
    )
    bund_chart.add_tools(
        HoverTool(
            renderers=[bund_points],
            tooltips=[
                ("Date", "@observation_date{%F}"),
                ("10Y Bund yield", "@value{0.00}%"),
                ("Point type", "@point_type"),
                ("Context", "@context_note"),
                ("Source", "@source_name"),
            ],
            formatters={"@observation_date": "datetime"},
        )
    )
    bund_chart.add_layout(
        Span(
            location=event_date.timestamp() * 1000,
            dimension="height",
            line_color="#E9A23B",
            line_dash="dashed",
            line_width=2,
        )
    )

    for chart in (dax_chart, bund_chart):
        chart.grid.grid_line_alpha = 0.2
        chart.toolbar.logo = None

    method_note = Div(
        text=(
            "<p style='color:#A9B5C3;font-size:12px'>"
            "<b>Two additional transmission channels beyond the oil "
            "price:</b> German politicians and market commentary "
            "repeatedly linked the war to (1) German government bond "
            "yields and (2) equity-market sentiment via diplomacy/"
            "de-escalation hope, not only via the fuel-price channel "
            "already covered in Strikes &amp; energy. Vice-Chancellor "
            "Klingbeil publicly attributed rising Bund yields to "
            "war-driven uncertainty (24 Aug 2026) and separately "
            "attributed high fuel prices to the war while renewing a "
            "call for an EU windfall tax on oil companies (28 Aug "
            "2026); the DAX hit successive record closes explicitly "
            "credited by financial media to 'hope for an Iran deal' "
            "and falling oil prices. <b>These are individually sourced "
            "real data points from financial news, not a continuous "
            "daily time series</b> \u2014 gaps between points do not mean "
            "the index or yield stood still, only that no dated news "
            "item was found and sourced for that day. Triangles mark "
            "intraday highs/lows, circles mark closing levels or the "
            "level as reported at a point in time; do not read the "
            "connecting line as an actual daily path. The dashed "
            "vertical line marks the primary event date (28 Feb 2026). "
            "Correlation with the war is suggested by contemporaneous "
            "news commentary, not established here through statistical "
            "testing; other drivers (ECB policy, US Fed commentary, "
            "German fiscal/defence spending plans, general inflation) "
            "were explicitly cited alongside the war in the same "
            "source articles and are not separated out."
            "</p>"
        ),
        sizing_mode="stretch_width",
    )

    header = Div(text=_header_html(logo_path), sizing_mode="stretch_width")
    dashboard = column(
        header,
        dax_chart,
        bund_chart,
        method_note,
        sizing_mode="stretch_width",
        max_width=1100,
    )
    save(
        dashboard,
        filename=str(output_path),
        title="BLACK DOVES \u2013 German Financial Channels",
        resources=INLINE,
        template=get_env().from_string(DARK_BOKEH_HTML_TEMPLATE),
    )

    return output_path, len(dax), len(bund)


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Create the BLACK DOVES chart for DAX and German 10-year "
            "Bund yield as additional war-transmission channels beyond "
            "the oil price."
        )
    )
    parser.add_argument("observations_file", type=Path)
    parser.add_argument("output_file", type=Path)
    parser.add_argument("--logo", type=Path)
    return parser


def main(arguments=None):
    parser = build_parser()
    options = parser.parse_args(arguments)

    try:
        output_path, dax_count, bund_count = (
            create_german_financial_channels_chart(
                observations_file=options.observations_file,
                output_path=options.output_file,
                logo_path=options.logo,
            )
        )
    except (FileNotFoundError, TypeError, ValueError) as error:
        parser.error(str(error))

    print("\nBLACK DOVES German financial channels visualization completed.")
    print(f"DAX observations: {dax_count}")
    print(f"Bund yield observations: {bund_count}")
    print(f"Chart: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
