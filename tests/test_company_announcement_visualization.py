import tempfile
import unittest

from pathlib import Path

import pandas as pd

from src.visualize_company_announcements import (
    _filter_callback_code,
    _load_announcements,
    _load_market,
    create_company_announcement_dashboard,
)


class TestCompanyAnnouncementVisualization(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary_directory.name)
        self.market_file = self.directory / "market.csv"
        self.conflict_file = self.directory / "conflict.csv"
        self.announcement_file = self.directory / "announcements.csv"
        self.centcom_file = self.directory / "centcom.csv"
        self._write_inputs()

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_creates_selector_for_every_company_and_coverage_warning(self):
        output = self.directory / "company_explorer.html"

        result = create_company_announcement_dashboard(
            market_file=self.market_file,
            conflict_file=self.conflict_file,
            announcement_file=self.announcement_file,
            centcom_file=self.centcom_file,
            output_path=output,
        )

        document = result.read_text(encoding="utf-8")
        self.assertIn("Company &amp; Announcement Explorer", document)
        self.assertIn("Alpha Defence (ALP)", document)
        self.assertIn("Beta Energy (BET)", document)
        self.assertIn("Announcement coverage: MISSING", document)
        self.assertIn("Zero markers must not be read as zero", document)
        self.assertIn("Imported company announcements", document)
        self.assertIn("Aligned-day abnormal return", document)
        self.assertIn("Aligned market date", document)
        self.assertIn(".bk-input option", document)
        self.assertNotIn("https://cdn.bokeh.org", document)

    def test_filter_callback_never_indexes_yaxis_client_side(self):
        # Regression test: BokehJS Figure models do not expose a usable
        # `.yaxis` array client-side (unlike the Python API), so
        # `conflict_chart.yaxis[0].axis_label = ...` inside the CustomJS
        # threw "Cannot read properties of undefined (reading '0')" on
        # every single filter change, silently aborting the rest of the
        # callback before it could update the status banner and
        # announcement list. Confirmed live in a real headless-Chromium
        # session. The fix resolves the axis on the Python side and
        # passes it into `args` (the same pattern already used in
        # src/visualize_fuel_price_lags.py), so the JS body must never
        # re-index `.yaxis[` itself, and must use the resolved
        # `conflict_axis` reference instead.
        callback = _filter_callback_code()

        self.assertNotIn(".yaxis[", callback)
        self.assertIn("conflict_axis.axis_label", callback)

    def test_callback_rebases_market_data_and_filters_announcements(self):
        callback = _filter_callback_code()

        self.assertIn("firstCompanyPrice", callback)
        self.assertIn("visibleAnnouncementIndices", callback)
        self.assertIn("nearestMarketIndices", callback)
        self.assertIn("event_day_abnormal_return", callback)
        self.assertIn("Announcement coverage: MISSING", callback)
        self.assertIn("conflict_metric_filter.value", callback)
        self.assertIn("centcom_source.data", callback)

    def test_rejects_unknown_announcement_company(self):
        announcements = pd.read_csv(self.announcement_file)
        announcements.loc[0, "company_id"] = "CMP999"
        announcements.to_csv(self.announcement_file, index=False)
        market = _load_market(self.market_file)

        with self.assertRaisesRegex(ValueError, "unknown company IDs"):
            _load_announcements(self.announcement_file, market)

    def _write_inputs(self):
        market_rows = []

        for company_id, company_name, ticker in (
            ("CMP001", "Alpha Defence", "ALP"),
            ("CMP002", "Beta Energy", "BET"),
        ):
            for index, market_date in enumerate(
                pd.to_datetime(["2025-01-02", "2025-01-03", "2026-01-02"])
            ):
                market_rows.append(
                    {
                        "company_id": company_id,
                        "company_name": company_name,
                        "market_data_ticker": ticker,
                        "benchmark_ticker": "^INDEX",
                        "role_category": "Test role",
                        "Date": market_date,
                        "company_price": 100 + index * 2,
                        "benchmark_price": 100 + index,
                        "company_return": 0.01,
                        "benchmark_return": 0.005,
                        "abnormal_return": 0.005,
                    }
                )
        pd.DataFrame(market_rows).to_csv(self.market_file, index=False)
        pd.DataFrame(
            [
                {
                    "week_end_date": "2025-01-04",
                    "country_name": "Iran",
                    "country_code": "IR",
                    "strike_events": 2,
                    "strike_fatalities": 1,
                    "air_drone_strike_events": 1,
                    "air_drone_strike_fatalities": 1,
                    "shelling_artillery_missile_events": 1,
                    "shelling_artillery_missile_fatalities": 0,
                }
            ]
        ).to_csv(self.conflict_file, index=False)
        pd.DataFrame(
            [
                {
                    "announcement_id": "announcement-1",
                    "announcement_date": "2025-01-03",
                    "company_id": "CMP001",
                    "company_name": "Alpha Defence",
                    "market_data_ticker": "ALP",
                    "announcement_type": "order_award",
                    "title": "Verified order",
                    "source_name": "Alpha Defence",
                    "source_url": "https://example.com/order",
                    "verification_status": "primary_source_confirmed",
                    "coverage_status": "PARTIAL_CURATED",
                    "record_scope": "TEST_SCOPE",
                    "counterparty_name": "Test ministry",
                    "counterparty_country_code": "DE",
                    "systems": "System A",
                    "contract_value_eur": "",
                    "value_description": "Not disclosed",
                    "reviewed_by": "Tester",
                    "notes": "Test row",
                }
            ]
        ).to_csv(self.announcement_file, index=False)
        pd.DataFrame(
            [
                {
                    "event_date": "2026-01-02",
                    "operation_day_count": 1,
                    "include_in_core_series": True,
                    "title": "Confirmed operation",
                }
            ]
        ).to_csv(self.centcom_file, index=False)


if __name__ == "__main__":
    unittest.main()
