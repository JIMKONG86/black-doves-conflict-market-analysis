import argparse
import base64
import html
import sys

from pathlib import Path

import pandas as pd

from src.black_doves_theme import (
    ACCENT,
    AMBER,
    BLUE,
    DARK_BOKEH_HTML_TEMPLATE,
    GREEN,
    MUTED,
    VIOLET,
    activate_black_doves_theme,
)


_REQUIRED_COLUMNS = {
    "week_end_date",
    "market_date",
    "country_name",
    "strike_events",
    "strike_fatalities",
    "company_ticker",
    "benchmark_ticker",
    "company_cumulative_return",
    "benchmark_cumulative_return",
    "weekly_abnormal_return",
}

_COUNTRY_STYLES = (
    (BLUE, "solid"),
    (VIOLET, "dashed"),
    (GREEN, "dotdash"),
    (ACCENT, "dotted"),
)


def create_black_doves_chart(
    input_file,
    output_path,
    logo_path=None,
    procurement_event_file=None,
):
    from bokeh.core.templates import get_env
    from bokeh.layouts import column
    from bokeh.models import (
        ColumnDataSource,
        Div,
        HoverTool,
        NumeralTickFormatter,
        Span,
    )
    from bokeh.plotting import (
        figure,
        save,
    )
    from bokeh.resources import INLINE

    activate_black_doves_theme()

    analysis_data = _load_analysis_data(input_file)
    output_path = Path(output_path)
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    market_data = (
        analysis_data.sort_values(
            ["week_end_date", "country_name"]
        )
        .drop_duplicates("week_end_date")
        .reset_index(drop=True)
    )
    company_ticker = _one_value(
        analysis_data,
        "company_ticker",
    )
    benchmark_ticker = _one_value(
        analysis_data,
        "benchmark_ticker",
    )
    market_source = ColumnDataSource(
        _with_labels(market_data)
    )

    market_chart = figure(
        title=(
            f"{company_ticker} versus {benchmark_ticker}: "
            "cumulative return"
        ),
        x_axis_type="datetime",
        x_axis_label="Week ending",
        y_axis_label="Cumulative return",
        width=1000,
        height=330,
        sizing_mode="stretch_width",
        tools="pan,wheel_zoom,box_zoom,reset,save",
    )
    company_line = market_chart.line(
        "week_end_date",
        "company_cumulative_return",
        source=market_source,
        legend_label=company_ticker,
        color=AMBER,
        line_width=3,
    )
    company_points = market_chart.scatter(
        "week_end_date",
        "company_cumulative_return",
        source=market_source,
        color=AMBER,
        size=6,
        alpha=0.75,
    )
    benchmark_line = market_chart.line(
        "week_end_date",
        "benchmark_cumulative_return",
        source=market_source,
        legend_label=benchmark_ticker,
        color=BLUE,
        line_width=3,
        line_dash="dashed",
    )
    benchmark_points = market_chart.scatter(
        "week_end_date",
        "benchmark_cumulative_return",
        source=market_source,
        color=BLUE,
        size=6,
        alpha=0.75,
    )
    market_chart.add_tools(
        HoverTool(
            renderers=[company_points],
            tooltips=[
                ("Week", "@week_label"),
                ("Market date", "@market_label"),
                (
                    f"{company_ticker} cumulative",
                    "@company_cumulative_return{0.00%}",
                ),
                (
                    "Weekly abnormal return",
                    "@weekly_abnormal_return{0.00%}",
                ),
            ],
        ),
        HoverTool(
            renderers=[benchmark_points],
            tooltips=[
                ("Week", "@week_label"),
                (
                    f"{benchmark_ticker} cumulative",
                    "@benchmark_cumulative_return{0.00%}",
                ),
            ],
        ),
    )

    if procurement_event_file is not None:
        procurement_data = _load_procurement_markers(
            procurement_event_file,
            market_data,
        )
        procurement_source = ColumnDataSource(
            procurement_data
        )
        procurement_points = market_chart.scatter(
            "effective_market_date",
            "marker_y",
            source=procurement_source,
            marker="diamond",
            color=ACCENT,
            size=13,
            legend_label="Procurement announcement",
        )
        market_chart.add_tools(
            HoverTool(
                renderers=[procurement_points],
                tooltips=[
                    ("Announcement", "@announcement_label"),
                    ("Buyer", "@buyer_name"),
                    ("Systems", "@systems"),
                    ("Title", "@title"),
                    (
                        "Event-day abnormal return",
                        "@event_day_abnormal_return{0.00%}",
                    ),
                ],
            )
        )

        for event_date in procurement_data[
            "effective_market_date"
        ]:
            market_chart.add_layout(
                Span(
                    location=event_date.value / 1_000_000,
                    dimension="height",
                    line_color=ACCENT,
                    line_dash="dotted",
                    line_alpha=0.32,
                    line_width=1,
                )
            )
    market_chart.yaxis.formatter = NumeralTickFormatter(
        format="0.0%"
    )
    _style_chart(market_chart)

    event_chart = figure(
        title="Reported strike events by affected country",
        x_axis_type="datetime",
        x_range=market_chart.x_range,
        x_axis_label="Week ending",
        y_axis_label="Events per week",
        width=1000,
        height=270,
        sizing_mode="stretch_width",
        tools="pan,wheel_zoom,box_zoom,reset,save",
    )
    fatality_chart = figure(
        title="Reported strike fatalities by affected country",
        x_axis_type="datetime",
        x_range=market_chart.x_range,
        x_axis_label="Week ending",
        y_axis_label="Reported fatalities per week",
        width=1000,
        height=270,
        sizing_mode="stretch_width",
        tools="pan,wheel_zoom,box_zoom,reset,save",
    )

    countries = sorted(
        analysis_data["country_name"].unique()
    )

    for index, country_name in enumerate(countries):
        color, line_dash = _COUNTRY_STYLES[
            index % len(_COUNTRY_STYLES)
        ]
        country_data = (
            analysis_data[
                analysis_data["country_name"]
                == country_name
            ]
            .sort_values("week_end_date")
            .reset_index(drop=True)
        )
        source = ColumnDataSource(
            _with_labels(country_data)
        )
        event_line = event_chart.line(
            "week_end_date",
            "strike_events",
            source=source,
            legend_label=country_name,
            color=color,
            line_dash=line_dash,
            line_width=2.5,
        )
        event_points = event_chart.scatter(
            "week_end_date",
            "strike_events",
            source=source,
            color=color,
            size=6,
            alpha=0.75,
        )
        fatality_line = fatality_chart.line(
            "week_end_date",
            "strike_fatalities",
            source=source,
            legend_label=country_name,
            color=color,
            line_dash=line_dash,
            line_width=2.5,
        )
        fatality_points = fatality_chart.scatter(
            "week_end_date",
            "strike_fatalities",
            source=source,
            color=color,
            size=6,
            alpha=0.75,
        )
        event_chart.add_tools(
            HoverTool(
                renderers=[event_points],
                tooltips=[
                    ("Country", country_name),
                    ("Week", "@week_label"),
                    ("Strike events", "@strike_events{0,0}"),
                ],
            )
        )
        fatality_chart.add_tools(
            HoverTool(
                renderers=[fatality_points],
                tooltips=[
                    ("Country", country_name),
                    ("Week", "@week_label"),
                    (
                        "Strike fatalities",
                        "@strike_fatalities{0,0}",
                    ),
                ],
            )
        )

    _style_chart(event_chart)
    _style_chart(fatality_chart)

    header = Div(
        text=_header_html(logo_path),
        sizing_mode="stretch_width",
    )
    scope = Div(
        text=(
            "<h2 style='margin:0 0 4px'>Rheinmetall conflict case</h2>"
            "<p style='margin:0 0 12px'>Long-horizon supporting view · "
            f"{market_data['week_end_date'].min().strftime('%d %b %Y')}–"
            f"{market_data['week_end_date'].max().strftime('%d %b %Y')} · "
            f"{market_data['week_end_date'].nunique()} weekly observations · "
            f"affected countries: {html.escape(', '.join(countries))}</p>"
        ),
        sizing_mode="stretch_width",
    )
    procurement_note = ""

    if procurement_event_file is not None:
        procurement_note = (
            " Diamond markers show verified Rheinmetall "
            "procurement announcement dates."
        )

    source_note = Div(
        text=(
            f"<p style='color:{MUTED};font-size:12px'>"
            "Conflict source: ACLED weekly aggregated data. "
            "Market source: Yahoo Finance. Strike values combine "
            "ACLED air/drone and shelling/artillery/missile "
            "categories. Weekly market returns use all available "
            "trading days assigned to the following Saturday."
            f"{procurement_note}"
            "</p>"
        ),
        sizing_mode="stretch_width",
    )
    dashboard = column(
        header,
        scope,
        market_chart,
        event_chart,
        fatality_chart,
        source_note,
        sizing_mode="stretch_width",
        max_width=1100,
    )

    save(
        dashboard,
        filename=str(output_path),
        title="BLACK DOVES – Rheinmetall Market and Conflict Case",
        resources=INLINE,
        template=get_env().from_string(DARK_BOKEH_HTML_TEMPLATE),
    )

    return output_path


def _load_analysis_data(input_file):
    input_path = Path(input_file)

    if not input_path.is_file():
        raise FileNotFoundError(
            f"BLACK DOVES analysis CSV not found: {input_path}"
        )

    data = pd.read_csv(input_path)
    missing_columns = _REQUIRED_COLUMNS - set(data.columns)

    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(
            "BLACK DOVES analysis CSV is missing required "
            f"columns: {missing}"
        )

    if data.empty:
        raise ValueError(
            "BLACK DOVES analysis CSV must not be empty"
        )

    for column_name in ("week_end_date", "market_date"):
        data[column_name] = pd.to_datetime(
            data[column_name],
            errors="coerce",
        )

        if data[column_name].isna().any():
            raise ValueError(
                f"{column_name} must contain only valid dates"
            )

    for column_name in (
        "strike_events",
        "strike_fatalities",
        "company_cumulative_return",
        "benchmark_cumulative_return",
        "weekly_abnormal_return",
    ):
        data[column_name] = pd.to_numeric(
            data[column_name],
            errors="coerce",
        )

        if data[column_name].isna().any():
            raise ValueError(
                f"{column_name} must contain only numeric values"
            )

    return data.sort_values(
        ["week_end_date", "country_name"]
    ).reset_index(drop=True)


def _with_labels(data):
    result = data.copy()
    result["week_label"] = result[
        "week_end_date"
    ].dt.strftime("%d %b %Y")

    if "market_date" in result.columns:
        result["market_label"] = result[
            "market_date"
        ].dt.strftime("%d %b %Y")

    return result


def _load_procurement_markers(input_file, market_data):
    input_path = Path(input_file)

    if not input_path.is_file():
        raise FileNotFoundError(
            f"Procurement event summary CSV not found: {input_path}"
        )

    events = pd.read_csv(input_path)
    required_columns = {
        "event_id",
        "announcement_date",
        "effective_market_date",
        "buyer_name",
        "title",
        "systems",
        "event_day_abnormal_return",
    }
    missing_columns = required_columns - set(events.columns)

    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(
            "Procurement event summary CSV is missing required "
            f"columns: {missing}"
        )

    if events.empty:
        raise ValueError(
            "Procurement event summary CSV must not be empty"
        )

    result = events.copy()

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

    result["event_day_abnormal_return"] = pd.to_numeric(
        result["event_day_abnormal_return"],
        errors="coerce",
    )

    if result["event_day_abnormal_return"].isna().any():
        raise ValueError(
            "event_day_abnormal_return must contain only "
            "numeric values"
        )

    if result["event_id"].duplicated().any():
        raise ValueError(
            "Procurement event summary CSV contains duplicate events"
        )

    market_points = market_data[
        ["week_end_date", "company_cumulative_return"]
    ].copy()
    market_points = market_points.sort_values(
        "week_end_date"
    ).drop_duplicates("week_end_date")
    result = pd.merge_asof(
        result.sort_values("effective_market_date"),
        market_points,
        left_on="effective_market_date",
        right_on="week_end_date",
        direction="nearest",
    )

    if result["company_cumulative_return"].isna().any():
        raise ValueError(
            "Procurement events could not be aligned to market data"
        )

    result["marker_y"] = result["company_cumulative_return"]
    result["announcement_label"] = result[
        "announcement_date"
    ].dt.strftime("%d %b %Y")

    return result.reset_index(drop=True)


def _one_value(data, column_name):
    values = {
        str(value).strip()
        for value in data[column_name]
        if str(value).strip()
    }

    if len(values) != 1:
        raise ValueError(
            f"{column_name} must contain exactly one value"
        )

    return next(iter(values))


def _header_html(logo_path):
    if logo_path is None:
        return (
            "<h1 style='margin:0'>BLACK DOVES</h1>"
            "<p style='margin:4px 0 12px'>"
            "Identifying the Value of Life in Financial Markets"
            "</p>"
        )

    path = Path(logo_path)

    if not path.is_file():
        raise FileNotFoundError(
            f"BLACK DOVES logo not found: {path}"
        )

    mime_type = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
    }.get(path.suffix.casefold())

    if mime_type is None:
        raise ValueError(
            "BLACK DOVES logo must use PNG or JPEG"
        )

    image_data = base64.b64encode(
        path.read_bytes()
    ).decode("ascii")
    alt_text = html.escape(
        "BLACK DOVES – Identifying the Value of Life "
        "in Financial Markets",
        quote=True,
    )

    return (
        "<div style='margin-bottom:12px'>"
        f"<img src='data:{mime_type};base64,{image_data}' "
        f"alt='{alt_text}' style='width:260px;max-width:60%;"
        "height:auto'>"
        "</div>"
    )


def _style_chart(chart):
    chart.legend.location = "top_left"
    chart.legend.click_policy = "hide"
    chart.legend.label_text_font_size = "11pt"
    chart.grid.grid_line_alpha = 0.2
    chart.toolbar.logo = None


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Create the BLACK DOVES market and conflict "
            "visualization from the joined analysis CSV."
        )
    )
    parser.add_argument(
        "input_file",
        type=Path,
    )
    parser.add_argument(
        "output_file",
        type=Path,
    )
    parser.add_argument(
        "--logo",
        type=Path,
        help="Optional BLACK DOVES PNG or JPEG logo.",
    )
    parser.add_argument(
        "--procurement-events",
        type=Path,
        help=(
            "Optional procurement event-summary CSV used to "
            "add announcement markers to the market chart."
        ),
    )
    return parser


def main(arguments=None):
    parser = build_parser()
    options = parser.parse_args(arguments)

    try:
        output_path = create_black_doves_chart(
            input_file=options.input_file,
            output_path=options.output_file,
            logo_path=options.logo,
            procurement_event_file=options.procurement_events,
        )
    except (
        FileNotFoundError,
        TypeError,
        ValueError,
    ) as error:
        parser.error(str(error))

    print("BLACK DOVES chart saved to:", output_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
