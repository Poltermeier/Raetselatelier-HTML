"""Sparse planar relation graphs with fewer clues and longer deductions."""
import random

from .extra_constraints import HallDifferent, RelationshipOrder
from .generators import finish, first_solution, reduce_givens
from .solver import Model, Table, deduce


def relation_model(keys, edges):
    separated = tuple((a, b) for a in range(1, 10) for b in range(1, 10) if abs(a-b) >= 2)
    return Model({k: set(range(1, 10)) for k in keys},
                 [HallDifferent(tuple(keys)), RelationshipOrder(keys, edges)]
                 + [Table((a, b), separated) for a, b in edges])


def connected(keys, edges):
    graph = {k: set() for k in keys}
    for a, b in edges:
        graph[a].add(b)
        graph[b].add(a)
    seen, todo = {keys[0]}, [keys[0]]
    while todo:
        for k in graph[todo.pop()]-seen:
            seen.add(k)
            todo.append(k)
    return len(seen) == len(keys)


def relationship(seed, difficulty):
    rng = random.Random(seed)
    keys = tuple(f'Kreis {i+1}' for i in range(9))
    outer, hub = keys[:-1], keys[-1]
    positions = dict(zip(keys, ((70, 65), (320, 65), (570, 65), (570, 240),
                               (570, 415), (320, 415), (70, 415), (70, 240), (320, 240))))
    best = None
    for _ in range(24):
        edges = [(hub, k) for k in rng.sample(list(outer), 7)]
        ring = [(outer[i], outer[(i+1) % 8]) for i in range(8)]
        rng.shuffle(ring)
        # Include enough perimeter segments to connect the one non-spoke node.
        covered = {k for edge in edges for k in edge}
        for edge in ring:
            if any(k not in covered for k in edge):
                edges.append(edge)
                covered.update(edge)
        for edge in ring:
            if edge not in edges and len(edges) < 12:
                edges.append(edge)
        model = relation_model(keys, edges)
        for _ in range(32):
            solution = first_solution(model, rng)
            givens = reduce_givens(model, solution, rng, 3)
            if len(givens) > 4:
                continue
            proof = deduce(model, givens)
            score = (-len(givens), -int(hub in givens), len(proof.steps))
            if best is None or score > best[0]:
                best = score, solution, givens, edges.copy()
            if len(givens) == 3 and hub not in givens:
                break
        if best is not None and len(best[2]) == 3 and hub not in best[2]:
            break
    if best is None:
        raise ValueError('Keine ausreichend sparsame Beziehungskiste gefunden')
    _, solution, givens, edges = best
    minimum = 10 if difficulty == 'schwer' else 11
    options = edges.copy()
    rng.shuffle(options)
    for edge in options:
        if len(edges) <= minimum:
            break
        candidate = [e for e in edges if e != edge]
        if connected(keys, candidate) and deduce(relation_model(keys, candidate), givens, trace=False).solved:
            edges = candidate
    model = relation_model(keys, edges)
    p = finish('beziehungskiste', 'Beziehungskiste',
        'Verteile 1 bis 9 jeweils genau einmal auf die neun Kreise. Verbundene Kreise müssen '
        'eine Differenz von mindestens 2 haben. Die Linien enden an den Kreisen; es gibt keine '
        'zusätzlichen Verbindungen. Wenige Vorgaben verlangen auch Überlegungen dazu, '
        'wo die aufeinanderfolgenden Zahlen überhaupt stehen können.',
        model, solution, givens, dict(kind='diagram', positions=positions, links=edges,
                                     width=640, height=480, labels=False), seed, difficulty)
    p.analysis['relation_clues'] = len(givens)
    p.analysis['relation_connections'] = len(edges)
    return p
