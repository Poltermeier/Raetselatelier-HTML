"""Deal a symbol deck in which every pair of cards has one match."""
from random import Random

ORDER = 7
SYMBOL_COUNT = ORDER**2 + ORDER + 1
CARD_COUNT = 55
SYMBOLS_PER_CARD = ORDER + 1


def deal_symbols(seed):
    # Lines of the projective plane modulo 7. A direction symbol is the
    # common point of parallel lines, and the last card joins all directions.
    cards = [
        tuple(x * ORDER + (slope * x + offset) % ORDER for x in range(ORDER))
        + (ORDER**2 + slope,)
        for slope in range(ORDER) for offset in range(ORDER)
    ]
    cards += [
        tuple(x * ORDER + y for y in range(ORDER)) + (SYMBOL_COUNT - 1,)
        for x in range(ORDER)
    ]
    cards.append(tuple(range(ORDER**2, SYMBOL_COUNT)))

    rng = Random(seed)
    symbols = rng.sample(range(SYMBOL_COUNT), SYMBOL_COUNT)
    rng.shuffle(cards)
    return tuple(
        tuple(rng.sample([symbols[point] for point in card], SYMBOLS_PER_CARD))
        for card in cards[:CARD_COUNT]
    )


class SymbolDuel:
    def __init__(self, seed):
        self.deck = deal_symbols(seed)
        self.open_indices = (0, 1)
        self.hits = 0

    @property
    def open_cards(self):
        left, right = self.open_indices
        return self.deck[left], self.deck[right]

    @property
    def finished(self):
        return self.hits == len(self.deck) - 1

    def choose(self, symbol):
        left, right = self.open_cards
        if self.finished or symbol not in left or symbol not in right:
            return False
        self.hits += 1
        if not self.finished:
            # Alternate which of the two displayed cards is replaced.
            previous, newest = self.open_indices
            card = self.hits + 1
            self.open_indices = (previous, card) if self.hits % 2 else (card, newest)
        return True
