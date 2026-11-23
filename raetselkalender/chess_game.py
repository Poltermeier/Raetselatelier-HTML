"""Rules and Stockfish requests for a full game of chess."""
from dataclasses import dataclass

import chess
import chess.engine

from .chess_engine import stockfish_path, stockfish_missing_message
from .chess_explanations import SAN_GERMAN, san
from .live_chess import open_engine

PLAY_SECONDS = .35
REVIEW_NODES = 24000
TERMINATIONS = {
    chess.Termination.CHECKMATE: "Schachmatt",
    chess.Termination.STALEMATE: "Patt",
    chess.Termination.INSUFFICIENT_MATERIAL: "Unzureichendes Material",
    chess.Termination.SEVENTYFIVE_MOVES: "75-Züge-Regel",
    chess.Termination.FIVEFOLD_REPETITION: "Fünffache Stellungswiederholung",
}


def color_name(color):
    return "Weiß" if color else "Schwarz"


class ChessGame:
    def __init__(self, elo, player):
        self.board = chess.Board()
        self.elo = elo
        self.player = player
        self.result = ""

    def play(self, move):
        if self.result or move not in self.board.legal_moves:
            return False
        self.board.push(move)
        outcome = self.board.outcome()
        if outcome:
            reason = TERMINATIONS[outcome.termination]
            winner = "Remis" if outcome.winner is None else f"{color_name(outcome.winner)} gewinnt"
            self.result = f"{winner} durch {reason}."
        return True

    def resign(self):
        if not self.result:
            self.result = f"{color_name(self.player)} gibt auf. {color_name(not self.player)} gewinnt."

    def claim_draw(self):
        if not self.result and self.board.turn == self.player and self.board.can_claim_draw():
            self.result = "Remis beansprucht nach der 50-Züge-Regel oder durch Stellungswiederholung."

    def position_before(self, index):
        board = chess.Board()
        for move in self.board.move_stack[:index]:
            board.push(move)
        return board


@dataclass(frozen=True)
class Review:
    best_move: str
    best_score: dict
    played_score: dict
    variation: tuple[str, ...]


def score_label(score):
    if "mate" in score:
        mate = score["mate"]
        return f"Matt in {abs(mate)} {'für' if mate > 0 else 'gegen'} die Seite am Zug" if mate else "Schachmatt"
    return f"{score['cp']/100:+.2f}".replace(".", ",")


def review_text(position, played, review):
    best = chess.Move.from_uci(review.best_move)
    if best == played:
        comparison = f"Stockfish empfiehlt ebenfalls {san(position, best)} ({score_label(review.best_score)})."
    else:
        comparison = (f"Stockfish empfiehlt {san(position, best)} ({score_label(review.best_score)}). "
                      f"Gespielt wurde {san(position, played)} ({score_label(review.played_score)}).")
    line = [chess.Move.from_uci(uci) for uci in review.variation]
    context = f" Bewertung aus Sicht von {color_name(position.turn)}."
    variation = "\nVariante · " + position.variation_san(line).translate(SAN_GERMAN) if line else ""
    return comparison + context + variation


def native_chess_request(kind, board, argument):
    path = stockfish_path()
    if not path:
        raise ValueError(stockfish_missing_message())
    with open_engine(path) as engine:
        if kind == "play":
            elo = engine.options["UCI_Elo"]
            if not elo.min <= argument <= elo.max:
                raise ValueError(f"Diese Stockfish-Version unterstützt {elo.min} bis {elo.max} Elo.")
            result = engine.play(board, chess.engine.Limit(time=PLAY_SECONDS),
                                 options={"UCI_LimitStrength": True, "UCI_Elo": argument})
            return result.move.uci()

        limit = chess.engine.Limit(nodes=REVIEW_NODES)
        best = engine.analyse(board, limit)
        played = argument
        actual = best if played == best["pv"][0] else engine.analyse(board, limit, root_moves=[played])

        def score(row):
            value = row["score"].pov(board.turn)
            return {"mate": value.mate()} if value.is_mate() else {"cp": value.score()}

        return Review(best["pv"][0].uci(), score(best), score(actual),
                      tuple(move.uci() for move in best["pv"][:6]))
