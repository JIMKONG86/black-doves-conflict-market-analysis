import base64
import csv
import tempfile
import unittest
from pathlib import Path

from src.master_dashboard import (
    _inline_bokeh_resources,
    _master_brand_html,
    create_master_dashboard,
)


class TestMasterDashboard(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        (self.root / "output").mkdir()
        (self.root / "data" / "analysis").mkdir(parents=True)
        (self.root / "data" / "processed" / "energy").mkdir(parents=True)
        (self.root / "data" / "processed" / "market").mkdir(parents=True)
        (self.root / "data" / "validated").mkdir(parents=True)
        (self.root / "data" / "reference").mkdir(parents=True)
        (self.root / "config").mkdir()
        resource = (
            "<html><script>/* BEGIN bokeh.min.js */CORE"
            "/* END bokeh.min.js */</script>"
            "<script>/* BEGIN bokeh-widgets.min.js */WIDGETS"
            "/* END bokeh-widgets.min.js */</script></html>"
        )
        report_names = {
            "black_doves_energy_price_lag.html": resource,
            "black_doves_market_universe_event_study.html": "<html>EVENT</html>",
            "black_doves_long_horizon_market_position.html": "<html>POSITION</html>",
            "black_doves_company_announcements.html": "<html>COMPANIES</html>",
            "black_doves_procurement_event_study.html": "<html>PROCUREMENT</html>",
        }
        for name, content in report_names.items():
            (self.root / "output" / name).write_text(content, encoding="utf-8")
        self._write_csv(
            "narrative_coverage.csv",
            [
                ["source_layer", "source_count", "document_count", "reviewed_document_count", "coverage_status"],
                ["STATE_ORGAN", "1", "1", "0", "PARTIAL"],
                ["NEWS", "0", "0", "0", "MISSING"],
                ["TELEVISION", "0", "0", "0", "MISSING"],
            ],
        )
        category_rows = [[
            "source_layer", "category_code", "category_label",
            "reviewed_document_count", "reviewed_layer_total", "reviewed_share",
            "suggested_document_count", "suggested_layer_total", "suggested_share",
        ]]
        from src.services.narrative_classifier import NARRATIVE_TAXONOMY
        for layer in ("STATE_ORGAN", "NEWS", "TELEVISION"):
            for code, item in NARRATIVE_TAXONOMY.items():
                category_rows.append([
                    layer, code, item["label"], "0", "0", "",
                    "1" if layer == "STATE_ORGAN" else "0",
                    "1" if layer == "STATE_ORGAN" else "0",
                    "1" if layer == "STATE_ORGAN" else "",
                ])
        self._write_csv("narrative_category_summary.csv", category_rows)
        self._write_csv(
            "narrative_documents.csv",
            [["document_id", "title", "country_code", "source_layer"], ["1", "Test", "US", "STATE_ORGAN"]],
        )
        self._write_csv(
            "market_universe_company_summary.csv",
            [["company_id"], ["CMP001"]],
        )
        self._write_csv(
            "energy_price_weekly_panel.csv",
            [["fuel_observation_date"], ["2026-01-05"]],
            base=self.root / "data" / "processed" / "energy",
        )
        self._write_csv(
            "centcom_us_strike_operation_days.csv",
            [["event_date", "include_in_core_series"], ["2026-02-28", "true"]],
            base=self.root / "data" / "validated",
        )

    def tearDown(self):
        self.temporary_directory.cleanup()

    def _write_csv(self, name, rows, base=None):
        path = (base or self.root / "data" / "analysis") / name
        with path.open("w", encoding="utf-8", newline="") as file:
            csv.writer(file).writerows(rows)

    def test_replaces_cdn_resources_with_inline_scripts(self):
        resource = (
            "<script>/* BEGIN bokeh.min.js */CORE"
            "/* END bokeh.min.js */</script>"
        )
        document = (
            '<script src="https://cdn.bokeh.org/bokeh/release/'
            'bokeh-3.10.0.min.js"></script>'
        )

        result = _inline_bokeh_resources(document, resource)

        self.assertIn("CORE", result)
        self.assertNotIn("cdn.bokeh.org", result)

    def test_embeds_the_dark_mode_logo_in_the_master_header(self):
        assets = self.root / "assets"
        assets.mkdir()
        (assets / "black_doves_logo.png").write_bytes(b"new-logo")

        result = _master_brand_html(self.root)

        encoded = base64.b64encode(b"new-logo").decode("ascii")
        self.assertIn(f"data:image/png;base64,{encoded}", result)
        self.assertIn("dove carrying barbed wire", result)
        self.assertNotIn(">BD<", result)

    def test_creates_one_master_html_with_reports_and_complete_data_register(self):
        output = self.root / "output" / "master.html"

        result = create_master_dashboard(self.root, output)
        document = result.read_text(encoding="utf-8")

        self.assertIn("BLACK DOVES · Complete Analysis", document)
        self.assertIn("Complete embedded data register", document)
        self.assertIn("Narratives", document)
        self.assertIn("missing, not zero", document)
        self.assertIn("No row sampling", document)
        self.assertIn("Company &amp; announcements", document)
        self.assertIn("Core study window", document)
        self.assertIn("csv_b64", document)
        encoded = base64.b64encode(b"<html>EVENT</html>").decode("ascii")
        self.assertIn(encoded, document)


if __name__ == "__main__":
    unittest.main()
