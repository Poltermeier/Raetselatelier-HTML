from fractions import Fraction
import unittest

from raetselkalender.catalog import generate
from raetselkalender.friedman import evaluate_friedman, friedman_numbers
from raetselkalender.new_puzzles import distance_paths, rotate_block
from raetselkalender.popout import LEVELS, PopOutGame, apply_move, engine_move, has_four, legal_moves


class NewPuzzleTests(unittest.TestCase):
    def test_distance_path_is_unique_and_strictly_increasing(self):
        for level in ("mittel", "schwer"):
            puzzle = generate("distance", 42, level)
            points = puzzle.view["points"]
            path, = distance_paths(points)
            keys = [f"{points[i][1]},{points[i][0]}" for i in path]
            self.assertEqual([puzzle.solution[k] for k in keys], list(range(1, len(keys)+1)))
            edges = [(points[a][0]-points[b][0])**2+(points[a][1]-points[b][1])**2 for a,b in zip(path, path[1:])]
            self.assertTrue(all(a < b for a,b in zip(edges, edges[1:])))

    def test_sum_product_satisfies_rows_columns_and_distinctness(self):
        for level in ("mittel", "schwer"):
            for seed in range(10):
                puzzle = generate("summe-produkt", seed, level)
                cols = puzzle.view["cols"]
                top, bottom = [[puzzle.solution[f"{r},{c}"] for c in range(cols)] for r in range(2)]
                self.assertEqual(sum(top), sum(bottom))
                self.assertEqual(len({a*b for a,b in zip(top, bottom)}), 1)
                self.assertEqual(len(set(top+bottom)), 2*cols)
                self.assertEqual(len(puzzle.givens), cols)
                self.assertTrue(all(v > 0 for v in top+bottom))

    def test_friedman_bank_and_exact_ordered_evaluation(self):
        data = friedman_numbers()
        self.assertEqual(len(data), 648)
        for value, expression in data:
            self.assertEqual(evaluate_friedman(expression, value), value)
        self.assertEqual(evaluate_friedman("(3/4)^3", 343), Fraction(27,64))
        self.assertEqual(evaluate_friedman("-1 + 2^7", 127), 127)
        for expression, number in (("3^7",73), ("127",127), ("1//27",127), ("1*02+7",1027)):
            with self.assertRaises(ValueError):
                evaluate_friedman(expression, number)

    def test_twiddle_replays_both_board_sizes(self):
        for level in ("mittel", "schwer"):
            puzzle = generate("twiddle", 42, level)
            view = puzzle.view
            board = view["initial"]
            self.assertNotEqual(board, view["target"])
            for action in puzzle.solution.values():
                board = rotate_block(board, view["size"], view["block"], action)
            self.assertEqual(board, view["target"])
        self.assertEqual(rotate_block(tuple(range(1,10)), 3, 2, (0,0,1)), (4,1,3,5,2,6,7,8,9))


class PopOutTests(unittest.TestCase):
    def test_pop_shifts_both_colors_and_only_owner_can_pop(self):
        game = PopOutGame(4, "mittel")
        self.assertTrue(game.play(0))
        self.assertFalse(game.play(7))
        self.assertTrue(game.play(0))
        self.assertTrue(game.play(0))
        self.assertTrue(game.play(1))
        self.assertTrue(game.play(7))
        self.assertTrue(game.board[1] & 1)
        self.assertTrue(game.board[0] & 2)
        self.assertFalse(game.board[0] & 4)

    def test_pops_can_win_for_opponent_or_both_mover_has_priority(self):
        for before, move, expected in (
                ((69795397632,4433215783040), 10, 1),
                ((79201992786560,57188852859136), 9, 0)):
            game = PopOutGame(4, "mittel")
            game.board = before
            self.assertFalse(any(map(has_four, before)))
            self.assertTrue(game.play(move))
            self.assertEqual(game.result, expected)

    def test_threefold_repetition_draws_and_full_columns_can_be_popped(self):
        game = PopOutGame(4, "mittel")
        for move in (0,1,7,8)*2:
            self.assertTrue(game.play(move))
        self.assertEqual(game.result, "draw")
        filled = (0b010101, 0b101010)
        self.assertNotIn(0, legal_moves(filled, 0))
        self.assertIn(7, legal_moves(filled, 0))

    def test_engine_takes_a_win_on_all_levels(self):
        for level in LEVELS:
            game = PopOutGame(19, level)
            for move in (0, 6, 1, 6, 2, 5):
                self.assertTrue(game.play(move))
            move = engine_move(game)
            self.assertIn(move, legal_moves(game.board, game.turn))
            self.assertTrue(has_four(apply_move(game.board, game.turn, move)[0]))
