# BLACK DOVES Brent-to-fuel transmission analysis

This module compares official Brent spot prices with weekly German petrol and
diesel prices and estimates exploratory transmission lags from zero through
eight weeks.

## Sources and units

- Brent: U.S. Energy Information Administration, Europe Brent Spot Price FOB,
  daily, USD per barrel.
- German petrol and diesel: European Commission Weekly Oil Bulletin, weekly
  Monday observations, EUR per 1,000 litres in the source workbook.
- The processor converts German prices to EUR per litre and retains both prices
  including taxes and prices excluding taxes.
- The German methodological note identifies petrol as Euro-Super 95 (E5) and
  diesel as B7.

Official source pages:

- <https://www.eia.gov/dnav/pet/hist/RBRTED.htm>
- <https://energy.ec.europa.eu/data-and-analysis/weekly-oil-bulletin_en>
- <https://energy.ec.europa.eu/document/download/6b94220a-8483-44cd-bd23-e699050e6047_en?filename=2018_germany_notes.pdf>

## Run the workflow

Download the source workbooks and create the aligned price files:

```powershell
.\.venv\Scripts\python.exe -m src.collect_energy_prices
```

_Linux/macOS equivalent (after `source .venv/bin/activate`):_

```bash
.venv/bin/python -m src.collect_energy_prices
```

Existing raw source workbooks are retained. Use `--refresh` only when a new
official snapshot is intentionally required.

Estimate lags from zero through eight weeks:

```powershell
.\.venv\Scripts\python.exe -m src.analyze_fuel_price_lags
```

_Linux/macOS equivalent (after `source .venv/bin/activate`):_

```bash
.venv/bin/python -m src.analyze_fuel_price_lags
```

Create and open the self-contained dashboard:

```powershell
.\.venv\Scripts\python.exe -m src.visualize_fuel_price_lags

Invoke-Item .\output\black_doves_energy_price_lag.html
```

_Linux/macOS equivalent (after `source .venv/bin/activate`):_

```bash
.venv/bin/python -m src.visualize_fuel_price_lags

xdg-open ./output/black_doves_energy_price_lag.html
# macOS: use 'open' instead of 'xdg-open'
```

The dashboard also reads `data/analysis/weekly_conflict_features.csv` and
`data/validated/centcom_us_strike_operation_days.csv` and adds a `Strikes`
tab. The first aligned panel shows ACLED metrics for Iran and Israel as
affected countries. The second shows the United States as initiator using
officially confirmed CENTCOM strike-operation days. Its role/series filter
switches between the affected-country and initiator views. The metric filter
provides total strikes, strike fatalities and the separate air/drone and
shelling/artillery/missile components for ACLED only.

The `EUR/L` tab shows the absolute German consumer-price levels. The `Index`
tab separately compares relative development with each series rebased to 100.
Consequently, an untaxed series may have the higher index because it increased
more strongly from a lower baseline, even though its absolute EUR-per-litre
price remains below the taxed series. The dashboard validates this ordering
for every weekly observation before it is written.

## Outputs

- `data/processed/energy/energy_price_timeline.csv`: daily Brent and weekly
  German fuel prices in original units plus an index with the first selected
  observation equal to 100.
- `data/processed/energy/energy_price_weekly_panel.csv`: weekly aligned prices
  and week-over-week percentage changes.
- `data/analysis/fuel_price_lag_results.csv`: Pearson and Spearman correlations,
  p-values, observation counts and date coverage for every product, tax basis
  and lag.
- `output/black_doves_energy_price_lag.html`: responsive interactive dashboard
  with separate absolute-price and relative-index views.
- `data/validated/centcom_us_strike_operation_days.csv`: reviewed official
  CENTCOM operation-day evidence, including initiator and affected-country
  roles, exact source URLs and core-scope decisions.

## Lag definition

To avoid look-ahead bias, each German Monday price is paired with the mean
Brent price from the immediately preceding Monday-to-Friday trading week.

- `lag 0`: the preceding-week Brent change versus the change in the immediately
  following German Monday price;
- `lag 1`: the same Brent change versus the German fuel-price change one week
  later;
- `lag 8`: the same comparison eight weeks later.

The correlations use weekly percentage changes rather than price levels. This
reduces the risk of a spurious relationship caused only by two trending price
series.

## Short interpretation guide

- **Indexed price**: a visual scale where each series begins at 100. It does not
  change the underlying price or unit.
- **Pearson correlation**: measures a linear association between the weekly
  changes.
- **Spearman correlation**: measures whether larger Brent changes tend to be
  associated with larger later fuel-price changes, without requiring a linear
  relationship.
- **Exploratory**: the lags are inspected after observing the data. The largest
  coefficient is a pattern to investigate, not a pre-specified confirmatory
  result.
- **p-value**: a descriptive uncertainty measure here. Because nine lags are
  tested for each series, unadjusted p-values must not be treated as standalone
  proof.
- **Temporal association**: one series changes before or alongside another. It
  does not by itself establish that the first change caused the second.
- **All strike events**: the sum of ACLED air/drone strikes and
  shelling/artillery/missile attacks. The total and its components are nested
  measures and must not be treated as independent evidence.
- **Strike fatalities**: fatalities attributed to those two ACLED strike
  categories in the weekly aggregate. They are reported aggregate counts, not
  independently re-verified individual cases.
- **U.S. strike-operation day**: one distinct calendar day for which an
  official CENTCOM full text confirms an executed U.S. strike. This is not a
  count of targets, munitions, sorties, waves or releases and must not be added
  to ACLED event counts.

The conflict date is a reference marker. Exchange rates, refining and
distribution margins, inventories, demand, biofuel blending, taxes and policy
can all affect German pump prices. A causal conflict effect would require a
separate identification strategy and additional controls.
