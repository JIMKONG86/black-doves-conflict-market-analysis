# BLACK DOVES: complete market-universe event study

This extension applies one or more documented events to the analysis-ready
46-company market panel. It creates company-level event windows and descriptive
average abnormal return (AAR) and cumulative average abnormal return (CAAR)
series.

## Scientific boundary

- The eight pre-specified companies remain the confirmatory sample.
- The 37 remaining pre-existing companies form an exploratory sample.
- Volkswagen is retained separately as a post-hoc exploratory robustness case.
- The event date is mapped separately for every company to the first available
  trading day on or after the calendar event date. This preserves differences
  between exchange calendars instead of imposing one global trading date.
- Daily abnormal return in this event-study extension (AAR/CAAR, CAR) remains
  the naive market-adjusted return `company_return - local_benchmark_return`.
  This is a legitimate, common event-study quantity, but it is not an
  OLS-based expected-return deviation and must not be described as one.
- CAR is the arithmetic sum of daily abnormal returns within the stated window.
- AAR is the cross-company mean abnormal return for one relative trading day.
- CAAR is the cumulative sum of AAR beginning at relative trading day `-5`.
- Results are descriptive for this AAR/CAAR extension specifically. It does
  not calculate inferential significance, control concurrent news or infer
  causality.
- **Update:** an OLS single-factor market model (`company_return = alpha +
  beta * benchmark_return`, fitted on all trading days strictly before the
  fixed event date) is now estimated separately per company in
  `src/services/ols_market_model.py` and is available in
  `data/processed/market/company_benchmark_returns.csv` and in the report's
  data register as `ols_alpha`, `ols_beta`, `ols_r_squared`,
  `ols_estimation_window_observations`, `market_model_expected_return` and
  `market_model_abnormal_return`. This satisfies the written assignment's
  requirement to use Ordinary Least Squares for the abnormal-return
  estimation. As of this update, the AAR/CAAR charts in this event-study
  extension still use the naive market-adjusted return, not
  `market_model_abnormal_return`; rewiring the AAR/CAAR aggregation to the
  OLS series (or presenting both side by side) is a follow-up, not yet done
  here.

The included event is the primary 28 February 2026 date fixed in the approved
research design. Its `RESEARCH_DESIGN_PRE_SPECIFIED` status does not claim that
the linked news article is a primary source or independently validates market
effects.

## Files

```text
data/reference/black_doves_market_events.csv
src/models/market_event.py
src/data_access/market_event_reader.py
src/services/market_universe_event_study.py
src/analyze_market_universe_event_study.py
tests/test_market_event_reader.py
tests/test_market_universe_event_study.py
```

The package also contains the corrected provider mappings in
`config/company_market_universe.csv`, the associated configuration test and an
updated market-universe README.

## Install and test

Extract the ZIP directly into the project root and overwrite matching files.

```powershell
Expand-Archive -LiteralPath `
    ".\black_doves_market_universe_event_study_v1.zip" `
    -DestinationPath "." `
    -Force

.\.venv\Scripts\python.exe -m compileall -q src tests

.\.venv\Scripts\python.exe -m unittest `
    tests.test_market_event_reader `
    tests.test_market_universe_event_study `
    tests.test_company_market_universe `
    -v

.\.venv\Scripts\python.exe -m unittest discover `
    -s tests `
    -p "test_*.py"
```

_Linux/macOS equivalent (after `source .venv/bin/activate`):_

```bash
unzip -o "black_doves_market_universe_event_study_v1.zip" -d .

.venv/bin/python -m compileall -q src tests

.venv/bin/python -m unittest \
    tests.test_market_event_reader \
    tests.test_market_universe_event_study \
    tests.test_company_market_universe \
    -v

.venv/bin/python -m unittest discover \
    -s tests \
    -p "test_*.py"
```

The event-study functionality adds eight tests and the provider-mapping guard
adds one. With the last confirmed 238-test baseline, the expected full-suite
result is 247 tests.

## Run the complete-universe analysis

The default paths match the files already produced by the market-universe
pipeline:

```powershell
.\.venv\Scripts\python.exe -m src.analyze_market_universe_event_study
```

_Linux/macOS equivalent (after `source .venv/bin/activate`):_

```bash
.venv/bin/python -m src.analyze_market_universe_event_study
```

Expected scope for the included event and the complete market panel:

```text
Events: 1
Companies: 46
Confirmatory companies: 8
Exploratory companies: 37
Post-hoc companies: 1
Event-window rows: 736
Trading-day window: -5 to +10
```

## Outputs

- `data/analysis/market_universe_event_window.csv`: all 16 relative trading
  days for every company and event, including provenance and metadata.
- `data/analysis/market_universe_company_summary.csv`: one row per company and
  event with event-day return and CAR measures.
- `data/analysis/market_universe_sample_aar_caar.csv`: AAR/CAAR separated into
  confirmatory, exploratory and post-hoc samples.
- `data/analysis/market_universe_role_aar_caar.csv`: descriptive AAR/CAAR by
  company role category.

## Inspect the company-level result

```powershell
Import-Csv ".\data\analysis\market_universe_company_summary.csv" |
    Sort-Object {[double]$_.post_event_car_0_10} -Descending |
    Select-Object `
        company_name, `
        sample_group, `
        role_category, `
        effective_market_date, `
        event_day_abnormal_return, `
        post_event_car_0_1, `
        post_event_car_0_5, `
        post_event_car_0_10 |
    Format-Table -AutoSize
```

Positive CAR means that a company outperformed its configured local benchmark
over the stated event window; negative CAR means underperformance. This alone
does not establish that the conflict event caused the difference.
