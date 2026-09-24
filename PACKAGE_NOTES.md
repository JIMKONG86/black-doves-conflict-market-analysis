# BLACK DOVES - Hinweise zum bereinigten Abgabepaket

Stand: 24.09.2026

## Enthalten

- reproduzierbarer Python-Quellcode und Abhaengigkeiten;
- 46-Unternehmen-Universum einschliesslich Volkswagen als gesonderter
  Post-hoc-Robustheitsfall;
- oeffentlich weitergebbare Rohdaten sowie Zwischen-, Validierungs-, Referenz-
  und Analysedaten;
- 361 erfolgreich ausgefuehrte Unit- und Regressionstests;
- ein reproduzierbarer Build fuer die offlinefaehigen HTML-Ausgaben;
- zentrale Zielausgabe: `output/black_doves_complete_analysis.html`.

## Bewusst nicht enthalten

- virtuelle Python-Umgebungen und installierte Drittanbieterpakete;
- Git-Historie, Editorprofile, Caches, Logs und temporaere Testausgaben;
- lokale `.env`-Dateien, Zugangsdaten oder Tokens;
- veraltete Dubletten und verschachtelte Zwischenarchive.
- der lizenzierte ACLED-Rohdownload und generierte HTML-Dateien; siehe
  `DATA_AVAILABILITY.md`.

## Reproduzierbarkeit

Die vollstaendigen Befehle sowie die Datenstruktur und methodischen Grenzen
stehen in `README.md`. Fuer den lokalen Neubau werden eine frische virtuelle
Umgebung und `requirements.txt` verwendet. Externe Datenabrufe sind fuer den
Neubau des enthaltenen Reports nicht erforderlich.
