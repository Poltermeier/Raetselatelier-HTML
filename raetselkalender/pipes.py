"""Rotatable pipe forests: exact local joins and one connected net per colour."""
from itertools import product
import random

from .generators import cell
from .puzzle import Puzzle
from .solver import Contradiction,Model,Table,deduce,restrict

PIPE_SIZES=(4,5,7,10,12,15,20)
PIPE_COLORS=('#2166ac','#bc412e','#52842a','#8449a1')
STEPS=((-1,0,1,4),(0,1,2,8),(1,0,4,1),(0,-1,8,2))


def rotate_pipe(mask):return ((mask<<1)&15)|(mask>>3)


def pipe_orientations(mask):
    result={mask}
    for _ in range(3):mask=rotate_pipe(mask);result.add(mask)
    return result


def pipe_neighbors(key,n):
    r,c=map(int,key.split(','))
    return tuple((cell(r+dr,c+dc),bit,reverse) for dr,dc,bit,reverse in STEPS if 0<=r+dr<n and 0<=c+dc<n)


class PipeNetwork:
    def __init__(self,keys,n):
        self.keys=tuple(sorted(keys));own=set(keys)
        self.neighbors={k:tuple((other,bit,rev) for other,bit,rev in pipe_neighbors(k,n) if other in own) for k in self.keys}

    def reduce(self,domains):
        graph={k:[] for k in self.keys}
        for k,neighbors in self.neighbors.items():
            for other,bit,rev in neighbors:
                if any(mask&bit for mask in domains[k]) and any(mask&rev for mask in domains[other]):graph[k].append((other,bit,rev))
        order={};low={};bridges=[]
        def visit(k,parent=None):
            order[k]=low[k]=len(order)
            for other,bit,rev in graph[k]:
                if other==parent:continue
                if other in order:low[k]=min(low[k],order[other])
                else:
                    visit(other,k);low[k]=min(low[k],low[other])
                    if low[other]>order[k]:bridges.append((k,other,bit,rev))
        visit(self.keys[0])
        if len(order)!=len(self.keys):raise Contradiction
        for a,b,bit,rev in bridges:
            restrict(domains,a,{mask for mask in domains[a] if mask&bit})
            restrict(domains,b,{mask for mask in domains[b] if mask&rev})


def pipe_model(shapes,colors,n):
    domains={k:pipe_orientations(mask) for k,mask in shapes.items()};constraints=[]
    for k in domains:
        r,c=map(int,k.split(','));closed=0
        for dr,dc,bit,rev in STEPS:
            other=cell(r+dr,c+dc)
            if other not in colors or colors[other]!=colors[k]:closed|=bit
        constraints.append(Table((k,),tuple((mask,) for mask in sorted(domains[k]) if not mask&closed)))
        for other,bit,rev in pipe_neighbors(k,n):
            if k<other and colors[k]==colors[other]:
                rows=tuple((a,b) for a,b in product(sorted(domains[k]),sorted(domains[other])) if bool(a&bit)==bool(b&rev))
                constraints.append(Table((k,other),rows))
    constraints.extend(PipeNetwork([k for k in domains if colors[k]==color],n) for color in sorted(set(colors.values())))
    return Model(domains,constraints)


def valid_pipe_board(values,colors,n):
    if set(values)!=set(colors) or any(type(mask) is not int or not 1<=mask<=15 for mask in values.values()):return False
    for k,mask in values.items():
        r,c=map(int,k.split(','))
        for dr,dc,bit,rev in STEPS:
            other=cell(r+dr,c+dc)
            if mask&bit and (other not in values or colors[k]!=colors[other] or not values[other]&rev):return False
    for color in set(colors.values()):
        group={k for k in colors if colors[k]==color};seen={min(group)};todo=list(seen)
        while todo:
            k=todo.pop()
            for other,bit,rev in pipe_neighbors(k,n):
                if values[k]&bit and other not in seen:seen.add(other);todo.append(other)
        if seen!=group:return False
    return True


def colored_regions(n,count,rng):
    cells=[cell(r,c) for r in range(n) for c in range(n)]
    for _ in range(100):
        seeds=rng.sample(cells,count);colors={key:i for i,key in enumerate(seeds)}
        front=[(key,other) for key in seeds for other,bit,rev in pipe_neighbors(key,n)]
        while front:
            index=rng.randrange(len(front));key,other=front[index];front[index]=front[-1];front.pop()
            if other in colors:continue
            colors[other]=colors[key]
            front.extend((other,target) for target,bit,rev in pipe_neighbors(other,n) if target not in colors)
        sizes=[sum(value==i for value in colors.values()) for i in range(count)]
        if min(sizes)>=2 and max(sizes)<=max(n*n*.72,n*n/count+2):return {k:colors[k] for k in cells}
    # A connected strip partition is a bounded fallback, never an invalid net.
    return {cell(r,c):min(count-1,c*count//n) for r in range(n) for c in range(n)}


def pipes(seed,difficulty,*,size=None):
    n=5 if size is None else size
    if type(n) is not int or n not in PIPE_SIZES:raise ValueError('Pipes: Feldgröße 4, 5, 7, 10, 12, 15 oder 20 wählen')
    rng=random.Random(seed);count=1 if difficulty=='mittel' else (2 if n<=5 else 3 if n<=10 else 4)
    for attempt in range(30):
        colors=colored_regions(n,count,rng);keys=list(colors);parent={k:k for k in keys};solution=dict.fromkeys(keys,0)
        def root(k):
            while parent[k]!=k:parent[k]=parent[parent[k]];k=parent[k]
            return k
        edges=[(k,other,bit,rev) for k in keys for other,bit,rev in pipe_neighbors(k,n) if k<other and colors[k]==colors[other]]
        rng.shuffle(edges)
        for a,b,bit,rev in edges:
            ra,rb=root(a),root(b)
            if ra==rb:continue
            parent[ra]=rb;solution[a]|=bit;solution[b]|=rev
        model=pipe_model(solution,colors,n);givens={};limit=max(2,n*n//(10 if attempt<20 else 5))
        for _ in range(limit+1):
            result=deduce(model,givens,trace=False)
            if result.solved:break
            unknown=[k for k,values in result.domains.items() if len(values)>1 and k not in givens]
            if not unknown:break
            key=rng.choice(unknown);givens[key]=solution[key]
        if not result.solved:continue
        initial={k:givens[k] if k in givens else rng.choice(sorted(model.domains[k])) for k in keys}
        if initial==solution:
            key=next(k for k in keys if k not in givens and len(model.domains[k])>1)
            initial[key]=next(mask for mask in model.domains[key] if mask!=solution[key])
        p=Puzzle('pipes','Pipes',
            'Drehe die Rohrteile durch Anklicken um 90° nach rechts; ein Rechtsklick dreht nach links. '
            'Alle Anschlüsse müssen passend verbunden sein, auch am Rand darf kein Ende offen bleiben. '
            +('Alle Rohre bilden ein einziges zusammenhängendes Netz.' if count==1 else
              'Nur gleiche Farben dürfen verbunden werden. Jede Farbe bildet ein eigenes zusammenhängendes Netz.')+
            ' Kleine Schlossmarkierungen kennzeichnen fest vorgegebene Teile. Rückgängig nimmt eine Drehung zurück.',
            model,solution,givens,dict(kind='activity',mode='pipes',size=n,colors=colors,palette=list(PIPE_COLORS[:count]),initial=initial),seed,difficulty)
        if not valid_pipe_board(solution,colors,n):raise ValueError('Ungültiger Rohrplan')
        p.certify();p.analysis.update(rules_verified=True,model_role='accepted_answers');return p
    raise ValueError('Kein eindeutig logisch lösbares Rohrnetz gefunden')
