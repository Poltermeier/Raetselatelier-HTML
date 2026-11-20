"""Four-player Hearts and the rules shared by real and simulated turns."""
from dataclasses import dataclass
import random

from .playing_cards import CLUBS, DECK, HEARTS, SPADES, rank, suit
from .puzzle import Puzzle
from .solver import Model

HEARTS_LEVELS = ("leicht", "mittel", "schwer", "experte")
TWO_CLUBS = CLUBS * 13 + 1
QUEEN_SPADES = SPADES * 13 + 11
ACE_SPADES = SPADES * 13
KING_SPADES = SPADES * 13 + 12
PASS_OFFSETS = (1, -1, 2, 0)
ROUND_LIMIT = 100


def hearts_rank(card):
    return (rank(card) - 1) % 13  # Two low, ace high.


def penalty(card):
    return 13 if card == QUEEN_SPADES else int(suit(card) == HEARTS)


def legal_cards(hand, trick, first, broken):
    if first and not trick:
        return (TWO_CLUBS,) if TWO_CLUBS in hand else ()
    if trick:
        lead = suit(trick[0][1])
        following = tuple(card for card in hand if suit(card) == lead)
        if following:
            return following
        if first:
            nonpoints = tuple(card for card in hand if not penalty(card))
            if nonpoints:
                return nonpoints
    elif not broken:
        others = tuple(card for card in hand if suit(card) != HEARTS)
        if others:
            return others
    return tuple(hand)


def trick_winner(trick):
    lead = suit(trick[0][1])
    return max((hearts_rank(card), player) for player, card in trick if suit(card) == lead)[1]


def hand_scores(points):
    return tuple(0 if point == 26 else 26 for point in points) if 26 in points else tuple(points)


def public_voids(history):
    """Players who failed to follow a suit cannot hold it later in the hand."""
    voids = [set() for _ in range(4)]
    for index in range(0, len(history), 4):
        trick = history[index:index + 4]
        lead = suit(trick[0][1])
        for player, card in trick[1:]:
            if suit(card) != lead:
                voids[player].add(lead)
    return tuple(frozenset(v) for v in voids)


@dataclass(frozen=True)
class SeatView:
    player: int
    hand: tuple[int, ...]
    history: tuple[tuple[int, int], ...]
    trick: tuple[tuple[int, int], ...]
    points: tuple[int, ...]
    scores: tuple[int, ...]
    broken: bool
    sent: tuple[int, ...] = ()
    pass_target: int | None = None

    def legal(self):
        return legal_cards(self.hand, self.trick, not self.history, self.broken)


class HeartsMatch:
    def __init__(self, seed, difficulty):
        self.dealer = random.Random(f"hearts:dealer:{seed}")
        self.bot_rngs = [random.Random(f"hearts:seat:{player}:{seed}") for player in range(4)]
        self.difficulty = difficulty
        self.scores = (0, 0, 0, 0)
        self.round_number = 0
        self.start_round()

    def start_round(self):
        if self.round_number and self.stage != "between":
            raise ValueError("Die laufende Partie erlaubt noch keine neue Runde.")
        self.round_number += 1
        deck = list(DECK)
        self.dealer.shuffle(deck)
        self.hands = [sorted(deck[i::4]) for i in range(4)]
        self.offset = PASS_OFFSETS[(self.round_number - 1) % 4]
        self.sent = [()] * 4
        self.points = [0] * 4
        self.history = []
        self.trick = []
        self.last_trick = ()
        self.last_winner = None
        self.broken = False
        self.turn = None
        self.stage = "pass" if self.offset else "play"
        if not self.offset:
            self.begin_play()

    def begin_play(self):
        self.stage = "play"
        self.turn = next(player for player, hand in enumerate(self.hands) if TWO_CLUBS in hand)

    def observation(self, player):
        return SeatView(player, tuple(self.hands[player]), tuple(self.history), tuple(self.trick),
                        tuple(self.points), self.scores, self.broken, self.sent[player],
                        (player + self.offset) % 4 if self.offset else None)

    def exchange(self, outgoing):
        if (self.stage != "pass" or len(outgoing) != 4
                or any(len(cards) != 3 or len(set(cards)) != 3 or not set(cards) <= set(hand)
                       for hand, cards in zip(self.hands, outgoing))):
            raise ValueError("Jede Hand gibt genau drei eigene Karten weiter.")
        self.sent = list(map(tuple, outgoing))
        self.hands = [sorted((set(hand) - set(outgoing[player])) | set(outgoing[(player - self.offset) % 4]))
                      for player, hand in enumerate(self.hands)]
        self.begin_play()

    def play(self, card):
        if self.stage != "play" or card not in self.observation(self.turn).legal():
            raise ValueError("Diese Karte ist jetzt nicht erlaubt.")
        self.hands[self.turn].remove(card)
        self.trick.append((self.turn, card))
        self.broken |= suit(card) == HEARTS
        if len(self.trick) < 4:
            self.turn = (self.turn + 1) % 4
            return False

        winner = trick_winner(self.trick)
        self.points[winner] += sum(penalty(value) for _, value in self.trick)
        self.last_trick = tuple(self.trick)
        self.last_winner = winner
        self.history.extend(self.trick)
        self.trick.clear()
        self.turn = winner
        if len(self.history) == 52:
            self.scores = tuple(a + b for a, b in zip(self.scores, hand_scores(self.points)))
            self.stage = "over" if max(self.scores) >= ROUND_LIMIT else "between"
            self.turn = None
        return True

    def winners(self):
        return tuple(player for player, score in enumerate(self.scores) if score == min(self.scores))


def hearts(seed, difficulty):
    rules = ("Spiele gegen drei getrennte Gegner. Gib zu Rundenbeginn gegebenenfalls drei Karten weiter. "
             "Kreuz 2 eröffnet. Bedien die ausgespielte Farbe, wenn du kannst. Im ersten Stich sind Punktkarten "
             "beim Abwerfen nur erlaubt, wenn du ausschließlich Punktkarten hast. Herz darf erst ausgespielt "
             "werden, nachdem Herz gefallen ist oder du nur noch Herz hast. Herzkarten zählen je einen Punkt, "
             "die Pik-Dame zählt 13. Wer alle 26 holt, gibt den anderen je 26 Punkte. Erreicht jemand 100, "
             "gewinnt der niedrigste Gesamtstand.")
    return Puzzle("hearts", "Hearts", rules, Model({}, []), {}, {},
                  dict(kind="activity", mode="hearts"), seed, difficulty)
