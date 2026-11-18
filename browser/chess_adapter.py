"""Provide browser Stockfish analyses to the shared chess generator."""
from collections import OrderedDict
import json

from js import atelierChess

from raetselkalender.chess_puzzle import puzzle_from_record
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
