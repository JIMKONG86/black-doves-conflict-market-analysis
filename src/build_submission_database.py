"""Build the compact SQLite database shipped with the final report."""

from pathlib import Path

from src.persistence import DatasetMetadata, SubmissionDatabase


ROOT = Path(__file__).resolve().parents[1]
DATABASE_FILE = (
    ROOT
    / "data"
    / "processed"
    / "submission"
    / "black_doves_submission.sqlite"
)


DATASETS = (
    DatasetMetadata(
        "event_study_company_summary",
        "data/analysis/market_universe_company_summary.csv",
        "Yahoo Finance snapshots for exchange-listed securities and configured national benchmarks",
        "https://finance.yahoo.com/",
        "2026-02-23/2026-03-16",
        "decimal return",
        "DERIVED_DESCRIPTIVE",
    ),
    DatasetMetadata(
        "event_study_window",
        "data/analysis/market_universe_event_window.csv",
        "Yahoo Finance snapshots for exchange-listed securities and configured national benchmarks",
        "https://finance.yahoo.com/",
        "2026-02-23/2026-03-16",
        "decimal return",
        "DERIVED_DESCRIPTIVE",
    ),
    DatasetMetadata(
        "event_study_bootstrap",
        "data/analysis/event_study_bootstrap_summary.csv",
        "Derived from event-study company summary",
        "data/analysis/market_universe_company_summary.csv",
        "Event 2026-02-28; market window [0,+10]",
        "decimal return",
        "DERIVED_BOOTSTRAP_INTERVAL",
    ),
    DatasetMetadata(
        "long_horizon_company_summary",
        "data/analysis/market_position_company_summary.csv",
        "Yahoo Finance snapshots for exchange-listed securities and configured national benchmarks",
        "https://finance.yahoo.com/",
        "2026-01-01/2026-08-18",
        "decimal return",
        "DERIVED_DESCRIPTIVE",
    ),
    DatasetMetadata(
        "energy_price_timeline",
        "data/processed/energy/energy_price_timeline.csv",
        "EIA and European Commission Weekly Oil Bulletin",
        "data/raw/energy/",
        "2026-01-01/2026-08-18",
        "row-specific",
        "OBSERVED_OFFICIAL_SOURCE",
    ),
    DatasetMetadata(
        "energy_weekly_panel",
        "data/processed/energy/energy_price_weekly_panel.csv",
        "EIA and European Commission Weekly Oil Bulletin",
        "data/processed/energy/energy_price_timeline.csv",
        "2025-12-29/2026-08-17",
        "mixed; see column names",
        "DERIVED_WEEKLY_ALIGNMENT",
    ),
    DatasetMetadata(
        "fuel_price_lags_holm",
        "data/analysis/fuel_price_lag_adjusted.csv",
        "Derived from aligned EIA and European Commission weekly prices",
        "data/processed/energy/energy_price_weekly_panel.csv",
        "2025-12-29/2026-08-17",
        "correlation coefficient and p-value",
        "DERIVED_EXPLORATORY",
    ),
    DatasetMetadata(
        "iran_china_oil_dependency",
        "data/reference/iran_china_oil_dependency.csv",
        "EIA, Reuters/Kpler and U.S. Treasury",
        "data/reference/iran_china_oil_dependency.csv",
        "2023/2026",
        "percent; million barrels/day",
        "ESTIMATE_NOT_CUSTOMS",
    ),
    DatasetMetadata(
        "arms_supply_context",
        "data/reference/arms_supply_context.csv",
        "Stockholm International Peace Research Institute",
        "https://www.sipri.org/sites/default/files/2026-03/fs_2603_at_2025.pdf",
        "2021/2025",
        "percent of major-arms import volume",
        "ESTIMATE_PRE_CONFLICT_CONTEXT",
    ),
    DatasetMetadata(
        "country_role_profile",
        "data/reference/country_role_profile.csv",
        "Official government statements plus documented economic context",
        "data/reference/country_role_profile.csv",
        "2021/2026",
        "qualitative multidimensional classification",
        "SOURCE_TRIANGULATED_ROLE_CODING",
    ),
    DatasetMetadata(
        "ucdp_method_reference",
        "data/reference/ucdp_method_reference.csv",
        "Uppsala Conflict Data Program",
        "https://ucdp.uu.se/downloads/",
        "Definitions accessed 2026-09-14; annual data through 2025",
        "methodological source register",
        "REFERENCE_ONLY_NOT_STATISTICAL_INPUT",
    ),
    DatasetMetadata(
        "centcom_operation_days",
        "data/validated/centcom_us_strike_operation_days.csv",
        "U.S. Central Command public releases",
        "https://www.centcom.mil/MEDIA/PRESS-RELEASES/",
        "2026-02-28/2026-08-18",
        "official release-confirmed operation day",
        "OFFICIAL_CLAIM_NOT_INDEPENDENT_VERIFICATION",
    ),
    DatasetMetadata(
        "rheinmetall_procurement_events",
        "data/analysis/rheinmetall_procurement_event_summary.csv",
        "Rheinmetall primary corporate announcements",
        "data/reference/rheinmetall_air_defence_procurement_events.csv",
        "2025",
        "decimal return",
        "DERIVED_EXPLORATORY_SMALL_SAMPLE",
    ),
    DatasetMetadata(
        "post_hoc_market_checks",
        "data/analysis/post_hoc_market_checks.csv",
        "Derived from the complete Yahoo Finance market panel and two dated source anchors",
        "data/processed/market/company_benchmark_returns.csv",
        "2026-07-01/2026-08-10",
        "decimal return",
        "POST_HOC_DESCRIPTIVE_NOT_CAUSAL",
    ),
    DatasetMetadata(
        "blackrock_13f_holdings",
        "data/reference/blackrock_13f_holdings.csv",
        "U.S. Securities and Exchange Commission",
        "https://www.sec.gov/Archives/edgar/data/2012383/000201238326003238/0002012383-26-003238-index.htm",
        "Position date 2026-06-30; filed 2026-08-07",
        "shares and U.S. dollars",
        "OBSERVED_REGULATORY_FILING",
    ),
    DatasetMetadata(
        "patriot_supply_context",
        "data/reference/patriot_supply_context.csv",
        "CSIS, Associated Press, RTX and U.S. Army",
        "data/reference/patriot_supply_context.csv",
        "2026-04-10/2026-08-09",
        "row-specific estimate or qualitative signal",
        "CONTEXT_NOT_CAUSAL",
    ),
    DatasetMetadata(
        "additional_findings_audit",
        "data/reference/additional_findings_audit.csv",
        "Source-critical audit of user-supplied additional findings",
        "data/reference/additional_findings_audit.csv",
        "Audited 2026-09-14",
        "claim-level inclusion decision",
        "METHODOLOGICAL_AUDIT",
    ),
    DatasetMetadata(
        "media_sampling_audit",
        "data/reference/media_sampling_audit.csv",
        "Derived from the excluded 247-document media pilot",
        "user-supplied/black_doves_changed_files_only.zip",
        "2026 pilot; audited 2026-09-14",
        "document count and percent",
        "DERIVED_COVERAGE_AUDIT_ONLY",
    ),
)


def main():
    database = SubmissionDatabase(DATABASE_FILE)
    database.create_schema()
    for metadata in DATASETS:
        row_count = database.import_csv(ROOT, metadata)
        print(f"{metadata.dataset_key}: {row_count} rows")
    print(f"SQLite database: {DATABASE_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
