"""One non-touching cat per row, column and connected coloured region."""
import random
from collections import deque
from functools import lru_cache

from .extra_constraints import HallDifferent
from .generators import cell, finish
from .solver import Model, SearchLimit, Table, deduce, restrict, solve
from .calendar_generators import connected


class RegionPermutation:
    def __init__(self,keys,owner):
        self.keys=tuple(keys)
        self.owner=owner

    def reduce(self,domains):
        regions={key:{self.owner[cell(r,c-1)] for c in domains[key]} for r,key in enumerate(self.keys)}
        HallDifferent(self.keys).reduce(regions)
        for r,key in enumerate(self.keys):
            restrict(domains,key,{c for c in domains[key] if self.owner[cell(r,c-1)] in regions[key]})
        # The same region matching rule also applies to columns, not just rows.
        columns={c:{self.owner[cell(r,c-1)] for r,key in enumerate(self.keys) if c in domains[key]}
                 for c in range(1,len(self.keys)+1)}
        HallDifferent(tuple(columns)).reduce(columns)
        for r,key in enumerate(self.keys):
            restrict(domains,key,{c for c in domains[key] if self.owner[cell(r,c-1)] in columns[c]})


def cat_model(regions,n):
    keys=tuple(f'Reihe {r+1}' for r in range(n))
    owner={k:i for i,g in enumerate(regions) for k in g}
    constraints=[HallDifferent(keys),RegionPermutation(keys,owner)]
    for r in range(n):
        for rr in range(r+1,n):
            allowed=tuple((c+1,cc+1) for c in range(n) for cc in range(n)
                if c!=cc and (rr-r>1 or abs(c-cc)>1)
                and owner[cell(r,c)]!=owner[cell(rr,cc)])
            constraints.append(Table((keys[r],keys[rr]),allowed))
    return Model({k:set(range(1,n+1)) for k in keys},constraints)


def balanced_region_sizes(sizes):
    n=len(sizes)
    return (min(sizes)>=1 and max(sizes)<=2*n and sum(s<=2 for s in sizes)<=1
            and sum((n+1)//2<=s<=8*n//5 for s in sizes)>=(n+1)//2)


def grow_regions(n,positions,rng):
    regions=[{cell(r,c)} for r,c in enumerate(positions)]
    owner={k:i for i,g in enumerate(regions) for k in g}
    # A single tiny entry region is allowed; other starters grow with the board.
    singletons=int(n>=6)
    small=rng.sample(range(n),singletons+max(0,n-6))
    limits={i:1 if j<singletons else rng.choice((max(3,n//2),max(4,n//2+1)))
            for j,i in enumerate(small)}
    for i,cap in limits.items():
        if cap==1:continue
        r,c=i,positions[i]
        strips=[]
        for dr,dc in ((0,1),(1,0)):
            for offset in range(cap):
                coords=[(r+(t-offset)*dr,c+(t-offset)*dc) for t in range(cap)]
                strip={cell(rr,cc) for rr,cc in coords}
                if all(0<=rr<n and 0<=cc<n for rr,cc in coords) and all(k not in owner or owner[k]==i for k in strip):
                    strips.append(strip)
        if not strips:return None
        regions[i]=rng.choice(strips)
        owner.update((k,i) for k in regions[i])
    weights=[rng.uniform(.8,1.2) if i not in limits else 0 for i in range(n)]
    remaining=n*n-sum(limits.values())
    targets=[remaining*w/sum(weights) if w else limits[i] for i,w in enumerate(weights)]
    while len(owner)<n*n:
        options=[];priorities=[]
        for i,g in enumerate(regions):
            if len(g)>=limits.get(i,2*n):
                continue
            frontier={cell(rr,cc) for k in g for r,c in [map(int,k.split(','))]
                for rr,cc in ((r-1,c),(r+1,c),(r,c-1),(r,c+1))
                if 0<=rr<n and 0<=cc<n and cell(rr,cc) not in owner}
            if frontier:
                options.append((i,sorted(frontier)))
                priorities.append(max(.1,targets[i]-len(g))**2)
        if not options:
            return None
        # Pick a region by its deficit, rather than favouring long frontiers.
        i,frontier=rng.choices(options,weights=priorities)[0]
        key=rng.choice(frontier)
        regions[i].add(key);owner[key]=i
    return [sorted(g) for g in regions]


def refine_regions(regions,positions,rng,steps=24):
    """Reshape colours, never add cats or hidden rules, to remove ambiguities.

    Alternate placements guide board construction only. Every returned board
    must still have a complete deduction proof from its visible regions.
    """
    n=len(regions)
    actual={cell(r,c) for r,c in enumerate(positions)}
    solution={f'Reihe {r+1}':c+1 for r,c in enumerate(positions)}
    seen=set();past_alternatives=[]
    for _ in range(steps):
        model=cat_model(regions,n)
        proof=deduce(model,trace=False)
        if proof.solved:return regions
        signature=tuple(tuple(sorted(g)) for g in regions)
        seen.add(signature)
        try:answers=solve(model,limit=3,seconds=.12,rng=rng).solutions
        except SearchLimit:return None
        alternatives=[s for s in answers if s!=solution]
        if not alternatives:return None
        past_alternatives.extend(alternatives)
        alternative=rng.choice(alternatives)
        other_cats={cell(r,alternative[f'Reihe {r+1}']-1) for r in range(n)}
        owner={k:i for i,g in enumerate(regions) for k in g}
        groups=[set(g) for g in regions]
        def neighbors(key):
            r,c=map(int,key.split(','))
            return {k for k in (cell(r-1,c),cell(r+1,c),cell(r,c-1),cell(r,c+1)) if k in owner}
        options=[]
        for key in sorted(other_cats-actual):
            i=owner[key]
            for j in sorted({owner[k] for k in neighbors(key)}-{i}):
                if len(groups[i])>2 and connected(groups[i]-{key}):
                    a,b=groups[i]-{key},groups[j]|{key}
                    options.append((i,j,a,b))
                for replacement in sorted(groups[j]-actual-other_cats):
                    if not any(owner[k]==i for k in neighbors(replacement)):continue
                    a,b=groups[i]-{key}|{replacement},groups[j]-{replacement}|{key}
                    if connected(a) and connected(b):options.append((i,j,a,b))
            # An alternate cat can lie inside a larger region. Move a short
            # connected boundary patch to reach it without splitting a colour.
            todo=deque([(key,)]);visited={key}
            while todo:
                path=todo.popleft();patch=set(path)
                for neighbor in sorted(neighbors(path[-1])):
                    j=owner[neighbor]
                    if j!=i:
                        a,b=groups[i]-patch,groups[j]|patch
                        if a and connected(a):options.append((i,j,a,b))
                    elif neighbor not in visited and neighbor not in actual and len(path)<4:
                        visited.add(neighbor);todo.append(path+(neighbor,))
        rng.shuffle(options)
        best=None
        candidates=[]
        for i,j,a,b in options:
            candidate=[sorted(a) if q==i else sorted(b) if q==j else sorted(g) for q,g in enumerate(groups)]
            if tuple(tuple(g) for g in candidate) in seen:continue
            if not balanced_region_sizes(list(map(len,candidate))):continue
            candidates.append(candidate)
            if len(candidates)>=12:break
        for candidate in candidates:
            result=deduce(cat_model(candidate,n),trace=False)
            if result.solved:return candidate
            candidate_owner={k:i for i,g in enumerate(candidate) for k in g}
            remaining=sum(len({candidate_owner[cell(r,s[f'Reihe {r+1}']-1)] for r in range(n)})==n
                          for s in past_alternatives)
            score=(remaining,sum(len(v)-1 for v in result.domains.values()),
                   sum((len(g)-n)**2 for g in candidate))
            if best is None or score<best[0]:best=score,candidate
        if best is None:return None
        regions=best[1]
    return None


@lru_cache(maxsize=32)
def cat_layout(seed,size):
    """Cache immutable construction data; every game still gets a fresh model."""
    rng=random.Random(seed)
    for _ in range(400):
        positions=rng.sample(range(size),size)
        while any(abs(a-b)<=1 for a,b in zip(positions,positions[1:])):
            positions=rng.sample(range(size),size)
        regions=grow_regions(size,positions,rng)
        if regions is None or not balanced_region_sizes(list(map(len,regions))):
            continue
        model=cat_model(regions,size)
        if not deduce(model,trace=False).solved:
            if size<6:continue
            regions=refine_regions(regions,positions,rng)
            if regions is None:continue
            model=cat_model(regions,size)
        return tuple(positions),tuple(tuple(g) for g in regions)
    raise ValueError('Keine eindeutig logisch lösbare Katzensuche in dieser Größe gefunden')


def cats(seed,difficulty,size=6):
    if type(size) is not int or not 4<=size<=10:
        raise ValueError('Die Katzengröße muss zwischen 4 und 10 liegen')
    positions,layout=cat_layout(seed,size)
    regions=[list(g) for g in layout]
    model=cat_model(regions,size)
    solution={f'Reihe {r+1}':c+1 for r,c in enumerate(positions)}
    return finish('katzensuche','Katzensuche',
        'Setze genau eine Katze in jede Zeile, jede Spalte und jeden farbigen Bereich. '
        'Katzen dürfen sich auch diagonal nicht berühren. Klicken setzt oder entfernt eine Katze. '
        'Die übrigen Felder ihrer Zeile, Spalte und ihres Farbbereichs sowie alle angrenzenden Felder werden automatisch durchgestrichen. '
        'Im Notizmodus kannst du weitere Felder manuell ausschließen.',
        model,solution,{},dict(kind='cats',size=size,regions=regions),seed,difficulty)
