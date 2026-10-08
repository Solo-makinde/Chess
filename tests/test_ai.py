from engine import AI, Board


def test_finds_mate_in_one():
    # Back rank mate: Re8#
    b = Board("6k1/5ppp/8/8/8/8/8/4R1K1 w - - 0 1")
    mv, _ = AI(depth=2).best_move(b)
    assert mv.uci() == "e1e8"


def test_takes_free_queen():
    b = Board("4k3/8/8/3q4/8/8/8/3QK3 w - - 0 1")
    mv, _ = AI(depth=2).best_move(b)
    assert mv.uci() == "d1d5"


def test_moves_attacked_queen_to_safety():
    # The black pawn on e3 attacks the queen on d2
    b = Board("4k3/8/8/8/8/4p3/3Q4/4K3 w - - 0 1")
    mv, _ = AI(depth=3).best_move(b)
    b.make_move(mv)
    qr, qc = next((r, c) for r in range(8) for c in range(8) if b.board[r][c] == ("w", "Q"))
    assert not b.is_attacked(qr, qc, "b")
