"""Killer cages, mines, Hakyuu regions and permutation equations."""
from itertools import combinations
import random

from .calendar_generators import connected
from .generators import cell, finish, first_solution, grid_domains, lines, reduce_givens, sudoku_model
from .new_calendar_generators import sum_patterns
from .solver import AllDifferent, Model, SearchLimit, Sum, Table, deduce, solve


def killer_model(cages, totals):
    model=sudoku_model()
    model.constraints += [Table(tuple(group),sum_patterns(len(group))[total]) for group,total in zip(cages,totals)]
    # The 45 rule: cages contained entirely in a house leave a known sum for
    # the other cells. This is derived solely from printed cages and Sudoku.
    for house in lines(9)+[tuple(cell(br+r,bc+c) for r in range(3) for c in range(3))
                           for br in range(0,9,3) for bc in range(0,9,3)]:
        inside=[i for i,g in enumerate(cages) if set(g)<=set(house)]
        covered={k for i in inside for k in cages[i]}
        remainder=tuple(k for k in house if k not in covered)
        if remainder:
            model.constraints.append(Sum(remainder,45-sum(totals[i] for i in inside)))
    return model


def killer_sudoku(seed,difficulty):
    rng=random.Random(seed)
    solution=first_solution(sudoku_model(),rng)
    cages=[[k] for k in solution]
    target=36 if difficulty=='mittel' else 30
    while len(cages)>target:
        owner={k:i for i,g in enumerate(cages) for k in g}
        pairs=set()
        for k in solution:
            r,c=map(int,k.split(','))
            for neighbor in (cell(r+1,c),cell(r,c+1)):
                if neighbor in owner and owner[k]!=owner[neighbor]:
                    pairs.add(tuple(sorted((owner[k],owner[neighbor]))))
        options=[]
        for i,j in sorted(pairs):
            group=cages[i]+cages[j]
            if len(group)<=5 and len({solution[k] for k in group})==len(group):
                options.append((int(len(cages[i])==1)+int(len(cages[j])==1)+rng.random(),i,j))
        options.sort(reverse=True)
        for _,i,j in options:
            candidate=[g for q,g in enumerate(cages) if q not in (i,j)]+[sorted(cages[i]+cages[j])]
            totals=[sum(solution[k] for k in g) for g in candidate]
            if deduce(killer_model(candidate,totals),trace=False).solved:
                cages=candidate;break
        else:
            break
    totals=[sum(solution[k] for k in g) for g in cages]
    return finish('killer-sudoku','Killer-Sudoku',
        'Jede Zeile, Spalte und jeder 3×3-Block enthält 1 bis 9 genau einmal. '
        'In jedem gestrichelt umrandeten Käfig ergibt die Summe aller Zahlen den kleinen Hinweis. '
        'Auch innerhalb eines Käfigs darf keine Zahl doppelt vorkommen.',
        killer_model(cages,totals),solution,{},dict(kind='grid',size=9,blocks=True,cell_size=57,entry_size=34,
            corner_labels={min(g):str(t) for g,t in zip(cages,totals)},
            cage_sums=[dict(cells=g,total=t) for g,t in zip(cages,totals)]),seed,difficulty)


def adjacent8(key,n):
    r,c=map(int,key.split(','))
    return tuple(cell(rr,cc) for rr in range(max(0,r-1),min(n,r+2))
                 for cc in range(max(0,c-1),min(n,c+2)) if (rr,cc)!=(r,c))


class CountSubsets:
    """Subtract overlapping binary count equations with known cells removed."""
    def __init__(self,groups):
        self.groups=tuple((tuple(keys),total) for keys,total in groups)
        self.keys=tuple(dict.fromkeys(k for keys,total in groups for k in keys))

    def reduce(self,domains):
        pending=[]
        for keys,total in self.groups:
            unknown=frozenset(k for k in keys if len(domains[k])>1)
            needed=total-sum(next(iter(domains[k])) for k in keys if len(domains[k])==1)
            Sum(tuple(unknown),needed).reduce(domains)
            pending.append((unknown,needed))
        for i,(a,na) in enumerate(pending):
            for b,nb in pending[i+1:]:
                if a<=b:
                    Sum(tuple(sorted(b-a)),nb-na).reduce(domains)
                elif b<=a:
                    Sum(tuple(sorted(a-b)),na-nb).reduce(domains)


def mine_model(n,clues,count):
    groups=[(adjacent8(key,n),total) for key,total in clues.items()]
    groups.append((tuple(grid_domains(n,())),count))
    return Model(grid_domains(n,(0,1)),[Sum(keys,total) for keys,total in groups]+[CountSubsets(groups)])


def minesweeper(seed,difficulty):
    rng=random.Random(seed)
    n,count=(7,10) if difficulty=='mittel' else (8,14)
    keys=list(grid_domains(n,()))
    mines=set(rng.sample(keys,count))
    solution={k:int(k in mines) for k in keys}
    clues={k:sum(solution[t] for t in adjacent8(k,n)) for k in keys if k not in mines}
    order=list(clues);rng.shuffle(order)
    target=16 if n==7 else 20
    for key in order:
        if len(clues)<=target:
            break
        candidate={k:v for k,v in clues.items() if k!=key}
        if deduce(mine_model(n,candidate,count),{k:0 for k in candidate},trace=False).solved:
            clues=candidate
    return finish('minesweeper','Minesweeper',
        f'Finde alle {count} Minen allein aus den sichtbaren Hinweisen. Jede Zahl zählt Minen '
        'in ihren acht unmittelbar benachbarten Feldern. Zahlenfelder enthalten keine Mine. '
        'Klicken setzt oder entfernt eine Flagge; Notizen streicht sichere Felder durch. '
        'Es gibt kein zufälliges Aufdecken. Sobald alle Minen markiert sind, wird geprüft.',
        mine_model(n,clues,count),solution,{k:0 for k in clues},
        dict(kind='mines',size=n,labels=clues,mine_count=count),seed,difficulty)


def ripple_model(regions):
    domains={k:set(range(1,len(g)+1)) for g in regions for k in g}
    constraints=[AllDifferent(tuple(g)) for g in regions]
    for axis in (0,1):
        for fixed in range(7):
            for a,b in combinations(range(7),2):
                ka,kb=(cell(fixed,a),cell(fixed,b)) if axis==0 else (cell(a,fixed),cell(b,fixed))
                constraints.append(Table((ka,kb),tuple((x,y) for x in domains[ka] for y in domains[kb]
                    if x!=y or b-a>x)))
    return Model(domains,constraints)


def ripple_effect(seed,difficulty):
    rng=random.Random(seed)
    for _ in range(80):
        regions=[set(cell(r,c) for c in range(7)) for r in range(7)]
        for _ in range(220):
            owner={k:i for i,g in enumerate(regions) for k in g}
            key=rng.choice(sorted(owner));r,c=map(int,key.split(','));i=owner[key]
            adjacent=[owner[k] for k in (cell(r-1,c),cell(r+1,c),cell(r,c-1),cell(r,c+1)) if k in owner and owner[k]!=i]
            if not adjacent:
                continue
            j=rng.choice(adjacent)
            if len(regions[i])>5 and len(regions[j])<9 and connected(regions[i]-{key}):
                regions[i].remove(key);regions[j].add(key)
        regions=[sorted(g) for g in regions]
        model=ripple_model(regions)
        try:
            result=solve(model,limit=1,seconds=.8,rng=rng)
        except SearchLimit:
            continue
        if not result.solutions:
            continue
        solution=result.solutions[0]
        givens=reduce_givens(model,solution,rng,18 if difficulty=='mittel' else 12,budget=2)
        return finish('ripple-effect','Ripple Effect',
            'Jeder dick umrandete Bereich enthält die Zahlen von 1 bis zu seiner Feldanzahl '
            'jeweils genau einmal. Zwischen zwei gleichen Zahlen k in derselben Zeile oder '
            'Spalte müssen mindestens k andere Felder liegen. Das Feld hat 7×7 Kästchen.',
            model,solution,givens,dict(kind='grid',size=7,regions=regions),seed,difficulty)
    raise ValueError('Keine passende Ripple-Effect-Aufgabe gefunden')


def logic_equations(seed,difficulty):
    rng=random.Random(seed)
    keys=tuple('ABCDE')
    solution=dict(zip(keys,rng.sample(range(1,6),5)))
    options=[]
    for a,b in combinations(keys,2):
        lo,hi=(a,b) if solution[a]<solution[b] else (b,a)
        distance=solution[hi]-solution[lo]
        options.append((f'{hi} = {lo} + {distance}',Table((hi,lo),tuple((x,y) for x in range(1,6) for y in range(1,6) if x==y+distance))))
        options.append((f'{hi} > {lo}',Table((hi,lo),tuple((x,y) for x in range(1,6) for y in range(1,6) if x>y))))
        for c in keys:
            if c not in (a,b) and solution[a]+solution[b]==solution[c]:
                options.append((f'{a} + {b} = {c}',Table((a,b,c),tuple((x,y,x+y) for x in range(1,6) for y in range(1,6) if x!=y and x+y<=5))))
    rng.shuffle(options)
    chosen=options.copy()
    for candidate in options:
        trial=[o for o in chosen if o is not candidate]
        model=Model({k:set(range(1,6)) for k in keys},[AllDifferent(keys)]+[constraint for text,constraint in trial])
        if len(trial)>=3 and deduce(model,trace=False).solved:
            chosen=trial
    model=Model({k:set(range(1,6)) for k in keys},[AllDifferent(keys)]+[constraint for text,constraint in chosen])
    return finish('logic-equations','Logic Equations',
        'Ordne A bis E die Zahlen 1 bis 5 jeweils genau einmal zu. Alle Gleichungen und '
        'Ungleichungen müssen stimmen. Klicke pro Buchstaben die passende Spalte an. '
        'Die übrigen Felder dieser Zeile und Spalte werden automatisch durchgestrichen; '
        'erneutes Klicken entfernt deine Auswahl.', model,solution,{},
        dict(kind='matrix',size=5,equations=[text for text,constraint in chosen],row_labels=list(keys)),seed,difficulty)
