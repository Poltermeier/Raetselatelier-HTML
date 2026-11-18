"""Disjoint, noncrossing nine-pearl strings covering the complete board."""
from functools import lru_cache


def pearl_partition(solution, rng):
    regions = [frozenset(f"{br+r},{bc+c}" for r in range(3) for c in range(3))
               for br in range(0, 9, 3) for bc in range(0, 9, 3)]
    neighbors = {}
    for key in solution:
        r, c = map(int, key.split(','))
        neighbors[key] = {f"{rr},{cc}" for rr, cc in ((r-1, c), (r+1, c), (r, c-1), (r, c+1))
                          if 0 <= rr < 9 and 0 <= cc < 9}

    @lru_cache(maxsize=4096)
    def path(region):
        adjacency = {key: neighbors[key] & region for key in sorted(region)}
        leaves = [key for key in adjacency if len(adjacency[key]) == 1]
        if len(leaves) > 2 or any(not others for others in adjacency.values()):
            return None
        failed = set()
        def visit(key, remaining):
            if not remaining:
                return (key,)
            state = key, remaining
            if state in failed:
                return None
            for other in sorted(adjacency[key] & remaining):
                tail = visit(other, remaining-{other})
                if tail is not None:
                    return (key,)+tail
            failed.add(state)
            return None
        for key in leaves or sorted(region):
            result = visit(key, region-{key})
            if result is not None:
                return result
        return None

    # Equal-valued exchanges preserve every region's 1–9 set. Only accept an
    # exchange if each resulting region still has a simple orthogonal path.
    # Neighboring grid segments cannot cross, and no pearl is ever shared.
    visited = {tuple(regions)}
    for _ in range(20):
        owner = {k: i for i, region in enumerate(regions) for k in region}
        values = [{solution[k]: k for k in region} for region in regions]
        options = []
        for a in sorted(solution):
            i = owner[a]
            for j in sorted({owner[k] for k in neighbors[a]}-{i}):
                if i > j:
                    continue
                b = values[j][solution[a]]
                if not any(owner[k] == i for k in neighbors[b]):
                    continue
                first, second = regions[i]-{a}|{b}, regions[j]-{b}|{a}
                candidate = regions[:]
                candidate[i], candidate[j] = first, second
                if tuple(candidate) in visited:
                    continue
                if path(first) is not None and path(second) is not None:
                    options.append(candidate)
        if not options:
            break
        regions = rng.choice(options)
        visited.add(tuple(regions))
    paths = [list(path(region)) for region in regions]
    for string in paths:
        if rng.randrange(2):
            string.reverse()
    return paths
