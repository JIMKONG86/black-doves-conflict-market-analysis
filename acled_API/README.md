# ACLED API connector — BLACK DOVES

This small Python module connects the written assignment to ACLED's current
OAuth API. It contains a bounded connection test and an optional study-period
download. No credentials are embedded in the code.

## What ACLED contributes

Use ACLED for geocoded conflict events, involved actors, event types, sources,
locations, and ACLED's conservative reported-fatality estimate. Do not use this
dataset as evidence for share prices, arms contracts, state announcements,
political positioning, or consumer prices; those require separate sources.

The country filter describes **where an event occurred**. Events returned for
Germany or China are therefore not automatically connected to the
Israel–Iran–United States conflict. Conflict relevance must be established by
transparent actor/event criteria or manual validation.

## Setup (Windows / VS Code)

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Open `.env` and enter the credentials for the activated university myACLED
account. Never email, upload, commit, or paste this file into a chat.

If the account uses a sign-in method for which the password flow does not work,
insert a currently valid OAuth access token under `ACLED_ACCESS_TOKEN` instead.
ACLED states that access tokens expire after 24 hours.

## 1. Safe connection test

```powershell
py download_acled.py --smoke-test
```

This retrieves at most one row. A successful request proves that OAuth and API
permission work; it does not yet validate the scientific sample.

## 2. Optional frozen study-period download

```powershell
py download_acled.py --download-study-data
```

Prepared filters:

- countries: Iran, Israel, United States, Germany, China
- dates: 2026-01-01 through 2026-08-18
- response format: JSON, written locally as UTF-8 CSV
- pagination: cursor-based

Output: `data/acled_events_2026-01-01_to_2026-08-18.csv`

This is deliberately a broad candidate dataset. Before analysis, define and
document which actors and event types identify the focal conflict, then retain
only validated records. Do not interpret ACLED `fatalities` as a complete or
final casualty count.

## Tests

```powershell
py -m pytest -q
```

The tests use simulated API responses and never contact ACLED.

## Official documentation

- https://acleddata.com/api-documentation/getting-started
- https://acleddata.com/api-documentation/acled-endpoint
- https://acleddata.com/api-documentation/elements-acleds-api
