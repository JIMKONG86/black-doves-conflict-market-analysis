import argparse
import html
import sys

from pathlib import Path

import pandas as pd

from src.black_doves_visualization import _header_html
from src.black_doves_theme import (
    DARK_BOKEH_HTML_TEMPLATE,
    activate_black_doves_theme,
    style_dark_tabs,
)


_DETAIL_COLUMNS = {
    "event_id",
    "event_calendar_date",
    "effective_market_date",
    "event_title",
    "company_id",
    "company_name",
    "analysis_tier",
    "role_category",
    "is_confirmatory",
    "sample_group",
    "market_date",
    "relative_trading_day",
    "abnormal_return",
    "event_window_car",
}

_COMPANY_COLUMNS = {
    "event_id",
    "event_calendar_date",
    "effective_market_date",
    "event_title",
    "company_id",
    "company_name",
    "market_data_ticker",
    "benchmark_ticker",
    "analysis_tier",
    "role_category",
    "is_confirmatory",
    "sample_group",
    "event_day_abnormal_return",
    "post_event_car_0_1",
    "post_event_car_0_5",
    "post_event_car_0_10",
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


def create_market_universe_event_study_chart(
    detail_file,
    company_summary_file,
    sample_summary_file,
    output_path,
    logo_path=None,
    event_id=None,
):
    from bokeh.core.templates import get_env
    from bokeh.layouts import column
    from bokeh.models import (
        ColumnDataSource,
        Div,
        HoverTool,
        Legend,
        NumeralTickFormatter,
        Span,
        TabPanel,
        Tabs,
    )
    from bokeh.palettes import Category10
    from bokeh.plotting import figure, save
    from bokeh.resources import INLINE

    activate_black_doves_theme()

    detail = _load_detail(detail_file)
    companies = _load_companies(company_summary_file)
    samples = _load_samples(sample_summary_file)
    selected_event = _select_event(
        (detail, companies, samples),
        event_id,
    )
    detail = _event_rows(detail, selected_event)
    companies = _event_rows(companies, selected_event)
    samples = _event_rows(samples, selected_event)
    _validate_scope(detail, companies, samples)
    output_path = Path(output_path)

    if output_path.suffix.casefold() != ".html":
        raise ValueError("Market-universe chart output must use .html")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    sample_aar_chart = figure(
        title="Average abnormal return by sample",
        x_axis_label="Relative trading day",
        y_axis_label="Average abnormal return",
        width=1050,
        height=320,
        sizing_mode="stretch_width",
        tools="pan,wheel_zoom,box_zoom,reset,save",
    )
    sample_caar_chart = figure(
        title="Cumulative average abnormal return by sample",
        x_axis_label="Relative trading day",
        y_axis_label="CAAR from day -5",
        x_range=sample_aar_chart.x_range,
        width=1050,
        height=350,
        sizing_mode="stretch_width",
        tools="pan,wheel_zoom,box_zoom,reset,save",
    )

    for sample_group in _sample_order(samples):
        color, line_dash, marker = _SAMPLE_STYLES.get(
            sample_group,
            ("#5D6D7E", "dotdash", "diamond"),
        )
        sample = samples[
            samples["sample_group"] == sample_group
        ].sort_values("relative_trading_day")
        source = ColumnDataSource(sample)
        label = _sample_label(sample_group)
        aar_line = sample_aar_chart.line(
            "relative_trading_day",
            "aar",
            source=source,
            color=color,
            line_dash=line_dash,
            line_width=3,
            legend_label=label,
        )
        aar_points = sample_aar_chart.scatter(
            "relative_trading_day",
            "aar",
            source=source,
            marker=marker,
            color=color,
            size=8,
            legend_label=label,
        )
        sample_aar_chart.add_tools(
            HoverTool(
                renderers=[aar_points],
                tooltips=[
                    ("Sample", label),
                    ("Relative day", "@relative_trading_day"),
                    ("AAR", "@aar{0.00%}"),
                    ("Companies", "@company_count"),
                ],
            )
        )
        caar_line = sample_caar_chart.line(
            "relative_trading_day",
            "caar",
            source=source,
            color=color,
            line_dash=line_dash,
            line_width=3,
            legend_label=label,
        )
        caar_points = sample_caar_chart.scatter(
            "relative_trading_day",
            "caar",
            source=source,
            marker=marker,
            color=color,
            size=8,
            legend_label=label,
        )
        sample_caar_chart.add_tools(
            HoverTool(
                renderers=[caar_points],
                tooltips=[
                    ("Sample", label),
                    ("Relative day", "@relative_trading_day"),
                    ("CAAR", "@caar{0.00%}"),
                    ("Companies", "@company_count"),
                ],
            )
        )
        _ = (aar_line, caar_line)

    for chart in (sample_aar_chart, sample_caar_chart):
        _add_reference_lines(chart, Span)
        _style_chart(chart, NumeralTickFormatter)

    has_ols_samples = (
        "ols_caar" in samples.columns and samples["ols_caar"].notna().any()
    )

    if has_ols_samples:
        sample_ols_caar_chart = figure(
            title="OLS market-model CAAR by sample",
            x_axis_label="Relative trading day",
            y_axis_label="CAAR from day -5 (OLS market-model AR)",
            x_range=sample_aar_chart.x_range,
            width=1050,
            height=320,
            sizing_mode="stretch_width",
            tools="pan,wheel_zoom,box_zoom,reset,save",
        )

        for sample_group in _sample_order(samples):
            color, line_dash, marker = _SAMPLE_STYLES.get(
                sample_group,
                ("#5D6D7E", "dotdash", "diamond"),
            )
            sample = (
                samples[samples["sample_group"] == sample_group]
                .dropna(subset=["ols_caar"])
                .sort_values("relative_trading_day")
            )

            if sample.empty:
                continue

            source = ColumnDataSource(sample)
            label = _sample_label(sample_group)
            ols_caar_line = sample_ols_caar_chart.line(
                "relative_trading_day",
                "ols_caar",
                source=source,
                color=color,
                line_dash=line_dash,
                line_width=3,
                legend_label=label,
            )
            ols_caar_points = sample_ols_caar_chart.scatter(
                "relative_trading_day",
                "ols_caar",
                source=source,
                marker=marker,
                color=color,
                size=8,
                legend_label=label,
            )
            sample_ols_caar_chart.add_tools(
                HoverTool(
                    renderers=[ols_caar_points],
                    tooltips=[
                        ("Sample", label),
                        ("Relative day", "@relative_trading_day"),
                        ("OLS CAAR", "@ols_caar{0.00%}"),
                        ("Companies", "@company_count"),
                    ],
                )
            )
            _ = ols_caar_line

        _add_reference_lines(sample_ols_caar_chart, Span)
        _style_chart(sample_ols_caar_chart, NumeralTickFormatter)
    else:
        sample_ols_caar_chart = Div(
            text=(
                "<p style='color:#A9B5C3;font-size:12px'>OLS "
                "market-model CAAR is not available for this event/export "
                "(the underlying market panel was generated before the "
                "OLS market model existed, or every company's estimation "
                "window had too few pre-event observations).</p>"
            ),
            sizing_mode="stretch_width",
        )

    ranking = _company_ranking(companies)
    ranking_source = ColumnDataSource(ranking)
    ranking_chart = figure(
        title="Company abnormal return: event day through day +10",
        x_axis_label="CAR [0,+10] relative to local benchmark",
        y_range=ranking["company_label"].tolist(),
        width=1050,
        height=676,
        sizing_mode="stretch_width",
        tools="pan,wheel_zoom,box_zoom,reset,save",
    )
    ranking_bars = ranking_chart.hbar(
        y="company_label",
        left=0,
        right="post_event_car_0_10",
        height=0.72,
        color="bar_color",
        alpha=0.88,
        source=ranking_source,
        legend_field="sample_label",
    )
    ranking_chart.add_tools(
        HoverTool(
            renderers=[ranking_bars],
            tooltips=[
                ("Company", "@company_name"),
                ("Ticker", "@market_data_ticker"),
                ("Benchmark", "@benchmark_ticker"),
                ("Sample", "@sample_label"),
                ("Role", "@role_category"),
                ("Event day", "@event_day_abnormal_return{0.00%}"),
                ("CAR [0,+1]", "@post_event_car_0_1{0.00%}"),
                ("CAR [0,+5]", "@post_event_car_0_5{0.00%}"),
                ("CAR [0,+10]", "@post_event_car_0_10{0.00%}"),
            ],
        )
    )
    ranking_chart.add_layout(
        Span(
            location=0,
            dimension="height",
            line_color="#666666",
            line_width=1,
        )
    )
    ranking_chart.yaxis.major_label_text_font_size = "8pt"
    _style_chart(ranking_chart, NumeralTickFormatter)

    roles = _role_ranking(companies)
    roles_source = ColumnDataSource(roles)
    role_chart = figure(
        title="Mean ten-day abnormal return by company role",
        x_axis_label="Mean CAR [0,+10]",
        y_range=roles["role_category"].tolist(),
        width=1050,
        height=676,
        sizing_mode="stretch_width",
        tools="pan,wheel_zoom,box_zoom,reset,save",
    )
    role_bars = role_chart.hbar(
        y="role_category",
        left=0,
        right="mean_car_0_10",
        height=0.68,
        color="bar_color",
        alpha=0.88,
        source=roles_source,
    )
    role_chart.add_tools(
        HoverTool(
            renderers=[role_bars],
            tooltips=[
                ("Role", "@role_category"),
                ("Companies", "@company_count"),
                ("Mean CAR [0,+10]", "@mean_car_0_10{0.00%}"),
                ("Median CAR [0,+10]", "@median_car_0_10{0.00%}"),
                ("Positive companies", "@positive_share{0.0%}"),
            ],
        )
    )
    role_chart.add_layout(
        Span(
            location=0,
            dimension="height",
            line_color="#666666",
            line_width=1,
        )
    )
    _style_chart(role_chart, NumeralTickFormatter, legend=False)

    selected = _selected_company_paths(detail)
    selected_chart = figure(
        title="Post-event CAR: confirmatory companies and Volkswagen",
        x_axis_label="Relative trading day",
        y_axis_label="CAR from event day 0",
        width=1050,
        height=676,
        sizing_mode="stretch_width",
        tools="pan,wheel_zoom,box_zoom,reset,save",
    )
    selected_legend = []
    palette = Category10[10]

    for index, (company_name, company) in enumerate(
        selected.groupby("company_name", sort=True)
    ):
        source = ColumnDataSource(company)
        color = palette[index % len(palette)]
        line = selected_chart.line(
            "relative_trading_day",
            "post_event_car",
            source=source,
            color=color,
            line_width=2.4,
        )
        points = selected_chart.scatter(
            "relative_trading_day",
            "post_event_car",
            source=source,
            color=color,
            size=7,
        )
        selected_legend.append((company_name, [line, points]))
        selected_chart.add_tools(
            HoverTool(
                renderers=[points],
                tooltips=[
                    ("Company", company_name),
                    ("Relative day", "@relative_trading_day"),
                    ("Post-event CAR", "@post_event_car{0.00%}"),
                    ("Daily abnormal return", "@abnormal_return{0.00%}"),
                ],
            )
        )

    _add_reference_lines(selected_chart, Span)
    _style_chart(selected_chart, NumeralTickFormatter, legend=False)
    legend = Legend(
        items=selected_legend,
        title="Companies",
        location="top_left",
        label_text_font_size="9pt",
        click_policy="hide",
    )
    selected_chart.add_layout(legend, "right")

    title = html.escape(companies["event_title"].iloc[0])
    event_date = companies["event_calendar_date"].iloc[0].strftime(
        "%d %B %Y"
    )
    counts = companies["sample_group"].value_counts()
    scope = Div(
        text=(
            "<h2 style='margin:0 0 4px'>Complete market-universe "
            "event study</h2>"
            f"<p style='margin:0 0 12px'><b>{title}</b> · "
            f"{event_date} · {len(companies)} companies · "
            f"{int(counts.get('CONFIRMATORY', 0))} confirmatory · "
            f"{int(counts.get('EXPLORATORY', 0))} exploratory · "
            f"{int(counts.get('POST_HOC_EXPLORATORY', 0))} post-hoc"
            "</p>"
        ),
        sizing_mode="stretch_width",
    )
    method_note = Div(
        text=(
            "<p style='color:#A9B5C3;font-size:12px'>"
            "Daily abnormal return equals company return minus the "
            "configured local-benchmark return. The calendar event is "
            "mapped separately to the first available trading day for "
            "each exchange. CAAR begins at relative day -5; company and "
            "role rankings use CAR [0,+10]. The OLS market-model CAAR "
            "chart uses a separate single-factor market model "
            "(company_return = alpha + beta * benchmark_return) fitted "
            "per company on trading days strictly before the event date; "
            "see BLACK_DOVES_MARKET_UNIVERSE_EVENT_STUDY_README.md and "
            "src/services/ols_market_model.py for the estimation-window "
            "definition. Results are descriptive and do not establish "
            "causality. Click legend entries to hide or show series. "
            "Source: Yahoo Finance market observations and the "
            "pre-specified BLACK DOVES event registry."
            "</p>"
        ),
        sizing_mode="stretch_width",
    )
    tabs = Tabs(
        tabs=[
            TabPanel(
                title="Sample AAR / CAAR",
                child=column(
                    sample_aar_chart,
                    sample_caar_chart,
                    sample_ols_caar_chart,
                    sizing_mode="stretch_width",
                ),
            ),
            TabPanel(title="All companies", child=ranking_chart),
            TabPanel(title="Company roles", child=role_chart),
            TabPanel(
                title="Confirmatory + VW",
                child=selected_chart,
            ),
        ],
        sizing_mode="stretch_width",
    )
    style_dark_tabs(tabs)
    dashboard = column(
        Div(
            text=_header_html(logo_path),
            sizing_mode="stretch_width",
        ),
        scope,
        tabs,
        method_note,
        sizing_mode="stretch_width",
        max_width=1250,
    )
    save(
        dashboard,
        filename=str(output_path),
        title="BLACK DOVES – Complete Market-Universe Event Study",
        resources=INLINE,
        template=get_env().from_string(DARK_BOKEH_HTML_TEMPLATE),
    )
    return output_path


def _load_detail(file_path):
    data = _load_csv(file_path, _DETAIL_COLUMNS, "Event-window")
    return _typed_data(
        data,
        date_columns=(
            "event_calendar_date",
            "effective_market_date",
            "market_date",
        ),
        numeric_columns=(
            "relative_trading_day",
            "abnormal_return",
            "event_window_car",
        ),
    )


def _load_companies(file_path):
    data = _load_csv(file_path, _COMPANY_COLUMNS, "Company-summary")
    data = _typed_data(
        data,
        date_columns=("event_calendar_date", "effective_market_date"),
        numeric_columns=(
            "event_day_abnormal_return",
            "post_event_car_0_1",
            "post_event_car_0_5",
            "post_event_car_0_10",
        ),
    )

    if data.duplicated(["event_id", "company_id"]).any():
        raise ValueError(
            "Company-summary CSV contains duplicate event-company rows"
        )

    return data


def _load_samples(file_path):
    data = _load_csv(file_path, _SAMPLE_COLUMNS, "Sample-summary")
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

    # ols_aar / ols_caar are optional: older exports (generated before
    # src.services.ols_market_model existed) simply do not have them,
    # and even current exports legitimately contain NaN for companies
    # whose OLS estimation window had too few observations. They are
    # therefore coerced but never required or validated against NaN,
    # unlike the columns above.
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


def _validate_scope(detail, companies, samples):
    company_ids = set(companies["company_id"])

    if set(detail["company_id"]) != company_ids:
        raise ValueError(
            "Detail and company-summary CSVs use different companies"
        )

    detail_groups = set(detail["sample_group"])
    company_groups = set(companies["sample_group"])
    sample_groups = set(samples["sample_group"])

    if not (detail_groups == company_groups == sample_groups):
        raise ValueError("Input CSVs use inconsistent sample groups")

    expected_days = set(samples["relative_trading_day"])

    for company_id, rows in detail.groupby("company_id"):
        if set(rows["relative_trading_day"]) != expected_days:
            raise ValueError(
                f"Company {company_id} has an incomplete event window"
            )


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


def _sample_label(sample_group):
    return {
        "CONFIRMATORY": "Confirmatory",
        "EXPLORATORY": "Exploratory",
        "POST_HOC_EXPLORATORY": "Post-hoc: Volkswagen",
    }.get(sample_group, sample_group.replace("_", " ").title())


def _company_ranking(companies):
    ranking = companies.sort_values(
        ["post_event_car_0_10", "company_name"]
    ).copy()
    ranking["sample_label"] = ranking["sample_group"].map(_sample_label)
    ranking["bar_color"] = ranking["sample_group"].map(
        lambda value: _SAMPLE_STYLES.get(
            value,
            ("#5D6D7E", "dotdash", "diamond"),
        )[0]
    )
    ranking["company_label"] = (
        ranking["company_name"]
        + " ("
        + ranking["market_data_ticker"]
        + ")"
    )
    return ranking.reset_index(drop=True)


def _role_ranking(companies):
    roles = (
        companies.groupby("role_category", sort=True)[
            "post_event_car_0_10"
        ]
        .agg(
            company_count="count",
            mean_car_0_10="mean",
            median_car_0_10="median",
            positive_share=lambda values: (values > 0).mean(),
        )
        .reset_index()
        .sort_values(["mean_car_0_10", "role_category"])
        .reset_index(drop=True)
    )
    roles["bar_color"] = roles["mean_car_0_10"].map(
        lambda value: "#FF8A65" if value >= 0 else "#60758A"
    )
    return roles


def _selected_company_paths(detail):
    selected = detail[
        detail["is_confirmatory"].map(_boolean_value)
        | (detail["sample_group"] == "POST_HOC_EXPLORATORY")
    ].copy()
    selected = selected[selected["relative_trading_day"] >= 0]
    selected = selected.sort_values(
        ["company_name", "relative_trading_day"]
    )
    selected["post_event_car"] = selected.groupby(
        "company_id", sort=False
    )["abnormal_return"].cumsum()
    return selected


def _boolean_value(value):
    if isinstance(value, bool):
        return value

    normalized = str(value).strip().casefold()

    if normalized in {"true", "1", "yes"}:
        return True

    if normalized in {"false", "0", "no"}:
        return False

    raise ValueError(f"Invalid is_confirmatory value: {value}")


def _add_reference_lines(chart, span_class):
    chart.add_layout(
        span_class(
            location=0,
            dimension="width",
            line_color="#777777",
            line_width=1,
        )
    )
    chart.add_layout(
        span_class(
            location=0,
            dimension="height",
            line_color="#B03A2E",
            line_dash="dashed",
            line_width=2,
        )
    )


def _style_chart(chart, formatter_class, legend=True):
    chart.xaxis.formatter = (
        formatter_class(format="0.0%")
        if "CAR" in (chart.xaxis.axis_label or "")
        else chart.xaxis.formatter
    )
    chart.yaxis.formatter = (
        formatter_class(format="0.0%")
        if any(
            term in (chart.yaxis.axis_label or "")
            for term in ("return", "CAAR", "CAR")
        )
        else chart.yaxis.formatter
    )

    if legend and len(chart.legend) > 0:
        chart.legend.location = "top_left"
        chart.legend.click_policy = "hide"
        chart.legend.label_text_font_size = "10pt"

    chart.grid.grid_line_alpha = 0.2
    chart.toolbar.logo = None


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Create an interactive BLACK DOVES visualization for the "
            "complete market-universe event study."
        )
    )
    parser.add_argument(
        "--detail-file",
        type=Path,
        default=Path("data/analysis/market_universe_event_window.csv"),
    )
    parser.add_argument(
        "--company-summary-file",
        type=Path,
        default=Path(
            "data/analysis/market_universe_company_summary.csv"
        ),
    )
    parser.add_argument(
        "--sample-summary-file",
        type=Path,
        default=Path(
            "data/analysis/market_universe_sample_aar_caar.csv"
        ),
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        default=Path(
            "output/black_doves_market_universe_event_study.html"
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
        output_path = create_market_universe_event_study_chart(
            detail_file=options.detail_file,
            company_summary_file=options.company_summary_file,
            sample_summary_file=options.sample_summary_file,
            output_path=options.output_file,
            logo_path=options.logo,
            event_id=options.event_id,
        )
    except (FileNotFoundError, TypeError, ValueError) as error:
        parser.error(str(error))

    print("\nBLACK DOVES market-universe visualization completed.")
    print(f"Chart: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
