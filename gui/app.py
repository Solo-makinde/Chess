"""Tkinter interface: click to move, play against a friend or the computer."""
import copy
import threading
import tkinter as tk
from typing import Optional

from engine import BLACK, WHITE, Board, Move, choose_move
from engine.board import FILES

UNICODE = {
    ("w", "K"): "♔", ("w", "Q"): "♕", ("w", "R"): "♖",
    ("w", "B"): "♗", ("w", "N"): "♘", ("w", "P"): "♙",
    ("b", "K"): "♚", ("b", "Q"): "♛", ("b", "R"): "♜",
    ("b", "B"): "♝", ("b", "N"): "♞", ("b", "P"): "♟",
}

SIZE = 60
OFFSET = 40
LIGHT, DARK = "#f0d9b5", "#b58863"
LAST_MOVE = "#cdd26a"
SELECTED = "#7fa650"
CHECK = "#e05050"


class ChessGUI:
    def __init__(self, root: tk.Tk, ai_color: Optional[str] = None, depth: int = 3):
        self.root = root
        self.root.title("Chess")
        self.b = Board()
        self.ai_color = ai_color
        self.depth = depth
        self.flipped = ai_color == WHITE  # human plays Black, so show Black at the bottom
        self.selected = None
        self.legal = []
        self.san_log = []
        self.game_over = False
        self.thinking = False

        frame = tk.Frame(root, bg="#222")
        frame.pack()
        self.canvas = tk.Canvas(frame, width=SIZE * 8 + OFFSET * 2, height=SIZE * 8 + OFFSET * 2,
                                bg="#222", highlightthickness=0)
        self.canvas.grid(row=0, column=0)
        self.canvas.bind("<Button-1>", self.on_click)

        side = tk.Frame(frame, bg="#222")
        side.grid(row=0, column=1, sticky="ns", padx=(0, 12), pady=OFFSET)
        self.status = tk.Label(side, text="", fg="#ddd", bg="#222", font=("Segoe UI", 12, "bold"),
                               width=22, anchor="w")
        self.status.pack(anchor="w")
        self.moves = tk.Text(side, width=24, height=20, bg="#2b2b2b", fg="#ddd", relief="flat",
                             font=("Consolas", 11), state="disabled")
        self.moves.pack(pady=8)
        btns = tk.Frame(side, bg="#222")
        btns.pack(anchor="w")
        tk.Button(btns, text="Undo", command=self.undo).pack(side="left", padx=(0, 6))
        tk.Button(btns, text="New game", command=self.new_game).pack(side="left")
        root.bind("u", lambda e: self.undo())
        root.bind("n", lambda e: self.new_game())

        self.draw()
        self.maybe_ai_move()

    # ---------- coordinates ----------
    def to_screen(self, r, c):
        if self.flipped:
            r, c = 7 - r, 7 - c
        return OFFSET + c * SIZE, OFFSET + r * SIZE

    def to_square(self, x, y):
        c, r = (x - OFFSET) // SIZE, (y - OFFSET) // SIZE
        if self.flipped:
            r, c = 7 - r, 7 - c
        return r, c

    # ---------- drawing ----------
    def draw(self):
        cv = self.canvas
        cv.delete("all")
        last = self.b.move_log[-1] if self.b.move_log else None
        king_in_check = self.b.king_pos(self.b.turn) if self.b.in_check(self.b.turn) else None

        for r in range(8):
            for c in range(8):
                x, y = self.to_screen(r, c)
                color = LIGHT if (r + c) % 2 == 0 else DARK
                if last and (r, c) in (last.fr, last.to):
                    color = LAST_MOVE
                if self.selected == (r, c):
                    color = SELECTED
                if king_in_check == (r, c):
                    color = CHECK
                cv.create_rectangle(x, y, x + SIZE, y + SIZE, fill=color, outline="")

        for mv in self.legal:
            x, y = self.to_screen(*mv.to)
            cx, cy = x + SIZE // 2, y + SIZE // 2
            if self.b.piece(*mv.to):
                cv.create_oval(x + 3, y + 3, x + SIZE - 3, y + SIZE - 3, outline="#2e7d32", width=3)
            else:
                cv.create_oval(cx - 8, cy - 8, cx + 8, cy + 8, fill="#2e7d32", outline="")

        for r in range(8):
            for c in range(8):
                p = self.b.piece(r, c)
                if p:
                    x, y = self.to_screen(r, c)
                    cv.create_text(x + SIZE // 2, y + SIZE // 2, text=UNICODE[p],
                                   font=("Segoe UI Symbol", 36))

        for i in range(8):
            f = FILES[7 - i] if self.flipped else FILES[i]
            rank = str(i + 1) if self.flipped else str(8 - i)
            cv.create_text(OFFSET + i * SIZE + SIZE // 2, OFFSET + 8 * SIZE + 15, text=f, fill="#ddd")
            cv.create_text(OFFSET - 15, OFFSET + i * SIZE + SIZE // 2, text=rank, fill="#ddd")

        self.update_status()
        self.update_move_list()

    def update_status(self):
        if self.game_over:
            text = self.b.result()
        elif self.thinking:
            text = "Computer is thinking..."
        else:
            text = f"{'White' if self.b.turn == WHITE else 'Black'} to move"
            if self.b.in_check(self.b.turn):
                text += ", check"
        self.status.config(text=text)

    def update_move_list(self):
        lines = []
        for i in range(0, len(self.san_log), 2):
            pair = self.san_log[i:i + 2]
            lines.append(f"{i // 2 + 1:>3}. {pair[0]:<8}{pair[1] if len(pair) > 1 else ''}")
        self.moves.config(state="normal")
        self.moves.delete("1.0", "end")
        self.moves.insert("end", "\n".join(lines))
        self.moves.see("end")
        self.moves.config(state="disabled")

    # ---------- input ----------
    def on_click(self, event):
        if self.game_over or self.thinking or self.b.turn == self.ai_color:
            return
        r, c = self.to_square(event.x, event.y)
        if not (0 <= r < 8 and 0 <= c < 8):
            return

        if self.selected is not None:
            chosen = next((m for m in self.legal if m.to == (r, c)), None)
            if chosen:
                if chosen.promotion:
                    chosen.promotion = self.ask_promo()
                self.play(chosen)
                return
        # Select (or switch to) one of your own pieces; clicking elsewhere clears the selection
        if self.b.color_at(r, c) == self.b.turn and self.selected != (r, c):
            self.selected = (r, c)
            self.legal = [m for m in self.b.legal_moves() if m.fr == (r, c)]
        else:
            self.selected = None
            self.legal = []
        self.draw()

    def ask_promo(self) -> str:
        win = tk.Toplevel(self.root)
        win.title("Promote to")
        choice = tk.StringVar(value="Q")
        for p, name in (("Q", "Queen"), ("R", "Rook"), ("B", "Bishop"), ("N", "Knight")):
            tk.Radiobutton(win, text=name, variable=choice, value=p).pack(anchor="w", padx=12)
        tk.Button(win, text="OK", command=win.destroy).pack(pady=6)
        win.transient(self.root)
        win.grab_set()
        self.root.wait_window(win)
        return choice.get()

    # ---------- game flow ----------
    def play(self, mv: Move):
        self.san_log.append(self.b.san(mv))
        self.b.make_move(mv)
        self.selected = None
        self.legal = []
        self.game_over = self.b.result() is not None
        self.draw()
        self.maybe_ai_move()

    def maybe_ai_move(self):
        if self.game_over or self.ai_color != self.b.turn:
            return
        self.thinking = True
        self.update_status()
        snapshot = copy.deepcopy(self.b)  # search on a copy so drawing never sees half made moves
        result = {}

        def worker():
            result["move"] = choose_move(snapshot, self.depth)

        t = threading.Thread(target=worker, daemon=True)
        t.start()
        self.root.after(50, self._poll_ai, t, result)

    def _poll_ai(self, thread, result):
        if thread.is_alive():
            self.root.after(50, self._poll_ai, thread, result)
            return
        self.thinking = False
        mv = result.get("move")
        if mv is not None and not self.game_over:
            self.play(mv)

    def undo(self):
        if self.thinking or not self.b.move_log:
            return
        # Against the computer, take back your move and its reply together
        count = 2 if self.ai_color and len(self.b.move_log) >= 2 and self.b.turn != self.ai_color else 1
        for _ in range(count):
            self.b.undo()
            self.san_log.pop()
        self.game_over = False
        self.selected = None
        self.legal = []
        self.draw()
        self.maybe_ai_move()

    def new_game(self):
        if self.thinking:
            return
        self.b = Board()
        self.san_log.clear()
        self.game_over = False
        self.selected = None
        self.legal = []
        self.draw()
        self.maybe_ai_move()
