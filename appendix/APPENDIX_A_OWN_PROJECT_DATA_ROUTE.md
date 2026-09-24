# Appendix A — Approved own-project data route

## Status

The professor confirmed that students who complete their own project do not
need to implement the separate programming task based on the faculty-supplied
training, ideal-function and test datasets. BLACK DOVES follows the approved
own-project route.

## Data purpose and structure

The project combines documented company classifications, daily company and
benchmark prices, conflict-related reference events, Brent crude prices,
German petrol and diesel prices, and country-role context. Raw source records,
processed analytical panels and derived results remain separated. Dataset
purpose, fields, periods, units, source status and exclusions are documented in
`DATA_PROVENANCE.md`, the SQLite manifest and the report.

## Python implementation

The submission includes the corresponding Python implementation for validated
data ingestion, object-oriented domain models, market-model and event-window
calculations, lag analysis, SQLAlchemy/SQLite persistence, Bokeh visualization
and deterministic tests. The empirical results do not use undisclosed or
unlabelled synthetic observations.
