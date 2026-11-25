from itertools import combinations
from math import dist, hypot
import unittest

from raetselkalender.symbol_duel import SymbolDuel, deal_symbols
from raetselkalender.symbol_duel_ui import CARD_RADIUS, SYMBOL_OFFSETS, TARGET_RADIUS, symbol_faces
from raetselkalender.symbol_icons import ICONS


class SymbolDuelTests(unittest.TestCase):
    def test_deck_size_and_unique_match_for_every_pair(self):
        self.assertEqual(len(ICONS), 57)
        self.assertEqual(len({name for name, _, _ in ICONS}), 57)
        for seed in (0, 1, 49383):
            with self.subTest(seed=seed):
                cards = list(map(frozenset, deal_symbols(seed)))
                self.assertEqual(len(set(cards)), 55)
                self.assertTrue(all(len(card) == 8 for card in cards))
                self.assertEqual(set.union(set(), *cards), set(range(len(ICONS))))
                for first, second in combinations(cards, 2):
                    self.assertEqual(len(first & second), 1)

    def test_seed_reproduces_deck_and_symbol_order(self):
        cards = deal_symbols(12)
        self.assertEqual(cards, deal_symbols(12))
        self.assertNotEqual(cards, deal_symbols(13))

    def test_round_cards_keep_targets_separate_and_motifs_varied(self):
        self.assertEqual(len(SYMBOL_OFFSETS), 8)
        for x, y in SYMBOL_OFFSETS:
            self.assertLess(hypot(x, y) + TARGET_RADIUS, CARD_RADIUS)
        for first, second in combinations(SYMBOL_OFFSETS, 2):
            self.assertGreater(dist(first, second), 2 * TARGET_RADIUS)
        faces = symbol_faces(42, 0)
        sizes, angles = zip(*faces)
        self.assertEqual(len(set(sizes)), 8)
        self.assertEqual(sum(angle == 0 for angle in angles), 2)
        self.assertTrue(all(abs(angle) < 20 for angle in angles))
        self.assertEqual(faces, symbol_faces(42, 0))
        self.assertNotEqual(faces, symbol_faces(42, 1))

    def test_only_matches_advance_and_each_replacement_uses_next_card(self):
        game = SymbolDuel(4)
        for hits in range(54):
            before = game.open_indices
            left, right = map(set, game.open_cards)
            self.assertFalse(game.choose(min(left - right)))
            self.assertEqual(game.open_indices, before)
            self.assertEqual(game.hits, hits)
            self.assertTrue(game.choose(min(left & right)))
            self.assertEqual(game.hits, hits + 1)
            if hits < 53:
                removed_side = 1 if hits % 2 == 0 else 0
                self.assertEqual(game.open_indices[1 - removed_side], before[1 - removed_side])
                self.assertEqual(game.open_indices[removed_side], hits + 2)
            else:
                self.assertEqual(game.open_indices, before)
        self.assertTrue(game.finished)
        self.assertFalse(game.choose(min(left & right)))
