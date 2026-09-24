# BLACK DOVES: analysis-ready ACLED country-week data

This extension converts the validated ACLED weekly aggregate repository into
one analysis row per source snapshot, country and week. It is intended as the
conflict-side input for the later market-data join.

## Methodological scope

The export contains transparent event and fatality counts rather than a
synthetic conflict-intensity score. It keeps different ACLED source snapshots
separate so that revised observations are not counted twice.

`POPULATION_EXPOSURE` is deliberately not summed. The value can occur on
multiple aggregate rows for the same administrative area and week; summing it
would therefore overstate the exposed population.

The two available strike categories remain separately visible:

- `Air/drone strike`
- `Shelling/artillery/missile attack`

The second ACLED category cannot be separated further without event-level
source data. It must not be interpreted as missile strikes alone.

## Added files

```text
src/models/weekly_conflict_feature.py
src/services/weekly_conflict_feature_builder.py
src/data_access/weekly_conflict_feature_exporter.py
src/export_weekly_conflict_features.py
tests/test_weekly_conflict_feature.py
tests/test_weekly_conflict_feature_builder.py
tests/test_weekly_conflict_feature_exporter.py
```

## Installation

Extract the ZIP directly into the project root
`conflict_market_analysis`. Existing files are not overwritten by this
extension.

Then run:

```powershell
.\.venv\Scripts\python.exe -m compileall -q src tests

.\.venv\Scripts\python.exe -m unittest discover `
    -s tests `
    -p "test_weekly_conflict_feature*.py" `
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
    -p "test_weekly_conflict_feature*.py" \
    -v

.venv/bin/python -m unittest discover \
    -s tests \
    -p "test_*.py"
```

## Create the analysis table

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

For the already imported Middle East source file, the expected result is:

```text
Country-week rows: 1112
Total events: 64175
Strike events: 10148
Total fatalities: 35904
```

Country-level reconciliation:

| Country | Source rows | Total events | Fatalities | Strike events | Strike fatalities |
|---|---:|---:|---:|---:|---:|
| Iran | 14,081 | 42,882 | 33,785 | 3,950 | 2,868 |
| Israel | 5,873 | 21,293 | 2,119 | 6,198 | 198 |

## Export grain and columns

Each CSV row represents one combination of:

```text
source_snapshot_date + week_end_date + country
```

The export includes:

- total events and fatalities;
- political-violence events and fatalities;
- total strike events and fatalities;
- separate air/drone and shelling/artillery/missile values;
- violence-against-civilians events and fatalities;
- protest, riot and strategic-development event counts;
- source-row and administrative-area counts for auditability;
- provenance, review metadata and a deterministic `feature_id`.

The intended market join key is initially `week_end_date`. Market values
should later be aligned using a documented trading-week rule rather than a
silent calendar-date merge.
