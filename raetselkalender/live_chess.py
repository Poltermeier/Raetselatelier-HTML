"""Generate fresh reachable chess positions and verify them with a live UCI engine."""
from functools import lru_cache
import hashlib
import json
import os
import random
import subprocess
import time

import chess
import chess.engine

from .chess_engine import stockfish_path,stockfish_missing_message
from .chess_explanations import PIECE_VALUES
from .chess_validation import MateProofBudget,verify_unique_mate

BUDGETS={'mittel':(35000,100000),'schwer':(60000,180000)}
SHALLOW_NODES = 1200


def digest(record):
    return hashlib.sha256(json.dumps({k:v for k,v in record.items() if k!='digest'},sort_keys=True,separators=(',',':')).encode()).hexdigest()


def open_engine(path):
    kwargs={'creationflags':subprocess.CREATE_NO_WINDOW} if os.name=='nt' else {}
    engine=chess.engine.SimpleEngine.popen_uci(path,timeout=15,**kwargs)
    engine.configure({name: value for name, value in {'Threads':1,'Hash':32}.items() if name in engine.options})
    return engine


def analysis(engine,board,nodes):
    if 'Clear Hash' in engine.options:engine.configure({'Clear Hash':None})
    by_depth = {}
    with engine.analysis(board.copy(stack=False), chess.engine.Limit(nodes=nodes), multipv=2) as stream:
        for row in stream:
            if row.get('depth') and row.get('pv') and 'score' in row and not (row.get('upperbound') or row.get('lowerbound')):
                by_depth.setdefault(row['depth'], {})[row['multipv']] = row
    depth = max((depth for depth, pair in by_depth.items() if 1 in pair and 2 in pair), default=0)
    if not depth:
        return None
    best, runner = by_depth[depth][1], by_depth[depth][2]
    def score(row):
        value=row['score'].pov(board.turn)
        return {'mate':value.mate()} if value.is_mate() else {'cp':value.score()}
    return dict(nodes_limit=nodes, depth=depth,
                best_move=best['pv'][0].uci(), runner_up_move=runner['pv'][0].uci(),
                best=score(best), runner_up=score(runner), pv=[m.uci() for m in best['pv'][:12]],
                runner_pv=[m.uci() for m in runner['pv'][:8]])


def acceptable(check,difficulty,*,quick=False):
    if check is None:return False
    best,runner=check['best'],check['runner_up']
    if 'mate' in best:
        mate=best['mate'];other=runner.get('mate')
        return mate is not None and (mate==2 if difficulty=='schwer' else 1<=mate<=2) and (other is None or other<=0 or other>mate)
    gap = (130 if difficulty == 'schwer' else 170) if quick else 200
    return ('cp' in runner and runner['cp']<=(250 if quick else 200) and best['cp']>=-150 and best['cp']<=1800
            and best['cp']-runner['cp']>=gap)


def exchange_value(board, move):
    """Value of a capture or promotion if both sides trade optimally on that square."""
    captured = board.piece_type_at(move.to_square)
    gain = 100 if board.is_en_passant(move) else PIECE_VALUES.get(captured, 0)
    if move.promotion:
        gain += PIECE_VALUES[move.promotion] - PIECE_VALUES[chess.PAWN]
    board.push(move)
    try:
        replies = board.generate_legal_captures(to_mask=chess.BB_SQUARES[move.to_square])
        return gain - max(0, max((exchange_value(board, reply) for reply in replies), default=0))
    finally:
        board.pop()


def obvious_material_win(board, uci):
    move = chess.Move.from_uci(uci)
    return (board.is_capture(move) or bool(move.promotion)) and exchange_value(board, move) >= 250


def hard_enough(board, shallow, check):
    if (not shallow or shallow['nodes_limit'] != SHALLOW_NODES or board.legal_moves.count() < 4
            or obvious_material_win(board, check['best_move'])):
        return False
    if shallow['best_move'] != check['best_move']:
        return True
    first, alternative = shallow['best'], shallow['runner_up']
    if first.get('mate', 0) > 0:
        return False
    return not ('cp' in first and 'cp' in alternative and first['cp'] - alternative['cp'] >= 140)


def random_move(board,rng):
    moves=sorted(board.legal_moves,key=lambda m:m.uci());weights=[]
    for move in moves:
        piece=board.piece_at(move.from_square);weight=1
        if board.fullmove_number<7:
            weight=3 if piece.piece_type in (chess.PAWN,chess.KNIGHT,chess.BISHOP) else .4
        if board.is_capture(move):weight*=2
        if board.gives_check(move):weight*=1.5
        weights.append(weight)
    return rng.choices(moves,weights=weights,k=1)[0]


def verify_candidate(engine_name,board,history,difficulty,quick):
    shallow = None
    if difficulty == 'schwer':
        shallow = yield board, SHALLOW_NODES
        if not hard_enough(board, shallow, quick):return None
    checks=[]
    for nodes in BUDGETS[difficulty]:
        check = yield board,nodes
        if not acceptable(check,difficulty):return None
        checks.append(check)
    if checks[0]['best_move']!=checks[1]['best_move']:return None
    mate=checks[-1]['best'].get('mate')
    if mate is not None and checks[0]['best'].get('mate')!=mate:return None
    if mate is None and any('cp' not in c['best'] for c in checks):return None
    best=checks[-1]['best_move'];proof_nodes=0
    if difficulty == 'schwer' and not hard_enough(board, shallow, checks[-1]):return None
    if mate is not None:
        try:proof_nodes=verify_unique_mate(board.fen(),mate,best)
        except (MateProofBudget,ValueError):return None
    return dict(fen=board.fen(),best_move=best,kind='mate' if mate is not None else 'best',mate=mate,
                pv=checks[-1]['pv'],engine_checks=checks,difficulty_probe=shallow,exact_mate_proof_nodes=proof_nodes,
                engine=engine_name,playout=history.copy(),origin='generated_legal_playout')


def search_record(seed,difficulty,engine_name):
    """Yield requested UCI analyses so native and browser engines share the search."""
    hard = difficulty == 'schwer'
    rng = random.Random((seed << 1) | hard)
    prefer_mate = rng.randrange(4) == 0
    fallback = None
    started = time.monotonic()
    checked = 0

    def finish(record):
        record.update(difficulty=difficulty, generation_candidates=checked)
        record['id'] = 'generated-'+hashlib.sha256(record['fen'].encode()).hexdigest()[:16]
        record['digest'] = digest(record)
        return json.dumps(record, sort_keys=True)

    for _ in range(44 if hard else 24):
        board = chess.Board()
        history = []
        for ply in range(rng.randint(55, 90)):
            if fallback is not None and checked >= 60:
                return finish(fallback)
            if board.is_game_over() or time.monotonic()-started > 35:
                break
            if ply >= (20 if hard else 10) and ply % 3 == seed % 3 and board.legal_moves.count() >= (4 if hard else 2):
                quick = yield board, 6000
                checked += 1
                if (acceptable(quick, difficulty, quick=True)
                        and (fallback is None or 'mate' in quick['best'])
                        and (not hard or not obvious_material_win(board, quick['best_move']))):
                    record = yield from verify_candidate(engine_name, board, history, difficulty, quick)
                    if record is not None:
                        if not prefer_mate or record['kind'] == 'mate':
                            return finish(record)
                        fallback = record
            move = random_move(board, rng)
            history.append(move.uci())
            board.push(move)
        if time.monotonic()-started > 35:
            break
    if fallback is not None:
        return finish(fallback)
    raise ValueError('Keine ausreichend eindeutige neue Schachaufgabe im Versuchslimit gefunden. Bitte mit einem neuen Seed versuchen.')


@lru_cache(maxsize=128)
def generated_record_json(seed,difficulty,path):
    try:
        with open_engine(path) as engine:
            search=search_record(seed,difficulty,engine.id.get('name','Stockfish'))
            response=None
            while True:
                try:
                    board,nodes=search.send(response)
                except StopIteration as result:
                    return result.value
                response=analysis(engine,board,nodes)
    except (OSError,chess.engine.EngineError) as exc:
        raise ValueError(f'Stockfish konnte die Schachaufgabe nicht erzeugen: {exc}') from exc


def generate_record(seed,difficulty):
    path=stockfish_path()
    if path is None:raise ValueError(stockfish_missing_message())
    return json.loads(generated_record_json(seed,difficulty,path))
