"""Slitherlink, Numberlink and Country Road."""
from itertools import combinations, product
import random

from .generators import cell, finish
from .network_rules import RouteTopology
from .puzzle import Puzzle
from .solver import Model, Sum, Table, deduce


def grid_edges(rows, cols):
    return [(f'E{len_prefix+r*cols+c}', cell(r,c), cell(rr,cc))
            for len_prefix, dr, dc in ((0,0,1),(rows*cols,1,0))
            for r in range(rows-dr) for c in range(cols-dc)
            for rr,cc in [(r+dr,c+dc)]]


def incident_edges(edges):
    incident = {}
    for key,a,b in edges:
        incident.setdefault(a,[]).append(key)
        incident.setdefault(b,[]).append(key)
    return incident


def degree_table(keys, degrees):
    return Table(tuple(keys), tuple(bits for bits in product((0,1),repeat=len(keys)) if sum(bits) in degrees))


def poly_boundary(cells):
    edges = set()
    for r,c in cells:
        for a,b in (((r,c),(r,c+1)),((r,c),(r+1,c)),((r+1,c),(r+1,c+1)),((r,c+1),(r+1,c+1))):
            pair = tuple(sorted((cell(*a),cell(*b))))
            if pair in edges:
                edges.remove(pair)
            else:
                edges.add(pair)
    return edges


def single_cycle(pairs):
    graph = {}
    for a,b in pairs:
        graph.setdefault(a,set()).add(b); graph.setdefault(b,set()).add(a)
    if not graph or any(len(v) != 2 for v in graph.values()):
        return False
    seen, pending = set(), [next(iter(graph))]
    while pending:
        v = pending.pop()
        if v not in seen:
            seen.add(v); pending.extend(graph[v]-seen)
    return len(seen) == len(graph)


def random_cycle(size, rng):
    cells = {(rng.randrange(size-1),rng.randrange(size-1))}
    target = rng.randint(max(3,(size-1)**2//3), max(4,(size-1)**2*2//3))
    while len(cells) < target:
        options = sorted({(r+dr,c+dc) for r,c in cells for dr,dc in ((1,0),(-1,0),(0,1),(0,-1))
                          if 0 <= r+dr < size-1 and 0 <= c+dc < size-1}-cells)
        rng.shuffle(options)
        for candidate in options:
            if single_cycle(poly_boundary(cells|{candidate})):
                cells.add(candidate); break
        else:
            break
    return poly_boundary(cells)


def slither_model(edges, clues, n):
    incident = incident_edges(edges)
    lookup = {tuple(sorted((a,b))): key for key,a,b in edges}
    constraints = [degree_table(keys,(0,2)) for keys in incident.values()]
    for key,total in clues.items():
        r,c = map(int,key.split(','))
        corners = [cell(r,c),cell(r,c+1),cell(r+1,c+1),cell(r+1,c)]
        keys = tuple(lookup[tuple(sorted((corners[i],corners[(i+1)%4])))] for i in range(4))
        constraints.append(Sum(keys,total))
    return Model({k:{0,1} for k,a,b in edges}, constraints+[RouteTopology(edges)])


def slitherlink(seed, difficulty):
    rng = random.Random(seed)
    n = 6 if difficulty == 'mittel' else 7
    edges = grid_edges(n+1,n+1)
    for _ in range(160):
        chosen = random_cycle(n+1,rng)
        solution = {k:int(tuple(sorted((a,b))) in chosen) for k,a,b in edges}
        clues = {}
        lookup = {tuple(sorted((a,b))):solution[k] for k,a,b in edges}
        for r in range(n):
            for c in range(n):
                corners = [cell(r,c),cell(r,c+1),cell(r+1,c+1),cell(r+1,c)]
                clues[cell(r,c)] = sum(lookup[tuple(sorted((corners[i],corners[(i+1)%4])))] for i in range(4))
        if not deduce(slither_model(edges,clues,n), trace=False).solved:
            continue
        order = list(clues); rng.shuffle(order)
        for key in order:
            candidate = {k:v for k,v in clues.items() if k != key}
            if deduce(slither_model(edges,candidate,n),trace=False).solved:
                clues = candidate
        return finish('slitherlink','Slitherlink',
            'Zeichne auf den Gitterkanten genau einen geschlossenen Rundweg ohne Kreuzung oder Verzweigung. '
            'Eine Zahl nennt, wie viele der vier Seiten ihres Kästchens zum Weg gehören. '
            'Klicken oder Ziehen schaltet Kanten; Notizen markiert ausgeschlossene Kanten.',
            slither_model(edges,clues,n),solution,{},dict(kind='routes', mode='slitherlink',rows=n,cols=n,
                edges=edges,labels=clues),seed,difficulty)
    raise ValueError('Kein Slitherlink mit vollständigem logischem Lösungsweg gefunden')


def hamiltonian(rows, cols, rng):
    path = [cell(r,c) for r in range(rows) for c in (range(cols) if r%2 == 0 else range(cols-1,-1,-1))]
    for _ in range(rows*cols*12):
        if rng.randrange(2):
            path.reverse()
        r,c = map(int,path[-1].split(','))
        neighbors = {cell(rr,cc) for rr,cc in ((r-1,c),(r+1,c),(r,c-1),(r,c+1))
                     if 0 <= rr < rows and 0 <= cc < cols}-{path[-2]}
        if neighbors:
            at = path.index(rng.choice(sorted(neighbors)))
            path = path[:at+1]+list(reversed(path[at+1:]))
    return path


def number_model(edges, terminals):
    return Model({k:{0,1} for k,a,b in edges},
        [degree_table(keys,(1,) if node in terminals else (2,))
         for node,keys in incident_edges(edges).items()]+[RouteTopology(edges,terminals)])


def numberlink(seed, difficulty):
    rng = random.Random(seed)
    n = 5 if difficulty == 'mittel' else 6
    edges = grid_edges(n,n)
    pair_count = 6 if n == 5 else 9
    for _ in range(240):
        path = hamiltonian(n,n,rng)
        lengths = [2]*pair_count
        for _ in range(n*n-2*pair_count):
            lengths[rng.randrange(pair_count)] += 1
        terminals, chosen, offset = {}, set(), 0
        labels = rng.sample(range(1,pair_count+1),pair_count)
        for length,label in zip(lengths,labels):
            group = path[offset:offset+length]; offset += length
            terminals[group[0]] = terminals[group[-1]] = label
            chosen.update(tuple(sorted(pair)) for pair in zip(group,group[1:]))
        model = number_model(edges,terminals)
        if deduce(model,trace=False).solved:
            solution = {k:int(tuple(sorted((a,b))) in chosen) for k,a,b in edges}
            return finish('numberlink','Numberlink',
                'Verbinde jedes Paar gleicher Zahlen durch einen waagerechten oder senkrechten Weg. '
                'Die Wege bedecken gemeinsam alle Felder, ohne sich zu kreuzen oder zu verzweigen. '
                'Klicke oder ziehe zwischen benachbarten Feldern; Notizen streicht eine Verbindung durch.',
                model,solution,{},dict(kind='routes',mode='numberlink',rows=n,cols=n,edges=edges,labels=terminals),seed,difficulty)
    raise ValueError('Kein eindeutig logisch lösbares Numberlink gefunden')



class RoadPuzzle(Puzzle):
    @property
    def editable(self):
        return [key for key in self.model.domains if key.startswith('E')]

    def check(self, entries):
        supplied = entries.copy()
        for node,keys in incident_edges(self.view['edges']).items():
            if all(key in entries and type(entries[key]) is int for key in keys):
                key = 'visit:'+node
                value = int(any(entries[k] for k in keys))
                if key in supplied and supplied[key] != value:
                    return 'invalid',[]
                supplied[key] = value
        return super().check(supplied)


def region_path_table(edges,region,total):
    inside=set(region)
    internal=[(k,a,b) for k,a,b in edges if a in inside and b in inside]
    external=[(k,a if a in inside else b) for k,a,b in edges if (a in inside)!=(b in inside)]
    adjacent={node:[] for node in region}
    exits={node:[] for node in region}
    for key,a,b in internal:
        adjacent[a].append((b,key));adjacent[b].append((a,key))
    for key,node in external:
        exits[node].append(key)
    keys=tuple('visit:'+k for k in region)+tuple(k for k,a,b in internal)+tuple(k for k,a in external)
    rows=set()
    def extend(path,used):
        if total is None or len(path)==total:
            pairs=(combinations(exits[path[0]],2) if len(path)==1 else
                   product(exits[path[0]],exits[path[-1]]))
            for first,last in pairs:
                selected=set(used)|{first,last}
                row=tuple(int(k in path) for k in region)+tuple(int(k in selected) for k in keys[len(region):])
                rows.add(row)
                if len(rows)>6000:
                    raise OverflowError
        if len(path)<(len(region) if total is None else total):
            for node,key in adjacent[path[-1]]:
                if node not in path:
                    extend(path+[node],used+[key])
    try:
        for node in region:
            if exits[node]:
                extend([node],[])
    except OverflowError:
        return None
    return Table(keys,tuple(sorted(rows)))


def road_model(edges,regions,clues):
    incident = incident_edges(edges)
    owner = {k:i for i,group in enumerate(regions) for k in group}
    domains = {key:{0,1} for key,a,b in edges}
    domains.update({'visit:'+node:{0,1} for node in incident})
    constraints = []
    for node,keys in incident.items():
        allowed = tuple(bits+(int(sum(bits)==2),) for bits in product((0,1),repeat=len(keys)) if sum(bits) in (0,2))
        constraints.append(Table(tuple(keys)+('visit:'+node,),allowed))
    for i,region in enumerate(regions):
        crossing = tuple(key for key,a,b in edges if (owner[a]==i) != (owner[b]==i))
        constraints.append(Sum(crossing,2))
        if i in clues:
            constraints.append(Sum(tuple('visit:'+k for k in region),clues[i]))
            internal = tuple(key for key,a,b in edges if owner[a] == i == owner[b])
            constraints.append(Sum(internal,clues[i]-1))
        if i in clues or len(region)<=8:
            pattern=region_path_table(edges,region,clues.get(i))
            if pattern is not None:
                constraints.append(pattern)
    constraints += [Table(('visit:'+a,'visit:'+b),((0,1),(1,0),(1,1)))
                    for key,a,b in edges if owner[a] != owner[b]]
    return Model(domains,constraints+[RouteTopology(edges)])


def country_road(seed,difficulty):
    rng = random.Random(seed)
    n = 6 if difficulty == 'mittel' else 7
    edges = grid_edges(n,n)
    nodes = {cell(r,c) for r in range(n) for c in range(n)}
    for _ in range(200):
        chosen = random_cycle(n,rng)
        graph = {}
        for a,b in chosen:
            graph.setdefault(a,[]).append(b);graph.setdefault(b,[]).append(a)
        coordinates=[tuple(map(int,k.split(','))) for k in graph]
        if (len(graph)<n*n//2+2
                or {r for r,c in coordinates}!={*range(n)}
                or {c for r,c in coordinates}!={*range(n)}):
            continue
        start = min(graph)
        cycle,previous,current = [],None,start
        while current not in cycle:
            cycle.append(current)
            following = next(k for k in sorted(graph[current]) if k != previous)
            previous,current = current,following
        offset = rng.randrange(len(cycle));cycle=cycle[offset:]+cycle[:offset]
        count = min(n+1,len(cycle)//2)
        lengths = [2]*count
        for _ in range(len(cycle)-2*count):
            lengths[rng.randrange(count)] += 1
        regions,offset = [],0
        for length in lengths:
            regions.append(set(cycle[offset:offset+length]));offset+=length
        remaining = nodes-set(cycle)
        while remaining:
            component,pending = set(),[min(remaining)]
            while pending:
                key = pending.pop()
                if key in component:
                    continue
                component.add(key)
                r,c=map(int,key.split(','))
                pending.extend(k for k in (cell(r-1,c),cell(r+1,c),cell(r,c-1),cell(r,c+1)) if k in remaining-component)
            bordering = {k for key in component for r,c in [map(int,key.split(','))]
                         for k in (cell(r-1,c),cell(r+1,c),cell(r,c-1),cell(r,c+1))}-component
            options = [i for i,g in enumerate(regions) if g & bordering]
            regions[rng.choice(options)].update(component)
            remaining -= component
        regions = [sorted(g) for g in regions]
        if max(map(len,regions))>n*n//3+2:
            continue
        clues = {i:sum(k in graph for k in group) for i,group in enumerate(regions)}
        model = road_model(edges,regions,clues)
        if not deduce(model,trace=False).solved:
            continue
        solution={key:int(tuple(sorted((a,b))) in chosen) for key,a,b in edges}
        solution.update({'visit:'+node:int(node in graph) for node in nodes})
        p=RoadPuzzle('country-road','Country Road',
            'Zeichne einen einzigen geschlossenen Weg durch die Feldmitten. Er besucht jeden '
            'Bereich genau einmal, ohne Kreuzung oder Verzweigung. Jedes Gebiet hat eine Zahl; sie zählt '
            'die benutzten Felder in diesem Bereich. Zwei waagerecht oder senkrecht benachbarte '
            'unbenutzte Felder dürfen nicht in verschiedenen Bereichen liegen. '
            'Klicken oder Ziehen verbindet benachbarte Felder; Notizen markiert ausgeschlossene Verbindungen.',
            road_model(edges,regions,clues),solution,{},dict(kind='routes',mode='country-road',rows=n,cols=n,
                regions=regions,region_clues=clues,edges=edges,labels={}),seed,difficulty)
        p.certify();return p
    raise ValueError('Keine logisch eindeutige Country-Road-Aufgabe gefunden')
