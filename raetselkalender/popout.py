"""Four-in-a-row rules and a bounded alpha-beta engine on a 7 × 6 bitboard."""
from collections import Counter
from random import Random

WIDTH, HEIGHT, STRIDE = 7, 6, 7
COLUMNS = tuple(63 << (column * STRIDE) for column in range(WIDTH))
CENTER_FIRST = (3, 2, 4, 1, 5, 0, 6)
DIRECTIONS = (1, STRIDE, STRIDE-1, STRIDE+1)
BOARD_MASK = sum(COLUMNS)
BOTTOM_ROW = sum(1 << (column * STRIDE) for column in range(WIDTH))
LEVELS = {"leicht": (2, 900), "mittel": (5, 9000), "schwer": (6, 18000), "experte": (7, 32000)}
WIN = 100000


def legal_moves(board, player, *, allow_remove=True):
    occupied = board[0] | board[1]
    drops, pops = [], []
    for column in CENTER_FIRST:
        base = column * STRIDE
        if not occupied & (1 << (base+HEIGHT-1)):
            drops.append(column)
        if allow_remove and board[player] & (1 << base):
            pops.append(column+WIDTH)
    return drops + pops


def apply_move(board, player, move):
    column = move % WIDTH
    mask = COLUMNS[column]
    if move < WIDTH:
        filled = ((board[0] | board[1]) & mask).bit_count()
        disc = 1 << (column*STRIDE+filled)
        return (board[0] | disc, board[1]) if player == 0 else (board[0], board[1] | disc)
    return tuple((bits & ~mask) | ((bits & mask) >> 1 & mask) for bits in board)


def has_four(bits):
    for shift in DIRECTIONS:
        pairs = bits & (bits >> shift)
        if pairs & (pairs >> (2*shift)):
            return True
    return False


def winner(board, mover):
    if has_four(board[mover]):
        return mover
    if has_four(board[1-mover]):
        return 1-mover
    return None


def winning_cells(bits):
    cells = set()
    for shift in DIRECTIONS:
        starts = bits & (bits >> shift) & (bits >> (2*shift)) & (bits >> (3*shift))
        while starts:
            first = (starts & -starts).bit_length()-1
            starts &= starts-1
            cells.update(divmod(first + i*shift, STRIDE) for i in range(4))
    return cells


class PopOutGame:
    def __init__(self, seed, difficulty, *, allow_remove=True):
        self.board = (0, 0)
        self.turn = 0
        self.result = None
        self.difficulty = difficulty
        self.allow_remove = allow_remove
        self.random = Random(seed)
        self.repetitions = Counter({(*self.board, self.turn): 1})

    def moves(self):
        return legal_moves(self.board, self.turn, allow_remove=self.allow_remove)

    def play(self, move):
        if type(move) is not int or self.result is not None or move not in self.moves():
            return False
        self.board = apply_move(self.board, self.turn, move)
        won = winner(self.board, self.turn)
        self.turn ^= 1
        key = (*self.board, self.turn)
        self.repetitions[key] += 1
        if won is not None:
            self.result = won
        elif self.repetitions[key] >= 3 or not self.moves():
            self.result = "draw"
        return True


def simple_position_value(board, player):
    def value(bits):
        strength = 5*(bits & COLUMNS[3]).bit_count()
        for shift in DIRECTIONS:
            pairs = bits & (bits >> shift)
            strength += 3*pairs.bit_count() + 11*(pairs & (bits >> (2*shift))).bit_count()
        return strength
    return value(board[player]) - value(board[1-player])



def winning_targets(bits):
    """Squares that would complete a four, including gaps between pieces."""
    targets = 0
    for shift in DIRECTIONS:
        pairs = bits & (bits >> shift)
        triples = pairs & (bits >> (2 * shift))
        targets |= (triples >> shift) | (triples << (3 * shift))
        targets |= (pairs & (bits >> (3 * shift))) << (2 * shift)
        targets |= (bits & (pairs >> (2 * shift))) << shift
    return targets & BOARD_MASK


def playable_drops(board):
    # Adding at the bottom of each column carries into its lowest empty square.
    return ((board[0] | board[1]) + BOTTOM_ROW) & BOARD_MASK


def open_pairs(bits, opponent):
    available = BOARD_MASK ^ opponent
    total = 0
    for shift in DIRECTIONS:
        open_two = available & (available >> shift)
        open_four = open_two & (open_two >> (2 * shift))
        a, b, c, d = (bits >> (i * shift) for i in range(4))
        pairs = (a & b) | (c & d) | ((a | b) & (c | d))
        total += (open_four & pairs).bit_count()
    return total


def position_value(board, player, plies, allow_remove):
    own, opponent = board[player], board[1-player]
    vacant = BOARD_MASK ^ (own | opponent)
    playable = playable_drops(board)
    our_targets = winning_targets(own) & vacant
    their_targets = winning_targets(opponent) & vacant
    if our_targets & playable:
        return WIN - plies - 1
    their_playable = (their_targets & playable).bit_count()
    if not allow_remove and their_playable > 1:
        return plies + 2 - WIN
    center = (own & COLUMNS[3]).bit_count() - (opponent & COLUMNS[3]).bit_count()
    pairs = open_pairs(own, opponent) - open_pairs(opponent, own)
    return 4 * center + 3 * pairs + 8 * (our_targets.bit_count() - their_targets.bit_count()) - 22 * their_playable


class SearchBudget(Exception):
    pass


def engine_move(game):
    """Check immediate tactics and search more deeply at higher levels."""
    depth_limit, budget = LEVELS[game.difficulty]
    remaining = budget
    repetitions = game.repetitions.copy()
    tactical = game.difficulty != "leicht"

    def grade(board, player, move, depth, plies, alpha, beta):
        following = apply_move(board, player, move)
        won = winner(following, player)
        if won is not None:
            return (WIN-plies) if won == player else (plies-WIN)
        next_player = 1-player
        if not game.allow_remove:
            return -search(following, next_player, depth-1, plies, -beta, -alpha)
        key = (*following, next_player)
        repetitions[key] += 1
        try:
            if repetitions[key] >= 3:
                return 0
            return -search(following, next_player, depth-1, plies, -beta, -alpha)
        finally:
            repetitions[key] -= 1

    def search(board, player, depth, plies, alpha, beta):
        nonlocal remaining
        remaining -= 1
        if remaining < 0:
            raise SearchBudget
        actions = legal_moves(board, player, allow_remove=game.allow_remove)
        if not actions:
            return 0
        if not depth:
            return (position_value(board, player, plies, game.allow_remove) if tactical
                    else simple_position_value(board, player))
        if tactical and not game.allow_remove:
            playable = playable_drops(board)
            if winning_targets(board[player]) & playable:
                return WIN - plies - 1
            threats = winning_targets(board[1-player]) & playable
            if threats:
                if threats.bit_count() > 1:
                    return plies + 2 - WIN
                actions = ((threats.bit_length() - 1) // STRIDE,)
        best = -WIN
        for move in actions:
            best = max(best, grade(board, player, move, depth, plies+1, alpha, beta))
            alpha = max(alpha, best)
            if alpha >= beta:
                break
        return best

    moves = game.moves()
    favorite = moves[0]
    for depth in range(1, depth_limit+1):
        best, candidate = -WIN, favorite
        order = [favorite] + [move for move in moves if move != favorite]
        # Vary equally promising opening replies on the two easier settings.
        if depth == 1 and game.difficulty in ("leicht", "mittel"):
            game.random.shuffle(order)
        try:
            for move in order:
                value = grade(game.board, game.turn, move, depth, 1, best, WIN)
                if value > best:
                    best, candidate = value, move
        except SearchBudget:
            break
        favorite = candidate
        if best >= WIN-depth:
            break
    return favorite
