"""Provide browser Stockfish analyses to the shared chess generator."""
from collections import OrderedDict
import json

from js import atelierChess

from raetselkalender.chess_puzzle import puzzle_from_record
from raetselkalender.chess_game import PLAY_SECONDS, REVIEW_NODES, Review
from raetselkalender.live_chess import search_record

_records = OrderedDict()


async def browser_chess_puzzle(seed, difficulty):
    key = seed, difficulty
    if key in _records:
        _records.move_to_end(key)
    else:
        _records[key] = await generate_record(seed, difficulty)
        if len(_records) > 128:
            _records.popitem(last=False)
    return puzzle_from_record(seed, difficulty, json.loads(_records[key]))


async def generate_record(seed, difficulty):
    engine = atelierChess()
    try:
        await engine.ready
        search = search_record(seed, difficulty, engine.name)
        response = None
        while True:
            try:
                board, nodes = search.send(response)
            except StopIteration as result:
                return result.value
            raw = await engine.analyze(board.fen(), nodes)
            response = json.loads(raw) if raw else None
    finally:
        engine.close()


async def browser_chess_request(kind, board, argument):
    position = "startpos"
    if board.move_stack:
        position += " moves " + " ".join(move.uci() for move in board.move_stack)
    engine = atelierChess()
    try:
        await engine.ready
        if kind == "play":
            return str(await engine.play(position, argument, round(PLAY_SECONDS * 1000)))
        best = json.loads(await engine.evaluate(position, REVIEW_NODES, ""))
        played = argument.uci()
        actual = best if played == best["moves"][0] else json.loads(await engine.evaluate(position, REVIEW_NODES, played))
        return Review(best["moves"][0], best["score"], actual["score"], tuple(best["moves"]))
    finally:
        engine.close()
