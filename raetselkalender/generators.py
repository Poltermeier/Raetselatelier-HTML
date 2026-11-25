"""Remove clues only while a complete logical solution remains provable.

Seeds are local random.Random instances; global random state is never changed.
"""
from __future__ import annotations

from itertools import combinations, permutations, product
import random
import time

from .puzzle import Puzzle
from .pearl_paths import pearl_partition
from .hashi_network import island_layout, bridge_assignment
from .binary_patterns import balanced_patterns, binary_grid
from .nonogram_digits import DIGITS, digit_bitmap
from .arithmetic_equations import expression_value, expression_table, result_table, varied_equations
from .solver import (AllDifferent, ConnectedEdges, Model, SearchLimit, Sum,
                     Table, deduce, solve, unequal)


def cell(r: int, c: int) -> str:
    return f"{r},{c}"


def grid_domains(n: int, values, cols: int | None = None) -> dict[str, set[int]]:
    return {cell(r, c): set(values) for r in range(n) for c in range(n if cols is None else cols)}


def lines(n: int, cols: int | None = None):
    width = n if cols is None else cols
    return ([tuple(cell(r, c) for c in range(width)) for r in range(n)]
            + [tuple(cell(r, c) for r in range(n)) for c in range(width)])


def orthogonal(r: int, c: int, n: int):
    return [(rr, cc) for rr, cc in ((r-1, c), (r+1, c), (r, c-1), (r, c+1))
            if 0 <= rr < n and 0 <= cc < n]


def reduce_givens(model: Model, solution: dict[str, int], rng: random.Random,
                  target: int, budget: float = 7) -> dict[str, int]:
    givens = solution.copy()
    keys = list(givens)
    rng.shuffle(keys)
    deadline = time.monotonic() + budget
    for key in keys:
        if len(givens) <= target or time.monotonic() > deadline:
            break
        value = givens.pop(key)
        result = deduce(model, givens, seconds=min(.65, max(.01, deadline-time.monotonic())), trace=False)
        if not result.solved:
            givens[key] = value
    return givens


def first_solution(model: Model, rng: random.Random) -> dict[str, int]:
    result = solve(model, limit=1, rng=rng, seconds=15)
    if not result.solutions:
        raise ValueError("Keine Ausgangslösung gefunden")
    return result.solutions[0]


def finish(type_id, title, rules, model, solution, givens, view, seed, difficulty, *, result=None):
    puzzle = Puzzle(type_id, title, rules, model, solution, givens, view, seed, difficulty, result=result)
    if not puzzle.editable:
        raise ValueError("Ein Rätsel muss freie Felder besitzen")
    puzzle.certify()
    return puzzle


def sudoku_model(*, diagonal=False) -> Model:
    groups = lines(9)
    groups += [tuple(cell(br+r, bc+c) for r in range(3) for c in range(3))
               for br in range(0, 9, 3) for bc in range(0, 9, 3)]
    if diagonal:
        groups += [tuple(cell(i, i) for i in range(9)),
                   tuple(cell(i, 8-i) for i in range(9))]
    return Model(grid_domains(9, range(1, 10)), [AllDifferent(g) for g in groups])


def kropki(seed: int, difficulty: str) -> Puzzle:
    rng = random.Random(seed)
    base = sudoku_model()
    solution = first_solution(base, rng)
    dots = []
    for r in range(9):
        for c in range(9):
            for rr, cc in ((r+1, c), (r, c+1)):
                if rr >= 9 or cc >= 9:
                    continue
                a, b = cell(r, c), cell(rr, cc)
                x, y = solution[a], solution[b]
                kind = "black" if max(x, y) == 2*min(x, y) else "white" if abs(x-y) == 1 else "none"
                def relation(u, v):
                    return ("black" if max(u, v) == 2*min(u, v)
                            else "white" if abs(u-v) == 1 else "none")
                base.constraints.append(Table((a, b), tuple((u, v) for u in range(1, 10)
                    for v in range(1, 10) if relation(u, v) == kind)))
                if kind != "none":
                    dots.append([a, b, kind])
    givens = reduce_givens(base, solution, rng, 9 if difficulty == "mittel" else 0)
    return finish("kropki-sudoku", "Kropki Sudoku",
        "In jeder Zeile, Spalte und jedem 3×3-Block stehen 1–9 genau einmal. "
        "Weißer Punkt: Differenz 1. Schwarzer Punkt: Verhältnis 1:2. Bei 1 und 2 wird "
        "schwarz gezeichnet. Alle Punkte sind angegeben: Ohne Punkt gilt keine der beiden Beziehungen.",
        base, solution, givens, dict(kind="grid", size=9, blocks=True, dots=dots), seed, difficulty)


def pearls(seed: int, difficulty: str) -> Puzzle:
    rng = random.Random(seed)
    # Block Sudoku is only a source of a filled grid. Its regions are reshaped
    # into disjoint paths; the final model has no additional 3×3-block rule.
    solution = first_solution(sudoku_model(diagonal=True), rng)
    paths = pearl_partition(solution, rng)
    base = Model(grid_domains(9, range(1, 10)), [AllDifferent(g) for g in lines(9)]
                 + [AllDifferent(tuple(cell(i, i) for i in range(9))),
                    AllDifferent(tuple(cell(i, 8-i) for i in range(9)))]
                 + [AllDifferent(tuple(path)) for path in paths])
    givens = reduce_givens(base, solution, rng, 32 if difficulty == "mittel" else 24)
    return finish("perlenschnursudoku", "Perlenschnursudoku",
        "In jeder Zeile, jeder Spalte, beiden langen Diagonalen und jeder Perlenschnur "
        "stehen 1–9 genau einmal. Jede der neun getrennten Schnüre hat neun Perlen. "
        "Die beiden langen Diagonalen sind farbig markiert; die Mitte gehört zu beiden. Es gibt keine zusätzliche Blockregel.",
        base, solution, givens, dict(kind="pearls", size=9, paths=paths, diagonals=True), seed, difficulty)


def binary(seed: int, difficulty: str) -> Puzzle:
    rng = random.Random(seed)
    rows, cols = 6, 12
    groups = lines(rows, cols)
    row_patterns, col_patterns = balanced_patterns(cols), balanced_patterns(rows)
    model = Model(grid_domains(rows, (0, 1), cols),
                  [Table(g, row_patterns) for g in groups[:rows]]
                  + [Table(g, col_patterns) for g in groups[rows:]])
    # Two complete rows/columns must differ. A table over matching bits would be exponential.
    model.constraints += [DistinctLines(a, b) for group in (groups[:rows], groups[rows:])
                          for a, b in combinations(group, 2)]
    solution = binary_grid(rng, rows, cols)
    givens = reduce_givens(model, solution, rng, 36 if difficulty == "mittel" else 30)
    return finish("binaersystem", "Binärsystem",
        "Trage 0 oder 1 ein. Jede Zeile enthält sechs Nullen und sechs Einsen, "
        "jede Spalte drei Nullen und drei Einsen. "
        "Nie stehen drei gleiche Ziffern direkt hintereinander. Keine zwei Zeilen und "
        "keine zwei Spalten sind identisch.",
        model, solution, givens, dict(kind="grid", size=cols, rows=rows, cols=cols), seed, difficulty)


class DistinctLines:
    def __init__(self, a, b):
        self.a, self.b = a, b
        self.keys = a + b

    def reduce(self, domains):
        from .solver import Contradiction, restrict
        possible = [(a, b) for a, b in zip(self.a, self.b)
                    if any(x != y for x in domains[a] for y in domains[b])]
        if not possible:
            raise Contradiction
        if len(possible) == 1:
            a, b = possible[0]
            da, db = domains[a].copy(), domains[b].copy()
            restrict(domains, a, {x for x in da if any(x != y for y in db)})
            restrict(domains, b, {y for y in db if any(x != y for x in da)})


def runs(bits):
    result = []
    length = 0
    for bit in list(bits) + [0]:
        if bit:
            length += 1
        elif length:
            result.append(length)
            length = 0
    return result


def nonogram(seed: int, difficulty: str) -> Puzzle:
    rng = random.Random(seed)
    rows, cols = 5, 10
    candidates = ["".join(code) for code in product(DIGITS, repeat=3)
                  if sum(len(DIGITS[digit][0]) for digit in code)+2 <= cols]
    rng.shuffle(candidates)
    tables = {}
    for length in (rows, cols):
        by_hint = {}
        for bits in product((0, 1), repeat=length):
            by_hint.setdefault(tuple(runs(bits)), []).append(bits)
        tables[length] = by_hint
    groups = lines(rows, cols)
    for code in candidates[:80]:
        bitmap = digit_bitmap(code)
        solution = {cell(r, c): bitmap[r][c] for r in range(rows) for c in range(cols)}
        hints = [runs(solution[k] for k in g) for g in groups]
        # Uniqueness follows from the run clues alone; digit recognition is not
        # an extra solver constraint and no inner numbers need to be supplied.
        model = Model(grid_domains(rows, (0, 1), cols),
            [Table(g, tuple(tables[len(g)][tuple(h)])) for g, h in zip(groups, hints)])
        try:
            result = solve(model, seconds=1)
        except SearchLimit:
            continue
        if len(result.solutions) == 1:
            return finish("nonogramm", "Zahlen Nonogramm",
                "Fülle das 10×5-Gitter per Maus: Ein Klick malt ein Feld aus, ein weiterer entfernt die Füllung. "
                "Im Notizmodus streichst du freie Felder durch. Die Hinweise nennen "
                "die Längen zusammenhängender Blöcke in ihrer Reihenfolge. Zwischen zwei "
                "Blöcken liegt mindestens ein freies Feld. Das fertige Bild zeigt drei Ziffern. "
                "Sobald alle Bildfelder ausgemalt sind, zählen die übrigen Felder automatisch als frei.",
                model, solution, {}, dict(kind="grid", size=cols, rows=rows, cols=cols,
                    row_hints=hints[:rows], col_hints=hints[rows:], binary_paint=True),
                seed, difficulty, result=code)
    raise ValueError("Kein eindeutiges Nonogramm im Versuchslimit gefunden; bitte einen neuen Seed wählen")


def arithmetic(seed: int, difficulty: str) -> Puzzle:
    rng = random.Random(seed)
    symbols = ("Dreieck", "Raute", "Stern", "Fünfeck")
    clues, solution, expression = varied_equations(symbols, rng)
    model = Model({k: set(range(1, 10)) for k in symbols}, [AllDifferent(symbols)])
    equations = []
    for expr, total in clues:
        model.constraints.append(expression_table(expr, total))
        equations.append(f"{expr} = {total}")
    solution["Ergebnis"] = expression_value(expression, solution)
    model.domains["Ergebnis"] = set(range(1, 100))
    model.constraints.append(result_table(expression, symbols))
    return finish("rechenfreude", "Rechenfreude",
        "Jedes Symbol steht für eine andere Zahl von 1 bis 9. Ein Symbol hat überall "
        "denselben Wert, auch wenn es in einer Gleichung mehrfach vorkommt. "
        "Vier Gleichungen mit Plus, Minus, Mal und Geteilt bestimmen die Symbolwerte. "
        "Es gilt Punkt vor Strich; Divisionen gehen ohne Rest auf. Berechne "
        "anschließend das Ergebnis der Schlussformel.", model, solution, {},
        dict(kind="arithmetic", equations=equations, expression=expression,
             symbols=dict(zip(symbols, ("triangle", "diamond", "star", "pentagon")))), seed, difficulty)


def suguru(seed: int, difficulty: str) -> Puzzle:
    rng = random.Random(seed)
    n = 6
    # Partition a Hamiltonian snake into connected tetrominoes/pentominoes.
    # Growing regions independently often leaves unsatisfiable tiny remnants.
    for _ in range(200):
        path = [(r, c if r % 2 == 0 else n-1-c) for r in range(n) for c in range(n)]
        if rng.randrange(2):
            path = [(c, r) for r, c in path]
        if rng.randrange(2):
            path = [(n-1-r, c) for r, c in path]
        if rng.randrange(2):
            path.reverse()
        sizes = [4]*4 + [5]*4
        rng.shuffle(sizes)
        regions = []
        position = 0
        for size in sizes:
            regions.append([cell(*p) for p in path[position:position+size]])
            position += size
        domains = {k: set(range(1, len(g)+1)) for g in regions for k in g}
        constraints = [AllDifferent(tuple(g)) for g in regions]
        for r in range(n):
            for c in range(n):
                for dr, dc in ((0, 1), (1, -1), (1, 0), (1, 1)):
                    rr, cc = r+dr, c+dc
                    if 0 <= rr < n and 0 <= cc < n:
                        constraints.append(unequal(cell(r, c), cell(rr, cc), range(1, 6)))
        model = Model(domains, constraints)
        try:
            solution = first_solution(model, rng)
        except (SearchLimit, ValueError):
            continue
        givens = reduce_givens(model, solution, rng, 9 if difficulty == "mittel" else 5)
        return finish("suguru", "Suguru",
            "Eine Region mit n Feldern enthält die Zahlen 1 bis n jeweils einmal. "
            "Gleiche Zahlen dürfen einander weder waagerecht, senkrecht noch diagonal berühren.",
            model, solution, givens, dict(kind="grid", size=n, regions=regions), seed, difficulty)
    raise ValueError("Kein gültiges Suguru im Versuchslimit gefunden")


def hidato(seed: int, difficulty: str) -> Puzzle:
    rng = random.Random(seed)
    n = 6
    # A Hamiltonian path begins as a snake, then receives endpoint backbite moves.
    path = [(r, c if r % 2 == 0 else n-1-c) for r in range(n) for c in range(n)]
    for _ in range(600):
        if rng.randrange(2):
            path.reverse()
        options = [i for i in range(2, len(path))
                   if max(abs(path[i][0]-path[0][0]), abs(path[i][1]-path[0][1])) == 1]
        if options:
            i = rng.choice(options)
            path = list(reversed(path[:i])) + path[i:]
    # Variables are positions of numbers; UI fields are cell values, via a dual model.
    solution = {cell(*p): i+1 for i, p in enumerate(path)}
    model = Model(grid_domains(n, range(1, n*n+1)), [])
    model.constraints.append(AllDifferent(tuple(model.domains)))
    model.constraints.append(ConsecutiveNeighbors(n))
    givens = reduce_givens(model, solution, rng, 18 if difficulty == "mittel" else 13, budget=5)
    # The endpoints are always supplied for recognisable Hidato rules.
    givens[cell(*path[0])] = 1
    givens[cell(*path[-1])] = n*n
    return finish("hidato", "Hidato",
        "Fülle das Gitter mit 1 bis 36, jede Zahl genau einmal. Aufeinanderfolgende "
        "Zahlen müssen sich waagerecht, senkrecht oder diagonal berühren. 1 und 36 sind vorgegeben.",
        model, solution, givens, dict(kind="grid", size=n), seed, difficulty)


class ConsecutiveNeighbors:
    def __init__(self, n):
        self.n = n
        self.keys = tuple(grid_domains(n, ()))
        self.neighbors = {cell(r, c): {cell(rr, cc) for rr in range(max(0, r-1), min(n, r+2))
                                     for cc in range(max(0, c-1), min(n, c+2)) if (rr, cc) != (r, c)}
                          for r in range(n) for c in range(n)}

    def reduce(self, domains):
        from .solver import restrict
        for k in self.keys:
            available = set().union(*(domains[j] for j in self.neighbors[k]))
            restrict(domains, k, {v for v in domains[k]
                if (v == 1 or v-1 in available) and (v == self.n*self.n or v+1 in available)})


def camping(seed: int, difficulty: str) -> Puzzle:
    rng = random.Random(seed)
    n = 7
    target = 9 if difficulty == "mittel" else 10
    # Generate non-touching tents, with a distinct orthogonal tree for each tent.
    for _ in range(500):
        tents = []
        cells = [(r, c) for r in range(n) for c in range(n)]
        rng.shuffle(cells)
        for p in cells:
            if all(max(abs(p[0]-q[0]), abs(p[1]-q[1])) > 1 for q in tents):
                tents.append(p)
            if len(tents) == target:
                break
        if len(tents) < target:
            continue
        trees = []
        for p in tents:
            options = [q for q in orthogonal(*p, n) if q not in tents and q not in trees]
            if not options:
                break
            trees.append(rng.choice(options))
        if len(trees) != len(tents):
            continue
        candidates = sorted(p for p in cells if p not in trees)
        domains = {cell(*p): {0, 1} for p in candidates}
        constraints = [Sum(tuple(cell(r, c) for r, c in candidates if r == row),
                           sum(r == row for r, c in tents)) for row in range(n)]
        constraints += [Sum(tuple(cell(r, c) for r, c in candidates if c == col),
                            sum(c == col for r, c in tents)) for col in range(n)]
        constraints += [Table((cell(*p), cell(*q)), ((0, 0), (0, 1), (1, 0)))
                        for p, q in combinations(candidates, 2)
                        if max(abs(p[0]-q[0]), abs(p[1]-q[1])) <= 1]
        constraints.append(TentMatching(tuple(domains), tuple(cell(*p) for p in trees), n))
        model = Model(domains, constraints)
        solution = {cell(*p): int(p in tents) for p in candidates}
        try:
            result = solve(model, seconds=1)
        except SearchLimit:
            continue
        if result.solutions != [solution]:
            continue
        return finish("camping", "Camping", "Stelle neben jeden Baum genau ein Zelt, "
            "waagerecht oder senkrecht angrenzend. Jedes Zelt gehört zu einem anderen Baum. "
            "Zelte berühren sich auch diagonal nicht. Die Zahlen rechts und unten geben die "
            "Zeltanzahl je Zeile und Spalte an. Klicken setzt oder entfernt ein Zelt; "
            "Notizen streicht freie Felder durch. Leere Felder zählen als Wiese.",
            model, solution, {}, dict(kind="grid", size=n, rows=n, cols=n, trees=[cell(*p) for p in trees],
                row_hints=[[sum(r == row for r, c in tents)] for row in range(n)],
                col_hints=[[sum(c == col for r, c in tents)] for col in range(n)],
                hints_side="bottom-right"), seed, difficulty)
    raise ValueError("Kein eindeutiges Camping im Versuchslimit gefunden")


class TentMatching:
    """Hall feasibility via bipartite matching, including all selected tents at leaves."""
    def __init__(self, keys, trees, n):
        self.keys, self.trees = keys, trees
        self.options = {t: [cell(*p) for p in orthogonal(*map(int, t.split(',')), n)
                            if cell(*p) in keys] for t in trees}

    def reduce(self, domains):
        from .solver import Contradiction, restrict
        for t in self.trees:
            possible = [k for k in self.options[t] if 1 in domains[k]]
            if not possible:
                raise Contradiction
            if len(possible) == 1:
                restrict(domains, possible[0], {1})
        # Match selected tents first, then optional tents; selected ones must remain covered.
        selected = [k for k in self.keys if domains[k] == {1}]
        matched = {}
        def augment(tent, seen):
            for t in self.trees:
                if tent not in self.options[t] or t in seen:
                    continue
                seen.add(t)
                if t not in matched or augment(matched[t], seen):
                    matched[t] = tent
                    return True
            return False
        for tent in selected:
            if not augment(tent, set()):
                raise Contradiction
        for tent in self.keys:
            if tent not in selected and 1 in domains[tent]:
                augment(tent, set())
        if len(matched) != len(self.trees):
            raise Contradiction


def hashi(seed: int, difficulty: str) -> Puzzle:
    rng = random.Random(seed)
    n = 10
    count = 20 if difficulty == "mittel" else 24
    for _ in range(2000):
        layout = island_layout(rng, n, count)
        if layout is None:
            continue
        points, edges, crossings = layout
        values = bridge_assignment(rng, points, edges, crossings)
        if values is None:
            continue
        names = [f"Brücke {i+1}" for i in range(len(edges))]
        endpoints = tuple((cell(*p), cell(*q)) for p, q in edges)
        constraints = [ConnectedEdges(tuple(names), endpoints, tuple(cell(*p) for p in points))]
        for i, j in crossings:
            constraints.append(Table((names[i], names[j]),
                tuple((a, b) for a in range(4) for b in range(4) if not (a and b))))
        model = Model({k: {0, 1, 2, 3} for k in names}, constraints)
        solution = {name: values[i] for i, name in enumerate(names)}
        islands = []
        for p in points:
            keys = tuple(names[i] for i, edge in enumerate(edges) if p in edge)
            total = sum(solution[k] for k in keys)
            constraints.append(Sum(keys, total))
            islands.append([cell(*p), total])
        # Reject ambiguous layouts directly; bridge values are never clues.
        try:
            result = solve(model, seconds=.75)
        except SearchLimit:
            continue
        if result.solutions != [solution]:
            continue
        return finish("pontifex-hashikake", "Pontifex Hashikake",
            "Verbinde die Inseln auf dem 10×10-Raster waagerecht oder senkrecht. Eine Brücke darf nur die nächste "
            "sichtbare Insel erreichen. Klicke zwischen zwei Inseln: Die Brückenzahl steigt von 0 auf 3 "
            "und sinkt danach wieder bis 0. Mit Notizen lassen sich Verbindungen durchstreichen. Brücken "
            "kreuzen sich nicht und laufen nicht durch Inseln. Die Inselzahl ist die Summe "
            "ihrer Brücken; alle Inseln bilden ein zusammenhängendes Netz.", model, solution, {},
            dict(kind="hashi", size=n, islands=islands, max_bridges=3,
                 edges=[[k, a, b] for k, (a, b) in zip(names, endpoints)]), seed, difficulty)
    raise ValueError("Kein eindeutiges Hashikake im Versuchslimit gefunden")
