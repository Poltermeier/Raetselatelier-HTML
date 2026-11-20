"""FreeCell rules and verified, seed-based deals."""
from functools import lru_cache
from importlib.resources import files
import json
import random
from typing import NamedTuple

from .playing_cards import rank, red, suit
from .puzzle import Puzzle
from .solver import Model

EMPTY = -1
CELLS = 8
FOUNDATIONS = 12


class FreeState(NamedTuple):
    columns: tuple[tuple[int, ...], ...]
    cells: tuple[int, ...]
    foundations: tuple[int, ...]


def initial_state(columns):
    return FreeState(tuple(map(tuple, columns)), (EMPTY,) * 4, (0,) * 4)


def fits(upper, lower):
    return rank(upper) + 1 == rank(lower) and red(upper) != red(lower)


def ordered(cards):
    return all(fits(upper, lower) for lower, upper in zip(cards, cards[1:]))


def capacity(state, destination):
    spaces = state.cells.count(EMPTY) + 1
    empty_columns = sum(not cards for index, cards in enumerate(state.columns) if index != destination)
    return spaces << empty_columns


def free_move(state, move):
    source, target, count = move
    if not (0 <= source < FOUNDATIONS and 0 <= target < 16 and source != target and count >= 1):
        return None
    columns, cells, foundations = map(list, state)
    if source < CELLS:
        if count > len(columns[source]):
            return None
        cards = columns[source][-count:]
        if not ordered(cards):
            return None
        columns[source] = columns[source][:-count]
    else:
        if count != 1 or cells[source - CELLS] == EMPTY:
            return None
        cards = (cells[source - CELLS],)
        cells[source - CELLS] = EMPTY

    first = cards[0]
    if target < CELLS:
        if count > capacity(state, target) or (columns[target] and not fits(first, columns[target][-1])):
            return None
        columns[target] += cards
    elif target < FOUNDATIONS:
        if count != 1 or cells[target - CELLS] != EMPTY:
            return None
        cells[target - CELLS] = first
    else:
        if count != 1 or suit(first) != target - FOUNDATIONS or rank(first) != foundations[target - FOUNDATIONS]:
            return None
        foundations[target - FOUNDATIONS] += 1
    return FreeState(tuple(columns), tuple(cells), tuple(foundations))


@lru_cache(maxsize=1)
def deals():
    path = files("raetselkalender").joinpath("data", "freecell.json")
    return json.loads(path.read_text(encoding="utf-8"))


def freecell(seed, difficulty):
    rng = random.Random(seed)
    columns, path = rng.choice(deals()[difficulty])
    order = rng.sample(range(4), 4) + rng.sample(range(4, 8), 4)
    black = rng.sample((0, 2), 2)
    red_suits = rng.sample((1, 3), 2)
    suits = (black[0], red_suits[0], black[1], red_suits[1])
    if rng.randrange(2):
        suits = tuple(color ^ 1 for color in suits)
    columns = [[13 * suits[suit(card)] + rank(card) for card in columns[index]] for index in order]
    locations = [order.index(index) for index in range(8)]
    locations.extend(rng.sample(range(8, 12), 4))
    locations.extend(12 + color for color in suits)
    moves = [(locations[source], locations[target], count) for source, target, count in path]
    state = initial_state(columns)
    for move in moves:
        state = free_move(state, move)
        if state is None:
            raise ValueError("Ein gespeicherter FreeCell-Zug ist ungültig.")
    if sum(state.foundations) != 52:
        raise ValueError("Ein FreeCell-Räumweg ist unvollständig.")
    rules = ("Lege alle Karten auf die vier Zielstapel, je Farbe vom Ass bis zum König. "
             "In den Spalten stapelst du absteigend und abwechselnd rot und schwarz. "
             "Die vier freien Zellen nehmen je eine Karte auf. Auf leere Spalten darf jede Karte. "
             "Eine geordnete Folge darfst du verschieben, wenn genug freie Zellen und Spalten zum Zwischenlagern da sind.")
    return Puzzle("freecell", "FreeCell", rules, Model({}, []), dict(enumerate(moves)), {},
                  dict(kind="activity", mode="freecell", columns=columns), seed, difficulty,
                  analysis=dict(solution_verified=True))
