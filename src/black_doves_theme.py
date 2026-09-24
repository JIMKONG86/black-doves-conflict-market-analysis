"""Shared BLACK DOVES dark visual language for standalone Bokeh reports."""


BACKGROUND = "#080C12"
SURFACE = "#111823"
PLOT_SURFACE = "#151E29"
ELEVATED = "#1B2735"
TEXT = "#F3F6FA"
MUTED = "#A9B5C3"
BORDER = "#344457"
ACCENT = "#FF6B5F"
BLUE = "#55B6E8"
AMBER = "#F2B84B"
GREEN = "#54C98A"
VIOLET = "#C792EA"
FIELD_BORDER = "#52667B"


_UI_VARIABLES = {
    "--color": TEXT,
    "--background-color": SURFACE,
    "--hover-color": ELEVATED,
    "--disabled-color": "#6F7D8C",
    "--border-color": BORDER,
    "--divider-color": BORDER,
    "--shortcut-color": MUTED,
    "--highlight-color": ACCENT,
    "--active-bg": ELEVATED,
    "--active-border": ACCENT,
    "--active-fg": TEXT,
    "--inactive-bg": SURFACE,
    "--inactive-fg": MUTED,
    "--icon-color": MUTED,
    "--icon-color-disabled": "#5B6877",
    "--placeholder-color": "#7F8B98",
    "--surface-background-color": ELEVATED,
    "--disabled-background-color": "#202A36",
    "--input-focus-border-color": ACCENT,
    "--input-focus-halo-color": "rgba(255, 107, 95, 0.28)",
    "--outline-color": ACCENT,
    "--box-shadow-color": "rgba(0, 0, 0, 0.42)",
    "--default": SURFACE,
    "--default-border": BORDER,
    "--default-hover": ELEVATED,
    "--default-hover-border": ACCENT,
    "--default-active": ELEVATED,
    "--default-active-border": ACCENT,
    "--light": SURFACE,
    "--light-border": BORDER,
    "--light-hover": ELEVATED,
    "--light-hover-border": ACCENT,
}


DARK_SELECT_STYLESHEET = f"""
:host {{
  color-scheme: dark;
  --font-size: 13px;
  --color: {TEXT};
  --background-color: {ELEVATED};
  --hover-color: #223244;
  --border-color: {FIELD_BORDER};
  --border: 1px solid {FIELD_BORDER};
  --border-radius: 7px;
  --padding-vertical: 7px;
  --padding-horizontal: 10px;
  --input-focus-border-color: {ACCENT};
  --input-focus-halo-color: rgba(255, 107, 95, 0.28);
}}
label {{
  color: {MUTED} !important;
  font-size: 12px;
  line-height: 1.25;
}}
.bk-input {{
  min-height: 40px;
  color: {TEXT} !important;
  background-color: {ELEVATED} !important;
  border: 1px solid {FIELD_BORDER} !important;
}}
.bk-input:hover {{
  color: {TEXT} !important;
  background-color: #223244 !important;
  border-color: #6B829A !important;
}}
.bk-input:focus {{
  color: {TEXT} !important;
  background-color: {ELEVATED} !important;
  border-color: {ACCENT} !important;
}}
select.bk-input {{
  color-scheme: dark;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 12 8'%3E%3Cpath fill='%23A9B5C3' d='M1 1l5 5 5-5' stroke='%23A9B5C3' stroke-width='1.5' fill='none' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E") !important;
  background-position: right 12px center !important;
  background-size: 10px 7px !important;
  background-repeat: no-repeat !important;
  padding-right: 34px !important;
}}
.bk-input option {{
  color: {TEXT} !important;
  background-color: {ELEVATED} !important;
}}
.bk-input option:checked {{
  color: {TEXT} !important;
  background-color: #26394C !important;
}}
"""


DARK_BUTTON_STYLESHEET = f"""
:host {{
  color-scheme: dark;
  --font-size: 13px;
  --color: {TEXT};
  --default: {ELEVATED};
  --default-border: {FIELD_BORDER};
  --default-hover: #223244;
  --default-hover-border: #6B829A;
  --default-active: #26394C;
  --default-active-border: {ACCENT};
  --outline: 2px solid {ACCENT};
  --border-radius: 7px;
  --padding-vertical: 7px;
  --padding-horizontal: 12px;
}}
.bk-btn-default {{
  min-height: 40px;
  color: {TEXT} !important;
  background-color: {ELEVATED} !important;
  border-color: {FIELD_BORDER} !important;
}}
.bk-btn-default:hover {{
  color: {TEXT} !important;
  background-color: #223244 !important;
  border-color: #6B829A !important;
}}
.bk-btn-default:focus,
.bk-btn-default:active,
.bk-active.bk-btn-default {{
  color: {TEXT} !important;
  background-color: #26394C !important;
  border-color: {ACCENT} !important;
}}
"""


DARK_TABS_STYLESHEET = f"""
:host {{
  color-scheme: dark;
  --color: {TEXT};
  --background-color: {ELEVATED};
  --hover-color: #223244;
  --border-color: {ACCENT};
  --divider-color: {BORDER};
  --divider: 1px solid {BORDER};
  --outline: 2px solid {ACCENT};
  --border-radius: 7px;
  --padding-vertical: 8px;
  --padding-horizontal: 12px;
}}
.bk-header {{
  color: {MUTED};
  background-color: {BACKGROUND};
  border-color: {BORDER} !important;
}}
.bk-headers-wrapper {{
  gap: 3px;
}}
.bk-tab {{
  color: {MUTED} !important;
  background-color: transparent !important;
  border-color: transparent !important;
}}
.bk-tab:hover {{
  color: {TEXT} !important;
  background-color: #223244 !important;
}}
.bk-tab:focus,
.bk-tab:active {{
  outline: 2px solid {ACCENT} !important;
  outline-offset: -3px;
}}
.bk-tab.bk-active {{
  color: {TEXT} !important;
  background-color: {ELEVATED} !important;
  border-color: {ACCENT} !important;
}}
"""


DARK_FILTER_ROW_STYLESHEET = f"""
:host {{
  align-items: flex-end;
  flex-wrap: wrap !important;
  column-gap: 12px !important;
  row-gap: 10px !important;
  padding: 12px;
  background: {SURFACE};
  border: 1px solid {BORDER};
  border-radius: 10px;
}}
:host > * {{
  flex: 1 1 205px !important;
  min-width: 185px !important;
}}
@media (max-width: 720px) {{
  :host > * {{
    flex-basis: calc(50% - 6px) !important;
    min-width: 220px !important;
  }}
}}
@media (max-width: 520px) {{
  :host {{ padding: 10px; }}
  :host > * {{
    flex-basis: 100% !important;
    min-width: 0 !important;
  }}
}}
"""


def style_dark_select(widget):
    """Apply the accessible BLACK DOVES dark style to a Bokeh select."""

    widget.css_variables = dict(_UI_VARIABLES)
    widget.stylesheets = [DARK_SELECT_STYLESHEET]
    return widget


def style_dark_button(widget):
    """Apply the accessible BLACK DOVES dark style to a Bokeh button."""

    widget.css_variables = dict(_UI_VARIABLES)
    widget.stylesheets = [DARK_BUTTON_STYLESHEET]
    return widget


def style_dark_tabs(widget):
    """Apply visible inactive, hover, focus and active states to tabs."""

    widget.css_variables = dict(_UI_VARIABLES)
    widget.stylesheets = [DARK_TABS_STYLESHEET]
    return widget


DARK_DOCUMENT_CSS = """
  :root { color-scheme: dark; }
  *, *::before, *::after { box-sizing: border-box; }
  html, body {
    width: 100%;
    max-width: 100%;
    min-height: 100%;
    margin: 0;
    padding: 0;
    overflow-x: hidden;
    color: #F3F6FA;
    background: #080C12;
    font-family: Inter, ui-sans-serif, system-ui, -apple-system,
      "Segoe UI", sans-serif;
    -webkit-text-size-adjust: 100%;
  }
  body {
    padding: max(12px, env(safe-area-inset-top))
             max(12px, env(safe-area-inset-right))
             max(12px, env(safe-area-inset-bottom))
             max(12px, env(safe-area-inset-left));
    background:
      radial-gradient(circle at 8% 0%, rgba(255,107,95,.08), transparent 30rem),
      #080C12;
  }
  h1, h2, h3, h4, b, strong { color: #F3F6FA; }
  p, label { color: #A9B5C3; }
  a { color: #55B6E8; }
  ::selection { color: #FFFFFF; background: rgba(255,107,95,.55); }
  * { scrollbar-color: #344457 #111823; scrollbar-width: thin; }
  @media (max-width: 600px) { body { padding: 8px; } }
"""


DARK_BOKEH_HTML_TEMPLATE = (
    """{% from macros import embed %}
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
    <meta name="color-scheme" content="dark">
    <meta name="theme-color" content="#080C12">
    <title>{{ title | e if title else "Bokeh Plot" }}</title>
    <style>
"""
    + DARK_DOCUMENT_CSS
    + """
    </style>
    {{ bokeh_css if bokeh_css }}
    {{ bokeh_js if bokeh_js }}
  </head>
  <body>
    {% for doc in docs %}
      {{ embed(doc) if doc.elementid }}
      {% for root in doc.roots %}{{ embed(root) }}{% endfor %}
    {% endfor %}
    {{ plot_script | indent(4) }}
  </body>
</html>
"""
)


def activate_black_doves_theme():
    """Apply and return the shared theme used by standalone Bokeh exports."""

    from bokeh.io import curdoc
    from bokeh.themes import Theme

    theme = Theme(
        json={
            "attrs": {
                "Plot": {
                    "background_fill_color": PLOT_SURFACE,
                    "border_fill_color": BACKGROUND,
                    "outline_line_color": BORDER,
                    "outline_line_alpha": 0.85,
                },
                "Grid": {
                    "grid_line_color": BORDER,
                    "grid_line_alpha": 0.38,
                    "minor_grid_line_color": BORDER,
                    "minor_grid_line_alpha": 0.12,
                },
                "Axis": {
                    "axis_line_color": BORDER,
                    "axis_line_alpha": 0.9,
                    "major_tick_line_color": MUTED,
                    "minor_tick_line_color": BORDER,
                    "major_label_text_color": MUTED,
                    "axis_label_text_color": TEXT,
                    "axis_label_text_font_style": "normal",
                },
                "Title": {
                    "text_color": TEXT,
                    "text_font_style": "normal",
                    "text_font_size": "1.15em",
                },
                "Legend": {
                    "background_fill_color": SURFACE,
                    "background_fill_alpha": 0.92,
                    "border_line_color": BORDER,
                    "border_line_alpha": 0.9,
                    "label_text_color": MUTED,
                    "title_text_color": TEXT,
                    "inactive_fill_color": BACKGROUND,
                    "inactive_fill_alpha": 0.75,
                },
                "BaseColorBar": {
                    "title_text_color": TEXT,
                    "major_label_text_color": MUTED,
                    "background_fill_color": SURFACE,
                    "major_tick_line_color": MUTED,
                    "bar_line_color": BORDER,
                },
                "LayoutDOM": {
                    "css_variables": _UI_VARIABLES,
                },
                "Tooltip": {
                    "css_variables": _UI_VARIABLES,
                },
                "Div": {
                    "styles": {
                        "color": MUTED,
                    },
                },
            }
        }
    )
    curdoc().theme = theme
    return theme
