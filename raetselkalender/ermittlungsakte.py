"""Generate cases with independent evidence and a complete deduction proof."""
from itertools import combinations
import random

from .puzzle import Puzzle
from .solver import Model, Sum, Table, deduce

MODE = "ermittlungsakte"
ROLES = ("Unbeteiligt", "Eingeweiht")
NAMES = (
    "Ada", "Aylin", "Ben", "Clara", "Daria", "David", "Ella", "Emil", "Fatma",
    "Felix", "Greta", "Hana", "Ida", "Jana", "Jari", "Jona", "Kaya", "Lara",
    "Lea", "Levi", "Lina", "Luis", "Mara", "Mert", "Mia", "Mika", "Nils",
    "Noah", "Nora", "Omar", "Ravi", "Rosa", "Sami", "Tara", "Theo", "Timo",
    "Uma", "Vera", "Yuna", "Zoe",
)
CASES = (
    ("Jemand bereitete heimlich ein Überraschungskonzert vor.", ("Bühne", "Studio", "Werkstatt")),
    ("Ein Geheimplan für einen neuen Dachgarten ist aufgetaucht.", ("Archiv", "Innenhof", "Dach")),
    ("Eine Gruppe organisierte im Stillen eine nächtliche Ausstellung.", ("Museum", "Atelier", "Depot")),
    ("Eine Wandergruppe hat eine Überraschung am Ziel vorbereitet.", ("Hütte", "Brücke", "Lichtung")),
    ("Für das Stadtfest wurde im Geheimen eine Zeitkapsel befüllt.", ("Bibliothek", "Rathaus", "Marktplatz")),
    ("Ein Nachbarschaftsteam plante heimlich ein Straßenkino.", ("Kiosk", "Park", "Vereinsheim")),
)


def ermittlungsakte(seed, difficulty):
    rng = random.Random(seed)
    cols = 3 if difficulty == "mittel" else 4
    story, rooms = rng.choice(CASES)
    keys = tuple(rng.sample(NAMES, 3 * cols))
    areas = tuple(keys[start:start + cols] for start in range(0, len(keys), cols))
    solution = {}
    for area in areas:
        count = rng.randint(1, cols - 1)
        informed = set(rng.sample(area, count))
        solution.update({key: int(key in informed) for key in area})
    start = rng.choice(keys)
    givens = {start: solution[start]}
    model = Model({key: {0, 1} for key in keys}, [])
    clues = [dict(text=f"Bestätigter Status: {start} ist {ROLES[givens[start]].lower()}.", people=[start])]

    def add_clue(rule, text):
        model.constraints.append(rule)
        clues.append(dict(text=text, people=list(rule.keys)))

    for room, people in zip(rooms, areas):
        count = sum(solution[key] for key in people)
        phrase = "Genau eine Person ist eingeweiht." if count == 1 else f"Genau {count} Personen sind eingeweiht."
        add_clue(Sum(people, count), f"{room}: {phrase}")

    cross_area_pairs = [pair for pair in combinations(keys, 2)
                        if not any(set(pair).issubset(area) for area in areas)]
    triples = [triple for triple in combinations(keys, 3)
               if len({solution[key] for key in triple}) == 2] if difficulty == "schwer" else []

    # Each added relation lets the player transfer established information to someone new.
    while True:
        proof = deduce(model, givens, trace=False)
        unresolved = {key for key, options in proof.domains.items() if len(options) != 1}
        if not unresolved:
            break
        usable_triples = [triple for triple in triples if sum(key in unresolved for key in triple) == 1]
        if usable_triples:
            people = rng.choice(usable_triples)
            count = sum(solution[key] for key in people)
            phrase = "ist genau eine Person eingeweiht." if count == 1 else "sind genau zwei Personen eingeweiht."
            add_clue(Sum(people, count),
                     f"Von {people[0]}, {people[1]} und {people[2]} {phrase}")
        else:
            people = rng.choice([pair for pair in cross_area_pairs if sum(key in unresolved for key in pair) == 1])
            first, second = people
            if solution[first] == solution[second]:
                add_clue(Table(people, ((0, 0), (1, 1))), f"{first} und {second} haben denselben Status.")
            else:
                add_clue(Sum(people, 1), f"Von {first} und {second} ist genau eine Person eingeweiht.")

    puzzle = Puzzle(MODE, "Ermittlungsakte",
                    f"{story} Finde heraus, wer eingeweiht war. Blättere durch die Spuren "
                    "und markiere jede Person als eingeweiht oder unbeteiligt. Prüfe am Ende deine Akte.",
                    model, solution, givens,
                    dict(kind="activity", mode=MODE, rooms=rooms, people=areas, clues=clues), seed, difficulty)
    puzzle.certify()
    return puzzle
