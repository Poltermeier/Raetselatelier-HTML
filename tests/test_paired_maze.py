from itertools import product
import unittest

from raetselkalender.paired_maze import (
    Board, MINOTAUR, MIRROR, RIGHT, UP, WAIT, PairedMaze, generate_maze,
    grid_neighbours, shortest_moves,
)


def open_board(width, height, *, wall=None):
    neighbours = [list(row) for row in grid_neighbours(width, height)]
    if wall:
        first, second = wall
        neighbours[first][neighbours[first].index(second)] = first
        neighbours[second][neighbours[second].index(first)] = second
    return Board(width, height, tuple(map(tuple, neighbours)))


class PairedMazeTests(unittest.TestCase):
    def test_minotaur_moves_horizontally_first_and_captures_as_soon_as_it_arrives(self):
        board = open_board(3, 3)
        maze = PairedMaze(MINOTAUR, (board,), (0, 8), (2,))
        self.assertEqual(maze.trace(maze.start, RIGHT), ((1, 8), (1, 7), (1, 4)))
        waiting = maze.trace((1, 4), WAIT)
        self.assertEqual(waiting, ((1, 4), (1, 1)))
        self.assertEqual(maze.result(waiting[-1]), "caught")

    def test_minotaur_uses_vertical_step_behind_wall_and_can_capture_on_exit(self):
        board = open_board(3, 3, wall=(7, 8))
        maze = PairedMaze(MINOTAUR, (board,), (0, 8), (1,))
        self.assertEqual(maze.trace(maze.start, RIGHT), ((1, 8), (1, 5), (1, 4)))
        self.assertEqual(maze.result(maze.trace((0, 2), RIGHT)[-1]), "caught")
        self.assertEqual(maze.result(maze.trace((0, 8), RIGHT)[-1]), "won")

    def test_mirror_moves_each_piece_independently_and_requires_both_goals(self):
        left = open_board(2, 2, wall=(0, 1))
        right = open_board(2, 2)
        maze = PairedMaze(MIRROR, (left, right), (0, 1), (2, 0))
        self.assertEqual(maze.trace(maze.start, RIGHT), ((0, 0),))
        self.assertIsNone(maze.result((0, 0)))
        self.assertEqual(maze.trace(maze.start, UP), ())
        self.assertEqual(maze.trace(maze.start, WAIT), ())
        self.assertEqual(maze.result((2, 0)), "won")

    def test_generated_mazes_have_seeded_solutions_in_both_difficulties(self):
        for variant, difficulty in product((MINOTAUR, MIRROR), ("mittel", "schwer")):
            with self.subTest(variant=variant, difficulty=difficulty):
                examples = [generate_maze(variant, seed, difficulty) for seed in (0, 41, -73)]
                self.assertEqual(len({example.view["maze"] for example in examples}), 3)
                self.assertEqual(examples[0].view, generate_maze(variant, 0, difficulty).view)
                for puzzle in examples:
                    maze = puzzle.view["maze"]
                    route = shortest_moves(maze)
                    self.assertEqual(len(route), puzzle.analysis["shortest_moves"])
                    state = maze.start
                    for action in route:
                        self.assertIsNone(maze.result(state))
                        state = maze.trace(state, action)[-1]
                    self.assertEqual(maze.result(state), "won")
                    if variant == MINOTAUR:
                        row, col = divmod(maze.goals[0], maze.boards[0].width)
                        self.assertTrue(row in (0, maze.boards[0].height - 1)
                                        or col in (0, maze.boards[0].width - 1))
