"""Calendar-style equations, always using the known center number."""
from dataclasses import dataclass
from functools import lru_cache
from itertools import combinations, permutations, product

from .solver import Table


@lru_cache(maxsize=12)
def allowed_rows(kind, center):
    arity = 2 if kind in ("difference", "ratio") else 3
    rows = []
    for values in product(range(1, 10), repeat=arity):
        if center in values or len(set(values)) != arity:
            continue
        a, b = values[:2]
        if kind == "difference": valid = center == a-b
        elif kind == "ratio": valid = a == center*b
        elif kind == "sum": valid = center+a == b+values[2]
        elif kind == "product": valid = center*a == b*values[2]
        else: raise ValueError(f"Unbekannte Windrosen-Gleichung: {kind}")
        if valid:
            rows.append(values)
    return tuple(rows)


@dataclass(frozen=True)
class CompassEquation:
    kind: str
    directions: tuple[str, ...]

    def text(self, center):
        a, b = self.directions[:2]
        if self.kind == "difference": return f"{center} = {a} - {b}"
        if self.kind == "ratio": return f"{center} = {a} : {b}"
        c = self.directions[2]
        op = "+" if self.kind == "sum" else "×"
        return f"{center} {op} {a} = {b} {op} {c}"

    def table(self, center):
        return Table(self.directions, allowed_rows(self.kind, center))


def candidate_equations(solution):
    center = solution["Mitte"]
    directions = [key for key in solution if key != "Mitte"]
    candidates = []
    for a, b in permutations(directions, 2):
        if solution[a]-solution[b] == center:
            candidates.append(CompassEquation("difference", (a, b)))
        if solution[a] == center*solution[b]:
            candidates.append(CompassEquation("ratio", (a, b)))
    for a in directions:
        for b, c in combinations([key for key in directions if key != a], 2):
            if center+solution[a] == solution[b]+solution[c]:
                candidates.append(CompassEquation("sum", (a, b, c)))
            if center*solution[a] == solution[b]*solution[c]:
                candidates.append(CompassEquation("product", (a, b, c)))
    return candidates
