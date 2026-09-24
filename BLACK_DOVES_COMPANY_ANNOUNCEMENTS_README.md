# BLACK DOVES – Firmen- und Ankündigungsansicht

## Zweck

Der Master-Tab `Company & announcements` ist ein exploratives Werkzeug zur
visuellen Gegenüberstellung von Firmenkursen, lokalen Benchmarks,
firmenbezogenen Ankündigungen und Konfliktaktivität. Rheinmetall ist nur die
Vorauswahl und der derzeit einzige Fall mit kuratierten Ankündigungsdaten. Das
Auswahlmenü enthält alle 46 Unternehmen des definierten Marktuniversums.

Die Ansicht unterstützt die Ableitung prüfbarer zeitlicher Muster. Sie liefert
keinen Kausalitätsnachweis und ersetzt keine Event-Study-Spezifikation.

## Reihenfolge und Elemente

1. **Firmenfilter:** wählt eine `company_id` und damit Firma, Ticker, Rolle und
   konfigurierten Benchmark.
2. **Zeitraumfilter:** wählt Kernfenster, unterstützenden Horizont oder gesamte
   verfügbare Markthistorie.
3. **Ankündigungstyp:** filtert ausschließlich importierte Firmenmarker und
   das darunterliegende Register.
4. **Konfliktmetrik:** wechselt die betroffene-Länder-Linien zwischen
   Ereignissen und Todesopfern für alle Strikes, Air/Drone oder
   Shelling/Artillery/Missile.
5. **Abdeckungsbanner:** zeigt `PARTIAL_CURATED` oder `MISSING` sowie den
   aktuellen Zeitraum und die Anzahl passender Datensätze.
6. **Marktchart:** Firma und lokaler Benchmark werden am ersten sichtbaren
   Handelstag jeweils auf 100 rebasiert. Diamanten markieren importierte
   Ankündigungsdaten.
7. **Ankündigungsregister:** listet Quelle, Typ, Gegenpartei, System,
   Wertbeschreibung, Scope und Verifikationsstatus.
8. **Konfliktchart:** zeigt die gewählte ACLED-Metrik nach betroffenem Land.
9. **CENTCOM-Strip:** zeigt separat bestätigte U.S.-initiierte Einsatztage aus
   offiziellen CENTCOM-Veröffentlichungen.

Bei einem Ankündigungsdatum ohne Kursbeobachtung wird der Markerwert am
nächstgelegenen verfügbaren Handelstag ausgerichtet. Im Hover werden das
ursprüngliche Ankündigungsdatum, der ausgerichtete Handelstag und dessen
Abnormal Return getrennt ausgewiesen.

## Abdeckung im ausgelieferten Stand

| Datenebene | Abdeckung | Status |
|---|---:|---|
| Firmenauswahl | 46/46 | vollständig für das konfigurierte Universum |
| Firma plus Benchmark | 46/46 | vorhanden |
| Firmenankündigungen | 1/46 | `PARTIAL_CURATED` |
| Rheinmetall-Ankündigungen | 5 Datensätze | primärquellenbestätigt |
| Andere Firmen | 0 importierte Datensätze | `MISSING`, nicht „keine Ankündigungen“ |

Die fünf Rheinmetall-Datensätze wurden aus der älteren verifizierten
Einzelfallansicht in das allgemeine Register migriert. Die aktuelle Abdeckung
ist weder ein vollständiger Rheinmetall-Newsfeed noch ein vollständiges
Firmenpanel.

## Datenquellen und Trennung

| Inhalt | Datei | Einheit / Rolle |
|---|---|---|
| Firmenuniversum | `config\company_market_universe.csv` | Firma, Ticker, Benchmark, Rolle |
| Marktzeitreihen | `data\processed\market\company_benchmark_returns.csv` | tägliche Preise und Renditen |
| Firmenankündigungen | `data\reference\company_announcements.csv` | kuratierte, quellenverknüpfte Ereignisse |
| Konfliktkontext | `data\analysis\weekly_conflict_features.csv` | wöchentliche Ereignisse nach betroffenem Land |
| U.S.-Initiator-Reihe | `data\validated\centcom_us_strike_operation_days.csv` | bestätigte Operationstage aus CENTCOM-Releases |

Die CENTCOM-Reihe wird nicht zu ACLED-Ereignissen addiert. Damit bleibt die
unterschiedliche Beobachtungseinheit sichtbar: betroffenes Land einerseits,
offiziell bestätigter Initiator-/Operationstag andererseits.

## Neue Ankündigungen importieren

1. `data\import_templates\company_announcements_template.csv` kopieren.
2. Die Beispielzeile ersetzen und mindestens diese Felder ausfüllen:
   `announcement_date`, `company_id`, `announcement_type`, `title`,
   `source_name`, `source_url`, `verification_status`, `coverage_status` und
   `record_scope`.
3. Import und Neubau aus dem Projektordner ausführen:

```powershell
.\.venv\Scripts\python.exe -m src.import_company_announcements `
  data\imports\company_announcements.csv

.\.venv\Scripts\python.exe -m src.build_black_doves_master
```

_Linux/macOS equivalent (after `source .venv/bin/activate`):_

```bash
.venv/bin/python -m src.import_company_announcements \
  data/imports/company_announcements.csv

.venv/bin/python -m src.build_black_doves_master
```

Der Importer validiert Datum, HTTP(S)-Quelle, Firmenzuordnung, Ticker,
optionale numerische Vertragswerte und eindeutige IDs. Fehlt die ID, wird sie
deterministisch aus Firma, Datum, Typ, Titel und URL gebildet. Ein identischer
erneuter Import ist idempotent; gleicher ID-Wert mit verändertem Inhalt wird
als Kollision abgewiesen.

## Verteidigbare Aussagen

- Zulässig: „Im ausgewählten Zeitraum liegen diese importierten und
  quellenverknüpften Ankündigungen nahe an diesen beobachteten Markt- und
  Konfliktverläufen.“
- Nicht zulässig: „Der Konflikt oder die Ankündigung verursachte die
  Kursbewegung.“
- Nicht zulässig: „Für eine Firma ohne Marker gab es keine Ankündigungen.“
- Für quantitative Ereignisfenster sind die separaten Tabs `Event study` und
  `Procurement` maßgeblich; diese Ansicht dient der Exploration und Prüfung.

## Reproduzierbarkeit

- Generator: `src\visualize_company_announcements.py`
- Importer: `src\import_company_announcements.py`
- Einzeldatei: `output\black_doves_company_announcements.html`
- Gesamtdatei: `output\black_doves_complete_analysis.html`
- Tests: `tests\test_company_announcement_visualization.py` und
  `tests\test_import_company_announcements.py`
