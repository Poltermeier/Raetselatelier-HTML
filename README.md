# Simon's Rätselatelier im Browser

Webport von [Raetselkalender-Generator](https://github.com/Poltermeier/Raetselkalender-Generator/tree/acf15a5799e1503f36a30726b63a7b60b43d378a) mit **89 Rätsel- und Spieltypen**. Für die Rätsel gibt es die Stufen *Mittel* und *Schwer*. Hearts, Schach, beide Vier-gewinnt-Varianten, Symbolduell, beide Farbfolge-Spiele und die beiden Labyrinthe stehen im Menü *Längere Denkspiele*. Die Bedienung entspricht der Desktop-App, mit Rätselauswahl, Regeln und Spielfeld, Notizen, Rückgängig, Lösungsansicht und JSON-Export ohne Lösung. Die Einstellungen für Ton und Farbblindheitsmodus bleiben im jeweiligen Browser gespeichert.

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

Für die **Sonderkommission Nordhafen** ermittelst du zu 20 Personen mit Namen und Beruf. Das Raster ist alphabetisch sortiert, mit Spalten A–D und Reihen 1–5. Am Anfang ist eine Spur offen. Jede eindeutig belegte Zuordnung öffnet eine wahre Aussage. Spuren beziehen sich unter anderem auf Berufe, Positionen, gemeinsame Nachbarn, Ränder und lückenlose Gruppen. Nachbarn können auch diagonal sitzen. Verbundene Gruppen setzen sich aus waagerechten und senkrechten Schritten zusammen.

**Begriffe** erklärt die räumlichen Regeln im Spiel. **Tipp** markiert zuerst die Spuren, die einen Schluss erlauben. Beim zweiten Drücken wird die zuordenbare Person hervorgehoben. Die Fälle, Figuren und Spuren entstehen im Atelier. [Spielregeln von Clues by Sam](https://cluesbysam.com/)

## Karten- und Brettspiele

- **Mahjong** ist die Solitärvariante mit 144 Steinen. Du räumst freie Paare ab. Blumen und Jahreszeiten bilden jeweils eigene Paargruppen. Beide Layouts haben einen geprüften Räumweg.
- **FreeCell** verwendet ein Standarddeck mit vier freien Zellen und vier Zielstapeln. Die freien Zellen und leeren Spalten bestimmen die maximal verschiebbare Kartenfolge. Die Austeilungen enthalten einen geprüften Lösungsweg.
- **Hearts** spielt sich gegen drei unabhängige Gegner. Wähle vor dem Start *Leicht*, *Mittel*, *Schwer* oder *Experte*. Jeder Gegner erhält seine eigene Hand, seine ausgetauschten Karten und die sichtbaren Spielinformationen. *Experte* testet mögliche Verteilungen der unbekannten Karten. Es gelten Kartenweitergabe, Bedienpflicht, die Herz- und Pik-Dame-Punkte und das Spielende ab 100 Punkten.
- **Schach** lässt dich als Weiß oder Schwarz gegen Stockfish mit acht Elo-Einstellungen von 1320 bis 3000 spielen. Nach Partieende öffnet *Partie analysieren* die Zugnavigation. Für den angezeigten Zug berechnet Stockfish seine Empfehlung, eine mögliche Fortsetzung und die Bewertungen. Gold markiert den gespielten Zug, Blau eine abweichende Empfehlung.
- **Vier gewinnt** bietet die klassische Variante gegen eine Engine auf vier Stufen. Auf Mittel berücksichtigt die Engine offene Gewinnlinien und Doppeldrohungen. Ein volles Brett ohne Viererreihe ergibt ein Remis.
- **Vier gewinnt - entfernen** bietet die Variante mit herausnehmbaren Kugeln gegen eine Engine auf vier Stufen. Tippe zum Einwerfen auf den Spaltenkopf oder ein freies Feld. Eine eigene Kugel in der untersten Reihe lässt sich direkt antippen und entfernen. Bei gleichzeitig entstehenden Viererreihen gewinnt die ziehende Seite. Dreimal dieselbe Stellung mit demselben Zugrecht ergibt ein Remis.
- **Symbolduell** verwendet 55 runde Karten mit jeweils acht von 57 eigenen Vektorsymbolen. Die Motive variieren in Größe und Drehung. Pro Karte werden mehrere Anordnungen verglichen und die Motive passend zum freien Platz vergrößert. Die Tippflächen bleiben getrennt. Zwei Karten sind offen und teilen genau ein Symbol. Tippe es auf einer der Karten an, damit die nächste Karte eine der beiden ersetzt. Die Deckgröße orientiert sich an der klassischen Ausgabe. [Regeln der klassischen Ausgabe](https://cdn.svc.asmodee.net/production-zygomatic/uploads/2026/01/DOBSPO07EN_RULES_20251210.pdf)
- **Farbfolge** und **Farbfolge Extrem** verwenden vier breite, abgerundete Tasten um den Punktestand beziehungsweise neun Felder im Raster. Jedes Feld hat eine kräftige Farbe und einen eigenen Ton. Die Folge wächst nach jeder richtigen Eingabe. Vor dem ersten Signal jeder Folge gibt es 1,2 Sekunden Vorbereitungszeit. Der Punktestand zählt die vollständig wiedergegebenen Folgen. Der Lautstärkeregler in den Einstellungen steuert auch die Farbtöne.
- **Minotaurus-Labyrinth** führt dich durch ein Labyrinth mit einem Verfolger. Nach einem Zug oder Warten versucht der Minotaurus bis zu zwei Schritte in deine Richtung, waagerecht vor senkrecht.
- **Spiegellabyrinth** steuert zwei Figuren gleichzeitig. Auf dem rechten Brett sind links und rechts gespiegelt. Mauern wirken je Brett, und beide Ziele müssen nach demselben Zug besetzt sein.

Beide Labyrinthe bieten unter **Bauform** Gänge, Verzweigungen und Kammern. **Zufällig** wählt die Bauform aus dem Seed. Eine Breitensuche prüft die Lösbarkeit und liefert auf Wunsch einen Tipp ab der aktuellen Stellung. Zum Steuern kannst du das Steuerkreuz oder die Pfeiltasten verwenden.

## Nonogramme

- **Zahlen Nonogramm** zeigt drei Ziffern in einem 10 × 5-Gitter.
- **Nonogramm - Motiv** zeigt einen Gegenstand in einem Raster mit 11 × 18, 12 × 20, 13 × 22 oder 14 × 24 Feldern. Die 36 eigenen Motive und ihre Spiegelungen sind allein aus den Zeilen- und Spaltenhinweisen lösbar. Falsches Ausmalen und falsche Kreuze kosten jeweils eines von drei Herzen. Ein verlorenes Herz wird grau. Bei null Leben endet die Runde. [Motivliste](raetselkalender/nonogram_images.py)

## Weitere Zahlen- und Drehrätsel

- **Distanz** ordnet sechs oder neun Zahlen so an, dass die Luftlinie zwischen aufeinanderfolgenden Zahlen strikt wächst. Jede erzeugte Anordnung hat genau eine Lösung.
- **Friedman Zahlen** bietet 648 Zielzahlen. Auf *Mittel* sind die Ziele drei- oder vierstellig. Setze ihre Ziffern in Reihenfolge zu einer Rechnung zusammen. Die Zahlenbasis stammt aus der OEIS-Tabelle von Javier Cobos del Alamo. Der Generator leitet eigene Beispielausdrücke her und prüft sie exakt. [Zahlenfolge A080035 bei OEIS](https://oeis.org/A080035) · [Ausdrücke erzeugen](tools/build_friedman.py)
- **Summe Produkt** verwendet gleiche Zeilensummen, gleiche Spaltenprodukte und lauter verschiedene positive Zahlen. Auf *Mittel* gibt es kleine Zahlen und eine Vorgabe je Spalte in einer 2 × 3-Matrix. Auf *Schwer* kommen 2 × 4- und 3 × 3-Matrizen vor.
- **Twiddle** sortiert ein Raster durch Vierteldrehungen. Auf Mittel drehen sich 2 × 2-Blöcke, auf Schwer 3 × 3-Blöcke. Der Lösungsweg lässt sich schrittweise ansehen.
- **Harakiri** trägt die Zahlen 1 bis 8 auf vier Ringen ein. Auf jedem Ring und jedem Durchmesser kommt jede Zahl genau einmal vor.
- **H₂O** verbindet jedes vorgegebene H mit einem benachbarten O. Wähle ein leeres Feld als O und tippe zwei benachbarte H an.
- **Schachaufstellung** platziert fünf Figuren, die einander nicht angreifen. Die Zahlen geben an, wie viele Figuren das jeweilige Feld angreifen.
- **Fillomino** füllt rechteckige Raster mit zusammenhängenden Gruppen. Jede Zahl entspricht der Feldanzahl ihrer Gruppe.

## Weiterentwicklung

`raetselkalender/` enthält die Python-Generatoren, die Prüfverfahren und die Spiellogik. `browser/` verbindet diese mit HTML-Eingaben und der Canvas-Zeichenfläche. Pyodide führt den Python-Code in einem Web Worker aus. Für **Schach - Best move** erzeugt und prüft der Browser die Stellungen mit der WebAssembly-Version von Stockfish 19 Lite. Derselbe Seed kann im Desktop-Stockfish zu einer anderen Schachstellung führen.

Nach Änderungen an den Python-Dateien das Browserarchiv neu erzeugen und mit einchecken.

```sh
python tools/build_runtime.py
```

Die eigenen FreeCell-Austeilungen lassen sich mit `python tools/build_freecell_deals.py` neu erzeugen.

Die mitgelieferten Laufzeiten, ihre Lizenzen und Quellen stehen unter [third_party/NOTICE.md](third_party/NOTICE.md).
