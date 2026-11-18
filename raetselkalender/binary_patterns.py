"""Construct balanced binary grids without searching for an initial solution."""
from functools import lru_cache
from itertools import product


@lru_cache(maxsize=4)
def balanced_patterns(length):
    return tuple(bits for bits in product((0, 1), repeat=length)
                 if sum(bits) == length//2
                 and all(len(set(bits[i:i+3])) != 1 for i in range(length-2)))


def binary_grid(rng, rows, cols):
    # Complement pairs provide balance in every row and avoid horizontal
    # triples; each column is already a valid, distinct balanced pattern.
    pairs = [pattern for pattern in balanced_patterns(rows) if pattern[0] == 0]
    if rows % 2 or cols % 2 or cols//2 > len(pairs):
        raise ValueError('Nicht unterstützte Binärfeldgröße')
    columns = []
    for pattern in rng.sample(pairs, cols//2):
        complement = tuple(1-bit for bit in pattern)
        columns.extend((pattern, complement) if rng.randrange(2) else (complement, pattern))
    grid = [list(line) for line in zip(*columns)]

    def no_triples(lines):
        return all(not a == b == c for line in lines for a, b, c in zip(line, line[1:], line[2:]))

    # Valid swaps dissolve the initial pairing and vary both axes without
    # ever falling back to an expensive search for a starting grid.
    for _ in range(80):
        vertical = bool(rng.randrange(2))
        a, b = rng.sample(range(rows if vertical else cols), 2)
        if vertical:
            grid[a], grid[b] = grid[b], grid[a]
            if not no_triples(zip(*grid)):
                grid[a], grid[b] = grid[b], grid[a]
        else:
            for row in grid:
                row[a], row[b] = row[b], row[a]
            if not no_triples(grid):
                for row in grid:
                    row[a], row[b] = row[b], row[a]
    if len({tuple(row) for row in grid}) != rows:
        raise ValueError('Die Binärzeilen müssen verschieden sein')
    return {f'{r},{c}': grid[r][c] for r in range(rows) for c in range(cols)}
