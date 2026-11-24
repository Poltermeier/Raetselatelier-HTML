from collections import Counter
import unittest

from raetselkalender.catalog import generate
from raetselkalender.case_clues import adjacent_run, position_clues
from raetselkalender.gruppen import partition_bank, partition_count, theme_bank
from raetselkalender.solver import Model, solve


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
                self.assertEqual([len(row) for row in rows], [4, 4, 4, 4, 4])
                names = [name for row in rows for name in row]
                self.assertEqual(names, sorted(puzzle.model.domains))
                self.assertEqual(puzzle.view["jobs"].keys(), puzzle.model.domains.keys())
                self.assertTrue(any(clue.kind == "profession" for clue in puzzle.statements.values()))
                self.assertIn("Nordhafen", puzzle.rules)
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

    def test_spatial_clues_distinguish_diagonal_neighbors_from_connections(self):
        rows = ("ABCD", "EFGH", "IJKL", "MNOP", "QRST")
        solution = {name: index % 2 for index, name in enumerate("".join(rows))}
        scopes, clues, orthogonal = position_clues(tuple(map(tuple, rows)), {"Küche": ("A", "H", "L", "Q")}, solution)
        self.assertEqual(next(scope.keys for scope in scopes if scope.kind == "neighbors" and scope.anchors == ("A",)), ("B", "E", "F"))
        self.assertEqual(orthogonal["A"], ("B", "E"))
        self.assertEqual(next(scope.keys for scope in scopes if scope.kind == "shared" and scope.anchors == ("A", "F")), ("B", "E"))
        self.assertEqual(next(scope.keys for scope in scopes if scope.kind == "between" and scope.anchors == ("A", "D")), ("B", "C"))
        self.assertEqual(next(clue.rule.keys for clue in clues if clue.text.startswith("In Spalte C")), ("C", "G", "K", "O", "S"))
        self.assertEqual(len(next(scope.keys for scope in scopes if scope.kind == "edge")), 14)
        self.assertEqual(next(scope.keys for scope in scopes if scope.kind == "corner"), ("A", "D", "Q", "T"))
        self.assertEqual(next(scope.keys for scope in scopes if scope.kind == "profession"), ("A", "H", "L", "Q"))
        self.assertTrue(adjacent_run((0, 1, 0)))
        self.assertFalse(adjacent_run((1, 0, 1)))

    def test_two_stage_hint_only_uses_open_clues_that_prove_the_person(self):
        puzzle = generate("ermittlungsakte", 42, "schwer")
        confirmed = {}
        name, indices = puzzle.next_hint(confirmed)
        self.assertEqual(indices, (0,))
        self.assertEqual((name,), puzzle.opening.rule.keys)
        for step in puzzle.logical_steps[:9]:
            confirmed[step["person"]] = step["value"]
        name, indices = puzzle.next_hint(confirmed)
        visible = puzzle.revealed_clues(confirmed)
        self.assertNotIn(name, confirmed)
        self.assertTrue(all(0 <= idx < len(visible) for idx in indices))
        model = Model(puzzle.model.domains, [visible[idx][1].rule for idx in indices])
        self.assertEqual(solve(model, {name: 1-puzzle.solution[name]}, limit=1).solutions, [])
