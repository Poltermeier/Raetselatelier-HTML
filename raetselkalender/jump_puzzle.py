"""Exact shortest paths on a directed grid of jump distances."""
from collections import deque
import random

from .puzzle import Puzzle
from .solver import Model, Table


def jump_targets(numbers, size, position, goal):
    if position == goal:
        return ()
    r, c = divmod(position, size)
    distance = numbers[position]
    return tuple(rr*size+cc for rr, cc in ((r-distance,c),(r+distance,c),(r,c-distance),(r,c+distance))
                 if 0 <= rr < size and 0 <= cc < size)


def jump_graph(numbers, size, start, goal):
    return shortest_path_graph(lambda position:jump_targets(numbers,size,position,goal),start,goal)


def shortest_path_graph(targets,start,goal):
    distance, ways, parents = {start: 0}, {start: 1}, {start: []}
    pending = deque([start])
    while pending:
        position = pending.popleft()
        for target in targets(position):
            depth = distance[position]+1
            if target not in distance:
                distance[target], ways[target], parents[target] = depth, 0, []
                pending.append(target)
            if distance[target] == depth:
                parents[target].append(position)
                ways[target] = min(2,ways[target]+ways[position])
    route = []
    if goal in distance:
        current = goal
        while current != start:
            route.append(current)
            current = parents[current][0]
        route.append(start)
        route.reverse()
    return distance, ways, route


class JumpPuzzle(Puzzle):
    def targets(self,position):
        v=self.view
        return jump_targets(v['numbers'],v['size'],position,v['goal'])

    def check_path(self, path):
        v = self.view
        if (not path or path[0] != v['start'] or any(type(k) is not int or not 0 <= k < v['size']**2 for k in path)):
            return 'invalid'
        for a,b in zip(path,path[1:]):
            if b not in self.targets(a):
                return 'invalid'
        if path[-1] != v['goal']:
            return 'incomplete'
        if v['require_shortest'] and len(path)-1 != v['par']:
            return 'nonoptimal'
        return 'correct'

    def check(self, entries):
        if any(k not in self.model.domains or type(v) is not int or v not in self.model.domains[k] for k,v in entries.items()):
            return 'invalid',[]
        if any(k not in entries for k in self.editable):
            return 'incomplete',[]
        state = self.check_path([self.view['start']]+[entries[k] for k in self.editable])
        return ('correct',[]) if state == 'correct' else ('wrong',self.editable)

    def certify(self):
        v = self.view
        if len(v['numbers']) != v['size']**2 or any(type(n) is not int or not 0 <= n < v['size'] for n in v['numbers']):
            raise ValueError('Ungültiges Sprungfeld')
        if any(n == 0 for i,n in enumerate(v['numbers']) if i != v['goal']):
            raise ValueError('Nur das Ziel darf die Sprungweite 0 haben')
        self.certify_path()

    def certify_path(self):
        v=self.view
        distance, ways, route = shortest_path_graph(self.targets,v['start'],v['goal'])
        if not route or ways[v['goal']] != 1 or distance[v['goal']] != v['par']:
            raise ValueError('Kein eindeutiger kürzester Sprungweg')
        if [self.solution[k] for k in self.editable] != route[1:]:
            raise ValueError('Gespeicherter Sprungweg stimmt nicht mit dem BFS-Nachweis überein')
        if self.model.constraints[0].rows != (tuple(route[1:]),):
            raise ValueError('Zugmodell passt nicht zum Sprungweg')
        self.analysis.update(unique=v['require_shortest'], unique_shortest=True, optimality_verified=True,
            logical_solvable=False, solution_method='shortest_path_bfs', minimum_moves=v['par'],
            search_nodes=len(distance), search_branches=None,
            difficulty_note='Planungsrätsel: vollständiger kürzester-Wege-Nachweis, keine menschliche Kalibrierung.')
        self.logical_steps = [dict(rule=v.get('mode','exact_jump'), source=a, target=b,
            **({'distance':v['numbers'][a]} if 'numbers' in v else {})) for a,b in zip(route,route[1:])]


def jump_puzzle(seed,difficulty):
    rng = random.Random(seed)
    size,start,goal = 5,0,24
    low,high = (5,7) if difficulty == 'mittel' else (8,10)
    for _ in range(12000):
        numbers = [rng.randrange(1,size) for _ in range(size*size)]
        numbers[goal] = 0
        distance,ways,route = jump_graph(numbers,size,start,goal)
        if goal not in distance or not low <= distance[goal] <= high or ways[goal] != 1:
            continue
        keys = tuple(f'Sprung {i+1}' for i in range(len(route)-1))
        model = Model({k:set(range(size*size)) for k in keys},[Table(keys,(tuple(route[1:]),))])
        p = JumpPuzzle('jump-puzzle','Jump Puzzle',
            'Springe vom Start S zur grünen Zielflagge. Die Zahl deines aktuellen Feldes bestimmt '
            'die exakte Sprungweite. Erlaubt sind waagerechte und senkrechte Sprünge, keine Diagonalen. '
            'Klicke ein erreichbares Feld an. Nur der kürzeste Weg zählt; die benötigte Zugzahl steht oben. '
            'Rückgängig nimmt einen Sprung zurück.',model,dict(zip(keys,route[1:])),{},
            dict(kind='jump',size=size,numbers=numbers,start=start,goal=goal,par=distance[goal],require_shortest=True),
            seed,difficulty)
        p.certify();return p
    raise ValueError('Kein passendes Jump Puzzle mit eindeutig kürzestem Weg gefunden')
