"""Additional variants specified by the calendar owner."""
from itertools import combinations, combinations_with_replacement, permutations, product
import math
import random

from .extra_constraints import ContainsAll, Counts, RectangleCover
from .diagram_geometry import clears_circles, crosses
from .windrose_equations import candidate_equations
from .generators import (cell, finish, first_solution, grid_domains, lines,
                         orthogonal, reduce_givens, sudoku_model)
from .solver import AllDifferent, Model, SearchLimit, Sum, Table, solve, unequal


def latin(n):
    return Model(grid_domains(n, range(1, n+1)), [AllDifferent(g) for g in lines(n)])


def neighbors(seed, difficulty):
    rng = random.Random(seed)
    model = latin(6)
    opposite = tuple((a, b) for a in range(1, 7) for b in range(1, 7) if a % 2 != b % 2)
    for r in range(6):
        for c in range(6):
            for rr, cc in ((r+1, c), (r, c+1)):
                if rr < 6 and cc < 6:
                    model.constraints.append(Table((cell(r, c), cell(rr, cc)), opposite))
    solution = first_solution(model, rng)
    givens = reduce_givens(model, solution, rng, 11 if difficulty == "mittel" else 7)
    return finish("mein-guter-nachbar", "Mein guter Nachbar",
        "In jeder Zeile und Spalte stehen 1–6 genau einmal. Waagerecht und senkrecht "
        "benachbarte Zahlen haben immer unterschiedliche Parität: Auf gerade folgt ungerade "
        "und umgekehrt. Es gibt keine zusätzliche Blockregel.", model, solution, givens,
        dict(kind="grid", size=6), seed, difficulty)


def crossie(seed, difficulty):
    rng = random.Random(seed)
    model = latin(5)
    cross = [cell(2, 2), cell(1, 2), cell(3, 2), cell(2, 1), cell(2, 3)]
    model.constraints.append(AllDifferent(tuple(cross)))
    solution = first_solution(model, rng)
    givens = reduce_givens(model, solution, rng, 8 if difficulty == "mittel" else 5)
    return finish("crossie", "Crossie", "Jede Zeile, jede Spalte und das graue Kreuz "
        "in der Mitte enthalten die Zahlen 1 bis 5 genau einmal.", model, solution, givens,
        dict(kind="grid", size=5, shaded=cross), seed, difficulty)


def tatami(seed, difficulty):
    rng = random.Random(seed)

    def tile(remaining, regions, orientations):
        if not remaining:
            return regions if len(orientations) == 2 else None
        r, c = min(remaining)
        directions = [(0, 1), (1, 0)]
        rng.shuffle(directions)
        for dr, dc in directions:
            mat = {(r+i*dr, c+i*dc) for i in range(3)}
            if mat <= remaining:
                result = tile(remaining-mat,
                              regions+[[cell(rr, cc) for rr, cc in sorted(mat)]],
                              orientations | {(dr, dc)})
                if result is not None:
                    return result
        return None

    regions = tile({(r, c) for r in range(6) for c in range(6)}, [], set())
    if regions is None:
        raise ValueError("Keine gemischte Tatami-Einteilung gefunden")
    model = Model(grid_domains(6, (1, 2, 3)),
                  [Counts(g, ((1, 2), (2, 2), (3, 2))) for g in lines(6)]
                  + [AllDifferent(tuple(g)) for g in regions])
    for r in range(6):
        for c in range(6):
            for rr, cc in ((r+1, c), (r, c+1)):
                if rr < 6 and cc < 6:
                    model.constraints.append(unequal(cell(r, c), cell(rr, cc), range(1, 4)))
    solution = first_solution(model, rng)
    givens = reduce_givens(model, solution, rng, 11 if difficulty == "mittel" else 6)
    return finish("tatami", "Tatami", "Trage 1, 2 oder 3 ein. In jeder Zeile und "
        "Spalte steht jede Zahl genau zweimal. Waagerecht und senkrecht dürfen sich "
        "gleiche Zahlen nicht berühren. Jedes dick umrandete Gebiet ist eine waagerechte "
        "oder senkrechte Matte aus drei Feldern und enthält 1, 2 und 3 genau einmal.",
        model, solution, givens,
        dict(kind="grid", size=6, regions=regions), seed, difficulty)


def kistenguck(seed, difficulty):
    rng = random.Random(seed)
    cells = [cell(r, c) for r in range(4) for c in range(4)]
    for _ in range(100):
        clues = rng.sample(cells, 4)
        spaces = [k for k in cells if k not in clues]
        visibility = {k: tuple(j for j in spaces if j.split(',')[0] == k.split(',')[0]
                              or j.split(',')[1] == k.split(',')[1]) for k in clues}
        groups = {}
        for occupied in combinations(spaces, 7):
            tents = set(occupied)
            signature = tuple(sum(j in tents for j in visibility[k]) for k in clues)
            groups.setdefault(signature, []).append(tents)
        options = [(signature, layouts[0]) for signature, layouts in groups.items()
                   if len(layouts) == 1 and all(v > 0 for v in signature)]
        if not options:
            continue
        signature, occupied = rng.choice(options)
        model = Model({k: {0, 1} for k in spaces}, [Sum(tuple(spaces), 7)]
                      + [Sum(visibility[k], v) for k, v in zip(clues, signature)])
        solution = {k: int(k in occupied) for k in spaces}
        return finish("kistenguck", "Kistenguck",
            "Verteile genau sieben Kisten. Klicke ein Feld zum Setzen oder Entfernen einer Kiste; "
            "leere Felder zählen als frei. Mit Notizen lassen sich freie Felder durchstreichen. Die vier farbigen "
            "Zahlenfelder bleiben frei. Jede Zahl zählt alle Kisten in ihrer gesamten Zeile "
            "und Spalte, in allen vier Richtungen. Kisten verdecken einander nicht.",
            model, solution, {}, dict(kind="grid", size=4, labels=dict(zip(clues, signature)),
                binary_paint=True), seed, difficulty)
    raise ValueError("Kein eindeutiges Kistenguck im Versuchslimit gefunden")


def ones_twos(seed, difficulty, n=5):
    rng = random.Random(seed)
    for _ in range(600):
        density = rng.choice((.25, .3, .7, .75) if n == 5 else (.4, .45, .55, .6))
        solution = {k: 1 + int(rng.random() < density) for k in grid_domains(n, ())}
        # Avoid all-one/all-two rows: otherwise the puzzle is mostly transcription.
        sums = [sum(solution[k] for k in g) for g in lines(n)]
        if sum(v in (n, 2*n) for v in sums) > 2:
            continue
        diagonals = [tuple(cell(i, i) for i in range(n)), tuple(cell(i, n-1-i) for i in range(n))]
        diag_sums = [sum(solution[k] for k in g) for g in diagonals]
        model = Model(grid_domains(n, (1, 2)),
            [Sum(g, total) for g, total in zip(lines(n)+diagonals, sums+diag_sums)])
        givens = reduce_givens(model, solution, rng, 7 if difficulty == 'mittel' else 5) if n == 6 else {}
        if n == 6 or len(solve(model, seconds=1).solutions) == 1:
            return finish(f"lauter-einser-und-zweier-{n}x{n}", f"Lauter Einser und Zweier {n}x{n}",
                "Trage in jedes Feld 1 oder 2 ein. Die Zahlen rechts und unterhalb des "
                "Gitters geben die Zeilen- und Spaltensummen an. Zusätzlich sind die "
                "Summen beider langen Diagonalen mit Pfeilen direkt an den Ecken angegeben.", model, solution, givens,
                dict(kind="grid", size=n, row_hints=[[v] for v in sums[:n]],
                     col_hints=[[v] for v in sums[n:]], hints_side="bottom-right",
                     diagonal_sums=diag_sums), seed, difficulty)
    raise ValueError("Kein eindeutiges Einser-und-Zweier-Rätsel im Versuchslimit gefunden")


def ones_twos_6(seed, difficulty):
    return ones_twos(seed, difficulty, 6)


def connected(region):
    todo = [next(iter(region))]
    seen = set(todo)
    while todo:
        r, c = map(int, todo.pop().split(','))
        for rr, cc in ((r-1, c), (r+1, c), (r, c-1), (r, c+1)):
            key = cell(rr, cc)
            if key in region and key not in seen:
                seen.add(key)
                todo.append(key)
    return seen == set(region)


def jigsaw(seed, difficulty):
    rng = random.Random(seed)
    solution = first_solution(sudoku_model(), rng)
    regions = [set(cell(br+r, bc+c) for r in range(3) for c in range(3))
               for br in range(0, 9, 3) for bc in range(0, 9, 3)]
    changes = 0
    for _ in range(60):
        owner = {k: i for i, g in enumerate(regions) for k in g}
        options = []
        for i, j in combinations(range(9), 2):
            for a in sorted(regions[i]):
                r, c = map(int, a.split(','))
                if not any(owner[cell(*p)] == j for p in orthogonal(r, c, 9)):
                    continue
                for b in sorted(regions[j]):
                    rr, cc = map(int, b.split(','))
                    if solution[a] != solution[b] or not any(owner[cell(*p)] == i for p in orthogonal(rr, cc, 9)):
                        continue
                    gi, gj = regions[i]-{a}|{b}, regions[j]-{b}|{a}
                    if connected(gi) and connected(gj):
                        options.append((i, j, gi, gj))
        if not options:
            break
        i, j, regions[i], regions[j] = rng.choice(options)
        changes += 1
    if changes == 0:
        raise ValueError("Keine unregelmäßigen Sudoku-Gebiete gefunden")
    groups = [sorted(g) for g in regions]
    model = latin(9)
    model.constraints += [AllDifferent(tuple(g)) for g in groups]
    givens = reduce_givens(model, solution, rng, 31 if difficulty == "mittel" else 24)
    return finish("formen-sudoku", "Formen Sudoku", "Jede Zeile, jede Spalte und jeder "
        "dick umrandete Bereich enthalten 1–9 genau einmal. Die neun Bereiche haben "
        "jeweils neun zusammenhängende Felder und ersetzen die üblichen 3×3-Blöcke.",
        model, solution, givens, dict(kind="grid", size=9, regions=groups), seed, difficulty)


def rinjin(seed, difficulty):
    rng = random.Random(seed)
    n = 8
    solution = {cell(r, c): (r+c) % n+1 for r in range(n) for c in range(n)}
    if rng.randrange(2):
        solution = {k: 9-v for k, v in solution.items()}
    if rng.randrange(2):
        solution = {cell(r, c): solution[cell(7-r, c)] for r in range(n) for c in range(n)}
    model = latin(n)
    remaining = set(solution)
    regions = []
    while remaining:
        start = rng.choice(sorted(remaining))
        region = [start]
        remaining.remove(start)
        for _ in range(rng.choice((1, 2, 3))):
            options = set()
            for k in region:
                r, c = map(int, k.split(','))
                for p in orthogonal(r, c, n):
                    j = cell(*p)
                    values = [solution[t] for t in region] + [solution[j]]
                    if j in remaining and len(set(values)) == len(values) and max(values)-min(values) == len(values)-1:
                        options.add(j)
            if not options:
                break
            j = rng.choice(sorted(options))
            region.append(j)
            remaining.remove(j)
        # Keep single cells in the partition too. Otherwise the renderer joins
        # adjacent unassigned cells into an apparent, unconstrained region.
        regions.append(region)
        if len(region) > 1:
            rows = tuple(p for low in range(1, 10-len(region))
                         for p in permutations(range(low, low+len(region))))
            model.constraints.append(Table(tuple(region), rows))
    givens = reduce_givens(model, solution, rng, 24 if difficulty == "mittel" else 17)
    return finish("rinjin-sudoku", "Rinjin-Sudoku", "In jeder Zeile und Spalte stehen "
        "1–8 genau einmal. Jeder dick umrandete Teilbereich enthält verschiedene "
        "aufeinanderfolgende Zahlen, beispielsweise 2, 3, 4. Ihre räumliche Reihenfolge ist beliebig.",
        model, solution, givens, dict(kind="grid", size=8, regions=regions), seed, difficulty)


def grow_cages(n, solution, rng):
    remaining = set(solution)
    cages = []
    while remaining:
        start = rng.choice(sorted(remaining))
        group = [start]
        remaining.remove(start)
        for _ in range(rng.choice((1, 1, 2, 3))):
            choices = sorted({cell(*p) for k in group for p in orthogonal(*map(int, k.split(',')), n)
                              if cell(*p) in remaining})
            if not choices:
                break
            k = rng.choice(choices)
            remaining.remove(k)
            group.append(k)
        cages.append(group)
    return cages


def cage_result(values, operation):
    if operation == "+":
        return sum(values)
    if operation == "×":
        return math.prod(values)
    if operation == "−":
        return abs(values[0]-values[1])
    if operation == "÷":
        a, b = max(values), min(values)
        return a//b if a % b == 0 else None
    return values[0]


def kenken(seed, difficulty):
    rng = random.Random(seed)
    for _ in range(80):
        model = latin(6)
        solution = first_solution(model, rng)
        cages = grow_cages(6, solution, rng)
        labels = {}
        clues = []
        for group in cages:
            vals = [solution[k] for k in group]
            operations = ["= "] if len(group) == 1 else ["+", "×"]
            if len(group) == 2:
                operations.append("−")
                if max(vals) % min(vals) == 0:
                    operations.append("÷")
            op = rng.choice(operations)
            target = cage_result(vals, op)
            rows = tuple(values for values in product(range(1, 7), repeat=len(group))
                         if cage_result(values, op) == target)
            model.constraints.append(Table(tuple(group), rows))
            key = min(group, key=lambda k: tuple(map(int, k.split(','))))
            labels[key] = f"{target}{op.strip() if len(group) > 1 else ''}"
            clues.append(dict(cells=group, operation=op.strip(), target=target))
        if len(solve(model, seconds=2).solutions) != 1:
            continue
        return finish("denk-denk", "Denk Denk", "Jede Zeile und Spalte enthält 1–6 "
            "genau einmal. Die Zahlen eines umrandeten Gebiets ergeben mit der angegebenen "
            "Operation den Zielwert. Bei − und ÷ haben Gebiete zwei Felder; größere minus "
            "kleinere Zahl bzw. größere geteilt durch kleinere Zahl. Wiederholungen in einem "
            "Gebiet sind erlaubt, sofern sie nicht in derselben Zeile oder Spalte stehen.",
            model, solution, {}, dict(kind="grid", size=6, regions=cages, corner_labels=labels,
                cages=clues), seed, difficulty)
    raise ValueError("Kein eindeutiges Denk-Denk-Rätsel im Versuchslimit gefunden")


def rectangles(seed, difficulty):
    rng = random.Random(seed)
    height, width = 6, 11
    for _ in range(160):
        parcels = [(0, 0, height, width)]
        for _ in range(11 if difficulty == "mittel" else 9):
            options = []
            for i, (r, c, h, w) in enumerate(parcels):
                for cut in range(1, h):
                    if cut*w >= 3 and (h-cut)*w >= 3:
                        options.append((i, (r, c, cut, w), (r+cut, c, h-cut, w)))
                for cut in range(1, w):
                    if cut*h >= 3 and (w-cut)*h >= 3:
                        options.append((i, (r, c, h, cut), (r, c+cut, h, w-cut)))
            if not options:
                break
            i, a, b = rng.choice(options)
            parcels[i:i+1] = [a, b]
        clues = []
        for i, (r, c, h, w) in enumerate(parcels):
            clues.append([f"Parzelle {i+1}", r+rng.randrange(h), c+rng.randrange(w), h+w])
        candidates = {}
        solution = {}
        for (key, row, col, value), original in zip(clues, parcels):
            options = []
            for h in range(1, height+1):
                w = value-h
                if not 1 <= w <= width:
                    continue
                for r in range(max(0, row-h+1), min(row, height-h)+1):
                    for c in range(max(0, col-w+1), min(col, width-w)+1):
                        if any(k != key and r <= rr < r+h and c <= cc < c+w for k, rr, cc, v in clues):
                            continue
                        options.append((r, c, h, w))
            candidates[key] = options
            solution[key] = options.index(original)
        model = Model({k: set(range(len(options))) for k, options in candidates.items()},
                      [RectangleCover(candidates, height, width)])
        try:
            unique = len(solve(model, seconds=1).solutions) == 1
        except SearchLimit:
            continue
        if unique:
            return finish("breite-plus-hoehe", "Breite Plus Höhe",
                "Unterteile das 11×6-Gitter vollständig in Rechtecke. Jedes Rechteck "
                "enthält genau eine Hinweiszahl. Sie ist die Summe aus Breite und Höhe "
                "in Kästchen. Ziehe mit der Maus eine Rechteckauswahl auf; beim Loslassen wird "
                "die Parzelle umrandet. Einzelklicks schalten einzelne Kanten um. Sobald alle Parzellen gültige Rechtecke mit je einem "
                "Hinweis sind, wird die Einteilung automatisch geprüft.", model, solution, {},
                dict(kind="rectangles", rows=height, cols=width, clues=clues,
                     candidates=candidates), seed, difficulty)
    raise ValueError("Keine eindeutige Rechteckaufteilung im Versuchslimit gefunden")


def windrose(seed, difficulty):
    rng = random.Random(seed)
    keys = ("Mitte", "N", "NO", "O", "SO", "S", "SW", "W", "NW")
    # A distinct integer quotient with digits 1–9 permits centers 2, 3, 4.
    # E.g. center 5 would require 5/1, reusing the center as a direction value.
    center = rng.choice((2, 3, 4))
    solution = dict(zip(keys, [center]+rng.sample([v for v in range(1, 10) if v != center], 8)))
    givens = {"Mitte": center}
    candidates = candidate_equations(solution)
    counts = {"sum": 4, "difference": 3, "ratio": 1, "product": 1}
    for _ in range(120):
        chosen = [equation for kind, count in counts.items()
                  for equation in rng.sample([e for e in candidates if e.kind == kind], count)]
        if {key for equation in chosen for key in equation.directions} != set(keys[1:]):
            continue
        model = Model({k: set(range(1, 10)) for k in keys},
                      [AllDifferent(keys)]+[equation.table(center) for equation in chosen])
        if len(solve(model, givens, seconds=2).solutions) == 1:
            break
    else:
        raise ValueError("Kein eindeutiges Windrosen-System mit neun Gleichungen gefunden")
    rng.shuffle(chosen)
    positions = {"Mitte": [270, 150]}
    label_positions = {}
    for i, key in enumerate(keys[1:]):
        angle = math.radians(-90+i*45)
        positions[key] = [270+100*math.cos(angle), 150+100*math.sin(angle)]
        label_positions[key] = [270+142*math.cos(angle), 150+142*math.sin(angle)]
    return finish("windrose", "Windrose", "Die neun Felder enthalten die Zahlen 1–9 "
        "jeweils einmal. Die Mitte ist vorgegeben. Bestimme die acht Himmelsrichtungen "
        "mithilfe der neun Gleichungen. Jede Formel enthält die vorgegebene Mittelzahl. "
        "Der Doppelpunkt bedeutet Division ohne Rest.", model, solution, givens,
        dict(kind="diagram", positions=positions, links=[["Mitte", k] for k in keys[1:]],
             equations=[equation.text(center) for equation in chosen], equation_columns=2,
             width=560, height=330, labels=True, label_positions=label_positions,
             center_label=False), seed, difficulty)


def relationship(seed, difficulty):
    from .relationship_generator import relationship as generate_relationship
    return generate_relationship(seed, difficulty)


def lock_score(code, guess):
    exact = sum(a == b for a, b in zip(code, guess))
    common = sum(min(code.count(digit), guess.count(digit)) for digit in set(code))
    return exact, common-exact


def lock_hint(right, misplaced):
    """Describe total matches first, then their positions; omit zero counts."""
    if right < 0 or misplaced < 0 or right+misplaced > 4:
        raise ValueError("Ungültige Trefferzahlen")
    words = {1: "eine", 2: "zwei", 3: "drei", 4: "vier"}
    total = right+misplaced
    if total == 0:
        return "Keine Ziffer dieser Kombination gehört zum gesuchten Code."
    if total == 1:
        return ("Genau eine Ziffer ist richtig und steht an der richtigen Position." if right
                else "Genau eine Ziffer ist richtig, steht aber an der falschen Position.")
    prefix = f"Genau {words[total]} Ziffern sind richtig"
    if right == 0:
        return prefix+f"; {'beide' if total == 2 else 'alle'} stehen an der falschen Position."
    if misplaced == 0:
        return prefix+f"; {'beide' if total == 2 else 'alle'} stehen an der richtigen Position."
    first = "eine steht an der richtigen Position" if right == 1 else f"{words[right]} stehen an den richtigen Positionen"
    second = "eine an der falschen Position" if misplaced == 1 else f"{words[misplaced]} an den falschen Positionen"
    return prefix+f": {first}, {second}."


def combination_lock(seed, difficulty):
    rng = random.Random(seed)
    for _ in range(500):
        increasing = bool(rng.randrange(2))
        codes = list(combinations_with_replacement(range(10), 4))
        if not increasing:
            codes = [tuple(reversed(code)) for code in codes]
        code = rng.choice([c for c in codes if len(set(c)) >= 3])
        distinct = len(set(code)) if rng.randrange(2) else None
        candidates = [c for c in codes if sum(c) == sum(code) and (distinct is None or len(set(c)) == distinct)]
        guesses = []
        for i in range(2):
            options = []
            for _ in range(90):
                guess = tuple(rng.randrange(10) for _ in range(4))
                score = lock_score(code, guess)
                if guess == code or guess in [g for g, s in guesses] or score == (4, 0):
                    continue
                rest = [c for c in candidates if lock_score(c, guess) == score]
                options.append((len(rest), guess, score, rest))
            if not options:
                break
            _, guess, score, candidates = min(options, key=lambda x: x[0])
            guesses.append((guess, score))
        if len(guesses) != 2 or candidates != [code]:
            continue
        # Both clue rows must carry information; no already-unique sum/order puzzles.
        base = [c for c in codes if sum(c) == sum(code) and (distinct is None or len(set(c)) == distinct)]
        if any(len([c for c in base if lock_score(c, guess) == score]) == 1 for guess, score in guesses):
            continue
        keys = tuple(f"Stelle {i+1}" for i in range(4))
        model = Model({k: set(range(10)) for k in keys}, [Table(keys, tuple(candidates))])
        hints = [lock_hint(right, wrong) for guess, (right, wrong) in guesses]
        equations = ["".join(map(str, guess))+": "+hint for (guess, score), hint in zip(guesses, hints)]
        extra = f"\nVerschiedene Ziffern: {distinct}" if distinct is not None else ""
        return finish("kombinationsschloss", "Kombinationsschloss", "Gesucht ist ein "
            "vierstelliger Code mit Ziffern 0–9; führende Nullen und Wiederholungen sind "
            "erlaubt. Jeder Hinweis nennt exakte Trefferzahlen. Jede Ziffer einer Vermutung "
            "wird höchstens so oft gezählt, wie sie im Code vorkommt. Alle übrigen Ziffern "
            "dieser Vermutung sind falsch. Gib den vollständigen Code in das Eingabefeld ein.",
            model, dict(zip(keys, code)), {},
            dict(kind="lock", equations=equations, hint_texts=hints, code_keys=list(keys),
                expression=f"Ziffernsumme: {sum(code)}\nReihenfolge: {'aufsteigend' if increasing else 'absteigend'} (Gleichstände erlaubt){extra}",
                lock_clues=[[list(g), list(s)] for g, s in guesses], total=sum(code),
                increasing=increasing, distinct=distinct), seed, difficulty)
    raise ValueError("Kein eindeutiges Kombinationsschloss mit genau zwei Hinweisen gefunden")


def bees(seed, difficulty):
    rng = random.Random(seed)
    directions = ((1, 0), (0, 1), (-1, 1), (-1, 0), (0, -1), (1, -1))
    centers = [(0, 0)] + list(directions)
    groups = [[f"Wabe {i+1}/{j+1}" for j in range(6)] for i in range(7)]
    model = Model({k: set(range(1, 7)) for g in groups for k in g}, [AllDifferent(tuple(g)) for g in groups])
    contacts, outer = [], []
    for i, (q, r) in enumerate(centers):
        for j, (dq, dr) in enumerate(directions):
            other = (q+dq, r+dr)
            a = groups[i][j]
            if other not in centers:
                outer.append(a)
            else:
                ii = centers.index(other)
                b = groups[ii][(j+3) % 6]
                if i < ii:
                    contacts.append([a, b])
                    model.constraints.append(Sum((a, b), 7))
    solution = first_solution(model, rng)
    givens = reduce_givens(model, solution, rng, 22 if difficulty == "mittel" else 18)
    givens.update({k: solution[k] for k in outer})
    positions, polygons = {}, {}
    radius = 78
    for i, (q, r) in enumerate(centers):
        x, y = 270+math.sqrt(3)*radius*(q+r/2), 260+1.5*radius*r
        for j, key in enumerate(groups[i]):
            a, b = math.radians(j*60-30), math.radians(j*60+30)
            polygon = [x, y, x+radius*math.cos(a), y+radius*math.sin(a),
                       x+radius*math.cos(b), y+radius*math.sin(b)]
            polygons[key] = polygon
            positions[key] = [sum(polygon[::2])/3, sum(polygon[1::2])/3]
    return finish("bienensudoku", "Bienensudoku", "Jede Wabe besteht aus sechs "
        "Dreiecken und enthält 1–6 genau einmal. Zwei Dreiecke, die über eine gemeinsame "
        "Wabenkante Kontakt haben, ergeben zusammen 7. Dreiecke ohne Kontakt zu einer "
        "anderen Wabe sind immer vorgegeben.", model, solution, givens,
        dict(kind="diagram", positions=positions, polygons=polygons, width=550, height=510,
             groups=groups, contacts=contacts, outer=outer, entry_size=27), seed, difficulty)


def pyramid(seed, difficulty):
    rng = random.Random(seed)
    groups = [tuple(cell(level, i) for i in range(9-level)) for level in range(9)]
    domains = {k: set(range(1, 10)) for g in groups for k in g}
    constraints = [AllDifferent(g) for g in groups]
    allowed = tuple((a, b, c) for a, b, c in product(range(1, 10), repeat=3)
                    if c == a+b or c == abs(a-b))
    triangles = []
    for level in range(1, 9):
        for i, top in enumerate(groups[level]):
            keys = (groups[level-1][i], groups[level-1][i+1], top)
            triangles.append(keys)
            constraints.append(Table(keys, allowed))
    model = Model(domains, constraints)
    # Construct rows directly. Unconstrained cell-wise search spends most of its
    # time on bottom rows that cannot extend even a few levels upward.
    failed = set()
    def extend(row):
        if len(row) == 1:
            return [row]
        canonical = min(row, row[::-1])
        if canonical in failed:
            return None
        options = [sorted({abs(a-b)} | ({a+b} if a+b <= 9 else set()))
                   for a, b in zip(row, row[1:])]
        def build(i, result, used):
            if i == len(options):
                upper = extend(tuple(result))
                return [row]+upper if upper else None
            choices = options[i][:]
            rng.shuffle(choices)
            for value in choices:
                if value and value not in used:
                    found = build(i+1, result+[value], used | {value})
                    if found:
                        return found
            return None
        result = build(0, [], set())
        if result is None:
            failed.add(canonical)
        return result
    for _ in range(5000):
        rows = extend(tuple(rng.sample(range(1, 10), 9)))
        if rows:
            break
    else:
        raise ValueError("Keine gültige Rechenpyramide im Versuchslimit gefunden")
    solution = {cell(level, i): value for level, row in enumerate(rows) for i, value in enumerate(row)}
    givens = reduce_givens(model, solution, rng, 17 if difficulty == "mittel" else 12)
    positions = {cell(level, i): [45+level*26+i*52, 485-level*52]
                 for level in range(9) for i in range(9-level)}
    return finish("denk-denk-pyramide", "Denk Denk Pyramide", "Die unterste Reihe "
        "hat neun Steine. Trage Zahlen von 1–9 ein; innerhalb jeder Reihe darf jede "
        "Zahl nur einmal vorkommen. Jeder obere Stein ist entweder die Summe oder "
        "die positive Differenz (größere minus kleinere Zahl) der beiden darunter. "
        "Die Operation kann für jeden Stein anders sein und muss nicht eingetragen werden.",
        model, solution, givens, dict(kind="diagram", positions=positions, tiles=True,
            width=540, height=550, groups=groups, triangles=triangles), seed, difficulty)


def kakuro(seed, difficulty):
    rng = random.Random(seed)
    # Break every five-cell straight. With distinct digits, four cells can
    # sum to at most 30; nine-cell / 45 clues can no longer occur.
    source = first_solution(sudoku_model(), rng)
    cells = {(r, c) for r in range(9) for c in range(9)}
    segments = [set((r+i*dr, c+i*dc) for i in range(5))
                for dr,dc in ((1,0),(0,1)) for r in range(9-4*dr) for c in range(9-4*dc)]
    for _ in range(100):
        holes, pending = set(), segments.copy()
        while pending and len(holes) < 27:
            options = []
            for candidate in sorted(cells-holes):
                r,c = candidate
                proposed = holes | {candidate}
                if (sum(rr == r for rr,cc in proposed) > 4 or sum(cc == c for rr,cc in proposed) > 4
                        or sum(rr//3 == r//3 and cc//3 == c//3 for rr,cc in proposed) > 4
                        or any({(rr,cc),(rr+1,cc),(rr,cc+1),(rr+1,cc+1)} <= proposed
                               for rr in range(max(0,r-1), min(r+1,8)) for cc in range(max(0,c-1), min(c+1,8)))):
                    continue
                score = sum(candidate in group for group in pending)
                if score:
                    options.append((score+rng.random()*2, candidate))
            if not options:
                break
            _, chosen = max(options)
            holes.add(chosen)
            pending = [group for group in pending if chosen not in group]
        if not pending and len(holes) >= 18:
            break
    else:
        raise ValueError("Kein geeignetes Kakuro-Diagramm gefunden")
    white = cells-holes
    runs = []
    for r, c in sorted(white):
        for dr, dc, direction in ((0, 1, "right"), (1, 0, "down")):
            if (r-dr, c-dc) in white:
                continue
            rr, cc = r, c
            keys = []
            while (rr, cc) in white:
                keys.append(cell(rr, cc))
                rr, cc = rr+dr, cc+dc
            runs.append(dict(cells=keys, clue=cell(r-dr, c-dc), direction=direction))
    groups = lines(9)+[tuple(cell(br+r,bc+c) for r in range(3) for c in range(3))
                       for br in range(0,9,3) for bc in range(0,9,3)]
    domains = {cell(r,c): set(range(1,10)) for r,c in sorted(white)}
    model = Model(domains, [AllDifferent(tuple(k for k in group if k in domains)) for group in groups])
    solution = {k: source[k] for k in domains}
    single_givens = {}
    hints = {}
    for run in runs:
        keys = tuple(run["cells"])
        total = sum(solution[k] for k in keys)
        run["total"] = total
        if len(keys) == 1:
            single_givens[keys[0]] = total
            continue
        hints.setdefault(run["clue"], {})[run["direction"]] = total
        if len(keys) <= 4:
            rows = tuple(values for values in permutations(range(1, 10), len(keys)) if sum(values) == total)
            model.constraints.append(Table(keys, rows))
        else:
            model.constraints.append(Sum(keys, total))
    missing = {}
    for r in range(9):
        keys = tuple(k for k in model.domains if int(k.split(',')[0]) == r)
        present = frozenset(solution[k] for k in keys)
        missing[str(r)] = sorted(set(range(1, 10))-present)
        model.constraints.append(ContainsAll(keys, present))
    givens = reduce_givens(model, solution, rng, 24 if difficulty == "mittel" else 18, budget=2)
    givens.update(single_givens)
    return finish("kakuro-sudoku", "Kakuro Sudoku", "Trage 1–9 in die weißen Felder des "
        "9×9-Zahlenbereichs ein. Keine Wiederholung in einer Zeile, Spalte, einem 3×3-Block "
        "oder einer Zahlengruppe. Die Pfeile geben die Summe der anschließenden Gruppe bis "
        "zum nächsten Hinweisfeld oder Rand an. Startpfeile stehen oben und links außerhalb. "
        "Jede Zahlengruppe hat höchstens vier Felder und ihre Summe beträgt höchstens 30. "
        "Rechts stehen nur die fehlenden Ziffern der Zeile. Einzelne isolierte "
        "Zahlenfelder sind vorgegeben.",
        model, solution, givens, dict(kind="kakuro", size=9, rows=9, cols=9, blocks=True, runs=runs, hints=hints,
            missing=missing, max_run=4, max_sum=30), seed, difficulty)
