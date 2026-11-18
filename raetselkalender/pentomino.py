"""Generate varied polyomino sets from verified rectangular pentomino tilings."""
from functools import lru_cache
from itertools import chain
import random

from .card_code_matches import validate_entries
from .puzzle import Puzzle
from .solver import Model,Table

SHAPES={
 'F':((0,1),(0,2),(1,0),(1,1),(2,1)),
 'I':((0,0),(1,0),(2,0),(3,0),(4,0)),
 'L':((0,0),(1,0),(2,0),(3,0),(3,1)),
 'P':((0,0),(0,1),(1,0),(1,1),(2,0)),
 'N':((0,0),(1,0),(1,1),(2,1),(3,1)),
 'T':((0,0),(0,1),(0,2),(1,1),(2,1)),
 'U':((0,0),(0,2),(1,0),(1,1),(1,2)),
 'V':((0,0),(1,0),(2,0),(2,1),(2,2)),
 'W':((0,0),(1,0),(1,1),(2,1),(2,2)),
 'X':((0,1),(1,0),(1,1),(1,2),(2,1)),
 'Y':((0,0),(1,0),(2,0),(3,0),(1,1)),
 'Z':((0,0),(0,1),(1,1),(2,1),(2,2)),
}
PIECE_COLORS=('#3b75b5','#c75242','#4f933c','#9865b3','#d6942e','#378f91',
              '#bd5591','#827437','#6655a5','#c77d54','#5c9eb2','#798744')


def normalize_shape(shape):
    top=min(r for r,c in shape);left=min(c for r,c in shape)
    return tuple(sorted((r-top,c-left) for r,c in shape))


def transform_shape(shape,turns=0,mirror=False):
    points=tuple((r,-c if mirror else c) for r,c in shape)
    for _ in range(turns%4):points=tuple((c,-r) for r,c in points)
    return normalize_shape(points)


def orientations(shape):return tuple(sorted({transform_shape(shape,turns,mirror) for turns in range(4) for mirror in (False,True)}))


@lru_cache(maxsize=256)
def shape_placements(rows, cols, points):
    return tuple(tuple((row + dr) * cols + col + dc for dr, dc in shape)
                 for shape in orientations(points)
                 for row in range(rows - max(dr for dr, dc in shape))
                 for col in range(cols - max(dc for dr, dc in shape)))


def placement_options(rows, cols, shapes=SHAPES):
    return {name: shape_placements(rows, cols, normalize_shape(points)) for name, points in shapes.items()}


def pentomino_solution(rows,cols,rng):
    options=placement_options(rows,cols);names=tuple(options);full=(1<<(rows*cols))-1
    masks={name:tuple(sum(1<<cell for cell in cells) for cells in choices) for name,choices in options.items()}
    cover=[[] for _ in range(rows*cols)]
    for pi,name in enumerate(names):
        for index,cells in enumerate(options[name]):
            for point in cells:cover[point].append((pi,index,masks[name][index]))
    for group in cover:rng.shuffle(group)
    nodes=0
    def components_fit(occupied):
        free=full^occupied
        while free:
            start=free&-free;seen=start;front=start
            while front:
                following=0
                bits=front
                while bits:
                    bit=bits&-bits;bits-=bit;point=bit.bit_length()-1;r,c=divmod(point,cols)
                    for other in (point-cols if r else -1,point+cols if r+1<rows else -1,
                                  point-1 if c else -1,point+1 if c+1<cols else -1):
                        if other>=0:following|=1<<other
                front=following&free&~seen;seen|=front
            if seen.bit_count()%5:return False
            free&=~seen
        return True
    def place(occupied,used,chosen):
        nonlocal nodes
        nodes+=1
        if nodes>12_000:raise TimeoutError  # Stable across machines for a given seed.
        if occupied==full:return chosen
        best=None;free=full^occupied
        while free:
            bit=free&-free;free-=bit;point=bit.bit_length()-1
            candidates=[item for item in cover[point] if not used&(1<<item[0]) and not occupied&item[2]]
            if not candidates:return None
            if best is None or len(candidates)<len(best):best=candidates
            if len(best)==1:break
        for pi,index,mask in best:
            following=occupied|mask
            if not components_fit(following):continue
            result=place(following,used|(1<<pi),chosen|{names[pi]:index})
            if result is not None:return result
        return None
    result=place(0,0,{})
    if result is None:raise ValueError('Keine Pentomino-Belegung gefunden')
    return {name:result[name] for name in names}


def neighbors(point):
    row, col = point
    return ((row - 1, col), (row + 1, col), (row, col - 1), (row, col + 1))


def connected(points):
    start = min(points)
    seen = {start}
    pending = [start]
    while pending:
        for point in neighbors(pending.pop()):
            if point in points and point not in seen:
                seen.add(point)
                pending.append(point)
    return len(seen) == len(points)


def transfer_choices(tiles):
    """A boundary square can turn two adjacent fives into a four and a six."""
    owners = {point: name for name, cells in tiles.items() for point in cells}
    for donor, cells in tiles.items():
        for point in sorted(cells):
            remaining = cells - {point}
            if not connected(remaining):
                continue
            smaller = orientations(remaining)[0]
            recipients = {owners[neighbor] for neighbor in neighbors(point) if neighbor in owners} - {donor}
            for recipient in sorted(recipients):
                enlarged = tiles[recipient] | {point}
                larger = orientations(enlarged)[0]
                yield {donor, recipient, smaller, larger}, ((donor, remaining), (recipient, enlarged))


def select_transfers(choices, count, start=0, used=frozenset()):
    """Choose disjoint transfers with distinct shapes up to rotation and reflection."""
    if not count:
        return ()
    for index in range(start, len(choices) - count + 1):
        conflicts, transfer = choices[index]
        if used.isdisjoint(conflicts):
            rest = select_transfers(choices, count - 1, index + 1, used | conflicts)
            if rest is not None:
                return (transfer, *rest)
    return None


def mix_tiles(tiles, pairs, rng):
    choices = list(transfer_choices(tiles))
    rng.shuffle(choices)
    transfers = select_transfers(choices, pairs)
    if transfers is None:
        return None
    mixed = tiles.copy()
    for new_name, (old_name, cells) in zip("ABCDEG", chain.from_iterable(transfers)):
        del mixed[old_name]
        mixed[new_name] = cells
    names = list(mixed)
    rng.shuffle(names)
    return {name: mixed[name] for name in names}


class PentominoPuzzle(Puzzle):
    def check(self,entries):
        pending=validate_entries(self,entries)
        if pending:return pending,[]
        used=set()
        for name,index in entries.items():
            cells=set(self.options[name][index])
            if len(cells)!=len(self.view['shapes'][name]) or used&cells:return 'wrong',self.editable
            used.update(cells)
        return ('correct',[]) if len(used)==self.view['rows']*self.view['cols'] else ('wrong',self.editable)

    def certify(self):
        self.options=placement_options(self.view['rows'],self.view['cols'],self.view['shapes'])
        self.piece_colors=dict(zip(self.view['shapes'],self.view['palette']))
        if self.check(self.solution)[0]!='correct':raise ValueError('Ungültiger Pentomino-Lösungsnachweis')
        self.analysis.update(unique=False,logical_solvable=False,rules_verified=True,model_role='example_solution',
                             solution_method='exact_cover_witness_and_independent_tiling_validation',search_branches=None)


def pentomino(seed,difficulty):
    rng = random.Random(seed)
    rows, cols = (6, 10) if difficulty == 'mittel' else (5, 12)
    pairs = 2 if difficulty == 'mittel' else 3
    base_options = placement_options(rows, cols)
    for _ in range(8):
        try:
            base_solution = pentomino_solution(rows, cols, rng)
        except TimeoutError:
            continue
        base_tiles = {
            name: {divmod(point, cols) for point in base_options[name][index]}
            for name, index in base_solution.items()
        }
        tiles = mix_tiles(base_tiles, pairs, rng)
        if tiles is not None:
            break
    else:
        raise ValueError('Für diese Teilemischung wurde im Versuchslimit keine Belegung gefunden')

    shapes = {name: list(SHAPES[name] if name in SHAPES else normalize_shape(cells))
              for name, cells in tiles.items()}
    options = placement_options(rows, cols, shapes)
    solution = {name: options[name].index(tuple(sorted(row * cols + col for row, col in cells)))
                for name, cells in tiles.items()}
    keys = tuple(shapes)
    puzzle = PentominoPuzzle('pentomino-puzzle','Pentomino Puzzle',
        'Lege die zwölf verschiedenen Teile aus vier, fünf oder sechs Quadraten lückenlos in das Rechteck. '
        'Jedes Teil wird genau einmal benutzt; Teile dürfen sich nicht überlappen. '
        'Ziehe eine Figur aus der Auswahl ins Feld und lasse sie passend am Raster los. Drehe sie mit R oder spiegle sie mit M. '
        'Du kannst auch ein Teil wählen und im Raster auf die obere linke Ecke seines Umrisses klicken. '
        'Ein Klick auf ein gelegtes Teil nimmt es wieder auf. '
        'Jede vollständige gültige Belegung zählt.',
        Model({name:set(range(len(options[name]))) for name in keys},[Table(keys,(tuple(solution[k] for k in keys),))]),
        solution,{},dict(kind='activity',mode='pentomino',rows=rows,cols=cols,shapes=shapes,palette=list(PIECE_COLORS)),seed,difficulty)
    puzzle.certify()
    return puzzle
