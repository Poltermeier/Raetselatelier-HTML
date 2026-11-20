"""The standard 52-card deck shared by the card games."""

DECK = tuple(range(52))
CLUBS, DIAMONDS, SPADES, HEARTS = range(4)
SUIT_SIGNS = "♣♦♠♥"
SUIT_NAMES = ("Kreuz", "Karo", "Pik", "Herz")
RANKS = ("A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "B", "D", "K")


def suit(card):
    return card // 13


def rank(card):
    return card % 13


def red(card):
    return bool(suit(card) % 2)


def card_text(card):
    return RANKS[rank(card)] + SUIT_SIGNS[suit(card)]
