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
from .chess_validation import MateProofBudget,verify_unique_mate

BUDGETS={'mittel':(35000,100000),'schwer':(60000,180000)}


def digest(record):
    return hashlib.sha256(json.dumps({k:v for k,v in record.items() if k!='digest'},sort_keys=True,separators=(',',':')).encode()).hexdigest()


def open_engine(path):
    kwargs={'creationflags':subprocess.CREATE_NO_WINDOW} if os.name=='nt' else {}
    engine=chess.engine.SimpleEngine.popen_uci(path,timeout=15,**kwargs)
    engine.configure({'Threads':1,'Hash':32})
    return engine


def analysis(engine,board,nodes):
    if 'Clear Hash' in engine.options:engine.configure({'Clear Hash':None})
    rows=engine.analyse(board.copy(stack=False),chess.engine.Limit(nodes=nodes),multipv=2)
    if len(rows)<2:return None
    def score(row):
        value=row['score'].pov(board.turn)
        return {'mate':value.mate()} if value.is_mate() else {'cp':value.score()}
    return dict(nodes_limit=nodes,depth=min(row.get('depth',0) for row in rows),
                best_move=rows[0]['pv'][0].uci(),runner_up_move=rows[1]['pv'][0].uci(),
                best=score(rows[0]),runner_up=score(rows[1]),pv=[m.uci() for m in rows[0]['pv'][:12]])


def acceptable(check,difficulty,*,quick=False):
    if check is None:return False
    best,runner=check['best'],check['runner_up']
    if 'mate' in best:
        mate=best['mate'];other=runner.get('mate')
        return mate is not None and (mate==2 if difficulty=='schwer' else 1<=mate<=2) and (other is None or other<=0 or other>mate)
    return ('cp' in runner and runner['cp']<=(250 if quick else 200) and best['cp']>=-150 and best['cp']<=1800
            and best['cp']-runner['cp']>=(170 if quick else 200))


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


def verify_candidate(engine_name,board,history,difficulty):
    checks=[]
    for nodes in BUDGETS[difficulty]:
        checks.append((yield board,nodes))
    if not all(acceptable(check,difficulty) for check in checks):return None
    if checks[0]['best_move']!=checks[1]['best_move']:return None
    mate=checks[-1]['best'].get('mate')
    if mate is not None and checks[0]['best'].get('mate')!=mate:return None
    if mate is None and any('cp' not in c['best'] for c in checks):return None
    best=checks[-1]['best_move'];proof_nodes=0
    if difficulty=='schwer' and mate is None:
        move=chess.Move.from_uci(best);captured=board.piece_at(move.to_square)
        if captured is not None and captured.piece_type not in (chess.PAWN,chess.KING) and not board.gives_check(move):
            after=board.copy();after.push(move)
            if not after.is_attacked_by(after.turn,move.to_square):return None
    if mate is not None:
        try:proof_nodes=verify_unique_mate(board.fen(),mate,best)
        except (MateProofBudget,ValueError):return None
    return dict(fen=board.fen(),best_move=best,kind='mate' if mate is not None else 'best',mate=mate,
                pv=checks[-1]['pv'],engine_checks=checks,exact_mate_proof_nodes=proof_nodes,
                engine=engine_name,playout=history.copy(),origin='generated_legal_playout')


def search_record(seed,difficulty,engine_name):
    """Yield requested UCI analyses so native and browser engines share the search."""
    rng=random.Random((seed<<1)|(difficulty=='schwer'));prefer_mate=rng.randrange(4)==0;fallback=None;started=time.monotonic();checked=0
    for game in range(24):
        board=chess.Board();history=[]
        for ply in range(rng.randint(55,90)):
            if board.is_game_over():break
            if ply>=(10 if difficulty=='mittel' else 20) and ply%3==seed%3 and len(list(board.legal_moves))>=2:
                quick=(yield board,6000);checked+=1
                if acceptable(quick,difficulty,quick=True):
                    if prefer_mate and 'mate' not in quick['best']:
                        if fallback is None:fallback=(board.fen(),history.copy())
                    else:
                        record=yield from verify_candidate(engine_name,board,history,difficulty)
                        if record:
                            record.update(difficulty=difficulty,generation_candidates=checked)
                            record['id']='generated-'+hashlib.sha256(record['fen'].encode()).hexdigest()[:16]
                            record['digest']=digest(record);return json.dumps(record,sort_keys=True)
            move=random_move(board,rng);history.append(move.uci());board.push(move)
        if prefer_mate and fallback is not None and (game>=2 or time.monotonic()-started>12):
            fen,trace=fallback;record=yield from verify_candidate(engine_name,chess.Board(fen),trace,difficulty)
            if record:
                record.update(difficulty=difficulty,generation_candidates=checked)
                record['id']='generated-'+hashlib.sha256(record['fen'].encode()).hexdigest()[:16]
                record['digest']=digest(record);return json.dumps(record,sort_keys=True)
            fallback=None
        if time.monotonic()-started>35:break
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
