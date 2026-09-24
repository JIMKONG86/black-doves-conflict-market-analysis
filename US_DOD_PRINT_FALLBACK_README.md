# US DOD contracts: official print-view hotfix

## Reason

The official RSS feed successfully discovers the latest daily contract
announcements. In the Windows user environment, the standard public article
view returned HTTP 403 to the academic crawler even though the page remained
available interactively.

## Resolution

The adapter now derives the article identifier from the RSS URL and retrieves
the full text through the official ArticleCS print view on the same government
domain. The stored `url` and `canonical_url` remain the normal public article
URL so the evidence record stays suitable for review and citation.

No third-party source, scraping proxy, authentication bypass or browser
automation is used.

## Test

```powershell
.\.venv\Scripts\python.exe -m unittest `
    tests.test_configured_announcement_adapter `
    tests.test_source_registry `
    -v

.\.venv\Scripts\python.exe -m src.collect_country_announcements `
    --source-id US_DOD_CONTRACTS `
    --max-results 1
```

_Linux/macOS equivalent (after `source .venv/bin/activate`):_

```bash
.venv/bin/python -m unittest \
    tests.test_configured_announcement_adapter \
    tests.test_source_registry \
    -v

.venv/bin/python -m src.collect_country_announcements \
    --source-id US_DOD_CONTRACTS \
    --max-results 1
```

The second command should save one successful record with a non-empty full
contract text while retaining the ordinary `war.gov/News/Contracts/...` URL.
