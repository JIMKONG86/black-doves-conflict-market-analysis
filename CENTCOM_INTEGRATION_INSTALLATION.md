# CENTCOM integration – installation

This archive contains only the files added or changed for the CENTCOM
integration. It is not a complete project copy.

## Install on Windows

1. Extract this archive into a temporary folder.
2. Open the existing `conflict_market_analysis` project folder.
3. Copy every file and folder from the extracted archive into that project
   folder.
4. Confirm **Replace the files in the destination** when Windows asks.

The archive paths already match the project layout (`config`, `data`, `src`,
and `tests`). No long raw-data paths are included.

## Included behavior

- official CENTCOM public-release source configuration and HTML parsing;
- reviewed U.S. strike-operation-day data;
- validated CENTCOM importer and command-line entry point;
- U.S.-initiator panel in the fuel-price lag visualization;
- documentation and focused tests.

## Verify

From the project root, run:

```powershell
python -m unittest discover -s tests
```

See `BLACK_DOVES_CENTCOM_STRIKES_README.md` for methodology and usage.
