from collections import Counter
import random
import unittest

from raetselkalender.catalog import generate
from raetselkalender.freecell import FreeState, capacity, free_move, initial_state
from raetselkalender.hearts import (QUEEN_SPADES, TWO_CLUBS, HeartsMatch, hand_scores, legal_cards,
                                    hearts_hand_order, penalty, public_voids, trick_winner)
from raetselkalender.hearts_ai import choose_card, choose_pass, possible_hands
from raetselkalender.mahjong import blockers, group, mahjong_move, open_tiles
from raetselkalender.playing_cards import DECK, suit


class SolitaireGames(unittest.TestCase):
    def test_mahjong_deals_include_all_tiles_and_a_legal_route(self):
        for level in ("mittel", "schwer"):
            for seed in range(5):
                puzzle = generate("mahjong", seed, level)
                faces = puzzle.view["faces"]
                self.assertEqual(Counter(map(group, faces)), {i: 4 for i in range(36)})
                geometry = blockers(puzzle.view["tiles"])
                mask = (1 << 144) - 1
                available = open_tiles(mask, geometry)
                self.assertLess(len(available), len(faces))
                self.assertIsNone(mahjong_move(mask, (available[0], available[0]), faces, geometry))
                for pair in puzzle.solution.values():
                    mask = mahjong_move(mask, pair, faces, geometry)
                    self.assertIsNotNone(mask)
                self.assertEqual(mask, 0)

    def test_freecell_deals_and_replay(self):
        for level in ("mittel", "schwer"):
            for seed in range(6):
                puzzle = generate("freecell", seed, level)
                state = initial_state(puzzle.view["columns"])
                self.assertEqual([len(stack) for stack in state.columns], [7] * 4 + [6] * 4)
                self.assertEqual(sorted(card for col in state.columns for card in col), list(DECK))
                for move in puzzle.solution.values():
                    state = free_move(state, move)
                    self.assertIsNotNone(state)
                self.assertEqual(state.foundations, (13, 13, 13, 13))

    def test_freecell_supermove_uses_empty_cells_and_intermediate_columns(self):
        columns = ((4, 16, 2), (), (12,), (38,), (24,), (36,), (20,), (3,))
        board = FreeState(columns, (-1, 11, 10, 50), (0, 0, 0, 0))
        self.assertEqual(capacity(board, 1), 2)
        self.assertIsNone(free_move(board, (0, 1, 3)))
        self.assertIsNotNone(free_move(board, (0, 1, 2)))
        self.assertIsNone(free_move(board, (0, 2, 1)))
        self.assertIsNone(free_move(board, (0, 8, 2)))
        self.assertEqual(free_move(board, (0, 8, 1)).cells[0], 2)


class HeartsRules(unittest.TestCase):
    def test_hand_order_puts_each_ace_after_the_king_of_its_suit(self):
        expected = [color * 13 + rank for color in range(4) for rank in (*range(1, 13), 0)]
        self.assertEqual(sorted(DECK, key=hearts_hand_order), expected)

    def test_opening_follow_suit_points_and_broken_hearts(self):
        heart, diamond = 40, 14
        self.assertEqual(legal_cards((TWO_CLUBS, heart), (), True, False), (TWO_CLUBS,))
        self.assertEqual(legal_cards((heart, 0), ((0, TWO_CLUBS),), True, False), (0,))
        self.assertEqual(legal_cards((heart, diamond, QUEEN_SPADES), ((0, TWO_CLUBS),), True, False), (diamond,))
        self.assertEqual(legal_cards((heart, QUEEN_SPADES), ((0, TWO_CLUBS),), True, False), (heart, QUEEN_SPADES))
        self.assertEqual(legal_cards((heart, QUEEN_SPADES), (), False, False), (QUEEN_SPADES,))
        self.assertEqual(legal_cards((heart,), (), False, False), (heart,))
        self.assertEqual(legal_cards((heart, diamond), (), False, True), (heart, diamond))
        self.assertEqual(trick_winner(((0, TWO_CLUBS), (1, 0), (2, 12), (3, 39))), 1)
        self.assertEqual((penalty(QUEEN_SPADES), penalty(heart), penalty(diamond)), (13, 1, 0))
        self.assertEqual(hand_scores((0, 0, 26, 0)), (26, 26, 0, 26))
        self.assertEqual(hand_scores((0, 13, 8, 5)), (0, 13, 8, 5))

    def test_simultaneous_exchange_and_a_complete_match(self):
        game = HeartsMatch(52, "mittel")
        offsets = []
        while game.stage != "over":
            offsets.append(game.offset)
            if game.stage == "pass":
                before = [tuple(hand) for hand in game.hands]
                sent = [choose_pass(game.observation(p), game.difficulty, game.bot_rngs[p]) for p in range(4)]
                game.exchange(sent)
                for p in range(4):
                    self.assertEqual(set(game.hands[p]), (set(before[p]) - set(sent[p])) | set(sent[(p - game.offset) % 4]))
                    self.assertEqual(game.observation(p).sent, sent[p])
            self.assertIn(TWO_CLUBS, game.hands[game.turn])
            previous_scores = game.scores
            while game.stage == "play":
                p = game.turn
                game.play(choose_card(game.observation(p), game.difficulty, game.bot_rngs[p]))
            self.assertEqual(sorted(card for _, card in game.history), list(DECK))
            self.assertEqual(sum(game.points), 26)
            self.assertEqual(game.scores, tuple(a + b for a, b in zip(previous_scores, hand_scores(game.points))))
            if game.stage == "between":
                game.start_round()
        self.assertEqual(offsets, [1, -1, 2, 0] * (len(offsets) // 4) + [1, -1, 2, 0][:len(offsets) % 4])
        self.assertGreaterEqual(max(game.scores), 100)
        self.assertTrue(all(game.scores[p] == min(game.scores) for p in game.winners()))

    def test_ai_sees_own_hand_only_and_samples_possible_deals(self):
        game = HeartsMatch(339, "experte")
        sent = [tuple(hand[:3]) for hand in game.hands]
        game.exchange(sent)
        for _ in range(16):
            game.play(game.observation(game.turn).legal()[0])
        view = game.observation(game.turn)
        altered = HeartsMatch(339, "experte")
        altered.exchange(sent)
        for _ in range(16):
            altered.play(altered.observation(altered.turn).legal()[0])
        other = [(view.player + offset) % 4 for offset in (1, 2)]
        altered.hands[other[0]], altered.hands[other[1]] = altered.hands[other[1]], altered.hands[other[0]]
        self.assertEqual(view, altered.observation(view.player))
        for level in ("leicht", "mittel", "schwer", "experte"):
            self.assertIn(choose_card(view, level, random.Random(7)), view.legal())
            self.assertEqual(choose_card(view, level, random.Random(7)),
                             choose_card(altered.observation(view.player), level, random.Random(7)))
        played = (*view.history, *view.trick)
        voids = public_voids(played)
        sample = possible_hands(view, random.Random(16))
        self.assertIsNotNone(sample)
        self.assertEqual(sample[view.player], view.hand)
        self.assertEqual(sorted(card for hand in sample for card in hand),
                         sorted(set(DECK) - {card for _, card in played}))
        self.assertTrue(all(suit(card) not in voids[p] for p, hand in enumerate(sample) for card in hand))
        self.assertNotIn("hands", generate("hearts", 0, "experte").export()["view"])
        self.assertTrue(all(len(hand) == 13 - sum(seat == p for seat, _ in played) for p, hand in enumerate(sample)))
