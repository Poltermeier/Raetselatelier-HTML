"""Exhaustive numbered-to-plate paths with an exact cover of the board."""
from collections import defaultdict
import random

from .extra_constraints import RectangleCover
from .generators import cell
from .puzzle import Puzzle
from .route_generators import grid_edges,hamiltonian
from .solver import Model,SearchLimit,deduce,restrict


def candidate_paths(start,length,labels,plates,n,limit=18000):
    neighbors={cell(r,c):tuple(cell(rr,cc) for rr,cc in ((r-1,c),(r+1,c),(r,c-1),(r,c+1))
                 if 0<=rr<n and 0<=cc<n) for r in range(n) for c in range(n)}
    result=[]
    def extend(path,visited):
        node=path[-1]
        if node in plates:
            if len(path)==length:
                result.append(path)
                if len(result)>limit:raise SearchLimit('Zu viele vollständige Kontakt-Wege')
            return
        if len(path)>=length:return
        r,c=map(int,node.split(','));remaining=length-len(path)
        if not any(abs(r-int(k.split(',')[0]))+abs(c-int(k.split(',')[1]))<=remaining
                   and (remaining-abs(r-int(k.split(',')[0]))-abs(c-int(k.split(',')[1])))%2==0
                   for k in plates-visited):return
        for other in neighbors[node]:
            if other not in visited and other not in labels:
                extend(path+(other,),visited|{other})
    extend((start,),{start})
    return tuple(result)


class PathCover(RectangleCover):
    """Reuse the one-owner-per-cell deductions for arbitrary simple paths."""
    def __init__(self,candidates,n):
        self.keys=tuple(candidates)
        self.covered={k:tuple(frozenset(path) for path in paths) for k,paths in candidates.items()}
        self.cells=tuple(cell(r,c) for r in range(n) for c in range(n))


class PathEdgeLinks:
    def __init__(self,candidates,edges):
        self.paths={k:tuple(frozenset(tuple(sorted(pair)) for pair in zip(path,path[1:])) for path in paths)
                    for k,paths in candidates.items()}
        self.edges=tuple(edges)
        self.keys=tuple(candidates)+tuple(k for k,a,b in edges)

    def reduce(self,domains):
        for edge,a,b in self.edges:
            pair=tuple(sorted((a,b)))
            owners={k:{i for i in domains[k] if pair in self.paths[k][i]} for k in self.paths}
            owners={k:values for k,values in owners.items() if values}
            if not owners:
                restrict(domains,edge,{0});continue
            if any(values==domains[k] for k,values in owners.items()):restrict(domains,edge,{1})
            if domains[edge]=={0}:
                for k,values in owners.items():restrict(domains,k,domains[k]-values)
            elif domains[edge]=={1} and len(owners)==1:
                k=next(iter(owners));restrict(domains,k,owners[k])


class ContactPuzzle(Puzzle):
    @property
    def editable(self):return [k for k in self.model.domains if k.startswith('E')]

    def check(self,entries):
        if any(k not in self.model.domains or type(value) is not int or value not in self.model.domains[k]
               for k,value in entries.items()):return 'invalid',[]
        if any(k not in entries for k in self.editable):return 'incomplete',[]
        graph=defaultdict(set)
        for k,a,b in self.view['edges']:
            if entries[k]:graph[a].add(b);graph[b].add(a)
        values=entries.copy()
        for start,paths in self.view['candidates'].items():
            path=[start];previous=None;current=start
            while True:
                following=graph[current]-({previous} if previous is not None else set())
                if len(following)!=1:break
                target=next(iter(following))
                if target in path:break
                path.append(target);previous,current=current,target
                if current in self.view['plates']:break
            try:index=paths.index(tuple(path))
            except ValueError:return 'wrong',[k for k in self.editable if entries[k]!=self.solution[k]]
            if start in values and values[start]!=index:return 'invalid',[]
            values[start]=index
        return super().check(values)


def contact(seed,difficulty):
    rng=random.Random(seed);n=5 if difficulty=='mittel' else 6
    count=4 if n==5 else 6
    edges=grid_edges(n,n)
    for _ in range(240):
        path=hamiltonian(n,n,rng)
        lengths=[3]*count
        for _ in range(n*n-3*count):lengths[rng.randrange(count)]+=1
        if max(lengths)>11:continue
        groups=[];offset=0
        for length in lengths:
            group=tuple(path[offset:offset+length]);offset+=length
            if rng.randrange(2):group=group[::-1]
            groups.append(group)
        labels={group[0]:len(group) for group in groups};plates={group[-1] for group in groups}
        try:candidates={start:candidate_paths(start,length,labels,plates,n) for start,length in labels.items()}
        except SearchLimit:continue
        if not all(candidates.values()):continue
        domains={k:set(range(len(paths))) for k,paths in candidates.items()}|{k:{0,1} for k,a,b in edges}
        model=Model(domains,[PathCover(candidates,n),PathEdgeLinks(candidates,edges)])
        if not deduce(model,trace=False).solved:continue
        chosen={tuple(sorted(pair)) for group in groups for pair in zip(group,group[1:])}
        solution={group[0]:candidates[group[0]].index(group) for group in groups}
        solution.update((k,int(tuple(sorted((a,b))) in chosen)) for k,a,b in edges)
        p=ContactPuzzle('kontakt','Kontakt',
            'Verbinde jede Zahl durch waagerechte und senkrechte Linien mit genau einem blauen Teller. '
            'Die Zahl nennt die Anzahl der vom Weg besuchten Felder, einschließlich Zahlenfeld und Teller. '
            'Jeder Teller wird genau einmal erreicht. Alle Felder werden benutzt; Wege dürfen sich weder '
            'kreuzen noch verzweigen. Klicke oder ziehe zwischen benachbarten Feldern. Notizen streicht eine Verbindung durch.',
            model,solution,{},dict(kind='routes',mode='contact',rows=n,cols=n,edges=edges,labels=labels,
                                  plates=sorted(plates),candidates=candidates),seed,difficulty)
        p.certify();return p
    raise ValueError('Kein eindeutig logisch lösbares Kontakt gefunden')
