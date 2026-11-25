from itertools import product
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from raetselkalender.catalog import BY_ID, generate
from raetselkalender.generators import runs
from raetselkalender.nonogram_images import MOTIFS
from raetselkalender.nonogram_ui import NonogramUI
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
                    width, height = len(bitmap[0]), len(bitmap)
                    self.assertIn((width, height), {(11, 18), (12, 20), (13, 22), (14, 24)})
                    self.assertEqual((puzzle.view["cols"], puzzle.view["rows"]), (width, height))
                    self.assertTrue(all(len(line) == width and set(line) <= {"#", "."} for line in bitmap))
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
        self.assertEqual(BY_ID["bild-nonogramm"].title, "Nonogramm - Motiv")
        for level in ("mittel", "schwer"):
            puzzles = [generate("bild-nonogramm", seed, level) for seed in range(16)]
            self.assertTrue(all(puzzle.title == "Nonogramm - Motiv" for puzzle in puzzles))
            self.assertEqual({(puzzle.view["cols"], puzzle.view["rows"]) for puzzle in puzzles},
                             {(11, 18), (12, 20), (13, 22), (14, 24)})
            self.assertEqual(puzzles[0].solution, generate("bild-nonogramm", 0, level).solution)

    def test_wrong_fill_and_cross_each_cost_one_heart_and_lock_at_zero(self):
        ui = NonogramUI()
        ui.puzzle = SimpleNamespace(solution={"blank": 0, "filled": 1})
        ui.vars = {key: Mock() for key in ui.puzzle.solution}
        ui.note_vars = {key: Mock() for key in ui.puzzle.solution}
        ui.showing_solution = ui.busy = ui.nonogram_won = ui.note_mode = False
        ui.nonogram_lives = 3
        ui.on_change = Mock()
        ui.close_assistance = Mock()
        for key, value, remaining in (("blank", "1", 2), ("filled", "0", 1)):
            ui.mark_nonogram(key, value)
            self.assertEqual(ui.nonogram_lives, remaining)
            self.assertEqual(ui.nonogram_mistake, (key, value))
            ui.vars[key].set.assert_not_called()

        ui.mark_nonogram("blank", "0")
        ui.vars["blank"].set.assert_called_once_with("0")
        self.assertEqual(ui.nonogram_lives, 1)
        ui.mark_nonogram("blank", "1")
        self.assertEqual(ui.nonogram_lives, 0)
        ui.close_assistance.assert_called_once()
        ui.mark_nonogram("filled", "1")
        ui.vars["filled"].set.assert_not_called()
        self.assertEqual(ui.on_change.call_count, 4)
