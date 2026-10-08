"""Chess rules engine: board state, legal move generation, draw rules, undo."""
from dataclasses import dataclass
from typing import List, Optional, Tuple

WHITE, BLACK = "w", "b"
FILES = "abcdefgh"
RANKS = "12345678"
START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

KNIGHT_STEPS = [(-2, -1), (-2, 1), (-1, -2), (-1, 2), (1, -2), (1, 2), (2, -1), (2, 1)]
KING_STEPS = [(dr, dc) for dr in (-1, 0, 1) for dc in (-1, 0, 1) if (dr, dc) != (0, 0)]
DIAGONALS = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
STRAIGHTS = [(-1, 0), (1, 0), (0, -1), (0, 1)]


def opponent(color: str) -> str:
    return BLACK if color == WHITE else WHITE


def in_bounds(r: int, c: int) -> bool:
    return 0 <= r < 8 and 0 <= c < 8


def square_name(r: int, c: int) -> str:
    """Row 0 is rank 8, column 0 is file a."""
    return FILES[c] + str(8 - r)


@dataclass
class Move:
    fr: Tuple[int, int]
    to: Tuple[int, int]
    promotion: Optional[str] = None
    is_castle: bool = False
    is_en_passant: bool = False

    def uci(self) -> str:
        s = square_name(*self.fr) + square_name(*self.to)
        return s + (self.promotion.lower() if self.promotion else "")


class Board:
    def __init__(self, fen: str = START_FEN):
        self.board: List[List] = [["."] * 8 for _ in range(8)]
        self.turn = WHITE
        self.castling = {"wK": False, "wQ": False, "bK": False, "bQ": False}
        self.en_passant: Optional[Tuple[int, int]] = None
        self.halfmove_clock = 0
        self.fullmove = 1
        self.move_log: List[Move] = []
        self._undo_stack = []
        self._positions: List[tuple] = []
        self.load_fen(fen)

    # ---------- setup ----------
    def load_fen(self, fen: str) -> None:
        parts = fen.split()
        rows = parts[0].split("/")
        for r, row in enumerate(rows):
            c = 0
            for ch in row:
                if ch.isdigit():
                    for _ in range(int(ch)):
                        self.board[r][c] = "."
                        c += 1
                else:
                    color = WHITE if ch.isupper() else BLACK
                    self.board[r][c] = (color, ch.upper())
                    c += 1
        self.turn = parts[1] if len(parts) > 1 else WHITE
        rights = parts[2] if len(parts) > 2 else "-"
        self.castling = {"wK": "K" in rights, "wQ": "Q" in rights,
                         "bK": "k" in rights, "bQ": "q" in rights}
        ep = parts[3] if len(parts) > 3 else "-"
        self.en_passant = None if ep == "-" else (8 - int(ep[1]), FILES.index(ep[0]))
        self.halfmove_clock = int(parts[4]) if len(parts) > 4 else 0
        self.fullmove = int(parts[5]) if len(parts) > 5 else 1
        self.move_log.clear()
        self._undo_stack.clear()
        self._positions = [self.position_key()]

    def position_key(self) -> tuple:
        return (tuple(tuple(row) for row in self.board), self.turn,
                tuple(sorted(k for k, v in self.castling.items() if v)), self.en_passant)

    # ---------- queries ----------
    def piece(self, r, c):
        v = self.board[r][c]
        return None if v == "." else v

    def color_at(self, r, c):
        v = self.board[r][c]
        return None if v == "." else v[0]

    def king_pos(self, color):
        target = (color, "K")
        for r in range(8):
            for c in range(8):
                if self.board[r][c] == target:
                    return (r, c)
        return None

    def is_attacked(self, r, c, by_color) -> bool:
        b = self.board
        # A white pawn attacks diagonally upward (toward row 0), so it sits one row BELOW the target.
        pr = r + 1 if by_color == WHITE else r - 1
        for dc in (-1, 1):
            if in_bounds(pr, c + dc) and b[pr][c + dc] == (by_color, "P"):
                return True
        for dr, dc in KNIGHT_STEPS:
            rr, cc = r + dr, c + dc
            if in_bounds(rr, cc) and b[rr][cc] == (by_color, "N"):
                return True
        for dirs, sliders in ((DIAGONALS, ("B", "Q")), (STRAIGHTS, ("R", "Q"))):
            for dr, dc in dirs:
                rr, cc = r + dr, c + dc
                while in_bounds(rr, cc):
                    v = b[rr][cc]
                    if v != ".":
                        if v[0] == by_color and v[1] in sliders:
                            return True
                        break
                    rr += dr
                    cc += dc
        for dr, dc in KING_STEPS:
            rr, cc = r + dr, c + dc
            if in_bounds(rr, cc) and b[rr][cc] == (by_color, "K"):
                return True
        return False

    def in_check(self, color) -> bool:
        pos = self.king_pos(color)
        return pos is not None and self.is_attacked(pos[0], pos[1], opponent(color))

    # ---------- move generation ----------
    def generate_pseudo(self, color) -> List[Move]:
        moves = []
        b = self.board
        for r in range(8):
            for c in range(8):
                v = b[r][c]
                if v == "." or v[0] != color:
                    continue
                p = v[1]
                if p == "P":
                    self._pawn_moves(r, c, color, moves)
                elif p == "N":
                    for dr, dc in KNIGHT_STEPS:
                        rr, cc = r + dr, c + dc
                        if in_bounds(rr, cc) and self.color_at(rr, cc) != color:
                            moves.append(Move((r, c), (rr, cc)))
                elif p in ("B", "R", "Q"):
                    dirs = []
                    if p in ("B", "Q"):
                        dirs += DIAGONALS
                    if p in ("R", "Q"):
                        dirs += STRAIGHTS
                    for dr, dc in dirs:
                        rr, cc = r + dr, c + dc
                        while in_bounds(rr, cc):
                            if b[rr][cc] == ".":
                                moves.append(Move((r, c), (rr, cc)))
                            else:
                                if b[rr][cc][0] != color:
                                    moves.append(Move((r, c), (rr, cc)))
                                break
                            rr += dr
                            cc += dc
                elif p == "K":
                    for dr, dc in KING_STEPS:
                        rr, cc = r + dr, c + dc
                        if in_bounds(rr, cc) and self.color_at(rr, cc) != color:
                            moves.append(Move((r, c), (rr, cc)))
                    self._castle_moves(color, moves)
        return moves

    def _pawn_moves(self, r, c, color, moves):
        b = self.board
        d = -1 if color == WHITE else 1
        start_row = 6 if color == WHITE else 1
        rr = r + d

        def add(to):
            if to[0] in (0, 7):
                for promo in "QRBN":
                    moves.append(Move((r, c), to, promotion=promo))
            else:
                moves.append(Move((r, c), to))

        if in_bounds(rr, c) and b[rr][c] == ".":
            add((rr, c))
            if r == start_row and b[r + 2 * d][c] == ".":
                moves.append(Move((r, c), (r + 2 * d, c)))
        for dc in (-1, 1):
            cc = c + dc
            if not in_bounds(rr, cc):
                continue
            if b[rr][cc] != "." and b[rr][cc][0] != color:
                add((rr, cc))
            elif self.en_passant == (rr, cc):
                moves.append(Move((r, c), (rr, cc), is_en_passant=True))

    def _castle_moves(self, color, moves):
        row = 7 if color == WHITE else 0
        enemy = opponent(color)
        b = self.board
        if b[row][4] != (color, "K") or self.is_attacked(row, 4, enemy):
            return
        if (self.castling[color + "K"] and b[row][7] == (color, "R")
                and b[row][5] == "." and b[row][6] == "."
                and not self.is_attacked(row, 5, enemy) and not self.is_attacked(row, 6, enemy)):
            moves.append(Move((row, 4), (row, 6), is_castle=True))
        if (self.castling[color + "Q"] and b[row][0] == (color, "R")
                and b[row][1] == "." and b[row][2] == "." and b[row][3] == "."
                and not self.is_attacked(row, 3, enemy) and not self.is_attacked(row, 2, enemy)):
            moves.append(Move((row, 4), (row, 2), is_castle=True))

    def legal_moves(self, color=None) -> List[Move]:
        color = color or self.turn
        out = []
        for mv in self.generate_pseudo(color):
            self._apply(mv)
            if not self.in_check(color):
                out.append(mv)
            self._revert()
        return out

    # ---------- making and undoing moves ----------
    def _apply(self, mv: Move) -> None:
        """Make a move without touching the repetition history (fast path for search)."""
        self._undo_stack.append(([row[:] for row in self.board], self.turn, self.castling.copy(),
                                 self.en_passant, self.halfmove_clock, self.fullmove))
        b = self.board
        fr, fc = mv.fr
        tr, tc = mv.to
        piece = b[fr][fc]
        color, p = piece
        captured = b[tr][tc] != "." or mv.is_en_passant
        self.en_passant = None

        if p == "K":
            self.castling[color + "K"] = self.castling[color + "Q"] = False
        for sq, right in (((7, 0), "wQ"), ((7, 7), "wK"), ((0, 0), "bQ"), ((0, 7), "bK")):
            if (fr, fc) == sq or (tr, tc) == sq:
                self.castling[right] = False

        if mv.is_en_passant:
            b[tr + (1 if color == WHITE else -1)][tc] = "."
        b[fr][fc] = "."
        b[tr][tc] = (color, mv.promotion or "Q") if (p == "P" and tr in (0, 7)) else piece

        if mv.is_castle:
            if tc == 6:
                b[tr][5], b[tr][7] = b[tr][7], "."
            else:
                b[tr][3], b[tr][0] = b[tr][0], "."

        if p == "P" and abs(tr - fr) == 2:
            self.en_passant = ((tr + fr) // 2, fc)

        self.halfmove_clock = 0 if (p == "P" or captured) else self.halfmove_clock + 1
        if color == BLACK:
            self.fullmove += 1
        self.turn = opponent(self.turn)

    def _revert(self) -> None:
        (self.board, self.turn, self.castling, self.en_passant,
         self.halfmove_clock, self.fullmove) = self._undo_stack.pop()

    def make_move(self, mv: Move) -> None:
        self._apply(mv)
        self.move_log.append(mv)
        self._positions.append(self.position_key())

    def undo(self) -> Optional[Move]:
        if not self.move_log:
            return None
        self._revert()
        self._positions.pop()
        return self.move_log.pop()

    # ---------- game result ----------
    def is_threefold(self) -> bool:
        return self._positions.count(self._positions[-1]) >= 3

    def is_fifty_move(self) -> bool:
        return self.halfmove_clock >= 100

    def is_insufficient_material(self) -> bool:
        minors = []
        for r in range(8):
            for c in range(8):
                v = self.board[r][c]
                if v == "." or v[1] == "K":
                    continue
                if v[1] in ("P", "R", "Q"):
                    return False
                minors.append((v, (r + c) % 2))
        if len(minors) <= 1:
            return True
        # Only bishops left, all on the same color squares
        return all(m[0][1] == "B" for m in minors) and len({m[1] for m in minors}) == 1

    def result(self) -> Optional[str]:
        """None if the game continues, otherwise a short description."""
        if not self.legal_moves(self.turn):
            if self.in_check(self.turn):
                winner = "White" if self.turn == BLACK else "Black"
                return f"Checkmate. {winner} wins."
            return "Draw by stalemate."
        if self.is_insufficient_material():
            return "Draw by insufficient material."
        if self.is_fifty_move():
            return "Draw by the fifty move rule."
        if self.is_threefold():
            return "Draw by threefold repetition."
        return None

    # ---------- notation ----------
    def san(self, mv: Move) -> str:
        """Standard algebraic notation for a legal move in the current position."""
        if mv.is_castle:
            s = "O-O" if mv.to[1] == 6 else "O-O-O"
        else:
            color, p = self.board[mv.fr[0]][mv.fr[1]]
            capture = self.board[mv.to[0]][mv.to[1]] != "." or mv.is_en_passant
            dest = square_name(*mv.to)
            if p == "P":
                s = (FILES[mv.fr[1]] + "x" if capture else "") + dest
                if mv.promotion:
                    s += "=" + mv.promotion
            else:
                rivals = [m for m in self.legal_moves() if m.to == mv.to and m.fr != mv.fr
                          and self.board[m.fr[0]][m.fr[1]] == (color, p)]
                dis = ""
                if rivals:
                    if all(m.fr[1] != mv.fr[1] for m in rivals):
                        dis = FILES[mv.fr[1]]
                    elif all(m.fr[0] != mv.fr[0] for m in rivals):
                        dis = str(8 - mv.fr[0])
                    else:
                        dis = square_name(*mv.fr)
                s = p + dis + ("x" if capture else "") + dest
        self._apply(mv)
        if self.in_check(self.turn):
            s += "#" if not self.legal_moves(self.turn) else "+"
        self._revert()
        return s


def perft(board: Board, depth: int) -> int:
    """Count leaf nodes of the legal move tree. Used to verify move generation."""
    moves = board.legal_moves()
    if depth == 1:
        return len(moves)
    total = 0
    for mv in moves:
        board._apply(mv)
        total += perft(board, depth - 1)
        board._revert()
    return total
