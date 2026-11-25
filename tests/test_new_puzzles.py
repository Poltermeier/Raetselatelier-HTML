from fractions import Fraction
from math import lcm, prod
import unittest

from raetselkalender.catalog import generate
from raetselkalender.friedman import evaluate_friedman, friedman_numbers, readable_expression
from raetselkalender.new_puzzles import distance_paths, rotate_block
from raetselkalender.popout import LEVELS, PopOutGame, apply_move, engine_move, has_four, legal_moves


class NewPuzzleTests(unittest.TestCase):
    def test_distance_path_is_unique_and_strictly_increasing(self):
        for level in ("mittel", "schwer"):
            puzzle = generate("distance", 42, level)
            self.assertEqual(puzzle.title, "Distanz")
            points = puzzle.view["points"]
            path, = distance_paths(points)
            keys = [f"{points[i][1]},{points[i][0]}" for i in path]
            self.assertEqual([puzzle.solution[k] for k in keys], list(range(1, len(keys)+1)))
            edges = [(points[a][0]-points[b][0])**2+(points[a][1]-points[b][1])**2 for a,b in zip(path, path[1:])]
            self.assertTrue(all(a < b for a,b in zip(edges, edges[1:])))

    def test_sum_product_satisfies_rows_columns_and_distinctness(self):
        hard_sizes = set()
        for level in ("mittel", "schwer"):
            for seed in range(10):
                puzzle = generate("summe-produkt", seed, level)
                rows, cols = puzzle.view["rows"], puzzle.view["cols"]
                board = [[puzzle.solution[f"{r},{c}"] for c in range(cols)] for r in range(rows)]
                self.assertEqual(len({sum(row) for row in board}), 1)
                self.assertEqual(len({prod(col) for col in zip(*board)}), 1)
                self.assertEqual(len(set(puzzle.solution.values())), rows*cols)
                self.assertTrue(all(v > 0 for v in puzzle.solution.values()))
                if level == "mittel":
                    self.assertLessEqual(max(puzzle.solution.values()), 26)
                    given_counts = [sum(f"{r},{c}" in puzzle.givens for r in range(rows)) for c in range(cols)]
                    self.assertEqual(given_counts, [1, 1, 1])
                    products = []
                    given_values = list(puzzle.givens.values())
                    product_step = lcm(*given_values)
                    for common in range(product_step, 999*min(given_values)+1, product_step):
                        completions = puzzle.givens.copy()
                        for key in puzzle.editable:
                            r, c = key.split(",")
                            completions[key] = common//puzzle.givens[f"{1-int(r)},{c}"]
                        difference = sum(value if key.startswith("0,") else -value for key, value in completions.items())
                        if difference == 0 and len(set(completions.values())) == 6:
                            products.append(common)
                    self.assertEqual(products, [prod(row[0] for row in board)])
                else:
                    hard_sizes.add((rows, cols))
        self.assertEqual(hard_sizes, {(2, 4), (3, 3)})

    def test_friedman_bank_and_exact_ordered_evaluation(self):
        data = friedman_numbers()
        self.assertEqual(len(data), 648)
        for value, expression in data:
            self.assertEqual(evaluate_friedman(expression, value), value)
            self.assertEqual(evaluate_friedman(readable_expression(expression), value), value)
        self.assertEqual(readable_expression("((-1)+(2^7))"), "-1 + 2 ^ 7")
        for seed in range(16):
            self.assertLess(generate("friedman-zahlen", seed, "mittel").view["number"], 10000)
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

    def test_classic_does_not_offer_removal_to_either_player(self):
        for level in LEVELS:
            game = PopOutGame(2, level, allow_remove=False)
            for move in (0, 6, 1, 6, 2, 5):
                self.assertTrue(game.play(move))
            self.assertFalse(game.play(7))
            self.assertEqual(engine_move(game), 3)
            self.assertTrue(game.play(3))
            self.assertEqual(game.result, 0)

    def test_classic_draws_on_full_board_without_a_four(self):
        game = PopOutGame(3, "mittel", allow_remove=False)
        moves = (6, 6, 4, 1, 3, 5, 2, 2, 0, 2, 6, 2, 1, 0, 4, 0, 6, 5, 0, 4, 4, 4,
                 1, 1, 0, 4, 1, 3, 3, 5, 5, 3, 5, 3, 0, 1, 2, 3, 2, 6, 5, 6)
        for move in moves:
            self.assertIsNone(game.result)
            self.assertTrue(game.play(move))
        self.assertEqual(game.result, "draw")


    def test_medium_stops_the_early_fork_in_both_board_variants(self):
        for allow_remove in (False, True):
            for opening in ((3, 1, 2, 0), (3, 2, 1, 0), (3, 5, 4, 6)):
                with self.subTest(allow_remove=allow_remove, opening=opening):
                    game = PopOutGame(42, "mittel", allow_remove=allow_remove)
                    for column in opening:
                        self.assertTrue(game.play(column))
                        self.assertNotEqual(game.result, 0)
                        if game.result is not None:
                            break
                        self.assertTrue(game.play(engine_move(game)))
                        if game.result is not None:
                            break
