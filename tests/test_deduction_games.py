from collections import Counter
import unittest

from raetselkalender.catalog import generate
from raetselkalender.gruppen import partition_count, theme_bank
from raetselkalender.solver import deduce


class GruppenTests(unittest.TestCase):
    def test_four_distinct_groups_and_a_single_catalogued_partition(self):
        for difficulty in ("mittel", "schwer"):
            seen = set()
            for seed in range(25):
                puzzle = generate("gruppen", seed, difficulty)
                words = puzzle.view["words"]
                self.assertEqual(len(words), 16)
                self.assertEqual(Counter(words), Counter(word for _, group in puzzle.groups for word in group))
                self.assertEqual(partition_count(words, theme_bank(difficulty)), 1)
                self.assertEqual(len(puzzle.groups), 4)
                for index, (_, group) in enumerate(puzzle.groups):
                    self.assertEqual(puzzle.check_group(group[::-1]), index)
                    self.assertIsNone(puzzle.check_group(group[:3]))
                self.assertNotIn("solution", puzzle.export())
                self.assertEqual(set(puzzle.export()["view"]), {"kind", "mode", "words"})
                self.assertEqual(len(puzzle.export(True)["solution"]), 4)
                seen.add(tuple(words))
                if difficulty == "schwer":
                    self.assertTrue(any(len(set(words).intersection(theme_bank(difficulty)[theme])) > 4
                                        for theme, _ in puzzle.groups))
            self.assertEqual(len(seen), 25)
            self.assertEqual(generate("gruppen", 42, difficulty).export(True),
                             generate("gruppen", 42, difficulty).export(True))

    def test_partition_validation_detects_an_alternate_grouping(self):
        catalog = {
            "a": ("a", "b", "c", "d", "e"),
            "b": ("a", "b", "e", "f", "g", "h"),
        }
        self.assertEqual(partition_count("abcdefgh", catalog), 2)
        self.assertEqual(partition_count("abcdefgi", catalog), 0)


class ErmittlungsakteTests(unittest.TestCase):
    def test_public_evidence_proves_every_person_without_search(self):
        for difficulty, size in (("mittel", 9), ("schwer", 12)):
            for seed in range(30):
                puzzle = generate("ermittlungsakte", seed, difficulty)
                people = {name for room in puzzle.view["people"] for name in room}
                self.assertEqual(len(people), size)
                self.assertEqual(people, puzzle.model.domains.keys())
                self.assertEqual(len(puzzle.givens), 1)
                self.assertEqual(len(puzzle.view["clues"]), 1 + len(puzzle.model.constraints))
                for clue, constraint in zip(puzzle.view["clues"][1:], puzzle.model.constraints):
                    self.assertEqual(tuple(clue["people"]), constraint.keys)
                deduction = deduce(puzzle.model, puzzle.givens)
                self.assertTrue(deduction.solved)
                self.assertEqual({key: next(iter(values)) for key, values in deduction.domains.items()},
                                 puzzle.solution)
                entries = {name: puzzle.solution[name] for name in puzzle.editable}
                self.assertEqual(puzzle.check(entries), ("correct", []))
                first = next(iter(entries))
                self.assertEqual(puzzle.check(entries | {first: 1 - entries[first]}), ("wrong", [first]))
                self.assertEqual(puzzle.check({}), ("incomplete", []))
                self.assertNotIn("solution", puzzle.export())
                self.assertNotIn("logical_proof", puzzle.export())
                self.assertTrue(puzzle.export(True)["logical_proof"])
            self.assertEqual(generate("ermittlungsakte", 42, difficulty).export(True),
                             generate("ermittlungsakte", 42, difficulty).export(True))
