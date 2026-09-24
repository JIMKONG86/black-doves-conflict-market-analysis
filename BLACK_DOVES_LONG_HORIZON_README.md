# BLACK DOVES long-horizon market-position analysis

This package adds a descriptive analysis of the complete period from
1 January through 18 August 2026. It does not replace the short event window
from trading day -5 through +10. The two views answer different questions:

- the short event study examines the immediate market reaction;
- the long-horizon analysis describes how relative performance developed over
  the complete research period.

The long-horizon result must not be interpreted as a causal conflict effect,
because later news and company-specific developments can also affect prices.

## Install

Run from the project root in PowerShell:

```powershell
$package = Get-ChildItem "$env:USERPROFILE\Downloads" `
    -Filter "black_doves_long_horizon_market_position_v5.zip" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

Expand-Archive `
    -LiteralPath $package.FullName `
    -DestinationPath . `
    -Force
```

## Test

```powershell
.\.venv\Scripts\python.exe -m unittest `
    tests.test_market_position_analysis `
    tests.test_market_position_visualization `
    -v
```

_Linux/macOS equivalent (after `source .venv/bin/activate`):_

```bash
.venv/bin/python -m unittest \
    tests.test_market_position_analysis \
    tests.test_market_position_visualization \
    -v
```

## Run the full-period analysis

The default dates match the approved research design:

```powershell
.\.venv\Scripts\python.exe -m src.analyze_market_position
```

_Linux/macOS equivalent (after `source .venv/bin/activate`):_

```bash
.venv/bin/python -m src.analyze_market_position
```

This creates:

- `data/analysis/market_position_full_period_detail.csv`
- `data/analysis/market_position_company_summary.csv`
- `data/analysis/market_position_sample_aar_caar.csv`
- `data/analysis/market_position_role_aar_caar.csv`

Dates can be changed explicitly if required:

```powershell
.\.venv\Scripts\python.exe -m src.analyze_market_position `
    --analysis-start 2026-01-01 `
    --analysis-end 2026-08-18
```

_Linux/macOS equivalent (after `source .venv/bin/activate`):_

```bash
.venv/bin/python -m src.analyze_market_position \
    --analysis-start 2026-01-01 \
    --analysis-end 2026-08-18
```

## Create and open the dashboard

```powershell
.\.venv\Scripts\python.exe -m src.visualize_market_position_analysis

Invoke-Item .\output\black_doves_long_horizon_market_position.html
```

_Linux/macOS equivalent (after `source .venv/bin/activate`):_

```bash
.venv/bin/python -m src.visualize_market_position_analysis

xdg-open ./output/black_doves_long_horizon_market_position.html
# macOS: use 'open' instead of 'xdg-open'
```

The dashboard contains:

1. post-event CAAR across the complete period for all three sample groups;
   the lower x-axis shows relative trading days and a second line shows the
   corresponding calendar month and year;
2. a pre/post percentile map for all companies;
3. the exact company rank changes;
4. a full post-event CAR ranking;
5. long-horizon CAR paths for the confirmatory sample and Volkswagen.

The dashboard also includes a compact interpretation guide defining the three
sample classifications, AR, CAR, AAR, CAAR, benchmark proxies, the dual time
scale, capital-market positioning, and the causal limitation of the results.
The guide is placed below the interactive diagram area so that the data remain
the primary visual focus.

## Interactive filters and mobile use

The dashboard provides three combinable client-side filters:

- sample classification;
- company role;
- individual company.

The filters update every tab without a Python server. CAAR is recalculated from
the matching company observations. Existing company ranks, percentiles, and
quartiles remain based on the complete 46-company universe so filtering cannot
silently redefine the comparison population.

For narrow screens, the generated document now includes an explicit mobile
viewport, prevents horizontal page overflow, moves chart toolbars below the
plots, reduces chart heights, and reacts to screen rotation or resizing. The
controls are stacked vertically, company axes use compact ticker symbols, and
the multi-company legend is placed below the chart. Selecting one company gives
the clearest detailed mobile view. Bars and points retain the full company names
and exact values in their tap or hover information.

The generated dashboard embeds Bokeh's JavaScript resources directly. It does
not depend on loading the Bokeh CDN when the HTML file is opened on a phone or
shared to another device.

## Sample classifications

- `Confirmatory`: the eight companies selected before the results were
  evaluated; this is the pre-specified primary sample.
- `Exploratory`: 37 additional companies used to identify broader patterns;
  the resulting findings are hypothesis-generating rather than independent
  confirmation.
- `Post-hoc exploratory`: Volkswagen was added after an interesting signal was
  observed and is therefore reported separately because selection bias is
  possible.

## Return measures

- `AR`: daily company return minus the configured benchmark return. A positive
  value means relative outperformance and does not necessarily mean that the
  share price itself increased.
- `CAR`: arithmetic sum of one company's daily abnormal returns over the stated
  period.
- `AAR`: group-average abnormal return on one relative trading day.
- `CAAR`: cumulative sum of the group's AAR values from the event onward.
- `Benchmark`: configured local-market index used to remove broad market
  movements. A disclosed proxy is used only when the intended index is not
  available from the provider.

Relative trading day 0 is each company's first tradable day after the event.
The second x-axis maps relative trading days to calendar months using the
median actual market date across the sample, which accommodates differences in
trading calendars.

## Meaning of capital-market position

`Capital-market position` is deliberately narrower than economic market
position. It describes only the relative position of a company within the
46-company project sample.

The ranking variable is mean daily abnormal return:

```text
mean(company daily return - configured benchmark daily return)
```

This daily mean makes the pre- and post-event phases comparable even though
they contain different numbers of trading days.

- `pre_rank` and `post_rank`: rank 1 is the strongest relative performance;
- `rank_change`: positive values mean that the company moved upward;
- `pre_percentile` and `post_percentile`: normalized position from 0 to 100%;
- `position_shift`: improved, unchanged, or weakened based on an actual
  quartile change;
- `pre_car` and `post_car`: cumulative arithmetic abnormal return in each
  phase;
- `*_company_total_return` and `*_benchmark_total_return`: geometrically
  compounded observed returns for contextual interpretation.

These variables support statements about relative stock-market positioning.
They do not measure product-market share, revenue share, order-book share, or
competitive power in the underlying industries.
