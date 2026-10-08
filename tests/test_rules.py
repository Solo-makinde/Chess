from engine import Board, Move


def play(board, *ucis):
    for u in ucis:
        mv = next(m for m in board.legal_moves() if m.uci() == u)
        board.make_move(mv)


def test_king_cannot_step_into_pawn_attack():
    # Bug in the original version: the king could walk onto a square attacked by a pawn.
    b = Board("8/8/8/8/3k4/8/4P3/4K3 b - - 0 1")
    targets = {m.uci()[2:] for m in b.legal_moves()}
    assert "d3" not in targets


def test_fools_mate():
    b = Board()
    play(b, "f2f3", "e7e5", "g2g4", "d8h4")
    assert b.result() == "Checkmate. Black wins."


def test_stalemate():
    b = Board("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1")
    assert b.result() == "Draw by stalemate."


def test_threefold_repetition():
    b = Board()
    play(b, "g1f3", "g8f6", "f3g1", "f6g8", "g1f3", "g8f6", "f3g1", "f6g8")
    assert b.result() == "Draw by threefold repetition."


def test_fifty_move_rule():
    b = Board("8/8/8/4k3/8/8/4K3/4R3 w - - 99 80")
    play(b, "e1d1")
    assert b.result() == "Draw by the fifty move rule."


def test_insufficient_material():
    assert Board("8/8/8/4k3/8/8/4K3/8 w - - 0 1").is_insufficient_material()
    assert Board("8/8/8/4k3/8/8/4KN2/8 w - - 0 1").is_insufficient_material()
    assert not Board("8/8/8/4k3/8/8/4KP2/8 w - - 0 1").is_insufficient_material()


def test_undo_restores_position():
    b = Board()
    before = b.position_key()
    play(b, "e2e4", "d7d5", "e4d5")
    for _ in range(3):
        b.undo()
    assert b.position_key() == before
    assert b.move_log == []


def test_castling_and_en_passant_notation():
    b = Board("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1")
    assert b.san(Move((7, 4), (7, 6), is_castle=True)) == "O-O"
    b = Board()
    play(b, "e2e4", "a7a6", "e4e5", "d7d5")
    ep = next(m for m in b.legal_moves() if m.is_en_passant)
    assert b.san(ep) == "exd6"


def test_promotion():
    b = Board("8/P6k/8/8/8/8/8/K7 w - - 0 1")
    play(b, "a7a8n")
    assert b.board[0][0] == ("w", "N")
