"""Independent Hearts policies. No policy receives the match or another real hand."""
from collections import Counter

from .hearts import (ACE_SPADES, KING_SPADES, QUEEN_SPADES, SeatView, hand_scores, hearts_rank,
                     legal_cards, penalty, public_voids, trick_winner)
from .playing_cards import DECK, HEARTS, SPADES, suit


def danger(card, hand, queen_live=True):
    rank = hearts_rank(card)
    if queen_live and card in (ACE_SPADES, KING_SPADES):
        return rank + 10
    if queen_live and card == QUEEN_SPADES:
        return 23 - sum(suit(other) == SPADES and hearts_rank(other) < 10 for other in hand) * 2.4
    return rank * (1.1 if suit(card) == HEARTS else 1.0)


def choose_pass(view, difficulty, rng):
    if difficulty == "leicht":
        return tuple(rng.sample(view.hand, 3))
    counts = Counter(map(suit, view.hand))
    queen = QUEEN_SPADES in view.hand
    def cost(card):
        score = danger(card, view.hand)
        if difficulty in ("schwer", "experte") and suit(card) not in (SPADES, HEARTS) and counts[suit(card)] <= 2:
            score += 8 if counts[suit(card)] == 1 else 5
        if queen and suit(card) == SPADES and hearts_rank(card) < 10:
            score -= 4
        return score, card
    return tuple(sorted(view.hand, key=cost, reverse=True)[:3])


def basic_card(view):
    legal = view.legal()
    if not view.trick:
        return min(legal, key=hearts_rank)
    lead = suit(view.trick[0][1])
    if suit(legal[0]) != lead:
        return max(legal, key=lambda card: (penalty(card), hearts_rank(card)))
    return min(legal, key=hearts_rank)


def tactical_scores(view):
    legal = view.legal()
    played = {card for _, card in (*view.history, *view.trick)}
    queen_live = QUEEN_SPADES not in played
    trick = view.trick
    points = sum(penalty(card) for _, card in trick)
    current_winner = trick_winner(trick) if trick else None
    lead = suit(trick[0][1]) if trick else None
    voids = public_voids((*view.history, *trick))
    behind = tuple((view.player + i) % 4 for i in range(1, 4 - len(trick)))
    moon = next((p for p, total in enumerate(view.points) if total >= 17 and total == sum(view.points)), None)

    def score(card):
        color, rank = suit(card), hearts_rank(card)
        risk = danger(card, view.hand, queen_live)
        if not trick:
            void_count = sum(color in voids[seat] for seat in behind)
            score = -rank * .7 - void_count * 1.0
            if queen_live and color == SPADES and rank < hearts_rank(QUEEN_SPADES):
                score += 2.3
            return score - (4 if color == HEARTS else 0)

        if color != lead:
            score = 5 * penalty(card) + risk
            if moon == current_winner and moon != view.player:
                score -= 9 * penalty(card)
            if sum(suit(other) == color for other in view.hand) == 1:
                score += 2.0
            return score

        winning = trick_winner((*trick, (view.player, card))) == view.player
        if not winning:
            return 13 + risk * .5
        total = points + penalty(card)
        if not behind and total == 0:
            return 10 + risk * .8
        if not behind and moon is not None and moon != view.player and total and (
            moon == current_winner or view.points[moon] >= 21
        ):
            return 25 - total * .7 + risk * .2

        cannot_follow = all(color in voids[seat] for seat in behind)
        unseen_higher = sum(suit(other) == color and hearts_rank(other) > rank
                            for other in DECK if other not in played and other not in view.hand)
        loss = 5 * total
        if behind and (cannot_follow or not unseen_higher):
            loss += 4
        return -loss - rank * .45 + risk * (.65 if not behind else .10)

    return {card: score(card) for card in legal}


def possible_hands(view, rng):
    """Draw a possible allocation using only played cards, inferred voids and own pass."""
    played = (*view.history, *view.trick)
    seen = {card for _, card in played} | set(view.hand)
    counts = Counter(player for player, _ in played)
    voids = public_voids(played)
    result = [[] for _ in range(4)]
    result[view.player] = list(view.hand)
    if view.pass_target is not None:
        result[view.pass_target] = [card for card in view.sent if card not in seen]
        seen.update(result[view.pass_target])
    recipients = [p for p in range(4) if p != view.player]
    slots = [p for p in recipients for _ in range(13 - counts[p] - len(result[p]))]
    rng.shuffle(slots)
    cards = [card for card in DECK if card not in seen]
    rng.shuffle(cards)
    candidates = {card: [i for i, player in enumerate(slots) if suit(card) not in voids[player]]
                  for card in cards}
    assigned = {}

    def assign(card, visited):
        for index in candidates[card]:
            if index in visited:
                continue
            visited.add(index)
            if index not in assigned or assign(assigned[index], visited):
                assigned[index] = card
                return True
        return False

    if not all(assign(card, set()) for card in sorted(cards, key=lambda card: len(candidates[card]))):
        return None
    for index, card in assigned.items():
        result[slots[index]].append(card)
    return tuple(tuple(sorted(hand)) for hand in result)


def simulate(view, deal, first_card):
    """Play a hypothetical deal. Every simulated seat uses its own observation."""
    hands = [list(hand) for hand in deal]
    history, trick, points = list(view.history), list(view.trick), list(view.points)
    turn, broken, card = view.player, view.broken, first_card
    while True:
        hands[turn].remove(card)
        trick.append((turn, card))
        broken |= suit(card) == HEARTS
        if len(trick) == 4:
            turn = trick_winner(trick)
            points[turn] += sum(penalty(other) for _, other in trick)
            history.extend(trick)
            trick = []
            if not any(hands):
                return hand_scores(points)
        else:
            turn = (turn + 1) % 4
        sample = SeatView(turn, tuple(hands[turn]), tuple(history), tuple(trick), tuple(points), view.scores, broken)
        scores = tactical_scores(sample)
        card = max(scores, key=scores.get)


def choose_card(view, difficulty, rng):
    legal = view.legal()
    if len(legal) == 1 or difficulty == "leicht":
        return rng.choice(legal)
    if difficulty == "mittel":
        return basic_card(view)
    tactical = tactical_scores(view)
    if difficulty == "schwer":
        return max(tactical, key=tactical.get)

    # Share the same hypothetical deals across this seat's card choices to compare them fairly.
    deals = [deal for _ in range(10) if (deal := possible_hands(view, rng)) is not None]
    if not deals:
        return max(tactical, key=tactical.get)
    rivals = [p for p in range(4) if p != view.player]
    target = min(rivals, key=lambda p: view.scores[p])
    ranked = sorted(tactical, key=tactical.get, reverse=True)
    candidates = ranked[:6]
    def merit(card):
        total = 0
        for deal in deals:
            points = simulate(view, deal, card)
            cost = points[view.player] - .30 * points[target]
            scores = tuple(a + b for a, b in zip(view.scores, points))
            if max(scores) >= 100:
                cost += 12 if scores[view.player] > min(scores) else -12
            total += cost
        return -total / len(deals) + .12 * tactical[card]
    return max(candidates, key=merit)
