from itertools import product
import unittest

from raetselkalender.catalog import BY_ID, generate
from raetselkalender.generators import runs
from raetselkalender.nonogram_images import MOTIFS
from raetselkalender.picture_nonogram import line_patterns, puzzle_for_motif


class PictureNonogramTests(unittest.TestCase):
    def test_line_patterns_match_binary_runs(self):
        for length in range(1, 8):
            by_hint = {}
            for bits in product((0, 1), repeat=length):
                by_hint.setdefault(tuple(runs(bits)), set()).add(bits)
            for hints, expected in by_hint.items():
                self.assertEqual(set(line_patterns(length, hints)), expected)

    def test_each_original_motif_and_mirror_is_unique_without_givens(self):
        self.assertEqual(len({name for name, _, _ in MOTIFS}), len(MOTIFS))
        for name, level, image in MOTIFS:
            for mirrored in (False, True):
                with self.subTest(name=name, mirrored=mirrored):
                    bitmap = tuple(line[::-1] for line in image) if mirrored else image
                    puzzle = puzzle_for_motif(name, bitmap, 42, level)
                    self.assertEqual((puzzle.view["cols"], puzzle.view["rows"]), (12, 20))
                    self.assertTrue(all(len(line) == 12 and set(line) <= {"#", "."} for line in bitmap))
                    self.assertEqual(puzzle.result, name)
                    self.assertTrue(puzzle.analysis["unique"])
                    self.assertTrue(puzzle.analysis["logical_solvable"])
                    self.assertFalse(puzzle.givens)
                    self.assertNotIn("result", puzzle.export())

    def test_renamed_digit_puzzle_and_new_picture_puzzle_are_available(self):
        old = generate("nonogramm", 30, "mittel")
        self.assertEqual(BY_ID["nonogramm"].title, "Zahlen Nonogramm")
        self.assertEqual(old.title, "Zahlen Nonogramm")
        self.assertEqual((old.view["cols"], old.view["rows"]), (10, 5))
        for level in ("mittel", "schwer"):
            puzzles = [generate("bild-nonogramm", seed, level) for seed in range(6)]
            self.assertGreater(len({puzzle.result for puzzle in puzzles}), 1)
            self.assertEqual(puzzles[0].solution, generate("bild-nonogramm", 0, level).solution)
