"""Unique placements for Harakiri, H₂O and Schachaufstellung."""
from functools import lru_cache
from itertools import combinations
import random

from .puzzle import LogicalProofMissing, Puzzle
from .solver import AllDifferent, Model, deduce

PIECES = ("D", "T", "L", "S", "K")
PIECE_NAMES = {"K": "König", "D": "Dame", "T": "Turm", "L": "Läufer", "S": "Springer"}
ORTHOGONAL = ((-1, 0), (1, 0), (0, -1), (0, 1))
DIAGONAL = ((-1, -1), (-1, 1), (1, -1), (1, 1))


def bits(mask):
    while mask:
        bit = mask & -mask
        yield bit.bit_length()-1
        mask ^= bit


@lru_cache(maxsize=8)
def adjacency(size):
    rows = []
    for cell in range(size*size):
        r, c = divmod(cell, size)
        rows.append(tuple((r+dr)*size+c+dc for dr, dc in ORTHOGONAL
                          if 0 <= r+dr < size and 0 <= c+dc < size))
    return tuple(rows)


def harakiri(seed, difficulty):
    rng = random.Random(seed)
    rings = [tuple(f"{r},{a}" for a in range(8)) for r in range(4)]
    axes = [tuple(row[a+side] for row in rings for side in (0, 4)) for a in range(4)]
    model = Model({k: set(range(1, 9)) for row in rings for k in row}, [AllDifferent(g) for g in rings + axes])
    digits = rng.sample(range(1, 9), 8)
    pairs = rng.sample(range(4), 4)
    solution = {}
    for row, shift in zip(rings, rng.sample(range(4), 4)):
        for axis, offset in enumerate(pairs):
            start = 2*((shift+offset) % 4)
            a, b = rng.sample(digits[start:start+2], 2)
            solution[row[axis]], solution[row[axis+4]] = a, b
    givens = solution.copy()
    order = rng.sample(list(solution), 32)
    target = 20 if difficulty == "mittel" else 12
    for key in order:
        old = givens.pop(key)
        if not deduce(model, givens, trace=False).solved:
            givens[key] = old
        if len(givens) <= target:
            break
    rules = ("Trage Zahlen von 1 bis 8 ein. Jede Zahl kommt in jedem der vier Ringe und auf jedem "
             "der vier Durchmesser genau einmal vor. Ein Durchmesser verbindet gegenüberliegende Felder durch die Mitte.")
    puzzle = Puzzle("harakiri", "Harakiri", rules, model, solution, givens, {"kind": "harakiri"}, seed, difficulty)
    puzzle.certify()
    return puzzle


def water_options(size, hydrogen):
    neighbors = adjacency(size)
    pool = set(hydrogen)
    return [(center, a, b) for center in range(size*size) if center not in pool
            for a, b in combinations(sorted(n for n in neighbors[center] if n in pool), 2)]


def water_solutions(size, hydrogen, limit=2):
    options = {cell: [] for cell in hydrogen}
    for center, a, b in water_options(size, hydrogen):
        h_mask = (1 << a) | (1 << b)
        candidate = (center, a, b, h_mask)
        options[a].append(candidate)
        options[b].append(candidate)
    found = []

    def visit(remaining, oxygens, chosen):
        if not remaining:
            found.append(tuple(sorted(chosen)))
            return
        variants = min(([entry for entry in options[cell]
                         if remaining & entry[3] == entry[3] and not oxygens & (1 << entry[0])]
                        for cell in bits(remaining)), key=len)
        for center, a, b, mask in variants:
            visit(remaining ^ mask, oxygens | (1 << center), (*chosen, (center, a, b)))
            if len(found) >= limit:
                return

    visit(sum(1 << cell for cell in hydrogen), 0, ())
    return found


def water(seed, difficulty):
    rng = random.Random(seed)
    size, amount = (5, 5) if difficulty == "mittel" else (6, 7)
    triples = [(center, a, b) for center, near in enumerate(adjacency(size))
               for a, b in combinations(sorted(near), 2)]
    straight = {triple for triple in triples if 2*triple[0] == triple[1]+triple[2]}
    for _ in range(900):
        unused = set(range(size*size))
        selected = []
        for _ in range(amount):
            possible = [(o, a, b) for o, a, b in triples if o in unused and a in unused and b in unused]
            if not possible:
                break
            preferred = [triple for triple in possible if triple in straight] if rng.random() < .55 else []
            o, a, b = rng.choice(preferred or possible)
            selected.append((o, a, b))
            unused.difference_update((o, a, b))
        if len(selected) != amount:
            continue
        hydrogen = sorted(cell for _, a, b in selected for cell in (a, b))
        solutions = water_solutions(size, hydrogen)
        if len(solutions) == 1:
            break
    else:
        raise LogicalProofMissing("Keine eindeutige H₂O-Anordnung gefunden.")
    solution = {str(o): (a, b) for o, a, b in solutions[0]}
    rules = ("Verbinde jedes H genau einmal. Wähle zunächst ein leeres Feld als O, dann zwei direkt benachbarte H. "
             "Die Verbindungen verlaufen waagerecht oder senkrecht. Tippe erneut auf ein fertiges O, um das Molekül zu entfernen.")
    return Puzzle("h2o", "H₂O", rules, Model({}, []), solution, {},
                  dict(kind="activity", mode="h2o", size=size, hydrogen=hydrogen), seed, difficulty,
                  analysis=dict(unique=True, solution_method="exact_molecule_cover"))


@lru_cache(maxsize=4)
def chess_attacks(size):
    result = {}
    for piece, directions, reach in (
            ("D", ORTHOGONAL+DIAGONAL, size), ("T", ORTHOGONAL, size), ("L", DIAGONAL, size),
            ("K", ORTHOGONAL+DIAGONAL, 2),
            ("S", tuple((a*x, b*y) for x, y in ((1, 2), (2, 1)) for a in (-1, 1) for b in (-1, 1)), 2)):
        masks = []
        for cell in range(size*size):
            r, c = divmod(cell, size)
            masks.append(sum(1 << ((r+dr*i)*size+c+dc*i)
                             for dr, dc in directions for i in range(1, reach)
                             if 0 <= r+dr*i < size and 0 <= c+dc*i < size))
        result[piece] = tuple(masks)
    return result


def placement_solutions(size, clues, limit=2):
    attack = chess_attacks(size)
    free = [cell for cell in range(size*size) if cell not in clues]
    labels = tuple((1 << cell, val) for cell, val in clues.items())
    zeros = sum(bit for bit, val in labels if val == 0)
    available = [[(where, 1 << where, attack[piece][where]) for where in free
                  if not attack[piece][where] & zeros] for piece in PIECES]
    found = []

    def visit(placed, blocked, positions, choices, needed):
        if not choices:
            if not any(needed):
                found.append(dict(zip(PIECES, positions)))
            return
        if not all(choices):
            return
        for remaining, (bit, _) in zip(needed, labels):
            if sum(all(mask & bit for _, _, mask in opts) for opts in choices) > remaining:
                return
            if sum(any(mask & bit for _, _, mask in opts) for opts in choices) < remaining:
                return
        for where, occupied, mask in choices[0]:
            update = tuple(n - bool(mask & bit) for n, (bit, _) in zip(needed, labels))
            if min(update, default=0) < 0:
                continue
            taken, forbidden = placed | occupied, blocked | mask
            following = [[(a, b, c) for a, b, c in group if not (b & (taken | forbidden) or c & taken)]
                         for group in choices[1:]]
            visit(taken, forbidden, (*positions, where), following, update)
            if len(found) >= limit:
                return

    visit(0, 0, (), available, tuple(val for _, val in labels))
    return found


def chess_placement(seed, difficulty):
    rng = random.Random(seed)
    size, target = (5, 12) if difficulty == "mittel" else (6, 13)
    attack = chess_attacks(size)
    for _ in range(80):
        solution, used, forbidden = {}, 0, 0
        for piece in PIECES:
            options = [c for c in range(size*size) if not (used | forbidden) & (1 << c) and not attack[piece][c] & used]
            if not options:
                break
            cell = rng.choice(options)
            solution[piece] = cell
            used |= 1 << cell
            forbidden |= attack[piece][cell]
        if len(solution) != len(PIECES):
            continue
        clues = {c: sum(bool(attack[p][q] & (1 << c)) for p, q in solution.items())
                 for c in range(size*size) if not used & (1 << c)}
        if len(placement_solutions(size, clues)) == 1:
            break
    else:
        raise LogicalProofMissing("Keine eindeutige Schachaufstellung gefunden.")
    for cell in rng.sample(list(clues), len(clues)):
        old = clues.pop(cell)
        if len(placement_solutions(size, clues)) != 1:
            clues[cell] = old
        if len(clues) <= target:
            break
    rules = ("Platziere König, Dame, Turm, Läufer und Springer. Keine Figur darf eine andere angreifen. "
             "Eine Zahl gibt an, wie viele Figuren dieses Feld angreifen. Zahlenfelder bleiben frei. "
             "Wähle eine Figur und tippe auf ein freies Feld. Ein zweiter Tipp auf dieselbe Figur hebt ihre Platzierung auf.")
    return Puzzle("schachaufstellung", "Schachaufstellung", rules, Model({}, []), solution, {},
                  dict(kind="activity", mode="schachaufstellung", size=size, clues=clues), seed, difficulty,
                  analysis=dict(unique=True, solution_method="exhaustive_non_attacking_placement"))
