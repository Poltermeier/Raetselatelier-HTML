"""Local degree rules and graph deductions for loops and paired paths."""
from collections import Counter

from .solver import Contradiction, restrict


class RouteTopology:
    def __init__(self, edges, terminals=None):
        self.edges = tuple((k, a, b) for k, a, b in edges)
        self.keys = tuple(k for k, a, b in edges)
        self.terminals = terminals

    def reduce(self, domains):
        possible, selected = {}, {}
        for key, a, b in self.edges:
            if 1 in domains[key]:
                possible.setdefault(a, []).append((b, key))
                possible.setdefault(b, []).append((a, key))
            if domains[key] == {1}:
                selected.setdefault(a, set()).add(b)
                selected.setdefault(b, set()).add(a)
        if not possible:
            raise Contradiction
        owner, components = {}, []
        for start in selected:
            if start in owner:
                continue
            component, pending = set(), [start]
            while pending:
                v = pending.pop()
                if v in component:
                    continue
                component.add(v)
                pending.extend(selected[v]-component)
            for v in component:
                owner[v] = len(components)
            components.append(component)
        for component in components:
            closed = all(len(selected[v]) == 2 for v in component)
            if self.terminals is None:
                if closed:
                    if len(component) != len(selected):
                        raise Contradiction
                    for key, a, b in self.edges:
                        if a not in component or b not in component:
                            restrict(domains, key, {0})
            else:
                labels = [self.terminals[v] for v in component if v in self.terminals]
                if closed or len(labels) > 2 or len(set(labels)) > 1:
                    raise Contradiction
        for key, a, b in self.edges:
            if domains[key] != {0, 1}:
                continue
            ca, cb = owner.get(a), owner.get(b)
            if ca is not None and ca == cb:
                if self.terminals is not None or len(components[ca]) < len(selected):
                    restrict(domains, key, {0})
            elif self.terminals is not None:
                merged = (components[ca] if ca is not None else {a}) | (components[cb] if cb is not None else {b})
                labels = [self.terminals[v] for v in merged if v in self.terminals]
                if len(labels) > 2 or len(set(labels)) > 1:
                    restrict(domains, key, {0})
        # A possible bridge cannot belong to a closed loop. For paired paths,
        # the parity of terminal counts on either side determines the bridge.
        order, low, seen_components = {}, {}, []
        timer = 0
        bridges = []
        def visit(v, incoming=None):
            nonlocal timer
            timer += 1
            order[v] = low[v] = timer
            nodes = {v}
            terminal_count = int(self.terminals is not None and v in self.terminals)
            for other, key in possible.get(v, []):
                if key == incoming or 1 not in domains[key]:
                    continue
                if other not in order:
                    descendants, count = visit(other, key)
                    nodes.update(descendants)
                    terminal_count += count
                    low[v] = min(low[v], low[other])
                    if low[other] > order[v]:
                        bridges.append((key, count))
                else:
                    low[v] = min(low[v], order[other])
            return nodes, terminal_count
        for v in possible:
            if v not in order:
                component, count = visit(v)
                seen_components.append(component)
                if self.terminals is not None:
                    labels = Counter(self.terminals[k] for k in component if k in self.terminals)
                    if not labels or any(n != 2 for n in labels.values()):
                        raise Contradiction
        if self.terminals is None and selected:
            if not any(set(selected) <= group for group in seen_components):
                raise Contradiction
        for key, count in bridges:
            restrict(domains, key, {count % 2 if self.terminals is not None else 0})
