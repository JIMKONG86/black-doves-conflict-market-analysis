import argparse
import sys

from pathlib import Path

from src.black_doves_theme import (
    DARK_BOKEH_HTML_TEMPLATE,
    activate_black_doves_theme,
)
from src.black_doves_visualization import _header_html
from src.services.procurement_event_aggregate import (
    ProcurementEventAggregateAnalyzer,
)


def create_procurement_event_study_chart(
    input_file,
    aggregate_output_file,
    output_path,
    logo_path=None,
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
    from bokeh.palettes import Category10
    from bokeh.plotting import figure, save
    from bokeh.resources import INLINE

    activate_black_doves_theme()

    analyzer = ProcurementEventAggregateAnalyzer()
    detail, aggregate, summary = analyzer.analyze(input_file)
    analyzer.export_csv(aggregate, aggregate_output_file)
    output_path = Path(output_path)

    if output_path.suffix.casefold() != ".html":
        raise ValueError("Event-study chart output must use .html")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    aggregate_source = ColumnDataSource(aggregate)
    aar_chart = figure(
        title="Average abnormal return around procurement announcements",
        x_axis_label="Relative trading day",
        y_axis_label="Average abnormal return",
        width=1000,
        height=310,
        sizing_mode="stretch_width",
        tools="pan,wheel_zoom,box_zoom,reset,save",
    )
    bars = aar_chart.vbar(
        x="relative_trading_day",
        top="average_abnormal_return",
        width=0.72,
        source=aggregate_source,
        color="#E67E22",
        alpha=0.85,
    )
    aar_chart.add_tools(
        HoverTool(
            renderers=[bars],
            tooltips=[
                ("Relative day", "@relative_trading_day"),
                ("AAR", "@average_abnormal_return{0.00%}"),
                ("Median AR", "@median_abnormal_return{0.00%}"),
                ("Positive events", "@positive_abnormal_share{0.0%}"),
                ("Events", "@event_count"),
            ],
        )
    )
    _add_reference_lines(aar_chart)
    _style_chart(aar_chart)

    caar_chart = figure(
        title="Individual event CAR and cumulative average abnormal return",
        x_axis_label="Relative trading day",
        y_axis_label="Cumulative abnormal return",
        x_range=aar_chart.x_range,
        width=1000,
        height=390,
        sizing_mode="stretch_width",
        tools="pan,wheel_zoom,box_zoom,reset,save",
    )
    palette = Category10[10]
    legend_items = []

    for index, (event_id, event_data) in enumerate(
        detail.groupby("event_id", sort=False)
    ):
        event_data = event_data.sort_values("relative_trading_day")
        event_source = ColumnDataSource(event_data)
        buyer = event_data["buyer_name"].iloc[0]
        line = caar_chart.line(
            "relative_trading_day",
            "event_car",
            source=event_source,
            color=palette[index % len(palette)],
            line_width=1.5,
            alpha=0.48,
        )
        points = caar_chart.scatter(
            "relative_trading_day",
            "event_car",
            source=event_source,
            color=palette[index % len(palette)],
            size=5,
            alpha=0.55,
        )
        legend_items.append((buyer, [line, points]))
        caar_chart.add_tools(
            HoverTool(
                renderers=[points],
                tooltips=[
                    ("Buyer", buyer),
                    ("Relative day", "@relative_trading_day"),
                    ("Event CAR", "@event_car{0.00%}"),
                    ("Title", "@title"),
                ],
            )
        )

    caar_line = caar_chart.line(
        "relative_trading_day",
        "cumulative_average_abnormal_return",
        source=aggregate_source,
        color="#F3F6FA",
        line_width=4,
    )
    caar_points = caar_chart.scatter(
        "relative_trading_day",
        "cumulative_average_abnormal_return",
        source=aggregate_source,
        color="#F3F6FA",
        size=8,
    )
    legend_items.append(("CAAR", [caar_line, caar_points]))
    caar_chart.add_tools(
        HoverTool(
            renderers=[caar_points],
            tooltips=[
                ("Relative day", "@relative_trading_day"),
                (
                    "CAAR",
                    "@cumulative_average_abnormal_return{0.00%}",
                ),
                ("Events", "@event_count"),
            ],
        )
    )

    has_ols = (
        "cumulative_average_ols_abnormal_return" in aggregate.columns
        and aggregate["cumulative_average_ols_abnormal_return"]
        .notna()
        .any()
    )

    if has_ols:
        ols_caar_line = caar_chart.line(
            "relative_trading_day",
            "cumulative_average_ols_abnormal_return",
            source=aggregate_source,
            color="#F3F6FA",
            line_width=2,
            line_dash="dotted",
            line_alpha=0.75,
        )
        legend_items.append(("CAAR (OLS)", [ols_caar_line]))
        caar_chart.add_tools(
            HoverTool(
                renderers=[ols_caar_line],
                tooltips=[
                    ("Relative day", "@relative_trading_day"),
                    (
                        "OLS CAAR",
                        "@cumulative_average_ols_abnormal_return{0.00%}",
                    ),
                    ("Events", "@event_count"),
                ],
            )
        )

    _add_reference_lines(caar_chart)
    _style_chart(caar_chart)
    _add_outside_legend(caar_chart, legend_items)

    header = Div(
        text=_header_html(logo_path),
        sizing_mode="stretch_width",
    )
    method_note = Div(
        text=(
            "<p style='color:#A9B5C3;font-size:12px'>"
            f"Exploratory market-adjusted event study based on "
            f"{summary.event_count} procurement announcements. "
            "AAR is the cross-event mean abnormal return. CAAR is "
            "the cumulative mean from the start of the event window. "
            "Where available, the dotted 'CAAR (OLS)' line uses a "
            "separate single-factor market model fitted per event on "
            "trading days before that event's own announcement date "
            "instead of the naive market-adjusted return; see "
            "src/services/ols_market_model.py. "
            "The vertical reference marks announcement day 0. "
            "Results are descriptive and do not establish causality."
            "</p>"
        ),
        sizing_mode="stretch_width",
    )
    dashboard = column(
        header,
        aar_chart,
        caar_chart,
        method_note,
        sizing_mode="stretch_width",
        max_width=1100,
    )
    save(
        dashboard,
        filename=str(output_path),
        title="BLACK DOVES – Procurement Event Study",
        resources=INLINE,
        template=get_env().from_string(DARK_BOKEH_HTML_TEMPLATE),
    )

    return output_path, Path(aggregate_output_file), summary


def _add_reference_lines(chart):
    from bokeh.models import Span

    chart.add_layout(
        Span(
            location=0,
            dimension="width",
            line_color="#777777",
            line_width=1,
        )
    )
    chart.add_layout(
        Span(
            location=0,
            dimension="height",
            line_color="#B03A2E",
            line_dash="dashed",
            line_width=2,
        )
    )


def _style_chart(chart):
    from bokeh.models import NumeralTickFormatter

    chart.yaxis.formatter = NumeralTickFormatter(format="0.0%")

    if len(chart.legend) > 0:
        chart.legend.location = "top_left"
        chart.legend.label_text_font_size = "10pt"

    chart.grid.grid_line_alpha = 0.2
    chart.toolbar.logo = None


def _add_outside_legend(chart, items):
    from bokeh.models import Legend

    legend = Legend(
        items=items,
        title="Procurement announcements",
        location="top_left",
        label_text_font_size="9pt",
        click_policy="hide",
    )
    chart.add_layout(legend, "right")

    return legend


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Calculate AAR and CAAR and create the BLACK DOVES "
            "procurement event-study chart."
        )
    )
    parser.add_argument("input_file", type=Path)
    parser.add_argument("aggregate_output_file", type=Path)
    parser.add_argument("output_file", type=Path)
    parser.add_argument("--logo", type=Path)
    return parser


def main(arguments=None):
    parser = build_parser()
    options = parser.parse_args(arguments)

    try:
        output_path, aggregate_path, summary = (
            create_procurement_event_study_chart(
                input_file=options.input_file,
                aggregate_output_file=options.aggregate_output_file,
                output_path=options.output_file,
                logo_path=options.logo,
            )
        )
    except (FileNotFoundError, TypeError, ValueError) as error:
        parser.error(str(error))

    print("\nBLACK DOVES procurement visualization completed.")
    print(f"Events: {summary.event_count}")
    print(
        "Event-time period: "
        f"{summary.first_relative_day} to "
        f"+{summary.last_relative_day} trading days"
    )
    print(f"Aggregate CSV: {aggregate_path}")
    print(f"Chart: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
