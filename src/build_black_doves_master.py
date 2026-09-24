"""Build the narrative corpus and the consolidated BLACK DOVES dashboard."""

from pathlib import Path

from src.black_doves_visualization import create_black_doves_chart
from src.master_dashboard import create_master_dashboard
from src.services.narrative_corpus_builder import NarrativeCorpusBuilder
from src.visualize_fuel_price_lags import create_fuel_price_lag_dashboard
from src.visualize_market_position_analysis import (
    create_market_position_dashboard,
)
from src.visualize_media_positioning import create_media_positioning_chart
from src.visualize_casualty_damage import create_casualty_damage_chart
from src.visualize_market_universe_event_study import (
    create_market_universe_event_study_chart,
)
from src.visualize_procurement_event_study import (
    create_procurement_event_study_chart,
)
from src.visualize_company_announcements import (
    create_company_announcement_dashboard,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
STUDY_START = "2026-01-01"
STUDY_END = "2026-08-18"


def _refresh_dark_reports():
    analysis = PROJECT_ROOT / "data" / "analysis"
    output = PROJECT_ROOT / "output"
    logo = PROJECT_ROOT / "assets" / "black_doves_logo.png"

    create_fuel_price_lag_dashboard(
        timeline_file=(
            PROJECT_ROOT
            / "data"
            / "processed"
            / "energy"
            / "energy_price_timeline.csv"
        ),
        weekly_file=(
            PROJECT_ROOT
            / "data"
            / "processed"
            / "energy"
            / "energy_price_weekly_panel.csv"
        ),
        lag_file=analysis / "fuel_price_lag_results.csv",
        conflict_file=analysis / "weekly_conflict_features.csv",
        centcom_file=(
            PROJECT_ROOT
            / "data"
            / "validated"
            / "centcom_us_strike_operation_days.csv"
        ),
        output_path=output / "black_doves_energy_price_lag.html",
        logo_path=logo,
    )
    create_market_universe_event_study_chart(
        detail_file=analysis / "market_universe_event_window.csv",
        company_summary_file=(
            analysis / "market_universe_company_summary.csv"
        ),
        sample_summary_file=(
            analysis / "market_universe_sample_aar_caar.csv"
        ),
        output_path=(
            output / "black_doves_market_universe_event_study.html"
        ),
        logo_path=logo,
    )
    create_market_position_dashboard(
        detail_file=analysis / "market_position_full_period_detail.csv",
        company_file=analysis / "market_position_company_summary.csv",
        sample_file=analysis / "market_position_sample_aar_caar.csv",
        output_path=(
            output / "black_doves_long_horizon_market_position.html"
        ),
        logo_path=logo,
    )
    create_procurement_event_study_chart(
        input_file=analysis / "rheinmetall_procurement_event_window.csv",
        aggregate_output_file=(
            analysis / "rheinmetall_procurement_event_aggregate.csv"
        ),
        output_path=output / "black_doves_procurement_event_study.html",
        logo_path=logo,
    )
    create_black_doves_chart(
        input_file=analysis / "black_doves_country_week.csv",
        output_path=output / "black_doves_market_conflict.html",
        logo_path=logo,
        procurement_event_file=(
            analysis / "rheinmetall_procurement_event_summary.csv"
        ),
    )
    create_company_announcement_dashboard(
        market_file=(
            PROJECT_ROOT
            / "data"
            / "processed"
            / "market"
            / "company_benchmark_returns.csv"
        ),
        conflict_file=analysis / "weekly_conflict_features.csv",
        announcement_file=(
            PROJECT_ROOT
            / "data"
            / "reference"
            / "company_announcements.csv"
        ),
        centcom_file=(
            PROJECT_ROOT
            / "data"
            / "validated"
            / "centcom_us_strike_operation_days.csv"
        ),
        output_path=output / "black_doves_company_announcements.html",
        logo_path=logo,
    )


def main():
    from datetime import date

    _refresh_dark_reports()
    analysis_directory = PROJECT_ROOT / "data" / "analysis"
    builder = NarrativeCorpusBuilder()
    documents = builder.build(
        start_date=date.fromisoformat(STUDY_START),
        end_date=date.fromisoformat(STUDY_END),
        announcement_directory=PROJECT_ROOT / "data" / "raw" / "announcements",
        media_directory=PROJECT_ROOT / "data" / "raw" / "media",
        media_registry_file=PROJECT_ROOT / "config" / "media_sources.json",
        centcom_file=(
            PROJECT_ROOT
            / "data"
            / "validated"
            / "centcom_us_strike_operation_days.csv"
        ),
        review_directory=(
            PROJECT_ROOT / "data" / "validated" / "narrative_reviews"
        ),
    )
    builder.export(
        documents,
        analysis_directory / "narrative_documents.csv",
        analysis_directory / "narrative_category_summary.csv",
        analysis_directory / "narrative_coverage.csv",
    )

    # Media-positioning pilot sample: the four manually-verified media
    # documents added for the broadcaster_control feature are genuinely
    # dated (real publication dates), and three of them fall after the
    # fixed core study window (1 Jan-18 Aug 2026). Rather than silently
    # widen the core window's own fixed period, a second, clearly
    # separate export uses an extended monitoring horizon (matching the
    # "Supporting horizon" concept already used elsewhere in this
    # project, e.g. the company/announcement explorer) so the media
    # positioning chart can show them without touching the core dataset.
    media_positioning_documents = builder.build(
        start_date=date(2025, 1, 1),
        end_date=date(2026, 9, 14),
        announcement_directory=PROJECT_ROOT / "data" / "raw" / "announcements",
        media_directory=PROJECT_ROOT / "data" / "raw" / "media",
        media_registry_file=PROJECT_ROOT / "config" / "media_sources.json",
        centcom_file=(
            PROJECT_ROOT
            / "data"
            / "validated"
            / "centcom_us_strike_operation_days.csv"
        ),
        review_directory=(
            PROJECT_ROOT / "data" / "validated" / "narrative_reviews"
        ),
    )
    builder.export(
        media_positioning_documents,
        analysis_directory / "narrative_documents_media_positioning.csv",
        analysis_directory / "narrative_category_summary_media_positioning.csv",
        analysis_directory / "narrative_coverage_media_positioning.csv",
    )
    create_media_positioning_chart(
        document_file=(
            analysis_directory / "narrative_documents_media_positioning.csv"
        ),
        output_path=PROJECT_ROOT / "output" / "black_doves_media_positioning.html",
        logo_path=PROJECT_ROOT / "assets" / "black_doves_logo.png",
    )
    create_casualty_damage_chart(
        estimates_file=(
            PROJECT_ROOT / "data" / "reference" / "casualty_damage_estimates.csv"
        ),
        output_path=PROJECT_ROOT / "output" / "black_doves_casualty_damage.html",
        logo_path=PROJECT_ROOT / "assets" / "black_doves_logo.png",
    )

    output = (
        PROJECT_ROOT / "output" / "black_doves_complete_analysis.html"
    )
    create_master_dashboard(PROJECT_ROOT, output)
    manually_reviewed = sum(
        document.classification_status == "MANUALLY_REVIEWED"
        for document in documents
    )
    print(f"Narrative documents: {len(documents)}")
    print(f"Manually reviewed: {manually_reviewed}")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
