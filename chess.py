#!/usr/bin/env python3
import tkinter as tk
from dataclasses import dataclass
from typing import Optional, Tuple, List

WHITE, BLACK = "w", "b"
FILES = "abcdefgh"
RANKS = "12345678"

UNICODE = {
    ("w","K"): "♔", ("w","Q"): "♕", ("w","R"): "♖", ("w","B"): "♗", ("w","N"): "♘", ("w","P"): "♙",
    ("b","K"): "♚", ("b","Q"): "♛", ("b","R"): "♜", ("b","B"): "♝", ("b","N"): "♞", ("b","P"): "♟",
}

@dataclass
class Move:
    fr: Tuple[int, int]
    to: Tuple[int, int]
    promotion: Optional[str] = None
    is_castle: bool = False
    is_en_passant: bool = False

def in_bounds(r, c): return 0 <= r < 8 and 0 <= c < 8

class Board:
    def __init__(self):
        self.board = [["." for _ in range(8)] for _ in range(8)]
        self.turn = WHITE
        self.castling = {"wK": True, "wQ": True, "bK": True, "bQ": True}
        self.en_passant: Optional[Tuple[int, int]] = None
        self._setup()

    def _setup(self):
        back = ["R","N","B","Q","K","B","N","R"]
        for i,p in enumerate(back):
            self.board[7][i] = ("w", p)
            self.board[0][i] = ("b", p)
        for i in range(8):
            self.board[6][i] = ("w","P")
            self.board[1][i] = ("b","P")

    def clone(self):
        b = Board()
        b.board = [row[:] for row in self.board]
        b.turn = self.turn
        b.castling = self.castling.copy()
        b.en_passant = self.en_passant
        return b

    def piece(self, r, c):
        v = self.board[r][c]
        return None if v == "." else v

    def color_at(self, r, c):
        v = self.piece(r,c)
        return v[0] if v else None

    def king_pos(self, color):
        for r in range(8):
            for c in range(8):
                if self.board[r][c] != "." and self.board[r][c] == (color,"K"):
                    return (r,c)
        return None

    def is_attacked(self, r, c, by_color):
        dr = -1 if by_color == WHITE else 1
        for dc in (-1,1):
            rr, cc = r+dr, c+dc
            if in_bounds(rr,cc) and self.board[rr][cc] == (by_color,"P"):
                return True
        for dr,dc in [(-2,-1),(-2,1),(-1,-2),(-1,2),(1,-2),(1,2),(2,-1),(2,1)]:
            rr,cc = r+dr, c+dc
            if in_bounds(rr,cc) and self.board[rr][cc] == (by_color,"N"):
                return True
        for dr,dc in [(-1,-1),(-1,1),(1,-1),(1,1)]:
            rr,cc = r+dr, c+dc
            while in_bounds(rr,cc):
                v = self.board[rr][cc]
                if v != ".":
                    if v in ((by_color,"B"),(by_color,"Q")): return True
                    break
                rr += dr; cc += dc
        for dr,dc in [(-1,0),(1,0),(0,-1),(0,1)]:
            rr,cc = r+dr, c+dc
            while in_bounds(rr,cc):
                v = self.board[rr][cc]
                if v != ".":
                    if v in ((by_color,"R"),(by_color,"Q")): return True
                    break
                rr += dr; cc += dc
        for dr in (-1,0,1):
            for dc in (-1,0,1):
                if dr==0 and dc==0: continue
                rr,cc = r+dr, c+dc
                if in_bounds(rr,cc) and self.board[rr][cc] == (by_color,"K"):
                    return True
        return False

    def in_check(self, color):
        kr,kc = self.king_pos(color)
        return self.is_attacked(kr,kc, WHITE if color==BLACK else BLACK)

    def generate_pseudo(self, color):
        moves = []
        for r in range(8):
            for c in range(8):
                if self.color_at(r,c) != color: continue
                _, p = self.board[r][c]
                if p == "P":
                    dir = -1 if color==WHITE else 1
                    rr = r+dir
                    if in_bounds(rr,c) and self.board[rr][c] == ".":
                        if rr in (0,7):
                            for promo in ["Q","R","B","N"]:
                                moves.append(Move((r,c),(rr,c),promotion=promo))
                        else:
                            moves.append(Move((r,c),(rr,c)))
                        rr2 = r + 2*dir
                        if (r==6 and color==WHITE) or (r==1 and color==BLACK):
                            if self.board[rr2][c] == ".":
                                moves.append(Move((r,c),(rr2,c)))
                    for dc in (-1,1):
                        cc = c+dc
                        rr = r+dir
                        if in_bounds(rr,cc) and self.board[rr][cc] != "." and self.color_at(rr,cc) != color:
                            if rr in (0,7):
                                for promo in ["Q","R","B","N"]:
                                    moves.append(Move((r,c),(rr,cc),promotion=promo))
                            else:
                                moves.append(Move((r,c),(rr,cc)))
                    if self.en_passant:
                        er,ec = self.en_passant
                        if er == r+dir and abs(ec-c)==1:
                            moves.append(Move((r,c),(er,ec),is_en_passant=True))
                elif p == "N":
                    for dr,dc in [(-2,-1),(-2,1),(-1,-2),(-1,2),(1,-2),(1,2),(2,-1),(2,1)]:
                        rr,cc = r+dr, c+dc
                        if in_bounds(rr,cc) and self.color_at(rr,cc) != color:
                            moves.append(Move((r,c),(rr,cc)))
                elif p in ("B","R","Q"):
                    dirs = []
                    if p in ("B","Q"): dirs += [(-1,-1),(-1,1),(1,-1),(1,1)]
                    if p in ("R","Q"): dirs += [(-1,0),(1,0),(0,-1),(0,1)]
                    for dr,dc in dirs:
                        rr,cc = r+dr, c+dc
                        while in_bounds(rr,cc):
                            if self.board[rr][cc] == ".":
                                moves.append(Move((r,c),(rr,cc)))
                            else:
                                if self.color_at(rr,cc) != color:
                                    moves.append(Move((r,c),(rr,cc)))
                                break
                            rr += dr; cc += dc
                elif p == "K":
                    for dr in (-1,0,1):
                        for dc in (-1,0,1):
                            if dr==0 and dc==0: continue
                            rr,cc = r+dr, c+dc
                            if in_bounds(rr,cc) and self.color_at(rr,cc) != color:
                                moves.append(Move((r,c),(rr,cc)))
                    if not self.in_check(color):
                        if color==WHITE:
                            if self.castling["wK"] and self.board[7][5]=="." and self.board[7][6]==".":
                                if not self.is_attacked(7,5,BLACK) and not self.is_attacked(7,6,BLACK):
                                    moves.append(Move((7,4),(7,6),is_castle=True))
                            if self.castling["wQ"] and self.board[7][1]=="." and self.board[7][2]=="." and self.board[7][3]==".":
                                if not self.is_attacked(7,3,BLACK) and not self.is_attacked(7,2,BLACK):
                                    moves.append(Move((7,4),(7,2),is_castle=True))
                        else:
                            if self.castling["bK"] and self.board[0][5]=="." and self.board[0][6]==".":
                                if not self.is_attacked(0,5,WHITE) and not self.is_attacked(0,6,WHITE):
                                    moves.append(Move((0,4),(0,6),is_castle=True))
                            if self.castling["bQ"] and self.board[0][1]=="." and self.board[0][2]=="." and self.board[0][3]==".":
                                if not self.is_attacked(0,3,WHITE) and not self.is_attacked(0,2,WHITE):
                                    moves.append(Move((0,4),(0,2),is_castle=True))
        return moves

    def legal_moves(self, color):
        out = []
        for mv in self.generate_pseudo(color):
            b = self.clone()
            b.make_move(mv)
            if not b.in_check(color):
                out.append(mv)
        return out

    def make_move(self, mv: Move):
        fr,fc = mv.fr; tr,tc = mv.to
        piece = self.board[fr][fc]
        color, p = piece
        captured = self.board[tr][tc] != "."
        self.en_passant = None

        if p == "K":
            if color==WHITE: self.castling["wK"]=self.castling["wQ"]=False
            else: self.castling["bK"]=self.castling["bQ"]=False
        if p == "R":
            if (fr,fc)==(7,0): self.castling["wQ"]=False
            if (fr,fc)==(7,7): self.castling["wK"]=False
            if (fr,fc)==(0,0): self.castling["bQ"]=False
            if (fr,fc)==(0,7): self.castling["bK"]=False
        if captured:
            if (tr,tc)==(7,0): self.castling["wQ"]=False
            if (tr,tc)==(7,7): self.castling["wK"]=False
            if (tr,tc)==(0,0): self.castling["bQ"]=False
            if (tr,tc)==(0,7): self.castling["bK"]=False

        if mv.is_en_passant:
            cap_r = tr + (1 if color==WHITE else -1)
            self.board[cap_r][tc] = "."

        self.board[fr][fc] = "."
        self.board[tr][tc] = piece

        if p == "P" and tr in (0,7):
            promo = mv.promotion or "Q"
            self.board[tr][tc] = (color, promo)

        if mv.is_castle:
            if (tr,tc)==(7,6):
                self.board[7][5] = self.board[7][7]; self.board[7][7]="."
            elif (tr,tc)==(7,2):
                self.board[7][3] = self.board[7][0]; self.board[7][0]="."
            elif (tr,tc)==(0,6):
                self.board[0][5] = self.board[0][7]; self.board[0][7]="."
            elif (tr,tc)==(0,2):
                self.board[0][3] = self.board[0][0]; self.board[0][0]="."

        if p == "P" and abs(tr-fr)==2:
            self.en_passant = ((tr+fr)//2, fc)

        self.turn = WHITE if self.turn==BLACK else BLACK

class ChessGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Chess")
        self.b = Board()
        self.selected = None
        self.legal = []
        self.info = tk.StringVar()
        self.canvas = tk.Canvas(root, width=520, height=560, bg="#222")
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self.on_click)
        self.draw()

    def draw(self):
        self.canvas.delete("all")
        size = 60
        offset = 40
        for r in range(8):
            for c in range(8):
                x1 = offset + c*size
                y1 = offset + r*size
                x2 = x1 + size
                y2 = y1 + size
                color = "#f0d9b5" if (r+c)%2==0 else "#b58863"
                self.canvas.create_rectangle(x1,y1,x2,y2, fill=color, outline="")
        # highlights
        for mv in self.legal:
            r,c = mv.to
            x = offset + c*size + size//2
            y = offset + r*size + size//2
            self.canvas.create_oval(x-8,y-8,x+8,y+8, fill="#00b050", outline="")
        # pieces
        for r in range(8):
            for c in range(8):
                p = self.b.piece(r,c)
                if p:
                    x = offset + c*size + size//2
                    y = offset + r*size + size//2
                    self.canvas.create_text(x,y, text=UNICODE[p], font=("Segoe UI Symbol", 36))
        # labels
        for i,f in enumerate(FILES):
            self.canvas.create_text(offset + i*size + size//2, offset-15, text=f, fill="#ddd")
        for i,rk in enumerate(reversed(RANKS)):
            self.canvas.create_text(offset-15, offset + i*size + size//2, text=rk, fill="#ddd")

        status = f"{'White' if self.b.turn==WHITE else 'Black'} to move"
        if self.b.in_check(self.b.turn):
            status += " - Check"
        self.canvas.create_text(260, 520, text=status, fill="#ddd", font=("Segoe UI", 12))

    def on_click(self, event):
        size = 60; offset = 40
        c = (event.x - offset) // size
        r = (event.y - offset) // size
        if not in_bounds(r,c): return
        if self.selected is None:
            if self.b.color_at(r,c) == self.b.turn:
                self.selected = (r,c)
                self.legal = [m for m in self.b.legal_moves(self.b.turn) if m.fr == self.selected]
        else:
            target = (r,c)
            chosen = None
            for m in self.b.legal_moves(self.b.turn):
                if m.fr == self.selected and m.to == target:
                    chosen = m
                    break
            if chosen:
                if chosen.promotion:
                    chosen.promotion = self.ask_promo()
                self.b.make_move(chosen)
            self.selected = None
            self.legal = []
        self.draw()
        self.check_game_over()

    def ask_promo(self):
        win = tk.Toplevel(self.root)
        win.title("Promote to")
        choice = tk.StringVar(value="Q")
        for p in ["Q","R","B","N"]:
            tk.Radiobutton(win, text=p, variable=choice, value=p).pack(anchor="w")
        tk.Button(win, text="OK", command=win.destroy).pack()
        win.grab_set()
        self.root.wait_window(win)
        return choice.get()

    def check_game_over(self):
        legal = self.b.legal_moves(self.b.turn)
        if legal:
            return
        msg = "Checkmate." if self.b.in_check(self.b.turn) else "Stalemate."
        win = tk.Toplevel(self.root)
        win.title("Game Over")
        tk.Label(win, text=msg).pack(padx=20, pady=10)
        tk.Button(win, text="Close", command=self.root.destroy).pack(pady=10)

def main():
    root = tk.Tk()
    ChessGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
