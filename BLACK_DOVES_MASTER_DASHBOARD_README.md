# BLACK DOVES – Master-Dashboard und Medien-Connectoren

## Ergebnis

Der zentrale Build erzeugt eine einzige, offline nutzbare HTML-Datei:

`output\\black_doves_complete_analysis.html`

Sie enthält die vollständigen vorhandenen Analyseansichten, einen
länderübergreifenden Strike-/Energiebericht, die Narrativansicht, das
Datenregister, die Defense-Map sowie die Methoden- und Quellenübersicht.
Analysefertige CSV-Dateien werden vollständig eingebettet und können aus dem
Datenregister wieder unverändert heruntergeladen werden.

Das Layout ist fest auf das bestätigte BLACK-DOVES-Dark-Theme eingestellt.
Master-Navigation, Tabellen, Filter, Tooltips und alle fünf aktiven
Diagrammberichte verwenden dieselben dunklen Flächen, Kontraste und
Farbakzente; die Darstellung ist nicht von der Browser-Systemeinstellung
abhängig.

Die Filter im Strike-/Energiebericht und in der Marktposition sind als
kompakte Toolbars umgesetzt: dauerhaft beschriftete Einzelauswahlen stehen auf
großen Bildschirmen in einer Reihe, umbrechen auf mittleren Breiten und wechseln
auf Mobilgeräten in eine Spalte. Auswahlfelder, Optionsmenüs, Schaltflächen,
Tabs, Pfeile, Rahmen, Hover- und Fokuszustände besitzen explizite
Dark-Mode-Farben; dadurch greifen keine hellen Browser-Standardflächen in die
Ansicht ein.

Der Tab `Company & announcements` verallgemeinert die frühere
Rheinmetall-Einzelfallansicht. Alle 46 Unternehmen können gewählt und jeweils
mit ihrem konfigurierten lokalen Benchmark, dem Konfliktkontext und
firmenbezogenen Ankündigungen betrachtet werden. Der alte Rheinmetall-Fall ist
als voreingestellte Auswahl erhalten, aber nicht mehr als eigener starrer Tab.

Die Abdeckung wird absichtlich zweigeteilt dargestellt:

- Markt- und Benchmarkdaten: 46 von 46 Unternehmen.
- Firmenbezogene Ankündigungen: derzeit 1 von 46 Unternehmen, nämlich fünf
  kuratierte Rheinmetall-Beschaffungsankündigungen.

Bei den übrigen Unternehmen zeigt die Ansicht `Announcement coverage:
MISSING`. Keine Marker dürfen deshalb nicht als null reale Ankündigungen
interpretiert werden. Der auswählbare Zeitraum unterscheidet das Kernfenster
01.01.–18.08.2026, den unterstützenden Horizont 2025–2026 und die gesamte
verfügbare Markthistorie.

Die Diagrammhöhen innerhalb der Ansichten `Market position`, `Event study` und
`Strikes & energy` sind pro Tabgruppe vereinheitlicht. Dadurch reserviert Bokeh
nicht mehr die Höhe der größten 46-Unternehmens-Rangliste für kürzere Charts;
die zuvor sichtbaren großen Leerflächen entfallen.

## Logo-System

Das vereinfachte Logo verbindet die Friedenstaube bewusst mit einem
Stacheldraht-Zweig. Die Bedeutung entsteht aus diesem Gegensatz und hängt
nicht davon ab, dass die Bildmarke selbst schwarz dargestellt wird.

Für die dunkle Benutzeroberfläche wird deshalb die weiße, transparente
Negativvariante eingesetzt. Sie erhält Silhouette, Wortmarke und den feinen
Stacheldraht-Kontrast, ohne eine helle rechteckige Fläche in das Interface zu
setzen.

- `assets\black_doves_logo.png`: aktives Logo für alle generierten HTMLs
- `assets\black_doves_logo_dark.png`: identische benannte Dark-Mode-Variante
- `assets\black_doves_logo_light.png`: schwarze transparente Variante für helle Flächen
- `assets\black_doves_logo_print.png`: schwarze Variante auf Weiß für Druck/Export
- `assets\black_doves_logo_legacy.png`: vorheriges Logo, nur als Archivkopie

## Master-Datei in VS Code bauen

Im Projektordner in PowerShell ausführen:

```powershell
.\.venv\Scripts\python.exe -m src.build_black_doves_master
```

_Linux/macOS equivalent (after `source .venv/bin/activate`):_

```bash
.venv/bin/python -m src.build_black_doves_master
```

Der Befehl regeneriert zunächst alle fünf interaktiven Einzelberichte im
Dark-Theme, aktualisiert danach die Narrativtabellen und erstellt zuletzt die
Master-Datei. Dadurch bleibt das Erscheinungsbild auch nach späteren
Datenaktualisierungen konsistent.

## Firmenankündigungen ergänzen

Die Importvorlage liegt unter
`data\import_templates\company_announcements_template.csv`. Jede Zeile muss
einem `company_id` aus `config\company_market_universe.csv` zugeordnet sein und
eine prüfbare HTTP(S)-Quelle enthalten. `company_name`, Ticker und eine
deterministische ID werden bei Bedarf ergänzt; unbekannte Unternehmen,
abweichende Metadaten, ungültige Datumswerte oder ID-Kollisionen werden
abgewiesen.

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

Der Import ist idempotent: dieselbe unveränderte Zeile kann erneut eingelesen
werden, ohne ein Duplikat zu erzeugen. Neue Datensätze gelten erst nach
inhaltlicher Quellenprüfung als belastbar. Felddefinitionen, Ansichtslogik und
Abdeckungsregeln stehen in
`BLACK_DOVES_COMPANY_ANNOUNCEMENTS_README.md`.

## Nachrichten-Connector

Der Registry-Eintrag `DE_TAGESSCHAU_NEWS_RSS` ist technisch vorbereitet, aber
bewusst inaktiv. Der aktuelle RSS-Feed ersetzt kein historisches Archiv für
den festen Untersuchungszeitraum. Ein leerer Import darf daher nicht als
„keine Berichterstattung“ interpretiert werden.

Ein bewusster Testabruf kann so erfolgen:

```powershell
.\.venv\Scripts\python.exe -m src.collect_media_documents `
  --source-id DE_TAGESSCHAU_NEWS_RSS `
  --query "Iran Israel USA" `
  --start-date 2026-01-01 `
  --end-date 2026-08-18
```

_Linux/macOS equivalent (after `source .venv/bin/activate`):_

```bash
.venv/bin/python -m src.collect_media_documents \
  --source-id DE_TAGESSCHAU_NEWS_RSS \
  --query "Iran Israel USA" \
  --start-date 2026-01-01 \
  --end-date 2026-08-18
```

Vor der Verwendung in der schriftlichen Auswertung sind Outlet-Auswahl,
Archivzugang und Stichprobenregel zu dokumentieren.

## TV-Transkript-Importer

Die Vorlage liegt unter
`data\\import_templates\\broadcast_transcripts_template.csv`. Die
Beispielzeile muss gelöscht und durch rechtmäßig bezogene Transkripte ersetzt
werden. Pflichtfelder:

- `published_at`: ISO-8601, möglichst mit Zeitzone
- `programme`: Name der Sendung
- `title`: Beitragstitel
- `transcript`: vollständiger vorhandener Transkripttext
- `url`: nachvollziehbare Quellenadresse
- `presenter`: optional

Import:

```powershell
.\.venv\Scripts\python.exe -m src.collect_media_documents `
  --source-id DE_TAGESSCHAU_20H_TRANSCRIPTS `
  --input-file data\imports\tagesschau_20h_transcripts.csv `
  --query "Iran Israel USA" `
  --start-date 2026-01-01 `
  --end-date 2026-08-18
```

_Linux/macOS equivalent (after `source .venv/bin/activate`):_

```bash
.venv/bin/python -m src.collect_media_documents \
  --source-id DE_TAGESSCHAU_20H_TRANSCRIPTS \
  --input-file data/imports/tagesschau_20h_transcripts.csv \
  --query "Iran Israel USA" \
  --start-date 2026-01-01 \
  --end-date 2026-08-18
```

Der Importer umgeht keine Zugangsschranken und lädt keine Videos herunter.

## Kategorien prüfen

Die automatische Zuordnung ist nur ein deterministischer Vorschlag. Sie ist
kein ML-Ergebnis und keine fertige inhaltliche Codierung. Die Primärauswertung
darf nur manuell geprüfte Dokumente verwenden.

1. `data\\analysis\\narrative_documents.csv` öffnen und `document_id`, Text,
   vorgeschlagene Kategorien sowie Frames prüfen.
2. Pro geprüftem Dokument eine JSON-Datei in
   `data\\validated\\narrative_reviews` anlegen. Die Vorlage
   `review_template.json.example` zeigt das Schema.
3. `src.build_black_doves_master` erneut ausführen.

Zulässige Hauptkategorien:

- `MILITARY_OPERATIONS_SECURITY`
- `DIPLOMACY_MEDIATION_DEESCALATION`
- `PROCUREMENT_MILITARY_CAPABILITY`
- `SANCTIONS_ECONOMIC_MEASURES`
- `ENERGY_TRADE_DEPENDENCY`
- `HUMANITARIAN_CIVILIAN_IMPACT`
- `DOMESTIC_POLITICS_LAW_BUDGET`

## Methodische Grenzen

- Fehlende Nachrichten- oder TV-Korpora bleiben `MISSING`, nicht null.
- Vorschlagskategorien werden im Dashboard ausdrücklich als solche markiert.
- Staatliche Stellen, Nachrichten und TV sind getrennte Quellenebenen.
- Mehrfachkategorien sind zulässig; Anteile benötigen einen klaren Nenner.
- Die Ansichten zeigen zeitliche Zusammenhänge und deskriptive Muster, keine
  Kausalität.
- Der Hauptsample umfasst 46 Unternehmen; Volkswagen bleibt eine nachträglich
  dokumentierte Ergänzung. Die konfirmatorische Stichprobe umfasst 8 Firmen.
- `Source_Raw` bleibt unangetastet; die Python-Pipeline liest den
  `Company_Master`-Stand beziehungsweise dessen exportierte Analysedateien.

## Relevante Dateien

- `BLACK_DOVES_REPORT_VIEW_AUDIT.md`: Alt-/Neu-Abgleich aller Ansichten und Unternehmensdaten
- `src/master_dashboard.py`: Aufbau der zentralen HTML
- `src/build_black_doves_master.py`: reproduzierbarer Gesamt-Build
- `src/visualize_company_announcements.py`: Firmen-, Markt-, Ankündigungs- und Konfliktansicht
- `src/import_company_announcements.py`: validierter, idempotenter CSV-Import
- `data/reference/company_announcements.csv`: kuratiertes Firmenankündigungsregister
- `src/collect_media_documents.py`: Connector-CLI
- `config/media_sources.json`: Quellenregister und Abdeckungsgrenzen
- `src/services/narrative_classifier.py`: feste Taxonomie und Vorschläge
- `src/services/narrative_corpus_builder.py`: Korpus, Reviews und Coverage
- `data/analysis/narrative_coverage.csv`: dokumentierter Abdeckungsstatus
