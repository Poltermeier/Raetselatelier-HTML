"""Generate and check cases with evidence that opens one statement at a time."""
from dataclasses import dataclass
import random

from .case_clues import COLUMNS, Clue, consequence, paired_counts, parity_clue, position_clues
from .puzzle import LogicalProofMissing, Puzzle
from .solver import Model, SearchLimit, Sum, deduce, solve

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


def combined_clues(scopes, known, solution, singles, used, visible, rng, *, allow_parity):
    counts = list(paired_counts(scopes, known, solution))
    parities = []
    if allow_parity:
        for scope in scopes:
            unknown = set(scope.keys).difference(known)
            if len(unknown) == 2:
                parity = parity_clue(scope, sum(solution[name] for name in scope.keys))
                for clue, forced in singles:
                    if len(forced & unknown) == 1:
                        parities.append((parity, clue, forced | unknown))
    rng.shuffle(counts)
    rng.shuffle(parities)
    options = counts[:30] + parities[:40] if rng.random() < .65 else parities[:40] + counts[:30]
    for first, second, forced in options:
        if first.text in used or second.text in used:
            continue
        alternatives = [Model(visible.domains, [*visible.constraints, clue.rule]) for clue in (first, second)]
        for name in sorted(forced):
            opposite = known | {name: 1 - solution[name]}
            if all(solve(model, opposite, limit=1).solutions for model in alternatives):
                return (first, second), forced
    return None


def ermittlungsakte(seed, difficulty):
    rng = random.Random(seed)
    story, rooms = rng.choice(CASES)
    keys = tuple(rng.sample(NAMES, ROWS * COLS))
    areas = tuple(keys[start:start + COLS] for start in range(0, len(keys), COLS))
    guilty = set(rng.sample(keys, rng.randint(8, 12)))
    solution = {name: int(name in guilty) for name in keys}
    domains = {name: {0, 1} for name in keys}
    first = rng.choice(keys)
    row, col = divmod(keys.index(first), COLS)
    opening = Clue(f"Die Person in Reihe „{rooms[row]}“ und Spalte {COLUMNS[col]} "
                   f"ist {ROLES[solution[first]].lower()}.", Sum((first,), solution[first]), "opening")
    scopes, candidates, neighbors = position_clues(areas, rooms, solution)
    known = {first: solution[first]}
    pending = [first]
    statements = {}
    used = set()
    order = []
    kinds = {}
    hard = difficulty == "schwer"
    combined_count = 0

    while len(known) < len(keys):
        singles = [(clue, consequence(clue, known)) for clue in candidates if clue.text not in used]
        singles = [(clue, forced) for clue, forced in singles if forced]
        combined = None
        if len(pending) >= 2 and (hard or not combined_count):
            visible = Model(domains, [opening.rule, *(clue.rule for clue in statements.values())])
            combined = combined_clues(scopes, known, solution, singles, used, visible, rng, allow_parity=hard)
        if combined:
            clues, forced = combined
            combined_count += 1
        elif singles:
            clue, forced = max(singles, key=lambda option: (
                2 * min(len(option[1]), 3) - kinds.get(option[0].kind, 0) + rng.random() * 2))
            clues = (clue,)
        else:
            # A boundary edge always exists on this connected grid.
            witness, person = rng.choice([(name, other) for name in known for other in neighbors[name]
                                          if other not in known])
            r, c = divmod(keys.index(witness), COLS)
            rr, cc = divmod(keys.index(person), COLS)
            direction = "über" if rr < r else "unter" if rr > r else "links von" if cc < c else "rechts von"
            role = ROLES[solution[person]].lower()
            clues = (Clue(f"Die Person direkt {direction} {witness} ist {role}.",
                          Sum((person,), solution[person]), "position", (witness,)),)
            forced = {person}
        for clue in clues:
            owner = pending.pop(0)
            statements[owner] = clue
            order.append(owner)
            used.add(clue.text)
            kinds[clue.kind] = kinds.get(clue.kind, 0) + 1
        for name in keys:
            if name in forced:
                known[name] = solution[name]
                pending.append(name)

    if combined_count < (2 if hard else 1):
        raise LogicalProofMissing("Die Spuren des Falls greifen zu selten ineinander.")

    unused = [clue for clue in candidates if clue.text not in used]
    rng.shuffle(unused)
    for name, clue in zip(pending, unused[:len(pending)], strict=True):
        order.append(name)
        statements[name] = clue

    model = Model({name: {0, 1} for name in keys}, [opening.rule, *(clue.rule for clue in statements.values())])
    rules = (f"{story} Wähle eine Person und ordne ihr den Status „Schuldig“ oder „Unschuldig“ zu. "
             "Der Status muss eindeutig aus den offenen Spuren folgen. Jede bestätigte Zuordnung öffnet "
             "eine Aussage dieser Person. Direkte Nachbarn sitzen waagerecht oder senkrecht nebeneinander.")
    puzzle = CasePuzzle(MODE, "Ermittlungsakte", rules, model, solution, {},
                        dict(kind="activity", mode=MODE, rooms=rooms, people=areas, clues=[opening.export()]),
                        seed, difficulty, opening=opening, statements=statements)
    puzzle.certify_progression(order)
    return puzzle
