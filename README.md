# BLACK DOVES: data and Python implementation

This package accompanies the written assignment:

> *Tracing the Economic Effects of the 2026 Israel-Iran-United States
> Conflict: An Object-Oriented Python Framework Linking State Roles,
> Sectoral Returns, Oil Prices, and Consumer Costs*

Package freeze: **24 September 2026**
Core study window: **1 January-18 August 2026**
Primary event date: **28 February 2026**

The project connects conflict, policy, procurement, media, company-market,
oil-price and German fuel-price observations. It covers 46 companies. The
original 45-company universe is retained, while Volkswagen (`CMP046`) is
marked as a post-hoc exploratory robustness case.

This public repository contains the complete Python implementation, automated
tests, configuration, documentation and the fixed analytical inputs required
to inspect and reproduce the submitted results. The licensed original ACLED
weekly export and the large generated HTML files are intentionally not
published here. Their treatment is documented in `DATA_AVAILABILITY.md`.

Repository: https://github.com/JIMKONG86/black-doves-conflict-market-analysis

## Quick start

Python 3.12 or newer is recommended. The package deliberately does not contain
a virtual environment.

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m unittest discover -s tests
python -m src.build_black_doves_master
```

### Linux or macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m unittest discover -s tests
python -m src.build_black_doves_master
```

The last command rebuilds the consolidated offline dashboard at:

`output/black_doves_complete_analysis.html`

The regression suite was executed on 24 September 2026 with Python 3.12.14:
**361 tests passed**. Expected log messages in negative-path tests describe
simulated network or source failures; they are not test failures.

## Package structure

| Path | Purpose |
| --- | --- |
| `src/` | Object-oriented domain models, importers, transformations, statistical analyses and visualisations |
| `tests/` | Offline regression and unit tests |
| `config/` | The 46-company market universe and auditable source registries |
| `data/raw/` | Redistributable source snapshots retained for auditability |
| `data/processed/` | Normalised and joined intermediate datasets |
| `data/validated/` | Versioned records that passed project-specific structural or review steps |
| `data/reference/` | Curated event, role, procurement and contextual reference tables |
| `data/analysis/` | Final analytical panels, event-window results and summaries |
| `output/` | Target directory for locally rebuilt HTML reports; generated files are not committed |
| `assets/` | BLACK DOVES logo files used by the reports |
| `acled_API/` | Optional ACLED acquisition client and preparation workflow |
| `appendix/` | Compact machine-readable supporting tables |

Import templates and unit-test fixtures support the software workflow and are
not treated as empirical evidence.

## Data purpose and provenance

The analysis uses documented real-world observations. The principal data
families are:

- daily company and benchmark market prices for the 46-company universe;
- ACLED weekly conflict observations and separately retained U.S. CENTCOM
  operation dates;
- official U.S. procurement transactions and selected official government or
  company announcements;
- EIA Brent prices and European Commission German petrol and diesel prices;
- curated country-role, company-event and media-source records with audit
  fields and source URLs.

The raw, processed and analytical layers are kept separate. This prevents a
downloaded observation from being silently replaced by a derived value and
makes the transformation path inspectable. Source-specific limitations and
commands are documented in the accompanying `*_README.md` files. Important
starting points are:

- `COUNTRY_SOURCE_INTEGRATION_README.md`
- `BLACK_DOVES_MARKET_UNIVERSE_README.md`
- `BLACK_DOVES_ENERGY_PRICE_LAG_README.md`
- `BLACK_DOVES_PROCUREMENT_EVENT_STUDY_README.md`
- `BLACK_DOVES_REPORT_VIEW_AUDIT.md`

The included fixed analytical inputs permit the principal report to be rebuilt
offline. Refreshing external sources is optional and may require network access
or source-specific credentials. See `DATA_AVAILABILITY.md` for the distinction
between the public repository and the frozen university submission package.

## Main analytical outputs

The consolidated dashboard embeds the following seven views:

1. Brent and German fuel-price transmission;
2. company-level market event study;
3. longer-horizon market positioning;
4. company and announcement explorer;
5. media-positioning pilot analysis;
6. casualty and damage context;
7. procurement event study.

Additional HTML reports are generated in `output/`. They are build artifacts and
are therefore not version-controlled; the authoritative implementation remains
the Python source plus the included analytical data.

## Credentials and security

No credentials, access tokens or local environment files are included. To use
the optional ACLED acquisition client, copy `acled_API/.env.example` to
`acled_API/.env` and insert credentials locally. Never commit or submit that
local file.

The live GDELT example in `examples/gdelt_live_demo.py` is intentionally kept
outside the regression suite because its result depends on an external service.

## Interpretation limits

- Abnormal returns and temporal overlaps are descriptive and do not prove
  causality, legal responsibility or a realised conflict-related profit.
- Company-event links require source, timing and confounder checks.
- Media-positioning results are based on a limited pilot corpus and must not be
  generalised to complete national media systems.
- Missing observations remain explicitly labelled rather than being converted
  to zero.
- Volkswagen remains a separately labelled post-hoc case and is not part of the
  original confirmatory sample.

## Optional source refresh

The package can be reviewed and rebuilt without credentials. Commands that
retrieve new observations are documented separately because they can change the
data freeze and therefore the reproduced results. If a refresh is performed,
record its retrieval date, source parameters and resulting file hashes before
comparing it with this submission package.
