"""Generate a clue-only puzzle from an original bitmap of a real object."""
from functools import lru_cache
from itertools import combinations
from random import Random

from .generators import cell, finish, grid_domains, lines, runs
from .nonogram_images import MOTIFS
from .solver import Model, Table

PICTURE_TYPE = "bild-nonogramm"
PICTURE_TITLE = "Nonogramm - Motiv"
LIVES = 3


@lru_cache(maxsize=256)
def line_patterns(length, hints):
    """Enumerate placements of the given runs within the available gaps."""
    patterns = []
    for positions in combinations(range(length - sum(hints) + 1), len(hints)):
        bits = [0] * length
        filled = 0
        for position, count in zip(positions, hints):
            start = position + filled
            bits[start:start + count] = [1] * count
            filled += count
        patterns.append(tuple(bits))
    return tuple(patterns)


def puzzle_for_motif(name, image, seed, difficulty):
    rows, cols = len(image), len(image[0])
    solution = {cell(r, c): int(pixel == "#") for r, line in enumerate(image) for c, pixel in enumerate(line)}
    groups = lines(rows, cols)
    clues = [runs(solution[key] for key in group) for group in groups]
    model = Model(grid_domains(rows, (0, 1), cols),
                  [Table(group, line_patterns(len(group), tuple(hint))) for group, hint in zip(groups, clues)])
    view = dict(kind="picture-nonogram", size=cols, rows=rows, cols=cols, cell_size=28,
                row_hints=clues[:rows], col_hints=clues[rows:], binary_paint=True)
    rules = ("Die Zahlen zeigen, wie viele Bildfelder am Stück liegen. Zwischen Blöcken bleibt mindestens ein Feld frei. "
             "Wähle Ausmalen oder Kreuz setzen. Auch Rechtsklick setzt ein Kreuz. "
             "Falsches Ausmalen und falsche Kreuze kosten je ein Herz. Male alle Bildfelder aus, um das Motiv zu sehen.")
    return finish(PICTURE_TYPE, PICTURE_TITLE, rules, model, solution, {}, view, seed, difficulty, result=name)


def picture_nonogram(seed, difficulty):
    rng = Random(seed)
    choices = [(name, image) for name, level, image in MOTIFS if level == difficulty]
    name, image = rng.choice(choices)
    if rng.randrange(2):
        image = tuple(row[::-1] for row in image)
    return puzzle_for_motif(name, image, seed, difficulty)
