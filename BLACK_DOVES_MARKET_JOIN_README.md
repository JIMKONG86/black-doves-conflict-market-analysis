# BLACK DOVES: weekly market-conflict join

This extension connects the analysis-ready ACLED country-week data from the
first BLACK DOVES package to Rheinmetall and DAX market observations. It also
creates a standalone Bokeh visualization with the BLACK DOVES logo.

All files in this ZIP are new. The existing `market_reader.py`,
`market_analysis.py`, `visualization.py` and `main.py` remain unchanged.

## Methodological decisions

- ACLED observations use a Saturday `week_end_date`.
- Every trading day from Monday through Friday is assigned to the following
  Saturday.
- Holidays therefore use the latest trading day that is actually present.
- Company and benchmark weekly returns are geometrically compounded.
- Weekly abnormal return is the sum of the daily market-adjusted abnormal
  returns, consistent with the existing event-study calculation.
- The first shared company/benchmark trading date is retained as a visible
  `0%` baseline.
- Conflict rows outside the available market period are reported as unmatched
  rather than silently interpreted as zero.

## Added files

```text
assets/black_doves_logo.png
src/services/black_doves_market_processor.py
src/services/weekly_market_conflict_builder.py
src/prepare_black_doves_market_data.py
src/create_black_doves_analysis.py
src/black_doves_visualization.py
tests/test_black_doves_market_processor.py
tests/test_weekly_market_conflict_builder.py
tests/test_black_doves_visualization.py
```

## 1. Install and test

Extract the ZIP directly into the `conflict_market_analysis` project root.

```powershell
.\.venv\Scripts\python.exe -m compileall -q src tests

.\.venv\Scripts\python.exe -m unittest discover `
    -s tests `
    -p "test_black_doves_*.py" `
    -v

.\.venv\Scripts\python.exe -m unittest discover `
    -s tests `
    -p "test_weekly_market_conflict_builder.py" `
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
    -p "test_black_doves_*.py" \
    -v

.venv/bin/python -m unittest discover \
    -s tests \
    -p "test_weekly_market_conflict_builder.py" \
    -v

.venv/bin/python -m unittest discover \
    -s tests \
    -p "test_*.py"
```

The extension adds 16 tests. Starting from the previously confirmed 138 tests,
the expected full-suite result is 154 tests.

## 2. Download the extended market period

The existing `market_reader.py` should now use:

```python
start_date="2025-01-01"
end_date="2026-08-24"
```

The end date is exclusive. `2026-08-24` therefore includes the final trading
day before the ACLED week ending `2026-08-22`.

Run the existing reader:

```powershell
.\.venv\Scripts\python.exe -m src.data_access.market_reader
```

_Linux/macOS equivalent (after `source .venv/bin/activate`):_

```bash
.venv/bin/python -m src.data_access.market_reader
```

## 3. Create baseline-normalized market data

```powershell
.\.venv\Scripts\python.exe -m src.prepare_black_doves_market_data `
    ".\data\raw\market\RHM_DE.csv" `
    ".\data\raw\market\GDAXI.csv" `
    ".\data\processed\market\RHM_DE_vs_GDAXI.csv"
```

_Linux/macOS equivalent (after `source .venv/bin/activate`):_

```bash
.venv/bin/python -m src.prepare_black_doves_market_data \
    "./data/raw/market/RHM_DE.csv" \
    "./data/raw/market/GDAXI.csv" \
    "./data/processed/market/RHM_DE_vs_GDAXI.csv"
```

This step uses `Adj Close`, begins both cumulative series at zero and keeps the
existing daily abnormal-return definition.

## 4. Create or refresh the ACLED country-week table

```powershell
.\.venv\Scripts\python.exe -m src.export_weekly_conflict_features `
    ".\data\analysis\weekly_conflict_features.csv" `
    --aggregate-directory ".\data\validated\weekly_conflict_aggregates" `
    --snapshot-date 2026-08-22 `
    --country Iran `
    --country Israel
```

_Linux/macOS equivalent (after `source .venv/bin/activate`):_

```bash
.venv/bin/python -m src.export_weekly_conflict_features \
    "./data/analysis/weekly_conflict_features.csv" \
    --aggregate-directory "./data/validated/weekly_conflict_aggregates" \
    --snapshot-date 2026-08-22 \
    --country Iran \
    --country Israel
```

## 5. Join conflict and market observations

```powershell
.\.venv\Scripts\python.exe -m src.create_black_doves_analysis `
    ".\data\analysis\weekly_conflict_features.csv" `
    ".\data\processed\market\RHM_DE_vs_GDAXI.csv" `
    ".\data\analysis\black_doves_country_week.csv" `
    --snapshot-date 2026-08-22 `
    --country Iran `
    --country Israel
```

_Linux/macOS equivalent (after `source .venv/bin/activate`):_

```bash
.venv/bin/python -m src.create_black_doves_analysis \
    "./data/analysis/weekly_conflict_features.csv" \
    "./data/processed/market/RHM_DE_vs_GDAXI.csv" \
    "./data/analysis/black_doves_country_week.csv" \
    --snapshot-date 2026-08-22 \
    --country Iran \
    --country Israel
```

With complete market data from January 2025 through 21 August 2026, the
expected maximum overlap is 86 weeks and 172 country-week rows.

## 6. Create the branded visualization

```powershell
.\.venv\Scripts\python.exe -m src.black_doves_visualization `
    ".\data\analysis\black_doves_country_week.csv" `
    ".\output\black_doves_market_conflict.html" `
    --logo ".\assets\black_doves_logo.png"
```

_Linux/macOS equivalent (after `source .venv/bin/activate`):_

```bash
.venv/bin/python -m src.black_doves_visualization \
    "./data/analysis/black_doves_country_week.csv" \
    "./output/black_doves_market_conflict.html" \
    --logo "./assets/black_doves_logo.png"
```

Open the result:

```powershell
Start-Process ".\output\black_doves_market_conflict.html"
```

The HTML shows three synchronized panels without a potentially misleading
dual axis:

1. Rheinmetall versus DAX cumulative return;
2. weekly reported strike events for Iran and Israel;
3. weekly reported strike fatalities for Iran and Israel.

Legends are clickable, values have hover details and every panel shares the
same time range.
