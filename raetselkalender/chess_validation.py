"""Offline, bounded mate proofs built on python-chess legal move generation."""
import time
from functools import lru_cache
import chess


class MateProofBudget(RuntimeError):
    pass


def mating_first_moves(board,moves,*,node_limit=250000,seconds=12):
    """All moves forcing mate within N own moves, considering every defense.

    A budget overrun raises; it never certifies an incomplete search.
    This is used to prepare/audit the bundled catalog, not an idle GUI worker.
    """
    if type(moves) is not int or moves<0:
        raise ValueError('Die Mattlänge muss eine nichtnegative ganze Zahl sein')
    if moves==0:return [],0
    attacker=board.turn
    cache={}
    nodes=0
    deadline=time.monotonic()+seconds
    def wins(remaining):
        nonlocal nodes
        nodes+=1
        if nodes>node_limit or time.monotonic()>deadline:
            raise MateProofBudget('Zeit-/Knotenlimit für den Mattnachweis erreicht')
        if board.is_checkmate():
            return board.turn != attacker
        if remaining<=0 or board.is_stalemate() or board.is_insufficient_material() or board.is_fifty_moves():
            return False
        key=(board.fen(),remaining)
        if key in cache:
            return cache[key]
        attacking=board.turn==attacker
        legal=list(board.legal_moves)
        legal.sort(key=lambda m:(board.gives_check(m),board.is_capture(m)),reverse=attacking)
        result=not attacking
        for move in legal:
            board.push(move)
            try:following=wins(remaining-1)
            finally:board.pop()
            if following==attacking:
                result=attacking;break
        cache[key]=result
        return result
    winning=[]
    for move in list(board.legal_moves):
        board.push(move)
        try:forced=wins(2*moves-2)
        finally:board.pop()
        if forced:winning.append(move.uci())
    return sorted(winning),nodes


@lru_cache(maxsize=64)
def verify_unique_mate(fen,moves,best_move):
    board=chess.Board(fen)
    winning,nodes=mating_first_moves(board,moves)
    if winning!=[best_move]:
        raise ValueError('Mattaufgabe hat keinen eindeutigen ersten Zug')
    shorter,extra=mating_first_moves(board,moves-1)
    if shorter:
        raise ValueError('Das Matt ist schneller als die Aufgabenstellung')
    return nodes+extra
