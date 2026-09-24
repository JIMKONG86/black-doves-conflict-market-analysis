# BLACK DOVES procurement event study

This extension adds a source-audited `ProcurementEvent` model and an
exploratory, market-adjusted event-window analysis for Rheinmetall air-defence
orders. It is designed to test the procurement link in the proposed mechanism:

`conflict intensity -> perceived threat -> procurement -> market response`

## Included files

- `src/models/procurement_event.py`
- `src/data_access/procurement_event_reader.py`
- `src/services/procurement_event_study.py`
- `src/analyze_procurement_events.py`
- `data/reference/rheinmetall_air_defence_procurement_events.csv`
- `tests/test_procurement_event.py`
- `tests/test_procurement_event_study.py`

## Curated events

The reference CSV contains five Rheinmetall announcements inside the current
market-data period. Each row links to the original Rheinmetall press release.

| Announcement | Buyer | Systems | Value treatment |
| --- | --- | --- | --- |
| 2025-01-15 | Italy | Skynex | EUR 73m exact award; EUR 204m option excluded from awarded value |
| 2025-10-10 | Ukraine | Skyranger 35 on Leopard 1 | Exact amount not disclosed; three-digit million-euro range retained as text |
| 2025-12-12 | Netherlands | Skyranger 30 | Exact amount not disclosed; high three-digit million-euro range retained as text |
| 2026-06-02 | Romania | Skyranger plus a multi-domain package | EUR 5.7bn stored only as aggregate package value, not as air-defence value |
| 2026-07-02 | Undisclosed customer | Four Skynex systems | Exact amount not disclosed; several hundred million euros retained as text |

The inclusion rule is deliberately narrow: a public announcement of a confirmed
order or contract during the market period. Prototype handovers, later delivery
updates and repeated detail releases are excluded to avoid double counting.

`primary_source_confirmed` means that the announcement and stated order terms
were checked against the issuer's original release. It does not mean that an
independent source has confirmed the market effect or the proposed causal chain.

## Method

The analyzer reads the existing daily market-comparison CSV and uses its
market-adjusted abnormal return:

`abnormal_return = company_return - benchmark_return`

For each procurement announcement it:

1. maps the announcement to the first available trading day on or after the
   announcement date;
2. extracts a default window of five trading days before through ten trading
   days after the event;
3. exports one detailed row per event and relative trading day;
4. calculates pre-event CAR, event-day abnormal return, CAR `[0,+1]`,
   CAR `[0,+5]`, CAR `[0,+10]` and full-window CAR.

CAR is the arithmetic sum of the daily market-adjusted abnormal returns in the
specified window.

This is an exploratory event-window analysis, not yet a full inferential event
study. The current version does not estimate alpha or beta in a separate
estimation window, calculate statistical significance, control for concurrent
news, or infer causality. Exact publication times are not available in the
reference file, so same-day versus next-day alignment remains a sensitivity
check for the written assignment.

## Install and test in PowerShell

Run these commands from the project root. Paste only the commands, not the
Markdown fence markers.

```powershell
Expand-Archive -LiteralPath ".\black_doves_procurement_event_study_v1.zip" `
    -DestinationPath "." `
    -Force

.\.venv\Scripts\python.exe -m compileall -q src tests

.\.venv\Scripts\python.exe -m unittest discover `
    -s tests `
    -p "test_procurement_event*.py" `
    -v

.\.venv\Scripts\python.exe -m unittest discover `
    -s tests `
    -p "test_*.py"
```

_Linux/macOS equivalent (after `source .venv/bin/activate`):_

```bash
unzip -o "black_doves_procurement_event_study_v1.zip" -d .

.venv/bin/python -m compileall -q src tests

.venv/bin/python -m unittest discover \
    -s tests \
    -p "test_procurement_event*.py" \
    -v

.venv/bin/python -m unittest discover \
    -s tests \
    -p "test_*.py"
```

The targeted run adds 21 tests. Based on the current 161-test baseline, the
merged full suite should report 182 tests.

## Run the analysis

```powershell
.\.venv\Scripts\python.exe -m src.analyze_procurement_events `
    ".\data\reference\rheinmetall_air_defence_procurement_events.csv" `
    ".\data\processed\market\RHM_DE_vs_GDAXI.csv" `
    ".\data\analysis\rheinmetall_procurement_event_window.csv" `
    ".\data\analysis\rheinmetall_procurement_event_summary.csv" `
    --pre-days 5 `
    --post-days 10
```

_Linux/macOS equivalent (after `source .venv/bin/activate`):_

```bash
.venv/bin/python -m src.analyze_procurement_events \
    "./data/reference/rheinmetall_air_defence_procurement_events.csv" \
    "./data/processed/market/RHM_DE_vs_GDAXI.csv" \
    "./data/analysis/rheinmetall_procurement_event_window.csv" \
    "./data/analysis/rheinmetall_procurement_event_summary.csv" \
    --pre-days 5 \
    --post-days 10
```

Inspect the compact event-level result:

```powershell
Import-Csv ".\data\analysis\rheinmetall_procurement_event_summary.csv" |
    Select-Object `
        announcement_date, `
        buyer_name, `
        systems, `
        event_day_abnormal_return, `
        post_event_car_0_1, `
        post_event_car_0_5, `
        post_event_car_0_10 |
    Format-Table -AutoSize
```

## Interpretation rule

Positive post-event CAR means Rheinmetall outperformed the DAX over that event
window; negative CAR means it underperformed. With only five selected events,
the results should be described as case-based exploratory evidence. They should
not be generalized into a stable procurement effect without a larger event set,
an estimation model and robustness checks.
