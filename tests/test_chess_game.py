from importlib.util import find_spec
import unittest

if find_spec("chess") is None:
    raise unittest.SkipTest("python-chess is optional outside the browser")

import chess

from raetselkalender.chess_game import ChessGame, Review, review_text


class ChessGameTests(unittest.TestCase):
    def test_legal_moves_checkmate_and_review_preserve_the_completed_game(self):
        game = ChessGame(1500, chess.WHITE)
        self.assertFalse(game.play(chess.Move.from_uci("e2e5")))
        for move in ("f2f3", "e7e5", "g2g4", "d8h4"):
            self.assertTrue(game.play(chess.Move.from_uci(move)))
        self.assertEqual(game.result, "Schwarz gewinnt durch Schachmatt.")
        review = game.position_before(3)
        self.assertFalse(review.is_checkmate())
        self.assertTrue(game.board.is_checkmate())
        self.assertFalse(game.play(chess.Move.from_uci("h2h3")))
        self.assertIn("Stockfish empfiehlt ebenfalls Dh4#", review_text(
            review, game.board.peek(), Review("d8h4", {"mate": 1}, {"mate": 1}, ("d8h4",))))

    def test_player_can_claim_a_threefold_repetition(self):
        game = ChessGame(1320, chess.WHITE)
        game.claim_draw()
        self.assertEqual(game.result, "")
        for move in ("g1f3", "g8f6", "f3g1", "f6g8") * 2:
            self.assertTrue(game.play(chess.Move.from_uci(move)))
        game.claim_draw()
        self.assertIn("Remis", game.result)
