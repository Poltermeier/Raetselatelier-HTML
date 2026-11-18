"""Regression tests for varying Pentomino pieces without losing legal tilings."""
from collections import Counter
from unittest import TestCase

from raetselkalender.catalog import generate
from raetselkalender.pentomino import orientations


class PentominoTests(TestCase):
    def test_seeds_vary_the_shapes_and_keep_a_complete_tiling(self):
        for level, pairs in (("mittel", 2), ("schwer", 3)):
            families_by_seed = set()
            for seed in (0, 17, 42):
                puzzle = generate("pentomino-puzzle", seed, level)
                shapes = puzzle.view["shapes"]
                self.assertEqual(Counter(map(len, shapes.values())),
                                 {4: pairs, 5: 12 - 2 * pairs, 6: pairs})
                families = frozenset(orientations(points)[0] for points in shapes.values())
                self.assertEqual(len(families), 12)
                families_by_seed.add(families)

                covered = Counter(cell for name, index in puzzle.solution.items()
                                  for cell in puzzle.options[name][index])
                self.assertEqual(covered, Counter(range(puzzle.view["rows"] * puzzle.view["cols"])))
                self.assertEqual(puzzle.check(puzzle.solution), ("correct", []))
            self.assertEqual(len(families_by_seed), 3)

    def test_reflected_tiling_is_accepted_and_the_same_seed_repeats(self):
        puzzle = generate("pentomino-puzzle", 42, "schwer")
        cols = puzzle.view["cols"]
        reflected = {}
        for name, index in puzzle.solution.items():
            cells = puzzle.options[name][index]
            mirror = tuple(sorted(point // cols * cols + cols - 1 - point % cols for point in cells))
            reflected[name] = puzzle.options[name].index(mirror)
        self.assertNotEqual(reflected, puzzle.solution)
        self.assertEqual(puzzle.check(reflected), ("correct", []))

        repeated = generate("pentomino-puzzle", 42, "schwer")
        self.assertEqual(repeated.view, puzzle.view)
        self.assertEqual(repeated.solution, puzzle.solution)
