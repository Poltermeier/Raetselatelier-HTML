# Simon's Rätselatelier im Browser

Webport von [Raetselkalender-Generator](https://github.com/Poltermeier/Raetselkalender-Generator/tree/acf15a5799e1503f36a30726b63a7b60b43d378a) mit **69 Rätseltypen** und den Schwierigkeitsstufen *Mittel* und *Schwer*. Die Bedienung entspricht der Desktop-App, mit Rätselauswahl, Regeln und Spielfeld, Notizen, Rückgängig, Lösungsansicht und JSON-Export ohne Lösung. Die Einstellungen für Ton und Farbblindheitsmodus bleiben im jeweiligen Browser gespeichert.

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

- **Wordle** gibt nach jedem Versuch Rückmeldung zur Position der Buchstaben. Auf „Mittel“ suchst du ein Fünf-Buchstaben-Wort in sechs Versuchen. Auf „Schwer“ sind es sechs Buchstaben in fünf Versuchen. Die Lösungen stammen überwiegend aus gängigen Grundformen. Als Versuche gelten auch belegte gebeugte Formen.
- **Spelling Bee** ordnet acht Buchstaben um den Pflichtbuchstaben an. Jeder Buchstabe darf pro Wort einmal vorkommen. Das Ziel sind acht Wörter auf „Mittel“ und zwölf auf „Schwer“. Der Wortschatz umfasst auch belegte Plurale und andere gebeugte Formen.
- **Wortring** nennt ein Thema. Man kann bei jedem Feld anfangen und in beide Richtungen lesen. Alle Felder müssen genau einmal verwendet werden. Auf „Schwer“ haben die Wörter elf bis 16 Buchstaben.
- **Gruppen** zeigt 16 Wörter auf einem Raster. Wähle jeweils vier Wörter, die zu demselben Thema gehören, und prüfe deine Auswahl. Auf „Schwer“ können Wörter in mehrere Kategorien passen. Zu jedem Rätsel prüft der Generator, dass die im Wortkatalog erfassten Kategorien genau eine vollständige Einteilung erlauben.

Die Wortdaten sind offline verfügbar. [Quellen, Lizenz und Erstellung der Wortliste](third_party/NOTICE.md#german-word-puzzles)

## Ermittlungsakte

Auf einem Raster mit fünf Spalten und vier Reihen ermittelst du zu 20 Personen. Am Anfang steht eine einzige Spur offen. Wähle eine Person und ordne ihr „Schuldig“ oder „Unschuldig“ zu. Das Spiel bestätigt eine Zuordnung erst, wenn die freigegebenen Spuren genau diesen Status erzwingen. Jede bestätigte Person öffnet eine eigene Aussage, auf die du über ihre Kachel oder über die Spurnavigation zugreifen kannst. „Schwer“ kombiniert mehrere Aussagen, um weitere Personen zu bestimmen. Alle Fälle lassen sich Schritt für Schritt ohne Raten lösen. Die Fälle sind eigene Rätsel des Ateliers, inspiriert vom Ermittlungsprinzip von [Clues by Sam](https://cluesbysam.com).

## Weiterentwicklung

`raetselkalender/` enthält die Python-Generatoren, die Prüfverfahren und die Spiellogik. `browser/` verbindet diese mit HTML-Eingaben und der Canvas-Zeichenfläche. Pyodide führt den Python-Code in einem Web Worker aus. Schachrätsel werden weiterhin frisch erzeugt und geprüft. Der Browser verwendet Stockfish 19 Lite als WebAssembly-Version. Derselbe Seed kann im Desktop-Stockfish zu einer anderen Schachstellung führen.

Nach Änderungen an den Python-Dateien das Browserarchiv neu erzeugen und mit einchecken.

```sh
python tools/build_runtime.py
```

Die mitgelieferten Laufzeiten, ihre Lizenzen und Quellen stehen unter [third_party/NOTICE.md](third_party/NOTICE.md).
