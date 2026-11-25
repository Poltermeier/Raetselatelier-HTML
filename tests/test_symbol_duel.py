from itertools import combinations
from math import dist, hypot
import unittest

from raetselkalender.symbol_duel import SymbolDuel, deal_symbols
from raetselkalender.symbol_duel_ui import (
    INNER_RADIUS, MIN_TOUCH_RADIUS, SYMBOL_GAP, SYMBOL_SIZES, native_symbol_points, symbol_placements, symbol_touch_radius,
)
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

    def test_cards_have_different_positions_and_clear_tap_targets(self):
        for seed in (0, 42, 49383):
            layouts = tuple(symbol_placements(seed, index) for index in range(55))
            with self.subTest(seed=seed):
                self.assertEqual(len({tuple(slot[:2] for slot in card) for card in layouts}), 55)
                self.assertEqual(layouts[0], symbol_placements(seed, 0))
                self.assertTrue(any(all(hypot(slot.x, slot.y) > 15 for slot in card) for card in layouts))
                for card in layouts:
                    self.assertEqual(len(card), 8)
                    for slot in card:
                        self.assertGreaterEqual(slot.radius, MIN_TOUCH_RADIUS)
                        self.assertLessEqual(hypot(slot.x, slot.y) + slot.radius, INNER_RADIUS + 1e-8)
                    gaps = [dist(a[:2], b[:2]) - a.radius - b.radius for a, b in combinations(card, 2)]
                    self.assertGreaterEqual(min(gaps), SYMBOL_GAP - 1e-8)
                    self.assertLessEqual(min(gaps), 7)

    def test_cards_keep_the_variation_in_symbol_size_and_rotation(self):
        card = symbol_placements(42, 0)
        sizes = {slot.size for slot in card}
        angles = {slot.angle for slot in card}
        self.assertEqual(len(sizes), 8)
        self.assertGreater(max(sizes) / min(sizes), 2.3)
        self.assertLessEqual(min(angles), -140)
        self.assertGreaterEqual(max(angles), 140)
        self.assertIn(0, angles)

    def test_motifs_fit_their_touch_targets_at_any_rotation(self):
        for name, _, primitives in ICONS:
            for kind, coords, _ in primitives:
                radius = max(hypot(x - 12, y - 12) for x, y in native_symbol_points(kind, coords))
                # Include half the 1.55-unit round outline for any non-dot primitive.
                if kind != "dot":
                    radius += 1.55 / 2
                for size in SYMBOL_SIZES:
                    self.assertLess(radius * (size / 24), symbol_touch_radius(size), name)

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
