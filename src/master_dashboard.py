import base64
import csv
import html
import json
import re
from pathlib import Path

from src.services.narrative_classifier import NARRATIVE_TAXONOMY


STUDY_START = "2026-01-01"
STUDY_END = "2026-08-18"

REPORT_DEFINITIONS = (
    (
        "conflict_energy",
        "Strikes & energy",
        "output/black_doves_energy_price_lag.html",
    ),
    (
        "event_study",
        "Event study",
        "output/black_doves_market_universe_event_study.html",
    ),
    (
        "market_position",
        "Market position",
        "output/black_doves_long_horizon_market_position.html",
    ),
    (
        "company_announcements",
        "Company & announcements",
        "output/black_doves_company_announcements.html",
    ),
    (
        "media_positioning",
        "Media positioning",
        "output/black_doves_media_positioning.html",
    ),
    (
        "casualty_damage",
        "Damage & losses",
        "output/black_doves_casualty_damage.html",
    ),
    (
        "procurement",
        "Procurement",
        "output/black_doves_procurement_event_study.html",
    ),
)


def create_master_dashboard(project_root, output_path):
    root = Path(project_root)
    output = Path(output_path)
    if output.suffix.casefold() != ".html":
        raise ValueError("Master dashboard output must use .html")
    output.parent.mkdir(parents=True, exist_ok=True)

    report_payloads = _load_reports(root)
    datasets = _load_datasets(root)
    coverage = _records_by_key(
        datasets.get("narrative_coverage", {}).get("records", []),
        "source_layer",
    )
    categories = datasets.get("narrative_category_summary", {}).get(
        "records", []
    )
    narrative_documents = datasets.get("narrative_documents", {}).get(
        "records", []
    )

    page = _PAGE_TEMPLATE
    page = page.replace("__MASTER_LOGO__", _master_brand_html(root))
    page = page.replace("__REPORT_NAV__", _report_navigation(report_payloads))
    page = page.replace("__REPORT_SECTIONS__", _report_sections(report_payloads))
    page = page.replace("__OVERVIEW__", _overview_html(datasets, coverage))
    page = page.replace(
        "__NARRATIVE_COVERAGE__", _narrative_coverage_html(coverage)
    )
    page = page.replace(
        "__NARRATIVE_MATRIX__", _narrative_matrix_html(categories, coverage)
    )
    page = page.replace("__DEFENSE_MAP__", _defense_map_html(coverage))
    page = page.replace(
        "__DEFENSE_MAP_NOTE__", _defense_map_note_html()
    )
    page = page.replace("__METHOD_TABLE__", _method_table_html(coverage))
    page = page.replace(
        "__REPORTS_JSON__", _safe_json({key: item["data"] for key, item in report_payloads.items()})
    )
    page = page.replace("__DATASETS_JSON__", _safe_json(_client_datasets(datasets)))
    page = page.replace(
        "__NARRATIVE_JSON__", _safe_json(narrative_documents)
    )
    page = page.replace(
        "__TAXONOMY_JSON__",
        _safe_json(
            {
                code: definition["label"]
                for code, definition in NARRATIVE_TAXONOMY.items()
            }
        ),
    )
    output.write_text(page, encoding="utf-8")
    return output


def _master_brand_html(root):
    logo_path = Path(root) / "assets" / "black_doves_logo.png"
    if not logo_path.is_file():
        return '<div class="mark" aria-hidden="true">BD</div>'
    encoded = base64.b64encode(logo_path.read_bytes()).decode("ascii")
    return (
        '<img class="brand-logo" '
        f'src="data:image/png;base64,{encoded}" '
        'alt="BLACK DOVES – dove carrying barbed wire">'
    )


def _load_reports(root):
    resource_path = root / "output" / "black_doves_energy_price_lag.html"
    resource_document = (
        resource_path.read_text(encoding="utf-8")
        if resource_path.is_file()
        else ""
    )
    payloads = {}
    for report_id, title, relative_path in REPORT_DEFINITIONS:
        path = root / relative_path
        if path.is_file():
            document = path.read_text(encoding="utf-8")
            document = _inline_bokeh_resources(document, resource_document)
            encoded = base64.b64encode(document.encode("utf-8")).decode("ascii")
            payloads[report_id] = {
                "title": title,
                "path": relative_path,
                "available": True,
                "data": encoded,
            }
        else:
            payloads[report_id] = {
                "title": title,
                "path": relative_path,
                "available": False,
                "data": "",
            }
    return payloads


def _inline_bokeh_resources(document, resource_document):
    if "https://cdn.bokeh.org" not in document or not resource_document:
        return document
    scripts = {}
    pattern = re.compile(
        r"<script>\s*/\* BEGIN (bokeh(?:-widgets)?\.min\.js) \*/"
        r".*?/\* END \1 \*/\s*</script>",
        flags=re.DOTALL,
    )
    for match in pattern.finditer(resource_document):
        scripts[match.group(1)] = match.group(0)

    def replace_script(match):
        filename = match.group(1)
        resource_name = filename.replace("-3.10.0", "")
        return scripts.get(resource_name, match.group(0))

    return re.sub(
        r'<script src="https://cdn\.bokeh\.org/bokeh/release/'
        r'(bokeh(?:-widgets)?-3\.10\.0\.min\.js)"></script>',
        replace_script,
        document,
    )


def _load_datasets(root):
    paths = list((root / "data" / "analysis").glob("*.csv"))
    paths.extend(
        [
            root / "data" / "processed" / "energy" / "energy_price_timeline.csv",
            root / "data" / "processed" / "energy" / "energy_price_weekly_panel.csv",
            root / "data" / "processed" / "market" / "company_benchmark_returns.csv",
            root / "data" / "processed" / "market" / "market_download_report.csv",
            root / "data" / "processed" / "market" / "market_processing_report.csv",
            root / "data" / "validated" / "centcom_us_strike_operation_days.csv",
            root / "data" / "reference" / "black_doves_market_events.csv",
            root / "data" / "reference" / "company_announcements.csv",
            root / "data" / "reference" / "rheinmetall_air_defence_procurement_events.csv",
            root / "config" / "company_market_universe.csv",
        ]
    )
    datasets = {}
    seen = set()
    for path in paths:
        if not path.is_file() or path.resolve() in seen:
            continue
        seen.add(path.resolve())
        dataset_id = path.stem
        if dataset_id in datasets:
            dataset_id = re.sub(r"[^a-z0-9]+", "_", str(path.relative_to(root)).casefold()).strip("_")
        with path.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.reader(file)
            rows = list(reader)
        if not rows:
            continue
        columns = rows[0]
        records = [
            dict(zip(columns, row + [""] * (len(columns) - len(row))))
            for row in rows[1:]
        ]
        datasets[dataset_id] = {
            "label": path.stem.replace("_", " ").title(),
            "path": str(path.relative_to(root)).replace("\\", "/"),
            "columns": columns,
            "records": records,
            "row_count": len(records),
            "csv_b64": base64.b64encode(path.read_bytes()).decode("ascii"),
        }
    return dict(sorted(datasets.items()))


def _client_datasets(datasets):
    return {
        dataset_id: {
            key: value
            for key, value in item.items()
            if key != "records"
        }
        for dataset_id, item in datasets.items()
    }


def _records_by_key(records, key):
    return {record.get(key, ""): record for record in records}


def _report_navigation(report_payloads):
    return "".join(
        (
            f'<button type="button" role="tab" data-view="report-{report_id}" '
            f'aria-selected="false">{html.escape(item["title"])}</button>'
        )
        for report_id, item in report_payloads.items()
    )


def _report_sections(report_payloads):
    sections = []
    for report_id, item in report_payloads.items():
        if item["available"]:
            content = (
                f'<iframe class="report-frame" data-report="{report_id}" '
                f'title="{html.escape(item["title"])}"></iframe>'
            )
        else:
            content = (
                '<div class="empty"><b>Report unavailable</b><span>'
                + html.escape(item["path"])
                + " was not found. Rebuild the corresponding analysis first.</span></div>"
            )
        sections.append(
            f'<section class="view" data-panel="report-{report_id}" hidden>'
            f'<div class="title-row"><div><h2>{html.escape(item["title"])}</h2>'
            '<p>Complete embedded analysis; filters and hover details remain active.</p>'
            '</div><span class="status">Embedded report</span></div>'
            f'{content}</section>'
        )
    return "".join(sections)


def _overview_html(datasets, coverage):
    companies = datasets.get("market_universe_company_summary", {}).get(
        "row_count", 0
    )
    energy_weeks = datasets.get("energy_price_weekly_panel", {}).get(
        "row_count", 0
    )
    centcom_rows = datasets.get(
        "centcom_us_strike_operation_days", {}
    ).get("records", [])
    centcom_days = len(
        {
            row.get("event_date")
            for row in centcom_rows
            if row.get("include_in_core_series", "").casefold() == "true"
        }
    )
    state_documents = int(
        coverage.get("STATE_ORGAN", {}).get("document_count") or 0
    )
    total_company_count = datasets.get("company_market_universe", {}).get(
        "row_count", 0
    )
    announcement_records = datasets.get("company_announcements", {}).get(
        "records", []
    )
    companies_with_announcements = len(
        {
            row.get("company_id")
            for row in announcement_records
            if row.get("company_id")
        }
    )
    media_positioning_records = datasets.get(
        "narrative_documents_media_positioning", {}
    ).get("records", [])
    media_layer_documents = sum(
        1
        for row in media_positioning_records
        if row.get("source_layer") in {"NEWS", "TELEVISION"}
    )
    cards = (
        ("Core study window", "01 Jan–18 Aug 2026", "Event, market-position and energy analyses"),
        ("Companies", str(companies), "Confirmatory, exploratory and post-hoc groups"),
        (
            "Curated announcements",
            (
                f"{companies_with_announcements} of {total_company_count}"
                if total_company_count
                else str(companies_with_announcements)
            ),
            (
                "Companies with an imported announcement dataset; the rest "
                "show 'coverage: MISSING' in Company & announcements, not "
                "zero events"
            ),
        ),
        ("Energy weeks", str(energy_weeks), "Weekly Brent and German fuel panel"),
        (
            "Media positioning",
            f"{media_layer_documents} pilot docs",
            (
                "Manually-verified NEWS/TELEVISION sample across state-"
                "controlled and independent outlets; proof of concept, "
                "not a comprehensive corpus"
            ),
        ),
        ("U.S. operation days", str(centcom_days), "CENTCOM-confirmed in-scope days"),
        ("State documents", str(state_documents), "Narrative corpus; coverage remains partial"),
        ("Embedded datasets", str(len(datasets)), "Complete analysis-ready tables"),
    )
    return "".join(
        '<div class="metric"><span>'
        + html.escape(label)
        + "</span><b>"
        + html.escape(value)
        + "</b><small>"
        + html.escape(note)
        + "</small></div>"
        for label, value, note in cards
    )


def _narrative_coverage_html(coverage):
    labels = {
        "STATE_ORGAN": "State organs",
        "NEWS": "News",
        "TELEVISION": "Television",
    }
    cards = []
    for layer in ("STATE_ORGAN", "NEWS", "TELEVISION"):
        record = coverage.get(layer, {})
        count = int(record.get("document_count") or 0)
        status = record.get("coverage_status") or "MISSING"
        detail = (
            f"{count} document(s) · {record.get('source_count') or 0} source(s)"
            if count
            else "No in-scope corpus loaded · missing, not zero"
        )
        cards.append(
            f'<div class="coverage {status.casefold()}"><b>{labels[layer]}</b>'
            f'<span>{html.escape(detail)}</span><em>{html.escape(status)}</em></div>'
        )
    return "".join(cards)


def _narrative_matrix_html(categories, coverage):
    indexed = {
        (row["source_layer"], row["category_code"]): row
        for row in categories
    }
    rows = []
    for code, definition in NARRATIVE_TAXONOMY.items():
        cells = []
        for layer in ("STATE_ORGAN", "NEWS", "TELEVISION"):
            layer_coverage = coverage.get(layer, {})
            record = indexed.get((layer, code), {})
            reviewed_total = int(record.get("reviewed_layer_total") or 0)
            if reviewed_total:
                count = int(record.get("reviewed_document_count") or 0)
                share = float(record.get("reviewed_share") or 0)
                value = f"{count} · {share:.1%} reviewed"
                css = "reviewed"
            elif int(layer_coverage.get("document_count") or 0):
                count = int(record.get("suggested_document_count") or 0)
                total = int(record.get("suggested_layer_total") or 0)
                share = float(record.get("suggested_share") or 0) if total else 0
                value = f"{count} · {share:.1%} suggested" if total else "Unclassified"
                css = "suggested"
            else:
                value = "Corpus missing"
                css = "missing"
            cells.append(f'<td class="{css}">{html.escape(value)}</td>')
        rows.append(
            f'<tr><th>{html.escape(definition["label"])}</th>{"".join(cells)}</tr>'
        )
    return "".join(rows)


def _defense_map_html(coverage):
    media_ready = all(
        int(coverage.get(layer, {}).get("document_count") or 0) > 0
        for layer in ("NEWS", "TELEVISION")
    )
    media_status = (
        "Available for reviewed comparison"
        if media_ready
        else "Connector ready; comparable news/TV corpora missing"
    )
    rows = (
        (
            "Direct military participation",
            "Strikes & energy → Strikes; Company & announcements",
            "Affected-country series and separate U.S.-initiator series",
            "Partial · Iran/Israel import plus CENTCOM U.S. days",
        ),
        (
            "Arms supply",
            "Procurement; Event study → roles; Narratives",
            "Verified procurement events, official statements and company response",
            "Partial · not a complete five-country profile",
        ),
        (
            "Political positioning / mediation",
            "Narratives → diplomacy and mediation",
            "Reviewed source-layer comparison and document drill-down",
            media_status,
        ),
        (
            "Economic dependency",
            "Defense map",
            "Country dependency indicators",
            "Open gap",
        ),
        (
            "Abnormal company returns",
            "Event study; Market position; Company & announcements",
            "AAR, CAAR, CAR, percentile and rank change",
            "Covered · descriptive, not causal",
        ),
        (
            "Brent and German fuel prices",
            "Strikes & energy → EUR/L, Index, Changes, Lag",
            "Weekly frequency, gross/net levels and lag associations",
            "Covered · carry-in and exploratory-lag caveats retained",
        ),
        (
            "Iran–China oil dependency",
            "Defense map",
            "Trade volume, shares and asymmetry",
            "Open gap · no validated trade connector yet",
        ),
    )
    return "".join(
        "<tr>" + "".join(f"<td>{html.escape(value)}</td>" for value in row) + "</tr>"
        for row in rows
    )


def _defense_map_note_html():
    return (
        "<div class='note'>"
        "<b>Iran\u2013China oil dependency \u2013 disclosed estimate, not a data "
        "connector:</b> the written assignment's own research proposal states "
        "that China purchases approximately 80\u201390% of Iranian oil exports. "
        "This range is reproduced here for context only, sourced to the "
        "research proposal itself rather than to an independently reconciled "
        "trade-flow computation. No SIPRI, U.S. Treasury, Reuters/Kpler, or "
        "customs dataset is wired into this application, so the figure cannot "
        "be re-derived, cross-checked, or broken down by period, denominator "
        "(share of Iranian exports vs. share of Chinese imports), or "
        "verification status here. Sanctions, indirect shipping routes and "
        "incomplete customs reporting materially limit the reliability of any "
        "such estimate. This row therefore remains an open gap for a "
        "validated trade connector; treat the 80\u201390% figure as a "
        "proposal-stated estimate, never as an exact or fully verified value."
        "</div>"
    )


def _method_table_html(coverage):
    news_status = coverage.get("NEWS", {}).get("coverage_status", "MISSING")
    tv_status = coverage.get("TELEVISION", {}).get("coverage_status", "MISSING")
    rows = (
        (
            "Iran / Israel strike activity",
            "Imported weekly conflict aggregate",
            "Reported events by affected country",
            "2026 ACLED API availability is unresolved; provenance must remain explicit",
        ),
        (
            "United States strike activity",
            "CENTCOM public releases",
            "Distinct official-release-confirmed operation day",
            "Never added to affected-country event counts",
        ),
        (
            "Brent",
            "U.S. EIA",
            "USD/barrel, weekly mean",
            "Aligned to weekly German fuel observations",
        ),
        (
            "Petrol / diesel",
            "EU Weekly Oil Bulletin",
            "EUR/litre including and excluding taxes",
            "Gross and net lines stay separately selectable",
        ),
        (
            "Company returns",
            "Configured market observations",
            "Abnormal return / CAR",
            "Company_Master and documented local benchmarks; no causal claim",
        ),
        (
            "Company-linked announcements",
            "Curated company-announcement registry",
            "Company event marker with verified source and coverage state",
            "Currently partial; missing coverage is never interpreted as zero",
        ),
        (
            "State announcements",
            "Government, ministry and CENTCOM sources",
            "Document with reviewed multi-label categories",
            "Partial study-window coverage; deduplicate before counting",
        ),
        (
            "News reporting",
            "Configured publisher RSS connector",
            "Article document",
            f"{news_status}; current feed cannot substitute for historical backfill",
        ),
        (
            "Television reporting",
            "Auditable transcript CSV importer",
            "Broadcast transcript document",
            f"{tv_status}; programme sample and lawful transcript files required",
        ),
    )
    return "".join(
        "<tr>" + "".join(f"<td>{html.escape(value)}</td>" for value in row) + "</tr>"
        for row in rows
    )


def _safe_json(value):
    return (
        json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )


_PAGE_TEMPLATE = r'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <meta name="color-scheme" content="dark">
  <meta name="theme-color" content="#080c12">
  <title>BLACK DOVES · Complete Analysis</title>
  <style>
    :root{color-scheme:dark;--bg:#080c12;--surface:#111823;--surface2:#1b2735;--surface3:#202f40;--text:#f3f6fa;--muted:#a9b5c3;--border:#344457;--accent:#ff6b5f;--blue:#55b6e8;--green:#54c98a;--amber:#f2b84b;--missing:#8a96a3}
    *{box-sizing:border-box}html,body{margin:0;min-height:100%;background:radial-gradient(circle at 8% 0%,rgba(255,107,95,.08),transparent 34rem),var(--bg);color:var(--text);font-family:Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif}button,select,input{font:inherit}.app{max-width:1600px;margin:auto}.head{display:flex;justify-content:space-between;gap:20px;padding:16px 24px 13px;background:color-mix(in srgb,var(--surface) 94%,transparent);border-bottom:1px solid var(--border)}.brand{display:flex;gap:16px;align-items:center}.brand-logo{display:block;width:clamp(150px,15vw,205px);height:auto;object-fit:contain}.brand-copy{padding-left:16px;border-left:1px solid var(--border)}.mark{display:grid;place-items:center;width:42px;height:42px;border:1px solid color-mix(in srgb,var(--accent) 65%,var(--border));border-radius:10px;background:linear-gradient(145deg,var(--accent),#8e2f39);color:#fff;box-shadow:0 8px 24px rgba(255,107,95,.18);font-weight:700}.head h1,.title-row h2,.panel h3{margin:0;font-weight:600}.head h1{font-size:18px}.head p,.title-row p,.panel p{margin:3px 0 0;color:var(--muted);font-size:12px}.window{font-size:12px;color:var(--muted);white-space:nowrap}.nav{position:sticky;top:0;z-index:10;display:flex;gap:4px;overflow-x:auto;padding:8px 12px;background:color-mix(in srgb,var(--surface) 96%,transparent);border-bottom:1px solid var(--border);backdrop-filter:blur(14px)}.nav button{border:1px solid transparent;border-radius:8px;background:transparent;color:var(--muted);padding:9px 12px;white-space:nowrap;cursor:pointer}.nav button:hover{color:var(--text);background:var(--surface2)}.nav button[aria-selected=true]{border-color:color-mix(in srgb,var(--accent) 55%,var(--border));background:color-mix(in srgb,var(--accent) 20%,var(--surface));color:#fff}main{padding:20px 24px 28px}.view[hidden]{display:none}.title-row{display:flex;justify-content:space-between;gap:18px;align-items:flex-start;margin-bottom:16px}.status{font-size:11px;color:var(--muted);white-space:nowrap}.status:before{content:"";display:inline-block;width:7px;height:7px;margin-right:7px;border-radius:50%;background:var(--green);box-shadow:0 0 10px color-mix(in srgb,var(--green) 65%,transparent)}.metric-grid,.coverage-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}.metric,.coverage,.panel{background:linear-gradient(145deg,color-mix(in srgb,var(--surface) 96%,#fff 4%),var(--surface));border:1px solid var(--border);border-radius:12px;box-shadow:0 10px 28px rgba(0,0,0,.16)}.metric{padding:15px}.metric span,.metric small,.coverage span,.coverage em{display:block}.metric span{font-size:11px;color:var(--muted)}.metric b{display:block;margin:5px 0;font-size:25px}.metric small{color:var(--muted);font-size:11px;line-height:1.4}.overview-note{margin-top:14px;padding:14px 16px;border-left:3px solid var(--accent);background:var(--surface);font-size:12px;line-height:1.55}.report-frame{width:100%;height:calc(100vh - 178px);min-height:720px;border:1px solid var(--border);border-radius:12px;background:var(--bg)}.coverage-grid{margin-bottom:14px}.coverage{padding:12px;border-top-width:3px}.coverage.partial{border-top-color:var(--amber)}.coverage.missing{border-top-color:var(--missing)}.coverage b{font-size:12px}.coverage span{margin-top:4px;color:var(--muted);font-size:11px}.coverage em{margin-top:8px;font-style:normal;font-size:10px;color:var(--muted)}.panel{padding:15px 16px;margin-top:14px}.panel-head{display:flex;justify-content:space-between;gap:12px;align-items:flex-start;margin-bottom:12px}.controls{display:flex;align-items:flex-end;gap:10px;flex-wrap:wrap;margin-bottom:12px;padding:12px;background:var(--surface);border:1px solid var(--border);border-radius:10px}.field{display:grid;gap:4px;flex:1 1 205px;min-width:185px}.field label{font-size:10px;color:var(--muted)}select,input{min-height:40px;border:1px solid #52667b;border-radius:8px;background:var(--surface2);color:var(--text);padding:8px 34px 8px 10px}select option{background:var(--surface2);color:var(--text)}select:hover,input:hover{border-color:#6b829a;background:var(--surface3)}select:focus,input:focus,button:focus-visible{outline:2px solid color-mix(in srgb,var(--accent) 75%,transparent);outline-offset:2px;border-color:var(--accent)}.table-wrap{overflow:auto;max-height:68vh;border:1px solid var(--border);border-radius:9px;background:color-mix(in srgb,var(--surface) 82%,var(--bg))}table{width:100%;border-collapse:collapse;font-size:11px}th,td{padding:9px 8px;text-align:left;vertical-align:top;border-bottom:1px solid var(--border)}tbody tr:hover{background:color-mix(in srgb,var(--blue) 8%,transparent)}thead th{position:sticky;top:0;background:var(--surface2);color:var(--muted);z-index:1}tbody th{font-weight:600;min-width:210px}.suggested{border-left:3px solid var(--amber)}.reviewed{border-left:3px solid var(--green)}.missing{color:var(--muted);font-style:italic;background:repeating-linear-gradient(135deg,transparent 0 7px,color-mix(in srgb,var(--border) 50%,transparent) 7px 8px)}.note{padding:11px 12px;margin-top:12px;background:var(--surface2);border-left:3px solid var(--amber);font-size:11px;line-height:1.5;color:var(--muted)}.pager{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-top:10px}.pager button{min-height:40px;border:1px solid #52667b;border-radius:7px;background:var(--surface2);color:var(--text);padding:7px 10px;cursor:pointer}.pager button:hover:not(:disabled){border-color:var(--accent);background:var(--surface3)}.pager button:disabled{opacity:.35}.pager span{font-size:11px;color:var(--muted)}.empty{padding:28px;border:1px dashed var(--border);border-radius:12px;background:var(--surface)}.empty b,.empty span{display:block}.empty span{margin-top:5px;color:var(--muted);font-size:12px}a{color:var(--blue)}*{scrollbar-color:var(--border) var(--surface);scrollbar-width:thin}::selection{color:#fff;background:color-mix(in srgb,var(--accent) 58%,transparent)}
    @media(max-width:760px){.head,.title-row,.panel-head{flex-direction:column}.brand{width:100%;gap:10px}.brand-logo{width:138px}.brand-copy{padding-left:10px}.window{white-space:normal}.metric-grid,.coverage-grid{grid-template-columns:1fr}.head{padding:13px}.nav{position:static}.nav button{min-height:44px}main{padding:15px 10px 22px}.field{width:100%}select,input{width:100%;font-size:16px;min-height:44px}.report-frame{height:78vh;min-height:620px}.table-wrap{max-height:65vh}}
  </style>
</head>
<body>
<div class="app">
  <header class="head"><div class="brand">__MASTER_LOGO__<div class="brand-copy"><h1>Complete Analysis</h1><p>Conflict, markets, energy, communication and audit trail</p></div></div><div class="window">Core study window · 01 Jan–18 Aug 2026</div></header>
  <nav class="nav" role="tablist" aria-label="Complete analysis views">
    <button type="button" role="tab" data-view="overview" aria-selected="true">Overview</button>
    __REPORT_NAV__
    <button type="button" role="tab" data-view="narratives" aria-selected="false">Narratives</button>
    <button type="button" role="tab" data-view="data" aria-selected="false">Data register</button>
    <button type="button" role="tab" data-view="defense" aria-selected="false">Defense map</button>
    <button type="button" role="tab" data-view="method" aria-selected="false">Method & sources</button>
  </nav>
  <main>
    <section class="view" data-panel="overview"><div class="title-row"><div><h2>Complete analytical workspace</h2><p>All current report outputs and analysis-ready data are contained in this HTML.</p></div><span class="status">Single-file report</span></div><div class="metric-grid">__OVERVIEW__</div><div class="overview-note"><b>Reading order:</b> start with Strikes & energy, then inspect the short-window Event study and long-horizon Market position. Company & announcements lets you select any of the 46 companies and compare rebased market performance, imported company-linked announcements and conflict context; its coverage banner distinguishes missing data from zero events. Procurement remains exploratory. Narratives separates state organs, news and television; only manually reviewed labels may support the primary written argument. The Data register exposes every embedded analysis row.</div></section>
    __REPORT_SECTIONS__
    <section class="view" data-panel="narratives" hidden><div class="title-row"><div><h2>Announcements and media reporting</h2><p>Same taxonomy, separate source layers, document-level audit trail.</p></div><span class="status">Manual review boundary</span></div><div class="coverage-grid">__NARRATIVE_COVERAGE__</div><article class="panel"><div class="panel-head"><div><h3>Category comparison</h3><p>Primary values use reviewed labels. Suggested values are shown only as preparation status.</p></div></div><div class="table-wrap"><table><thead><tr><th>Category</th><th>State organs</th><th>News</th><th>Television</th></tr></thead><tbody>__NARRATIVE_MATRIX__</tbody></table></div><div class="note">Comparisons use shares within each source layer. State, news and television document totals are never added together. Missing media corpora remain missing rather than appearing as zero reporting.</div></article><article class="panel"><div class="panel-head"><div><h3>Document drill-down</h3><p>Automatic suggestions remain visibly distinct from manually reviewed evidence.</p></div></div><div class="controls"><div class="field"><label for="n-country">Publisher country</label><select id="n-country"><option value="ALL">All countries</option><option>DE</option><option>IL</option><option>IR</option><option>US</option><option>CN</option></select></div><div class="field"><label for="n-layer">Source layer</label><select id="n-layer"><option value="ALL">All layers</option><option value="STATE_ORGAN">State organs</option><option value="NEWS">News</option><option value="TELEVISION">Television</option></select></div><div class="field"><label for="n-status">Classification</label><select id="n-status"><option value="ALL">All statuses</option><option value="MANUALLY_REVIEWED">Manually reviewed</option><option value="AUTO_SUGGESTED">Automatic suggestions</option><option value="UNCLASSIFIED">Unclassified</option></select></div><div class="field"><label for="n-search">Search documents</label><input id="n-search" type="search" placeholder="Title, publisher, category"></div></div><div class="table-wrap"><table id="n-table"><thead></thead><tbody></tbody></table></div><div class="pager"><button id="n-prev" type="button">Previous</button><button id="n-next" type="button">Next</button><span id="n-page"></span></div></article></section>
    <section class="view" data-panel="data" hidden><div class="title-row"><div><h2>Complete embedded data register</h2><p>Analysis-ready CSV content used by the reports; raw evidence files remain in the project package.</p></div><span class="status">No row sampling</span></div><article class="panel"><div class="controls"><div class="field"><label for="d-dataset">Dataset</label><select id="d-dataset"></select></div><div class="field"><label for="d-search">Search current dataset</label><input id="d-search" type="search" placeholder="Search all columns"></div><div class="field"><label for="d-size">Rows per page</label><select id="d-size"><option>50</option><option>100</option><option>250</option></select></div></div><div class="table-wrap"><table id="d-table"><thead></thead><tbody></tbody></table></div><div class="pager"><button id="d-prev" type="button">Previous</button><button id="d-next" type="button">Next</button><button id="d-download" type="button">Download current CSV</button><span id="d-page"></span></div></article></section>
    <section class="view" data-panel="defense" hidden><div class="title-row"><div><h2>Research-question traceability</h2><p>Submitted parameters mapped to exact locations and current evidence coverage.</p></div><span class="status">Defense guide</span></div><article class="panel"><div class="table-wrap"><table><thead><tr><th>Submitted parameter</th><th>Location</th><th>Element to explain</th><th>Coverage</th></tr></thead><tbody>__DEFENSE_MAP__</tbody></table></div>__DEFENSE_MAP_NOTE__</article></section>
    <section class="view" data-panel="method" hidden><div class="title-row"><div><h2>Method and source coverage</h2><p>Roles, counting units, source boundaries and unresolved gaps.</p></div><span class="status">Audit layer</span></div><article class="panel"><div class="table-wrap"><table><thead><tr><th>Series</th><th>Source</th><th>Unit</th><th>Display / interpretation rule</th></tr></thead><tbody>__METHOD_TABLE__</tbody></table></div></article></section>
  </main>
</div>
<script>
const REPORTS=__REPORTS_JSON__;
const DATASETS=__DATASETS_JSON__;
const NARRATIVES=__NARRATIVE_JSON__;
const TAXONOMY=__TAXONOMY_JSON__;
const objectUrls={};
function activate(view){document.querySelectorAll('[data-view]').forEach(b=>b.setAttribute('aria-selected',String(b.dataset.view===view)));document.querySelectorAll('[data-panel]').forEach(p=>p.hidden=p.dataset.panel!==view);if(view.startsWith('report-'))loadReport(view.slice(7));if(view==='data')renderData();if(view==='narratives')renderNarratives()}
function loadReport(id){const frame=document.querySelector(`[data-report="${id}"]`);if(!frame||frame.dataset.loaded)return;const value=REPORTS[id];if(!value)return;const binary=atob(value);const bytes=new Uint8Array(binary.length);for(let i=0;i<binary.length;i++)bytes[i]=binary.charCodeAt(i);const url=URL.createObjectURL(new Blob([bytes],{type:'text/html;charset=utf-8'}));objectUrls[id]=url;frame.src=url;frame.dataset.loaded='true'}
document.querySelectorAll('[data-view]').forEach(button=>button.addEventListener('click',()=>activate(button.dataset.view)));
const dSelect=document.getElementById('d-dataset'),dSearch=document.getElementById('d-search'),dSize=document.getElementById('d-size');let dPage=0;for(const [id,item] of Object.entries(DATASETS)){const option=document.createElement('option');option.value=id;option.textContent=`${item.label} (${item.row_count} rows)`;dSelect.appendChild(option)}if(DATASETS.narrative_documents)dSelect.value='narrative_documents';
function decodeBase64Utf8(value){const binary=atob(value);const bytes=new Uint8Array(binary.length);for(let i=0;i<binary.length;i++)bytes[i]=binary.charCodeAt(i);return new TextDecoder('utf-8').decode(bytes).replace(/^\uFEFF/,'')}
function parseCsv(text){const rows=[];let row=[],cell='',quoted=false;for(let i=0;i<text.length;i++){const char=text[i];if(quoted){if(char==='"'&&text[i+1]==='"'){cell+='"';i++}else if(char==='"')quoted=false;else cell+=char}else if(char==='"')quoted=true;else if(char===','){row.push(cell);cell=''}else if(char==='\n'){row.push(cell.replace(/\r$/,''));rows.push(row);row=[];cell=''}else cell+=char}if(cell||row.length){row.push(cell.replace(/\r$/,''));rows.push(row)}const columns=rows.shift()||[];return rows.filter(values=>values.length>1||values[0]!=='').map(values=>Object.fromEntries(columns.map((column,index)=>[column,values[index]??''])))}
function datasetRecords(item){if(!item.records)item.records=parseCsv(decodeBase64Utf8(item.csv_b64));return item.records}
function filteredData(){const item=DATASETS[dSelect.value],records=datasetRecords(item);const query=dSearch.value.trim().toLocaleLowerCase();return query?records.filter(row=>item.columns.some(column=>String(row[column]??'').toLocaleLowerCase().includes(query))):records}
function renderTable(table,columns,records){const head=table.tHead||table.createTHead();const body=table.tBodies[0]||table.createTBody();head.replaceChildren();body.replaceChildren();const hr=head.insertRow();for(const column of columns){const th=document.createElement('th');th.textContent=column;hr.appendChild(th)}for(const record of records){const tr=body.insertRow();for(const column of columns){const td=tr.insertCell();const value=String(record[column]??'');if(column==='url'&&/^https?:\/\//.test(value)){const a=document.createElement('a');a.href=value;a.target='_blank';a.rel='noreferrer';a.textContent=value;td.appendChild(a)}else td.textContent=value}}
}
function renderData(){const item=DATASETS[dSelect.value];if(!item)return;const rows=filteredData(),size=Number(dSize.value),pages=Math.max(1,Math.ceil(rows.length/size));dPage=Math.min(dPage,pages-1);renderTable(document.getElementById('d-table'),item.columns,rows.slice(dPage*size,(dPage+1)*size));document.getElementById('d-page').textContent=`${item.path} · ${rows.length} matching row(s) · page ${dPage+1}/${pages}`;document.getElementById('d-prev').disabled=dPage===0;document.getElementById('d-next').disabled=dPage>=pages-1}
dSelect.addEventListener('change',()=>{dPage=0;renderData()});dSearch.addEventListener('input',()=>{dPage=0;renderData()});dSize.addEventListener('change',()=>{dPage=0;renderData()});document.getElementById('d-prev').addEventListener('click',()=>{dPage--;renderData()});document.getElementById('d-next').addEventListener('click',()=>{dPage++;renderData()});document.getElementById('d-download').addEventListener('click',()=>{const item=DATASETS[dSelect.value];const bytes=Uint8Array.from(atob(item.csv_b64),char=>char.charCodeAt(0));const url=URL.createObjectURL(new Blob([bytes],{type:'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download=dSelect.value+'.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)});
let nPage=0;function filteredNarratives(){const country=document.getElementById('n-country').value,layer=document.getElementById('n-layer').value,status=document.getElementById('n-status').value,query=document.getElementById('n-search').value.trim().toLocaleLowerCase();return NARRATIVES.filter(row=>(country==='ALL'||row.country_code===country)&&(layer==='ALL'||row.source_layer===layer)&&(status==='ALL'||row.classification_status===status)&&(!query||[row.title,row.publisher,row.categories,row.framing_codes].some(value=>String(value??'').toLocaleLowerCase().includes(query))))}
function renderNarratives(){const rows=filteredNarratives(),size=25,pages=Math.max(1,Math.ceil(rows.length/size));nPage=Math.min(nPage,pages-1);const columns=['published_at','country_code','source_layer','publisher','title','categories','framing_codes','classification_status','verification_status','url'];renderTable(document.getElementById('n-table'),columns,rows.slice(nPage*size,(nPage+1)*size));document.getElementById('n-page').textContent=`${rows.length} matching document(s) · page ${nPage+1}/${pages}`;document.getElementById('n-prev').disabled=nPage===0;document.getElementById('n-next').disabled=nPage>=pages-1}
for(const id of ['n-country','n-layer','n-status'])document.getElementById(id).addEventListener('change',()=>{nPage=0;renderNarratives()});document.getElementById('n-search').addEventListener('input',()=>{nPage=0;renderNarratives()});document.getElementById('n-prev').addEventListener('click',()=>{nPage--;renderNarratives()});document.getElementById('n-next').addEventListener('click',()=>{nPage++;renderNarratives()});
window.addEventListener('beforeunload',()=>Object.values(objectUrls).forEach(URL.revokeObjectURL));
</script>
</body>
</html>'''
