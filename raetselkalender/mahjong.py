"""Mahjong solitaire geometry, matching and solvable deals."""
import random

from .puzzle import LogicalProofMissing, Puzzle
from .solver import Model


def turtle():
    base = [(12 - length + 2 * col, 2 * row, 0)
            for row, length in enumerate((12, 8, 10, 12, 12, 10, 8, 12))
            for col in range(length)]
    base += [(-2, 7, 0), (24, 7, 0), (26, 7, 0)]
    for layer, (left, top, side) in enumerate(((6, 2, 6), (8, 4, 4), (10, 6, 2)), 1):
        base.extend((left + 2 * col, top + 2 * row, layer) for row in range(side) for col in range(side))
    return (*base, (11, 7, 4))


def terrace():
    return tuple((2 * col, 2 * row, 0) for row in range(10) for col in range(12)) + tuple(
        (6 + 2 * col, 6 + 2 * row, 1) for row in range(4) for col in range(6))


def blockers(positions):
    result = []
    for x, y, z in positions:
        above, left, right = [], [], []
        for index, (other_x, other_y, other_z) in enumerate(positions):
            if abs(other_y - y) >= 2:
                continue
            if other_z > z and abs(other_x - x) < 2:
                above.append(index)
            if other_z == z and other_x == x - 2:
                left.append(index)
            if other_z == z and other_x == x + 2:
                right.append(index)
        result.append(tuple(sum(1 << index for index in group) for group in (above, left, right)))
    return tuple(result)


def open_tiles(mask, geometry):
    return tuple(index for index, (above, left, right) in enumerate(geometry)
                 if mask & (1 << index) and not mask & above and (not mask & left or not mask & right))


def group(face):
    if face < 34:
        return face
    return 34 if face < 38 else 35


def mahjong_move(mask, pair, faces, geometry):
    first, second = pair
    if first == second or not all(0 <= i < len(faces) for i in pair):
        return None
    available = open_tiles(mask, geometry)
    if first not in available or second not in available or group(faces[first]) != group(faces[second]):
        return None
    return mask ^ (1 << first) ^ (1 << second)


def mahjong(seed, difficulty):
    rng = random.Random(seed)
    positions = terrace() if difficulty == "mittel" else turtle()
    geometry = blockers(positions)
    initial = (1 << len(positions)) - 1
    for _ in range(160):
        mask, removals = initial, []
        while mask:
            available = open_tiles(mask, geometry)
            if len(available) < 2:
                break
            first, second = rng.sample(available, 2)
            removals.append((first, second))
            mask ^= (1 << first) | (1 << second)
        if not mask:
            break
    else:
        raise LogicalProofMissing("Für das Mahjong-Layout wurde kein Räumweg gefunden.")
    pairs = [(face, face) for face in range(34) for _ in range(2)]
    for start in (34, 38):
        values = list(range(start, start + 4))
        rng.shuffle(values)
        pairs.extend((values[i], values[i + 1]) for i in (0, 2))
    rng.shuffle(pairs)
    faces = [0] * len(positions)
    for (first, second), (a, b) in zip(removals, pairs):
        faces[first], faces[second] = a, b
    rules = ("Räume die 144 Steine paarweise ab. Ein Stein ist frei, wenn kein höherer Stein ihn überdeckt "
             "und mindestens seine linke oder rechte Seite frei ist. Gleiche Motive passen zusammen. "
             "Blumen (✿) passen zu anderen Blumen, Jahreszeiten (◈) zu anderen Jahreszeiten.")
    return Puzzle("mahjong", "Mahjong", rules, Model({}, []), dict(enumerate(removals)), {},
                  dict(kind="activity", mode="mahjong", tiles=positions, faces=faces), seed, difficulty,
                  analysis=dict(solution_verified=True))
