"""Generate Fillomino boards and check all possible connected region covers."""
from functools import lru_cache
import random

from .placement_puzzles import adjacency, bits
from .puzzle import LogicalProofMissing, Puzzle
from .solver import Model


@lru_cache(maxsize=4)
def neighbor_masks(size):
    return tuple(sum(1 << j for j in group) for group in adjacency(size))


def frontier(region, links):
    neighbors = 0
    for cell in bits(region):
        neighbors |= links[cell]
    return neighbors & ~region


def connected_regions(start, available, maximum, links):
    level = {1 << start}
    for size in range(1, maximum+1):
        if not level:
            break
        yield from level
        if size < maximum:
            level = {region | (1 << cell) for region in level for cell in bits(frontier(region, links) & available)}


def fillomino_solutions(size, clues, limit=2):
    links = neighbor_masks(size)
    count = size*size
    all_cells = (1 << count)-1
    given = {}
    for cell, value in clues.items():
        given[value] = given.get(value, 0) | (1 << cell)
    blanks = all_cells ^ sum(given.values())
    regions = set()
    for value, mask in given.items():
        for cell in bits(mask):
            for region in connected_regions(cell, blanks | mask, value, links):
                if region.bit_count() == value and not frontier(region, links) & mask:
                    regions.add(region)

    # A group with no given can have any size up to the size of its blank component.
    # The smallest cell in a region serves as its unique anchor.
    for cell in bits(blanks):
        remaining = blanks & ~((1 << cell)-1)
        for region in connected_regions(cell, remaining, remaining.bit_count(), links):
            if not frontier(region, links) & given.get(region.bit_count(), 0):
                regions.add(region)

    choices = [[] for _ in range(count)]
    for region in sorted(regions):
        value = region.bit_count()
        item = region, frontier(region, links), value
        for cell in bits(region):
            choices[cell].append(item)
    found = []
    board = [0]*count
    used_by_size = [0]*(count+1)

    def visit(unfilled):
        if not unfilled:
            found.append(tuple(board))
            return
        best = None
        for cell in bits(unfilled):
            candidates = [(mask, edge, value) for mask, edge, value in choices[cell]
                          if unfilled & mask == mask and not used_by_size[value] & edge]
            if best is None or len(candidates) < len(best):
                best = candidates
            if not best:
                return
        for mask, _, value in best:
            for cell in bits(mask):
                board[cell] = value
            used_by_size[value] |= mask
            visit(unfilled ^ mask)
            used_by_size[value] ^= mask
            if len(found) >= limit:
                return

    visit(all_cells)
    return found


def fillomino(seed, difficulty):
    rng = random.Random(seed)
    size = 4 if difficulty == "mittel" else 5
    count = size*size
    links = neighbor_masks(size)
    for _ in range(100):
        board = [0]*count
        remaining = (1 << count)-1
        used_by_size = [0]*6
        while remaining:
            anchor = (remaining & -remaining).bit_length()-1
            options = [region for region in connected_regions(anchor, remaining, 5, links)
                       if not used_by_size[region.bit_count()] & frontier(region, links)]
            if not options:
                break
            region = rng.choice(options)
            value = region.bit_count()
            used_by_size[value] |= region
            remaining ^= region
            for cell in bits(region):
                board[cell] = value
        if not remaining:
            break
    else:
        raise LogicalProofMissing("Keine Fillomino-Teilung gefunden.")

    givens = dict(enumerate(board))
    gap_target = 8 if difficulty == "mittel" else 14
    for cell in rng.sample(range(count), count):
        number = givens.pop(cell)
        if fillomino_solutions(size, givens) != [tuple(board)]:
            givens[cell] = number
        if count-len(givens) >= gap_target:
            break

    key = lambda cell: f"{cell//size},{cell%size}"
    solution = {key(cell): value for cell, value in enumerate(board)}
    givens = {key(cell): value for cell, value in givens.items()}
    model = Model({k: {givens[k]} if k in givens else set(range(1, count+1)) for k in solution}, [])
    rules = ("Trage in jedes Feld eine Zahl ein. Waagerecht oder senkrecht verbundene Felder mit derselben Zahl bilden eine Gruppe. "
             "In einer Gruppe steht genau ihre Feldanzahl. Gleich große Gruppen dürfen sich nur diagonal berühren. "
             "Auch Gruppen ohne Vorgabe sind möglich.")
    return Puzzle("fillomino", "Fillomino", rules, model, solution, givens,
                  dict(kind="grid", size=size, cell_size=64), seed, difficulty,
                  analysis=dict(unique=True, solution_method="exhaustive_region_cover"))
