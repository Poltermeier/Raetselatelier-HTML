import unittest

from raetselkalender.assistance import jump_distances, model_hint, wrong_answers
from raetselkalender.catalog import generate


class AssistanceTests(unittest.TestCase):
    def test_review_only_counts_entered_editable_answers(self):
        puzzle = generate("mini-sudoku", 42, "mittel")
        wrong, correct = puzzle.editable[:2]
        given = next(iter(puzzle.givens))
        answers = {wrong: 0, correct: puzzle.solution[correct], given: 0}

        self.assertEqual(wrong_answers(puzzle, answers), {wrong: 0})

    def test_hint_targets_an_unanswered_field_without_changing_inputs(self):
        puzzle = generate("mini-sudoku", 42, "mittel")
        filled = puzzle.editable[0]
        answers = {filled: puzzle.solution[filled]}
        snapshot = answers.copy()

        key, explanation = model_hint(puzzle, answers)

        self.assertIn(key, puzzle.editable[1:])
        self.assertTrue(explanation)
        self.assertEqual(answers, snapshot)

    def test_jump_distance_can_identify_a_legal_but_longer_route(self):
        puzzle = generate("jump-puzzle", 42, "mittel")
        view = puzzle.view
        distances = jump_distances(puzzle)
        first = puzzle.solution[puzzle.editable[0]]
        other = next(target for target in puzzle.targets(view["start"]) if target != first)

        self.assertEqual(distances[view["goal"]], 0)
        self.assertEqual(distances[view["start"]], view["par"])
        self.assertEqual(1 + distances[first], view["par"])
        self.assertGreater(1 + distances.get(other, float("inf")), view["par"])
