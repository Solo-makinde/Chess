"""Computer opponent: negamax search with alpha beta pruning."""
from typing import Optional, Tuple

from .board import BLACK, WHITE, Board, Move

PIECE_VALUES = {"P": 100, "N": 320, "B": 330, "R": 500, "Q": 900, "K": 0}
MATE_SCORE = 100_000

# Piece square tables from White's point of view, row 0 = rank 8.
# Values from the Simplified Evaluation Function (Tomasz Michniewski).
PST = {
    "P": [
        [0, 0, 0, 0, 0, 0, 0, 0],
        [50, 50, 50, 50, 50, 50, 50, 50],
        [10, 10, 20, 30, 30, 20, 10, 10],
        [5, 5, 10, 25, 25, 10, 5, 5],
        [0, 0, 0, 20, 20, 0, 0, 0],
        [5, -5, -10, 0, 0, -10, -5, 5],
        [5, 10, 10, -20, -20, 10, 10, 5],
        [0, 0, 0, 0, 0, 0, 0, 0],
    ],
    "N": [
        [-50, -40, -30, -30, -30, -30, -40, -50],
        [-40, -20, 0, 0, 0, 0, -20, -40],
        [-30, 0, 10, 15, 15, 10, 0, -30],
        [-30, 5, 15, 20, 20, 15, 5, -30],
        [-30, 0, 15, 20, 20, 15, 0, -30],
        [-30, 5, 10, 15, 15, 10, 5, -30],
        [-40, -20, 0, 5, 5, 0, -20, -40],
        [-50, -40, -30, -30, -30, -30, -40, -50],
    ],
    "B": [
        [-20, -10, -10, -10, -10, -10, -10, -20],
        [-10, 0, 0, 0, 0, 0, 0, -10],
        [-10, 0, 5, 10, 10, 5, 0, -10],
        [-10, 5, 5, 10, 10, 5, 5, -10],
        [-10, 0, 10, 10, 10, 10, 0, -10],
        [-10, 10, 10, 10, 10, 10, 10, -10],
        [-10, 5, 0, 0, 0, 0, 5, -10],
        [-20, -10, -10, -10, -10, -10, -10, -20],
    ],
    "R": [
        [0, 0, 0, 0, 0, 0, 0, 0],
        [5, 10, 10, 10, 10, 10, 10, 5],
        [-5, 0, 0, 0, 0, 0, 0, -5],
        [-5, 0, 0, 0, 0, 0, 0, -5],
        [-5, 0, 0, 0, 0, 0, 0, -5],
        [-5, 0, 0, 0, 0, 0, 0, -5],
        [-5, 0, 0, 0, 0, 0, 0, -5],
        [0, 0, 0, 5, 5, 0, 0, 0],
    ],
    "Q": [
        [-20, -10, -10, -5, -5, -10, -10, -20],
        [-10, 0, 0, 0, 0, 0, 0, -10],
        [-10, 0, 5, 5, 5, 5, 0, -10],
        [-5, 0, 5, 5, 5, 5, 0, -5],
        [0, 0, 5, 5, 5, 5, 0, -5],
        [-10, 5, 5, 5, 5, 5, 0, -10],
        [-10, 0, 5, 0, 0, 0, 0, -10],
        [-20, -10, -10, -5, -5, -10, -10, -20],
    ],
    "K": [
        [-30, -40, -40, -50, -50, -40, -40, -30],
        [-30, -40, -40, -50, -50, -40, -40, -30],
        [-30, -40, -40, -50, -50, -40, -40, -30],
        [-30, -40, -40, -50, -50, -40, -40, -30],
        [-20, -30, -30, -40, -40, -30, -30, -20],
        [-10, -20, -20, -20, -20, -20, -20, -10],
        [20, 20, 0, 0, 0, 0, 20, 20],
        [20, 30, 10, 0, 0, 10, 30, 20],
    ],
}


def evaluate(board: Board) -> int:
    """Score from White's point of view, in centipawns."""
    score = 0
    for r in range(8):
        for c in range(8):
            v = board.board[r][c]
            if v == ".":
                continue
            color, p = v
            if color == WHITE:
                score += PIECE_VALUES[p] + PST[p][r][c]
            else:
                score -= PIECE_VALUES[p] + PST[p][7 - r][c]
    return score


def _order(board: Board, moves):
    """Search captures and promotions first (most valuable victim, least valuable attacker)."""
    def key(mv: Move):
        victim = board.board[mv.to[0]][mv.to[1]]
        attacker = board.board[mv.fr[0]][mv.fr[1]]
        s = 0
        if victim != ".":
            s += 10 * PIECE_VALUES[victim[1]] - PIECE_VALUES[attacker[1]]
        if mv.promotion:
            s += PIECE_VALUES[mv.promotion]
        return -s
    return sorted(moves, key=key)


class AI:
    def __init__(self, depth: int = 3):
        self.depth = depth
        self.nodes = 0

    def best_move(self, board: Board) -> Tuple[Optional[Move], int]:
        """Return (move, score from the side to move's view)."""
        self.nodes = 0
        best, best_score = None, -MATE_SCORE - 1
        alpha, beta = -MATE_SCORE - 1, MATE_SCORE + 1
        for mv in _order(board, board.legal_moves()):
            board._apply(mv)
            score = -self._negamax(board, self.depth - 1, -beta, -alpha, 1)
            board._revert()
            if score > best_score:
                best, best_score = mv, score
            alpha = max(alpha, score)
        return best, best_score

    def _negamax(self, board: Board, depth: int, alpha: int, beta: int, ply: int) -> int:
        self.nodes += 1
        moves = board.legal_moves()
        if not moves:
            # Prefer faster mates and slower losses
            return -(MATE_SCORE - ply) if board.in_check(board.turn) else 0
        if board.halfmove_clock >= 100 or board.is_insufficient_material():
            return 0
        if depth == 0:
            return self._quiesce(board, alpha, beta, 0)
        for mv in _order(board, moves):
            board._apply(mv)
            score = -self._negamax(board, depth - 1, -beta, -alpha, ply + 1)
            board._revert()
            if score >= beta:
                return beta
            alpha = max(alpha, score)
        return alpha

    def _quiesce(self, board: Board, alpha: int, beta: int, qdepth: int) -> int:
        """Keep searching captures so the engine does not stop in the middle of a trade."""
        self.nodes += 1
        stand = evaluate(board) * (1 if board.turn == WHITE else -1)
        if stand >= beta or qdepth >= 4:
            return stand
        alpha = max(alpha, stand)
        captures = [m for m in board.legal_moves()
                    if board.board[m.to[0]][m.to[1]] != "." or m.is_en_passant or m.promotion]
        for mv in _order(board, captures):
            board._apply(mv)
            score = -self._quiesce(board, -beta, -alpha, qdepth + 1)
            board._revert()
            if score >= beta:
                return beta
            alpha = max(alpha, score)
        return alpha


def choose_move(board: Board, depth: int = 3) -> Optional[Move]:
    mv, _ = AI(depth).best_move(board)
    return mv
