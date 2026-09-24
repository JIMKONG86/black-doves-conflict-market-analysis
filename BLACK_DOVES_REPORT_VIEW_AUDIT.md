# BLACK DOVES – Audit der Berichtsansichten

Stand: 13.09.2026

## Ergebnis des Alt-/Neu-Abgleichs

Die Unternehmensdaten fehlen nicht. Die drei maßgeblichen Dateien enthalten
dieselben 46 eindeutigen `company_id`-Werte:

- `config\company_market_universe.csv`
- `data\analysis\market_universe_company_summary.csv`
- `data\analysis\market_position_company_summary.csv`

Der scheinbar leere Unternehmensfilter entstand durch helle
Browser-Standardflächen bei gleichzeitig heller Schrift. Auswahlfelder,
Optionslisten, Reset-Schaltfläche und Bokeh-Tabs besitzen nun explizite
Dark-Mode-Zustände. Ein Regressionstest vergleicht künftig die vollständigen
Unternehmensmengen aller drei Dateien.

## Zuordnung der alten Ansichten

| Alte Datei / Ansicht | Ort in `black_doves_complete_analysis.html` | Status |
|---|---|---|
| `black_doves_energy_price_lag.html` | `Strikes & energy` | Vollständig eingebettet; Strike-, CENTCOM-, EUR/L-, Index-, Änderungs- und Lag-Ansicht erhalten |
| `black_doves_market_universe_event_study.html` | `Event study` | Vollständig eingebettet; Sample AAR/CAAR, alle Unternehmen, Rollen und Confirmatory + VW erhalten |
| `black_doves_long_horizon_market_position.html` | `Market position` | Vollständig eingebettet; 46 Unternehmen sowie Sample CAAR, Position map, Rank shifts, Post CAR und Primary + VW erhalten |
| `black_doves_procurement_event_study_v2.html` | `Procurement` | Durch die aktive, reproduzierbar erzeugte Procurement-Ansicht abgedeckt |
| `black_doves_market_conflict_v2.html` | `Company & announcements` → Vorauswahl Rheinmetall | Markt-/Benchmarkvergleich, Konfliktkontext und fünf verifizierte Beschaffungsankündigungen übernommen und auf alle 46 Firmen verallgemeinert |
| `market_comparison.html` | `Company & announcements` → Marktchart | Inhaltlich durch die auswählbare Firma gegen ihren konfigurierten Benchmark abgedeckt; keine redundante zweite Seite |
| `black_doves_market_conflict.html` | `Company & announcements` → Konfliktcharts | Betroffene-Länder-Linien erhalten; U.S.-Initiator-Daten bleiben als eigener CENTCOM-Strip methodisch getrennt |

## Abgrenzung der Zeiträume

- Kernfenster: 01.01.–18.08.2026 für Event Study, Marktposition und
  Strike-/Energieanalyse.
- Firmenansicht, Kernfenster: 01.01.–18.08.2026.
- Firmenansicht, unterstützender Horizont: 01.01.2025 bis zum letzten
  verfügbaren Marktdatum der eingebetteten Datei.
- Firmenansicht, vollständige Historie: erstes bis letztes verfügbares
  Marktdatum. Diese Auswahl ist eine Unterstützungsperspektive und darf nicht
  mit dem einheitlichen Kernfenster gleichgesetzt werden.

## Firmen- und Ankündigungsabdeckung

| Ebene | Abdeckung | Interpretation |
|---|---:|---|
| Firmenuniversum | 46/46 | Alle konfigurierten Firmen sind im Auswahlmenü vorhanden |
| Firmen-/Benchmark-Zeitreihen | 46/46 | Preis-, Rendite- und Abnormal-Return-Felder liegen für alle Firmen vor |
| Firmenbezogene Ankündigungen | 1/46 | Fünf kuratierte Rheinmetall-Datensätze; `PARTIAL_CURATED` |
| Übrige Firmenankündigungen | 45/46 `MISSING` | Fehlender Import, ausdrücklich keine Nullbeobachtung |

Der Filter `Announcement type` wirkt nur auf importierte Firmenmarker und das
Register. Der Filter `Conflict metric` wirkt auf die Linien der betroffenen
Länder. CENTCOM-Einsatztage sind eine separate U.S.-Initiator-Reihe und werden
nie auf ACLED-Länderereignisse addiert.

## Menü- und Filterstandard

- Desktop: Filter stehen nebeneinander in einer kompakten Toolbar.
- Mittlere Breiten: kontrollierter Zeilenumbruch.
- Mobil: ein Feld pro Zeile mit ausreichend großen Bedienflächen.
- Auswahlfelder: sichtbare dunkle Fläche, helle Schrift, eigener Pfeil sowie
  definierte Hover- und Fokuszustände.
- Tabs: getrennte Zustände für inaktiv, Hover, Fokus und aktiv.
- Reset- und Paging-Schaltflächen: dunkle Fläche, sichtbarer Rahmen und
  mindestens 40 Pixel Höhe.
- Diagramm-Tabs: gemeinsame Panelhöhe innerhalb einer Tabgruppe. Die lange
  46-Firmen-Rangliste erzeugt dadurch keinen Leerraum mehr in kürzeren Tabs.

## Automatische Prüfung

Der vollständige Testlauf umfasst 308 erfolgreiche Tests. Zusätzlich zu den
fachlichen Tests prüfen Regressionstests nun:

- identische 46-Unternehmens-Abdeckung in Konfiguration und beiden Analysen,
- explizite Dark-Mode-Styles für Select, Button und Tabs,
- responsive Filter-Toolbars,
- den Firmenfilter mit sämtlichen 46 Firmennamen,
- explizite `MISSING`-Kennzeichnung bei fehlender Ankündigungsabdeckung,
- validierten und idempotenten Import neuer Firmenankündigungen,
- identische Diagrammhöhen in tab-basierten Ansichten,
- selbst enthaltene Berichte ohne Bokeh-CDN-Abhängigkeit,
- Einbettung aller fünf Diagrammberichte in die Master-HTML.
