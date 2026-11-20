"""Find reproducible solvable FreeCell deals and store their certified move paths."""
import argparse
from heapq import heappop, heappush
from itertools import count
import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from raetselkalender.freecell import EMPTY, capacity, fits, free_move, initial_state
from raetselkalender.playing_cards import DECK, rank, suit


def sources(state):
    return [(index, cards[-1]) for index, cards in enumerate(state.columns) if cards] + [
        (8 + index, card) for index, card in enumerate(state.cells) if card != EMPTY
    ]


def safe_foundations(state):
    moves = []
    while True:
        move = None
        for source, card in sources(state):
            color, value = suit(card), rank(card)
            if state.foundations[color] != value:
                continue
            if value <= 1 or all(state.foundations[k] >= value for k in range(4) if (k ^ color) & 1):
                move = source, 12 + color, 1
                break
        if not move:
            return state, moves
        state = free_move(state, move)
        moves.append(move)


def candidates(state):
    empty_col = next((index for index, cards in enumerate(state.columns) if not cards), None)
    empty_cell = 8 + state.cells.index(EMPTY) if EMPTY in state.cells else None
    for source, card in sources(state):
        color = suit(card)
        if state.foundations[color] == rank(card):
            yield source, 12 + color, 1
        if source < 8 and empty_cell is not None:
            yield source, empty_cell, 1

        cards = state.columns[source] if source < 8 else (card,)
        length = 1
        for lower, upper in zip(reversed(cards[:-1]), reversed(cards[1:])):
            if not fits(upper, lower):
                break
            length += 1
        for target, destination in enumerate(state.columns):
            if target == source or (not destination and target != empty_col):
                continue
            for number in range(1, min(length, capacity(state, target)) + 1):
                if destination and not fits(cards[-number], destination[-1]):
                    continue
                if not destination and source < 8 and number == len(cards):
                    continue
                yield source, target, number


def priority(state):
    remaining = 52 - sum(state.foundations)
    breaks = sum(not fits(upper, lower) for cards in state.columns for lower, upper in zip(cards, cards[1:]))
    blocked = sum(len(cards) - i - 1 for cards in state.columns for i, card in enumerate(cards)
                  if rank(card) == state.foundations[suit(card)])
    return 9 * remaining + 3 * breaks + 3 * blocked - 8 * state.columns.count(()) - 3 * state.cells.count(EMPTY)


def state_key(state):
    return tuple(sorted(state.columns)), tuple(sorted(state.cells)), state.foundations


def search(initial, limit):
    state, forced = safe_foundations(initial)
    ids = count()
    queue = [(priority(state), next(ids), state, tuple(forced))]
    visited = {state_key(state)}
    for _ in range(limit):
        if not queue:
            return None
        _, _, state, path = heappop(queue)
        if sum(state.foundations) == 52:
            return path
        for move in candidates(state):
            following = free_move(state, move)
            following, forced = safe_foundations(following)
            key = state_key(following)
            if key in visited:
                continue
            visited.add(key)
            moves = (*path, move, *forced)
            heappush(queue, (priority(following) + len(moves) * .15, next(ids), following, moves))
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=60, help="deals per difficulty")
    options = parser.parse_args()
    if options.count < 1:
        parser.error("--count must be positive")
    output = {"mittel": [], "schwer": []}
    for seed in count(0):
        deck = list(DECK)
        random.Random(seed).shuffle(deck)
        columns = [deck[index::8] for index in range(8)]
        moves = search(initial_state(columns), 3500)
        if moves:
            level = "mittel" if len(moves) < 92 else "schwer"
            if len(output[level]) < options.count:
                output[level].append((columns, moves))
                if len(output[level]) % 10 == 0:
                    print(f"{level}: {len(output[level])} ({seed}, {len(moves)} moves)", flush=True)
        if all(len(deals) == options.count for deals in output.values()):
            break
    path = ROOT / "raetselkalender/data/freecell.json"
    # One deal per line keeps the checked-in data reviewable.
    path.write_text("{\n" + ",\n".join(
        f'  "{level}": [\n' + ",\n".join("    " + json.dumps(deal, separators=(",", ":")) for deal in deals) + "\n  ]"
        for level, deals in output.items()
    ) + "\n}\n", encoding="utf-8")


if __name__ == "__main__":
    main()
