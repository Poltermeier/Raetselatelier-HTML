"""Irregular island layouts and connected, noncrossing bridge networks."""
from collections import Counter


def island_layout(rng, size, count):
    # Anchor the full board; grow along existing rows/columns so every island
    # remains reachable through nearest-neighbor visibility.
    last = size-1
    points = [(0, 0), (0, last), (last, 0), (last, last)]
    rows, cols = {r for r, c in points}, {c for r, c in points}
    blocked = set()
    def occupy(r, c):
        blocked.update(((r, c), (r-1, c), (r+1, c), (r, c-1), (r, c+1)))
    for p in points:
        occupy(*p)
    while len(points) < count:
        options = [(r, c) for r in range(size) for c in range(size)
                   if (r in rows or c in cols) and (r, c) not in blocked]
        if not options:
            return None
        weights = [1+3*(r not in rows)+3*(c not in cols) for r, c in options]
        r, c = rng.choices(options, weights=weights, k=1)[0]
        points.append((r, c))
        occupy(r, c)
        rows.add(r)
        cols.add(c)
    if any(len({p[axis] for p in points}) < 7 for axis in (0, 1)):
        return None
    points.sort()
    edges = []
    for p in points:
        for axis in (0, 1):
            visible = [q for q in points if q[1-axis] == p[1-axis] and q[axis] > p[axis]]
            if visible:
                edges.append((p, min(visible)))
    crossings = []
    for i, ((r, c), (rr, cc)) in enumerate(edges):
        for j, ((s, t), (ss, tt)) in enumerate(edges[:i]):
            if (r == rr and t == tt and c < t < cc and s < r < ss
                    or c == cc and s == ss and t < c < tt and r < s < rr):
                crossings.append((i, j))
    return points, edges, crossings


def bridge_assignment(rng, points, edges, crossings):
    conflicts = {i: set() for i in range(len(edges))}
    for i, j in crossings:
        conflicts[i].add(j)
        conflicts[j].add(i)
    order = list(range(len(edges)))
    rng.shuffle(order)
    order.sort(key=lambda i: sum(abs(a-b) for a, b in zip(*edges[i]))+rng.random()*3)
    groups = {p: {p} for p in points}
    used = set()
    # Connect every island before adding loops, so an optional crossing path
    # cannot prematurely block a connection needed by the spanning tree.
    for i in order:
        a, b = edges[i]
        if not used & conflicts[i] and groups[a] is not groups[b]:
            used.add(i)
            union = groups[a] | groups[b]
            for p in union:
                groups[p] = union
    if len(groups[points[0]]) != len(points):
        return None
    for i in order:
        if i not in used and not used & conflicts[i] and rng.random() < .5:
            used.add(i)
    degrees = Counter(p for i in used for p in edges[i])
    if len(used) < len(points) or sum(degree >= 3 for degree in degrees.values()) < 4:
        return None
    values = {i: rng.randint(1, 3) if i in used else 0 for i in range(len(edges))}
    return values if 3 in values.values() else None
