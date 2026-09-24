# Country announcement source integration

## Outcome

The five project countries now use the same auditable collection boundary.
Germany and the United States discover documents through RSS; Israel, China
and Iran discover them through official chronological HTML listings. The
United States also has a separate USAspending V2 connection for structured
contract transactions. Raw retrievals are stored append-only.

The Excel `Country_Source_Registry` remains the research master. The runtime
export in `config/country_sources.json` contains the first implementation
candidate for each country and must be reviewed whenever the Excel registry is
changed.

## Integration status

| Country | Source ID | Runtime status | Delivery | Main validation note |
|---|---|---|---|---|
| Germany | `DE_BMVG_NEWS` | `IMPLEMENTED` | RSS + HTML detail | Official BMVg RSS endpoint replaces the former Bundestag demo feed. |
| United States | `US_DOD_CONTRACTS` | `IMPLEMENTED` | RSS discovery only | Official publication timestamps and URLs; automated article and print views returned HTTP 403. |
| United States | `US_USASPENDING_CONTRACTS` | `IMPLEMENTED` | Paginated public API | Independent transaction records with award, modification, recipient, action date, amount and description. |
| Israel | `IL_IMOD_PRESS` | `IMPLEMENTED` | HTML listing + detail | Official English IMOD press room; English and Hebrew dates can differ. |
| China | `CN_STATE_COUNCIL` | `IMPLEMENTED` | Paginated HTML + detail | Numbered archive pages are supported; controlling Chinese documents remain separate evidence. |
| Iran | `IR_MFA_STATEMENTS` | `IMPLEMENTED` | HTML listing + detail | Statements endpoint plus stable numeric detail URLs; translation timing can differ. |

## Shared collection flow

1. `SourceRegistry` loads and validates the source definition, ISO country code,
   official URLs and IANA publication timezone.
2. `RssSourceAdapter` or `HtmlListingSourceAdapter` discovers official release
   URLs and retains the stable source ID, jurisdiction and timezone.
3. `HtmlDocumentFetcher` follows supported release links, stores the canonical
   URL and extracts the full article text. The U.S. DOD source deliberately
   stops after RSS discovery because both official detail views rejected the
   tested automated client.
4. `VersionedRawDocumentRepository` saves every retrieval append-only beneath
   source ID and URL-derived document ID. Later corrections therefore do not
   overwrite the evidence used by an earlier analysis.
5. Existing normalization and candidate extraction remain downstream steps.
   Automated candidate output is not a verified event until it passes the
   existing review process.

## Run the collectors

Install the project dependencies in the existing virtual environment and run
from the project root:

```powershell
.\.venv\Scripts\python.exe -m src.collect_country_announcements --source-id DE_BMVG_NEWS --query "*" --max-results 20
```

_Linux/macOS equivalent (after `source .venv/bin/activate`):_

```bash
.venv/bin/python -m src.collect_country_announcements --source-id DE_BMVG_NEWS --query "*" --max-results 20
```

For a bounded research window, use ISO dates:

```powershell
.\.venv\Scripts\python.exe -m src.collect_country_announcements --source-id DE_BMVG_NEWS --start-date 2026-01-01 --end-date 2026-12-31
```

_Linux/macOS equivalent (after `source .venv/bin/activate`):_

```bash
.venv/bin/python -m src.collect_country_announcements --source-id DE_BMVG_NEWS --start-date 2026-01-01 --end-date 2026-12-31
```

Bounded runs exclude entries without a parseable publication date. This avoids
silently placing undated evidence inside an event window.

To test discovery without downloading the linked pages, use either the new
name or the retained backwards-compatible alias:

```powershell
.\.venv\Scripts\python.exe -m src.collect_country_announcements --discovery-only --max-results 5
```

_Linux/macOS equivalent (after `source .venv/bin/activate`):_

```bash
.venv/bin/python -m src.collect_country_announcements --discovery-only --max-results 5
```

The United States adapter uses the same command boundary:

```powershell
.\.venv\Scripts\python.exe -m src.collect_country_announcements --source-id US_DOD_CONTRACTS --feed-only --max-results 5
```

_Linux/macOS equivalent (after `source .venv/bin/activate`):_

```bash
.venv/bin/python -m src.collect_country_announcements --source-id US_DOD_CONTRACTS --feed-only --max-results 5
```

The stable source ID retains `DOD` for database compatibility even though the
current official publisher and domain identify the agency as the U.S.
Department of War.

USAspending contract transactions require an explicit start and end date. A
recipient search is passed to the official API rather than applied to a press
release:

```powershell
.\.venv\Scripts\python.exe -m src.collect_country_announcements --source-id US_USASPENDING_CONTRACTS --query "Lockheed Martin" --start-date 2026-01-01 --end-date 2026-08-18 --max-results 5
```

_Linux/macOS equivalent (after `source .venv/bin/activate`):_

```bash
.venv/bin/python -m src.collect_country_announcements --source-id US_USASPENDING_CONTRACTS --query "Lockheed Martin" --start-date 2026-01-01 --end-date 2026-08-18 --max-results 5
```

Use `--query "*"` for an agency-wide bounded pull. Results are paginated in
stable blocks of at most 100 and saved under
`data/raw/contracts/usaspending/`. Keep an explicit maximum during validation;
the complete agency-wide transaction volume can be large.

## HTML country adapters

Run discovery-only checks first. These commands do not fetch individual detail
pages, but they do save the discovered source records append-only:

```powershell
.\.venv\Scripts\python.exe -m src.collect_country_announcements --source-id IL_IMOD_PRESS --discovery-only --max-results 3
.\.venv\Scripts\python.exe -m src.collect_country_announcements --source-id CN_STATE_COUNCIL --discovery-only --max-results 3
.\.venv\Scripts\python.exe -m src.collect_country_announcements --source-id IR_MFA_STATEMENTS --discovery-only --max-results 3
```

_Linux/macOS equivalent (after `source .venv/bin/activate`):_

```bash
.venv/bin/python -m src.collect_country_announcements --source-id IL_IMOD_PRESS --discovery-only --max-results 3
.venv/bin/python -m src.collect_country_announcements --source-id CN_STATE_COUNCIL --discovery-only --max-results 3
.venv/bin/python -m src.collect_country_announcements --source-id IR_MFA_STATEMENTS --discovery-only --max-results 3
```

Then validate one full document per country:

```powershell
.\.venv\Scripts\python.exe -m src.collect_country_announcements --source-id IL_IMOD_PRESS --max-results 1
.\.venv\Scripts\python.exe -m src.collect_country_announcements --source-id CN_STATE_COUNCIL --max-results 1
.\.venv\Scripts\python.exe -m src.collect_country_announcements --source-id IR_MFA_STATEMENTS --max-results 1
```

_Linux/macOS equivalent (after `source .venv/bin/activate`):_

```bash
.venv/bin/python -m src.collect_country_announcements --source-id IL_IMOD_PRESS --max-results 1
.venv/bin/python -m src.collect_country_announcements --source-id CN_STATE_COUNCIL --max-results 1
.venv/bin/python -m src.collect_country_announcements --source-id IR_MFA_STATEMENTS --max-results 1
```

China can traverse numbered archive pages for bounded research windows. Keep
the result limit explicit while validating the desired range:

```powershell
.\.venv\Scripts\python.exe -m src.collect_country_announcements --source-id CN_STATE_COUNCIL --start-date 2026-01-01 --end-date 2026-08-18 --max-results 20
```

_Linux/macOS equivalent (after `source .venv/bin/activate`):_

```bash
.venv/bin/python -m src.collect_country_announcements --source-id CN_STATE_COUNCIL --start-date 2026-01-01 --end-date 2026-08-18 --max-results 20
```

## Verification

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

_Linux/macOS equivalent (after `source .venv/bin/activate`):_

```bash
.venv/bin/python -m unittest discover -s tests -v
```

The suite includes coverage for three official listing shapes, local date
parsing, China pagination, same-domain enforcement, Iranian URL normalization,
source-specific timeouts and the bounded, paginated USAspending transaction
adapter.

## Research limitations

- The BMVg RSS feed is a current feed and does not establish completeness for a
  historical backfill. The 35 manually verified BMVg records in the workbook
  remain the backfill reference until archive completeness is documented.
- The U.S. Contract Announcements feed exposes the latest ten daily documents.
  It validates discovery but not automated full-text retrieval or historical
  completeness. Both official article views returned HTTP 403 to the tested
  automated Windows client; no bypass is attempted.
- USAspending is a separate transaction dataset. Its action date must not be
  silently substituted for the publication timestamp of a daily DOD contract
  announcement. Any connection between the two sources requires a documented
  matching step using identifiers, recipient, amount and date.
- One U.S. daily announcement can contain multiple awards and modifications.
  The connector stores the source document; event-family splitting and
  adjudication remain downstream research steps.
- The visible Israeli press-room listing does not establish a complete
  January-August archive. A separate backfill/completeness check remains
  necessary.
- China exposes stable numbered news pages, but some English items are newswire
  reports rather than controlling policy documents. Preserve the original
  Chinese policy link as separate evidence when it exists.
- Iran's current English statements listing and detail pages are automated.
  Historical pagination has not yet been treated as verified, and English
  publication can lag the Persian original.
- `IMPLEMENTED` describes technical retrieval, not semantic correctness or
  event eligibility. Verification status must remain separate.
- No credentials are stored in this integration. Runtime secrets remain in a
  local `.env` and are excluded by `.gitignore`.
