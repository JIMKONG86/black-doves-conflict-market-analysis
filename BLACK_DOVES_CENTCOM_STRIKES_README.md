# BLACK DOVES CENTCOM strike integration

This module adds official U.S. strike evidence to the conflict dashboard
without treating the United States as an affected country in the ACLED data.

## Source and scope

- Source: U.S. Central Command public releases:
  <https://www.centcom.mil/MEDIA/PUBLIC-RELEASES/>
- Source ID: `US_CENTCOM_PUBLIC_RELEASES`
- Study window: 2026-01-01 through 2026-08-18.
- Initiator: United States (`US`).
- Core affected country: Iran (`IR`).

The reviewed dataset is
`data/validated/centcom_us_strike_operation_days.csv`. It contains 24
documented operation-day rows. Twenty-three Iran rows are included in the core
dashboard series. The joint U.S.-Saudi strike in Iraq on 2026-07-28 is retained
for provenance but has `include_in_core_series=false` because Iraq is outside
the Iran/Israel affected-country scope.

## Counting rule

The unit is `official_release_confirmed_operation_day`: one distinct calendar
day on which the full text of an official CENTCOM release affirmatively states
that U.S. forces executed strikes.

It is not a count of targets, munitions, sorties, waves or press releases. Two
strike waves on the same day therefore count as one operation day. One release
that explicitly covers strikes on two calendar days can create two rows.

The dashboard displays the CENTCOM series in a separate aligned panel because
CENTCOM operation days and ACLED event counts are different units and cannot be
added or compared as though they were the same measurement.

## Inclusion and exclusion

Include only a full-text statement that:

1. identifies U.S. participation;
2. affirmatively describes completed or ongoing executed strikes;
3. identifies the affected country; and
4. supports a specific event date.

Exclude warnings, plans, situation/casualty updates, denials or refutations,
missile/drone interceptions, mine-clearance activity, blockades and vessel-only
disable actions. The 2026-04-05 release saying that strikes “continue” is not a
separate operation-day row because it does not identify the strike day. The
2026-03-31 Lamerd release is a refutation and is also excluded.

The records are official U.S. claims. They confirm what CENTCOM reported that
U.S. forces did; they do not independently verify damage or military effects.

## Collect the official chronology

Discovery stores versioned raw listing records and preserves the official
release URLs:

```powershell
.\.venv\Scripts\python.exe -m src.collect_country_announcements `
    --source-id US_CENTCOM_PUBLIC_RELEASES `
    --query "*" `
    --start-date 2026-01-01 `
    --end-date 2026-08-18 `
    --max-results 200 `
    --discovery-only
```

_Linux/macOS equivalent (after `source .venv/bin/activate`):_

```bash
.venv/bin/python -m src.collect_country_announcements \
    --source-id US_CENTCOM_PUBLIC_RELEASES \
    --query "*" \
    --start-date 2026-01-01 \
    --end-date 2026-08-18 \
    --max-results 200 \
    --discovery-only
```

Remove `--discovery-only` to retrieve article text. A human must still review
the full text before adding or changing a row in the validated CSV.

## Import into the strike domain

The importer creates `ClaimObservation` and `StrikeObservation` records with
`claim_status=confirmed`, `source_channel=government`,
`initiator_country_code=US` and the affected-country code from the CSV.

```powershell
.\.venv\Scripts\python.exe -m src.import_centcom_strikes `
    --reviewed-by "Markus Nestler" `
    --strict
```

_Linux/macOS equivalent (after `source .venv/bin/activate`):_

```bash
.venv/bin/python -m src.import_centcom_strikes \
    --reviewed-by "Markus Nestler" \
    --strict
```

The reviewer argument records who accepts responsibility for the validated
import. Repeating the same import with the same reviewer is idempotent.

## Build the dashboard

```powershell
.\.venv\Scripts\python.exe -m src.visualize_fuel_price_lags
```

_Linux/macOS equivalent (after `source .venv/bin/activate`):_

```bash
.venv/bin/python -m src.visualize_fuel_price_lags
```

The `Strikes` tab contains two aligned panels:

- ACLED weekly event/fatality metrics by affected country (Iran and Israel);
- CENTCOM-confirmed U.S. strike-operation days by initiator role.

The role/series filter controls which panels are visible. The conflict-metric
filter applies only to the ACLED panel.
