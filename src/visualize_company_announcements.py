"""Interactive company, announcement and conflict-context explorer."""

import argparse
import html
import sys

from pathlib import Path

import pandas as pd

from src.black_doves_theme import (
    ACCENT,
    AMBER,
    BLUE,
    DARK_BOKEH_HTML_TEMPLATE,
    DARK_FILTER_ROW_STYLESHEET,
    GREEN,
    MUTED,
    VIOLET,
    activate_black_doves_theme,
    style_dark_button,
    style_dark_select,
)
from src.black_doves_visualization import _header_html


_MARKET_COLUMNS = {
    "company_id",
    "company_name",
    "market_data_ticker",
    "benchmark_ticker",
    "role_category",
    "Date",
    "company_price",
    "benchmark_price",
    "company_return",
    "benchmark_return",
    "abnormal_return",
}

_CONFLICT_COLUMNS = {
    "week_end_date",
    "country_name",
    "country_code",
    "strike_events",
    "strike_fatalities",
    "air_drone_strike_events",
    "air_drone_strike_fatalities",
    "shelling_artillery_missile_events",
    "shelling_artillery_missile_fatalities",
}

_ANNOUNCEMENT_COLUMNS = {
    "announcement_id",
    "announcement_date",
    "company_id",
    "company_name",
    "market_data_ticker",
    "announcement_type",
    "title",
    "source_name",
    "source_url",
    "verification_status",
    "coverage_status",
    "record_scope",
}

_OPTIONAL_ANNOUNCEMENT_COLUMNS = (
    "counterparty_name",
    "counterparty_country_code",
    "systems",
    "contract_value_eur",
    "value_description",
    "reviewed_by",
    "notes",
)

_CENTCOM_COLUMNS = {
    "event_date",
    "operation_day_count",
    "include_in_core_series",
    "title",
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
}

_COUNTRY_COLORS = (BLUE, VIOLET, GREEN, ACCENT, AMBER)
_DEFAULT_COMPANY_ID = "CMP035"
_DEFAULT_PERIOD = "SUPPORTING"
_DEFAULT_CONFLICT_METRIC = "strike_events"


def create_company_announcement_dashboard(
    market_file,
    conflict_file,
    announcement_file,
    centcom_file,
    output_path,
    logo_path=None,
):
    from bokeh.core.templates import get_env
    from bokeh.layouts import column, row
    from bokeh.models import (
        Button,
        ColumnDataSource,
        CustomJS,
        Div,
        HoverTool,
        NumeralTickFormatter,
        Select,
    )
    from bokeh.plotting import figure, save
    from bokeh.resources import INLINE

    activate_black_doves_theme()
    market = _load_market(market_file)
    conflict = _load_conflict(conflict_file)
    announcements = _load_announcements(announcement_file, market)
    centcom = _load_centcom(centcom_file)
    output = Path(output_path)

    if output.suffix.casefold() != ".html":
        raise ValueError("Company explorer output must use .html")

    output.parent.mkdir(parents=True, exist_ok=True)
    companies = _company_directory(market)
    default_company = _default_company(companies, announcements)
    periods = _period_table(market)
    start, end = _period_bounds(periods, _DEFAULT_PERIOD)
    selected_market = _market_view(market, default_company, start, end)
    selected_announcements = _announcement_view(
        announcements,
        default_company,
        start,
        end,
        selected_market,
    )
    company_row = companies[companies["company_id"] == default_company].iloc[0]

    all_market_source = ColumnDataSource(market)
    all_conflict_source = ColumnDataSource(conflict)
    all_announcement_source = ColumnDataSource(announcements)
    all_centcom_source = ColumnDataSource(centcom)
    company_directory_source = ColumnDataSource(companies)
    period_source = ColumnDataSource(periods)
    market_source = ColumnDataSource(selected_market)
    announcement_source = ColumnDataSource(selected_announcements)

    market_chart = figure(
        title=_market_title(company_row),
        x_axis_type="datetime",
        x_axis_label="Market date",
        y_axis_label="Indexed level (first visible observation = 100)",
        height=500,
        sizing_mode="stretch_width",
        tools="pan,wheel_zoom,box_zoom,reset,save",
    )
    company_line = market_chart.line(
        "Date",
        "company_index",
        source=market_source,
        color=AMBER,
        line_width=3,
        legend_label="Selected company",
    )
    benchmark_line = market_chart.line(
        "Date",
        "benchmark_index",
        source=market_source,
        color=BLUE,
        line_width=2.5,
        line_dash="dashed",
        legend_label="Configured benchmark",
    )
    company_points = market_chart.scatter(
        "Date",
        "company_index",
        source=market_source,
        color=AMBER,
        size=4,
        alpha=0.35,
    )
    announcement_points = market_chart.scatter(
        "announcement_date",
        "marker_y",
        source=announcement_source,
        color=ACCENT,
        marker="diamond",
        size=13,
        line_color="#F3F6FA",
        line_width=1,
        legend_label="Imported company announcement",
    )
    market_chart.add_tools(
        HoverTool(
            renderers=[company_points],
            tooltips=[
                ("Company", "@company_name"),
                ("Ticker", "@market_data_ticker"),
                ("Date", "@Date{%d %b %Y}"),
                ("Price", "@company_price{0,0.00}"),
                ("Company index", "@company_index{0.0}"),
                ("Benchmark index", "@benchmark_index{0.0}"),
                ("Daily abnormal return", "@abnormal_return{0.00%}"),
            ],
            formatters={"@Date": "datetime"},
        ),
        HoverTool(
            renderers=[announcement_points],
            tooltips=[
                ("Announcement", "@title"),
                ("Date", "@announcement_date{%d %b %Y}"),
                ("Type", "@announcement_type_label"),
                ("Scope", "@record_scope"),
                ("Counterparty", "@counterparty_name"),
                ("Systems", "@systems"),
                ("Value", "@value_description"),
                ("Aligned market date", "@aligned_market_date{%d %b %Y}"),
                ("Aligned-day abnormal return", "@event_day_abnormal_return{0.00%}"),
                ("Source", "@source_name"),
                ("Verification", "@verification_status"),
            ],
            formatters={
                "@announcement_date": "datetime",
                "@aligned_market_date": "datetime",
            },
        ),
    )
    _style_chart(market_chart)

    conflict_sources = []
    country_codes = []
    countries = (
        conflict[["country_code", "country_name"]]
        .drop_duplicates()
        .sort_values("country_name")
    )
    conflict_chart = figure(
        title=_CONFLICT_METRICS[_DEFAULT_CONFLICT_METRIC],
        x_axis_type="datetime",
        x_axis_label="Week ending",
        y_axis_label=_CONFLICT_METRICS[_DEFAULT_CONFLICT_METRIC],
        height=340,
        sizing_mode="stretch_width",
        tools="pan,wheel_zoom,box_zoom,reset,save",
    )

    for index, country in enumerate(countries.itertuples(index=False)):
        country_view = _conflict_view(
            conflict,
            country.country_code,
            start,
            end,
            _DEFAULT_CONFLICT_METRIC,
        )
        source = ColumnDataSource(country_view)
        conflict_sources.append(source)
        country_codes.append(country.country_code)
        color = _COUNTRY_COLORS[index % len(_COUNTRY_COLORS)]
        line = conflict_chart.line(
            "week_end_date",
            "metric_value",
            source=source,
            color=color,
            line_width=2.5,
            legend_label=country.country_name,
        )
        points = conflict_chart.scatter(
            "week_end_date",
            "metric_value",
            source=source,
            color=color,
            size=6,
            alpha=0.72,
        )
        conflict_chart.add_tools(
            HoverTool(
                renderers=[points],
                tooltips=[
                    ("Country", "@country_name"),
                    ("Week", "@week_end_date{%d %b %Y}"),
                    ("Metric", "@metric_label"),
                    ("Value", "@metric_value{0,0}"),
                ],
                formatters={"@week_end_date": "datetime"},
            )
        )
        _ = line

    _style_chart(conflict_chart)

    selected_centcom = _centcom_view(centcom, start, end)
    centcom_source = ColumnDataSource(selected_centcom)
    centcom_chart = figure(
        title="United States operation days (initiator; CENTCOM)",
        x_axis_type="datetime",
        x_axis_label="Week ending",
        y_axis_label="Confirmed operation days",
        height=250,
        sizing_mode="stretch_width",
        tools="pan,wheel_zoom,box_zoom,reset,save",
    )
    centcom_bars = centcom_chart.vbar(
        x="week_end_date",
        top="operation_day_count",
        source=centcom_source,
        width=4 * 24 * 60 * 60 * 1000,
        color=GREEN,
        alpha=0.85,
    )
    centcom_chart.add_tools(
        HoverTool(
            renderers=[centcom_bars],
            tooltips=[
                ("Week", "@week_end_date{%d %b %Y}"),
                ("Operation days", "@operation_day_count{0,0}"),
                ("Releases", "@release_count{0,0}"),
                ("Titles", "@release_titles"),
            ],
            formatters={"@week_end_date": "datetime"},
        )
    )
    centcom_chart.y_range.start = 0
    _style_chart(centcom_chart, legend=False)

    company_filter = Select(
        title="Company",
        value=default_company,
        options=[
            (
                item.company_id,
                f"{item.company_name} ({item.market_data_ticker})",
            )
            for item in companies.itertuples(index=False)
        ],
        sizing_mode="stretch_width",
    )
    period_filter = Select(
        title="Analysis period",
        value=_DEFAULT_PERIOD,
        options=list(zip(periods["period_id"], periods["period_label"])),
        sizing_mode="stretch_width",
    )
    announcement_type_filter = Select(
        title="Announcement type",
        value="ALL",
        options=[("ALL", "All imported types")]
        + [
            (value, _label(value))
            for value in sorted(
                announcements["announcement_type"].dropna().unique()
            )
        ],
        sizing_mode="stretch_width",
    )
    conflict_metric_filter = Select(
        title="Conflict metric",
        value=_DEFAULT_CONFLICT_METRIC,
        options=list(_CONFLICT_METRICS.items()),
        sizing_mode="stretch_width",
    )
    reset_button = Button(
        label="Reset view",
        button_type="default",
        width=145,
        height=40,
    )

    for widget in (
        company_filter,
        period_filter,
        announcement_type_filter,
        conflict_metric_filter,
    ):
        style_dark_select(widget)
    style_dark_button(reset_button)

    coverage_companies = announcements["company_id"].nunique()
    scope = Div(
        text=(
            "<h2 style='margin:0 0 4px'>Company &amp; announcement "
            "explorer</h2>"
            f"<p style='margin:0 0 12px'>{len(companies)} companies with "
            "market and configured-benchmark data · company-linked "
            f"announcement records currently cover {coverage_companies} of "
            f"{len(companies)} companies</p>"
        ),
        sizing_mode="stretch_width",
    )
    status = Div(
        text=_status_html(
            company_row,
            announcements,
            selected_announcements,
            start,
            end,
        ),
        sizing_mode="stretch_width",
    )
    announcement_register = Div(
        text=_announcement_register_html(selected_announcements),
        sizing_mode="fixed",
        width=320,
        height=1050,
        styles={"overflow-y": "auto"},
    )

    callback = CustomJS(
        args={
            "all_market_source": all_market_source,
            "all_conflict_source": all_conflict_source,
            "all_announcement_source": all_announcement_source,
            "all_centcom_source": all_centcom_source,
            "company_directory_source": company_directory_source,
            "period_source": period_source,
            "market_source": market_source,
            "announcement_source": announcement_source,
            "conflict_sources": conflict_sources,
            "country_codes": country_codes,
            "centcom_source": centcom_source,
            "company_filter": company_filter,
            "period_filter": period_filter,
            "announcement_type_filter": announcement_type_filter,
            "conflict_metric_filter": conflict_metric_filter,
            "market_chart": market_chart,
            "conflict_chart": conflict_chart,
            "conflict_axis": conflict_chart.yaxis[0],
            "status": status,
            "announcement_register": announcement_register,
        },
        code=_filter_callback_code(),
    )

    for widget in (
        company_filter,
        period_filter,
        announcement_type_filter,
        conflict_metric_filter,
    ):
        widget.js_on_change("value", callback)

    reset_callback = CustomJS(
        args={
            "company_filter": company_filter,
            "period_filter": period_filter,
            "announcement_type_filter": announcement_type_filter,
            "conflict_metric_filter": conflict_metric_filter,
        },
        code=(
            f"company_filter.value = '{default_company}';\n"
            f"period_filter.value = '{_DEFAULT_PERIOD}';\n"
            "announcement_type_filter.value = 'ALL';\n"
            f"conflict_metric_filter.value = '{_DEFAULT_CONFLICT_METRIC}';\n"
            "company_filter.change.emit();"
        ),
    )
    reset_button.js_on_click(reset_callback)

    controls = row(
        company_filter,
        period_filter,
        announcement_type_filter,
        conflict_metric_filter,
        reset_button,
        spacing=12,
        sizing_mode="stretch_width",
        stylesheets=[DARK_FILTER_ROW_STYLESHEET],
    )
    method_note = Div(
        text=(
            f"<p style='color:{MUTED};font-size:12px'>Market lines are "
            "rebased to 100 at the first visible observation so companies "
            "and local benchmarks remain comparable across currencies. "
            "Conflict lines count affected-country events; the CENTCOM strip "
            "counts U.S.-initiated, release-confirmed operation days and is "
            "never added to affected-country counts. Announcement markers "
            "show only imported, company-linked records. Missing coverage "
            "must not be interpreted as zero real-world announcements. All "
            "relationships are descriptive, not causal.</p>"
        ),
        sizing_mode="stretch_width",
    )
    charts_column = column(
        market_chart,
        conflict_chart,
        centcom_chart,
        sizing_mode="stretch_width",
    )
    charts_with_sidebar = row(
        charts_column,
        announcement_register,
        sizing_mode="stretch_width",
    )
    dashboard = column(
        Div(text=_header_html(logo_path), sizing_mode="stretch_width"),
        scope,
        controls,
        status,
        charts_with_sidebar,
        method_note,
        sizing_mode="stretch_width",
        max_width=1250,
    )
    save(
        dashboard,
        filename=str(output),
        title="BLACK DOVES – Company & Announcement Explorer",
        resources=INLINE,
        template=get_env().from_string(DARK_BOKEH_HTML_TEMPLATE),
    )
    return output


def _load_market(path):
    data = _read_csv(path, _MARKET_COLUMNS, "Company market")
    data["Date"] = pd.to_datetime(data["Date"], errors="coerce")

    if data["Date"].isna().any():
        raise ValueError("Company market Date must contain valid dates")

    for column in (
        "company_price",
        "benchmark_price",
        "company_return",
        "benchmark_return",
        "abnormal_return",
    ):
        data[column] = pd.to_numeric(data[column], errors="coerce")

        if data[column].isna().any():
            raise ValueError(f"Company market {column} must be numeric")

    if data.duplicated(["company_id", "Date"]).any():
        raise ValueError("Company market data contains duplicate company dates")

    return data.sort_values(["company_id", "Date"]).reset_index(drop=True)


def _load_conflict(path):
    data = _read_csv(path, _CONFLICT_COLUMNS, "Conflict")
    data["week_end_date"] = pd.to_datetime(
        data["week_end_date"], errors="coerce"
    )

    if data["week_end_date"].isna().any():
        raise ValueError("Conflict week_end_date must contain valid dates")

    for column in _CONFLICT_METRICS:
        data[column] = pd.to_numeric(data[column], errors="coerce")

        if data[column].isna().any():
            raise ValueError(f"Conflict {column} must be numeric")

    return data.sort_values(["country_code", "week_end_date"]).reset_index(
        drop=True
    )


def _load_announcements(path, market):
    input_path = Path(path)

    if not input_path.is_file():
        return pd.DataFrame(
            columns=(
                *sorted(_ANNOUNCEMENT_COLUMNS),
                *_OPTIONAL_ANNOUNCEMENT_COLUMNS,
                "announcement_type_label",
            )
        )

    data = _read_csv(input_path, _ANNOUNCEMENT_COLUMNS, "Announcement")
    data["announcement_date"] = pd.to_datetime(
        data["announcement_date"], errors="coerce"
    )

    if data["announcement_date"].isna().any():
        raise ValueError("Announcement dates must use valid ISO dates")
    if data["announcement_id"].duplicated().any():
        raise ValueError("Announcement registry contains duplicate IDs")

    companies = _company_directory(market).set_index("company_id")
    unknown = set(data["company_id"]) - set(companies.index)

    if unknown:
        raise ValueError(
            "Announcement registry has unknown company IDs: "
            + ", ".join(sorted(unknown))
        )

    for row in data.itertuples(index=False):
        company = companies.loc[row.company_id]

        if row.market_data_ticker != company.market_data_ticker:
            raise ValueError(
                f"Announcement ticker mismatch for {row.company_id}"
            )

    for column in _OPTIONAL_ANNOUNCEMENT_COLUMNS:
        if column not in data:
            data[column] = ""

    data = data.fillna("")
    data["announcement_type_label"] = data["announcement_type"].map(_label)
    return data.sort_values(
        ["company_id", "announcement_date", "announcement_id"]
    ).reset_index(drop=True)


def _load_centcom(path):
    data = _read_csv(path, _CENTCOM_COLUMNS, "CENTCOM")
    data["event_date"] = pd.to_datetime(data["event_date"], errors="coerce")

    if data["event_date"].isna().any():
        raise ValueError("CENTCOM event_date must contain valid dates")

    included = data["include_in_core_series"].map(_boolean_value)
    data = data[included].copy()
    data["operation_day_count"] = pd.to_numeric(
        data["operation_day_count"], errors="coerce"
    )

    if data["operation_day_count"].isna().any():
        raise ValueError("CENTCOM operation_day_count must be numeric")

    data["week_end_date"] = data["event_date"] + pd.to_timedelta(
        (5 - data["event_date"].dt.weekday) % 7,
        unit="D",
    )
    return (
        data.groupby("week_end_date", as_index=False)
        .agg(
            operation_day_count=("operation_day_count", "sum"),
            release_count=("title", "size"),
            release_titles=(
                "title",
                lambda values: " | ".join(dict.fromkeys(map(str, values))),
            ),
        )
        .sort_values("week_end_date")
        .reset_index(drop=True)
    )


def _read_csv(path, required_columns, label):
    input_path = Path(path)

    if not input_path.is_file():
        raise FileNotFoundError(f"{label} CSV not found: {input_path}")

    data = pd.read_csv(input_path, dtype={"company_id": str})
    missing = required_columns - set(data.columns)

    if missing:
        raise ValueError(
            f"{label} CSV is missing required columns: "
            + ", ".join(sorted(missing))
        )
    if data.empty:
        raise ValueError(f"{label} CSV must not be empty")

    return data


def _company_directory(market):
    columns = [
        "company_id",
        "company_name",
        "market_data_ticker",
        "benchmark_ticker",
        "role_category",
    ]
    companies = market[columns].drop_duplicates()

    if companies["company_id"].duplicated().any():
        raise ValueError("Company market metadata is inconsistent")

    return companies.sort_values("company_name").reset_index(drop=True)


def _period_table(market):
    market_start = market["Date"].min().normalize()
    market_end = market["Date"].max().normalize()
    definitions = (
        (
            "CORE",
            "Core window · 01 Jan–18 Aug 2026",
            max(market_start, pd.Timestamp("2026-01-01")),
            min(market_end, pd.Timestamp("2026-08-18")),
        ),
        (
            "SUPPORTING",
            "Supporting horizon · 2025–2026",
            max(market_start, pd.Timestamp("2025-01-01")),
            market_end,
        ),
        (
            "FULL",
            "All available market history",
            market_start,
            market_end,
        ),
    )
    return pd.DataFrame(
        definitions,
        columns=("period_id", "period_label", "start_date", "end_date"),
    )


def _period_bounds(periods, period_id):
    selected = periods[periods["period_id"] == period_id]

    if selected.empty:
        raise ValueError(f"Unknown period: {period_id}")

    return selected.iloc[0][["start_date", "end_date"]].tolist()


def _default_company(companies, announcements):
    ids = set(companies["company_id"])

    if _DEFAULT_COMPANY_ID in ids:
        return _DEFAULT_COMPANY_ID
    if not announcements.empty:
        return str(announcements["company_id"].value_counts().index[0])

    return str(companies.iloc[0]["company_id"])


def _market_view(market, company_id, start, end):
    selected = market[
        (market["company_id"] == company_id)
        & (market["Date"] >= start)
        & (market["Date"] <= end)
    ].copy()

    if selected.empty:
        raise ValueError(f"No market rows for {company_id} in selected period")

    selected["company_index"] = (
        selected["company_price"] / selected["company_price"].iloc[0] * 100
    )
    selected["benchmark_index"] = (
        selected["benchmark_price"]
        / selected["benchmark_price"].iloc[0]
        * 100
    )
    return selected.reset_index(drop=True)


def _announcement_view(
    announcements,
    company_id,
    start,
    end,
    market_view,
    announcement_type="ALL",
):
    if announcements.empty:
        result = announcements.copy()
        result["marker_y"] = pd.Series(dtype=float)
        result["aligned_market_date"] = pd.Series(dtype="datetime64[ns]")
        result["event_day_abnormal_return"] = pd.Series(dtype=float)
        return result

    selected = announcements[
        (announcements["company_id"] == company_id)
        & (announcements["announcement_date"] >= start)
        & (announcements["announcement_date"] <= end)
    ].copy()

    if announcement_type != "ALL":
        selected = selected[
            selected["announcement_type"] == announcement_type
        ].copy()
    if selected.empty:
        selected["marker_y"] = pd.Series(dtype=float)
        selected["aligned_market_date"] = pd.Series(dtype="datetime64[ns]")
        selected["event_day_abnormal_return"] = pd.Series(dtype=float)
        return selected

    alignment = market_view[
        ["Date", "company_index", "abnormal_return"]
    ].sort_values("Date")
    selected = pd.merge_asof(
        selected.sort_values("announcement_date"),
        alignment,
        left_on="announcement_date",
        right_on="Date",
        direction="nearest",
    )
    selected["marker_y"] = selected["company_index"]
    selected["aligned_market_date"] = selected["Date"]
    selected["event_day_abnormal_return"] = selected["abnormal_return"]
    return selected.drop(
        columns=["Date", "company_index", "abnormal_return"]
    ).reset_index(drop=True)


def _conflict_view(conflict, country_code, start, end, metric):
    selected = conflict[
        (conflict["country_code"] == country_code)
        & (conflict["week_end_date"] >= start)
        & (conflict["week_end_date"] <= end)
    ].copy()
    selected["metric_value"] = selected[metric]
    selected["metric_label"] = _CONFLICT_METRICS[metric]
    return selected.reset_index(drop=True)


def _centcom_view(centcom, start, end):
    return centcom[
        (centcom["week_end_date"] >= start)
        & (centcom["week_end_date"] <= end)
    ].reset_index(drop=True)


def _market_title(company):
    return (
        f"{company.company_name} ({company.market_data_ticker}) versus "
        f"{company.benchmark_ticker}: rebased price performance"
    )


def _status_html(company, all_announcements, selected, start, end):
    available = all_announcements[
        all_announcements["company_id"] == company.company_id
    ]
    date_label = f"{start.strftime('%d %b %Y')}–{end.strftime('%d %b %Y')}"

    if available.empty:
        message = (
            "<b>Announcement coverage: MISSING.</b> No company-linked "
            "announcement dataset has been imported for this company. Zero "
            "markers must not be read as zero real-world announcements."
        )
        color = AMBER
    else:
        message = (
            f"<b>Announcement coverage: {html.escape(str(available.iloc[0]['coverage_status']))}.</b> "
            f"{len(selected)} matching record(s) in this view from "
            f"{len(available)} imported record(s) for the company."
        )
        color = GREEN

    return (
        f"<div style='padding:10px 12px;border-left:3px solid {color};"
        "background:#111823;border-radius:7px'>"
        f"<b>{html.escape(company.company_name)}</b> · "
        f"{html.escape(company.market_data_ticker)} · "
        f"{html.escape(company.role_category)} · {date_label}<br>"
        f"<span style='color:{MUTED};font-size:12px'>{message}</span></div>"
    )


def _announcement_register_html(announcements):
    if announcements.empty:
        return (
            "<div style='padding:12px;border:1px dashed #52667B;"
            "border-radius:8px;color:#A9B5C3'>No imported company-linked "
            "announcements match the current selection.</div>"
        )

    items = []

    for row in announcements.head(25).itertuples(index=False):
        details = " · ".join(
            value
            for value in (
                _label(row.announcement_type),
                str(row.counterparty_name or "").strip(),
                str(row.systems or "").strip(),
                str(row.value_description or "").strip(),
            )
            if value
        )
        audit = " · ".join(
            value
            for value in (
                str(row.record_scope or "").strip(),
                str(row.verification_status or "").strip(),
                str(row.source_name or "").strip(),
            )
            if value
        )
        items.append(
            "<li style='margin:0 0 8px'>"
            f"<b>{row.announcement_date.strftime('%d %b %Y')}</b> · "
            f"<a href='{html.escape(row.source_url, quote=True)}' "
            "target='_blank' rel='noreferrer'>"
            f"{html.escape(row.title)}</a>"
            + (f"<br><span style='color:{MUTED}'>{html.escape(details)}</span>" if details else "")
            + (f"<br><small style='color:{MUTED}'>{html.escape(audit)}</small>" if audit else "")
            + "</li>"
        )

    return (
        "<div style='padding:12px 14px;background:#111823;border:1px solid "
        "#344457;border-radius:9px'><h3 style='margin:0 0 8px'>Imported "
        "company announcements</h3><ul style='margin:0;padding-left:20px'>"
        + "".join(items)
        + "</ul></div>"
    )


def _filter_callback_code():
    metric_labels = "{" + ",".join(
        f"{key!r}:{value!r}" for key, value in _CONFLICT_METRICS.items()
    ) + "}"
    return f"""
const market = all_market_source.data;
const conflict = all_conflict_source.data;
const announcements = all_announcement_source.data;
const centcom = all_centcom_source.data;
const companies = company_directory_source.data;
const periods = period_source.data;
const companyId = company_filter.value;
const periodIndex = periods.period_id.indexOf(period_filter.value);
const start = Number(periods.start_date[periodIndex]);
const end = Number(periods.end_date[periodIndex]);
const metric = conflict_metric_filter.value;
const metricLabels = {metric_labels};
const companyIndex = companies.company_id.indexOf(companyId);
const name = String(companies.company_name[companyIndex]);
const ticker = String(companies.market_data_ticker[companyIndex]);
const benchmark = String(companies.benchmark_ticker[companyIndex]);
const role = String(companies.role_category[companyIndex]);

function subset(data, indices, columns=null) {{
    const output = {{}};
    const names = columns || Object.keys(data);
    for (const column of names) {{
        output[column] = indices.map((index) => data[column][index]);
    }}
    return output;
}}

function escapeHtml(value) {{
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}}

function label(value) {{
    return String(value ?? "")
        .toLowerCase()
        .split("_")
        .filter(Boolean)
        .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
        .join(" ");
}}

const marketIndices = [];
for (let index = 0; index < market.company_id.length; index++) {{
    const date = Number(market.Date[index]);
    if (market.company_id[index] === companyId && date >= start && date <= end) {{
        marketIndices.push(index);
    }}
}}

const marketData = subset(market, marketIndices);
const firstCompanyPrice = Number(marketData.company_price[0]);
const firstBenchmarkPrice = Number(marketData.benchmark_price[0]);
marketData.company_index = marketData.company_price.map(
    (value) => Number(value) / firstCompanyPrice * 100,
);
marketData.benchmark_index = marketData.benchmark_price.map(
    (value) => Number(value) / firstBenchmarkPrice * 100,
);
market_source.data = marketData;

const availableAnnouncementIndices = [];
const visibleAnnouncementIndices = [];
for (let index = 0; index < announcements.company_id.length; index++) {{
    if (announcements.company_id[index] !== companyId) continue;
    availableAnnouncementIndices.push(index);
    const date = Number(announcements.announcement_date[index]);
    const typeMatches = announcement_type_filter.value === "ALL"
        || announcements.announcement_type[index] === announcement_type_filter.value;
    if (date >= start && date <= end && typeMatches) {{
        visibleAnnouncementIndices.push(index);
    }}
}}

const announcementData = subset(announcements, visibleAnnouncementIndices);
const nearestMarketIndices = visibleAnnouncementIndices.map((announcementIndex) => {{
    const date = Number(announcements.announcement_date[announcementIndex]);
    let nearest = 0;
    let distance = Infinity;
    for (let index = 0; index < marketData.Date.length; index++) {{
        const candidate = Math.abs(Number(marketData.Date[index]) - date);
        if (candidate < distance) {{ distance = candidate; nearest = index; }}
    }}
    return nearest;
}});
announcementData.marker_y = nearestMarketIndices.map(
    (index) => marketData.company_index[index],
);
announcementData.aligned_market_date = nearestMarketIndices.map(
    (index) => marketData.Date[index],
);
announcementData.event_day_abnormal_return = nearestMarketIndices.map(
    (index) => marketData.abnormal_return[index],
);
announcement_source.data = announcementData;

for (let sourceIndex = 0; sourceIndex < conflict_sources.length; sourceIndex++) {{
    const countryCode = country_codes[sourceIndex];
    const indices = [];
    for (let index = 0; index < conflict.country_code.length; index++) {{
        const date = Number(conflict.week_end_date[index]);
        if (conflict.country_code[index] === countryCode && date >= start && date <= end) {{
            indices.push(index);
        }}
    }}
    const data = subset(conflict, indices);
    data.metric_value = indices.map((index) => Number(conflict[metric][index]));
    data.metric_label = indices.map(() => metricLabels[metric]);
    conflict_sources[sourceIndex].data = data;
    conflict_sources[sourceIndex].change.emit();
}}

const centcomIndices = [];
for (let index = 0; index < centcom.week_end_date.length; index++) {{
    const date = Number(centcom.week_end_date[index]);
    if (date >= start && date <= end) centcomIndices.push(index);
}}
centcom_source.data = subset(centcom, centcomIndices);

market_chart.title.text = `${{name}} (${{ticker}}) versus ${{benchmark}}: rebased price performance`;
conflict_chart.title.text = metricLabels[metric];
conflict_axis.axis_label = metricLabels[metric];

const dateFormat = new Intl.DateTimeFormat("en-GB", {{
    day: "2-digit", month: "short", year: "numeric", timeZone: "UTC",
}});
const dateLabel = `${{dateFormat.format(new Date(start))}}–${{dateFormat.format(new Date(end))}}`;
let coverageMessage;
let coverageColor;
if (availableAnnouncementIndices.length === 0) {{
    coverageColor = "{AMBER}";
    coverageMessage = "<b>Announcement coverage: MISSING.</b> No company-linked announcement dataset has been imported for this company. Zero markers must not be read as zero real-world announcements.";
}} else {{
    coverageColor = "{GREEN}";
    const coverage = escapeHtml(announcements.coverage_status[availableAnnouncementIndices[0]]);
    coverageMessage = `<b>Announcement coverage: ${{coverage}}.</b> ${{visibleAnnouncementIndices.length}} matching record(s) in this view from ${{availableAnnouncementIndices.length}} imported record(s) for the company.`;
}}
status.text = `<div style="padding:10px 12px;border-left:3px solid ${{coverageColor}};background:#111823;border-radius:7px"><b>${{escapeHtml(name)}}</b> · ${{escapeHtml(ticker)}} · ${{escapeHtml(role)}} · ${{dateLabel}}<br><span style="color:{MUTED};font-size:12px">${{coverageMessage}}</span></div>`;

if (visibleAnnouncementIndices.length === 0) {{
    announcement_register.text = '<div style="padding:12px;border:1px dashed #52667B;border-radius:8px;color:#A9B5C3">No imported company-linked announcements match the current selection.</div>';
}} else {{
    const items = visibleAnnouncementIndices.slice(0, 25).map((index) => {{
        const details = [
            label(announcements.announcement_type[index]),
            announcements.counterparty_name[index],
            announcements.systems[index],
            announcements.value_description[index],
        ].filter((value) => String(value ?? "").trim()).map(escapeHtml).join(" · ");
        const audit = [
            announcements.record_scope[index],
            announcements.verification_status[index],
            announcements.source_name[index],
        ].filter((value) => String(value ?? "").trim()).map(escapeHtml).join(" · ");
        const date = dateFormat.format(new Date(Number(announcements.announcement_date[index])));
        const detailLine = details ? `<br><span style="color:{MUTED}">${{details}}</span>` : "";
        const auditLine = audit ? `<br><small style="color:{MUTED}">${{audit}}</small>` : "";
        return `<li style="margin:0 0 8px"><b>${{date}}</b> · <a href="${{escapeHtml(announcements.source_url[index])}}" target="_blank" rel="noreferrer">${{escapeHtml(announcements.title[index])}}</a>${{detailLine}}${{auditLine}}</li>`;
    }}).join("");
    const capped = visibleAnnouncementIndices.length > 25
        ? `<p style="color:{MUTED};font-size:11px">Showing 25 of ${{visibleAnnouncementIndices.length}} matching records.</p>`
        : "";
    announcement_register.text = `<div style="padding:12px 14px;background:#111823;border:1px solid #344457;border-radius:9px"><h3 style="margin:0 0 8px">Imported company announcements</h3><ul style="margin:0;padding-left:20px">${{items}}</ul>${{capped}}</div>`;
}}

market_source.change.emit();
announcement_source.change.emit();
centcom_source.change.emit();
"""


def _style_chart(chart, legend=True):
    chart.toolbar.logo = None
    chart.grid.grid_line_alpha = 0.2

    if legend and chart.legend:
        chart.legend.location = "top_left"
        chart.legend.click_policy = "hide"
        chart.legend.label_text_font_size = "9pt"


def _label(value):
    return " ".join(
        part.capitalize() for part in str(value).split("_") if part
    )


def _boolean_value(value):
    if isinstance(value, bool):
        return value

    return str(value).strip().casefold() in {"true", "1", "yes", "y"}


def build_parser():
    parser = argparse.ArgumentParser(
        description="Create the BLACK DOVES company-announcement explorer."
    )
    parser.add_argument("market_file", type=Path)
    parser.add_argument("conflict_file", type=Path)
    parser.add_argument("announcement_file", type=Path)
    parser.add_argument("centcom_file", type=Path)
    parser.add_argument("output_file", type=Path)
    parser.add_argument("--logo", type=Path)
    return parser


def main(arguments=None):
    options = build_parser().parse_args(arguments)

    try:
        output = create_company_announcement_dashboard(
            market_file=options.market_file,
            conflict_file=options.conflict_file,
            announcement_file=options.announcement_file,
            centcom_file=options.centcom_file,
            output_path=options.output_file,
            logo_path=options.logo,
        )
    except (FileNotFoundError, TypeError, ValueError) as error:
        raise SystemExit(str(error)) from error

    print("BLACK DOVES company-announcement explorer saved to:", output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
