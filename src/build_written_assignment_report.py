"""Build the submission-safe, offline written-assignment report.

This report intentionally omits incomplete or methodologically unsuitable
prototype modules (2026 ACLED aggregates, unreviewed media classifications,
casualty compilations and incomplete company-announcement coverage).  It uses
only the auditable core tables and embeds Bokeh locally, so no network access
is required to read the charts.
"""

from __future__ import annotations

import base64
import html
import sqlite3

from datetime import date
from pathlib import Path

import pandas as pd
from bokeh.embed import components
from bokeh.models import (
    ColumnDataSource,
    FixedTicker,
    HoverTool,
    NumeralTickFormatter,
    Span,
)
from bokeh.plotting import figure
from bokeh.resources import INLINE
from bokeh.transform import dodge


ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "data" / "analysis"
REFERENCE = ROOT / "data" / "reference"
PROCESSED = ROOT / "data" / "processed"
VALIDATED = ROOT / "data" / "validated"
OUTPUT_FILE = ROOT / "output" / "black_doves_written_assignment_report.html"

BACKGROUND = "#0b1220"
PANEL = "#111827"
TEXT = "#e5e7eb"
MUTED = "#9ca3af"
GRID = "#334155"
TEAL = "#2dd4bf"
GOLD = "#f59e0b"
BLUE = "#60a5fa"
PINK = "#f472b6"
RED = "#fb7185"
PURPLE = "#a78bfa"
SERIES_COLORS = (TEAL, GOLD, BLUE, PINK, PURPLE)


def main():
    data = _load_data()
    charts = _create_charts(data)
    script, divs = components(charts)
    report = _report_html(data, script, divs)
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT_FILE.with_suffix(".html.tmp")
    temporary.write_text(report, encoding="utf-8")
    temporary.replace(OUTPUT_FILE)
    print(OUTPUT_FILE)
    return 0


def _load_data():
    files = {
        "event_window": ANALYSIS / "market_universe_event_window.csv",
        "company_short": ANALYSIS / "market_universe_company_summary.csv",
        "bootstrap": ANALYSIS / "event_study_bootstrap_summary.csv",
        "company_long": ANALYSIS / "market_position_company_summary.csv",
        "timeline": PROCESSED / "energy" / "energy_price_timeline.csv",
        "weekly_energy": PROCESSED / "energy" / "energy_price_weekly_panel.csv",
        "lags": ANALYSIS / "fuel_price_lag_adjusted.csv",
        "dependency": REFERENCE / "iran_china_oil_dependency.csv",
        "arms": REFERENCE / "arms_supply_context.csv",
        "roles": REFERENCE / "country_role_profile.csv",
        "ucdp": REFERENCE / "ucdp_method_reference.csv",
        "centcom": VALIDATED / "centcom_us_strike_operation_days.csv",
        "procurement": ANALYSIS / "rheinmetall_procurement_event_summary.csv",
        "post_hoc": ANALYSIS / "post_hoc_market_checks.csv",
        "blackrock": REFERENCE / "blackrock_13f_holdings.csv",
        "patriot": REFERENCE / "patriot_supply_context.csv",
        "findings_audit": REFERENCE / "additional_findings_audit.csv",
        "media_audit": REFERENCE / "media_sampling_audit.csv",
    }
    missing = [str(path) for path in files.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(
            "Report inputs are missing: " + ", ".join(missing)
        )
    result = {name: pd.read_csv(path) for name, path in files.items()}
    result["timeline"]["observation_date"] = pd.to_datetime(
        result["timeline"]["observation_date"]
    )
    return result


def _create_charts(data):
    return {
        "short_event": _short_event_chart(data["event_window"]),
        "long_horizon": _long_horizon_chart(data["company_long"]),
        "energy": _energy_chart(data["timeline"]),
        "lags": _lag_chart(data["lags"]),
    }


def _short_event_chart(event_window):
    selected = event_window[
        event_window["sample_group"].isin(
            ["CONFIRMATORY", "EXPLORATORY"]
        )
        & event_window["relative_trading_day"].between(0, 10)
    ].copy()
    summary = (
        selected.groupby(
            ["sample_group", "relative_trading_day"], sort=True
        )["abnormal_return"]
        .mean()
        .rename("aar")
        .reset_index()
    )
    summary["post_event_caar_pct"] = (
        summary.groupby("sample_group")["aar"].cumsum() * 100.0
    )

    chart = figure(
        title="Post-event cumulative average abnormal return",
        width=1050,
        height=390,
        sizing_mode="stretch_width",
        x_axis_label="Trading day relative to 2 March 2026",
        y_axis_label="CAAR from day 0 (%)",
        tools="pan,wheel_zoom,box_zoom,reset,save",
        active_scroll="wheel_zoom",
    )
    for group, color, label in (
        ("CONFIRMATORY", TEAL, "Confirmatory (n=8)"),
        ("EXPLORATORY", GOLD, "Exploratory (n=37)"),
    ):
        group_data = summary[summary["sample_group"] == group]
        source = ColumnDataSource(group_data)
        line = chart.line(
            "relative_trading_day",
            "post_event_caar_pct",
            source=source,
            line_width=3,
            color=color,
            legend_label=label,
        )
        points = chart.scatter(
            "relative_trading_day",
            "post_event_caar_pct",
            source=source,
            size=7,
            color=color,
        )
        chart.add_tools(
            HoverTool(
                renderers=[line, points],
                tooltips=[
                    ("Sample", label),
                    ("Trading day", "@relative_trading_day"),
                    ("CAAR", "@post_event_caar_pct{0.00}%"),
                ],
                mode="vline",
            )
        )
    chart.add_layout(
        Span(
            location=0,
            dimension="height",
            line_color=RED,
            line_dash="dashed",
            line_width=2,
        )
    )
    chart.xaxis.ticker = FixedTicker(ticks=list(range(0, 11)))
    _style_chart(chart)
    return chart


def _long_horizon_chart(company_long):
    selected = company_long[_boolean_mask(company_long["is_confirmatory"])].copy()
    selected = selected.sort_values("post_bhar")
    selected["company_label"] = selected["company_name"].map(_short_company)
    selected["bhar_pct"] = selected["post_bhar"] * 100.0
    selected["ols_pct"] = selected["post_ols_car"] * 100.0
    source = ColumnDataSource(selected)
    labels = selected["company_label"].tolist()
    chart = figure(
        title="Long-horizon benchmark-relative performance",
        width=1050,
        height=470,
        sizing_mode="stretch_width",
        y_range=labels,
        x_axis_label="Return difference / cumulative abnormal return (%)",
        tools="pan,wheel_zoom,box_zoom,reset,save",
        active_scroll="wheel_zoom",
    )
    bars_bhar = chart.hbar(
        y=dodge("company_label", -0.18, range=chart.y_range),
        right="bhar_pct",
        height=0.30,
        source=source,
        color=TEAL,
        legend_label="BHAR (preferred long-horizon measure)",
    )
    bars_ols = chart.hbar(
        y=dodge("company_label", 0.18, range=chart.y_range),
        right="ols_pct",
        height=0.30,
        source=source,
        color=GOLD,
        legend_label="OLS CAR (sensitivity)",
    )
    chart.add_tools(
        HoverTool(
            renderers=[bars_bhar, bars_ols],
            tooltips=[
                ("Company", "@company_name"),
                ("BHAR", "@bhar_pct{0.00}%"),
                ("OLS CAR", "@ols_pct{0.00}%"),
                ("Observations", "@post_observations"),
            ],
        )
    )
    chart.add_layout(
        Span(location=0, dimension="height", line_color=MUTED, line_width=1)
    )
    _style_chart(chart)
    chart.ygrid.grid_line_color = None
    return chart


def _energy_chart(timeline):
    chart = figure(
        title="Brent and German fuel prices, indexed to first observation",
        width=1050,
        height=430,
        sizing_mode="stretch_width",
        x_axis_type="datetime",
        x_axis_label="Observation date",
        y_axis_label="Index (first observation = 100)",
        tools="pan,wheel_zoom,box_zoom,reset,save",
        active_scroll="wheel_zoom",
    )
    for color, (series_id, series) in zip(
        SERIES_COLORS,
        timeline.groupby("series_id", sort=True),
    ):
        source = ColumnDataSource(series)
        line = chart.line(
            "observation_date",
            "indexed_value",
            source=source,
            line_width=2.4,
            color=color,
            legend_label=str(series["series_label"].iloc[0]),
        )
        chart.add_tools(
            HoverTool(
                renderers=[line],
                tooltips=[
                    ("Series", "@series_label"),
                    ("Date", "@observation_date{%F}"),
                    ("Value", "@value{0.000} @unit"),
                    ("Index", "@indexed_value{0.0}"),
                ],
                formatters={"@observation_date": "datetime"},
                mode="vline",
            )
        )
    chart.add_layout(
        Span(
            location=pd.Timestamp("2026-03-02").timestamp() * 1000,
            dimension="height",
            line_color=RED,
            line_dash="dashed",
            line_width=2,
        )
    )
    _style_chart(chart)
    chart.legend.click_policy = "hide"
    chart.legend.label_text_font_size = "9pt"
    return chart


def _lag_chart(lags):
    chart = figure(
        title="Exploratory Brent-to-German-fuel associations",
        width=1050,
        height=430,
        sizing_mode="stretch_width",
        x_axis_label="Fuel-price lag after Brent week (weeks)",
        y_axis_label="Spearman correlation",
        y_range=(-0.65, 0.75),
        tools="pan,wheel_zoom,box_zoom,reset,save",
        active_scroll="wheel_zoom",
    )
    for color, ((product, tax_basis), group) in zip(
        SERIES_COLORS,
        lags.groupby(["product", "tax_basis"], sort=True),
    ):
        label = f"{product.title()} – {tax_basis.replace('_', ' ').title()}"
        group = group.sort_values("lag_weeks").copy()
        source = ColumnDataSource(group)
        line = chart.line(
            "lag_weeks",
            "spearman_correlation",
            source=source,
            line_width=2.4,
            color=color,
            legend_label=label,
        )
        points = chart.scatter(
            "lag_weeks",
            "spearman_correlation",
            source=source,
            size=8,
            color=color,
        )
        significant = group[
            _boolean_mask(group["spearman_significant_holm_0_05"])
        ]
        if not significant.empty:
            chart.scatter(
                "lag_weeks",
                "spearman_correlation",
                source=ColumnDataSource(significant),
                marker="star",
                size=18,
                color=color,
                line_color=TEXT,
                line_width=1,
            )
        chart.add_tools(
            HoverTool(
                renderers=[line, points],
                tooltips=[
                    ("Series", label),
                    ("Lag", "@lag_weeks weeks"),
                    ("Spearman rho", "@spearman_correlation{0.000}"),
                    ("Raw p", "@spearman_p_value{0.0000}"),
                    ("Holm p", "@spearman_p_value_holm{0.0000}"),
                    ("Observations", "@observations"),
                ],
            )
        )
    chart.xaxis.ticker = FixedTicker(ticks=list(range(9)))
    chart.add_layout(
        Span(location=0, dimension="width", line_color=MUTED, line_width=1)
    )
    _style_chart(chart)
    chart.legend.click_policy = "hide"
    chart.legend.label_text_font_size = "9pt"
    return chart


def _style_chart(chart):
    chart.background_fill_color = PANEL
    chart.border_fill_color = PANEL
    chart.outline_line_color = GRID
    chart.title.text_color = TEXT
    chart.title.text_font_size = "15pt"
    chart.title.text_font_style = "bold"
    chart.axis.axis_label_text_color = MUTED
    chart.axis.major_label_text_color = TEXT
    chart.axis.axis_line_color = GRID
    chart.axis.major_tick_line_color = GRID
    chart.axis.minor_tick_line_color = GRID
    chart.grid.grid_line_color = GRID
    chart.grid.grid_line_alpha = 0.35
    chart.legend.background_fill_color = BACKGROUND
    chart.legend.background_fill_alpha = 0.8
    chart.legend.border_line_color = GRID
    chart.legend.label_text_color = TEXT
    chart.toolbar.logo = None


def _report_html(data, bokeh_script, divs):
    company_short = data["company_short"]
    confirmatory_short = company_short[
        company_short["sample_group"] == "CONFIRMATORY"
    ].copy()
    bootstrap = data["bootstrap"]
    company_long = data["company_long"]
    confirmatory_long = company_long[
        _boolean_mask(company_long["is_confirmatory"])
    ].copy()
    lags = data["lags"]
    weekly = data["weekly_energy"]
    centcom = data["centcom"]
    procurement = data["procurement"]
    post_hoc = data["post_hoc"]
    blackrock = data["blackrock"]
    patriot = data["patriot"]
    findings_audit = data["findings_audit"]

    event_day = _bootstrap_row(
        bootstrap, "event_day_abnormal_return", "MEAN", "CONFIRMATORY"
    )
    car_10 = _bootstrap_row(
        bootstrap, "post_event_car_0_10", "MEAN", "CONFIRMATORY"
    )
    car_difference = _bootstrap_row(
        bootstrap,
        "post_event_car_0_10",
        "DIFFERENCE_IN_MEANS",
        "CONFIRMATORY",
    )
    mean_bhar = float(confirmatory_long["post_bhar"].mean())
    positive_bhar = int((confirmatory_long["post_bhar"] > 0).sum())
    core_centcom = centcom[_boolean_mask(centcom["include_in_core_series"])]
    lag_zero = lags[lags["lag_weeks"] == 0].copy()
    pre_tax_significant = int(
        _boolean_mask(
            lag_zero["spearman_significant_holm_0_05"]
        ).sum()
    )

    logo = _embedded_logo()
    short_table = _short_company_table(confirmatory_short)
    bootstrap_table = _bootstrap_table(bootstrap)
    long_table = _long_company_table(confirmatory_long)
    lag_table = _lag_summary_table(lag_zero)
    role_table = _role_table(data["roles"])
    dependency_table = _dependency_table(data["dependency"])
    arms_table = _arms_table(data["arms"])
    ucdp_table = _ucdp_table(data["ucdp"])
    procurement_table = _procurement_table(procurement)
    centcom_table = _centcom_table(core_centcom)
    market_model_table = _market_model_diagnostic_table(company_short)
    post_hoc_table = _post_hoc_market_table(post_hoc)
    blackrock_table = _blackrock_table(blackrock)
    patriot_table = _patriot_table(patriot)
    findings_audit_table = _findings_audit_table(findings_audit)
    register_table = _database_register_table()

    blackrock_short = _company_row(company_short, "CMP005")
    blackrock_long = _company_row(company_long, "CMP005")
    july_defence = _post_hoc_row(
        post_hoc, "PHM_RHEINMETALL_JULY", "ALL_DEFENCE"
    )
    july_rheinmetall = _post_hoc_row(
        post_hoc, "PHM_RHEINMETALL_JULY", "RHEINMETALL"
    )
    pentagon_us_defence = _post_hoc_row(
        post_hoc, "PHM_PENTAGON_PRODUCTION", "US_DEFENCE_SP500"
    )
    pentagon_us_controls = _post_hoc_row(
        post_hoc,
        "PHM_PENTAGON_PRODUCTION",
        "US_NON_DEFENCE_SP500",
    )

    brent_change = _first_last_change(weekly, "brent_usd_per_barrel")
    petrol_change = _first_last_change(
        weekly, "petrol_with_tax_eur_per_liter"
    )
    diesel_change = _first_last_change(
        weekly, "diesel_with_tax_eur_per_liter"
    )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>BLACK DOVES — Written Assignment Report</title>
{INLINE.render_js()}
<style>
:root{{--bg:{BACKGROUND};--panel:{PANEL};--panel2:#172033;--text:{TEXT};--muted:{MUTED};--line:{GRID};--teal:{TEAL};--gold:{GOLD};--red:{RED};--blue:{BLUE};}}
*{{box-sizing:border-box}}
html{{scroll-behavior:smooth}}
body{{margin:0;background:var(--bg);color:var(--text);font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;line-height:1.58}}
a{{color:#7dd3fc;text-decoration:none}}a:hover{{text-decoration:underline}}
.shell{{max-width:1180px;margin:auto;padding:0 28px 80px}}
.hero{{padding:50px 0 32px;border-bottom:1px solid var(--line)}}
.brand{{display:flex;align-items:center;gap:18px;margin-bottom:28px}}.brand img{{width:72px;height:72px;object-fit:contain}}.brand-label{{letter-spacing:.18em;text-transform:uppercase;color:var(--teal);font-weight:800;font-size:.78rem}}
h1{{font-size:clamp(2.25rem,5vw,4.8rem);line-height:1.02;max-width:1040px;margin:0 0 20px;letter-spacing:-.045em}}
h2{{font-size:clamp(1.65rem,3vw,2.5rem);line-height:1.15;margin:0 0 14px;letter-spacing:-.025em}}h3{{font-size:1.18rem;margin:0 0 8px}}
.lede{{font-size:1.2rem;max-width:950px;color:#cbd5e1;margin:0 0 24px}}
.meta,.chips{{display:flex;gap:10px;flex-wrap:wrap}}.chip{{border:1px solid var(--line);background:var(--panel);border-radius:999px;padding:7px 12px;color:#cbd5e1;font-size:.83rem}}
nav{{position:sticky;top:0;z-index:20;background:rgba(11,18,32,.94);backdrop-filter:blur(12px);border-bottom:1px solid var(--line);margin:0 -28px;padding:11px 28px;display:flex;gap:18px;overflow:auto;white-space:nowrap}}nav a{{font-size:.82rem;color:#cbd5e1}}
section{{padding:54px 0;border-bottom:1px solid var(--line)}}
.section-kicker{{text-transform:uppercase;letter-spacing:.15em;font-size:.72rem;font-weight:800;color:var(--teal);margin-bottom:10px}}
.grid{{display:grid;grid-template-columns:repeat(12,1fr);gap:16px}}.card{{background:linear-gradient(145deg,var(--panel),#101a2d);border:1px solid var(--line);border-radius:16px;padding:20px;box-shadow:0 12px 34px rgba(0,0,0,.16)}}
.metric{{grid-column:span 3;min-height:170px}}.metric .value{{font-size:2rem;line-height:1.1;font-weight:850;color:var(--teal);margin:12px 0 8px}}.metric .value.gold{{color:var(--gold)}}.metric .value.red{{color:var(--red)}}.metric p,.note,p.muted{{color:#aeb9c9;margin:.35em 0;font-size:.93rem}}
.wide{{grid-column:span 8}}.narrow{{grid-column:span 4}}.half{{grid-column:span 6}}
.callout{{border-left:4px solid var(--gold);background:rgba(245,158,11,.08);padding:16px 18px;border-radius:0 12px 12px 0;margin:20px 0;color:#dbe4f0}}.callout.danger{{border-color:var(--red);background:rgba(251,113,133,.08)}}.callout.good{{border-color:var(--teal);background:rgba(45,212,191,.08)}}
.chart{{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:14px;margin:22px 0;overflow:hidden}}
.table-wrap{{overflow:auto;border:1px solid var(--line);border-radius:14px;margin:18px 0;background:var(--panel)}}table{{border-collapse:collapse;width:100%;font-size:.83rem}}th{{position:sticky;top:0;background:#172033;color:#dce6f5;text-align:left;padding:11px 12px;border-bottom:1px solid var(--line);white-space:nowrap}}td{{padding:10px 12px;border-bottom:1px solid rgba(51,65,85,.62);vertical-align:top}}tr:last-child td{{border-bottom:0}}tbody tr:hover{{background:rgba(96,165,250,.045)}}
.status{{display:inline-block;border-radius:999px;padding:3px 8px;font-size:.7rem;font-weight:800;letter-spacing:.04em}}.status.ok{{background:rgba(45,212,191,.13);color:#5eead4}}.status.caution{{background:rgba(245,158,11,.13);color:#fbbf24}}.status.no{{background:rgba(251,113,133,.13);color:#fda4af}}
.formula{{font-family:"SFMono-Regular",Consolas,monospace;background:#0a1020;border:1px solid var(--line);padding:13px 15px;border-radius:10px;overflow:auto;color:#c4b5fd}}
details{{background:var(--panel);border:1px solid var(--line);border-radius:12px;margin:10px 0;padding:13px 16px}}summary{{cursor:pointer;font-weight:750}}
.sources li{{margin:.45em 0}}footer{{padding:38px 0;color:var(--muted);font-size:.84rem}}
@media(max-width:850px){{.metric,.wide,.narrow,.half{{grid-column:span 12}}.shell{{padding-left:18px;padding-right:18px}}nav{{margin-left:-18px;margin-right:-18px;padding-left:18px}}}}
@media print{{body{{background:white;color:#111}}nav{{display:none}}.shell{{max-width:none}}section{{break-inside:auto}}.card,.chart,.table-wrap,details{{background:white;color:#111;box-shadow:none;border-color:#bbb}}a{{color:#075985}}.metric p,.note,p.muted{{color:#444}}}}
</style>
</head>
<body>
<div class="shell">
<header class="hero">
  <div class="brand">{logo}<div><div class="brand-label">BLACK DOVES / submission edition</div><div class="note">Reproducible Python analysis · generated {date.today().isoformat()}</div></div></div>
  <h1>Tracing the Economic Effects of the 2026 Israel–Iran–United States Conflict</h1>
  <p class="lede">An object-oriented Python framework linking state roles, sectoral returns, Brent crude oil and German consumer fuel prices.</p>
  <div class="meta"><span class="chip">Core period · 1 Jan–18 Aug 2026</span><span class="chip">Event · 28 Feb 2026</span><span class="chip">Effective market date · 2 Mar 2026</span><span class="chip">8 confirmatory companies</span><span class="chip">37 exploratory controls</span><span class="chip">Offline Bokeh report</span></div>
</header>
<nav><a href="#findings">Findings</a><a href="#design">Design</a><a href="#roles">State roles</a><a href="#markets">Markets</a><a href="#energy">Energy</a><a href="#dependency">Dependency</a><a href="#ownership">Ownership</a><a href="#operations">Operations</a><a href="#methods">Methods</a><a href="#questions">Open questions</a><a href="#audit">Audit</a></nav>

<section id="findings">
  <div class="section-kicker">Answer first</div><h2>What the evidence supports</h2>
  <div class="grid">
    <article class="card metric"><h3>Event-day AAR</h3><div class="value">{_pct(event_day.estimate)}</div><p>Confirmatory n=8; 95% percentile-bootstrap interval {_ci(event_day)}.</p></article>
    <article class="card metric"><h3>CAR [0,+10]</h3><div class="value">{_pct(car_10.estimate)}</div><p>Market-adjusted mean; 95% interval {_ci(car_10)}.</p></article>
    <article class="card metric"><h3>Specificity test</h3><div class="value gold">{_pp(car_difference.estimate)}</div><p>Confirmatory minus exploratory CAR; interval {_ci_pp(car_difference)} includes zero.</p></article>
    <article class="card metric"><h3>Post-event BHAR</h3><div class="value red">{_pct(mean_bhar)}</div><p>Mean through 18 Aug; {positive_bhar}/8 companies positive. Long-run performance is mixed.</p></article>
  </div>
  <div class="callout good"><strong>Core conclusion.</strong> The pre-specified companies show a positive short-window market reaction, but the exploratory universe moved by a similar amount. The design therefore supports a broad conflict-period market association—not a company-selection-specific effect and not a causal estimate.</div>
  <div class="callout"><strong>What the late evidence changes.</strong> It strengthens three contextual points without changing the core estimate: market-model betas differ sharply across firms; the 1–2 July defence rally was sector-wide rather than uniquely Rheinmetall; and a regulatory filing verifies a common BlackRock-managed ownership layer. The Pentagon production report is a credible timing anchor, but its 10 August return pattern is not specific to defence firms in this panel.</div>
  <div class="grid">
    <article class="card half"><h3>Energy channel</h3><p>Across the aligned weekly endpoints, Brent rose {_pct(brent_change)}, German petrol including tax {_pct(petrol_change)}, and diesel including tax {_pct(diesel_change)}. The strongest rank correlations occur contemporaneously at lag 0. After Holm correction, {pre_tax_significant}/4 lag-0 series remain significant—both before-tax series; delayed lags 1–8 do not provide a robust transmission peak.</p></article>
    <article class="card half"><h3>Dependency and operational record</h3><p>Independent tracking and official estimates place China at more than 80% to about 90% of Iranian oil exports, while Iranian oil represented 13.4% of China’s seaborne imports in Kpler’s 2025 estimate. The dependency is asymmetric. CENTCOM provides {len(core_centcom)} core operation-day observations, but these are official U.S. claims rather than independent conflict-event counts.</p></article>
  </div>
</section>

<section id="design">
  <div class="section-kicker">Research design</div><h2>Pre-specified event, transparent estimands</h2>
  <p>The research question asks how direct participation, arms-supply context, political positioning and economic dependency were associated with company abnormal returns, Brent prices and German consumer fuel prices. Country roles overlap and are not collapsed into a single score. With only five focal countries, the role profile is qualitative context rather than a cross-country regression.</p>
  <div class="grid"><article class="card wide"><h3>Event-study design</h3><p>The calendar event is Saturday, 28 February 2026. Because markets were closed, the first effective trading date is Monday, 2 March. The confirmatory window is five trading days before through ten trading days after. The OLS single-factor market model uses all available pre-event observations from the downloaded history; this avoids look-ahead but has no pre-event gap.</p><div class="formula">ARᵢₜ = Rᵢₜ − Rₘₜ &nbsp;&nbsp; | &nbsp;&nbsp; OLS ARᵢₜ = Rᵢₜ − (αᵢ + βᵢRₘₜ) &nbsp;&nbsp; | &nbsp;&nbsp; CAR = Σ ARᵢₜ</div></article><article class="card narrow"><h3>Long horizon</h3><p>For 2 March–18 August, BHAR is preferred because it compares compounded returns:</p><div class="formula">BHAR = Π(1+Rᵢₜ) − Π(1+Rₘₜ)</div><p class="note">CAR remains as a sensitivity metric, not the headline long-run measure.</p></article></div>
  <div class="callout"><strong>Market-data provenance correction.</strong> The supplied files were downloaded through <code>yfinance</code>/Yahoo Finance for exchange-listed instruments; they are not direct files from Nasdaq, Xetra or TASE. The report labels them accordingly. A final university submission should replace or independently verify these snapshots if the approved proposal strictly requires official-exchange delivery.</div>
  <div class="callout danger"><strong>Direct Israel–Germany channel not identified.</strong> Israeli decisions and German market outcomes are present as separate evidence layers, but no pre-specified Israeli announcement series is linked to German target assets. A bilateral claim would require a separate event design with verified timestamps, German securities and benchmarks, and controls for oil, interest rates and sector-wide defence news. Parallel narratives are not evidence of a direct effect.</div>
  <p class="note">The endpoint remains 18 August 2026 even though some raw market histories continue to 2 September and supplied media files to 14 September. Moving the endpoint after inspecting later dramatic stories would alter the approved design.</p>
  <h3>UCDP scope</h3><p>UCDP terminology supplies the conflict-definition and historical-actor framework promised in the proposal. The annual UCDP/PRIO and Actor releases are catalogued as version 26.1, but no UCDP row enters the 2026 statistical analysis. The focal event and country roles are therefore researcher-specified from dated official statements, not presented as UCDP-coded observations.</p>{ucdp_table}
</section>

<section id="roles">
  <div class="section-kicker">Multidimensional context</div><h2>Country-role profile</h2>
  <p>No role label is treated as mutually exclusive. Arms shares cover SIPRI major-arms transfers in 2021–25 and therefore establish pre-conflict exposure—not transfers made during the focal conflict.</p>{role_table}
</section>

<section id="markets">
  <div class="section-kicker">Market evidence</div><h2>Short-window results are positive but not specific</h2>
  <div class="chart">{divs['short_event']}</div>
  <p>The chart resets cumulative abnormal returns at trading day 0, avoiding contamination from the pre-event portion of the display window. Both samples rise together; the bootstrap difference interval includes zero for the event day, market-adjusted CAR and OLS CAR.</p>
  <h3>Eight pre-specified companies</h3>{short_table}
  <h3>Market-model diagnostics: beta is not conflict sensitivity</h3>
  <p>Pre-event beta measures historical co-movement with each company’s configured broad-market benchmark. Lockheed Martin, Northrop Grumman and RTX have low betas, but also very low R² values: the one-factor benchmark explains little of their daily return variation. Palantir and NVIDIA have betas above two and materially higher R². This is precisely why a naive return-minus-index calculation and an OLS market model need to be shown separately; neither specification is automatically the truth.</p>{market_model_table}
  <div class="callout"><strong>Interpretation.</strong> A low beta does not show that a defence firm is “war-sensitive but market-independent.” It shows low estimated broad-market loading in the pre-event window. When R² is near zero, residual returns can contain sector, company and other omitted shocks as well as any conflict-related component.</div>
  <details><summary>Bootstrap intervals and between-sample differences</summary>{bootstrap_table}<p class="note">50,000 resamples, deterministic seed. Intervals resample firms cross-sectionally and do not solve omitted-variable, dependence or event-confounding problems.</p></details>
  <h3>Long horizon: mixed performance</h3><div class="chart">{divs['long_horizon']}</div>{long_table}
  <div class="callout danger"><strong>Interpretation boundary.</strong> A long-horizon return through 18 August absorbs many company-specific, sectoral, macroeconomic and policy events. Quartile shifts and BHAR are descriptive; they must not be presented as the effect of the 28 February event.</div>
  <h3>Post-hoc mechanism checks</h3>
  <p>The unusually clean Rheinmetall movement on 1–2 July is real in the stored prices, but not unique: all {int(july_defence.positive_every_market_day_count)} of {int(july_defence.company_count)} defence companies were positive on both days and their mean two-day market-adjusted return was {_pct(july_defence.mean_market_adjusted_return)}; Rheinmetall recorded {_pct(july_rheinmetall.mean_market_adjusted_return)}. This supports a sector-wide component, not a sole-announcement explanation.</p>
  <p>The Associated Press production report appeared on Sunday, 9 August, making Monday the first eligible trading day. All four U.S. defence primes benchmarked to the S&amp;P 500 were positive, averaging {_pct(pentagon_us_defence.mean_market_adjusted_return)}. However, the fourteen non-defence S&amp;P-benchmarked companies averaged {_pct(pentagon_us_controls.mean_market_adjusted_return)}. The timing is plausible, but the panel does not show a defence-specific response.</p>{post_hoc_table}
  <p class="note">These checks were specified after inspecting later reports. They are retained because they test attractive narratives against complete comparison groups; they are explicitly post hoc and carry no confirmatory p-value.</p>
</section>

<section id="energy">
  <div class="section-kicker">Oil and consumer costs</div><h2>Large co-movement, weak evidence of a delayed peak</h2>
  <div class="chart">{divs['energy']}</div>
  <p>Indexed levels communicate scale but do not identify transmission. Weekly change correlations test lags 0–8. The star marker denotes a Spearman p-value below .05 after Holm correction within the nine-lag family for that product/tax series.</p>
  <div class="chart">{divs['lags']}</div>{lag_table}
  <p class="note">Before-tax correlations are stronger than tax-inclusive correlations, which is consistent with taxes dampening percentage movements in retail prices. This is an interpretation, not a causal estimate. EUR/USD movements, refining margins, inventories, regulation, demand and weekly autocorrelation remain uncontrolled.</p>
</section>

<section id="dependency">
  <div class="section-kicker">Economic dependency</div><h2>Iran–China oil exposure is asymmetric</h2>
  <p>Sanctions, ship-to-ship transfers and indirect routes make customs records incomplete. All shares below are explicitly stored as estimates with denominator and reference period.</p>{dependency_table}
  <p>Iran’s seller concentration is very high, but the reverse exposure is much smaller: Kpler’s 2025 estimate puts Iranian oil at 13.4% of China’s seaborne oil imports. “China buys 80–90%” therefore describes Iran’s export denominator, not China’s total oil demand.</p>
  <h3>Arms-supply context</h3>{arms_table}
</section>

<section id="ownership">
  <div class="section-kicker">Institutional ownership layer</div><h2>BlackRock links issuer categories—but does not prove profit or influence</h2>
  <p>The company taxonomy classifies what issuers do; it does not imply that finance, defence and oil firms are ownership-independent. BlackRock’s official Q2 2026 Form 13F combination report verifies managed positions in four focal U.S. issuers. The table sums all filing rows sharing each CUSIP and deliberately omits ownership percentages, which require a separately matched shares-outstanding denominator.</p>{blackrock_table}
  <p>The regulatory filing also states that BlackRock, Inc. is the parent of reporting investment managers and disclaims investment discretion over positions managed by those subsidiaries. The reported securities are therefore predominantly managed fund and client assets—not equivalent to BlackRock’s own balance-sheet investment, revenue or profit.</p>
  <div class="grid"><article class="card half"><h3>BlackRock share-price comparator</h3><p>BlackRock itself recorded a market-adjusted CAR [0,+10] of {_pct(blackrock_short.post_event_car_0_10)} and OLS CAR of {_pct(blackrock_short.ols_post_event_car_0_10)}. Its long-horizon BHAR through 18 August was {_pct(blackrock_long.post_bhar)}. Those descriptive returns do not support a simple claim that common holdings translated into superior performance for BlackRock shareholders.</p></article><article class="card half"><h3>What a real ownership study would require</h3><p>A defensible mark-to-market extension would use consecutive regulatory holdings snapshots, split-adjusted shares outstanding, security-level prices and explicit treatment of trading between quarter ends. Holding the 30 June share counts fixed over earlier dates would only be a hypothetical portfolio calculation—not BlackRock’s realised gain.</p></article></div>
</section>

<section id="operations">
  <div class="section-kicker">Official operational record</div><h2>CENTCOM series retained; ACLED 2026 removed</h2>
  <h3>Patriot replenishment: a documented mechanism, not an equity effect</h3>
  <p>CSIS estimated that Patriot interceptor stocks fell from a pre-war baseline of 2,330 to 759–827 by late July, a decline of at least 65%. This is one open-source estimate, not an official inventory count; repetition by news outlets does not create independent estimates. AP separately reported the Pentagon’s production-acceleration request. Product attribution is split: RTX/Raytheon supplies GEM-T, while Lockheed Martin supplies PAC-3 MSE. The evidence therefore supports a replenishment and capacity channel relevant to both companies—not a sole-RTX demand shock and not a causal return estimate.</p>{patriot_table}
  <p>The retained operational series counts release-confirmed days, not individual strikes, targets or fatalities. Multiple targets on one day still equal one operation day. It is suitable for documenting U.S. self-reported activity, not for measuring total conflict intensity.</p>{centcom_table}
  <h3>Exploratory procurement check</h3><p>Five curated Rheinmetall air-defence announcements yield a mean market-adjusted CAR [0,+10] of {_pct(procurement['post_event_car_0_10'].mean())}. Four have a valid OLS estimate; their mean OLS CAR is {_pct(procurement['ols_post_event_car_0_10'].mean())}. Both aggregate means are negative, so the small series does not support a general positive procurement-announcement effect. The Italian record is dated 15 January <strong>2025</strong> and concerns <strong>Skynex</strong>, not Skyranger: event-day abnormal return was −1.28%, followed by +4.12% on day +1. Irregular signs and lags are realistic, but they are not a provenance test.</p>{procurement_table}
</section>

<section id="methods">
  <div class="section-kicker">Implementation</div><h2>Reproducible object-oriented Python framework</h2>
  <div class="grid"><article class="card half"><h3>Object model and analysis</h3><p><code>Actor</code> is specialized into <code>Country</code> and <code>Company</code>; <code>Observation</code> into role, price and impact observations. Abstract source adapters support RSS, HTML, GDELT, broadcast CSV and USAspending inputs. Service classes isolate OLS, event-study, lag, validation and robustness logic.</p></article><article class="card half"><h3>Persistence and validation</h3><p>SQLAlchemy maps <code>DatasetManifest</code> and <code>AnalysisRecord</code> to SQLite. Every stored row retains reporting period, unit, source, status and its original JSON payload. CSV imports are checksum-tracked, transactional and idempotent. Automated tests cover models, adapters, methods and exports.</p></article></div>
  <h3>Rebuild commands</h3><div class="formula">python -m src.analyze_market_universe_event_study<br>python -m src.analyze_market_position<br>python -m src.analyze_fuel_price_lags<br>python -m src.build_post_hoc_market_checks<br>python -m src.build_submission_analysis<br>python -m src.build_submission_database<br>python -m src.build_written_assignment_report<br>python -m pytest -q</div><p class="note">The Rheinmetall procurement command takes four explicit file paths; the complete invocation is documented in <code>README.md</code>.</p>
  <h3>Core source links</h3><ul class="sources"><li><a href="https://ucdp.uu.se/downloads/">UCDP — datasets, versions and codebooks</a></li><li><a href="https://www.uu.se/en/department/peace-and-conflict-research/research/ucdp/ucdp-definitions">UCDP — conflict and actor definitions</a></li><li><a href="https://www.eia.gov/dnav/pet/hist/rbrted.htm">U.S. EIA — daily Brent prices</a></li><li><a href="https://energy.ec.europa.eu/data-and-analysis/weekly-oil-bulletin_en">European Commission — Weekly Oil Bulletin</a></li><li><a href="https://www.eia.gov/international/content/analysis/countries_long/iran/">U.S. EIA — Iran country analysis</a></li><li><a href="https://www.reuters.com/business/energy/chinas-heavy-reliance-iranian-oil-imports-2026-03-21/">Reuters/Kpler — China’s Iranian-oil purchases</a></li><li><a href="https://www.sipri.org/sites/default/files/2026-03/fs_2603_at_2025.pdf">SIPRI — Trends in International Arms Transfers 2025</a></li><li><a href="https://www.sec.gov/Archives/edgar/data/2012383/000201238326003238/0002012383-26-003238-index.htm">SEC — BlackRock Q2 2026 Form 13F</a></li><li><a href="https://www.csis.org/analysis/renewed-iran-war-would-test-diminished-interceptor-inventories">CSIS — interceptor inventory estimate</a></li><li><a href="https://apnews.com/article/c98e042bfd0fd22cd97d15b1fffa322c">Associated Press — production-acceleration report</a></li><li><a href="https://www.centcom.mil/MEDIA/PUBLIC-RELEASES/Article/4418396/us-forces-launch-operation-epic-fury/">CENTCOM — Operation Epic Fury launch release</a></li><li><a href="https://www.bundesregierung.de/breg-en/news/chancellor-statement-near-east-2409224">German Federal Government — position of 1 March 2026</a></li><li><a href="https://www.fmprc.gov.cn/eng/xw/fyrbt/202602/t20260228_11866531.html">Chinese Foreign Ministry — statement of 28 February 2026</a></li></ul>
</section>

<section id="questions">
  <div class="section-kicker">What we still cannot answer</div><h2>Open economic questions the data raises but cannot settle</h2>
  <p class="note">These are research questions generated by the evidence and its limitations. They are deliberately separated from the empirical findings and must not be read as claims that the present dataset confirms.</p>
  <div class="grid">
    <article class="card half">
      <h3>Israel → Germany: how exposed is German industry?</h3>
      <p>Israeli escalation rhetoric and German economic reactions run as two separate evidence threads in this project, connected only indirectly through the oil-price channel. Whether German industry has meaningful direct exposure to Israeli technology supply chains—such as semiconductor design, cybersecurity or defence electronics—that a specific Israeli escalation step could disrupt is not something this dataset can show. It would require a company-level Israel-revenue and supplier-exposure panel plus an event study anchored specifically on verified Israeli decision dates rather than U.S. or Iranian dates.</p>
    </article>
    <article class="card half">
      <h3>What is really driving Germany's higher borrowing costs?</h3>
      <p>Selected political commentary attributes movements in German Bund yields to the war, but the same period also contains global inflation pressure, energy-price shocks with multiple causes and anticipation of German defence and infrastructure borrowing. Without continuous official yield series and controls such as U.S. Treasuries and comparable euro-area sovereign bonds, that attribution remains one plausible narrative among several—not a causal estimate.</p>
    </article>
    <article class="card half">
      <h3>How much "war profit" actually stays in Germany?</h3>
      <p>Several Rheinmetall contracts in the curated announcement sample involve third-country customers. Headline contract value does not reveal where production, employment, taxation and value added occur. A foreign or licensed production line can carry the same order value while creating a very different German economic footprint. The current project contains no production-location or domestic-value-added dataset.</p>
    </article>
    <article class="card half">
      <h3>Does BlackRock's dual exposure create a voting conflict?</h3>
      <p>The verified filing shows BlackRock-managed positions across defence and oil issuers, but it does not show how BlackRock votes, whether mandates differ across funds or whether voting changes with issuer-level conflict exposure. Answering that question would require longitudinal proxy-voting records, mandate-level ownership data and a pre-specified comparison design. It is a legitimate governance question raised by the ownership layer—not a conflict that this project can support or refute.</p>
    </article>
  </div>
</section>

<section id="audit">
  <div class="section-kicker">Scope control</div><h2>What is included—and deliberately excluded</h2>
  <div class="table-wrap"><table><thead><tr><th>Module</th><th>Decision</th><th>Reason</th></tr></thead><tbody><tr><td>UCDP definitions and historical catalogues</td><td><span class="status caution">METHOD</span></td><td>Used to define concepts and document available historical resources; no UCDP row is treated as a 2026 statistical observation.</td></tr><tr><td>2026 ACLED aggregate</td><td><span class="status no">EXCLUDED</span></td><td>Access is available only through 2025; the supplied 2026 aggregate cannot be verified and is not conflict-specific.</td></tr><tr><td>Media-positioning pilot</td><td><span class="status no">EXCLUDED</span></td><td>Zero manually reviewed documents. RND supplies 178/247 records (72.1% of all records; 86.4% of the NEWS layer), so country-intensity comparisons would reproduce collection bias.</td></tr><tr><td>Casualty/damage compilation</td><td><span class="status no">EXCLUDED</span></td><td>Self, NGO, UN and adversary numbers have incompatible denominators and dates and were supplied through one secondary compilation. The discrepancy is a source-criticism result, not an intensity variable.</td></tr><tr><td>German DAX/Bund anchors</td><td><span class="status no">EXCLUDED</span></td><td>Sparse selected news points mix closes, intraday levels and approximations; several fall after 18 August. A continuous official series and controls are required.</td></tr><tr><td>Direct Israel–Germany effect</td><td><span class="status no">NOT IDENTIFIED</span></td><td>No pre-specified Israeli decision series is linked to German target assets. This is a documented research gap.</td></tr><tr><td>Company-announcement universe</td><td><span class="status caution">DEMOTED</span></td><td>Only five human-reviewed Rheinmetall records; inadequate coverage for 46-company comparison.</td></tr><tr><td>CENTCOM operation days</td><td><span class="status caution">CONTEXT</span></td><td>Official self-report, retained separately and never treated as total conflict intensity.</td></tr><tr><td>Market and energy results</td><td><span class="status ok">CORE</span></td><td>Reproducible calculations with explicit provenance and limitations.</td></tr></tbody></table></div>
  <h3>Claim-by-claim audit of the supplied additional findings</h3>{findings_audit_table}
  <h3>SQLite data register</h3>{register_table}
  <div class="callout"><strong>Approved own-project data route.</strong> The professor confirmed that students using their own project do not need to implement the separate faculty-supplied train/ideal/test task. This submission therefore documents the purpose, structure and provenance of its self-collected company, market, energy and country-context data and provides the corresponding tested Python implementation.</div>
</section>

<footer>BLACK DOVES written-assignment edition · Descriptive association study · Core period fixed at 2026-01-01 to 2026-08-18 · This report is self-contained and renders its Bokeh charts offline.</footer>
</div>
{bokeh_script}
</body></html>"""


def _market_model_diagnostic_table(data):
    selected_ids = {
        "CMP005",
        "CMP027",
        "CMP030",
        "CMP032",
        "CMP033",
        "CMP036",
    }
    frame = data[data["company_id"].isin(selected_ids)].copy()
    frame["ols_minus_simple"] = (
        frame["ols_post_event_car_0_10"] - frame["post_event_car_0_10"]
    )
    frame = frame[
        [
            "company_name",
            "ols_estimation_window_observations",
            "ols_beta",
            "ols_r_squared",
            "post_event_car_0_10",
            "ols_post_event_car_0_10",
            "ols_minus_simple",
        ]
    ].sort_values("ols_beta")
    frame.columns = [
        "Company",
        "Pre-event n",
        "Beta",
        "R²",
        "Simple CAR",
        "OLS CAR",
        "OLS − simple",
    ]
    return _html_table(
        frame,
        formatters={
            "Pre-event n": lambda value: str(int(value)),
            "Beta": lambda value: f"{float(value):.3f}",
            "R²": lambda value: f"{float(value):.3f}",
            "Simple CAR": _pct,
            "OLS CAR": _pct,
            "OLS − simple": _pp,
        },
    )


def _post_hoc_market_table(data):
    frame = data.copy()
    frame["Window"] = frame.apply(
        lambda row: (
            row["market_start"]
            if row["market_start"] == row["market_end"]
            else f"{row['market_start']} to {row['market_end']}"
        ),
        axis=1,
    )
    frame["Positive"] = frame.apply(
        lambda row: (
            f"{int(row['positive_company_count'])}/"
            f"{int(row['company_count'])}"
        ),
        axis=1,
    )
    frame["Positive every day"] = frame.apply(
        lambda row: (
            f"{int(row['positive_every_market_day_count'])}/"
            f"{int(row['company_count'])}"
        ),
        axis=1,
    )
    frame["Group"] = frame["group_id"].map(
        lambda value: str(value).replace("_", " ").title()
    )
    frame["Source"] = frame.apply(
        lambda row: _link(row["source_url"], row["source_name"]), axis=1
    )
    frame = frame[
        [
            "event_label",
            "Window",
            "Group",
            "Positive",
            "Positive every day",
            "mean_market_adjusted_return",
            "median_market_adjusted_return",
            "mean_ols_market_model_return",
            "Source",
        ]
    ]
    frame.columns = [
        "Post-hoc check",
        "Market window",
        "Group",
        "Positive",
        "Positive every day",
        "Mean simple AR",
        "Median simple AR",
        "Mean OLS AR",
        "Source",
    ]
    return (
        "<details><summary>Show complete post-hoc comparison groups</summary>"
        + _html_table(
            frame,
            formatters={
                "Mean simple AR": _pct,
                "Median simple AR": _pct,
                "Mean OLS AR": _pct,
            },
            safe_columns={"Source"},
        )
        + "</details>"
    )


def _blackrock_table(data):
    frame = data.copy()
    frame["Filing value"] = frame["value_usd"].map(
        lambda value: f"${float(value) / 1_000_000_000:.2f}bn"
    )
    frame["Source"] = frame["source_url"].map(
        lambda value: _link(value, "SEC filing")
    )
    frame = frame[
        [
            "issuer_name",
            "cusip",
            "shares",
            "Filing value",
            "report_period",
            "filing_date",
            "Source",
        ]
    ].sort_values("issuer_name")
    frame.columns = [
        "Issuer",
        "CUSIP",
        "Shares",
        "Filing value",
        "Position date",
        "Filed",
        "Source",
    ]
    return _html_table(
        frame,
        formatters={"Shares": lambda value: f"{int(value):,}"},
        safe_columns={"Source"},
    )


def _patriot_table(data):
    frame = data.copy()

    def estimate(row):
        if pd.isna(row["estimate_min"]):
            return "qualitative"
        minimum = float(row["estimate_min"])
        if pd.isna(row["estimate_max"]):
            value = f"≥{minimum:,.0f}"
        else:
            value = f"{minimum:,.0f}–{float(row['estimate_max']):,.0f}"
        return f"{value} {row['unit']}"

    frame["Estimate"] = frame.apply(estimate, axis=1)
    frame["Source"] = frame.apply(
        lambda row: _link(row["source_url"], row["source_name"]), axis=1
    )
    frame = frame[
        [
            "source_date",
            "context_type",
            "Estimate",
            "company_relevance",
            "evidence_summary",
            "Source",
            "estimation_status",
        ]
    ]
    frame.columns = [
        "Date",
        "Type",
        "Estimate / signal",
        "Company relevance",
        "Evidence",
        "Source",
        "Status",
    ]
    return _html_table(frame, safe_columns={"Source"})


def _findings_audit_table(data):
    frame = data[
        [
            "topic",
            "report_decision",
            "permitted_conclusion",
            "prohibited_inference",
            "status",
        ]
    ].copy()
    frame.columns = [
        "Topic",
        "Decision",
        "Supported conclusion",
        "Not supported",
        "Status",
    ]
    return (
        "<details><summary>Show the complete additional-findings audit</summary>"
        + _html_table(frame)
        + "</details>"
    )


def _short_company_table(data):
    frame = data[
        [
            "company_name",
            "role_category",
            "event_day_abnormal_return",
            "post_event_car_0_10",
            "ols_post_event_car_0_10",
        ]
    ].copy()
    frame.columns = [
        "Company",
        "Role",
        "Event day",
        "CAR [0,+10]",
        "OLS CAR [0,+10]",
    ]
    return _html_table(
        frame,
        formatters={
            "Event day": _pct,
            "CAR [0,+10]": _pct,
            "OLS CAR [0,+10]": _pct,
        },
    )


def _bootstrap_table(data):
    frame = data.copy()
    frame["Comparison"] = frame.apply(
        lambda row: (
            row["group_a"]
            if row["estimator"] == "MEAN"
            else f"{row['group_a']} − {row['group_b']}"
        ),
        axis=1,
    )
    frame = frame[
        [
            "metric_label",
            "Comparison",
            "estimate",
            "ci_lower",
            "ci_upper",
            "n_group_a",
            "n_group_b",
            "interpretation",
        ]
    ]
    frame.columns = [
        "Metric",
        "Estimate for",
        "Estimate",
        "CI lower",
        "CI upper",
        "n A",
        "n B",
        "Interval status",
    ]
    return _html_table(
        frame,
        formatters={
            "Estimate": _pct,
            "CI lower": _pct,
            "CI upper": _pct,
            "n B": lambda value: "—" if int(value) == 0 else str(int(value)),
            "Interval status": lambda value: (
                "excludes zero"
                if value == "INTERVAL_EXCLUDES_ZERO"
                else "includes zero"
            ),
        },
    )


def _long_company_table(data):
    frame = data[
        [
            "company_name",
            "post_company_total_return",
            "post_benchmark_total_return",
            "post_bhar",
            "post_car",
            "post_ols_car",
            "post_observations",
            "post_end_market_date",
        ]
    ].sort_values("post_bhar", ascending=False)
    frame.columns = [
        "Company",
        "Company return",
        "Benchmark return",
        "BHAR",
        "CAR",
        "OLS CAR",
        "Obs.",
        "Last date",
    ]
    return _html_table(
        frame,
        formatters={
            "Company return": _pct,
            "Benchmark return": _pct,
            "BHAR": _pct,
            "CAR": _pct,
            "OLS CAR": _pct,
            "Obs.": lambda value: str(int(value)),
        },
    )


def _lag_summary_table(data):
    frame = data[
        [
            "product",
            "tax_basis",
            "observations",
            "spearman_correlation",
            "spearman_p_value",
            "spearman_p_value_holm",
            "pearson_correlation",
            "pearson_p_value_holm",
            "spearman_significant_holm_0_05",
        ]
    ].copy()
    frame.columns = [
        "Product",
        "Tax basis",
        "n",
        "Spearman ρ",
        "Raw p",
        "Holm p",
        "Pearson r",
        "Pearson Holm p",
        "Spearman significant",
    ]
    return _html_table(
        frame,
        formatters={
            "n": lambda value: str(int(value)),
            "Spearman ρ": _decimal3,
            "Raw p": _pvalue,
            "Holm p": _pvalue,
            "Pearson r": _decimal3,
            "Pearson Holm p": _pvalue,
            "Spearman significant": lambda value: (
                "yes" if _as_bool(value) else "no"
            ),
        },
    )


def _role_table(data):
    frame = data[
        [
            "country_name",
            "direct_military_participation",
            "arms_supply_context",
            "political_position",
            "economic_dependency",
            "verification_status",
        ]
    ].copy()
    frame.columns = [
        "Country",
        "Direct",
        "Arms context",
        "Political position",
        "Economic dependency",
        "Evidence status",
    ]
    return _html_table(frame)


def _dependency_table(data):
    frame = data[
        [
            "reference_period",
            "estimated_share_pct_min",
            "estimated_share_pct_max",
            "estimated_volume_mbd",
            "comparison_share_pct",
            "denominator",
            "source_org",
            "source_url",
            "estimation_status",
        ]
    ].copy()
    frame["Share estimate"] = frame.apply(
        lambda row: _range_pct(
            row["estimated_share_pct_min"],
            row["estimated_share_pct_max"],
        ),
        axis=1,
    )
    frame["Volume"] = frame["estimated_volume_mbd"].map(
        lambda value: (
            "—" if pd.isna(value) else f"{float(value):.2f}m b/d"
        )
    )
    frame["China import share"] = frame["comparison_share_pct"].map(
        lambda value: "—" if pd.isna(value) else f"{float(value):.1f}%"
    )
    frame["Source"] = frame.apply(
        lambda row: _link(row["source_url"], row["source_org"]), axis=1
    )
    frame = frame[
        [
            "reference_period",
            "Share estimate",
            "Volume",
            "China import share",
            "denominator",
            "Source",
            "estimation_status",
        ]
    ]
    frame.columns = [
        "Period",
        "China share",
        "China volume",
        "Share of China seaborne",
        "Denominator",
        "Source",
        "Status",
    ]
    return _html_table(frame, safe_columns={"Source"})


def _arms_table(data):
    frame = data[
        [
            "reference_period",
            "supplier_country",
            "recipient_country",
            "share_pct",
            "metric_scope",
            "source_url",
            "estimation_status",
        ]
    ].copy()
    frame["Source"] = frame["source_url"].map(
        lambda value: _link(value, "SIPRI fact sheet")
    )
    frame = frame[
        [
            "reference_period",
            "supplier_country",
            "recipient_country",
            "share_pct",
            "metric_scope",
            "Source",
            "estimation_status",
        ]
    ]
    frame.columns = [
        "Period",
        "Supplier",
        "Recipient",
        "Share",
        "Scope",
        "Source",
        "Status",
    ]
    return _html_table(
        frame,
        formatters={"Share": lambda value: f"{float(value):.0f}%"},
        safe_columns={"Source"},
    )


def _ucdp_table(data):
    frame = data[
        [
            "resource",
            "version_or_access_date",
            "coverage",
            "purpose",
            "source_url",
            "application_status",
            "interpretation_boundary",
        ]
    ].copy()
    frame["Source"] = frame["source_url"].map(
        lambda value: _link(value, "official page")
    )
    frame = frame[
        [
            "resource",
            "version_or_access_date",
            "coverage",
            "purpose",
            "Source",
            "application_status",
            "interpretation_boundary",
        ]
    ]
    frame.columns = [
        "Resource",
        "Version / access",
        "Coverage",
        "Use",
        "Source",
        "Status",
        "Boundary",
    ]
    return _html_table(frame, safe_columns={"Source"})


def _procurement_table(data):
    frame = data[
        [
            "announcement_date",
            "title",
            "post_event_car_0_10",
            "ols_post_event_car_0_10",
            "ols_status",
            "source_url",
        ]
    ].copy()
    frame["Source"] = frame["source_url"].map(
        lambda value: _link(value, "announcement")
    )
    frame = frame[
        [
            "announcement_date",
            "title",
            "post_event_car_0_10",
            "ols_post_event_car_0_10",
            "ols_status",
            "Source",
        ]
    ]
    frame.columns = ["Date", "Announcement", "CAR", "OLS CAR", "OLS status", "Source"]
    return _html_table(
        frame,
        formatters={
            "CAR": _pct,
            "OLS CAR": lambda value: "—" if pd.isna(value) else _pct(value),
        },
        safe_columns={"Source"},
    )


def _centcom_table(data):
    frame = data[
        [
            "event_date",
            "title",
            "strike_type",
            "counting_unit",
            "source_url",
        ]
    ].sort_values("event_date")
    frame = frame.copy()
    frame["Source"] = frame["source_url"].map(
        lambda value: _link(value, "release")
    )
    frame = frame[
        ["event_date", "title", "strike_type", "counting_unit", "Source"]
    ]
    frame.columns = ["Date", "Title", "Type", "Counting unit", "Source"]
    return (
        "<details><summary>Show all 23 core operation days</summary>"
        + _html_table(frame, safe_columns={"Source"})
        + "</details>"
    )


def _database_register_table():
    database = (
        PROCESSED / "submission" / "black_doves_submission.sqlite"
    )
    if not database.is_file():
        return '<p class="note">Database not built.</p>'
    with sqlite3.connect(database) as connection:
        frame = pd.read_sql_query(
            """
            SELECT dataset_key, relative_path, row_count, sha256,
                   default_reporting_period, default_unit,
                   default_estimation_status
            FROM dataset_manifest
            ORDER BY dataset_key
            """,
            connection,
        )
    frame["sha256"] = frame["sha256"].map(lambda value: value[:12] + "…")
    frame.columns = [
        "Dataset",
        "CSV path",
        "Rows",
        "SHA-256",
        "Period",
        "Unit",
        "Default status",
    ]
    return _html_table(
        frame, formatters={"Rows": lambda value: f"{int(value):,}"}
    )


def _html_table(frame, formatters=None, safe_columns=None):
    formatters = formatters or {}
    safe_columns = safe_columns or set()
    headers = "".join(f"<th>{html.escape(str(column))}</th>" for column in frame.columns)
    rows = []
    for _, row in frame.iterrows():
        cells = []
        for column in frame.columns:
            value = row[column]
            if column in formatters:
                value = formatters[column](value)
            elif pd.isna(value):
                value = "—"
            else:
                value = str(value)
            text = str(value) if column in safe_columns else html.escape(str(value))
            cells.append(f"<td>{text}</td>")
        rows.append("<tr>" + "".join(cells) + "</tr>")
    return (
        '<div class="table-wrap"><table><thead><tr>'
        + headers
        + "</tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table></div>"
    )


def _embedded_logo():
    path = ROOT / "assets" / "black_doves_logo.png"
    if not path.is_file():
        return ""
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return (
        '<img alt="BLACK DOVES logo" '
        f'src="data:image/png;base64,{encoded}">'
    )


def _bootstrap_row(data, metric, estimator, group_a):
    selected = data[
        (data["metric"] == metric)
        & (data["estimator"] == estimator)
        & (data["group_a"] == group_a)
    ]
    if len(selected) != 1:
        raise ValueError(
            f"Expected one bootstrap row for {metric}/{estimator}/{group_a}"
        )
    return next(selected.itertuples(index=False))


def _company_row(data, company_id):
    selected = data[data["company_id"] == company_id]
    if len(selected) != 1:
        raise ValueError(f"Expected one company row for {company_id}")
    return next(selected.itertuples(index=False))


def _post_hoc_row(data, event_id, group_id):
    selected = data[
        (data["event_id"] == event_id) & (data["group_id"] == group_id)
    ]
    if len(selected) != 1:
        raise ValueError(
            f"Expected one post-hoc row for {event_id}/{group_id}"
        )
    return next(selected.itertuples(index=False))


def _first_last_change(data, column):
    values = pd.to_numeric(data[column], errors="coerce").dropna()
    return float(values.iloc[-1] / values.iloc[0] - 1.0)


def _boolean_mask(series):
    return series.map(_as_bool).astype(bool)


def _as_bool(value):
    if isinstance(value, bool):
        return value
    return str(value).strip().casefold() in {"1", "true", "yes", "y"}


def _short_company(value):
    replacements = {
        "China Petroleum & Chemical Corporation (Sinopec Corp.)": "Sinopec",
        "Lockheed Martin Corporation": "Lockheed Martin",
        "Exxon Mobil Corporation": "Exxon Mobil",
        "RTX Corporation": "RTX",
    }
    return replacements.get(str(value), str(value))


def _pct(value):
    if pd.isna(value):
        return "—"
    return f"{float(value) * 100:+.2f}%"


def _pp(value):
    if pd.isna(value):
        return "—"
    return f"{float(value) * 100:+.2f} pp"


def _ci(row):
    return f"[{_pct(row.ci_lower)}, {_pct(row.ci_upper)}]"


def _ci_pp(row):
    return f"[{_pp(row.ci_lower)}, {_pp(row.ci_upper)}]"


def _decimal3(value):
    return "—" if pd.isna(value) else f"{float(value):.3f}"


def _pvalue(value):
    if pd.isna(value):
        return "—"
    number = float(value)
    return "<0.001" if number < 0.001 else f"{number:.3f}"


def _range_pct(minimum, maximum):
    if pd.isna(maximum):
        return f">{float(minimum):.0f}%"
    if float(maximum) - float(minimum) <= 1.0:
        return f"≈{float(maximum):.0f}%"
    return f"{float(minimum):.0f}–{float(maximum):.0f}%"


def _link(url, label):
    safe_url = html.escape(str(url), quote=True)
    safe_label = html.escape(str(label))
    return f'<a href="{safe_url}">{safe_label}</a>'


if __name__ == "__main__":
    raise SystemExit(main())
