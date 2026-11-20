from importlib.util import find_spec
import unittest

if find_spec("chess") is None:
    raise unittest.SkipTest("python-chess is optional outside the browser")

import chess

from raetselkalender.live_chess import SHALLOW_NODES, hard_enough, obvious_material_win
from raetselkalender.chess_explanations import legal_line, mate_replies


class ChessDifficultyTests(unittest.TestCase):
    def test_free_queen_is_obvious_even_when_the_capture_gives_check(self):
        board = chess.Board("3q3k/6pp/8/8/8/8/3R4/6K1 w - - 0 1")
        move = chess.Move.from_uci("d2d8")
        self.assertTrue(board.gives_check(move))
        self.assertTrue(obvious_material_win(board, move.uci()))
        self.assertEqual(board.fen(), "3q3k/6pp/8/8/8/8/3R4/6K1 w - - 0 1")

    def test_a_capture_that_can_be_recaptured_is_not_automatically_obvious(self):
        board = chess.Board("3r3k/6pp/8/8/3p4/8/3Q4/6K1 w - - 0 1")
        self.assertFalse(obvious_material_win(board, "d2d4"))

    def test_short_search_must_not_identify_the_best_move_clearly(self):
        board = chess.Board()
        best = {"best_move": "e2e4"}
        probe = {"nodes_limit": SHALLOW_NODES, "best_move": "e2e4",
                 "best": {"cp": 120}, "runner_up": {"cp": -30}}
        self.assertFalse(hard_enough(board, probe, best))
        probe["runner_up"] = {"cp": 95}
        self.assertTrue(hard_enough(board, probe, best))

    def test_mate_example_uses_legal_replies_and_restores_the_board(self):
        board = chess.Board("7r/1P2bk2/p3p1p1/2Np1p2/Q2P4/4P3/4BKPq/R7 b - - 0 28")
        line = legal_line(board, ["e7h4", "f2f1", "h2h1", "a1a2"])
        self.assertEqual(len(line), 3)
        board.push(line[0])
        before = board.fen()
        examples = mate_replies(board, line)
        self.assertEqual(board.fen(), before)
        self.assertIn("Auf Kf1 folgt Dh1#.", examples)
        self.assertIn("Auf Kf3 folgt Dg3#.", examples)
