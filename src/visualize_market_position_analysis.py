import argparse
import html
import sys

from pathlib import Path

import pandas as pd

from src.black_doves_visualization import _header_html
from src.black_doves_theme import (
    DARK_BOKEH_HTML_TEMPLATE,
    DARK_FILTER_ROW_STYLESHEET,
    activate_black_doves_theme,
    style_dark_button,
    style_dark_select,
    style_dark_tabs,
)


_DETAIL_COLUMNS = {
    "event_id",
    "event_calendar_date",
    "event_title",
    "company_id",
    "company_name",
    "is_confirmatory",
    "sample_group",
    "market_date",
    "phase",
    "relative_trading_day",
    "abnormal_return",
    "phase_car",
}

_COMPANY_COLUMNS = {
    "event_id",
    "event_calendar_date",
    "event_title",
    "analysis_start_date",
    "analysis_end_date",
    "company_id",
    "company_name",
    "market_data_ticker",
    "benchmark_ticker",
    "role_category",
    "sample_group",
    "pre_car",
    "post_car",
    "pre_company_total_return",
    "pre_benchmark_total_return",
    "post_company_total_return",
    "post_benchmark_total_return",
    "pre_mean_daily_abnormal_return",
    "post_mean_daily_abnormal_return",
    "pre_rank",
    "post_rank",
    "rank_change",
    "pre_percentile",
    "post_percentile",
    "percentile_change",
    "pre_quartile",
    "post_quartile",
    "position_shift",
}

_SAMPLE_COLUMNS = {
    "event_id",
    "event_calendar_date",
    "event_title",
    "sample_group",
    "relative_trading_day",
    "company_count",
    "aar",
    "caar",
}

_SAMPLE_STYLES = {
    "CONFIRMATORY": ("#E67E22", "solid", "circle"),
    "EXPLORATORY": ("#2980B9", "dashed", "triangle"),
    "POST_HOC_EXPLORATORY": ("#8E44AD", "dotted", "square"),
}

_SHIFT_COLORS = {
    "IMPROVED_QUARTILE": "#1E8449",
    "UNCHANGED_QUARTILE": "#7F8C8D",
    "WEAKENED_QUARTILE": "#B03A2E",
}

_MOBILE_HTML_TEMPLATE = DARK_BOKEH_HTML_TEMPLATE


def create_market_position_dashboard(
    detail_file,
    company_file,
    sample_file,
    output_path,
    logo_path=None,
    event_id=None,
):
    from bokeh.core.templates import get_env
    from bokeh.events import DocumentReady
    from bokeh.layouts import column, row
    from bokeh.models import (
        Button,
        ColumnDataSource,
        CustomJS,
        Div,
        FixedTicker,
        HoverTool,
        Legend,
        LinearAxis,
        NumeralTickFormatter,
        Range1d,
        Select,
        Span,
        TabPanel,
        Tabs,
    )
    from bokeh.palettes import Category10
    from bokeh.plotting import figure, save
    from bokeh.resources import INLINE

    activate_black_doves_theme()

    detail = _load_detail(detail_file)
    companies = _load_companies(company_file)
    samples = _load_samples(sample_file)
    selected_event = _select_event((detail, companies, samples), event_id)
    detail = _event_rows(detail, selected_event)
    companies = _event_rows(companies, selected_event)
    samples = _event_rows(samples, selected_event)
    _validate_inputs(detail, companies, samples)
    dashboard_companies = _dashboard_company_data(companies)
    dashboard_detail = _detail_with_company_dimensions(
        detail,
        dashboard_companies,
    )
    output_path = Path(output_path)

    if output_path.suffix.casefold() != ".html":
        raise ValueError("Market-position dashboard output must use .html")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    sample_chart, sample_sources, sample_groups = _sample_chart(
        samples,
        dashboard_detail,
        ColumnDataSource,
        FixedTicker,
        HoverTool,
        LinearAxis,
        NumeralTickFormatter,
        Span,
        figure,
    )
    position_chart, position_source = _position_chart(
        dashboard_companies,
        ColumnDataSource,
        HoverTool,
        NumeralTickFormatter,
        Range1d,
        figure,
    )
    shift_chart, shift_source = _shift_chart(
        dashboard_companies,
        ColumnDataSource,
        HoverTool,
        figure,
    )
    ranking_chart, ranking_source = _post_ranking_chart(
        dashboard_companies,
        ColumnDataSource,
        HoverTool,
        NumeralTickFormatter,
        Span,
        figure,
    )
    (
        selected_chart,
        path_renderers,
        path_renderer_company_ids,
    ) = _selected_paths_chart(
        dashboard_detail,
        Category10,
        ColumnDataSource,
        HoverTool,
        Legend,
        NumeralTickFormatter,
        figure,
    )

    start = companies["analysis_start_date"].iloc[0].strftime("%d.%m.%Y")
    end = companies["analysis_end_date"].iloc[0].strftime("%d.%m.%Y")
    event_date = companies["event_calendar_date"].iloc[0].strftime(
        "%d.%m.%Y"
    )
    title = html.escape(str(companies["event_title"].iloc[0]))
    counts = companies["position_shift"].value_counts()
    scope = Div(
        text=(
            "<h2 style='margin:0 0 4px'>Long-horizon capital-market "
            "positioning</h2>"
            f"<p style='margin:0 0 12px'><b>{title}</b> · event "
            f"{event_date} · analysis {start}–{end} · "
            f"{len(companies)} companies · "
            f"{int(counts.get('IMPROVED_QUARTILE', 0))} improved · "
            f"{int(counts.get('UNCHANGED_QUARTILE', 0))} unchanged · "
            f"{int(counts.get('WEAKENED_QUARTILE', 0))} weakened"
            "</p>"
        ),
        sizing_mode="stretch_width",
    )
    interpretation_guide = Div(
        text=_interpretation_guide_html(),
        sizing_mode="stretch_width",
    )
    method_note = Div(
        text=(
            "<p style='color:#A9B5C3;font-size:12px'>"
            "Capital-market position means a company's relative rank "
            "within this 46-company sample, not its market share or "
            "competitive position in product markets. Pre- and post-event "
            "ranks use mean daily abnormal return, defined as company return "
            "minus the configured local-benchmark return. A categorical "
            "shift is reported only when the company changes quartile. "
            "Where available, the dotted 'OLS' line on Sample CAAR uses a "
            "separate single-factor market model (company_return = alpha + "
            "beta * benchmark_return) fitted per company on trading days "
            "before the event date instead of the naive market-adjusted "
            "return; see src/services/ols_market_model.py. Long-horizon "
            "results are descriptive, may reflect many later events, and do "
            "not establish causality."
            "</p>"
        ),
        sizing_mode="stretch_width",
    )
    (
        filter_panel,
        filter_callback,
        reset_callback,
    ) = _filter_controls(
        companies=dashboard_companies,
        detail=dashboard_detail,
        position_source=position_source,
        shift_source=shift_source,
        ranking_source=ranking_source,
        shift_chart=shift_chart,
        ranking_chart=ranking_chart,
        shift_range=shift_chart.y_range,
        ranking_range=ranking_chart.y_range,
        sample_sources=sample_sources,
        sample_groups=sample_groups,
        path_renderers=path_renderers,
        path_renderer_company_ids=path_renderer_company_ids,
        source_class=ColumnDataSource,
        select_class=Select,
        button_class=Button,
        div_class=Div,
        custom_js_class=CustomJS,
        column_class=column,
        row_class=row,
    )
    # Keep callback models alive through their widget references. The local
    # names make their intended ownership explicit for static HTML exports.
    _ = (filter_callback, reset_callback)
    tabs = Tabs(
        tabs=[
            TabPanel(title="Sample CAAR", child=sample_chart),
            TabPanel(title="Position map", child=position_chart),
            TabPanel(title="Rank shifts", child=shift_chart),
            TabPanel(title="Post CAR", child=ranking_chart),
            TabPanel(title="Primary + VW", child=selected_chart),
        ],
        sizing_mode="stretch_width",
    )
    style_dark_tabs(tabs)
    dashboard = column(
        Div(text=_header_html(logo_path), sizing_mode="stretch_width"),
        scope,
        filter_panel,
        tabs,
        interpretation_guide,
        method_note,
        sizing_mode="stretch_width",
        max_width=1250,
    )
    responsive_callback = CustomJS(
        args={
            "sample_chart": sample_chart,
            "position_chart": position_chart,
            "shift_chart": shift_chart,
            "ranking_chart": ranking_chart,
            "selected_chart": selected_chart,
            "shift_source": shift_source,
            "ranking_source": ranking_source,
        },
        code=_responsive_callback_code(),
    )
    dashboard.js_on_event(DocumentReady, responsive_callback)
    save(
        dashboard,
        filename=str(output_path),
        title="BLACK DOVES – Long-Horizon Market Positioning",
        resources=INLINE,
        template=get_env().from_string(_MOBILE_HTML_TEMPLATE),
    )
    return output_path


def _sample_chart(
    samples,
    detail,
    source_class,
    fixed_ticker_class,
    hover_class,
    linear_axis_class,
    formatter_class,
    span_class,
    figure_class,
):
    chart = figure_class(
        title="Post-event cumulative average abnormal return by sample",
        x_axis_label="Relative trading day after the event",
        y_axis_label="Post-event CAAR",
        width=1050,
        height=700,
        sizing_mode="stretch_width",
        tools="pan,wheel_zoom,box_zoom,reset,save",
    )

    sample_sources = []
    sample_groups = _sample_order(samples)

    for sample_group in sample_groups:
        color, line_dash, marker = _SAMPLE_STYLES.get(
            sample_group,
            ("#5D6D7E", "dotdash", "diamond"),
        )
        sample = samples[
            samples["sample_group"] == sample_group
        ].sort_values("relative_trading_day")
        source = source_class(sample)
        sample_sources.append(source)
        label = _sample_label(sample_group)
        chart.line(
            "relative_trading_day",
            "caar",
            source=source,
            color=color,
            line_dash=line_dash,
            line_width=3,
            legend_label=label,
        )
        points = chart.scatter(
            "relative_trading_day",
            "caar",
            source=source,
            marker=marker,
            color=color,
            size=6,
            legend_label=label,
        )

        if "ols_caar" in sample.columns and sample["ols_caar"].notna().any():
            ols_label = f"{label} (OLS)"
            ols_line = chart.line(
                "relative_trading_day",
                "ols_caar",
                source=source,
                color=color,
                line_dash="dotted",
                line_width=1.6,
                line_alpha=0.85,
                legend_label=ols_label,
            )
            chart.add_tools(
                hover_class(
                    renderers=[ols_line],
                    tooltips=[
                        ("Sample", ols_label),
                        ("Trading day", "@relative_trading_day"),
                        ("OLS CAAR", "@ols_caar{0.00%}"),
                        ("Companies", "@company_count"),
                    ],
                )
            )

        chart.add_tools(
            hover_class(
                renderers=[points],
                tooltips=[
                    ("Sample", label),
                    ("Trading day", "@relative_trading_day"),
                    ("CAAR", "@caar{0.00%}"),
                    ("Companies", "@company_count"),
                ],
            )
        )

    chart.add_layout(
        span_class(location=0, dimension="width", line_color="#666666")
    )
    month_ticks, month_labels = _month_axis_values(detail)
    month_axis = linear_axis_class(
        ticker=fixed_ticker_class(ticks=month_ticks),
        major_label_overrides=month_labels,
        axis_label="Calendar month",
    )
    chart.add_layout(month_axis, "below")
    chart.yaxis.formatter = formatter_class(format="0.0%")
    _style_chart(chart)
    return chart, sample_sources, sample_groups


def _position_chart(
    companies,
    source_class,
    hover_class,
    formatter_class,
    range_class,
    figure_class,
):
    position = companies.copy()
    source = source_class(position)
    chart = figure_class(
        title="Relative capital-market position before versus after event",
        x_axis_label="Pre-event sample percentile",
        y_axis_label="Post-event sample percentile",
        x_range=range_class(-0.05, 1.05),
        y_range=range_class(-0.05, 1.05),
        width=900,
        height=700,
        sizing_mode="stretch_width",
        tools="pan,wheel_zoom,box_zoom,reset,save",
    )
    chart.line(
        [0, 1],
        [0, 1],
        color="#7F8C8D",
        line_dash="dashed",
        line_width=2,
    )
    points = chart.scatter(
        "pre_percentile",
        "post_percentile",
        source=source,
        color="point_color",
        size=11,
        alpha=0.85,
        legend_field="shift_label",
    )
    chart.add_tools(
        hover_class(
            renderers=[points],
            tooltips=[
                ("Company", "@company_name"),
                ("Ticker", "@market_data_ticker"),
                ("Role", "@role_category"),
                ("Pre rank", "@pre_rank{0}"),
                ("Post rank", "@post_rank{0}"),
                ("Rank change", "@rank_change{+0;-0;0}"),
                ("Pre percentile", "@pre_percentile{0.0%}"),
                ("Post percentile", "@post_percentile{0.0%}"),
                ("Pre quartile", "@pre_quartile"),
                ("Post quartile", "@post_quartile"),
                ("Shift", "@shift_label"),
            ],
        )
    )
    chart.xaxis.formatter = formatter_class(format="0%")
    chart.yaxis.formatter = formatter_class(format="0%")
    _style_chart(chart)
    return chart, source


def _shift_chart(companies, source_class, hover_class, figure_class):
    shifts = companies.sort_values(
        ["rank_change", "company_name"]
    ).copy()
    source = source_class(shifts)
    chart = figure_class(
        title="Change in sample rank after the event",
        x_axis_label="Rank change (positive = moved upward)",
        y_range=shifts["axis_label"].tolist(),
        width=1050,
        height=700,
        sizing_mode="stretch_width",
        tools="pan,wheel_zoom,box_zoom,reset,save",
    )
    bars = chart.hbar(
        y="axis_label",
        left=0,
        right="rank_change",
        height=0.72,
        color="bar_color",
        alpha=0.88,
        source=source,
        legend_field="shift_label",
    )
    chart.add_tools(
        hover_class(
            renderers=[bars],
            tooltips=[
                ("Company", "@company_name"),
                ("Pre rank", "@pre_rank{0}"),
                ("Post rank", "@post_rank{0}"),
                ("Rank change", "@rank_change{+0;-0;0}"),
                ("Percentile change", "@percentile_change{+0.0%;-0.0%;0.0%}"),
                ("Shift", "@shift_label"),
            ],
        )
    )
    chart.yaxis.major_label_text_font_size = "8pt"
    _style_chart(chart)
    return chart, source


def _post_ranking_chart(
    companies,
    source_class,
    hover_class,
    formatter_class,
    span_class,
    figure_class,
):
    ranking = companies.sort_values(["post_car", "company_name"]).copy()
    source = source_class(ranking)
    chart = figure_class(
        title="Full post-event cumulative abnormal return",
        x_axis_label="Post-event CAR through analysis end",
        y_range=ranking["axis_label"].tolist(),
        width=1050,
        height=700,
        sizing_mode="stretch_width",
        tools="pan,wheel_zoom,box_zoom,reset,save",
    )
    bars = chart.hbar(
        y="axis_label",
        left=0,
        right="post_car",
        height=0.72,
        color="bar_color",
        alpha=0.88,
        source=source,
        legend_field="sample_label",
    )
    chart.add_tools(
        hover_class(
            renderers=[bars],
            tooltips=[
                ("Company", "@company_name"),
                ("Ticker", "@market_data_ticker"),
                ("Benchmark", "@benchmark_ticker"),
                ("Role", "@role_category"),
                ("Sample", "@sample_label"),
                ("Pre-period CAR", "@pre_car{0.00%}"),
                ("Post-event CAR", "@post_car{0.00%}"),
                ("Company total return", "@post_company_total_return{0.00%}"),
                ("Benchmark total return", "@post_benchmark_total_return{0.00%}"),
                ("Post daily mean", "@post_mean_daily_abnormal_return{0.000%}"),
            ],
        )
    )
    chart.add_layout(
        span_class(location=0, dimension="height", line_color="#666666")
    )
    chart.xaxis.formatter = formatter_class(format="0.0%")
    chart.yaxis.major_label_text_font_size = "8pt"
    _style_chart(chart)
    return chart, source


def _selected_paths_chart(
    detail,
    palette_class,
    source_class,
    hover_class,
    legend_class,
    formatter_class,
    figure_class,
):
    selected = detail[
        detail["is_confirmatory"].map(_boolean_value)
        | (detail["sample_group"] == "POST_HOC_EXPLORATORY")
    ].copy()
    selected = selected[selected["phase"] == "POST_EVENT"].sort_values(
        ["company_name", "market_date"]
    )
    chart = figure_class(
        title="Long-horizon post-event CAR: confirmatory companies and VW",
        x_axis_type="datetime",
        x_axis_label="Market date",
        y_axis_label="Post-event CAR",
        width=1050,
        height=700,
        sizing_mode="stretch_width",
        tools="pan,wheel_zoom,box_zoom,reset,save",
    )
    legend_items = []
    path_renderers = []
    path_renderer_company_ids = []
    palette = palette_class[10]

    for index, (company_id, company) in enumerate(
        selected.groupby("company_id", sort=True)
    ):
        company_name = str(company["company_name"].iloc[0])
        ticker = str(company["market_data_ticker"].iloc[0])
        source = source_class(company)
        color = palette[index % len(palette)]
        line = chart.line(
            "market_date",
            "phase_car",
            source=source,
            color=color,
            line_width=2.4,
        )
        points = chart.scatter(
            "market_date",
            "phase_car",
            source=source,
            color=color,
            size=5,
        )
        path_renderers.extend((line, points))
        path_renderer_company_ids.extend((company_id, company_id))
        legend_items.append((ticker, [line, points]))
        chart.add_tools(
            hover_class(
                renderers=[points],
                tooltips=[
                    ("Company", company_name),
                    ("Date", "@market_date{%F}"),
                    ("Post-event CAR", "@phase_car{0.00%}"),
                    ("Daily abnormal return", "@abnormal_return{0.00%}"),
                ],
                formatters={"@market_date": "datetime"},
            )
        )

    chart.yaxis.formatter = formatter_class(format="0.0%")
    legend = legend_class(
        items=legend_items,
        title="Companies (ticker)",
        location="top_left",
        label_text_font_size="9pt",
        click_policy="hide",
        orientation="horizontal",
        ncols=3,
    )
    chart.add_layout(legend, "below")
    _style_chart(chart, legend=False)
    return chart, path_renderers, path_renderer_company_ids


def _dashboard_company_data(companies):
    result = companies.copy()
    result["shift_label"] = result["position_shift"].map(_shift_label)
    result["point_color"] = result["position_shift"].map(_SHIFT_COLORS)
    result["bar_color"] = result["sample_group"].map(
        lambda value: _SAMPLE_STYLES.get(
            value,
            ("#5D6D7E", "dotdash", "diamond"),
        )[0]
    )
    result["sample_label"] = result["sample_group"].map(_sample_label)
    result["axis_label"] = result["market_data_ticker"].astype(str)

    duplicated = result["axis_label"].duplicated(keep=False)
    result.loc[duplicated, "axis_label"] = (
        result.loc[duplicated, "axis_label"]
        + " · "
        + result.loc[duplicated, "company_id"].astype(str)
    )
    return result


def _detail_with_company_dimensions(detail, companies):
    dimensions = companies[
        ["company_id", "role_category", "market_data_ticker"]
    ].drop_duplicates("company_id")
    result = detail.drop(
        columns=["role_category", "market_data_ticker"],
        errors="ignore",
    ).merge(
        dimensions,
        on="company_id",
        how="left",
        validate="many_to_one",
    )

    if result[["role_category", "market_data_ticker"]].isna().any().any():
        raise ValueError("Company dimensions are missing for detail rows")

    return result


def _filter_controls(
    companies,
    detail,
    position_source,
    shift_source,
    ranking_source,
    shift_chart,
    ranking_chart,
    shift_range,
    ranking_range,
    sample_sources,
    sample_groups,
    path_renderers,
    path_renderer_company_ids,
    source_class,
    select_class,
    button_class,
    div_class,
    custom_js_class,
    column_class,
    row_class,
):
    all_companies = source_class(companies)
    all_detail = source_class(
        detail[detail["phase"] == "POST_EVENT"].copy()
    )
    sample_options = [("ALL", "All sample groups")] + [
        (value, _sample_label(value)) for value in _sample_order_from_values(
            companies["sample_group"]
        )
    ]
    role_options = [("ALL", "All company roles")] + [
        (value, value)
        for value in sorted(companies["role_category"].astype(str).unique())
    ]
    company_options = [("ALL", "All companies")] + [
        (
            str(row.company_id),
            f"{row.company_name} ({row.market_data_ticker})",
        )
        for row in companies.sort_values("company_name").itertuples()
    ]
    sample_filter = select_class(
        title="Sample classification",
        value="ALL",
        options=sample_options,
        sizing_mode="stretch_width",
    )
    role_filter = select_class(
        title="Company role",
        value="ALL",
        options=role_options,
        sizing_mode="stretch_width",
    )
    company_filter = select_class(
        title="Company",
        value="ALL",
        options=company_options,
        sizing_mode="stretch_width",
    )
    reset_button = button_class(
        label="Reset filters",
        button_type="default",
        width=150,
        height=40,
    )
    for widget in (sample_filter, role_filter, company_filter):
        style_dark_select(widget)
    style_dark_button(reset_button)
    filter_status = div_class(
        text=(
            f"<p style='margin:2px 0 0;font-size:12px'><b>{len(companies)}"
            f"</b> of {len(companies)} companies displayed. Filters update "
            "all tabs; tap or hover over marks for exact values.</p>"
        ),
        sizing_mode="stretch_width",
    )
    callback = custom_js_class(
        args={
            "all_companies": all_companies,
            "all_detail": all_detail,
            "position_source": position_source,
            "shift_source": shift_source,
            "ranking_source": ranking_source,
            "shift_chart": shift_chart,
            "ranking_chart": ranking_chart,
            "shift_range": shift_range,
            "ranking_range": ranking_range,
            "sample_sources": sample_sources,
            "sample_groups": sample_groups,
            "path_renderers": path_renderers,
            "path_renderer_company_ids": path_renderer_company_ids,
            "sample_filter": sample_filter,
            "role_filter": role_filter,
            "company_filter": company_filter,
            "filter_status": filter_status,
        },
        code=_filter_callback_code(),
    )

    for widget in (sample_filter, role_filter, company_filter):
        widget.js_on_change("value", callback)

    reset_callback = custom_js_class(
        args={
            "sample_filter": sample_filter,
            "role_filter": role_filter,
            "company_filter": company_filter,
        },
        code=(
            "sample_filter.value = 'ALL';\n"
            "role_filter.value = 'ALL';\n"
            "company_filter.value = 'ALL';\n"
            "sample_filter.change.emit();"
        ),
    )
    reset_button.js_on_click(reset_callback)
    controls = row_class(
        sample_filter,
        role_filter,
        company_filter,
        reset_button,
        spacing=12,
        sizing_mode="stretch_width",
        stylesheets=[DARK_FILTER_ROW_STYLESHEET],
    )
    panel = column_class(
        div_class(
            text=(
                "<h3 style='margin:0 0 4px'>Filter dashboard data</h3>"
                "<p style='margin:0 0 6px;font-size:12px'>Filters are "
                "combined. CAAR is recalculated for matching companies; "
                "ranks and percentiles remain based on the full 46-company "
                "universe. Select one company for the clearest mobile "
                "comparison.</p>"
            ),
            sizing_mode="stretch_width",
        ),
        controls,
        filter_status,
        sizing_mode="stretch_width",
        spacing=5,
        margin=(0, 0, 12, 0),
    )
    return panel, callback, reset_callback


def _filter_callback_code():
    return """
const companyData = all_companies.data;

// If the person picks a specific company, align the other two filters
// to that company's own sample group and role instead of leaving them
// free to contradict the selection (e.g. "Airbus SE" together with
// "Exploratory" and "Transport & Logistics", which together match zero
// companies since Airbus is CONFIRMATORY / Defence Contractor). This
// runs only when the company dropdown itself triggered the callback, so
// it does not fight the person's own sample/role choices otherwise.
if (typeof cb_obj !== "undefined" && cb_obj === company_filter
    && company_filter.value !== "ALL") {
    const selectedIndex = companyData.company_id.indexOf(
        company_filter.value
    );

    if (selectedIndex !== -1) {
        const matchedSample = companyData.sample_group[selectedIndex];
        const matchedRole = companyData.role_category[selectedIndex];

        if (sample_filter.value !== matchedSample) {
            sample_filter.value = matchedSample;
        }

        if (role_filter.value !== matchedRole) {
            role_filter.value = matchedRole;
        }
    }
}

const total = companyData.company_id.length;
const matching = [];
const selectedIds = new Set();

for (let index = 0; index < total; index++) {
    const sampleMatches = sample_filter.value === "ALL"
        || companyData.sample_group[index] === sample_filter.value;
    const roleMatches = role_filter.value === "ALL"
        || companyData.role_category[index] === role_filter.value;
    const companyMatches = company_filter.value === "ALL"
        || companyData.company_id[index] === company_filter.value;

    if (sampleMatches && roleMatches && companyMatches) {
        matching.push(index);
        selectedIds.add(companyData.company_id[index]);
    }
}

function subset(indices) {
    const output = {};
    for (const [column, values] of Object.entries(companyData)) {
        output[column] = indices.map((index) => values[index]);
    }
    return output;
}

const shiftIndices = matching.slice().sort((left, right) => {
    const difference = companyData.rank_change[left]
        - companyData.rank_change[right];
    return difference !== 0
        ? difference
        : String(companyData.company_name[left]).localeCompare(
            String(companyData.company_name[right])
        );
});
const rankingIndices = matching.slice().sort((left, right) => {
    const difference = companyData.post_car[left] - companyData.post_car[right];
    return difference !== 0
        ? difference
        : String(companyData.company_name[left]).localeCompare(
            String(companyData.company_name[right])
        );
});

position_source.data = subset(matching);
shift_source.data = subset(shiftIndices);
ranking_source.data = subset(rankingIndices);
shift_range.factors = shiftIndices.map(
    (index) => companyData.axis_label[index]
);
ranking_range.factors = rankingIndices.map(
    (index) => companyData.axis_label[index]
);
const sharedChartHeight = window.innerWidth <= 600 ? 560 : 700;
shift_chart.height = sharedChartHeight;
ranking_chart.height = sharedChartHeight;

for (let index = 0; index < path_renderers.length; index++) {
    path_renderers[index].visible = selectedIds.has(
        path_renderer_company_ids[index]
    );
}

const detailData = all_detail.data;
const hasOls = Object.prototype.hasOwnProperty.call(
    detailData,
    "market_model_abnormal_return"
);

for (let groupIndex = 0; groupIndex < sample_groups.length; groupIndex++) {
    const group = sample_groups[groupIndex];
    const sums = new Map();
    const counts = new Map();
    const olsSums = new Map();
    const olsCounts = new Map();

    for (let index = 0; index < detailData.company_id.length; index++) {
        if (!selectedIds.has(detailData.company_id[index])) {
            continue;
        }
        if (detailData.sample_group[index] !== group) {
            continue;
        }

        const day = Number(detailData.relative_trading_day[index]);
        const abnormalReturn = Number(detailData.abnormal_return[index]);
        sums.set(day, (sums.get(day) || 0) + abnormalReturn);
        counts.set(day, (counts.get(day) || 0) + 1);

        if (hasOls) {
            const olsReturn = Number(
                detailData.market_model_abnormal_return[index]
            );
            // Some companies have no OLS value (insufficient pre-event
            // estimation window). They still count for the naive AAR
            // above, but must not silently pull the OLS average toward
            // zero, so they are skipped here rather than treated as 0.
            if (Number.isFinite(olsReturn)) {
                olsSums.set(day, (olsSums.get(day) || 0) + olsReturn);
                olsCounts.set(day, (olsCounts.get(day) || 0) + 1);
            }
        }
    }

    const days = Array.from(sums.keys()).sort((left, right) => left - right);
    const aar = [];
    const caar = [];
    const companyCount = [];
    const olsAar = [];
    const olsCaar = [];
    let cumulative = 0;
    let olsCumulative = 0;

    for (const day of days) {
        const count = counts.get(day);
        const average = sums.get(day) / count;
        cumulative += average;
        aar.push(average);
        caar.push(cumulative);
        companyCount.push(count);

        if (hasOls) {
            const olsCount = olsCounts.get(day) || 0;
            if (olsCount > 0) {
                const olsAverage = olsSums.get(day) / olsCount;
                olsCumulative += olsAverage;
                olsAar.push(olsAverage);
                olsCaar.push(olsCumulative);
            } else {
                // No company in the current filter selection has an OLS
                // value for this day; keep the CAAR line intact by
                // carrying the cumulative value forward instead of
                // dropping the point or resetting it to zero.
                olsAar.push(null);
                olsCaar.push(olsCumulative);
            }
        }
    }

    const nextData = {
        relative_trading_day: days,
        aar: aar,
        caar: caar,
        company_count: companyCount,
    };

    if (hasOls) {
        nextData.ols_aar = olsAar;
        nextData.ols_caar = olsCaar;
    }

    sample_sources[groupIndex].data = nextData;
    sample_sources[groupIndex].change.emit();
}

position_source.change.emit();
shift_source.change.emit();
ranking_source.change.emit();
const emptyNotice = matching.length === 0
    ? " No companies match this combination of filters \u2014 try Reset filters."
    : "";
filter_status.text = `<p style="margin:2px 0 0;font-size:12px"><b>${matching.length}</b> of ${total} companies displayed. Filters update all tabs; tap or hover over marks for exact values.${emptyNotice}</p>`;
"""


def _responsive_callback_code():
    return """
function applyResponsiveLayout() {
    const narrowScreen = window.innerWidth <= 600;
    const sharedChartHeight = narrowScreen ? 560 : 700;

    sample_chart.height = sharedChartHeight;
    position_chart.height = sharedChartHeight;
    selected_chart.height = sharedChartHeight;
    shift_chart.height = sharedChartHeight;
    ranking_chart.height = sharedChartHeight;

    for (const chart of [
        sample_chart,
        position_chart,
        shift_chart,
        ranking_chart,
        selected_chart,
    ]) {
        chart.toolbar_location = narrowScreen ? "below" : "right";
    }
}

applyResponsiveLayout();
window.addEventListener("resize", applyResponsiveLayout, {passive: true});
"""


def _load_detail(file_path):
    data = _load_csv(file_path, _DETAIL_COLUMNS, "Full-period detail")
    return _typed_data(
        data,
        date_columns=("event_calendar_date", "market_date"),
        numeric_columns=(
            "relative_trading_day",
            "abnormal_return",
            "phase_car",
        ),
    )


def _load_companies(file_path):
    data = _load_csv(file_path, _COMPANY_COLUMNS, "Company positioning")
    result = _typed_data(
        data,
        date_columns=(
            "event_calendar_date",
            "analysis_start_date",
            "analysis_end_date",
        ),
        numeric_columns=(
            "pre_car",
            "post_car",
            "pre_company_total_return",
            "pre_benchmark_total_return",
            "post_company_total_return",
            "post_benchmark_total_return",
            "pre_mean_daily_abnormal_return",
            "post_mean_daily_abnormal_return",
            "pre_rank",
            "post_rank",
            "rank_change",
            "pre_percentile",
            "post_percentile",
            "percentile_change",
        ),
    )

    if result.duplicated(["event_id", "company_id"]).any():
        raise ValueError(
            "Company-positioning CSV contains duplicate event-company rows"
        )

    return result


def _load_samples(file_path):
    data = _load_csv(file_path, _SAMPLE_COLUMNS, "Sample summary")
    data = _typed_data(
        data,
        date_columns=("event_calendar_date",),
        numeric_columns=(
            "relative_trading_day",
            "company_count",
            "aar",
            "caar",
        ),
    )

    # Optional: present only when the underlying panel carries the OLS
    # market-model column (src.services.ols_market_model). NaN is valid
    # here (insufficient estimation window for some companies), so this
    # is coerced but never required or validated against NaN.
    for optional_column in ("ols_aar", "ols_caar", "ols_aar_standard_error"):
        if optional_column in data.columns:
            data[optional_column] = pd.to_numeric(
                data[optional_column], errors="coerce"
            )

    return data


def _load_csv(file_path, required_columns, label):
    path = Path(file_path)

    if not path.is_file():
        raise FileNotFoundError(f"{label} CSV not found: {path}")

    data = pd.read_csv(path)
    missing = required_columns - set(data.columns)

    if missing:
        raise ValueError(
            f"{label} CSV is missing required columns: "
            + ", ".join(sorted(missing))
        )

    if data.empty:
        raise ValueError(f"{label} CSV must not be empty")

    return data


def _typed_data(data, date_columns, numeric_columns):
    result = data.copy()

    for column in date_columns:
        result[column] = pd.to_datetime(result[column], errors="coerce")

        if result[column].isna().any():
            raise ValueError(f"{column} must contain only valid dates")

    for column in numeric_columns:
        result[column] = pd.to_numeric(result[column], errors="coerce")

        if result[column].isna().any():
            raise ValueError(f"{column} must contain only numeric values")

    return result


def _select_event(data_frames, event_id):
    identifiers = set.intersection(
        *(set(frame["event_id"].astype(str)) for frame in data_frames)
    )

    if event_id is not None:
        if event_id not in identifiers:
            raise ValueError(f"Event not found in every input: {event_id}")

        return event_id

    if len(identifiers) != 1:
        raise ValueError(
            "Inputs contain multiple or inconsistent events; use --event-id"
        )

    return next(iter(identifiers))


def _event_rows(data, event_id):
    return data[data["event_id"].astype(str) == event_id].copy()


def _validate_inputs(detail, companies, samples):
    if set(detail["company_id"]) != set(companies["company_id"]):
        raise ValueError("Detail and company files use different companies")

    if set(detail["sample_group"]) != set(samples["sample_group"]):
        raise ValueError("Detail and sample files use different sample groups")

    if set(detail["phase"]) != {"PRE_EVENT", "POST_EVENT"}:
        raise ValueError("Detail CSV must contain PRE_EVENT and POST_EVENT")


def _sample_order(samples):
    preferred = (
        "CONFIRMATORY",
        "EXPLORATORY",
        "POST_HOC_EXPLORATORY",
    )
    available = set(samples["sample_group"])
    return [item for item in preferred if item in available] + sorted(
        available - set(preferred)
    )


def _sample_order_from_values(values):
    frame = pd.DataFrame({"sample_group": list(values)})
    return _sample_order(frame)


def _month_axis_values(detail):
    post = detail[detail["phase"] == "POST_EVENT"].copy()

    if post.empty:
        raise ValueError("Detail CSV contains no post-event observations")

    representative_dates = (
        post.groupby("relative_trading_day", sort=True)["market_date"]
        .median()
        .reset_index()
    )
    representative_dates["month"] = representative_dates[
        "market_date"
    ].dt.to_period("M")
    ticks = []
    labels = {}

    for month, rows in representative_dates.groupby("month", sort=True):
        midpoint = float(rows["relative_trading_day"].median())
        closest_index = (
            rows["relative_trading_day"] - midpoint
        ).abs().idxmin()
        tick = int(rows.loc[closest_index, "relative_trading_day"])
        ticks.append(tick)
        labels[tick] = month.to_timestamp().strftime("%b %Y")

    return ticks, labels


def _sample_label(value):
    return {
        "CONFIRMATORY": "Confirmatory",
        "EXPLORATORY": "Exploratory",
        "POST_HOC_EXPLORATORY": "Post-hoc: Volkswagen",
    }.get(value, str(value).replace("_", " ").title())


def _interpretation_guide_html():
    return (
        "<div style='border:1px solid #344457;border-radius:8px;"
        "padding:10px 14px;margin:0 0 12px;background:#151E29'>"
        "<h3 style='margin:0 0 7px'>How to read this dashboard</h3>"
        "<div style='display:grid;grid-template-columns:repeat(auto-fit,"
        "minmax(250px,1fr));gap:4px 22px;font-size:12px;line-height:1.45'>"
        "<div><b>Confirmatory (n=8):</b> companies selected before the "
        "results were evaluated; this is the pre-specified primary "
        "sample.</div>"
        "<div><b>Exploratory (n=37):</b> additional companies used to "
        "identify broader patterns. Results are hypothesis-generating, "
        "not independent confirmation.</div>"
        "<div><b>Post-hoc exploratory (Volkswagen):</b> added after an "
        "interesting signal was observed and therefore reported "
        "separately because selection bias is possible.</div>"
        "<div><b>Abnormal return (AR):</b> company return minus its "
        "configured benchmark return. A positive value means relative "
        "outperformance, even if the share price itself fell.</div>"
        "<div><b>CAR:</b> arithmetic sum of one company's daily abnormal "
        "returns over the stated period.</div>"
        "<div><b>AAR / CAAR:</b> AAR is the group-average abnormal return "
        "on one relative trading day; CAAR accumulates those averages "
        "from the event onward.</div>"
        "<div><b>Benchmark / proxy:</b> the configured market index removes "
        "broad local-market movement. A disclosed proxy is a substitute "
        "used when the intended index is unavailable.</div>"
        "<div><b>Capital-market position:</b> relative rank within these "
        "46 companies based on mean daily abnormal return; it is not "
        "product-market share or competitive power.</div>"
        "<div><b>Time scale:</b> day 0 is each company's first tradable day "
        "after the event. Calendar-month labels use the median observed "
        "market date across the sample.</div>"
        "<div><b>Interpretation limit:</b> long-horizon results describe "
        "association and relative performance; they do not establish "
        "that the conflict caused the movements.</div>"
        "</div></div>"
    )


def _shift_label(value):
    return {
        "IMPROVED_QUARTILE": "Improved quartile",
        "UNCHANGED_QUARTILE": "Unchanged quartile",
        "WEAKENED_QUARTILE": "Weakened quartile",
    }.get(value, str(value).replace("_", " ").title())


def _boolean_value(value):
    if isinstance(value, bool):
        return value

    normalized = str(value).strip().casefold()

    if normalized in {"true", "1", "yes"}:
        return True

    if normalized in {"false", "0", "no"}:
        return False

    raise ValueError(f"Invalid is_confirmatory value: {value}")


def _style_chart(chart, legend=True):
    if legend and len(chart.legend) > 0:
        chart.legend.location = "top_left"
        chart.legend.click_policy = "hide"
        chart.legend.label_text_font_size = "10pt"

    chart.grid.grid_line_alpha = 0.2
    chart.toolbar.logo = None
    chart.toolbar.autohide = True


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Create the BLACK DOVES long-horizon market-position dashboard."
        )
    )
    parser.add_argument(
        "--detail-file",
        type=Path,
        default=Path(
            "data/analysis/market_position_full_period_detail.csv"
        ),
    )
    parser.add_argument(
        "--company-file",
        type=Path,
        default=Path(
            "data/analysis/market_position_company_summary.csv"
        ),
    )
    parser.add_argument(
        "--sample-file",
        type=Path,
        default=Path(
            "data/analysis/market_position_sample_aar_caar.csv"
        ),
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        default=Path(
            "output/black_doves_long_horizon_market_position.html"
        ),
    )
    parser.add_argument(
        "--logo",
        type=Path,
        default=Path("assets/black_doves_logo.png"),
    )
    parser.add_argument("--event-id")
    return parser


def main(arguments=None):
    parser = build_parser()
    options = parser.parse_args(arguments)

    try:
        output_path = create_market_position_dashboard(
            detail_file=options.detail_file,
            company_file=options.company_file,
            sample_file=options.sample_file,
            output_path=options.output_file,
            logo_path=options.logo,
            event_id=options.event_id,
        )
    except (FileNotFoundError, TypeError, ValueError) as error:
        parser.error(str(error))

    print("\nBLACK DOVES long-horizon dashboard completed.")
    print(f"Chart: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
