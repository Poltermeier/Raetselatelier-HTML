"""Generate and check cases with evidence that opens one statement at a time."""
from dataclasses import dataclass
import random

from .case_clues import COLUMNS, Clue, consequence, paired_counts, parity_clue, position_clues
from .puzzle import LogicalProofMissing, Puzzle
from .solver import Model, SearchLimit, Sum, deduce, solve

MODE = "ermittlungsakte"
ROWS, COLS = 5, 4
ROLES = ("Unschuldig", "Schuldig")
WOMEN = ("Ada", "Aylin", "Clara", "Daria", "Ella", "Fatma", "Greta", "Hana", "Ida", "Jana", "Kaya", "Lara",
         "Lea", "Lina", "Mara", "Mia", "Nora", "Rosa", "Tara", "Uma", "Vera", "Yuna", "Zoe")
MEN = ("Amir", "Ben", "David", "Emil", "Felix", "Jari", "Jona", "Levi", "Luis", "Malik", "Mert", "Mika",
       "Nils", "Noah", "Omar", "Ravi", "Sami", "Theo", "Timo", "Yusuf")
PROFESSIONS = (
    ("Zoll", "Zöllnerin", "Zöllner"), ("Fotografie", "Fotografin", "Fotograf"),
    ("Kurierdienst", "Kurierin", "Kurier"), ("Technik", "Technikerin", "Techniker"),
    ("Redaktion", "Redakteurin", "Redakteur"), ("Küche", "Köchin", "Koch"),
    ("Lotsendienst", "Lotsin", "Lotse"), ("Fahrdienst", "Fahrerin", "Fahrer"),
    ("Sanitätsdienst", "Sanitäterin", "Sanitäter"), ("Gärtnerei", "Gärtnerin", "Gärtner"),
)
CASES = (
    ("Fracht ohne Papiere", "Am Kai taucht ein Container mit gefälschten Frachtpapieren auf."),
    ("Die Nacht im Depot", "Im Depot der Hafenbahn wurden die Wagennummern in den Lieferbüchern manipuliert."),
    ("Der Schlüssel zum Leuchtturm", "Aus dem Leuchtturmarchiv verschwinden die Originale alter Seekarten."),
    ("Die doppelte Rechnung", "Die Werft hat für dieselbe Reparatur zwei fingierte Rechnungen bezahlt."),
    ("Die stumme Boje", "Kurz vor einer Kontrolle wurden die Wartungsprotokolle der Hafenbojen ausgetauscht."),
    ("Das Siegel aus Blei", "An mehreren Lagerkisten finden sich nachgemachte Zollplomben."),
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

    def next_hint(self, confirmed):
        """Find a provable person and a sufficient subset of the already visible clues."""
        person = next((name for name in self.model.domains if name not in confirmed
                       and self.classify(name, self.solution[name], confirmed) == "correct"), None)
        if person is None:
            return None
        remaining = list(enumerate(self.revealed_clues(confirmed)))
        for indexed in tuple(remaining):
            subset = [item for item in remaining if item != indexed]
            model = Model(self.model.domains, [clue.rule for _, (_, clue) in subset])
            try:
                alternate = solve(model, {person: 1-self.solution[person]}, limit=1, seconds=.3)
            except SearchLimit:
                continue
            if not alternate.solutions:
                remaining = subset
        return person, tuple(index for index, _ in remaining)

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
            if len(unknown) == 2 and len(scope.keys) <= 8:
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
    case_name, story = rng.choice(CASES)
    keys = tuple(sorted(rng.sample(WOMEN + MEN, ROWS * COLS)))
    areas = tuple(keys[start:start + COLS] for start in range(0, len(keys), COLS))
    grouping = rng.sample(PROFESSIONS, 5)
    jobs, job_groups = {}, {}
    people = rng.sample(keys, len(keys))
    for index, (group, female, male) in enumerate(grouping):
        members = tuple(sorted(people[index*4:index*4+4]))
        job_groups[group] = members
        jobs.update((name, female if name in WOMEN else male) for name in members)
    guilty = set(rng.sample(keys, rng.randint(8, 12)))
    solution = {name: int(name in guilty) for name in keys}
    domains = {name: {0, 1} for name in keys}
    first = rng.choice(keys)
    row, col = divmod(keys.index(first), COLS)
    opening = Clue(f"Die Person auf Feld {COLUMNS[col]}{row+1} ist {ROLES[solution[first]].lower()}.",
                   Sum((first,), solution[first]), "opening")
    scopes, candidates, orthogonal = position_clues(areas, job_groups, solution)
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
                2 * min(len(option[1]), 3) - kinds.get(option[0].kind, 0) + rng.random() * 2
                + 2 * (option[0].kind == "profession" and "profession" not in kinds)))
            clues = (clue,)
        else:
            # A boundary edge always exists on this connected grid.
            witness, person = rng.choice([(name, other) for name in known for other in orthogonal[name]
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
    if "profession" not in kinds:
        unused.sort(key=lambda clue: clue.kind != "profession")
    for name, clue in zip(pending, unused[:len(pending)], strict=True):
        order.append(name)
        statements[name] = clue

    model = Model({name: {0, 1} for name in keys}, [opening.rule, *(clue.rule for clue in statements.values())])
    rules = (f"Sonderkommission Nordhafen · {case_name}. {story} "
             "Alle Aussagen sind wahr. Ordne eine Person erst zu, wenn ihre Rolle aus den offenen Spuren feststeht. "
             "Jede bestätigte Zuordnung öffnet eine neue Aussage. Nachbarn zählen auch diagonal.")
    puzzle = CasePuzzle(MODE, "Ermittlungsakte", rules, model, solution, {},
                        dict(kind="activity", mode=MODE, case_name=case_name, people=areas, jobs=jobs, clues=[opening.export()]),
                        seed, difficulty, opening=opening, statements=statements)
    puzzle.certify_progression(order)
    return puzzle
