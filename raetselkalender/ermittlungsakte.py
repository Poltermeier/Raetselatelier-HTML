"""Generate and check cases with evidence that opens one statement at a time."""
from dataclasses import dataclass
import random

from .puzzle import LogicalProofMissing, Puzzle
from .solver import Constraint, Model, SearchLimit, Sum, Table, deduce, solve

MODE = "ermittlungsakte"
ROWS, COLS = 4, 5
ROLES = ("Unschuldig", "Schuldig")
NAMES = (
    "Ada", "Aylin", "Ben", "Clara", "Daria", "David", "Ella", "Emil", "Fatma",
    "Felix", "Greta", "Hana", "Ida", "Jana", "Jari", "Jona", "Kaya", "Lara",
    "Lea", "Levi", "Lina", "Luis", "Mara", "Mert", "Mia", "Mika", "Nils",
    "Noah", "Nora", "Omar", "Ravi", "Rosa", "Sami", "Tara", "Theo", "Timo",
    "Uma", "Vera", "Yuna", "Zoe",
)
CASES = (
    ("Die Plakate für ein Konzert sind verschwunden.", ("Bühne", "Studio", "Werkstatt", "Foyer")),
    ("Die Entwürfe für einen Dachgarten wurden heimlich vertauscht.", ("Archiv", "Innenhof", "Dach", "Gewächshaus")),
    ("Aus einer Ausstellung fehlt das Modell des alten Rathauses.", ("Museum", "Atelier", "Depot", "Kasse")),
    ("Jemand hat die Wegweiser für den Wandertag umgestellt.", ("Hütte", "Brücke", "Lichtung", "Aussichtspunkt")),
    ("Kurz vor dem Stadtfest wurde eine Zeitkapsel entwendet.", ("Bibliothek", "Rathaus", "Marktplatz", "Innenhof")),
    ("Die Filmrolle für das Straßenkino wurde gegen eine leere ausgetauscht.", ("Kiosk", "Park", "Vereinsheim", "Lager")),
)


@dataclass(frozen=True)
class Clue:
    text: str
    rule: Constraint

    def export(self):
        return dict(text=self.text, people=list(self.rule.keys))


@dataclass(kw_only=True)
class CasePuzzle(Puzzle):
    opening: Clue
    statements: dict[str, Clue]

    def revealed_clues(self, confirmed):
        return [(None, self.opening), *((name, self.statements[name]) for name in confirmed)]

    def visible_model(self, confirmed):
        return Model(self.model.domains, [clue.rule for _, clue in self.revealed_clues(confirmed)])

    def classify(self, name, value, confirmed):
        """Accept a role only when every assignment consistent with the open clues requires it."""
        if name in confirmed or name not in self.model.domains or type(value) is not int or value not in (0, 1):
            return "invalid"
        visible = self.visible_model(confirmed)
        proof = deduce(visible, trace=False)
        if proof.status not in ("solved", "stalled"):
            return "unproven"
        options = proof.domains[name]
        if len(options) == 1:
            return "correct" if value in options else "wrong"
        try:
            # Overlapping clues can force a role even when applying each rule alone stalls.
            proposed = solve(visible, {name: value}, limit=1, seconds=1).solutions
            opposite = solve(visible, {name: 1 - value}, limit=1, seconds=1).solutions
        except SearchLimit:
            return "unproven"
        if proposed and opposite:
            return "undetermined"
        if proposed:
            return "correct"
        return "wrong" if opposite else "unproven"

    def certify_progression(self, order):
        if len(order) != len(self.model.domains) or set(order) != self.model.domains.keys():
            raise LogicalProofMissing("Die Folge der Aussagen erfasst nicht alle Personen.")
        self.logical_steps = []
        confirmed = []
        for name in order:
            role = self.solution[name]
            if self.classify(name, role, confirmed) != "correct":
                raise LogicalProofMissing("Der Fall lässt sich mit den freigegebenen Spuren nicht vollständig lösen.")
            self.logical_steps.append(dict(rule="revealed_clues", person=name, value=role))
            confirmed.append(name)
        if solve(self.model, limit=2).solutions != [self.solution]:
            raise LogicalProofMissing("Die vollständige Akte hat keine eindeutige Lösung.")
        self.analysis.update(unique=True, logical_solvable=True, logical_method="progressive_evidence",
                             logical_step_count=len(confirmed))

    def export(self, include_solution=False):
        data = super().export(include_solution)
        if include_solution:
            data["statements"] = {name: clue.export() for name, clue in self.statements.items()}
        return data


def comparison(first, second, solution):
    people = first, second
    if solution[first] == solution[second]:
        return Clue(f"{first} und {second} haben denselben Status.", Table(people, ((0, 0), (1, 1))))
    return Clue(f"Von {first} und {second} ist genau eine Person schuldig.", Sum(people, 1))


def counted(people, solution, *, room=None):
    total = sum(solution[name] for name in people)
    if room:
        lead = f"Auf der Liste für „{room}“"
    else:
        names = " und ".join(people) if len(people) == 2 else f"{', '.join(people[:-1])} und {people[-1]}"
        lead = f"Von {names}"
    if total == 0:
        phrase = "ist niemand schuldig."
    elif total == 1:
        phrase = "ist genau eine Person schuldig."
    else:
        phrase = f"sind genau {('zwei' if total == 2 else total)} Personen schuldig."
    return Clue(f"{lead} {phrase}", Sum(people, total))


def ermittlungsakte(seed, difficulty):
    rng = random.Random(seed)
    story, rooms = rng.choice(CASES)
    keys = tuple(rng.sample(NAMES, ROWS * COLS))
    areas = tuple(keys[start:start + COLS] for start in range(0, len(keys), COLS))
    guilty = set(rng.sample(keys, rng.randint(8, 12)))
    solution = {name: int(name in guilty) for name in keys}
    first, *remaining = rng.sample(keys, len(keys))
    opening = Clue(f"Die Auswertung des Fundbuchs zeigt eindeutig: {first} ist {ROLES[solution[first]].lower()}.",
                   Sum((first,), solution[first]))

    # The first statement gives two independent entry points into the investigation.
    common_role = rng.randrange(2)
    witnesses = tuple(rng.sample([name for name in remaining if solution[name] == common_role], 2))
    remaining = [name for name in remaining if name not in witnesses]
    statements = {first: counted(witnesses, solution)}
    order = [first, *witnesses]

    while remaining:
        left, right = witnesses
        if len(remaining) == 1:
            last = remaining.pop()
            statements[left] = comparison(left, last, solution)
            order.append(last)
            break

        innocent = [name for name in remaining if solution[name] == 0]
        culpable = [name for name in remaining if solution[name] == 1]
        witnesses = tuple(remaining[:2])
        if difficulty == "schwer" and len(remaining) >= 3 and innocent and culpable and rng.random() < .85:
            pair = [rng.choice(innocent), rng.choice(culpable)]
            rng.shuffle(pair)
            witnesses = tuple(pair)
            bridge = rng.choice([name for name in remaining if name not in witnesses])
            # The pair and triple totals together determine the third person. Their statement resolves the pair.
            statements[left] = counted(witnesses, solution)
            statements[right] = counted((*witnesses, bridge), solution)
            statements[bridge] = comparison(bridge, witnesses[0], solution)
            remaining.remove(bridge)
            order.append(bridge)
        elif difficulty == "schwer":
            statements[left] = comparison(*witnesses, solution)
            statements[right] = comparison(right, witnesses[0], solution)
        elif rng.random() < .5:
            statements[left] = counted((left, right, witnesses[0]), solution)
            statements[right] = comparison(right, witnesses[1], solution)
        else:
            statements[left] = comparison(left, witnesses[0], solution)
            statements[right] = comparison(right, witnesses[1], solution)
        remaining = [name for name in remaining if name not in witnesses]
        order.extend(witnesses)

    for room, area in zip(rooms, areas):
        for name in area:
            if name not in statements:
                statements[name] = counted(area, solution, room=room)

    model = Model({name: {0, 1} for name in keys}, [opening.rule, *(clue.rule for clue in statements.values())])
    rules = (f"{story} Wähle eine Person und ordne ihr den Status „Schuldig“ oder „Unschuldig“ zu. "
             "Der Status muss eindeutig aus den offenen Spuren folgen. Jede bestätigte Zuordnung öffnet "
             "eine Aussage dieser Person.")
    puzzle = CasePuzzle(MODE, "Ermittlungsakte", rules, model, solution, {},
                        dict(kind="activity", mode=MODE, rooms=rooms, people=areas, clues=[opening.export()]),
                        seed, difficulty, opening=opening, statements=statements)
    puzzle.certify_progression(order)
    return puzzle
