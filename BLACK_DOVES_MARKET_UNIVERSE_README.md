# BLACK DOVES: market-data universe

This extension downloads market data for the complete verified 46-company
universe and the 15 distinct local-market benchmarks in the Company Master.

## Scientific boundary

- The eight pre-specified companies remain the confirmatory sample.
- The other 37 companies are an exploratory universe.
- Volkswagen remains a separate post-hoc exploratory robustness case.
- Download availability does not determine analytical inclusion.
- Failed, partial and shorter histories remain visible in the audit report.
- Company returns are compared with their configured local-market benchmark.
- The download window extends beyond 2026-08-18 only to calculate the approved
  post-event window; later observations do not change event eligibility.

## Files

```text
config/company_market_universe.csv
src/models/market_universe_entry.py
src/data_access/company_market_universe.py
src/services/market_universe_collector.py
src/download_company_market_universe.py
src/services/market_universe_processor.py
src/process_company_market_universe.py
tests/test_company_market_universe.py
tests/test_market_universe_collector.py
tests/test_market_universe_processor.py
```

`src/data_access/market_reader.py` is updated to use atomic writes and one
consistent safe-filename rule.

## Test a small selection first

The downloader automatically includes the required benchmark and writes an
audit report. Existing files are skipped, so interrupted runs can resume.

```powershell
.\.venv\Scripts\python.exe -m src.download_company_market_universe `
    --company-id CMP035 `
    --company-id CMP027 `
    --request-delay 1
```

_Linux/macOS equivalent (after `source .venv/bin/activate`):_

```bash
.venv/bin/python -m src.download_company_market_universe \
    --company-id CMP035 \
    --company-id CMP027 \
    --request-delay 1
```

Expected instruments: two companies plus their two different benchmarks.

## Download the eight pre-specified companies

```powershell
.\.venv\Scripts\python.exe -m src.download_company_market_universe `
    --only-confirmatory `
    --request-delay 1
```

_Linux/macOS equivalent (after `source .venv/bin/activate`):_

```bash
.venv/bin/python -m src.download_company_market_universe \
    --only-confirmatory \
    --request-delay 1
```

## Download the full universe

```powershell
.\.venv\Scripts\python.exe -m src.download_company_market_universe `
    --request-delay 1
```

_Linux/macOS equivalent (after `source .venv/bin/activate`):_

```bash
.venv/bin/python -m src.download_company_market_universe \
    --request-delay 1
```

Default period:

- start: `2023-01-01` inclusive;
- end: `2026-09-03` exclusive.

The start provides market history before the announcement collection envelope.
The end covers the `+10` trading-day window for events first published through
2026-08-18.

## Resume, refresh and failures

- Run the same command again to skip valid files that already exist.
- Add `--refresh` only when existing raw files should be replaced.
- A partial provider failure does not discard successful downloads.
- Retries use a short backoff to reduce immediate repeat rate-limit failures.
- Exit code `2` means at least one instrument failed; inspect
  `data/processed/market/market_download_report.csv`.
- Failed tickers are not silently removed from the research population.

The full universe represents 61 provider instruments at most: 46 companies
plus 15 deduplicated benchmarks.

## Create the analysis-ready return panel

After the downloads, run:

```powershell
.\.venv\Scripts\python.exe -m src.process_company_market_universe
```

_Linux/macOS equivalent (after `source .venv/bin/activate`):_

```bash
.venv/bin/python -m src.process_company_market_universe
```

This creates:

- one company-versus-benchmark CSV per available company;
- `data/processed/market/company_benchmark_returns.csv` as a combined
  long-form panel;
- `data/processed/market/market_processing_report.csv` with one status row
  for each of the 46 companies.

The combined panel retains company ID, ticker, benchmark, trading currency,
exchange, analytical tier, role category and the pre-specified-sample flag.
Missing raw files and processing errors remain visible in the report.

## Provider-symbol fallbacks

- Equinor uses `OBX.OL`, the Yahoo Finance symbol for the OBX total-return
  index. The originally configured `^OBX` symbol did not return observations.
- CATL uses `000300.SS` (CSI 300) as a broad Chinese-market proxy because the
  more specific ChiNext symbol `399006.SZ` returned no historical observations
  through the selected provider after repeated, delayed retries.
- The CSI 300 is a documented data-availability proxy, not an identical
  substitute for ChiNext. This limitation must remain visible when CATL's
  abnormal returns are interpreted.
