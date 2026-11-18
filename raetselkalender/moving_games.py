"""Constructively reachable peg goals and shortest-path certified Water Sort."""
from collections import deque
from functools import lru_cache
import random

from .card_code_matches import validate_entries
from .pouring import transfer_amount
from .puzzle import Puzzle
from .solver import Model,SearchLimit,Table


PEG_CELLS=tuple((r,c) for r in range(7) for c in range(7) if 2<=r<=4 or 2<=c<=4)
PEG_INDEX={point:i for i,point in enumerate(PEG_CELLS)}
PEG_HOPS=tuple((i,PEG_INDEX[r+dr,c+dc],PEG_INDEX[r+2*dr,c+2*dc])
    for i,(r,c) in enumerate(PEG_CELLS) for dr,dc in ((1,0),(-1,0),(0,1),(0,-1))
    if (r+dr,c+dc) in PEG_INDEX and (r+2*dr,c+2*dc) in PEG_INDEX)


def peg_move(board,action):
    if type(action) is not int or not 0<=action<len(PEG_HOPS):return None
    a,b,c=PEG_HOPS[action];source,over,target=1<<a,1<<b,1<<c
    return board^(source|over|target) if board&source and board&over and not board&target else None


class SolitairePuzzle(Puzzle):
    def check_moves(self,moves):
        board=self.view['initial'];states=[board]
        for action in moves:
            board=peg_move(board,action)
            if board is None:return 'invalid',states
            states.append(board)
        return ('correct' if board==self.view['target'] else 'wrong'),states

    def score(self,board):
        if type(board) is not int or not 0<=board<1<<len(PEG_CELLS):raise ValueError('Ungültige Steinposition')
        initial_distance=(self.view['initial']^self.view['target']).bit_count()
        distance=(board^self.view['target']).bit_count()
        return max(0,round(100*(1-distance/max(1,initial_distance))))

    def check(self,entries):
        pending=validate_entries(self,entries)
        if pending:return pending,[]
        state,_=self.check_moves([entries[k] for k in self.editable])
        return ('correct',[]) if state=='correct' else ('wrong',self.editable)

    def certify(self):
        moves=tuple(self.solution[k] for k in self.editable)
        if self.check_moves(moves)[0]!='correct':raise ValueError('Solitär-Ziel nicht erreichbar')
        bound=self.view['initial'].bit_count()-self.view['target'].bit_count()
        if len(moves)!=bound or bound<=0:raise ValueError('Solitär-Sprungzahl stimmt nicht')
        if self.model.constraints[0].rows!=(moves,):raise ValueError('Ungültiger Solitär-Lösungsweg')
        self.analysis.update(unique=False,logical_solvable=False,rules_verified=True,optimality_verified=True,
            minimum_moves=bound,solution_method='peg_count_bound_with_legal_witness',model_role='example_solution',search_branches=None)
        self.logical_steps=[dict(rule='peg_jump',source=PEG_HOPS[a][0],over=PEG_HOPS[a][1],target=PEG_HOPS[a][2]) for a in moves]


def solitaire(seed,difficulty):
    rng=random.Random(seed);depth=9 if difficulty=='mittel' else 15
    center=PEG_INDEX[3,3]
    for _ in range(120):
        target=1<<center
        if difficulty=='schwer':target|=1<<rng.choice([i for i,p in enumerate(PEG_CELLS) if i!=center and max(abs(p[0]-3),abs(p[1]-3))<=2])
        board=target;reverse=[]
        for _ in range(depth):
            options=[]
            for action,(a,b,c) in enumerate(PEG_HOPS):
                if not board&(1<<a) and not board&(1<<b) and board&(1<<c):
                    options.append((action,board^((1<<a)|(1<<b)|(1<<c))))
            if not options:break
            action,board=rng.choice(options);reverse.append(action)
        if len(reverse)!=depth:continue
        moves=tuple(reversed(reverse));keys=tuple(f'Sprung {i+1}' for i in range(depth))
        p=SolitairePuzzle('solitaer','Solitär',
            'Springe waagerecht oder senkrecht über einen benachbarten Stein in ein freies Loch. '
            'Der übersprungene Stein wird entfernt. Jeder einzelne Sprung zählt als ein Zug. '
            'Erreiche das rechts gezeigte Zielbild. Wähle zuerst einen Stein und dann sein Zielloch. '
            '„Fertig – Score“ bewertet, wie gut die aktuelle Stellung zum Zielbild passt. 100 Punkte gibt es nur für das genaue Ziel.',
            Model({k:set(range(len(PEG_HOPS))) for k in keys},[Table(keys,(moves,))]),dict(zip(keys,moves)),{},
            dict(kind='activity',mode='solitaire',initial=board,target=target,cells=[list(p) for p in PEG_CELLS]),seed,difficulty)
        p.certify();return p
    raise ValueError('Kein erreichbares Solitär-Ziel gefunden')


def sort_pour(state,source,target,capacity):
    count=len(state)
    if type(source) is not int or type(target) is not int or not 0<=source<count or not 0<=target<count or source==target:return None
    a,b=state[source],state[target]
    if not a or len(b)>=capacity or b and b[-1]!=a[-1]:return None
    color=a[-1];run=1
    while run<len(a) and a[-run-1]==color:run+=1
    amount=transfer_amount(run,capacity-len(b))
    result=list(state);result[source]=a[:-amount];result[target]=b+(color,)*amount
    return tuple(result)


def sorted_water(state,capacity):
    return all(not tube or len(tube)==capacity and len(set(tube))==1 for tube in state)


@lru_cache(maxsize=32)
def water_search(initial,capacity):
    """BFS modulo bottle permutations; keep labelled witnesses for replay."""
    def key(state):return tuple(sorted(state))
    first=key(initial);states={first:initial};parents={first:None};todo=deque([first])
    while todo:
        current=todo.popleft();state=states[current]
        if sorted_water(state,capacity):
            route=[]
            while parents[current] is not None:
                previous,action=parents[current];route.append(action);current=previous
            return tuple(reversed(route)),len(states)
        sources=set()
        for a,tube in enumerate(state):
            if not tube or tube in sources:continue
            sources.add(tube);targets=set()
            for b,other in enumerate(state):
                if a==b or other in targets:continue
                targets.add(other)
                following=sort_pour(state,a,b,capacity)
                if following is None:continue
                canonical=key(following)
                if canonical in states:continue
                if len(states)>=150000:raise SearchLimit('Water-Sort-BFS im Zustandslimit')
                states[canonical]=following;parents[canonical]=(current,(a,b));todo.append(canonical)
    raise ValueError('Nicht lösbares Water Sort')


class WaterSortPuzzle(Puzzle):
    def check_moves(self,moves):
        state=tuple(tuple(tube) for tube in self.view['initial']);states=[state]
        for action in moves:
            if not isinstance(action,(tuple,list)) or len(action)!=2:return 'invalid',states
            state=sort_pour(state,*action,self.view['capacity'])
            if state is None:return 'invalid',states
            states.append(state)
        return ('correct' if sorted_water(state,self.view['capacity']) else 'wrong'),states

    def check(self,entries):
        pending=validate_entries(self,entries)
        if pending:return pending,[]
        count=len(self.view['initial'])
        state,_=self.check_moves([divmod(entries[k],count) for k in self.editable])
        return ('correct',[]) if state=='correct' else ('wrong',self.editable)

    def certify(self):
        initial=tuple(tuple(tube) for tube in self.view['initial']);capacity=self.view['capacity']
        route,nodes=water_search(initial,capacity)
        count=len(initial);moves=[divmod(self.solution[k],count) for k in self.editable]
        if self.check_moves(moves)[0]!='correct' or len(moves)!=len(route):raise ValueError('Ungültiger Water-Sort-Nachweis')
        if self.model.constraints[0].rows!=(tuple(self.solution.values()),):raise ValueError('Ungültiges Umfüll-Prüfmodell')
        self.analysis.update(unique=False,logical_solvable=False,rules_verified=True,optimality_verified=True,
            minimum_moves=len(route),search_nodes=nodes,search_branches=None,solution_method='bottle_permutation_bfs',model_role='example_solution')
        self.logical_steps=[dict(rule='sort_pour',source=a,target=b) for a,b in moves]


def water_sort(seed,difficulty):
    rng=random.Random(seed);colors,capacity=(4,4) if difficulty=='mittel' else (5,4)
    low,high=(10,14) if difficulty=='mittel' else (14,19)
    count=colors+2
    for _ in range(180):
        units=[color for color in range(colors) for _ in range(capacity)]
        rng.shuffle(units)
        state=tuple(tuple(units[i*capacity:(i+1)*capacity]) for i in range(colors))+((),())
        if sorted_water(state,capacity):continue
        try:route,nodes=water_search(state,capacity)
        except SearchLimit:continue
        if not low<=len(route)<=high:continue
        keys=tuple(f'Zug {i+1}' for i in range(len(route)));encoded=tuple(a*count+b for a,b in route)
        p=WaterSortPuzzle('water-sort','Water Sort',
            'Sortiere die Flüssigkeiten, bis jede Farbe ein eigenes volles Gefäß füllt. Wähle zuerst die Quelle '
            'und dann das Ziel. Du darfst nur in ein leeres Gefäß oder auf dieselbe oberste Farbe gießen. '
            'Der zusammenhängende oberste Farbblock fließt, bis er aufgebraucht oder das Ziel voll ist. '
            'Jede korrekte vollständige Sortierung zählt; Rückgängig nimmt einen Umfüllvorgang zurück.',
            Model({k:{a*count+b for a in range(count) for b in range(count) if a!=b} for k in keys},[Table(keys,(encoded,))]),
            dict(zip(keys,encoded)),{},dict(kind='activity',mode='water-sort',initial=[list(t) for t in state],capacity=capacity,
                palette=['#2462c0','#e68b24','#a636a5','#459a35','#cf343b']),seed,difficulty)
        p.certify();return p
    raise ValueError('Kein passend lösbares Water Sort gefunden')
