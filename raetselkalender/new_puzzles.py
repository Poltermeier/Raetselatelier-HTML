"""Verified distance paths, sum/product grids and reversible rotations."""
from collections import defaultdict
from fractions import Fraction
from functools import lru_cache
from itertools import combinations, permutations, product
from math import prod
import random

from .puzzle import LogicalProofMissing, Puzzle
from .solver import Model


def distance_paths(points, limit=2):
    """Enumerate strictly increasing paths using squared Euclidean distances."""
    count = len(points)
    edges = [sorted(((x-u)**2 + (y-v)**2, j)
                    for j, (u, v) in enumerate(points) if j != i)
             for i, (x, y) in enumerate(points)]
    full = (1 << count) - 1
    found = []

    def visit(path, used, previous):
        if used == full:
            found.append(path)
            return
        for length, target in edges[path[-1]]:
            if length > previous and not used & (1 << target):
                visit((*path, target), used | (1 << target), length)
                if len(found) >= limit:
                    return

    for start in range(count):
        visit((start,), 1 << start, 0)
        if len(found) >= limit:
            break
    return found


def distance(seed, difficulty):
    rng = random.Random(seed)
    count, rows, cols = (6, 3, 4) if difficulty == "mittel" else (9, 4, 5)
    grid = [(x, y) for y in range(rows) for x in range(cols)]
    for _ in range(1000):
        points = sorted(rng.sample(grid, count), key=lambda point: point[::-1])
        if (len({x for x, _ in points}) < cols or len({y for _, y in points}) < rows):
            continue
        paths = distance_paths(points)
        if len(paths) == 1:
            break
    else:
        raise LogicalProofMissing("Keine eindeutige Distanz-Anordnung gefunden.")
    keys = [f"{y},{x}" for x, y in points]
    solution = {keys[index]: value for value, index in enumerate(paths[0], 1)}
    model = Model({key: set(range(1, count+1)) for key in keys}, [])
    rules = (f"Trage die Zahlen 1 bis {count} je einmal ein. Die Luftlinie zwischen zwei aufeinanderfolgenden Zahlen "
             "muss jedes Mal länger werden. Auch diagonale Abstände zählen. Gleiche Längen sind ausgeschlossen.")
    return Puzzle("distance", "Distanz", rules, model, solution, {},
                  dict(kind="distance", points=points, rows=rows, cols=cols), seed, difficulty,
                  analysis=dict(unique=True, solution_method="exhaustive_distance_paths"))


def sum_product_completion(a, bottom):
    """Solve P from a + sum(P / b) = P / a + sum(b)."""
    coefficient = sum(Fraction(1, b) for b in bottom) - Fraction(1, a)
    if not coefficient:
        return None
    product = Fraction(sum(bottom)-a, coefficient)
    top = [Fraction(a), *(product / b for b in bottom)]
    lower = [product / a, *map(Fraction, bottom)]
    values = top + lower
    if any(x < 1 or x.denominator != 1 for x in values) or len(set(values)) != len(values):
        return None
    return tuple(tuple(map(int, row)) for row in (top, lower))


@lru_cache(maxsize=2)
def balanced_matrices(height, maximum):
    groups = defaultdict(list)
    for values in combinations(range(1, maximum+1), height):
        groups[prod(values)].append(values)
    boards = []
    for columns in groups.values():
        for first, second, third in combinations(columns, 3):
            values = first + second + third
            if len(set(values)) != len(values) or sum(values) % height:
                continue
            total = sum(values)//height
            for middle in permutations(second):
                last = tuple(total-a-b for a, b in zip(first, middle))
                if tuple(sorted(last)) == third:
                    boards.append(tuple(zip(first, middle, last)))
    return tuple(boards)


def complete_three_rows(first, left):
    total = sum(first)
    common = first[0]*left[0]*left[1]
    found = []
    for a in range(1, total-left[0]):
        b = total-left[0]-a
        if common % (first[1]*a) or common % (first[2]*b):
            continue
        lower = (left[1], common//(first[1]*a), common//(first[2]*b))
        middle = (left[0], a, b)
        if sum(lower) == total and len(set(first+middle+lower)) == 9:
            found.append((first, middle, lower))
    return found


def sum_product(seed, difficulty):
    rng = random.Random(seed)
    if difficulty == "mittel":
        boards = balanced_matrices(2, 26)
        board = rng.choice(boards)
        row_order = rng.sample(range(2), 2)
        col_order = rng.sample(range(3), 3)
        board = tuple(tuple(board[r][c] for c in col_order) for r in row_order)
        full_column = rng.randrange(3)
        clues = {(0, full_column), (1, full_column)}
        clues.update((rng.randrange(2), c) for c in range(3) if c != full_column)
    elif rng.randrange(2):
        boards = balanced_matrices(3, 36)
        for _ in range(100):
            board = rng.choice(boards)
            row_order = rng.sample(range(3), 3)
            col_order = rng.sample(range(3), 3)
            board = tuple(tuple(board[r][c] for c in col_order) for r in row_order)
            if complete_three_rows(board[0], (board[1][0], board[2][0])) == [board]:
                break
        else:
            raise LogicalProofMissing("Keine eindeutige 3 × 3-Matrix gefunden.")
        clues = {(r, c) for r in range(3) for c in range(3) if r == 0 or c == 0}
        # Scatter the reference row and column after proving uniqueness.
        row_order = rng.sample(range(3), 3)
        col_order = rng.sample(range(3), 3)
        board = tuple(tuple(board[r][c] for c in col_order) for r in row_order)
        clues = {(r, c) for r in range(3) for c in range(3) if (row_order[r], col_order[c]) in clues}
    else:
        for _ in range(6000):
            a, *bottom = rng.sample(range(2, 34), 4)
            board = sum_product_completion(a, bottom)
            if board and max(map(max, board)) <= 999:
                break
        else:
            raise LogicalProofMissing("Keine passende Summe-Produkt-Matrix gefunden.")
        clue_row = rng.randrange(2)
        order = rng.sample(range(4), 4)
        board = tuple(tuple(board[r ^ clue_row][c] for c in order) for r in range(2))
        clues = {(r, c) for r in range(2) for c in range(4) if (r == clue_row) == (order[c] == 0)}
    rows, cols = len(board), len(board[0])
    solution = {f"{r},{c}": value for r, row in enumerate(board) for c, value in enumerate(row)}
    givens = {f"{r},{c}": board[r][c] for r, c in clues}
    model = Model({key: {givens[key]} if key in givens else set(range(1, 1000)) for key in solution}, [])
    rules = ("Fülle die Matrix mit verschiedenen positiven ganzen Zahlen. Alle Zeilen haben dieselbe Summe. "
             "Alle Spalten haben dasselbe Produkt.")
    return Puzzle("summe-produkt", "Summe Produkt", rules, model, solution, givens,
                  dict(kind="grid", size=cols, rows=rows, cols=cols, cell_size=76), seed, difficulty,
                  analysis=dict(unique=True, solution_method="exact_common_product_equation"))


def rotate_block(board, size, block, action):
    r, c, direction = action
    following = list(board)
    for dr in range(block):
        for dc in range(block):
            nr, nc = (dc, block-1-dr) if direction == 1 else (block-1-dc, dr)
            following[(r+nr)*size+c+nc] = board[(r+dr)*size+c+dc]
    return tuple(following)


def inverse_turns(moves):
    return [(r, c, -direction) for r, c, direction in reversed(moves)]


def twiddle(seed, difficulty):
    rng = random.Random(seed)
    size, block, turns = (3, 2, 5) if difficulty == "mittel" else (4, 3, 10)
    target = tuple(range(1, size*size+1))
    anchors = [(r, c) for r in range(size-block+1) for c in range(size-block+1)]
    minimum_misplaced = 5 if size == 3 else 10
    for _ in range(100):
        board, scramble = target, []
        for _ in range(turns):
            r, c = rng.choice([pair for pair in anchors if not scramble or pair != scramble[-1][:2]])
            action = (r, c, rng.choice((-1, 1)))
            scramble.append(action)
            board = rotate_block(board, size, block, action)
        if sum(a != b for a, b in zip(board, target)) >= minimum_misplaced:
            break
    else:
        raise LogicalProofMissing("Keine ausreichend gemischte Twiddle-Stellung gefunden.")
    solution = dict(enumerate(inverse_turns(scramble)))
    rules = (f"Ordne die Zahlen von links oben zeilenweise von 1 bis {len(target)}. "
             f"Wähle eine Drehrichtung und drehe mit den runden Tasten jeweils einen {block} × {block}-Block um 90 Grad.")
    return Puzzle("twiddle", "Twiddle", rules, Model({}, []), solution, {},
                  dict(kind="activity", mode="twiddle", size=size, block=block, initial=board, target=target),
                  seed, difficulty, analysis=dict(solution_verified=True))
