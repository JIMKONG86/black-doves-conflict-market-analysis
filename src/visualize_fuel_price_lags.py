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
    style_dark_select,
    style_dark_tabs,
)


_TIMELINE_COLUMNS = {
    "observation_date",
    "series_id",
    "series_label",
    "product",
    "tax_basis",
    "value",
    "indexed_value",
    "unit",
}

_WEEKLY_COLUMNS = {
    "fuel_observation_date",
    "petrol_with_tax_eur_per_liter",
    "petrol_without_tax_eur_per_liter",
    "diesel_with_tax_eur_per_liter",
    "diesel_without_tax_eur_per_liter",
    "brent_weekly_pct_change",
    "petrol_with_tax_eur_per_liter_pct_change",
    "petrol_without_tax_eur_per_liter_pct_change",
    "diesel_with_tax_eur_per_liter_pct_change",
    "diesel_without_tax_eur_per_liter_pct_change",
}

_LAG_COLUMNS = {
    "product",
    "tax_basis",
    "lag_weeks",
    "observations",
    "pearson_correlation",
    "pearson_p_value",
    "spearman_correlation",
    "spearman_p_value",
    "status",
}

_CONFLICT_COLUMNS = {
    "week_end_date",
    "country_name",
    "country_code",
    "total_events",
    "total_fatalities",
    "strike_events",
    "strike_fatalities",
    "air_drone_strike_events",
    "air_drone_strike_fatalities",
    "shelling_artillery_missile_events",
    "shelling_artillery_missile_fatalities",
    "violence_against_civilians_events",
    "violence_against_civilians_fatalities",
}

_CONFLICT_METRICS = {
    "strike_events": "All strike events",
    "strike_fatalities": "Strike fatalities",
    "air_drone_strike_events": "Air/drone strike events",
    "air_drone_strike_fatalities": "Air/drone strike fatalities",
    "shelling_artillery_missile_events": (
        "Shelling/artillery/missile events"
    ),
    "shelling_artillery_missile_fatalities": (
        "Shelling/artillery/missile fatalities"
    ),
    "violence_against_civilians_events": (
        "Violence against civilians (events)"
    ),
    "violence_against_civilians_fatalities": (
        "Violence against civilians (fatalities)"
    ),
    "total_fatalities": "All conflict fatalities (ACLED total)",
}

_CENTCOM_COLUMNS = {
    "source_release_id",
    "event_date",
    "publication_date",
    "initiator_country_code",
    "affected_country_code",
    "operation_day_count",
    "verification_status",
    "include_in_core_series",
    "counting_unit",
    "title",
    "source_id",
    "source_url",
}

_CENTCOM_SOURCE_ID = "US_CENTCOM_PUBLIC_RELEASES"
_CENTCOM_COUNTING_UNIT = "official_release_confirmed_operation_day"

_COLORS = {
    "BRENT": "#F3F6FA",
    "PETROL_WITH_TAX": "#55B6E8",
    "PETROL_WITHOUT_TAX": "#9AD9F5",
    "DIESEL_WITH_TAX": "#FF8A65",
    "DIESEL_WITHOUT_TAX": "#F2C14E",
}

_MOBILE_TEMPLATE = DARK_BOKEH_HTML_TEMPLATE


def create_fuel_price_lag_dashboard(
    timeline_file,
    weekly_file,
    lag_file,
    output_path,
    conflict_file=Path("data/analysis/weekly_conflict_features.csv"),
    centcom_file=Path("data/validated/centcom_us_strike_operation_days.csv"),
    event_date="2026-02-28",
    logo_path=None,
):
    from bokeh.core.templates import get_env
    from bokeh.events import DocumentReady
    from bokeh.layouts import column, row
    from bokeh.models import (
        ColumnDataSource,
        CustomJS,
        Div,
        HoverTool,
        NumeralTickFormatter,
        Select,
        Span,
        TabPanel,
        Tabs,
    )
    from bokeh.plotting import figure, save
    from bokeh.resources import INLINE

    activate_black_doves_theme()

    timeline = _load_csv(
        timeline_file, _TIMELINE_COLUMNS, ("observation_date",)
    )
    weekly = _load_csv(
        weekly_file, _WEEKLY_COLUMNS, ("fuel_observation_date",)
    )
    _validate_tax_price_order(weekly)
    lags = _load_csv(lag_file, _LAG_COLUMNS, ())
    lags = lags[lags["status"] == "ok"].copy()
    if lags.empty:
        raise ValueError("Lag results contain no valid associations")
    conflict = _load_conflict(conflict_file)
    centcom = _load_centcom(centcom_file)

    event = pd.to_datetime(event_date, errors="coerce")
    if pd.isna(event):
        raise ValueError("event_date must be a valid date")

    output_path = Path(output_path)
    if output_path.suffix.casefold() != ".html":
        raise ValueError("Fuel-price dashboard output must use .html")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    analysis_start = timeline["observation_date"].min()
    analysis_end = weekly["fuel_observation_date"].max()
    conflict = conflict[
        conflict["week_end_date"].between(analysis_start, analysis_end)
    ].reset_index(drop=True)
    if conflict.empty:
        raise ValueError(
            "Conflict data does not overlap the energy-price period"
        )
    centcom = centcom[
        centcom["event_date"].between(analysis_start, analysis_end)
    ].reset_index(drop=True)
    if centcom.empty:
        raise ValueError(
            "Confirmed in-scope CENTCOM data does not overlap the "
            "energy-price period"
        )

    (
        conflict_chart,
        conflict_renderers,
        conflict_countries,
        conflict_sources,
    ) = _conflict_chart(
        conflict,
        event,
        ColumnDataSource,
        HoverTool,
        Span,
        figure,
    )
    centcom_weekly = _aggregate_centcom_weeks(
        centcom,
        conflict["week_end_date"].min(),
        conflict["week_end_date"].max(),
    )
    centcom_chart, centcom_renderers = _centcom_chart(
        centcom_weekly,
        event,
        ColumnDataSource,
        HoverTool,
        Span,
        figure,
        conflict_chart.x_range,
    )

    price_chart, price_renderers, price_dimensions = _price_chart(
        timeline, event, ColumnDataSource, HoverTool, Span, figure
    )
    (
        fuel_level_chart,
        fuel_level_renderers,
        fuel_level_dimensions,
    ) = _fuel_level_chart(
        weekly,
        event,
        ColumnDataSource,
        HoverTool,
        Span,
        figure,
    )
    change_chart, change_renderers, change_dimensions = _change_chart(
        weekly,
        event,
        ColumnDataSource,
        HoverTool,
        NumeralTickFormatter,
        Span,
        figure,
    )
    (
        lag_chart,
        lag_renderers,
        lag_dimensions,
        lag_sources,
    ) = _lag_chart(
        lags,
        ColumnDataSource,
        HoverTool,
        NumeralTickFormatter,
        figure,
    )
    product_filter = Select(
        title="Fuel product",
        value="ALL",
        options=[
            ("ALL", "Petrol + diesel"),
            ("PETROL", "Petrol Euro 95"),
            ("DIESEL", "Diesel"),
        ],
        sizing_mode="stretch_width",
    )
    tax_filter = Select(
        title="Price basis",
        value="BOTH",
        options=[
            ("BOTH", "Including + excluding taxes"),
            ("WITH_TAX", "Including taxes"),
            ("WITHOUT_TAX", "Excluding taxes"),
        ],
        sizing_mode="stretch_width",
    )
    correlation_filter = Select(
        title="Lag statistic",
        value="spearman",
        options=[
            ("spearman", "Spearman correlation"),
            ("pearson", "Pearson correlation"),
        ],
        sizing_mode="stretch_width",
    )
    country_filter = Select(
        title="Conflict role / series",
        value="ALL",
        options=[
            ("ALL", "Iran + Israel + U.S. initiator"),
            ("IR", "Iran (affected; ACLED)"),
            ("IL", "Israel (affected; ACLED)"),
            ("US", "United States (initiator; CENTCOM)"),
        ],
        sizing_mode="stretch_width",
    )
    conflict_metric_filter = Select(
        title="Conflict metric",
        value="strike_events",
        options=list(_CONFLICT_METRICS.items()),
        sizing_mode="stretch_width",
    )
    filters = (
        product_filter,
        tax_filter,
        correlation_filter,
        country_filter,
        conflict_metric_filter,
    )
    for control in filters:
        style_dark_select(control)
    all_renderers = (
        fuel_level_renderers
        + price_renderers
        + change_renderers
        + lag_renderers
    )
    all_dimensions = (
        fuel_level_dimensions
        + price_dimensions
        + change_dimensions
        + lag_dimensions
    )
    for renderer, (product, tax_basis) in zip(
        all_renderers, all_dimensions
    ):
        renderer.visible = (
            product == "ALL"
            or tax_basis in {"WITH_TAX", "WITHOUT_TAX"}
        )
    renderer_groups = {
        "brent": [],
        "petrol_with_tax": [],
        "petrol_without_tax": [],
        "diesel_with_tax": [],
        "diesel_without_tax": [],
    }
    for renderer, (product, tax_basis) in zip(
        all_renderers, all_dimensions
    ):
        if product == "ALL":
            renderer_groups["brent"].append(renderer)
        else:
            key = f"{product.lower()}_{tax_basis.lower()}"
            renderer_groups[key].append(renderer)

    visibility_callback = CustomJS(
        args={
            "product_filter": product_filter,
            "tax_filter": tax_filter,
            "brent": renderer_groups["brent"],
            "petrol_with_tax": renderer_groups["petrol_with_tax"],
            "petrol_without_tax": renderer_groups["petrol_without_tax"],
            "diesel_with_tax": renderer_groups["diesel_with_tax"],
            "diesel_without_tax": renderer_groups["diesel_without_tax"],
        },
        code="""
          const product = product_filter.value;
          const tax = tax_filter.value;
          const setVisible = (items, visible) => {
            for (const item of items) item.visible = visible;
          };
          setVisible(brent, true);
          setVisible(
            petrol_with_tax,
            product !== "DIESEL" &&
              (tax === "WITH_TAX" || tax === "BOTH")
          );
          setVisible(
            petrol_without_tax,
            product !== "DIESEL" &&
              (tax === "WITHOUT_TAX" || tax === "BOTH")
          );
          setVisible(
            diesel_with_tax,
            product !== "PETROL" &&
              (tax === "WITH_TAX" || tax === "BOTH")
          );
          setVisible(
            diesel_without_tax,
            product !== "PETROL" &&
              (tax === "WITHOUT_TAX" || tax === "BOTH")
          );
        """,
    )
    statistic_callback = CustomJS(
        args={
            "lag_sources": lag_sources,
            "correlation_filter": correlation_filter,
        },
        code="""
          const prefix = correlation_filter.value;
          for (const source of lag_sources) {
            source.data.correlation = source.data[prefix + "_correlation"].slice();
            source.data.p_value = source.data[prefix + "_p_value"].slice();
            source.change.emit();
          }
        """,
    )
    for control in (product_filter, tax_filter):
        control.js_on_change("value", visibility_callback)
    correlation_filter.js_on_change("value", statistic_callback)

    conflict_callback = CustomJS(
        args={
            "country_filter": country_filter,
            "metric_filter": conflict_metric_filter,
            "renderers": conflict_renderers,
            "countries": conflict_countries,
            "sources": conflict_sources,
            "centcom_renderers": centcom_renderers,
            "metric_labels": _CONFLICT_METRICS,
            "metric_axis": conflict_chart.yaxis[0],
        },
        code="""
          const country = country_filter.value;
          for (let i = 0; i < renderers.length; i++) {
            renderers[i].visible = country !== "US" &&
                                   (country === "ALL" ||
                                   countries[i] === country);
          }
          for (const renderer of centcom_renderers) {
            renderer.visible = country === "ALL" || country === "US";
          }
          const metric = metric_filter.value;
          const label = metric_labels[metric];
          for (const source of sources) {
            source.data.metric_value = source.data[metric].slice();
            source.data.metric_label = Array(
              source.data[metric].length
            ).fill(label);
            source.change.emit();
          }
          metric_axis.axis_label = label + " per week";
        """,
    )
    country_filter.js_on_change("value", conflict_callback)
    conflict_metric_filter.js_on_change("value", conflict_callback)

    controls = column(
        Div(
            text=(
                "<h3 style='margin:0 0 4px'>Filters</h3>"
                "<p style='margin:0 0 8px;color:#A9B5C3;font-size:12px'>"
                "Energy controls apply to EUR/L, index, change and lag; "
                "conflict controls apply to the strike views. Brent remains "
                "the common reference series.</p>"
            ),
            sizing_mode="stretch_width",
        ),
        row(
            *filters,
            spacing=12,
            sizing_mode="stretch_width",
            stylesheets=[DARK_FILTER_ROW_STYLESHEET],
        ),
        sizing_mode="stretch_width",
    )
    scope = Div(
        text=(
            "<h2 style='margin:0 0 4px'>Conflict, Brent and German "
            "fuel-price transmission</h2>"
            f"<p style='margin:0 0 12px'>Conflict reference: "
            f"<b>{event.strftime('%d.%m.%Y')}</b> · "
            f"{weekly['fuel_observation_date'].min().strftime('%d.%m.%Y')}–"
            f"{weekly['fuel_observation_date'].max().strftime('%d.%m.%Y')} · "
            f"{len(weekly)} weekly observations</p>"
        ),
        sizing_mode="stretch_width",
    )
    guide = Div(
        text=_interpretation_html(lags, centcom),
        sizing_mode="stretch_width",
    )
    strike_panel = column(
        conflict_chart,
        centcom_chart,
        sizing_mode="stretch_width",
    )
    tabs = Tabs(
        tabs=[
            TabPanel(title="Strikes", child=strike_panel),
            TabPanel(title="EUR/L", child=fuel_level_chart),
            TabPanel(
                title="Index",
                child=column(
                    Div(
                        text=(
                            "<p style='margin:0 0 8px;padding:8px 10px;"
                            "border-left:3px solid #E9A23B;"
                            "background:#1B2735;font-size:12px;"
                            "color:#D8DEE9'><b>Read this before comparing "
                            "lines:</b> every series here is rebased to "
                            "100, so an untaxed line can show a "
                            "<i>higher index</i> than the taxed line "
                            "while its actual EUR/L price stays lower "
                            "the whole time \u2014 taxed fuel is always "
                            "more expensive in absolute terms (see the "
                            "EUR/L tab). This happens because the fixed "
                            "tax component dampens the percentage swing "
                            "of the taxed price relative to its untaxed, "
                            "crude-linked component.</p>"
                        ),
                        sizing_mode="stretch_width",
                    ),
                    price_chart,
                    sizing_mode="stretch_width",
                ),
            ),
            TabPanel(title="Changes", child=change_chart),
            TabPanel(title="Lag", child=lag_chart),
        ],
        active=2,
        sizing_mode="stretch_width",
    )
    style_dark_tabs(tabs)

    # Each filter only affects certain tabs (product/tax feed EUR/L, Index,
    # Changes and Lag; the lag statistic only feeds Lag; country/metric
    # only feed Strikes). Grey out and disable whichever filters cannot
    # change anything on the currently active tab, instead of leaving all
    # five looking equally interactive regardless of relevance.
    _TAB_FILTER_RELEVANCE = {
        "0": {"product": False, "tax": False, "correlation": False, "country": True, "metric": True},
        "1": {"product": True, "tax": True, "correlation": False, "country": False, "metric": False},
        "2": {"product": True, "tax": True, "correlation": False, "country": False, "metric": False},
        "3": {"product": True, "tax": True, "correlation": False, "country": False, "metric": False},
        "4": {"product": True, "tax": True, "correlation": True, "country": False, "metric": False},
    }
    initial_relevance = _TAB_FILTER_RELEVANCE[str(tabs.active)]
    product_filter.disabled = not initial_relevance["product"]
    tax_filter.disabled = not initial_relevance["tax"]
    correlation_filter.disabled = not initial_relevance["correlation"]
    country_filter.disabled = not initial_relevance["country"]
    conflict_metric_filter.disabled = not initial_relevance["metric"]

    tab_relevance_callback = CustomJS(
        args={
            "product_filter": product_filter,
            "tax_filter": tax_filter,
            "correlation_filter": correlation_filter,
            "country_filter": country_filter,
            "conflict_metric_filter": conflict_metric_filter,
            "relevance_by_tab": _TAB_FILTER_RELEVANCE,
        },
        code="""
          const state = relevance_by_tab[String(cb_obj.active)] || {};
          product_filter.disabled = !state.product;
          tax_filter.disabled = !state.tax;
          correlation_filter.disabled = !state.correlation;
          country_filter.disabled = !state.country;
          conflict_metric_filter.disabled = !state.metric;
        """,
    )
    tabs.js_on_change("active", tab_relevance_callback)

    dashboard = column(
        Div(text=_header_html(logo_path), sizing_mode="stretch_width"),
        scope,
        controls,
        tabs,
        guide,
        sizing_mode="stretch_width",
        max_width=1250,
    )
    responsive = CustomJS(
        args={
            "charts": [
                conflict_chart,
                centcom_chart,
                fuel_level_chart,
                price_chart,
                change_chart,
                lag_chart,
            ],
        },
        code="""
          if (window.innerWidth <= 600) {
            for (const chart of charts) {
              chart.toolbar_location = "above";
              chart.min_border_left = 48;
              chart.min_border_right = 12;
              for (const axis of chart.xaxis) {
                axis.major_label_text_font_size = "8pt";
                axis.axis_label_text_font_size = "9pt";
              }
              for (const axis of chart.yaxis) {
                axis.major_label_text_font_size = "8pt";
                axis.axis_label_text_font_size = "9pt";
              }
              for (const legend of chart.legend) {
                legend.label_text_font_size = "8pt";
                legend.location = "top_left";
              }
            }
          }
        """,
    )
    dashboard.js_on_event(DocumentReady, responsive)
    save(
        dashboard,
        filename=str(output_path),
        title="BLACK DOVES – Conflict, Brent and German Fuel Prices",
        resources=INLINE,
        template=get_env().from_string(_MOBILE_TEMPLATE),
    )
    return output_path


def _fuel_level_chart(
    weekly,
    event,
    source_class,
    hover_class,
    span_class,
    figure,
):
    definitions = [
        (
            "PETROL_WITH_TAX",
            "Petrol Euro 95 incl. taxes",
            "PETROL",
            "WITH_TAX",
            "petrol_with_tax_eur_per_liter",
        ),
        (
            "PETROL_WITHOUT_TAX",
            "Petrol Euro 95 excl. taxes",
            "PETROL",
            "WITHOUT_TAX",
            "petrol_without_tax_eur_per_liter",
        ),
        (
            "DIESEL_WITH_TAX",
            "Diesel incl. taxes",
            "DIESEL",
            "WITH_TAX",
            "diesel_with_tax_eur_per_liter",
        ),
        (
            "DIESEL_WITHOUT_TAX",
            "Diesel excl. taxes",
            "DIESEL",
            "WITHOUT_TAX",
            "diesel_without_tax_eur_per_liter",
        ),
    ]
    chart = figure(
        title="German fuel price levels in EUR per litre",
        x_axis_type="datetime",
        x_axis_label="German fuel observation date",
        y_axis_label="Price (EUR/litre)",
        height=570,
        sizing_mode="stretch_width",
        tools="pan,wheel_zoom,box_zoom,reset,save",
    )
    renderers = []
    dimensions = []
    for series_id, label, product, tax_basis, column_name in definitions:
        selected = weekly[["fuel_observation_date", column_name]].copy()
        selected = selected.rename(columns={column_name: "price_eur_litre"})
        source = source_class(selected)
        line = chart.line(
            "fuel_observation_date",
            "price_eur_litre",
            source=source,
            color=_COLORS[series_id],
            line_width=2.8,
            legend_label=label,
        )
        points = chart.scatter(
            "fuel_observation_date",
            "price_eur_litre",
            source=source,
            color=_COLORS[series_id],
            size=7,
        )
        chart.add_tools(
            hover_class(
                renderers=[points],
                tooltips=[
                    ("Series", label),
                    ("Monday", "@fuel_observation_date{%d.%m.%Y}"),
                    ("Price", "@price_eur_litre{0.000} EUR/litre"),
                ],
                formatters={"@fuel_observation_date": "datetime"},
            )
        )
        renderers.extend([line, points])
        dimensions.extend([(product, tax_basis), (product, tax_basis)])
    chart.add_layout(
        span_class(
            location=event.timestamp() * 1000,
            dimension="height",
            line_color="#B03A2E",
            line_dash="dashed",
            line_width=2,
        )
    )
    _style_chart(chart)
    return chart, renderers, dimensions


def _conflict_chart(
    conflict,
    event,
    source_class,
    hover_class,
    span_class,
    figure,
):
    chart = figure(
        title="Weekly conflict intensity by affected country (ACLED)",
        x_axis_type="datetime",
        x_axis_label="Week ending Saturday",
        y_axis_label="All strike events per week",
        height=350,
        sizing_mode="stretch_width",
        tools="pan,wheel_zoom,box_zoom,reset,save",
    )
    country_styles = {
        "IR": ("Iran", "#B03A2E", "circle"),
        "IL": ("Israel", "#8E44AD", "triangle"),
    }
    renderers = []
    renderer_countries = []
    sources = []

    for country_code in ("IR", "IL"):
        selected = conflict[
            conflict["country_code"] == country_code
        ].sort_values("week_end_date").copy()
        if selected.empty:
            continue
        label, color, marker = country_styles[country_code]
        selected["metric_value"] = selected["strike_events"]
        selected["metric_label"] = _CONFLICT_METRICS["strike_events"]
        source = source_class(selected)
        sources.append(source)
        line = chart.line(
            "week_end_date",
            "metric_value",
            source=source,
            color=color,
            line_width=2.8,
            legend_label=label,
        )
        points = chart.scatter(
            "week_end_date",
            "metric_value",
            source=source,
            color=color,
            marker=marker,
            size=8,
            legend_label=label,
        )
        chart.add_tools(
            hover_class(
                renderers=[points],
                tooltips=[
                    ("Country", label),
                    ("Week ending", "@week_end_date{%d.%m.%Y}"),
                    ("Metric", "@metric_label"),
                    ("Weekly value", "@metric_value{0,0}"),
                    ("Total events", "@total_events{0,0}"),
                    ("Total fatalities", "@total_fatalities{0,0}"),
                ],
                formatters={"@week_end_date": "datetime"},
            )
        )
        renderers.extend([line, points])
        renderer_countries.extend([country_code, country_code])

    chart.add_layout(
        span_class(
            location=event.timestamp() * 1000,
            dimension="height",
            line_color="#F3F6FA",
            line_dash="dashed",
            line_width=2,
        )
    )
    _style_chart(chart)
    return chart, renderers, renderer_countries, sources


def _centcom_chart(
    centcom_weekly,
    event,
    source_class,
    hover_class,
    span_class,
    figure,
    x_range,
):
    chart = figure(
        title=(
            "U.S. strike-operation days in the Iran core scope "
            "(initiator; CENTCOM)"
        ),
        x_axis_type="datetime",
        x_axis_label="Week ending Saturday",
        y_axis_label="Confirmed U.S. operation days per week",
        x_range=x_range,
        height=210,
        sizing_mode="stretch_width",
        tools="pan,wheel_zoom,box_zoom,reset,save",
    )
    source = source_class(centcom_weekly)
    line = chart.line(
        "week_end_date",
        "operation_day_count",
        source=source,
        color="#1F618D",
        line_width=2.8,
        legend_label="United States (initiator)",
    )
    points = chart.scatter(
        "week_end_date",
        "operation_day_count",
        source=source,
        color="#1F618D",
        marker="diamond",
        size=9,
        legend_label="United States (initiator)",
    )
    chart.add_tools(
        hover_class(
            renderers=[points],
            tooltips=[
                ("Role", "United States – initiator"),
                ("Week ending", "@week_end_date{%d.%m.%Y}"),
                ("Confirmed operation days", "@operation_day_count{0,0}"),
                ("Distinct releases", "@release_count{0,0}"),
                ("Affected countries", "@affected_countries"),
                ("Release titles", "@release_titles"),
            ],
            formatters={"@week_end_date": "datetime"},
        )
    )
    chart.add_layout(
        span_class(
            location=event.timestamp() * 1000,
            dimension="height",
            line_color="#F3F6FA",
            line_dash="dashed",
            line_width=2,
        )
    )
    chart.y_range.start = 0
    _style_chart(chart)
    return chart, [line, points]


def _price_chart(timeline, event, source_class, hover_class, span_class, figure):
    chart = figure(
        title=(
            "Relative price development (index, not absolute price; "
            "first observation = 100)"
        ),
        x_axis_type="datetime",
        x_axis_label="Calendar date",
        y_axis_label="Relative price index",
        height=570,
        sizing_mode="stretch_width",
        tools="pan,wheel_zoom,box_zoom,reset,save",
    )
    renderers = []
    dimensions = []
    for series_id, series in timeline.groupby("series_id", sort=True):
        series = series.sort_values("observation_date")
        source = source_class(series)
        label = str(series["series_label"].iloc[0])
        product = str(series["product"].iloc[0])
        tax_basis = str(series["tax_basis"].iloc[0])
        line = chart.line(
            "observation_date",
            "indexed_value",
            source=source,
            color=_COLORS.get(series_id, "#A9B5C3"),
            line_width=3 if series_id == "BRENT" else 2.4,
            legend_label=label,
        )
        points = chart.scatter(
            "observation_date",
            "indexed_value",
            source=source,
            color=_COLORS.get(series_id, "#A9B5C3"),
            size=4 if series_id == "BRENT" else 7,
            alpha=0.75,
        )
        chart.add_tools(
            hover_class(
                renderers=[points],
                tooltips=[
                    ("Series", label),
                    ("Date", "@observation_date{%d.%m.%Y}"),
                    ("Price", "@value{0.000} @unit"),
                    ("Index", "@indexed_value{0.0}"),
                ],
                formatters={"@observation_date": "datetime"},
            )
        )
        renderers.extend([line, points])
        dimensions.extend([(product, tax_basis), (product, tax_basis)])
    chart.add_layout(
        span_class(
            location=event.timestamp() * 1000,
            dimension="height",
            line_color="#B03A2E",
            line_dash="dashed",
            line_width=2,
        )
    )
    _style_chart(chart)
    return chart, renderers, dimensions


def _change_chart(
    weekly,
    event,
    source_class,
    hover_class,
    formatter_class,
    span_class,
    figure,
):
    definitions = [
        (
            "BRENT",
            "Brent prior-week mean",
            "ALL",
            "NOT_APPLICABLE",
            "brent_weekly_pct_change",
        ),
        (
            "PETROL_WITH_TAX",
            "Petrol Euro 95 incl. taxes",
            "PETROL",
            "WITH_TAX",
            "petrol_with_tax_eur_per_liter_pct_change",
        ),
        (
            "PETROL_WITHOUT_TAX",
            "Petrol Euro 95 excl. taxes",
            "PETROL",
            "WITHOUT_TAX",
            "petrol_without_tax_eur_per_liter_pct_change",
        ),
        (
            "DIESEL_WITH_TAX",
            "Diesel incl. taxes",
            "DIESEL",
            "WITH_TAX",
            "diesel_with_tax_eur_per_liter_pct_change",
        ),
        (
            "DIESEL_WITHOUT_TAX",
            "Diesel excl. taxes",
            "DIESEL",
            "WITHOUT_TAX",
            "diesel_without_tax_eur_per_liter_pct_change",
        ),
    ]
    chart = figure(
        title="Weekly price changes on the aligned Monday timeline",
        x_axis_type="datetime",
        x_axis_label="German fuel observation date",
        y_axis_label="Week-over-week change",
        height=570,
        sizing_mode="stretch_width",
        tools="pan,wheel_zoom,box_zoom,reset,save",
    )
    renderers = []
    dimensions = []
    for series_id, label, product, tax_basis, column_name in definitions:
        selected = weekly[["fuel_observation_date", column_name]].dropna()
        selected = selected.rename(columns={column_name: "weekly_change"})
        source = source_class(selected)
        line = chart.line(
            "fuel_observation_date",
            "weekly_change",
            source=source,
            color=_COLORS[series_id],
            line_width=3 if series_id == "BRENT" else 2.4,
            legend_label=label,
        )
        points = chart.scatter(
            "fuel_observation_date",
            "weekly_change",
            source=source,
            color=_COLORS[series_id],
            size=6,
        )
        chart.add_tools(
            hover_class(
                renderers=[points],
                tooltips=[
                    ("Series", label),
                    ("Monday", "@fuel_observation_date{%d.%m.%Y}"),
                    ("Weekly change", "@weekly_change{+0.00%;-0.00%;0.00%}"),
                ],
                formatters={"@fuel_observation_date": "datetime"},
            )
        )
        renderers.extend([line, points])
        dimensions.extend([(product, tax_basis), (product, tax_basis)])
    chart.add_layout(
        span_class(location=0, dimension="width", line_color="#777777")
    )
    chart.add_layout(
        span_class(
            location=event.timestamp() * 1000,
            dimension="height",
            line_color="#B03A2E",
            line_dash="dashed",
            line_width=2,
        )
    )
    chart.yaxis.formatter = formatter_class(format="0.0%")
    _style_chart(chart)
    return chart, renderers, dimensions


def _lag_chart(lags, source_class, hover_class, formatter_class, figure):
    chart = figure(
        title="Correlation of Brent changes with later German fuel-price changes",
        x_axis_label="Transmission lag in weeks",
        y_axis_label="Correlation coefficient",
        height=570,
        sizing_mode="stretch_width",
        tools="pan,wheel_zoom,box_zoom,reset,save",
    )
    renderers = []
    dimensions = []
    sources = []
    for (product, tax_basis), series in lags.groupby(
        ["product", "tax_basis"], sort=True
    ):
        series = series.sort_values("lag_weeks").copy()
        series["correlation"] = series["spearman_correlation"]
        series["p_value"] = series["spearman_p_value"]
        series_id = f"{product}_{tax_basis}"
        label = (
            ("Diesel" if product == "DIESEL" else "Petrol Euro 95")
            + (" incl. taxes" if tax_basis == "WITH_TAX" else " excl. taxes")
        )
        source = source_class(series)
        sources.append(source)
        line = chart.line(
            "lag_weeks",
            "correlation",
            source=source,
            color=_COLORS[series_id],
            line_width=2.8,
            legend_label=label,
        )
        points = chart.scatter(
            "lag_weeks",
            "correlation",
            source=source,
            color=_COLORS[series_id],
            size=9,
        )
        chart.add_tools(
            hover_class(
                renderers=[points],
                tooltips=[
                    ("Series", label),
                    ("Lag", "@lag_weeks weeks"),
                    ("Correlation", "@correlation{0.000}"),
                    ("p-value", "@p_value{0.000}"),
                    ("Observations", "@observations"),
                ],
            )
        )
        renderers.extend([line, points])
        dimensions.extend([(product, tax_basis), (product, tax_basis)])
    chart.line(
        [min(lags["lag_weeks"]), max(lags["lag_weeks"])],
        [0, 0],
        line_color="#777777",
    )
    chart.yaxis.formatter = formatter_class(format="0.00")
    _style_chart(chart)
    return chart, renderers, dimensions, sources


def _style_chart(chart):
    chart.grid.grid_line_alpha = 0.18
    chart.toolbar.logo = None
    if len(chart.legend) > 0:
        chart.legend.location = "top_left"
        chart.legend.click_policy = "hide"
        chart.legend.label_text_font_size = "9pt"


def _load_csv(path, required_columns, date_columns):
    input_path = Path(path)
    if not input_path.is_file():
        raise FileNotFoundError(f"Dashboard input not found: {input_path}")
    data = pd.read_csv(input_path)
    missing = required_columns - set(data.columns)
    if missing:
        names = ", ".join(sorted(missing))
        raise ValueError(f"Dashboard input is missing columns: {names}")
    if data.empty:
        raise ValueError("Dashboard input must not be empty")
    for column_name in date_columns:
        data[column_name] = pd.to_datetime(data[column_name], errors="coerce")
        if data[column_name].isna().any():
            raise ValueError(f"{column_name} must contain valid dates")
    return data


def _load_conflict(path):
    data = _load_csv(path, _CONFLICT_COLUMNS, ("week_end_date",))
    data = data[data["country_code"].isin(("IR", "IL"))].copy()
    if data.empty:
        raise ValueError("Conflict data must contain Iran or Israel")
    if data.duplicated(["week_end_date", "country_code"]).any():
        raise ValueError(
            "Conflict data contains duplicate country-week rows"
        )
    numeric_columns = [
        column_name
        for column_name in _CONFLICT_COLUMNS
        if column_name.endswith("_events")
        or column_name.endswith("_fatalities")
    ]
    for column_name in numeric_columns:
        data[column_name] = pd.to_numeric(data[column_name], errors="coerce")
        if data[column_name].isna().any():
            raise ValueError(f"{column_name} must contain numeric values")
        if (data[column_name] < 0).any():
            raise ValueError(f"{column_name} must not be negative")
    expected_events = (
        data["air_drone_strike_events"]
        + data["shelling_artillery_missile_events"]
    )
    expected_fatalities = (
        data["air_drone_strike_fatalities"]
        + data["shelling_artillery_missile_fatalities"]
    )
    if not data["strike_events"].equals(expected_events):
        raise ValueError(
            "strike_events must equal its two strike-event components"
        )
    if not data["strike_fatalities"].equals(expected_fatalities):
        raise ValueError(
            "strike_fatalities must equal its two fatality components"
        )
    return data.sort_values(["week_end_date", "country_code"]).reset_index(
        drop=True
    )


def _load_centcom(path):
    data = _load_csv(
        path,
        _CENTCOM_COLUMNS,
        ("event_date", "publication_date"),
    )
    for column_name in (
        "source_release_id",
        "initiator_country_code",
        "affected_country_code",
        "verification_status",
        "counting_unit",
        "source_id",
        "source_url",
    ):
        data[column_name] = data[column_name].astype(str).str.strip()

    if not (data["source_id"] == _CENTCOM_SOURCE_ID).all():
        raise ValueError(f"CENTCOM source_id must be {_CENTCOM_SOURCE_ID}")
    if not (data["initiator_country_code"].str.upper() == "US").all():
        raise ValueError("CENTCOM initiator_country_code must be US")
    if not (data["counting_unit"] == _CENTCOM_COUNTING_UNIT).all():
        raise ValueError(
            f"CENTCOM counting_unit must be {_CENTCOM_COUNTING_UNIT}"
        )
    if (data["event_date"] > data["publication_date"]).any():
        raise ValueError(
            "CENTCOM event_date must not be after publication_date"
        )

    data["operation_day_count"] = pd.to_numeric(
        data["operation_day_count"], errors="coerce"
    )
    if data["operation_day_count"].isna().any() or not (
        data["operation_day_count"] == 1
    ).all():
        raise ValueError("CENTCOM operation_day_count must equal 1")
    data["include_in_core_series"] = data["include_in_core_series"].map(
        _boolean_value
    )
    if data["include_in_core_series"].isna().any():
        raise ValueError(
            "CENTCOM include_in_core_series must contain true or false"
        )

    official_url = data["source_url"].str.match(
        r"https://www\.centcom\.mil/MEDIA/PUBLIC-RELEASES/Article/\d+/"
    )
    if not official_url.all():
        raise ValueError(
            "CENTCOM source_url must be an official release URL"
        )

    selected = data[
        data["verification_status"].str.upper().eq("CONFIRMED")
        & data["include_in_core_series"]
    ].copy()
    if selected.empty:
        raise ValueError(
            "CENTCOM data must contain a confirmed in-scope operation day"
        )
    if selected.duplicated(["event_date", "affected_country_code"]).any():
        raise ValueError(
            "CENTCOM data contains a duplicate operation day and affected "
            "country"
        )
    return selected.sort_values(
        ["event_date", "affected_country_code"]
    ).reset_index(drop=True)


def _boolean_value(value):
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().casefold()
    if normalized in {"true", "1", "yes"}:
        return True
    if normalized in {"false", "0", "no"}:
        return False
    return None


def _aggregate_centcom_weeks(centcom, first_week, last_week):
    selected = centcom.copy()
    selected["week_end_date"] = (
        selected["event_date"]
        .dt.to_period("W-SAT")
        .dt.end_time
        .dt.normalize()
    )
    grouped = selected.groupby("week_end_date", sort=True).agg(
        operation_day_count=("event_date", "nunique"),
        release_count=("source_release_id", "nunique"),
        affected_countries=(
            "affected_country_code",
            lambda values: ", ".join(sorted(set(values))),
        ),
        release_titles=(
            "title",
            lambda values: " | ".join(dict.fromkeys(values)),
        ),
    )
    calendar = pd.DataFrame(
        {
            "week_end_date": pd.date_range(
                pd.Timestamp(first_week),
                pd.Timestamp(last_week),
                freq="7D",
            )
        }
    )
    weekly = calendar.merge(
        grouped.reset_index(),
        on="week_end_date",
        how="left",
    )
    for column_name in ("operation_day_count", "release_count"):
        weekly[column_name] = weekly[column_name].fillna(0).astype(int)
    for column_name in ("affected_countries", "release_titles"):
        weekly[column_name] = weekly[column_name].fillna("")
    return weekly


def _validate_tax_price_order(weekly):
    for product in ("petrol", "diesel"):
        with_tax = weekly[f"{product}_with_tax_eur_per_liter"]
        without_tax = weekly[f"{product}_without_tax_eur_per_liter"]
        if not (with_tax > without_tax).all():
            raise ValueError(
                f"{product} prices including taxes must exceed prices "
                "excluding taxes in every weekly observation"
            )


def _interpretation_html(lags, centcom):
    strongest = lags.loc[
        lags.groupby(["product", "tax_basis"])[
            "spearman_correlation"
        ].apply(lambda values: values.abs().idxmax())
    ]
    rows = []
    for row in strongest.sort_values(["tax_basis", "product"]).itertuples():
        product = "Diesel" if row.product == "DIESEL" else "Petrol Euro 95"
        basis = "incl. taxes" if row.tax_basis == "WITH_TAX" else "excl. taxes"
        rows.append(
            "<tr>"
            f"<td>{html.escape(product)}</td><td>{html.escape(basis)}</td>"
            f"<td>{row.lag_weeks}</td>"
            f"<td>{row.spearman_correlation:.3f}</td>"
            f"<td>{row.observations}</td>"
            "</tr>"
        )
    return (
        "<section style='margin-top:14px;line-height:1.45'>"
        "<h3 style='margin:0 0 6px'>How to read the charts</h3>"
        "<p><b>Strikes:</b> Weekly ACLED aggregates can be filtered by "
        "country and metric. All strike events equal air/drone strikes plus "
        "shelling/artillery/missile attacks; these are nested definitions, "
        "not independent indicators. 'Violence against civilians' is "
        "ACLED's own event-type category for attacks where civilians were "
        "the recorded target; it is not a comprehensive civilian-casualty "
        "count, since strike/shelling events can also kill civilians "
        "without being classified this way, and it is not comparable to "
        "military casualties, which ACLED's event typology does not "
        "separately report. No destroyed-facilities data (civilian or "
        "military) is available in this project; that remains an open "
        "gap, not a zero. The separate CENTCOM panel shows "
        f"{len(centcom)} distinct, officially confirmed U.S. strike-operation "
        "days in the Iran core scope. It counts days, not targets, munitions, "
        "sorties or releases, and is therefore not numerically interchangeable "
        "with ACLED event counts. <b>EUR/L:</b> This tab shows the actual "
        "German price level; prices including taxes are higher in every "
        "observation. <b>Index:</b> Every series starts at 100, so differently "
        "scaled prices can be compared by relative growth. An untaxed line "
        "can therefore have a higher index while its actual EUR/L price "
        "remains lower. Hover shows the original unit. "
        "<b>Changes:</b> Brent is the mean of the trading week immediately "
        "before the displayed German Monday price. <b>Lag:</b> lag 0 compares "
        "that Brent change with the next Monday fuel-price change; lag 1 "
        "tests the following week, through lag 8.</p>"
        "<h4 style='margin:10px 0 4px'>Strongest exploratory Spearman "
        "association in the selected window</h4>"
        "<div style='overflow-x:auto'><table style='border-collapse:collapse;"
        "min-width:520px'><thead><tr><th>Product</th><th>Basis</th>"
        "<th>Lag</th><th>Correlation</th><th>n</th></tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table></div>"
        "<p style='color:#A9B5C3;font-size:12px'><b>Interpretation limit:</b> "
        "This is an exploratory temporal association in weekly percentage "
        "changes, not evidence that the conflict caused German fuel prices. "
        "Exchange rates, refining and distribution margins, inventories, "
        "taxes, biofuel components, demand and policy may also affect the "
        "observed delay. Testing nine lags also creates a multiple-comparison "
        "risk; the strongest lag must therefore be treated as descriptive. "
        "The German EU series represents Monday observations for Euro-Super "
        "95 (E5) and diesel (B7). ACLED counts are reported aggregates and "
        "should not be interpreted as independently verified individual "
        "incidents. CENTCOM records are official U.S. claims and do not by "
        "themselves independently verify effects or damage.</p></section>"
    )


def build_parser():
    parser = argparse.ArgumentParser(
        description="Create the Brent-to-German-fuel lag dashboard."
    )
    parser.add_argument(
        "--timeline-file",
        type=Path,
        default=Path("data/processed/energy/energy_price_timeline.csv"),
    )
    parser.add_argument(
        "--weekly-file",
        type=Path,
        default=Path("data/processed/energy/energy_price_weekly_panel.csv"),
    )
    parser.add_argument(
        "--lag-file",
        type=Path,
        default=Path("data/analysis/fuel_price_lag_results.csv"),
    )
    parser.add_argument(
        "--conflict-file",
        type=Path,
        default=Path("data/analysis/weekly_conflict_features.csv"),
    )
    parser.add_argument(
        "--centcom-file",
        type=Path,
        default=Path("data/validated/centcom_us_strike_operation_days.csv"),
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        default=Path("output/black_doves_energy_price_lag.html"),
    )
    parser.add_argument("--event-date", default="2026-02-28")
    parser.add_argument("--logo", type=Path)
    return parser


def main(arguments=None):
    parser = build_parser()
    options = parser.parse_args(arguments)
    try:
        output_path = create_fuel_price_lag_dashboard(
            timeline_file=options.timeline_file,
            weekly_file=options.weekly_file,
            lag_file=options.lag_file,
            output_path=options.output_file,
            conflict_file=options.conflict_file,
            centcom_file=options.centcom_file,
            event_date=options.event_date,
            logo_path=options.logo,
        )
    except (FileNotFoundError, TypeError, ValueError) as error:
        parser.error(str(error))
    print("\nBLACK DOVES fuel-price lag dashboard completed.")
    print(f"HTML file: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
