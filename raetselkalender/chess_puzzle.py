"""Fresh reachable chess tasks generated and verified by a local Stockfish."""
from functools import lru_cache
import hashlib
from importlib.resources import files
import json

import chess

from .puzzle import Puzzle
from .solver import Model,Table
from .chess_validation import verify_unique_mate
from .chess_explanations import MOTIFS,generated_explanation
from .live_chess import generate_record,BUDGETS,acceptable

CHESS_TASKS=('mate','best')


def record_digest(record):
    return hashlib.sha256(json.dumps({k:v for k,v in record.items() if k!='digest'},sort_keys=True,separators=(',',':')).encode()).hexdigest()


@lru_cache(maxsize=1)
def chess_catalog():
    data=json.loads(files('raetselkalender').joinpath('data/chess_positions.json').read_text(encoding='utf-8'))
    if data['schema']!=1 or data['license']!='CC0-1.0':
        raise ValueError('Unbekanntes Schachkatalog-Format')
    for record in data['records']:
        if record_digest(record)!=record['digest']:
            raise ValueError('Beschädigter Schachkatalog')
        if record['id'] not in MOTIFS:raise ValueError('Zu dieser Schachstellung fehlt die Lösungserklärung')
    return tuple(data['records'])


def transform_move(uci,flip_colors=False,flip_files=False):
    move=chess.Move.from_uci(uci)
    def square(value):
        return value^(56 if flip_colors else 0)^(7 if flip_files else 0)
    return chess.Move(square(move.from_square),square(move.to_square),promotion=move.promotion).uci()


def transform_board(board,flip_colors=False,flip_files=False):
    board=board.copy(stack=False)
    if flip_colors:board=board.mirror()
    if flip_files:
        if board.castling_rights:
            raise ValueError('Dateispiegelung ist bei Rochaderechten nicht zulässig')
        board=board.transform(chess.flip_horizontal)
    return board


class ChessPuzzle(Puzzle):
    def solution_explanation(self):
        return generated_explanation(self)

    def check_move(self,uci):
        if uci=='':return 'incomplete'
        if type(uci) is not str:return 'invalid'
        try:move=chess.Move.from_uci(uci)
        except (ValueError,TypeError):return 'invalid'
        board=chess.Board(self.view['fen'])
        if move not in board.legal_moves:return 'invalid'
        return 'correct' if uci==self.best_move else 'wrong'

    def check(self,entries):
        if any(k not in self.model.domains or type(v) is not int or v not in self.model.domains[k] for k,v in entries.items()):
            return 'invalid',[]
        if 'Zug' not in entries:return 'incomplete',[]
        return ('correct',[]) if self.check_move(self.view['moves'][entries['Zug']])=='correct' else ('wrong',['Zug'])

    def certify(self):
        r=self.chess_record
        if record_digest(r)!=r['digest'] or json.dumps(r,sort_keys=True)!=self._verified_record:
            raise ValueError('Die Stellung stimmt nicht mit ihrem live erzeugten Prüfnachweis überein')
        board=chess.Board()
        for uci in r['playout']:
            move=chess.Move.from_uci(uci)
            if move not in board.legal_moves:raise ValueError('Die Stellung stammt nicht aus einer legalen Zugfolge')
            board.push(move)
        if board.fen()!=self.view['fen'] or board.fen()!=r['fen'] or not board.is_valid() or board.is_game_over():
            raise ValueError('Ungültige generierte Schachstellung')
        if r['origin']!='generated_legal_playout' or self.view['task']!=r['kind'] or self.view['mate_in']!=r['mate']:
            raise ValueError('Schachaufgabe passt nicht zur geprüften Stellung')
        if self.best_move!=r['best_move'] or self.view['moves']!=sorted(m.uci() for m in board.legal_moves):raise ValueError('Ungültige Schachzugliste')
        checks=r['engine_checks']
        if tuple(c['nodes_limit'] for c in checks)!=BUDGETS[self.difficulty]:raise ValueError('Unvollständige Engine-Prüfung')
        if not all(acceptable(c,self.difficulty) and c['best_move']==self.best_move and c['depth']>0 for c in checks):raise ValueError('Kein stabiler eindeutiger Bestzug')
        if r['kind']=='mate':
            if not all(c['best'].get('mate')==r['mate'] for c in checks):raise ValueError('Inkonsistente Mattlänge')
            if verify_unique_mate(r['fen'],r['mate'],r['best_move'])!=r['exact_mate_proof_nodes']:raise ValueError('Vollständiger Mattnachweis fehlt')
        variation=board.copy();self.logical_steps=[]
        for uci in self.principal_variation:
            move=chess.Move.from_uci(uci)
            if move not in variation.legal_moves:raise ValueError('Illegale Lösungsvariante')
            self.logical_steps.append(dict(rule='legal_chess_move',uci=uci,san=variation.san(move)));variation.push(move)
        if self.principal_variation!=r['pv'] or self.solution!={'Zug':self.view['moves'].index(self.best_move)}:raise ValueError('Ungültiges Zugmodell')
        if self.model.constraints[0].rows!=((self.solution['Zug'],),):raise ValueError('Ungültige Zugtabelle')
        self.analysis.update(unique=True,engine_verified=True,logical_solvable=False,exact_mate_verified=r['kind']=='mate',
            solution_method='generated_stockfish_analysis',verification_engine=r['engine'],
            verification_node_limits=list(BUDGETS[self.difficulty]),verification_depths=[c['depth'] for c in checks],
            position_origin='legal_playout',chess_candidates=r['generation_candidates'],search_nodes=None,search_branches=None,
            difficulty_note='Frisch erzeugte legale Stellung; zwei Stockfish-Prüfungen beim Erzeugen. Im ruhenden Spiel läuft keine Engine.')

    def export(self,include_solution=False):
        data=super().export(include_solution)
        if include_solution:
            data['verification']=self.chess_record
            data['best_move']=self.best_move
            data['principal_variation']=self.principal_variation
            data['explanation']=self.solution_explanation()
        return data


def chess_puzzle(seed,difficulty):
    return puzzle_from_record(seed,difficulty,generate_record(seed,difficulty))


def puzzle_from_record(seed,difficulty,record):
    board=chess.Board(record['fen']);best=record['best_move']
    moves=sorted(m.uci() for m in board.legal_moves);side='Weiß' if board.turn else 'Schwarz'
    objective=(f'Finde den einzigen ersten Zug, der Matt in höchstens {record["mate"]} '+('Zug' if record['mate']==1 else 'Zügen')+' erzwingt.'
               if record['kind']=='mate' else 'Finde den von Stockfish eindeutig bevorzugten besten Zug.')
    p=ChessPuzzle('schachraetsel','Schachrätsel',
        f'{side} ist am Zug. {objective} Wähle zuerst deine Figur und dann ihr Zielfeld. '
        'Es gelten die normalen Schachregeln. Bei einer Bauernumwandlung wählst du die neue Figur. '
        'Geprüft wird dein erster Zug; Rückgängig stellt die Ausgangsstellung wieder her.',
        Model({'Zug':set(range(len(moves)))},[Table(('Zug',),((moves.index(best),),))]),{'Zug':moves.index(best)}, {},
        dict(kind='chess',size=8,fen=board.fen(),moves=moves,task=record['kind'],mate_in=record['mate']),seed,difficulty)
    p.chess_record=record;p._verified_record=json.dumps(record,sort_keys=True)
    p.flip_colors=p.flip_files=False;p.best_move=best;p.principal_variation=record['pv'].copy()
    p.certify();return p
