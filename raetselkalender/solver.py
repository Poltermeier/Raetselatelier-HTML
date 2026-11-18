"""Exact finite-domain search. A timeout is never evidence of uniqueness."""
from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property, lru_cache
from collections import deque
from itertools import combinations
import random
import time
from typing import Protocol

Domains = dict[str, set[int]]


class Contradiction(Exception):
    pass


class SearchLimit(RuntimeError):
    pass


class Constraint(Protocol):
    keys: tuple[str, ...]

    def reduce(self, domains: Domains) -> None: ...


def restrict(domains: Domains, key: str, values: set[int]) -> None:
    domains[key] &= values
    if not domains[key]:
        raise Contradiction


@dataclass(frozen=True)
class AllDifferent:
    keys: tuple[str, ...]

    def reduce(self, domains: Domains) -> None:
        singles = [next(iter(domains[k])) for k in self.keys if len(domains[k]) == 1]
        if len(singles) != len(set(singles)):
            raise Contradiction
        used = set(singles)
        for k in self.keys:
            if len(domains[k]) > 1:
                restrict(domains, k, domains[k] - used)
        union = set().union(*(domains[k] for k in self.keys))
        if len(union) < len(self.keys):
            raise Contradiction
        if len(union) == len(self.keys):
            for v in union:
                places = [k for k in self.keys if v in domains[k]]
                if len(places) == 1:
                    restrict(domains, places[0], {v})
        # Hall pairs improve grid puzzles without changing completeness of search.
        pairs = {frozenset(domains[k]) for k in self.keys if len(domains[k]) == 2}
        for pair in pairs:
            owners = [k for k in self.keys if domains[k] == pair]
            if len(owners) == 2:
                for k in self.keys:
                    if k not in owners:
                        restrict(domains, k, domains[k] - pair)


@dataclass(frozen=True)
class Table:
    keys: tuple[str, ...]
    rows: tuple[tuple[int, ...], ...]

    @cached_property
    def supports(self):
        return table_supports(self.rows, len(self.keys))

    def reduce(self, domains: Domains) -> None:
        supports = self.supports
        possible = (1 << len(self.rows))-1
        for key, index in zip(self.keys, supports):
            allowed = 0
            for value in domains[key]:
                allowed |= index.get(value, 0)
            possible &= allowed
            if not possible:
                raise Contradiction
        if not possible:
            raise Contradiction
        for key, index in zip(self.keys, supports):
            restrict(domains, key, {v for v in domains[key] if possible & index.get(v, 0)})


@lru_cache(maxsize=256)
def table_supports(rows, width):
    """Bitsets share compiled patterns between constraints, not mutable domains."""
    indexes = tuple({} for _ in range(width))
    for i, row in enumerate(rows):
        bit = 1 << i
        for index, value in zip(indexes, row):
            index[value] = index.get(value, 0) | bit
    return indexes


@dataclass(frozen=True)
class Sum:
    keys: tuple[str, ...]
    total: int

    def reduce(self, domains: Domains) -> None:
        bounds = [(min(domains[k]), max(domains[k])) for k in self.keys]
        low = sum(a for a, b in bounds)
        high = sum(b for a, b in bounds)
        if not low <= self.total <= high:
            raise Contradiction
        for k, (a, b) in zip(self.keys, bounds):
            restrict(domains, k, {v for v in domains[k]
                     if low - a + v <= self.total <= high - b + v})


@dataclass(frozen=True)
class ConnectedEdges:
    """Hashi: even potentially nonzero edges must connect every island."""
    keys: tuple[str, ...]
    endpoints: tuple[tuple[str, str], ...]
    vertices: tuple[str, ...]

    def reduce(self, domains: Domains) -> None:
        graph: dict[str, set[str]] = {v: set() for v in self.vertices}
        for k, (a, b) in zip(self.keys, self.endpoints):
            if max(domains[k]) > 0:
                graph[a].add(b)
                graph[b].add(a)
        seen = {self.vertices[0]}
        todo = list(seen)
        while todo:
            for other in graph[todo.pop()] - seen:
                seen.add(other)
                todo.append(other)
        if len(seen) != len(self.vertices):
            raise Contradiction


@dataclass
class Model:
    domains: Domains
    constraints: list[Constraint]


@dataclass
class SearchResult:
    solutions: list[dict[str, int]]
    nodes: int
    branches: int


class Propagation:
    """Revisit only rules touched by changed candidates; never choose a value."""
    def __init__(self, model):
        self.constraints = model.constraints
        self.watching = {k: [] for k in model.domains}
        for i, constraint in enumerate(self.constraints):
            for key in constraint.keys:
                self.watching[key].append(i)

    def run(self, domains, deadline, steps=None):
        if time.monotonic() > deadline:
            raise SearchLimit("Zeitlimit bei der Regelprüfung erreicht")
        queue = deque(range(len(self.constraints)))
        queued = set(queue)
        while queue:
            if time.monotonic() > deadline:
                raise SearchLimit("Zeitlimit bei der Regelprüfung erreicht")
            i = queue.popleft()
            queued.remove(i)
            constraint = self.constraints[i]
            before = [len(domains[k]) for k in constraint.keys]
            previous = {k: domains[k].copy() for k in constraint.keys} if steps is not None else None
            constraint.reduce(domains)
            changed = [k for k, n in zip(constraint.keys, before) if len(domains[k]) != n]
            if changed and steps is not None:
                steps.append(dict(rule=type(constraint).__name__, constraint=i,
                                  removed={k: sorted(previous[k]-domains[k]) for k in changed}))
            for key in changed:
                for neighbor in self.watching[key]:
                    if neighbor not in queued:
                        queue.append(neighbor)
                        queued.add(neighbor)
        if time.monotonic() > deadline:
            raise SearchLimit("Zeitlimit bei der Regelprüfung erreicht")


@dataclass
class LogicalResult:
    status: str
    domains: Domains
    steps: list[dict]

    @property
    def solved(self):
        return self.status == "solved"


def deduce(model: Model, givens=None, *, seconds=4, trace=True):
    """Apply only forced rule eliminations. No search, trial values or solution input.

    Stalled means these rules cannot prove completion; it is not a claim that
    the puzzle is impossible. Time limits likewise never count as a proof.
    """
    domains = {k: set(v) for k, v in model.domains.items()}
    steps = []
    for key, value in (givens or {}).items():
        if key not in domains or value not in domains[key]:
            return LogicalResult("contradiction", domains, steps)
        domains[key] = {value}
    try:
        if any(not values for values in domains.values()):
            raise Contradiction
        Propagation(model).run(domains, time.monotonic()+seconds, steps if trace else None)
    except Contradiction:
        return LogicalResult("contradiction", domains, steps)
    except SearchLimit:
        return LogicalResult("timeout", domains, steps)
    return LogicalResult("solved" if all(len(v) == 1 for v in domains.values()) else "stalled", domains, steps)


def solve(model: Model, givens: dict[str, int] | None = None, *, limit: int = 2,
          seconds: float = 8, rng: random.Random | None = None) -> SearchResult:
    """Enumerate up to limit solutions. Exhaustive unless limit reached or raised."""
    if limit < 1:
        raise ValueError("limit must be positive")
    domains = {k: set(v) for k, v in model.domains.items()}
    if any(not values for values in domains.values()):
        return SearchResult([], 0, 0)
    for k, v in (givens or {}).items():
        if k not in domains or v not in domains[k]:
            return SearchResult([], 0, 0)
        domains[k] = {v}
    deadline = time.monotonic() + seconds
    result = SearchResult([], 0, 0)
    propagation = Propagation(model)
    degree = {k: len(watching) for k, watching in propagation.watching.items()}

    def visit(ds: Domains) -> None:
        if time.monotonic() > deadline:
            raise SearchLimit("Zeitlimit beim Lösungsnachweis erreicht")
        result.nodes += 1
        try:
            propagation.run(ds, deadline)
        except Contradiction:
            return
        open_keys = [k for k in ds if len(ds[k]) > 1]
        if not open_keys:
            result.solutions.append({k: next(iter(v)) for k, v in ds.items()})
            return
        key = min(open_keys, key=lambda k: (len(ds[k]), -degree[k]))
        values = sorted(ds[key])
        if rng is not None:
            rng.shuffle(values)
        result.branches += 1
        for v in values:
            child = {k: set(s) for k, s in ds.items()}
            child[key] = {v}
            visit(child)
            if len(result.solutions) >= limit:
                return

    visit(domains)
    return result


def unequal(a: str, b: str, values=range(1, 10)) -> Table:
    return Table((a, b), tuple((x, y) for x in values for y in values if x != y))
