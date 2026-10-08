"""Perft: count every legal position to a fixed depth and compare with published reference values.
Reference counts: https://www.chessprogramming.org/Perft_Results
"""
import pytest

from engine import Board, perft

START = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
KIWIPETE = "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1"
POS3 = "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1"
POS4 = "r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1"
POS5 = "rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ - 1 8"

CASES = [
    ("start", START, 1, 20),
    ("start", START, 2, 400),
    ("start", START, 3, 8902),
    ("kiwipete", KIWIPETE, 1, 48),
    ("kiwipete", KIWIPETE, 2, 2039),
    ("kiwipete", KIWIPETE, 3, 97862),
    ("pos3", POS3, 1, 14),
    ("pos3", POS3, 2, 191),
    ("pos3", POS3, 3, 2812),
    ("pos3", POS3, 4, 43238),
    ("pos4", POS4, 1, 6),
    ("pos4", POS4, 2, 264),
    ("pos4", POS4, 3, 9467),
    ("pos5", POS5, 1, 44),
    ("pos5", POS5, 2, 1486),
    ("pos5", POS5, 3, 62379),
]

SLOW_CASES = [
    ("start", START, 4, 197281),
    ("pos3", POS3, 5, 674624),
]


@pytest.mark.parametrize("name,fen,depth,expected", CASES)
def test_perft(name, fen, depth, expected):
    assert perft(Board(fen), depth) == expected


@pytest.mark.slow
@pytest.mark.parametrize("name,fen,depth,expected", SLOW_CASES)
def test_perft_deep(name, fen, depth, expected):
    assert perft(Board(fen), depth) == expected
