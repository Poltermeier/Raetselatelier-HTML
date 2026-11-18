"""Egg placement and decimal row permutations with visible sum clues."""
import random

from .calendar_generators import connected
from .generators import cell, finish, first_solution, grid_domains, lines, reduce_givens
from .solver import AllDifferent, Model, Sum, deduce, unequal


class ExactSum(Sum):
    """Eliminate values unsupported by the other cells' reachable sums."""
    def reduce(self, domains):
        from .solver import Contradiction, restrict
        prefix = [{0}]
        for key in self.keys:
            prefix.append({a+b for a in prefix[-1] for b in domains[key]})
        if self.total not in prefix[-1]:
            raise Contradiction
        suffix = {0}
        for i in range(len(self.keys)-1, -1, -1):
            key = self.keys[i]
            other = {a+b for a in prefix[i] for b in suffix}
            restrict(domains, key, {v for v in domains[key] if self.total-v in other})
            suffix = {a+b for a in suffix for b in domains[key]}


def decimal_rows(rng):
    solution = {}
    for r in range(5):
        domains = {}
        for c in range(10):
            forbidden = {solution[cell(r-1, cc)] for cc in range(max(0, c-1), min(10, c+2))} if r else set()
            domains[cell(r, c)] = set(range(10))-forbidden
        row = first_solution(Model(domains, [AllDifferent(tuple(domains))]), rng)
        solution.update(row)
    return solution


def tens_grid(seed, difficulty):
    rng = random.Random(seed)
    solution = decimal_rows(rng)
    groups = lines(5, 10)
    totals = [sum(solution[k] for k in group) for group in groups[5:]]
    constraints = [AllDifferent(group) for group in groups[:5]]
    constraints += [ExactSum(group, total) for group, total in zip(groups[5:], totals)]
    constraints += [unequal(cell(r, c), cell(r+1, cc), range(10))
                    for r in range(4) for c in range(10)
                    for cc in range(max(0, c-1), min(10, c+2))]
    model = Model(grid_domains(5, range(10), 10), constraints)
    givens = reduce_givens(model, solution, rng, 23 if difficulty == 'mittel' else 17)
    return finish('zehnergitter', 'Zehnergitter',
        'In jeder der fünf Zeilen stehen die Ziffern 0 bis 9 genau einmal. '
        'Die blauen Felder unter den zehn Spalten geben deren Summen an. '
        'Gleiche Ziffern dürfen sich weder waagerecht noch senkrecht oder diagonal berühren. '
        'Einige Ziffern sind bereits vorgegeben.',
        model, solution, givens, dict(kind='grid', size=10, rows=5, cols=10,
            col_hints=[[v] for v in totals], row_hints=[], hints_side='bottom-right',
            sum_cells=True, cell_size=55), seed, difficulty)


def nest_regions(rng):
    regions = [set(cell(br+r, bc+c) for r in range(2) for c in range(3))
               for br in range(0, 6, 2) for bc in range(0, 6, 3)]
    keys = list(grid_domains(6, ()))
    for _ in range(1200):
        owner = {k: i for i, group in enumerate(regions) for k in group}
        a, b = rng.sample(keys, 2)
        i, j = owner[a], owner[b]
        if i == j:
            continue
        left, right = regions[i]-{a}|{b}, regions[j]-{b}|{a}
        if connected(left) and connected(right):
            regions[i], regions[j] = left, right
    return [sorted(group) for group in regions]


def neighbors8(key):
    r, c = map(int, key.split(','))
    return tuple(cell(rr, cc) for rr in range(max(0, r-1), min(6, r+2))
                 for cc in range(max(0, c-1), min(6, c+2)) if (rr, cc) != (r, c))


def nest_model(regions, clues):
    groups = lines(6)+[tuple(group) for group in regions]
    return Model(grid_domains(6, (0, 1)),
                 [Sum(group, 2) for group in groups]
                 + [Sum(neighbors8(key), total) for key, total in clues.items()])


def easter_nest(seed, difficulty):
    rng = random.Random(seed)
    regions = nest_regions(rng)
    source = nest_model(regions, {})
    solution = first_solution(source, rng)
    clues = {key: sum(solution[k] for k in neighbors8(key))
             for key, value in solution.items() if not value}
    order = list(clues)
    rng.shuffle(order)
    for key in order:
        candidate = {k: v for k, v in clues.items() if k != key}
        if len(clues) <= (11 if difficulty == 'mittel' else 8):
            break
        if deduce(nest_model(regions, candidate), {k: 0 for k in candidate}, trace=False).solved:
            clues = candidate
    return finish('osternest-sudoku', 'Osternest Sudoku',
        'Lege in jede Zeile, jede Spalte und jeden dick umrandeten unregelmäßigen Bereich '
        'genau zwei Ostereier. Die Zahlen zählen die Eier in den unmittelbar angrenzenden '
        'Feldern: waagerecht, senkrecht und diagonal. Auf einem Zahlenfeld liegt kein Ei. '
        'Klicken setzt oder entfernt ein Ei; mit Notizen lassen sich freie Felder durchstreichen.',
        nest_model(regions, clues), solution, {key: 0 for key in clues},
        dict(kind='nest', size=6, regions=regions, labels=clues), seed, difficulty)
