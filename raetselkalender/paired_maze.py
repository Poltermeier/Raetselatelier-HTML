"""Two-piece mazes with seed-based boards and breadth-first verification."""
from collections import deque
from random import Random
from typing import NamedTuple

from .puzzle import Puzzle
from .solver import Model

MINOTAUR = "minotaurus-labyrinth"
MIRROR = "spiegellabyrinth"
MAZE_TITLES = {MINOTAUR: "Minotaurus-Labyrinth", MIRROR: "Spiegellabyrinth"}
VECTORS = ((-1, 0), (0, 1), (1, 0), (0, -1))
UP, RIGHT, DOWN, LEFT, WAIT = range(5)
REFLECTED = (UP, LEFT, DOWN, RIGHT)
MOVE_NAMES = ("Oben", "Rechts", "Unten", "Links", "Warten")


class Board(NamedTuple):
    width: int
    height: int
    steps: tuple

    def step(self, cell, direction):
        return self.steps[cell][direction]


class PairedMaze(NamedTuple):
    variant: str
    boards: tuple
    start: tuple
    goals: tuple

    def result(self, state):
        first, second = state
        if self.variant == MINOTAUR:
            if first == second:
                return "caught"
            if first == self.goals[0]:
                return "won"
        elif state == self.goals:
            return "won"
        return None

    def trace(self, state, action):
        """Positions in the order they become visible during one turn."""
        first, second = state
        board = self.boards[0]
        if self.variant == MIRROR:
            if not 0 <= action < WAIT:
                return ()
            target = board.step(first, action), self.boards[1].step(second, REFLECTED[action])
            return (target,) if target != state else ()
        new_first = first if action == WAIT else board.step(first, action)
        if action != WAIT and new_first == first:
            return ()
        frames = [(new_first, second)]
        if new_first == second:
            return tuple(frames)
        row, col = divmod(new_first, board.width)
        for _ in range(2):
            previous = second
            enemy_row, enemy_col = divmod(previous, board.width)
            if enemy_col != col:
                second = board.step(previous, RIGHT if enemy_col < col else LEFT)
            if second == previous and enemy_row != row:
                second = board.step(previous, DOWN if enemy_row < row else UP)
            if second == previous:
                break
            frames.append((new_first, second))
            if new_first == second:
                break
        return tuple(frames) if frames[-1] != state else ()


def shortest_moves(maze, start=None):
    """Find a shortest winning route. Captured positions are never expanded."""
    start = maze.start if start is None else start
    pending = deque([start])
    parents = {start: None}
    actions = range(5 if maze.variant == MINOTAUR else 4)
    while pending:
        state = pending.popleft()
        outcome = maze.result(state)
        if outcome == "won":
            route = []
            while parents[state] is not None:
                state, action = parents[state]
                route.append(action)
            return tuple(reversed(route))
        if outcome == "caught":
            continue
        for action in actions:
            frames = maze.trace(state, action)
            if frames and frames[-1] not in parents:
                parents[frames[-1]] = state, action
                pending.append(frames[-1])
    return None


def grid_neighbours(width, height):
    result = []
    for cell in range(width * height):
        row, col = divmod(cell, width)
        result.append(tuple((row + dr) * width + col + dc
                            if 0 <= row + dr < height and 0 <= col + dc < width else cell
                            for dr, dc in VECTORS))
    return tuple(result)


def random_board(rng, width, height, openings):
    """Carve a connected maze with depth-first search, then open some loops."""
    neighbours = grid_neighbours(width, height)
    steps = [[cell] * 4 for cell in range(width * height)]
    start = rng.randrange(len(steps))
    frontier = [start]
    visited = {start}

    def connect(cell, neighbour, direction):
        steps[cell][direction] = neighbour
        steps[neighbour][(direction + 2) % 4] = cell

    while frontier:
        cell = frontier[-1]
        choices = [(d, target) for d, target in enumerate(neighbours[cell]) if target not in visited]
        if not choices:
            frontier.pop()
            continue
        direction, target = rng.choice(choices)
        connect(cell, target, direction)
        visited.add(target)
        frontier.append(target)
    walls = [(cell, neighbour, direction) for cell, adj in enumerate(neighbours)
             for direction, neighbour in enumerate(adj)
             if cell < neighbour and steps[cell][direction] == cell]
    for cell, neighbour, direction in rng.sample(walls, openings):
        connect(cell, neighbour, direction)
    return Board(width, height, tuple(map(tuple, steps)))


def board_distances(board, start):
    distances = {start: 0}
    pending = deque([start])
    while pending:
        cell = pending.popleft()
        for target in board.steps[cell]:
            if target not in distances:
                distances[target] = distances[cell] + 1
                pending.append(target)

    return distances


def distant_goal(rng, board, start, *, border=False):
    distances = board_distances(board, start)
    eligible = distances
    if border:
        eligible = [cell for cell in distances if cell // board.width in (0, board.height - 1)
                    or cell % board.width in (0, board.width - 1)]
    distant = sorted(eligible, key=distances.__getitem__, reverse=True)[:len(eligible) // 4]
    return rng.choice(distant)


def candidate_maze(rng, variant, hard):
    if variant == MINOTAUR:
        size = 7 if hard else 6
        board = random_board(rng, size, size, 10 if hard else 7)
        first, second = rng.sample(range(size * size), 2)
        goal = distant_goal(rng, board, first, border=True)
        if goal == second:
            second = rng.choice([cell for cell in range(size * size) if cell not in (first, goal)])
        return PairedMaze(variant, (board,), (first, second), (goal,))
    size = 6 if hard else 5
    boards = tuple(random_board(rng, size, size, 2 if hard else 3) for _ in range(2))
    starts = tuple(rng.randrange(size * size) for _ in boards)
    goals = tuple(distant_goal(rng, board, start) for board, start in zip(boards, starts))
    return PairedMaze(variant, boards, starts, goals)


def generate_maze(variant, seed, difficulty):
    if seed is None:
        from secrets import randbits
        seed = randbits(48)
    rng = Random(seed)
    hard = difficulty == "schwer"
    if variant == MINOTAUR:
        low, high, extra = (23, 48, 6) if hard else (14, 25, 4)
        rules = ("Erreiche den grünen Ausgang (Z) und entkomme dem Minotaurus. Nach deinem Zug oder Warten verfolgt er dich "
                 "bis zu zwei Felder weit. Er versucht bei jedem Schritt zuerst die waagerechte Richtung, "
                 "dann die senkrechte. Mauern blockieren beide Figuren. Du musst die Verfolgung auch am Ausgang überstehen.")
    else:
        low, high, extra = (28, 58, 6) if hard else (18, 31, 5)
        rules = ("Steuere beide Figuren gleichzeitig. Oben und unten gelten für beide gleich, links und rechts "
                 "sind im rechten Labyrinth vertauscht. Eine Mauer hält nur die betroffene Figur auf. "
                 "Beide Figuren müssen am Ende desselben Zugs auf ihrem eigenen Ziel stehen.")
    for attempt in range(1, 401):
        if attempt == 301:
            # A bounded retry on a known solvable seed keeps the menu playable for any input seed.
            rng = Random(0)
        maze = candidate_maze(rng, variant, hard)
        solo = max(board_distances(board, start)[goal]
                   for board, start, goal in zip(maze.boards, maze.start, maze.goals))
        if solo > high:
            continue
        route = shortest_moves(maze)
        if route is None or not max(low, solo + extra) <= len(route) <= high:
            continue
        view = {"kind": "maze-game", "maze": maze}
        return Puzzle(variant, MAZE_TITLES[variant], rules, Model({}, []), {}, {}, view, seed, difficulty,
                      analysis={"shortest_moves": len(route), "generation_attempts": attempt})
    raise ValueError("Kein passendes Labyrinth gefunden. Bitte einen anderen Seed wählen.")
