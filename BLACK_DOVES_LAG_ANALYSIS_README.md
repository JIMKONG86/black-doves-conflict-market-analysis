# BLACK DOVES: exploratory lag analysis

This extension measures same-week and delayed associations between weekly
conflict intensity and Rheinmetall's market-adjusted return.

It adds only new files and does not replace the existing import, market,
analysis or visualization modules.

## Method

For every conflict metric `C` and lag `k`, the analysis compares:

```text
C in week t  <->  abnormal market return in week t + k
```

- Lag `0` means the conflict and market observations belong to the same week.
- Lags `1`, `2` and `4` measure the market response one, two and four weeks
  after the conflict observation.
- Pearson correlation measures linear association.
- Spearman correlation measures rank-based monotonic association and is less
  sensitive to the very large conflict spikes visible in the chart.
- Results are produced for Iran, Israel and the sum of both countries.
- Identical weekly market returns are counted once in the combined analysis,
  not once per country row.
- Missing calendar weeks are rejected because otherwise a lag of one row would
  not necessarily mean a lag of one week.

These correlations are exploratory associations. They do not establish that
conflict events caused a market movement. Procurement decisions, political
announcements and other market information can mediate or confound the
relationship.

## Added files

```text
src/services/lagged_conflict_market_analyzer.py
src/analyze_black_doves_lags.py
tests/test_lagged_conflict_market_analyzer.py
BLACK_DOVES_LAG_ANALYSIS_README.md
```

## Install and test

Extract the ZIP directly into the `conflict_market_analysis` project root.

```powershell
.\.venv\Scripts\python.exe -m compileall -q src tests

.\.venv\Scripts\python.exe -m unittest discover `
    -s tests `
    -p "test_lagged_conflict_market_analyzer.py" `
    -v

.\.venv\Scripts\python.exe -m unittest discover `
    -s tests `
    -p "test_*.py"
```

_Linux/macOS equivalent (after `source .venv/bin/activate`):_

```bash
.venv/bin/python -m compileall -q src tests

.venv/bin/python -m unittest discover \
    -s tests \
    -p "test_lagged_conflict_market_analyzer.py" \
    -v

.venv/bin/python -m unittest discover \
    -s tests \
    -p "test_*.py"
```

This extension adds eight tests. Starting from the user's confirmed 153 tests,
the expected full-suite result is 161 tests.

## Run the analysis

```powershell
.\.venv\Scripts\python.exe -m src.analyze_black_doves_lags `
    ".\data\analysis\black_doves_country_week.csv" `
    ".\data\analysis\black_doves_lag_analysis.csv"
```

_Linux/macOS equivalent (after `source .venv/bin/activate`):_

```bash
.venv/bin/python -m src.analyze_black_doves_lags \
    "./data/analysis/black_doves_country_week.csv" \
    "./data/analysis/black_doves_lag_analysis.csv"
```

With the current Iran and Israel data, the expected structure is:

- 172 input country-week rows;
- 86 distinct weeks;
- three scopes: Iran, Israel and both countries combined;
- two default conflict metrics;
- four default lags;
- 24 association rows.

The defaults are:

```text
metrics: strike_events, strike_fatalities
lags:    0, 1, 2, 4 weeks
```

Additional metrics or a custom lag selection can be requested explicitly:

```powershell
.\.venv\Scripts\python.exe -m src.analyze_black_doves_lags `
    ".\data\analysis\black_doves_country_week.csv" `
    ".\data\analysis\black_doves_lag_analysis.csv" `
    --metric strike_events `
    --metric strike_fatalities `
    --metric total_fatalities `
    --lag 0 `
    --lag 1 `
    --lag 2 `
    --lag 4
```

_Linux/macOS equivalent (after `source .venv/bin/activate`):_

```bash
.venv/bin/python -m src.analyze_black_doves_lags \
    "./data/analysis/black_doves_country_week.csv" \
    "./data/analysis/black_doves_lag_analysis.csv" \
    --metric strike_events \
    --metric strike_fatalities \
    --metric total_fatalities \
    --lag 0 \
    --lag 1 \
    --lag 2 \
    --lag 4
```

## Inspect the strongest exploratory results

```powershell
Import-Csv ".\data\analysis\black_doves_lag_analysis.csv" |
    Where-Object status -eq "ok" |
    Sort-Object {
        [math]::Abs(
            [double]$_.spearman_correlation
        )
    } -Descending |
    Select-Object -First 12 `
        scope_name, `
        conflict_metric, `
        lag_weeks, `
        observations, `
        pearson_correlation, `
        spearman_correlation |
    Format-Table -AutoSize
```

Positive coefficients mean that higher conflict values tend to accompany
higher later abnormal returns. Negative coefficients mean that higher conflict
values tend to accompany lower later abnormal returns. Magnitude alone is not
evidence of causality or statistical significance.
