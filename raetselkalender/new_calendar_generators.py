"""Additional calendar puzzles, certified from their visible rules and clues."""
from functools import lru_cache
from itertools import permutations, product
import random

from .generators import cell, finish, first_solution, grid_domains, reduce_givens, sudoku_model
from .solver import AllDifferent, Model, SearchLimit, Table, deduce, solve


@lru_cache(maxsize=8)
def sum_patterns(length):
    patterns = {}
    for row in permutations(range(1, 10), length):
        patterns.setdefault(sum(row), []).append(row)
    return {total: tuple(rows) for total, rows in patterns.items()}


def mini_sudoku(seed, difficulty):
    rng = random.Random(seed)
    corners = ('0,0', '0,2', '2,0', '2,2')
    quads = [tuple(cell(r+i, c+j) for i in range(2) for j in range(2))
             for r in range(2) for c in range(2)]
    for _ in range(200):
        values = rng.sample(range(1, 10), 9)
        solution = dict(zip(grid_domains(3, ()), values))
        totals = [sum(solution[k] for k in group) for group in quads]
        model = Model(grid_domains(3, range(1, 10)), [AllDifferent(tuple(solution))]
                      + [Table(group, sum_patterns(4)[total]) for group, total in zip(quads, totals)])
        givens = {k: solution[k] for k in corners}
        if not deduce(model, givens, trace=False).solved:
            continue
        return finish('mini-sudoku', 'Mini-Sudoku',
            'Verteile 1 bis 9 jeweils genau einmal im 3×3-Feld. Die vier Ecken sind vorgegeben. '
            'Jede kleine Zahl am Schnittpunkt ist die Summe der vier großen Felder um sie herum.',
            model, solution, givens, dict(kind='grid', size=3, cell_size=100, entry_size=58,
                intersection_sums=[(r, c, totals[2*r+c]) for r in range(2) for c in range(2)]), seed, difficulty)
    raise ValueError('Kein logisch lösbares Mini-Sudoku gefunden')


def one_to_nine(seed, difficulty):
    rng = random.Random(seed)
    solution = dict(zip(grid_domains(3, ()), rng.sample(range(1, 10), 9)))
    groups = [tuple(cell(r, c) for c in range(3)) for r in range(3)]
    groups += [tuple(cell(r, c) for r in range(3)) for c in range(3)]
    totals = [sum(solution[k] for k in group) for group in groups]
    model = Model(grid_domains(3, range(1, 10)), [AllDifferent(tuple(solution))]
                  + [Table(group, sum_patterns(3)[total]) for group, total in zip(groups, totals)])
    givens = reduce_givens(model, solution, rng, 3 if difficulty == 'mittel' else 2)
    return finish('von-1-bis-9', 'Von 1 bis 9',
        'Trage die Zahlen 1 bis 9 jeweils genau einmal ein. Die blauen Felder rechts und unten '
        'geben die Summen der jeweiligen Zeile und Spalte an. Einige Zahlen sind vorgegeben.',
        model, solution, givens, dict(kind='grid', size=3, cell_size=86, entry_size=60,
            row_hints=[[v] for v in totals[:3]], col_hints=[[v] for v in totals[3:]],
            hints_side='bottom-right', sum_cells=True), seed, difficulty)


@lru_cache(maxsize=16)
def straight_patterns(size, length):
    return tuple(row for low in range(1, size-length+2)
                 for row in permutations(range(low, low+length)))


def white_runs(size, black):
    groups = []
    for axis in (0, 1):
        for a in range(size):
            group = []
            for b in range(size+1):
                key = cell(a, b) if axis == 0 else cell(b, a)
                if b == size or key in black:
                    if group:
                        groups.append(tuple(group))
                    group = []
                else:
                    group.append(key)
    return groups


def streets(seed, difficulty):
    rng = random.Random(seed)
    n = 7
    keys = tuple(grid_domains(n, ()))
    for _ in range(60):
        black = set(rng.sample(keys, rng.randint(10, 14)))
        if any(sum(cell(r, c) not in black for c in range(n)) < 3 for r in range(n)):
            continue
        if any(sum(cell(r, c) not in black for r in range(n)) < 3 for c in range(n)):
            continue
        numbered = set(rng.sample(sorted(black), 3 if difficulty == 'mittel' else 4))
        active = [k for k in keys if k not in black or k in numbered]
        groups = [tuple(cell(r, c) for c in range(n) if cell(r, c) in active) for r in range(n)]
        groups += [tuple(cell(r, c) for r in range(n) if cell(r, c) in active) for c in range(n)]
        straights = white_runs(n, black)
        model = Model({k: set(range(1, n+1)) for k in active},
                      [AllDifferent(group) for group in groups]
                      + [Table(group, straight_patterns(n, len(group))) for group in straights if len(group) > 1])
        try:
            result = solve(model, limit=1, rng=rng, seconds=1)
        except SearchLimit:
            continue
        if not result.solutions:
            continue
        solution = result.solutions[0]
        givens = reduce_givens(model, solution, rng, 10 if difficulty == 'mittel' else 7)
        givens.update({k: solution[k] for k in numbered})
        return finish('strassen', 'Straßen',
            'Fülle die weißen Felder mit 1 bis 7. In keiner Zeile oder Spalte darf eine Zahl '
            'doppelt vorkommen; auch vorgegebene Zahlen in schwarzen Feldern zählen dabei mit. '
            'Jede zusammenhängende weiße Gruppe in einer Zeile oder Spalte bildet eine Straße: '
            'Ihre verschiedenen Zahlen sind lückenlos aufeinanderfolgend, in beliebiger Reihenfolge. '
            'Schwarze Felder ohne Zahl bleiben leer.',
            model, solution, givens, dict(kind='grid', size=n,
                black_cells={k: solution[k] if k in numbered else None for k in sorted(black)},
                straights=straights), seed, difficulty)
    raise ValueError('Keine passende Straßen-Aufgabe gefunden')


def doors(seed, difficulty):
    rng = random.Random(seed)
    model = sudoku_model(diagonal=True)
    solution = first_solution(model, rng)
    marked = []
    for r in range(9):
        for c in range(9):
            for rr, cc in ((r+1, c), (r, c+1)):
                if max(rr, cc) >= 9:
                    continue
                a, b = cell(r, c), cell(rr, cc)
                consecutive = abs(solution[a]-solution[b]) == 1
                if consecutive:
                    marked.append((a, b))
                model.constraints.append(Table((a, b), tuple((x, y) for x in range(1, 10)
                    for y in range(1, 10) if (abs(x-y) == 1) == consecutive)))
    givens = reduce_givens(model, solution, rng, 22 if difficulty == 'mittel' else 16)
    return finish('tuer-an-tuer-sudoku', 'Tür an Tür – Sudoku X',
        'Jede Zeile, Spalte, jeder 3×3-Block und beide großen Diagonalen enthalten 1 bis 9 '
        'genau einmal. An jeder blau gestrichelten Grenze unterscheiden sich die Nachbarn '
        'um genau 1. Alle solchen Grenzen sind markiert: An unmarkierten Grenzen ist die Differenz nicht 1.',
        model, solution, givens, dict(kind='grid', size=9, blocks=True,
            highlight_diagonals=True, door_edges=marked), seed, difficulty)


def cheese_cells():
    widths = (4, 6, 8, 10, 10, 10, 10, 8, 6, 4)
    return [cell(r, c) for r, width in enumerate(widths)
            for c in range((10-width)//2, (10+width)//2)]


def cheese(seed, difficulty):
    rng = random.Random(seed)
    keys = cheese_cells()
    present = set(keys)
    groups = [tuple(cell(r+i*dr, c+i*dc) for i in range(4))
              for key in keys for r, c in [tuple(map(int, key.split(',')))]
              for dr, dc in ((0, 1), (1, 0), (1, 1), (1, -1))
              if all(cell(r+i*dr, c+i*dc) in present for i in range(4))]
    allowed = tuple(row for row in product((0, 1), repeat=4) if len(set(row)) > 1)
    model = Model({k: {0, 1} for k in keys}, [Table(group, allowed) for group in groups])
    solution = first_solution(model, rng)
    givens = reduce_givens(model, solution, rng, 30 if difficulty == 'mittel' else 22)
    return finish('kaesekaestchen', 'Käsekästchen',
        'Fülle jedes vorhandene Kästchen mit X oder O. Waagerecht, senkrecht und in beiden '
        'Diagonalrichtungen dürfen niemals mehr als drei gleiche Zeichen unmittelbar '
        'aufeinanderfolgen. An der Außenform endet eine Reihe. Klickfolge: leer, X, O, leer. '
        'Notizen setzt kleine Kandidaten; es gibt keine zusätzliche Gleichverteilungsregel.',
        model, solution, givens, dict(kind='cheese', size=10, cells=keys), seed, difficulty)
