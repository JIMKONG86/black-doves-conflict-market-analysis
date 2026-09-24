# BLACK DOVES AAR/CAAR visualization

This extension aggregates the five procurement event windows and adds two
visual outputs:

1. a dedicated event-study chart with average abnormal return (AAR), cumulative
   average abnormal return (CAAR), and all five individual CAR paths;
2. procurement announcement markers in the existing BLACK DOVES market and
   conflict dashboard.

## Measures

- **AAR** is the arithmetic mean of all event-specific abnormal returns on the
  same relative trading day.
- **CAAR** is the cross-event mean cumulative abnormal return measured from the
  beginning of the selected event window.
- **Positive event share** is the proportion of events with an abnormal return
  greater than zero on a relative trading day.
- Standard deviations and standard errors are exported for transparency, but
  the chart remains descriptive because the event sample contains only five
  observations.

All events must have the same complete event-time window and exactly one row per
event and relative trading day. Invalid dates, duplicate event-days, non-finite
returns and changing event metadata are rejected.

## Included files

- `src/services/procurement_event_aggregate.py`
- `src/visualize_procurement_event_study.py`
- updated `src/black_doves_visualization.py`
- `tests/test_procurement_event_aggregate.py`
- `tests/test_black_doves_procurement_markers.py`
- `tests/test_procurement_event_visualization.py`

## Install and test

Run from the project root in PowerShell. Paste only the commands inside the
code blocks.

```powershell
Expand-Archive `
    -LiteralPath ".\black_doves_aar_caar_visualization_v2.zip" `
    -DestinationPath "." `
    -Force

.\.venv\Scripts\python.exe -m compileall -q src tests

.\.venv\Scripts\python.exe -m unittest discover `
    -s tests `
    -p "test_procurement_event_aggregate.py" `
    -v

.\.venv\Scripts\python.exe -m unittest discover `
    -s tests `
    -p "test_black_doves_procurement_markers.py" `
    -v

.\.venv\Scripts\python.exe -m unittest discover `
    -s tests `
    -p "test_procurement_event_visualization.py" `
    -v

.\.venv\Scripts\python.exe -m unittest discover `
    -s tests `
    -p "test_*.py"
```

_Linux/macOS equivalent (after `source .venv/bin/activate`):_

```bash
unzip -o "black_doves_aar_caar_visualization_v2.zip" -d .

.venv/bin/python -m compileall -q src tests

.venv/bin/python -m unittest discover \
    -s tests \
    -p "test_procurement_event_aggregate.py" \
    -v

.venv/bin/python -m unittest discover \
    -s tests \
    -p "test_black_doves_procurement_markers.py" \
    -v

.venv/bin/python -m unittest discover \
    -s tests \
    -p "test_procurement_event_visualization.py" \
    -v

.venv/bin/python -m unittest discover \
    -s tests \
    -p "test_*.py"
```

The extension adds 13 tests. Based on the current baseline of 182 tests, the
merged full suite should report 195 tests.

## Create the event-study visualization

```powershell
.\.venv\Scripts\python.exe `
    -m src.visualize_procurement_event_study `
    ".\data\analysis\rheinmetall_procurement_event_window.csv" `
    ".\data\analysis\rheinmetall_procurement_event_aggregate.csv" `
    ".\output\black_doves_procurement_event_study.html" `
    --logo ".\assets\black_doves_logo.png"

Start-Process `
    ".\output\black_doves_procurement_event_study.html"
```

_Linux/macOS equivalent (after `source .venv/bin/activate`):_

```bash
.venv/bin/python \
    -m src.visualize_procurement_event_study \
    "./data/analysis/rheinmetall_procurement_event_window.csv" \
    "./data/analysis/rheinmetall_procurement_event_aggregate.csv" \
    "./output/black_doves_procurement_event_study.html" \
    --logo "./assets/black_doves_logo.png"

Start-Process \
    "./output/black_doves_procurement_event_study.html"
```

The first panel displays AAR by relative trading day. The second panel displays
the five individual CAR paths and the thicker aggregate CAAR line. Day zero is
marked by a vertical dashed reference line. The clickable procurement legend
is positioned to the right of the second plot so it does not cover any event
paths.

## Add procurement markers to the existing dashboard

```powershell
.\.venv\Scripts\python.exe `
    -m src.black_doves_visualization `
    ".\data\analysis\black_doves_country_week.csv" `
    ".\output\black_doves_market_conflict.html" `
    --logo ".\assets\black_doves_logo.png" `
    --procurement-events `
    ".\data\analysis\rheinmetall_procurement_event_summary.csv"

Start-Process ".\output\black_doves_market_conflict.html"
```

_Linux/macOS equivalent (after `source .venv/bin/activate`):_

```bash
.venv/bin/python \
    -m src.black_doves_visualization \
    "./data/analysis/black_doves_country_week.csv" \
    "./output/black_doves_market_conflict.html" \
    --logo "./assets/black_doves_logo.png" \
    --procurement-events \
    "./data/analysis/rheinmetall_procurement_event_summary.csv"

Start-Process "./output/black_doves_market_conflict.html"
```

Red diamond markers indicate procurement announcement dates on the cumulative
market-return panel. Hovering over a marker shows the buyer, system, title and
event-day abnormal return. The existing dashboard remains backward-compatible:
omitting `--procurement-events` produces the original view.

## Interpretation boundary

The combined chart makes timing and heterogeneity visible, but it does not turn
the five observations into causal evidence. AAR and CAAR should be described as
exploratory descriptive statistics. Concurrent company news, publication time,
market expectations and broader defence-policy announcements remain potential
confounders.
