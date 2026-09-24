# BLACK DOVES market-universe visualization

This package adds an interactive Bokeh dashboard for the complete company
market-universe event study. It reads the existing analysis CSV files and does
not modify them.

## Install

From the project root in PowerShell, expand the ZIP into the current folder:

```powershell
$package = Get-ChildItem "$env:USERPROFILE\Downloads" `
    -Filter "black_doves_market_universe_visualization_v1.zip" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

Expand-Archive `
    -LiteralPath $package.FullName `
    -DestinationPath . `
    -Force
```

## Test

Run the new visualization tests:

```powershell
.\.venv\Scripts\python.exe -m unittest `
    tests.test_market_universe_event_study_visualization `
    -v
```

_Linux/macOS equivalent (after `source .venv/bin/activate`):_

```bash
.venv/bin/python -m unittest \
    tests.test_market_universe_event_study_visualization \
    -v
```

Run the complete test suite:

```powershell
.\.venv\Scripts\python.exe -m unittest discover `
    -s tests `
    -p "test_*.py"
```

_Linux/macOS equivalent (after `source .venv/bin/activate`):_

```bash
.venv/bin/python -m unittest discover \
    -s tests \
    -p "test_*.py"
```

## Create and open the dashboard

The default command uses the three CSV files already written by
`src.analyze_market_universe_event_study`:

```powershell
.\.venv\Scripts\python.exe -m src.visualize_market_universe_event_study
```

_Linux/macOS equivalent (after `source .venv/bin/activate`):_

```bash
.venv/bin/python -m src.visualize_market_universe_event_study
```

Open the generated standalone HTML file:

```powershell
Invoke-Item .\output\black_doves_market_universe_event_study.html
```

The dashboard contains four tabs:

1. sample-level AAR and CAAR for confirmatory, exploratory, and post-hoc groups;
2. CAR `[0,+10]` ranking for all companies;
3. mean CAR `[0,+10]` by company role;
4. post-event CAR paths for the confirmatory sample and Volkswagen.

Hover over a point or bar for exact values. Click a legend entry to hide or
show a series. The results are descriptive and do not establish causality.

## Optional arguments

Use `--event-id` if the input files contain more than one event. All paths can
also be changed explicitly:

```powershell
.\.venv\Scripts\python.exe -m src.visualize_market_universe_event_study `
    --detail-file .\data\analysis\market_universe_event_window.csv `
    --company-summary-file .\data\analysis\market_universe_company_summary.csv `
    --sample-summary-file .\data\analysis\market_universe_sample_aar_caar.csv `
    --output-file .\output\black_doves_market_universe_event_study.html
```

_Linux/macOS equivalent (after `source .venv/bin/activate`):_

```bash
.venv/bin/python -m src.visualize_market_universe_event_study \
    --detail-file ./data/analysis/market_universe_event_window.csv \
    --company-summary-file ./data/analysis/market_universe_company_summary.csv \
    --sample-summary-file ./data/analysis/market_universe_sample_aar_caar.csv \
    --output-file ./output/black_doves_market_universe_event_study.html
```
