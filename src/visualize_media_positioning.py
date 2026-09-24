import argparse
import sys

from pathlib import Path

import pandas as pd

from src.black_doves_theme import (
    DARK_BOKEH_HTML_TEMPLATE,
    activate_black_doves_theme,
)
from src.black_doves_visualization import _header_html

# Fixed display order for the five focus countries, independent of
# whichever countries happen to have documents in a given export, so the
# y-axis stays stable as more sources are added later.
_COUNTRY_ORDER = ("IR", "IL", "US", "DE", "CN")
_COUNTRY_LABELS = {
    "IR": "Iran",
    "IL": "Israel",
    "US": "United States",
    "DE": "Germany",
    "CN": "China",
}
_BROADCASTER_CONTROL_COLORS = {
    "STATE_CONTROLLED": "#B03A2E",
    "PUBLIC_SERVICE_INDEPENDENT": "#3B82C4",
    "PRIVATE_INDEPENDENT": "#54C98A",
    "UNKNOWN": "#7A8B9C",
}
_BROADCASTER_CONTROL_LABELS = {
    "STATE_CONTROLLED": "State-controlled",
    "PUBLIC_SERVICE_INDEPENDENT": "Public service, editorially independent",
    "PRIVATE_INDEPENDENT": "Privately/commercially owned, independent",
    "UNKNOWN": "Control type not documented",
}


def create_media_positioning_chart(
    document_file,
    output_path,
    logo_path=None,
):
    from bokeh.core.templates import get_env
    from bokeh.layouts import column
    from bokeh.models import ColumnDataSource, Div, HoverTool, Span
    from bokeh.plotting import figure, save
    from bokeh.resources import INLINE

    activate_black_doves_theme()

    output_path = Path(output_path)
    if output_path.suffix.casefold() != ".html":
        raise ValueError("Media-positioning chart output must use .html")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    documents = pd.read_csv(document_file)
    documents["published_at"] = pd.to_datetime(
        documents["published_at"], utc=True, errors="coerce"
    )
    documents = documents.dropna(subset=["published_at", "country_code"])
    documents["broadcaster_control"] = (
        documents["broadcaster_control"].fillna("UNKNOWN")
    )
    documents["framing_codes"] = documents["framing_codes"].fillna("")
    documents["categories"] = documents["categories"].fillna("")
    documents["company_ids"] = documents["company_ids"].fillna("")

    countries_present = [
        code for code in _COUNTRY_ORDER if (documents["country_code"] == code).any()
    ]
    documents = documents[documents["country_code"].isin(countries_present)]

    documents["escalation_signal"] = documents["framing_codes"].apply(
        lambda value: (
            "Escalation-leaning"
            if "ESCALATION" in value.split(";") and "DE_ESCALATION" not in value.split(";")
            else "De-escalation-leaning"
            if "DE_ESCALATION" in value.split(";") and "ESCALATION" not in value.split(";")
            else "Mixed/both framings"
            if "ESCALATION" in value.split(";") and "DE_ESCALATION" in value.split(";")
            else "No escalation framing detected"
        )
    )
    documents["country_label"] = documents["country_code"].map(
        lambda code: _COUNTRY_LABELS.get(code, code)
    )
    documents["marker_size"] = documents["source_layer"].map(
        {"STATE_ORGAN": 8, "NEWS": 11, "TELEVISION": 13}
    ).fillna(9)

    chart = figure(
        title=(
            "Media and state-communication positioning by country "
            "(pilot sample)"
        ),
        x_axis_type="datetime",
        x_axis_label="Publication date",
        y_range=[
            _COUNTRY_LABELS.get(code, code) for code in reversed(countries_present)
        ],
        width=1050,
        height=380,
        sizing_mode="stretch_width",
        tools="pan,wheel_zoom,box_zoom,reset,save",
    )

    for control_type in (
        "STATE_CONTROLLED",
        "PUBLIC_SERVICE_INDEPENDENT",
        "PRIVATE_INDEPENDENT",
        "UNKNOWN",
    ):
        subset = documents[documents["broadcaster_control"] == control_type]
        if subset.empty:
            continue
        source = ColumnDataSource(subset)
        points = chart.scatter(
            "published_at",
            "country_label",
            source=source,
            size="marker_size",
            color=_BROADCASTER_CONTROL_COLORS[control_type],
            alpha=0.85,
            legend_label=_BROADCASTER_CONTROL_LABELS[control_type],
        )
        chart.add_tools(
            HoverTool(
                renderers=[points],
                tooltips=[
                    ("Country", "@country_label"),
                    ("Publisher", "@publisher"),
                    ("Layer", "@source_layer"),
                    ("Control", "@broadcaster_control"),
                    ("Title", "@title"),
                    ("Categories", "@categories"),
                    ("Framing", "@framing_codes"),
                    ("Escalation signal", "@escalation_signal"),
                    ("Linked companies", "@company_ids"),
                    ("Published", "@published_at{%F}"),
                ],
                formatters={"@published_at": "datetime"},
            )
        )

    chart.add_layout(
        Span(
            location=pd.Timestamp("2026-02-28", tz="UTC").timestamp() * 1000,
            dimension="height",
            line_color="#E9A23B",
            line_dash="dashed",
            line_width=2,
        )
    )
    chart.add_layout(
        Span(
            location=pd.Timestamp("2026-08-18", tz="UTC").timestamp() * 1000,
            dimension="height",
            line_color="#777777",
            line_dash="dotted",
            line_width=1,
        )
    )
    chart.legend.location = "top_left"
    chart.legend.label_text_font_size = "9pt"
    chart.legend.click_policy = "hide"
    chart.grid.grid_line_alpha = 0.2
    chart.toolbar.logo = None

    total_documents = len(documents)
    media_documents = int(
        documents["source_layer"].isin(["NEWS", "TELEVISION"]).sum()
    )
    source_counts = documents["source_id"].value_counts()
    dominant_source = source_counts.index[0] if len(source_counts) else "n/a"
    dominant_share = (
        round(100 * source_counts.iloc[0] / total_documents)
        if total_documents
        else 0
    )
    method_note = Div(
        text=(
            "<p style='color:#A9B5C3;font-size:12px'>"
            f"<b>Pilot sample, not a comprehensive media corpus:</b> "
            f"{total_documents} documents total, of which "
            f"{media_documents} are independently or state-broadcast "
            "media items (NEWS/TELEVISION) manually located and "
            "verified via web search or a user-supplied page export; "
            "the rest are official state-organ releases. A single "
            f"source, {dominant_source}, accounts for {dominant_share}% "
            "of all documents here, so the sample is skewed toward "
            "whichever outlet happened to be worked through most "
            "thoroughly rather than toward even cross-country balance; "
            "read the whole chart as a proof of concept for the "
            "pipeline, not as a trend finding. Colour encodes who edits "
            "the outlet's "
            "content (broadcaster_control), which is tracked separately "
            "from source_layer (who communicated the item) and from "
            "categories/framing_codes (what the item argues): state "
            "broadcasters like CGTN and Press TV are classified "
            "STATE_CONTROLLED rather than treated as independent press, "
            "since in Iran and China that is the most direct available "
            "signal of official messaging direction rather than a "
            "reason to exclude them. 'Escalation signal' comes from the "
            "same transparent, rule-based framing classifier used "
            "elsewhere in this report (src/services/narrative_classifier.py) "
            "and reflects pattern matches on the stored text, not a "
            "manually verified sentiment judgement, unless "
            "classification_status is MANUALLY_REVIEWED in the data "
            "register. The dashed line marks the primary event date "
            "(28 Feb 2026); the dotted line marks the end of the fixed "
            "core study window (18 Aug 2026) \u2014 points to its right "
            "fall in an extended monitoring horizon, not the core "
            "analysis period. Click a legend entry to hide that series."
            "</p>"
        ),
        sizing_mode="stretch_width",
    )

    header = Div(text=_header_html(logo_path), sizing_mode="stretch_width")
    dashboard = column(
        header,
        chart,
        method_note,
        sizing_mode="stretch_width",
        max_width=1100,
    )
    save(
        dashboard,
        filename=str(output_path),
        title="BLACK DOVES \u2013 Media Positioning",
        resources=INLINE,
        template=get_env().from_string(DARK_BOKEH_HTML_TEMPLATE),
    )

    return output_path, total_documents, media_documents


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Create the BLACK DOVES media/state-communication "
            "positioning chart from the extended-horizon narrative "
            "corpus export."
        )
    )
    parser.add_argument("document_file", type=Path)
    parser.add_argument("output_file", type=Path)
    parser.add_argument("--logo", type=Path)
    return parser


def main(arguments=None):
    parser = build_parser()
    options = parser.parse_args(arguments)

    try:
        output_path, total_documents, media_documents = (
            create_media_positioning_chart(
                document_file=options.document_file,
                output_path=options.output_file,
                logo_path=options.logo,
            )
        )
    except (FileNotFoundError, TypeError, ValueError) as error:
        parser.error(str(error))

    print("\nBLACK DOVES media positioning visualization completed.")
    print(f"Documents plotted: {total_documents}")
    print(f"Media (NEWS/TELEVISION) documents: {media_documents}")
    print(f"Chart: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
