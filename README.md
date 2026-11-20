# Simon's Rätselatelier im Browser

Webport von [Raetselkalender-Generator](https://github.com/Poltermeier/Raetselkalender-Generator/tree/acf15a5799e1503f36a30726b63a7b60b43d378a) mit **67 Rätseltypen** und den Schwierigkeitsstufen *Mittel* und *Schwer*. Die Bedienung entspricht der Desktop-App, mit Rätselauswahl, Regeln und Spielfeld, Notizen, Rückgängig, Lösungsansicht und JSON-Export ohne Lösung. Die Einstellungen für Ton und Farbblindheitsmodus bleiben im jeweiligen Browser gespeichert.

## Lokal starten

Das Repository herunterladen oder klonen und den folgenden Befehl im Projektordner ausführen. Der Start benötigt Python 3 ohne Zusatzpakete und öffnet das Atelier unter <http://127.0.0.1:8750/>. Unter Windows funktioniert auch `py start_local.py`.

```sh
python start_local.py
```

Nach dem Download läuft das Atelier offline. Es lädt die Rätsel-Engine und alle weiteren Dateien vom eigenen Rechner. Alternativ kann ein beliebiger statischer Webserver den Projektordner bereitstellen. Der direkte Aufruf per Doppelklick auf `index.html` ist wegen der Browserregeln für Web Worker ungeeignet.

## Online spielen

Das Rätselatelier ist über Github Pages auch online verfügbar. Kein Download notwendig. Dies ermöglicht das nutzen auch auf Tablets, Smartphones etc. 

Link: https://poltermeier.github.io/Raetselatelier-HTML/

## Deutsche Worträtsel

- **Wordle** gibt nach jedem Versuch Rückmeldung zur Position der Buchstaben. Auf „Mittel“ suchst du ein Fünf-Buchstaben-Wort in sechs Versuchen. Auf „Schwer“ sind es sechs Buchstaben in fünf Versuchen.
- **Spelling Bee** ordnet acht Buchstaben um den Pflichtbuchstaben an. Jeder Buchstabe darf pro Wort einmal vorkommen. Das Ziel sind acht Wörter auf „Mittel“ und zwölf auf „Schwer“.
- **Wortring** nennt ein Thema. Man kann bei jedem Feld anfangen und in beide Richtungen lesen. Alle Felder müssen genau einmal verwendet werden. Auf „Schwer“ haben die Wörter elf bis 16 Buchstaben.

Die Wortdaten sind offline verfügbar. [Quellen, Lizenz und Erstellung der Wortliste](third_party/NOTICE.md#german-word-puzzles)

## Weiterentwicklung

`raetselkalender/` enthält die Python-Generatoren, die Prüfverfahren und die Spiellogik. `browser/` verbindet diese mit HTML-Eingaben und der Canvas-Zeichenfläche. Pyodide führt den Python-Code in einem Web Worker aus. Schachrätsel werden weiterhin frisch erzeugt und geprüft. Der Browser verwendet Stockfish 19 Lite als WebAssembly-Version. Derselbe Seed kann im Desktop-Stockfish zu einer anderen Schachstellung führen.

Nach Änderungen an den Python-Dateien das Browserarchiv neu erzeugen und mit einchecken.

```sh
python tools/build_runtime.py
```

Die mitgelieferten Laufzeiten, ihre Lizenzen und Quellen stehen unter [third_party/NOTICE.md](third_party/NOTICE.md).
