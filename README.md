# Simon's Rätselatelier im Browser

Webport von [Raetselkalender-Generator](https://github.com/Poltermeier/Raetselkalender-Generator/tree/acf15a5799e1503f36a30726b63a7b60b43d378a) mit **73 Rätsel- und Spieltypen**. Für die Rätsel gibt es die Stufen *Mittel* und *Schwer*. Hearts und Schach stehen im Menü *Längere Denkspiele*. Die Bedienung entspricht der Desktop-App, mit Rätselauswahl, Regeln und Spielfeld, Notizen, Rückgängig, Lösungsansicht und JSON-Export ohne Lösung. Die Einstellungen für Ton und Farbblindheitsmodus bleiben im jeweiligen Browser gespeichert.

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
- **Gruppen** zeigt 16 Wörter auf einem Raster. Wähle jeweils vier Wörter, die zu demselben Thema gehören, und prüfe deine Auswahl. Der Wortkatalog enthält 98 Kategorien für „Mittel“ und 167 für „Schwer“. Dazu gehören Alltagsbegriffe, Wortzusammensetzungen, Fachbegriffe und Reime. Auf „Schwer“ können Wörter in mehrere Kategorien passen. Zu jedem Rätsel prüft der Generator, dass beide Wortkataloge zusammen genau eine vollständige Einteilung erlauben.

Die Wortdaten sind offline verfügbar. [Quellen, Lizenz und Erstellung der Wortliste](third_party/NOTICE.md#german-word-puzzles)

## Ermittlungsakte

Auf einem Raster mit fünf Spalten und vier Reihen ermittelst du zu 20 Personen. Am Anfang steht eine einzige Spur offen. Wähle eine Person und ordne ihr „Schuldig“ oder „Unschuldig“ zu. Das Spiel bestätigt eine Zuordnung erst, wenn die freigegebenen Spuren genau diesen Status erzwingen. Jede bestätigte Person öffnet eine eigene Aussage, auf die du über ihre Kachel oder über die Spurnavigation zugreifen kannst. Die Spuren beziehen sich unter anderem auf Reihen, Spalten, gemeinsame Nachbarn und lückenlose Gruppen. Direkte Nachbarn sitzen waagerecht oder senkrecht nebeneinander. Auf „Schwer“ musst du mehrfach Hinweise kombinieren. Dazu gehören auch gerade und ungerade Anzahlen. Alle Fälle lassen sich Schritt für Schritt ohne Raten lösen. Die Fälle sind eigene Rätsel des Ateliers, inspiriert vom Ermittlungsprinzip von [Clues by Sam](https://cluesbysam.com).

## Karten- und Brettspiele

- **Mahjong** ist die Solitärvariante mit 144 Steinen. Du räumst freie Paare ab. Blumen und Jahreszeiten bilden jeweils eigene Paargruppen. Beide Layouts haben einen geprüften Räumweg.
- **FreeCell** verwendet ein Standarddeck mit vier freien Zellen und vier Zielstapeln. Die freien Zellen und leeren Spalten bestimmen die maximal verschiebbare Kartenfolge. Die Austeilungen enthalten einen geprüften Lösungsweg.
- **Hearts** spielt sich gegen drei unabhängige Gegner. Wähle vor dem Start *Leicht*, *Mittel*, *Schwer* oder *Experte*. Jeder Gegner erhält seine eigene Hand, seine ausgetauschten Karten und die sichtbaren Spielinformationen. *Experte* testet mögliche Verteilungen der unbekannten Karten. Es gelten Kartenweitergabe, Bedienpflicht, die Herz- und Pik-Dame-Punkte und das Spielende ab 100 Punkten.
- **Schach** lässt dich als Weiß oder Schwarz gegen Stockfish mit acht Elo-Einstellungen von 1320 bis 3000 spielen. Nach Partieende öffnet *Partie analysieren* die Zugnavigation. Für den angezeigten Zug berechnet Stockfish seine Empfehlung, eine mögliche Fortsetzung und die Bewertungen. Gold markiert den gespielten Zug, Blau eine abweichende Empfehlung.

## Weiterentwicklung

`raetselkalender/` enthält die Python-Generatoren, die Prüfverfahren und die Spiellogik. `browser/` verbindet diese mit HTML-Eingaben und der Canvas-Zeichenfläche. Pyodide führt den Python-Code in einem Web Worker aus. Schachrätsel werden weiterhin frisch erzeugt und geprüft. Der Browser verwendet Stockfish 19 Lite als WebAssembly-Version. Derselbe Seed kann im Desktop-Stockfish zu einer anderen Schachstellung führen.

Nach Änderungen an den Python-Dateien das Browserarchiv neu erzeugen und mit einchecken.

```sh
python tools/build_runtime.py
```

Die eigenen FreeCell-Austeilungen lassen sich mit `python tools/build_freecell_deals.py` neu erzeugen.

Die mitgelieferten Laufzeiten, ihre Lizenzen und Quellen stehen unter [third_party/NOTICE.md](third_party/NOTICE.md).
