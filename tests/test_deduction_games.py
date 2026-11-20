from collections import Counter
import unittest

from raetselkalender.catalog import generate
from raetselkalender.case_clues import position_clues
from raetselkalender.gruppen import partition_bank, partition_count, theme_bank


class GruppenTests(unittest.TestCase):
    def test_four_distinct_groups_and_a_single_catalogued_partition(self):
        for difficulty in ("mittel", "schwer"):
            seen = set()
            for seed in range(25):
                puzzle = generate("gruppen", seed, difficulty)
                words = puzzle.view["words"]
                self.assertEqual(len(words), 16)
                self.assertEqual(Counter(words), Counter(word for _, group in puzzle.groups for word in group))
                self.assertEqual(partition_count(words, partition_bank()), 1)
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
        equivalent = {"a": tuple("abcd"), "b": tuple("abcd"), "c": tuple("efgh")}
        self.assertEqual(partition_count("abcdefgh", equivalent), 1)

    def test_extended_categories_include_everyday_and_wordplay_entries(self):
        self.assertGreaterEqual(len(theme_bank("mittel")), 98)
        self.assertGreaterEqual(len(theme_bank("schwer")), 167)
        self.assertIn("Zürichsee", theme_bank("mittel")["Große Seen im Alpenraum"])
        self.assertIn("Fall", theme_bank("schwer")["Wörter mit „Wasser“ davor"])
        self.assertGreater(len(set().union(*map(set, partition_bank().values()))), 2300)


class ErmittlungsakteTests(unittest.TestCase):
    def test_certified_progression_reveals_one_statement_per_person(self):
        for difficulty in ("mittel", "schwer"):
            for seed in range(20):
                puzzle = generate("ermittlungsakte", seed, difficulty)
                rows = puzzle.view["people"]
                self.assertEqual([len(row) for row in rows], [5, 5, 5, 5])
                self.assertEqual({name for row in rows for name in row}, puzzle.model.domains.keys())
                self.assertEqual(puzzle.givens, {})
                self.assertEqual(puzzle.export()["view"]["clues"], [puzzle.opening.export()])
                self.assertNotIn("solution", puzzle.export())
                self.assertNotIn("statements", puzzle.export())
                self.assertNotIn("logical_proof", puzzle.export())
                self.assertEqual(puzzle.export(True)["statements"].keys(), puzzle.model.domains.keys())

                confirmed = {}
                self.assertEqual(puzzle.revealed_clues(confirmed), [(None, puzzle.opening)])
                for step in puzzle.logical_steps:
                    name, value = step["person"], step["value"]
                    self.assertEqual(puzzle.classify(name, value, confirmed), "correct")
                    self.assertEqual(puzzle.classify(name, 1 - value, confirmed), "wrong")
                    confirmed[name] = value
                    self.assertEqual(len(puzzle.revealed_clues(confirmed)), 1 + len(confirmed))
                    self.assertEqual(puzzle.revealed_clues(confirmed)[-1], (name, puzzle.statements[name]))
                    self.assertEqual(puzzle.classify(name, value, confirmed), "invalid")
                self.assertEqual(confirmed, puzzle.solution)
            self.assertEqual(generate("ermittlungsakte", 42, difficulty).export(True),
                             generate("ermittlungsakte", 42, difficulty).export(True))

    def test_hidden_evidence_cannot_validate_even_a_correct_guess(self):
        puzzle = generate("ermittlungsakte", 42, "mittel")
        start, left = [step["person"] for step in puzzle.logical_steps[:2]]
        self.assertEqual(puzzle.classify(left, puzzle.solution[left], {}), "undetermined")
        self.assertEqual(puzzle.classify(left, 1 - puzzle.solution[left], {}), "undetermined")
        self.assertEqual(puzzle.classify(start, puzzle.solution[start], {}), "correct")

        confirmed = {start: puzzle.solution[start]}
        self.assertEqual(puzzle.classify(left, puzzle.solution[left], confirmed), "correct")
        confirmed[left] = puzzle.solution[left]
        self.assertEqual([name for name, _ in puzzle.revealed_clues(confirmed)], [None, start, left])

    def test_combining_released_statements_is_required(self):
        for difficulty, minimum in (("mittel", 1), ("schwer", 2)):
            puzzle = generate("ermittlungsakte", 42, difficulty)
            order = [step["person"] for step in puzzle.logical_steps]
            combinations = 0
            for count in range(2, len(order)):
                old, one, other = order[:count - 2], order[count - 2], order[count - 1]
                for name in order[count:]:
                    role = puzzle.solution[name]
                    if (puzzle.classify(name, role, order[:count]) == "correct"
                            and puzzle.classify(name, role, [*old, one]) == "undetermined"
                            and puzzle.classify(name, role, [*old, other]) == "undetermined"):
                        combinations += 1
                        break
            self.assertGreaterEqual(combinations, minimum)

    def test_spatial_clues_use_orthogonal_neighbors_and_shared_neighbors(self):
        rows = ("ABCDE", "FGHIJ", "KLMNO", "PQRST")
        rooms = ("Werkstatt", "Bühne", "Foyer", "Studio")
        solution = {name: index % 2 for index, name in enumerate("".join(rows))}
        scopes, clues, _ = position_clues(tuple(map(tuple, rows)), rooms, solution)
        self.assertEqual(next(scope.keys for scope in scopes if scope.anchors == ("A",)), ("B", "F"))
        self.assertEqual(next(scope.keys for scope in scopes if scope.anchors == ("A", "G")), ("B", "F"))
        self.assertEqual(next(scope.keys for scope in scopes if scope.anchors == ("A", "E")), ("B", "C", "D"))
        self.assertEqual(next(clue.rule.keys for clue in clues if clue.text.startswith("In Spalte C")), ("C", "H", "M", "R"))
