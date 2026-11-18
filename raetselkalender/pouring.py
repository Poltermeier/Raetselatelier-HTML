"""Exact shortest paths for maximal pours between three labelled vessels."""
from collections import deque
import random

from .puzzle import Puzzle
from .solver import Model, Table

LETTERS = ('A', 'B', 'C')
ACTIONS = tuple((a, b) for a in range(3) for b in range(3) if a != b)


def transfer_amount(available,free_space):
    return max(0,min(available,free_space))


def pour(capacities, state, source, target):
    if source == target or not 0 <= source < 3 or not 0 <= target < 3:
        return None
    amount = transfer_amount(state[source], capacities[target]-state[target])
    if amount <= 0:
        return None
    result = list(state)
    result[source] -= amount
    result[target] += amount
    return tuple(result)


def shortest_graph(capacities, initial):
    initial = tuple(initial)
    distance, parents, ways = {initial: 0}, {initial: []}, {initial: 1}
    todo = deque([initial])
    while todo:
        state = todo.popleft()
        for action, (a, b) in enumerate(ACTIONS):
            following = pour(capacities, state, a, b)
            if following is None:
                continue
            depth = distance[state]+1
            if following not in distance:
                distance[following], parents[following], ways[following] = depth, [], 0
                todo.append(following)
            if distance[following] == depth:
                parents[following].append((state, action))
                ways[following] = min(33, ways[following]+ways[state])
    return distance, parents, ways


def optimal_routes(parents, initial, target):
    initial, target = tuple(initial), tuple(target)
    if target == initial:
        return [()]
    return [prefix+(action,) for state, action in parents[target]
            for prefix in optimal_routes(parents, initial, state)]


class PouringPuzzle(Puzzle):
    def check_moves(self, moves):
        state = tuple(self.view['initial'])
        states = [state]
        for a, b in moves:
            state = pour(self.view['capacities'], state, a, b)
            if state is None:
                return 'invalid', states
            states.append(state)
        if state != tuple(self.view['target']):
            return 'wrong', states
        return ('correct' if len(moves) == self.analysis['minimum_moves'] else 'nonoptimal'), states

    def check(self, entries):
        if any(k not in self.model.domains or type(v) is not int or v not in self.model.domains[k]
               for k, v in entries.items()):
            return 'invalid', []
        if any(k not in entries for k in self.editable):
            return 'incomplete', []
        moves = [ACTIONS[entries[k]] for k in self.editable]
        state, _ = self.check_moves(moves)
        return ('correct', []) if state == 'correct' else ('wrong', self.editable)

    def certify(self):
        self.logical_steps = []
        self.analysis.update(unique=False, optimality_verified=False, logical_solvable=False)
        capacities, initial, target = (tuple(self.view[k]) for k in ('capacities', 'initial', 'target'))
        distance, parents, ways = shortest_graph(capacities, initial)
        if target not in distance or not 0 < ways[target] <= 32:
            raise ValueError('Kein begrenzter vollständiger Optimalitätsnachweis möglich')
        routes = optimal_routes(parents, initial, target)
        table = self.model.constraints[0]
        if not isinstance(table, Table) or set(table.rows) != set(routes):
            raise ValueError('Zugmodell stimmt nicht mit dem unabhängigen kürzesten-Wege-Nachweis überein')
        canonical = tuple(self.solution[k] for k in self.editable)
        if canonical not in routes:
            raise ValueError('Die gespeicherte Umfüllfolge ist nicht optimal')
        self.analysis.update(unique=len(routes) == 1, optimality_verified=True,
                             solution_method='shortest_path_bfs', minimum_moves=distance[target],
                             optimal_solution_count=len(routes), search_nodes=len(distance), search_branches=None,
                             difficulty_note='Planungsrätsel: alle kürzesten korrekten Zugfolgen werden akzeptiert.')
        state = initial
        for action in canonical:
            a, b = ACTIONS[action]
            following = pour(capacities, state, a, b)
            self.logical_steps.append(dict(rule='maximal_pour', source=LETTERS[a], target=LETTERS[b],
                                           before=list(state), after=list(following)))
            state = following

    def export(self, include_solution=False):
        data = super().export(include_solution)
        if not include_solution:
            # The action-variable count itself would reveal the minimum length.
            data.pop('domains')
            data['analysis'] = {k: v for k, v in data['analysis'].items()
                                if k not in ('minimum_moves', 'optimal_solution_count')}
        return data


def pouring(seed, difficulty):
    rng = random.Random(seed)
    for _ in range(300):
        capacities = tuple(rng.sample(range(4, 14), 3))
        initial = tuple(rng.randrange(capacity+1) for capacity in capacities)
        if not 2 <= sum(initial) < sum(capacities)-2:
            continue
        distance, parents, ways = shortest_graph(capacities, initial)
        low, high = (3, 4) if difficulty == 'mittel' else (5, 6)
        targets = sorted(state for state, depth in distance.items() if low <= depth <= high
                         and ways[state] <= 8 and sum(a != b for a, b in zip(initial, state)) >= 2)
        if not targets:
            continue
        target = rng.choice(targets)
        routes = optimal_routes(parents, initial, target)
        keys = tuple(f'Zug {i+1}' for i in range(distance[target]))
        model = Model({k: set(range(6)) for k in keys}, [Table(keys, tuple(routes))])
        p = PouringPuzzle('optimal-umgefuellt', 'Optimal umgefüllt',
            'Bringe die Wassermengen von der Ausgangslage zur Zielverteilung. Die Behälter heißen A, B und C. '
            'Bei jedem Zug wird aus dem ersten in den zweiten Behälter gegossen, bis die Quelle leer '
            'oder das Zielgefäß voll ist. Wasser darf nicht von außen ergänzt oder weggeschüttet werden. '
            'Jeder vollständig eingegebene Schritt wird sofort animiert und aktualisiert die Füllstände. '
            f'Diese Aufgabe ist mit höchstens {high} Umfüllvorgängen lösbar. '
            'Ergänze Züge mit + und prüfe das Ziel mit Fertig. Gesucht ist eine möglichst kurze Folge; '
            'jede kürzeste korrekte Folge zählt.', model, dict(zip(keys, routes[0])), {},
            dict(kind='pouring', capacities=list(capacities), initial=list(initial), target=list(target)),
            seed, difficulty)
        p.certify()
        return p
    raise ValueError('Kein passendes Umfüllrätsel im Versuchslimit gefunden')
