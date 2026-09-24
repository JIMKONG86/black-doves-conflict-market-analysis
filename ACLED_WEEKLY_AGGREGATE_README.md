# ACLED weekly aggregate import

This package adds a separate import path for ACLED's weekly aggregated
Middle East workbook. It does not change the existing event-level
`ClaimObservation` and `StrikeObservation` import path.

## Files

- `src/models/weekly_conflict_aggregate.py`
- `src/data_access/acled_weekly_aggregate_importer.py`
- `src/data_access/weekly_conflict_aggregate_repository.py`
- `src/import_acled_weekly_aggregates.py`
- `tests/test_weekly_conflict_aggregate.py`
- `tests/test_acled_weekly_aggregate_importer.py`
- `tests/test_weekly_conflict_aggregate_repository.py`
- `tests/test_import_acled_weekly_aggregates.py`

## Prepare the ACLED file

Open `Middle-East_aggregated_data_up_to_week_of-2026-08-22.xlsx` in Excel
and save it as a UTF-8 CSV, for example:

```text
data/raw/acled/middle_east_weekly.csv
```

The importer accepts comma-, semicolon- and tab-separated files. It also
accepts the date formats `YYYY-MM-DD`, `DD.MM.YYYY`, `MM/DD/YYYY` and
localized values such as `31-August-2024`, `03-Mai-2025` or
`05-März-2016`.

## Run the new tests

```powershell
.\.venv\Scripts\python.exe -m compileall -q src tests

.\.venv\Scripts\python.exe -m unittest discover `
    -s tests `
    -p "test_weekly_conflict_aggregate.py" `
    -v

.\.venv\Scripts\python.exe -m unittest discover `
    -s tests `
    -p "test_acled_weekly_aggregate_importer.py" `
    -v

.\.venv\Scripts\python.exe -m unittest discover `
    -s tests `
    -p "test_weekly_conflict_aggregate_repository.py" `
    -v

.\.venv\Scripts\python.exe -m unittest discover `
    -s tests `
    -p "test_import_acled_weekly_aggregates.py" `
    -v
```

_Linux/macOS equivalent (after `source .venv/bin/activate`):_

```bash
.venv/bin/python -m compileall -q src tests

.venv/bin/python -m unittest discover \
    -s tests \
    -p "test_weekly_conflict_aggregate.py" \
    -v

.venv/bin/python -m unittest discover \
    -s tests \
    -p "test_acled_weekly_aggregate_importer.py" \
    -v

.venv/bin/python -m unittest discover \
    -s tests \
    -p "test_weekly_conflict_aggregate_repository.py" \
    -v

.venv/bin/python -m unittest discover \
    -s tests \
    -p "test_import_acled_weekly_aggregates.py" \
    -v
```

Then run the complete project tests:

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

## Verified full-file result

The importer was tested against the complete 152,366-row Middle East
dataset with the country filter `("Iran", "Israel")`:

- 19,954 selected aggregate rows
- 19,954 saved on the first import
- zero failed rows
- 19,954 duplicates and zero new saves on the second import
- Iran: 14,081 aggregate rows, 42,882 events, 33,785 fatalities
- Israel: 5,873 aggregate rows, 21,293 events, 2,119 fatalities

The repository writes one atomic JSON file per country and source
snapshot. The full validation produced:

- `IR_2026-08-22.json`: 14,081 aggregates
- `IL_2026-08-22.json`: 5,873 aggregates
- 19,954 successfully deserialized aggregates
- 19,954 unique and verified aggregate identifiers

## Import Iran and Israel

```powershell
.\.venv\Scripts\python.exe -m src.import_acled_weekly_aggregates `
    ".\data\raw\acled\middle_east_weekly.csv" `
    --reviewed-by "Markus" `
    --source-url "https://acleddata.com/" `
    --snapshot-date 2026-08-22 `
    --country Iran `
    --country Israel `
    --aggregate-directory `
        ".\data\validated\weekly_conflict_aggregates" `
    --strict
```

_Linux/macOS equivalent (after `source .venv/bin/activate`):_

```bash
.venv/bin/python -m src.import_acled_weekly_aggregates \
    "./data/raw/acled/middle_east_weekly.csv" \
    --reviewed-by "Markus" \
    --source-url "https://acleddata.com/" \
    --snapshot-date 2026-08-22 \
    --country Iran \
    --country Israel \
    --aggregate-directory \
        "./data/validated/weekly_conflict_aggregates" \
    --strict
```

The normal research import deliberately keeps every event category for
the selected countries. This preserves protests and other possible
control variables. Add `--strike-only` only for a separate,
strike-specific extract.
