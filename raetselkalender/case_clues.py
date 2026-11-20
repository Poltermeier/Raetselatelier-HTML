"""Original spatial clue templates and local deductions for the case generator."""
from dataclasses import dataclass
from itertools import combinations, product

from .solver import Constraint, Sum, Table

COLUMNS = "ABCDE"
NUMBERS = ("null", "eine", "zwei", "drei", "vier", "fünf")


@dataclass(frozen=True)
class Clue:
    text: str
    rule: Constraint
    kind: str
    anchors: tuple[str, ...] = ()

    def export(self):
        return dict(text=self.text, people=list(self.rule.keys))


@dataclass(frozen=True)
class Scope:
    keys: tuple[str, ...]
    where: str
    kind: str
    anchors: tuple[str, ...] = ()


def count_clue(scope, total):
    phrase = ("ist niemand schuldig." if total == 0 else "ist genau eine Person schuldig."
              if total == 1 else f"sind genau {NUMBERS[total]} Personen schuldig.")
    where = scope.where[0].upper() + scope.where[1:]
    return Clue(f"{where} {phrase}", Sum(scope.keys, total), scope.kind, scope.anchors)


def parity_clue(scope, total):
    odd = total % 2
    parity = "ungerade" if odd else "gerade"
    rows = tuple(values for values in product((0, 1), repeat=len(scope.keys)) if sum(values) % 2 == odd)
    text = f"Die Zahl der Schuldigen {scope.where} ist {parity}."
    return Clue(text, Table(scope.keys, rows), "parity", scope.anchors)


def comparison_clue(first, second, solution):
    first_total = sum(solution[key] for key in first.keys)
    second_total = sum(solution[key] for key in second.keys)
    if first_total < second_total:
        first, second = second, first
    difference = abs(first_total - second_total)
    if difference > 2:
        return None
    keys = tuple(dict.fromkeys((*first.keys, *second.keys)))
    coefficients = tuple(int(key in first.keys) - int(key in second.keys) for key in keys)
    rows = tuple(values for values in product((0, 1), repeat=len(keys))
                 if sum(coefficient * value for coefficient, value in zip(coefficients, values)) == difference)
    if difference:
        text = f"Es gibt {NUMBERS[difference]} Schuldige mehr {first.where} als {second.where}."
        if difference == 1:
            text = f"Es gibt eine schuldige Person mehr {first.where} als {second.where}."
    else:
        text = f"Es gibt {first.where} genauso viele Schuldige wie {second.where}."
    return Clue(text, Table(keys, rows), "comparison")


def adjacent_run(values):
    occupied = [index for index, value in enumerate(values) if value]
    return len(occupied) >= 2 and occupied[-1] - occupied[0] + 1 == len(occupied)


def position_clues(areas, rooms, solution):
    rows = [Scope(row, f"in Reihe „{room}“", "row") for row, room in zip(areas, rooms)]
    columns = [Scope(column, f"in Spalte {COLUMNS[i]}", "column") for i, column in enumerate(zip(*areas))]
    positions = {name: (r, c) for r, row in enumerate(areas) for c, name in enumerate(row)}
    names = tuple(positions)
    neighbors = {name: tuple(other for other, (r2, c2) in positions.items() if abs(r - r2) + abs(c - c2) == 1)
                 for name, (r, c) in positions.items()}
    scopes = rows + columns
    for name, adjacent in neighbors.items():
        scopes.append(Scope(adjacent, f"unter den direkten Nachbarn von {name}", "neighbors", (name,)))
    for first, second in combinations(names, 2):
        common = tuple(name for name in neighbors[first] if name in neighbors[second])
        if len(common) == 2:
            scopes.append(Scope(common, f"unter den gemeinsamen direkten Nachbarn von {first} und {second}",
                                "shared", (first, second)))
        r, c = positions[first]
        rr, cc = positions[second]
        if r == rr and cc - c >= 3:
            scopes.append(Scope(areas[r][c + 1:cc], f"zwischen {first} und {second}", "between", (first, second)))
        elif c == cc and rr - r >= 3:
            scopes.append(Scope(tuple(areas[row][c] for row in range(r + 1, rr)),
                                f"zwischen {first} und {second}", "between", (first, second)))

    counts = [(scope, sum(solution[name] for name in scope.keys)) for scope in scopes]
    clues = [count_clue(scope, total) for scope, total in counts]
    for first, second in [*combinations(rows, 2), *combinations(columns, 2)]:
        clue = comparison_clue(first, second, solution)
        if clue:
            clues.append(clue)
    for scope in rows + columns:
        values = tuple(solution[name] for name in scope.keys)
        if adjacent_run(values):
            patterns = tuple(bits for bits in product((0, 1), repeat=len(values)) if adjacent_run(bits))
            text = f"Die Schuldigen {scope.where} bilden eine lückenlose Gruppe aus mindestens zwei Personen."
        elif all(not (a and b) for a, b in zip(values, values[1:])):
            patterns = tuple(bits for bits in product((0, 1), repeat=len(values))
                             if all(not (a and b) for a, b in zip(bits, bits[1:])))
            text = f"Keine zwei Schuldigen {scope.where} sitzen direkt nebeneinander."
        else:
            continue
        clues.append(Clue(text, Table(scope.keys, patterns), "sequence"))
    return scopes, clues, neighbors


def consequence(clue, known):
    domains = {name: {known[name]} if name in known else {0, 1} for name in clue.rule.keys}
    clue.rule.reduce(domains)
    return {name for name, values in domains.items() if len(values) == 1 and name not in known}


def paired_counts(scopes, known, solution):
    """Two individually open counts can force the difference of their scopes."""
    options = []
    for scope in scopes:
        unknown = frozenset(name for name in scope.keys if name not in known)
        total = sum(solution[name] for name in unknown)
        if 0 < total < len(unknown):
            options.append((scope, unknown, total))
    for small, keys, total in options:
        for large, other, other_total in options:
            if keys < other and other_total - total in (0, len(other - keys)):
                yield (count_clue(small, sum(solution[key] for key in small.keys)),
                       count_clue(large, sum(solution[key] for key in large.keys)), other - keys)
