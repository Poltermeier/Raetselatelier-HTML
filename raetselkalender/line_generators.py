"""Fully covering Masyu loops and straight four-direction light rays."""
from itertools import combinations,product
import random
import time

from .generators import cell,finish
from .contact import PathEdgeLinks
from .extra_constraints import RectangleCover
from .network_rules import RouteTopology
from .puzzle import Puzzle
from .route_generators import degree_table,grid_edges,incident_edges
from .solver import Contradiction,Model,deduce,restrict


def edge_pair(a,b):return tuple(sorted((a,b)))


def is_turn(node,pair,other):
    a,b=[other[node][edge] for edge in pair]
    r,c=map(int,a.split(','));rr,cc=map(int,b.split(','))
    return r!=rr and c!=cc


class CircleRule:
    def __init__(self,node,filled,incident,other):
        self.node,self.filled,self.incident,self.other=node,filled,incident,other
        self.nodes=(node,)+tuple(other[node].values())
        self.keys=tuple(sorted({edge for k in self.nodes for edge in incident[k]}))
        self.pairs={k:tuple((frozenset(pair),is_turn(k,pair,other)) for pair in combinations(incident[k],2)) for k in self.nodes}

    def reduce(self,domains):
        options={k:[(pair,turn) for pair,turn in self.pairs[k]
                    if all((1 if edge in pair else 0) in domains[edge] for edge in self.incident[k])]
                 for k in self.nodes}
        supports={edge:set() for edge in self.keys}
        valid=False
        for pair,turn in options[self.node]:
            if turn!=self.filled:continue
            a,b=[self.other[self.node][edge] for edge in sorted(pair)]
            for (pa,ta),(pb,tb) in product(options[a],options[b]):
                if self.filled and (ta or tb) or not self.filled and not (ta or tb):continue
                assigned={};consistent=True
                for node,selected in ((self.node,pair),(a,pa),(b,pb)):
                    for edge in self.incident[node]:
                        value=int(edge in selected)
                        if edge in assigned and assigned[edge]!=value:consistent=False;break
                        assigned[edge]=value
                    if not consistent:break
                if not consistent:continue
                valid=True
                for edge in self.keys:
                    supports[edge].update({assigned[edge]} if edge in assigned else domains[edge])
        if not valid:raise Contradiction
        for edge,values in supports.items():restrict(domains,edge,values)


def masyu_model(edges,black,white):
    incident=incident_edges(edges);other={node:{} for node in incident}
    for key,a,b in edges:other[a][key]=b;other[b][key]=a
    constraints=[degree_table(tuple(keys),(2,)) for keys in incident.values()]
    constraints.extend(CircleRule(node,True,incident,other) for node in sorted(black))
    constraints.extend(CircleRule(node,False,incident,other) for node in sorted(white))
    return Model({key:{0,1} for key,a,b in edges},constraints+[RouteTopology(edges)])


def covering_cycle(n,rng):
    """Join disjoint 2×2 cycles along a random coarse-grid spanning tree."""
    chosen=set();side=n//2
    for r in range(side):
        for c in range(side):
            corners=[cell(2*r,2*c),cell(2*r,2*c+1),cell(2*r+1,2*c+1),cell(2*r+1,2*c)]
            chosen.update(edge_pair(corners[i],corners[(i+1)%4]) for i in range(4))
    tree=grid_edges(side,side);rng.shuffle(tree);parent={cell(r,c):cell(r,c) for r in range(side) for c in range(side)}
    def root(node):
        while parent[node]!=node:node=parent[node]
        return node
    for key,a,b in tree:
        ra,rb=root(a),root(b)
        if ra==rb:continue
        parent[ra]=rb
        r,c=map(int,a.split(','));rr,cc=map(int,b.split(','))
        if r==rr:
            first=[cell(2*r,2*c+1),cell(2*r+1,2*c+1)]
            second=[cell(2*rr,2*cc),cell(2*rr+1,2*cc)]
        else:
            first=[cell(2*r+1,2*c),cell(2*r+1,2*c+1)]
            second=[cell(2*rr,2*cc),cell(2*rr,2*cc+1)]
        chosen.remove(edge_pair(*first));chosen.remove(edge_pair(*second))
        chosen.add(edge_pair(first[0],second[0]));chosen.add(edge_pair(first[1],second[1]))
    return chosen


def abknicker(seed,difficulty):
    rng=random.Random(seed);n=8;edges=grid_edges(n,n)
    for _ in range(200):
        chosen=covering_cycle(n,rng);graph={cell(r,c):[] for r in range(n) for c in range(n)}
        for a,b in chosen:graph[a].append(b);graph[b].append(a)
        turns={node:(graph[node][0].split(',')[0]!=graph[node][1].split(',')[0]
                     and graph[node][0].split(',')[1]!=graph[node][1].split(',')[1]) for node in graph}
        black={k for k in graph if turns[k] and all(not turns[v] for v in graph[k])}
        white={k for k in graph if not turns[k] and any(turns[v] for v in graph[k])}
        if len(black)<2 or len(white)<4:continue
        if not deduce(masyu_model(edges,black,white),trace=False).solved:continue
        deadline=time.monotonic()+.8
        target=max(10,round((len(black)+len(white))*(.7 if difficulty=='mittel' else .45)))
        order=[(k,True) for k in sorted(black)]+[(k,False) for k in sorted(white)];rng.shuffle(order)
        for node,filled in order:
            if len(black)+len(white)<=target or time.monotonic()>deadline:break
            group=black if filled else white
            if len(group)<=2:continue
            group.remove(node)
            if not deduce(masyu_model(edges,black,white),trace=False).solved:group.add(node)
        solution={key:int(edge_pair(a,b) in chosen) for key,a,b in edges}
        starts=[]
        for origin in sorted(black):
            for following in sorted(graph[origin]):
                path=[origin,following]
                while len(path)<5:
                    path.append(next(node for node in graph[path[-1]] if node!=path[-2]))
                starts.append(path)
        start_path=rng.choice(starts)
        start_edges={edge_pair(a,b) for a,b in zip(start_path,start_path[1:])}
        givens={key:1 for key,a,b in edges if edge_pair(a,b) in start_edges}
        return finish('abknicker','Abknicker',
            'Zeichne einen einzigen geschlossenen Rundweg durch die Feldmitten. Er benutzt jedes Feld genau einmal, '
            'ohne Kreuzung oder Verzweigung, und verläuft nur waagerecht oder senkrecht. '
            'An einem gefüllten blauen Kreis muss er um 90° abbiegen; direkt davor und dahinter muss er geradeaus laufen. '
            'An einem weißen Kreis muss er geradeaus laufen und mindestens in einem der beiden direkt benachbarten '
            'Wegfelder abbiegen. Die blaue Startlinie gehört fest zum Rundweg und wird weitergeführt. '
            'Klicken oder Ziehen zeichnet Verbindungen; Notizen streicht Kanten durch.',
            masyu_model(edges,black,white),solution,givens,dict(kind='routes',mode='abknicker',rows=n,cols=n,edges=edges,
                labels={},black_circles=sorted(black),white_circles=sorted(white),start_path=start_path),seed,difficulty)
    raise ValueError('Kein eindeutig logisch lösbarer Abknicker gefunden')


RAY_DIRECTIONS=((-1,0),(0,1),(1,0),(0,-1))


def ray_cells(origin,labels,n):
    r,c=map(int,origin.split(','));rays=[]
    for dr,dc in RAY_DIRECTIONS:
        ray=[];rr,cc=r+dr,c+dc
        while 0<=rr<n and 0<=cc<n and cell(rr,cc) not in labels:
            ray.append(cell(rr,cc));rr+=dr;cc+=dc
        rays.append(tuple(ray))
    return tuple(rays)


def ray_candidates(labels,n):
    patterns={};covered={};paths={}
    for origin,total in labels.items():
        rays=ray_cells(origin,labels,n);patterns[origin]=[];covered[origin]=[];paths[origin]=[]
        for lengths in product(*(range(len(ray)+1) for ray in rays)):
            if sum(lengths)!=total:continue
            used=set();edges=set()
            for ray,length in zip(rays,lengths):
                previous=origin
                for point in ray[:length]:
                    used.add(point);edges.add(edge_pair(previous,point));previous=point
            patterns[origin].append(lengths);covered[origin].append(frozenset(used));paths[origin].append(frozenset(edges))
        patterns[origin]=tuple(patterns[origin]);covered[origin]=tuple(covered[origin]);paths[origin]=tuple(paths[origin])
    return patterns,covered,paths


class RayCover(RectangleCover):
    def __init__(self,covered,free):
        self.keys=tuple(covered);self.covered=covered;self.cells=tuple(sorted(free))


class RayEdgeLinks(PathEdgeLinks):
    def __init__(self,paths,edges):
        self.paths=paths;self.edges=tuple(edges);self.keys=tuple(paths)+tuple(k for k,a,b in edges)


def ray_model(labels,n,edges):
    patterns,covered,paths=ray_candidates(labels,n)
    free={cell(r,c) for r in range(n) for c in range(n)}-set(labels)
    domains={k:set(range(len(options))) for k,options in patterns.items()}|{k:{0,1} for k,a,b in edges}
    return Model(domains,[RayCover(covered,free),RayEdgeLinks(paths,edges)]),patterns


class RayPuzzle(Puzzle):
    @property
    def editable(self):return [k for k in self.model.domains if k.startswith('E')]

    def check(self,entries):
        if any(k not in self.model.domains or type(v) is not int or v not in self.model.domains[k] for k,v in entries.items()):return 'invalid',[]
        if any(k not in entries for k in self.editable):return 'incomplete',[]
        v=self.view;values=entries.copy();lookup={edge_pair(a,b):k for k,a,b in v['edges']}
        for origin,patterns in v['patterns'].items():
            lengths=[]
            for ray in ray_cells(origin,v['labels'],v['rows']):
                previous=origin;length=0
                for point in ray:
                    if not entries[lookup[edge_pair(previous,point)]]:break
                    length+=1;previous=point
                lengths.append(length)
            try:index=patterns.index(tuple(lengths))
            except ValueError:return 'wrong',[k for k in self.editable if entries[k]!=self.solution[k]]
            if origin in values and values[origin]!=index:return 'invalid',[]
            values[origin]=index
        return super().check(values)


def star_partition(n,rng):
    free={cell(r,c) for r in range(n) for c in range(n)};stars={};ones=0
    def adjacent(point):
        r,c=map(int,point.split(','))
        return {cell(r+dr,c+dc) for dr,dc in RAY_DIRECTIONS}
    while free:
        found=False;points=sorted(free)
        for _ in range(160):
            origin=rng.choice(points);r,c=map(int,origin.split(','));rays=[]
            for dr,dc in RAY_DIRECTIONS:
                ray=[];rr,cc=r+dr,c+dc
                while cell(rr,cc) in free:
                    ray.append(cell(rr,cc));rr+=dr;cc+=dc
                rays.append(ray)
            lengths=tuple(rng.randrange(min(5,len(ray))+1) for ray in rays)
            total=sum(lengths)
            if not total or (total==1 and ones==2):continue
            used={point for ray,length in zip(rays,lengths) for point in ray[:length]}
            remaining=free-used-{origin}
            neighbors={point:adjacent(point)&remaining for point in remaining}
            if any(not group for group in neighbors.values()):continue
            # An isolated two-cell component necessarily becomes a 1-clue.
            pairs=sum(len(group)==1 and len(neighbors[next(iter(group))])==1 for group in neighbors.values())//2
            if pairs+ones+(total==1)>2:continue
            stars[origin]=lengths;free=remaining;ones+=total==1;found=True;break
        if not found:return None
    return stars


def light_rays(seed,difficulty):
    rng=random.Random(seed);n=8;edges=grid_edges(n,n)
    for _ in range(1800):
        stars=star_partition(n,rng)
        if stars is None or not 9<=len(stars)<=23:continue
        if max(map(sum,stars.values()))<6:continue
        if sum(bool(lengths[0]+lengths[2]) and bool(lengths[1]+lengths[3]) for lengths in stars.values())<2:continue
        labels={k:sum(stars[k]) for k in sorted(stars)}
        if sum(total==1 for total in labels.values())>2:continue
        model,patterns=ray_model(labels,n,edges)
        if not deduce(model,trace=False).solved:continue
        selected=set()
        for origin,lengths in stars.items():
            for ray,length in zip(ray_cells(origin,labels,n),lengths):
                previous=origin
                for point in ray[:length]:selected.add(edge_pair(previous,point));previous=point
        solution={k:patterns[k].index(stars[k]) for k in labels}
        solution.update((k,int(edge_pair(a,b) in selected)) for k,a,b in edges)
        p=RayPuzzle('lichtstrahl','Lichtstrahl',
            'Ziehe von jedem Zahlenfeld gerade Linien in bis zu vier waagerechten oder senkrechten Richtungen. '
            'Die Zahl zählt die leeren Felder aller Strahlen dieses Zahlenfelds zusammen; das Zahlenfeld selbst '
            'zählt nicht mit. Strahlen biegen nicht ab und enden vor anderen Zahlenfeldern. Sie dürfen sich nicht '
            'kreuzen oder überlappen. Jedes leere Feld wird genau einmal benutzt. Klicken oder Ziehen zeichnet '
            'Verbindungen; Notizen streicht Kanten durch.',model,solution,{},
            dict(kind='routes',mode='lichtstrahl',rows=n,cols=n,edges=edges,labels=labels,patterns=patterns),seed,difficulty)
        p.certify();return p
    raise ValueError('Kein eindeutig logisch lösbares Lichtstrahl-Rätsel gefunden')
