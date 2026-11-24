import unittest

from raetselkalender.catalog import generate
from raetselkalender.fillomino import fillomino_solutions
from raetselkalender.placement_puzzles import PIECES, adjacency, chess_attacks, placement_solutions, water_solutions


class PlacementPuzzleTests(unittest.TestCase):
    def test_harakiri_rings_and_diameters_each_contain_all_eight_numbers(self):
        for level in ("mittel", "schwer"):
            puzzle = generate("harakiri", 42, level)
            self.assertEqual(len(puzzle.solution), 32)
            for unit in puzzle.model.constraints:
                self.assertEqual({puzzle.solution[k] for k in unit.keys}, set(range(1, 9)))
            self.assertTrue(puzzle.analysis["unique"])

    def test_water_has_one_cover_with_adjacent_hydrogen_atoms(self):
        for level in ("mittel", "schwer"):
            for seed in (1, 5, 42):
                puzzle = generate("h2o", seed, level)
                size, hydrogen = puzzle.view["size"], puzzle.view["hydrogen"]
                layout = tuple(sorted((int(o), *pair) for o, pair in puzzle.solution.items()))
                self.assertEqual(water_solutions(size, hydrogen), [layout])
                self.assertEqual(sorted(atom for _, a, b in layout for atom in (a, b)), hydrogen)
                for center, a, b in layout:
                    self.assertNotIn(center, hydrogen)
                    self.assertIn(a, adjacency(size)[center])
                    self.assertIn(b, adjacency(size)[center])

    def test_chess_pieces_respect_clue_counts_and_never_target_each_other(self):
        for level in ("mittel", "schwer"):
            puzzle = generate("schachaufstellung", 42, level)
            size, clues = puzzle.view["size"], puzzle.view["clues"]
            self.assertEqual(set(puzzle.solution), set(PIECES))
            self.assertEqual(len(set(puzzle.solution.values())), len(PIECES))
            self.assertFalse(set(puzzle.solution.values()).intersection(clues))
            for piece, origin in puzzle.solution.items():
                for other, target in puzzle.solution.items():
                    if piece != other:
                        self.assertFalse(chess_attacks(size)[piece][origin] & 1 << target)
            self.assertEqual(placement_solutions(size, clues), [puzzle.solution])

    def test_fillomino_has_one_cover_including_possible_unclued_groups(self):
        for level in ("mittel", "schwer"):
            puzzle = generate("fillomino", 42, level)
            size = puzzle.view["size"]
            labels = {}
            expected = []
            for r in range(size):
                for c in range(size):
                    key = f"{r},{c}"
                    expected.append(puzzle.solution[key])
                    if key in puzzle.givens:
                        labels[r*size+c] = puzzle.givens[key]
            self.assertEqual(fillomino_solutions(size, labels), [tuple(expected)])
        self.assertIn((4, 4, 4, 4), fillomino_solutions(2, {0: 4}))
        self.assertEqual(fillomino_solutions(2, {0: 1, 1: 1}), [])
