# Appendix B — Audit of additional findings

This appendix records how the late-supplied observations were checked against
the project data and which conclusions are admissible. It separates a
timestamped association from company/sector specificity and from causality.

## Decision table

| Proposed interpretation | Data check | Decision |
|---|---|---|
| Rheinmetall reactions look realistically irregular | The Italian event is 15 January **2025** and concerns **Skynex**, not Skyranger. Its event-day abnormal return is −1.28%; day +1 is +4.12%. The October event day is +0.35%, but CAR `[0,+10]` is −5.59% and OLS CAR −11.28%. | Retain as descriptive heterogeneity. Irregularity does not verify authenticity; provenance and checksums do. |
| Rheinmetall’s 1–2 July run is unusually clean | Rheinmetall’s two-day market-adjusted return is +9.86%. All nine defence firms are positive on both dates and average +6.99%; Rheinmetall’s eight peers average +6.63%. | The sector-wide component is directly supported. A firm-specific increment remains possible but is not identified. |
| The 9 August Pentagon report moved Lockheed and Northrop | On 10 August LMT is +2.65%, NOC +1.16%, GD +1.06% and RTX +0.55% market-adjusted. All four are positive and average +1.35%. The 14 non-defence companies using the same S&P 500 benchmark average +1.46%. | Retain as a clean Sunday-to-Monday, post-hoc timing anchor. Do not call it a defence-specific or causal media effect. |
| Patriot depletion creates a concrete RTX demand channel | CSIS estimates 759–827 Patriot interceptors remaining from a 2,330 pre-war baseline (at least −65%). AP reports the Pentagon production push. Primary sources map GEM-T to RTX/Raytheon and PAC-3 MSE to Lockheed Martin. | Retain as a replenishment/capacity mechanism relevant to both companies. It is one inventory estimate, not multiple independent counts or an equity effect. |
| BlackRock is an omitted common-ownership link | The SEC Q2 2026 13F combination report confirms 18,877,978 LMT shares, 11,783,817 NOC, 110,528,494 RTX and 334,746,496 Exxon shares across reporting entities. | Retain as a separate ownership-network layer. Do not equate managed client assets with BlackRock’s own profit, voting conduct or balance-sheet exposure. |
| Casualty discrepancies reveal source incentives | The supplied rows mix total, civilian-only and military-only counts, non-aligned dates and self/NGO/UN/adversary reporting, all routed through one secondary compilation. | Retain only as a source-criticism example. The data cannot identify the true total, bias direction or a consistent intensity measure. |
| Germany reacts through DAX and Bund yields | The supplied anchors are sparse and mix closes, intraday levels and approximations; three are after the fixed endpoint. | Plausible future channel, not a current result. Obtain continuous official series and add oil, rate and market controls first. |
| Israeli decisions directly affect Germany | No pre-specified Israeli decision set is linked to German target assets in the current design. | Explicit research gap. A separate bilateral event study is required. |
| The media corpus shows German reporting dominance | RND contributes 178 of 247 pilot documents (72.1%), or 178 of 206 NEWS-layer records (86.4%); no document is manually reviewed. | Sampling artifact. Exclude substantive media-positioning comparisons. |
| September stories can be matched to September market data | Some raw price histories end 2 September and media files 14 September, but the approved core endpoint is 18 August. | Keep outside the core design. Any extension must be specified and labelled separately before analysis. |

## Reproducible files

- `data/analysis/post_hoc_market_checks.csv` contains the complete comparison
  groups for the July and August checks.
- `data/reference/blackrock_13f_holdings.csv` contains SEC-derived positions
  aggregated by CUSIP.
- `data/reference/patriot_supply_context.csv` separates inventory estimates,
  production signals and contractor mappings.
- `data/reference/additional_findings_audit.csv` stores the claim-level
  inclusion and wording boundaries used by the report.

These checks refine interpretation; they do not change the pre-specified
28 February event-study estimates.
