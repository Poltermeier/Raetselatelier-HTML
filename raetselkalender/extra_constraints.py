"""Rules used by the calendar variants, without UI dependencies."""
from dataclasses import dataclass
from itertools import combinations

from .solver import AllDifferent, Contradiction, restrict


class HallDifferent(AllDifferent):
    """All-different with complete Hall-set deductions for small symbol groups."""
    def reduce(self, domains):
        super().reduce(domains)
        pending = [k for k in self.keys if len(domains[k]) > 1]
        for size in range(2, len(pending)):
            for group in combinations(pending, size):
                union = set().union(*(domains[k] for k in group))
                if len(union) < size:
                    raise Contradiction
                if len(union) == size:
                    for key in pending:
                        if key not in group:
                            restrict(domains, key, domains[key]-union)


class RelationshipOrder:
    """Locate consecutive numbers in the complement of the connection graph.

    Every number is used once: v-1 and v+1 need two distinct circles that are
    not connected to v. This is a rule deduction, not a trial assignment.
    """
    def __init__(self, keys, edges):
        self.keys = tuple(keys)
        self.allowed = {k: set(keys)-{k} for k in keys}
        for a, b in edges:
            self.allowed[a].discard(b)
            self.allowed[b].discard(a)

    def reduce(self, domains):
        n = len(self.keys)
        for key in self.keys:
            possible = set()
            for value in domains[key]:
                before = {k for k in self.allowed[key] if value-1 in domains[k]} if value > 1 else None
                after = {k for k in self.allowed[key] if value+1 in domains[k]} if value < n else None
                if before is not None and not before or after is not None and not after:
                    continue
                if before is not None and after is not None and len(before | after) < 2:
                    continue
                possible.add(value)
            restrict(domains, key, possible)


@dataclass(frozen=True)
class Counts:
    keys: tuple[str, ...]
    counts: tuple[tuple[int, int], ...]

    def reduce(self, domains):
        for value, count in self.counts:
            fixed = [k for k in self.keys if domains[k] == {value}]
            possible = [k for k in self.keys if value in domains[k]]
            if len(fixed) > count or len(possible) < count:
                raise Contradiction
            if len(fixed) == count:
                for key in possible:
                    if key not in fixed:
                        restrict(domains, key, domains[key] - {value})
            elif len(possible) == count:
                for key in possible:
                    restrict(domains, key, {value})


@dataclass(frozen=True)
class ContainsAll:
    keys: tuple[str, ...]
    required: frozenset[int]

    def reduce(self, domains):
        for key in self.keys:
            restrict(domains, key, set(self.required))
        for value in self.required:
            possible = [k for k in self.keys if value in domains[k]]
            if not possible:
                raise Contradiction
            if len(possible) == 1:
                restrict(domains, possible[0], {value})


class RectangleCover:
    """Each clue chooses a rectangle; each board cell has exactly one owner."""
    def __init__(self, candidates, rows, cols):
        self.keys = tuple(candidates)
        self.covered = {k: [frozenset((rr, cc) for rr in range(r, r+h)
                                    for cc in range(c, c+w)) for r, c, h, w in options]
                        for k, options in candidates.items()}
        self.cells = tuple((r, c) for r in range(rows) for c in range(cols))

    def reduce(self, domains):
        for cell in self.cells:
            owners = {k: {i for i in domains[k] if cell in self.covered[k][i]}
                      for k in self.keys}
            owners = {k: ids for k, ids in owners.items() if ids}
            if not owners:
                raise Contradiction
            mandatory = [k for k, ids in owners.items() if ids == domains[k]]
            if len(mandatory) > 1:
                raise Contradiction
            if len(owners) == 1:
                key = next(iter(owners))
                restrict(domains, key, owners[key])
            elif mandatory:
                for key, ids in owners.items():
                    if key != mandatory[0]:
                        restrict(domains, key, domains[key] - ids)
