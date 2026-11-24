"""Verified distance paths, sum/product grids and reversible rotations."""
from fractions import Fraction
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
        raise LogicalProofMissing("Keine eindeutige Distance-Anordnung gefunden.")
    keys = [f"{y},{x}" for x, y in points]
    solution = {keys[index]: value for value, index in enumerate(paths[0], 1)}
    model = Model({key: set(range(1, count+1)) for key in keys}, [])
    rules = (f"Trage die Zahlen 1 bis {count} je einmal ein. Die Luftlinie zwischen zwei aufeinanderfolgenden Zahlen "
             "muss jedes Mal länger werden. Auch diagonale Abstände zählen. Gleiche Längen sind ausgeschlossen.")
    return Puzzle("distance", "Distance", rules, model, solution, {},
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


def sum_product(seed, difficulty):
    rng = random.Random(seed)
    hard = difficulty == "schwer"
    cols, ceiling = (4, 34) if hard else (3, 14)
    for _ in range(6000):
        a, *bottom = rng.sample(range(2, ceiling), cols)
        rows = sum_product_completion(a, bottom)
        if rows and max(map(max, rows)) <= (999 if hard else 100):
            break
    else:
        raise LogicalProofMissing("Keine passende Summe-Produkt-Matrix gefunden.")
    clue_row = rng.randrange(2)
    order = list(range(cols))
    rng.shuffle(order)
    solution, givens = {}, {}
    for r in range(2):
        for c, original in enumerate(order):
            key = f"{r},{c}"
            solution[key] = rows[r ^ clue_row][original]
            if (r == clue_row) == (original == 0):
                givens[key] = solution[key]
    model = Model({key: {givens[key]} if key in givens else set(range(1, 1000)) for key in solution}, [])
    rules = ("Fülle die Matrix mit verschiedenen positiven ganzen Zahlen. Beide Zeilen haben dieselbe Summe. "
             "Alle Spalten haben dasselbe Produkt. Die gemeinsamen Werte ergeben sich aus den Vorgaben.")
    return Puzzle("summe-produkt", "Summe Produkt", rules, model, solution, givens,
                  dict(kind="grid", size=cols, rows=2, cols=cols, cell_size=76), seed, difficulty,
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
