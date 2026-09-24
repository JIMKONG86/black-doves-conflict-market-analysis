# Country adapter rollout order

The Version 4 files can be copied into the project once. Activate operational
use through the following small validation gates rather than collecting every
country in one run.

## Gate 1 - Israel

```powershell
.\.venv\Scripts\python.exe -m src.collect_country_announcements --source-id IL_IMOD_PRESS --discovery-only --max-results 3
.\.venv\Scripts\python.exe -m src.collect_country_announcements --source-id IL_IMOD_PRESS --max-results 1
```

_Linux/macOS equivalent (after `source .venv/bin/activate`):_

```bash
.venv/bin/python -m src.collect_country_announcements --source-id IL_IMOD_PRESS --discovery-only --max-results 3
.venv/bin/python -m src.collect_country_announcements --source-id IL_IMOD_PRESS --max-results 1
```

Pass criteria: three successful discoveries, one successful full document,
country code `IL`, timezone `Asia/Jerusalem`, and a plausible publication date.

## Gate 2 - China

```powershell
.\.venv\Scripts\python.exe -m src.collect_country_announcements --source-id CN_STATE_COUNCIL --discovery-only --max-results 3
.\.venv\Scripts\python.exe -m src.collect_country_announcements --source-id CN_STATE_COUNCIL --max-results 1
```

_Linux/macOS equivalent (after `source .venv/bin/activate`):_

```bash
.venv/bin/python -m src.collect_country_announcements --source-id CN_STATE_COUNCIL --discovery-only --max-results 3
.venv/bin/python -m src.collect_country_announcements --source-id CN_STATE_COUNCIL --max-results 1
```

Pass criteria: official `english.www.gov.cn` links, country code `CN`, timezone
`Asia/Shanghai`, and non-empty full text. A slower response is expected; the
configured timeout is 90 seconds.

## Gate 3 - Iran

```powershell
.\.venv\Scripts\python.exe -m src.collect_country_announcements --source-id IR_MFA_STATEMENTS --discovery-only --max-results 3
.\.venv\Scripts\python.exe -m src.collect_country_announcements --source-id IR_MFA_STATEMENTS --max-results 1
```

_Linux/macOS equivalent (after `source .venv/bin/activate`):_

```bash
.venv/bin/python -m src.collect_country_announcements --source-id IR_MFA_STATEMENTS --discovery-only --max-results 3
.venv/bin/python -m src.collect_country_announcements --source-id IR_MFA_STATEMENTS --max-results 1
```

Pass criteria: official `en.mfa.gov.ir` evidence, country code `IR`, timezone
`Asia/Tehran`, a numeric `/portal/newsview/<id>` retrieval URL and non-empty
full text.

## Regression gate

After each country gate, run:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

_Linux/macOS equivalent (after `source .venv/bin/activate`):_

```bash
.venv/bin/python -m unittest discover -s tests -v
```

The complete Version 4 suite should report `Ran 220 tests` and `OK`.

Technical success does not establish historical completeness, semantic event
eligibility or source neutrality. Those remain explicit research-validation
steps.
