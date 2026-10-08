#!/usr/bin/env python3
"""Start the chess game.

    python main.py                  two players on one computer
    python main.py --ai black       you play White against the computer
    python main.py --ai white -d 4  you play Black, computer searches 4 moves deep
"""
import argparse
import tkinter as tk

from engine import BLACK, WHITE
from gui.app import ChessGUI


def main():
    parser = argparse.ArgumentParser(description="Chess with a built in computer opponent")
    parser.add_argument("--ai", choices=["white", "black"], help="color the computer plays")
    parser.add_argument("-d", "--depth", type=int, default=3, help="search depth (default 3)")
    args = parser.parse_args()

    ai_color = {"white": WHITE, "black": BLACK}.get(args.ai)
    root = tk.Tk()
    root.resizable(False, False)
    ChessGUI(root, ai_color=ai_color, depth=args.depth)
    root.mainloop()


if __name__ == "__main__":
    main()
