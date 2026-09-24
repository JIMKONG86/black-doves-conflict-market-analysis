import unittest

from src.black_doves_theme import (
    DARK_BOKEH_HTML_TEMPLATE,
    DARK_BUTTON_STYLESHEET,
    DARK_FILTER_ROW_STYLESHEET,
    DARK_SELECT_STYLESHEET,
    DARK_TABS_STYLESHEET,
    activate_black_doves_theme,
)
from src.master_dashboard import _PAGE_TEMPLATE


class TestBlackDovesDarkTheme(unittest.TestCase):
    def test_master_and_report_templates_force_dark_mode(self):
        self.assertIn("color-scheme:dark", _PAGE_TEMPLATE)
        self.assertIn('content="#080c12"', _PAGE_TEMPLATE)
        self.assertNotIn("prefers-color-scheme:dark", _PAGE_TEMPLATE)
        self.assertIn("color-scheme: dark", DARK_BOKEH_HTML_TEMPLATE)
        self.assertIn("#080C12", DARK_BOKEH_HTML_TEMPLATE)

    def test_bokeh_theme_styles_plot_and_controls(self):
        theme = activate_black_doves_theme()
        attrs = theme._json["attrs"]
        self.assertEqual(attrs["Plot"]["background_fill_color"], "#151E29")
        self.assertEqual(attrs["Axis"]["major_label_text_color"], "#A9B5C3")
        self.assertEqual(
            attrs["LayoutDOM"]["css_variables"]["--background-color"],
            "#111823",
        )

    def test_filter_controls_define_accessible_dark_states(self):
        self.assertIn("color-scheme: dark", DARK_SELECT_STYLESHEET)
        self.assertIn("color: #F3F6FA", DARK_SELECT_STYLESHEET)
        self.assertIn("background-color: #1B2735", DARK_SELECT_STYLESHEET)
        self.assertIn("border: 1px solid #52667B", DARK_SELECT_STYLESHEET)
        self.assertIn("border-color: #FF6B5F", DARK_SELECT_STYLESHEET)
        self.assertIn(".bk-input option", DARK_SELECT_STYLESHEET)

    def test_filter_row_is_compact_and_responsive(self):
        self.assertIn("flex-wrap: wrap", DARK_FILTER_ROW_STYLESHEET)
        self.assertIn("flex: 1 1 205px", DARK_FILTER_ROW_STYLESHEET)
        self.assertIn("max-width: 520px", DARK_FILTER_ROW_STYLESHEET)

    def test_buttons_and_tabs_define_dark_interaction_states(self):
        self.assertIn(".bk-btn-default", DARK_BUTTON_STYLESHEET)
        self.assertIn("background-color: #1B2735", DARK_BUTTON_STYLESHEET)
        self.assertIn("border-color: #FF6B5F", DARK_BUTTON_STYLESHEET)
        self.assertIn(".bk-tab.bk-active", DARK_TABS_STYLESHEET)
        self.assertIn("color: #A9B5C3", DARK_TABS_STYLESHEET)
        self.assertIn("background-color: #1B2735", DARK_TABS_STYLESHEET)


if __name__ == "__main__":
    unittest.main()
