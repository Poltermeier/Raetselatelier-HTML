"""Hint text and checks shared by the assistance controls."""
from .jump_puzzle import shortest_path_graph
from .solver import AllDifferent, Sum, deduce


def wrong_answers(puzzle, answers):
    return {key: value for key, value in answers.items()
            if key in puzzle.solution and key not in puzzle.givens and value != puzzle.solution[key]}


def jump_distances(puzzle):
    view = puzzle.view
    predecessors = [[] for _ in range(view["size"] ** 2)]
    for position in range(len(predecessors)):
        for target in puzzle.targets(position):
            predecessors[target].append(position)
    goal = view["goal"]
    distances, _, _ = shortest_path_graph(predecessors.__getitem__, goal, goal)
    return distances


def model_hint(puzzle, answers):
    """Find a useful deduction without filling a field or reading its answer."""
    model = puzzle.model
    open_keys = set(puzzle.editable).difference(answers)
    if not open_keys:
        return None
    known = puzzle.givens | answers
    result = deduce(model, known, seconds=.6)
    if result.status not in ("solved", "stalled"):
        return None
    for key in model.domains:
        if key in open_keys and len(model.domains[key]) == 1:
            return key, "Der erlaubte Wertebereich dieses Felds hat nur eine Möglichkeit."
    for step in result.steps:
        key = next((key for key in step["removed"] if key in open_keys
                    and len(model.domains[key]) - len(step["removed"][key]) == 1), None)
        if key is None:
            key = next((key for key in step["removed"] if key in open_keys), None)
        if key is None:
            continue
        rule = model.constraints[step["constraint"]]
        if isinstance(rule, Sum):
            if puzzle.view["kind"] == "routes":
                text = f"Zähle an dieser Stelle die gesetzten und freien Kanten. Die Vorgabe verlangt genau {rule.total}."
            else:
                text = f"Diese Gruppe hat die Summe {rule.total}. Prüfe, was nach den bereits feststehenden Werten noch fehlt."
        elif isinstance(rule, AllDifferent):
            used = sorted(value for peer, value in known.items()
                          if peer in rule.keys and value in step["removed"][key])
            text = "Prüfe die Reihe, Spalte oder Gruppe des markierten Feldes."
            if used:
                text += f" Dort sind diese Werte bereits vergeben: {', '.join(map(str, used))}."
            else:
                text += " Bereits verwendete Werte scheiden dort aus."
        elif puzzle.view["kind"] == "routes":
            text = "Prüfe die Anschlüsse am markierten Abschnitt. Welche Kanten müssen frei bleiben, damit der Weg die Regeln erfüllt?"
        elif puzzle.type_id == "nonogramm":
            text = "Vergleiche die möglichen Lagen der Blöcke in der Zeile und Spalte. Überlappende Abschnitte lassen sich festlegen."
        else:
            text = "Lege für die markierte Stelle mögliche Werte nebeneinander und streiche alle, die den angrenzenden Vorgaben widersprechen."
        return key, text
    return None


ACTIVITY_HINTS = {
    "sets": "Wähle zwei Karten. Für jedes Merkmal lässt sich daraus ableiten, was die dritte Karte zeigen muss.",
    "mastermind": "Vergleiche zwei Versuche mit möglichst wenigen Änderungen. So lässt sich eingrenzen, welche Farbe oder Position den Unterschied macht.",
    "solitaire": "Plane vom Zielloch rückwärts. Welche beiden Positionen müssen vor dem letzten Sprung besetzt sein?",
    "freecell": "Halte freie Zellen verfügbar. Verschiebe zuerst Karten, die ein Ass oder eine andere niedrige Karte verdecken.",
    "matches": "Prüfe die Ziffern, die sich durch genau ein Segment ändern lassen. Vergleiche danach beide Seiten der Gleichung.",
    "water-sort": "Versuche ein Gefäß zu leeren. Ein freies Gefäß schafft Platz, um verdeckte Farbschichten erreichbar zu machen.",
    "crypto": "Beginne mit kurzen Wörtern und vergleiche wiederkehrende Buchstabenmuster. Dieselbe Ersetzung gilt im ganzen Satz.",
    "target24": "Bilde erst zwei Teilergebnisse. Die Faktorenpaare 2 × 12, 3 × 8 und 4 × 6 geben mögliche Zwischenziele.",
    "pentomino": "Beginne an einer Ecke oder einer schmalen Stelle. Vermeide abgeschlossene Lücken, deren Fläche kein Vielfaches von fünf ist.",
    "row-shift": "Vergleiche das Zielbild mit den äußeren Reihen. Richte zuerst einen kleinen Abschnitt ein, bevor du die Lücke weiterbewegst.",
    "wortspur": "Behalte richtig platzierte Buchstaben und teste eine neue Position für gelb markierte Buchstaben. Achte auf mögliche Wiederholungen.",
    "buchstabenwerkstatt": "Setze den Pflichtbuchstaben zuerst in verschiedene Wortpositionen. Probiere andere Endungen oder Wortformen.",
    "wortring": "Teste den Ring in beiden Richtungen. Ein plausibler Wortanfang muss zu allen übrigen Buchstaben passen.",
    "hearts": "Wenn du die ausgespielte Farbe hast, musst du sie bedienen. Eine niedrige Karte hilft oft, einen Stich mit Strafpunkten zu vermeiden.",
}
