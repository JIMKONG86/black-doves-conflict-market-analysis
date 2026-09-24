# Data availability

This repository is the public code and reproducibility record for the BLACK
DOVES written assignment. It uses a fixed submission freeze dated 24 September
2026.

## Included

- the complete Python implementation and automated test suite;
- the 46-company configuration and benchmark mapping;
- processed company/benchmark return panels;
- curated reference, procurement, country-role and event tables;
- derived and validated weekly conflict aggregates;
- Brent and German fuel-price inputs and analytical results;
- source registries, retrieval metadata and reproducibility documentation.

These files are sufficient to run the automated tests and rebuild the central
dashboard from the fixed analytical inputs.

## Not published in the public repository

- the original licensed ACLED weekly export;
- credentials, tokens and local `.env` files;
- Git history from development workspaces;
- virtual environments, caches and editor files;
- generated HTML reports and other large build artifacts.

The original ACLED export is omitted from the public repository to avoid
redistributing a licensed source dataset. The derived aggregates used by the
submitted analysis remain included for transparency and reproducibility. The
complete frozen data-and-output ZIP is archived separately as part of the
university handover.

## Source refreshes

Source acquisition scripts are included for methodological transparency.
Running them can create a data version that differs from the submitted freeze.
Any refresh should therefore record its retrieval date, query parameters and
file hashes before comparison with the submitted results.
