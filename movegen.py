"""Move generation.

`pseudo_moves()` yields every move a piece can physically make, ignoring
whether it leaves our own king in check.

`legal_moves()` filters the pseudo-legal list: a move is legal only if
our king is not attacked afterwards.  This one rule automatically covers
pins, moving the king into check, and en-passant captures that expose the
king — which is why the code stays short.

`perft()` counts leaf nodes in the move tree.  Comparing the counts
against published values is the standard correctness test for a move
generator (see tests/test_chess.py).
"""

from board import (Move, WHITE, KNIGHT_STEPS, KING_STEPS,
                   DIAGONALS, ORTHOGONAL)

PROMO_PIECES = ('q', 'r', 'b', 'n')


def _pawn_moves(b, s, r, f, us_white):
    """Pawn pushes, double pushes, captures, en passant, promotions."""
    step = 8 if us_white else -8
    start_rank = 1 if us_white else 6
    promo_rank = 6 if us_white else 1   # rank before the back rank
    last = 7 if us_white else 0

    # forward push (a pawn can never legally sit on the last rank,
    # but guard anyway in case a weird FEN is loaded)
    if r != last and b.sq[s + step] == '.':
        if r == promo_rank:
            for promo in PROMO_PIECES:
                yield Move(s, s + step, promo)
        else:
            yield Move(s, s + step)
            # double push from the starting rank over two empty squares
            two = s + 2 * step
            if r == start_rank and b.sq[two] == '.':
                yield Move(s, two)

    # diagonal captures (also the only way onto the ep square)
    for df in (-1, 1):
        nf = f + df
        if not 0 <= nf < 8 or r == last:
            continue
        t = s + step + df
        target = b.sq[t]
        if target != '.' and target.isupper() != us_white:
            if r == promo_rank:
                for promo in PROMO_PIECES:
                    yield Move(s, t, promo)
            else:
                yield Move(s, t)
        elif t == b.ep:
            yield Move(s, t)   # en passant; legality checked later


def _jump_moves(b, s, r, f, us_white, steps):
    for dr, df in steps:
        nr, nf = r + dr, f + df
        if 0 <= nr < 8 and 0 <= nf < 8:
            t = nr * 8 + nf
            target = b.sq[t]
            if target == '.' or target.isupper() != us_white:
                yield Move(s, t)


def _slide_moves(b, s, r, f, us_white, directions):
    for dr, df in directions:
        nr, nf = r + dr, f + df
        while 0 <= nr < 8 and 0 <= nf < 8:
            t = nr * 8 + nf
            target = b.sq[t]
            if target == '.':
                yield Move(s, t)
            else:
                if target.isupper() != us_white:
                    yield Move(s, t)
                break
            nr += dr
            nf += df


def _castle_moves(b, s, us_white):
    """Castling: rights intact, squares empty, king's path unattacked."""
    if us_white and s == 4:      # white king still on e1
        if ('K' in b.castling and b.sq[7] == 'R'
                and b.sq[5] == '.' and b.sq[6] == '.'
                and not b.is_attacked(4, False)
                and not b.is_attacked(5, False)
                and not b.is_attacked(6, False)):
            yield Move(4, 6)
        if ('Q' in b.castling and b.sq[0] == 'R'
                and b.sq[1] == '.' and b.sq[2] == '.' and b.sq[3] == '.'
                and not b.is_attacked(4, False)
                and not b.is_attacked(3, False)
                and not b.is_attacked(2, False)):
            yield Move(4, 2)
    elif not us_white and s == 60:  # black king still on e8
        if ('k' in b.castling and b.sq[63] == 'r'
                and b.sq[61] == '.' and b.sq[62] == '.'
                and not b.is_attacked(60, True)
                and not b.is_attacked(61, True)
                and not b.is_attacked(62, True)):
            yield Move(60, 62)
        if ('q' in b.castling and b.sq[56] == 'r'
                and b.sq[57] == '.' and b.sq[58] == '.' and b.sq[59] == '.'
                and not b.is_attacked(60, True)
                and not b.is_attacked(59, True)
                and not b.is_attacked(58, True)):
            yield Move(60, 58)


def pseudo_moves(b):
    """Every move a piece can physically make (may leave king in check)."""
    us_white = b.turn == WHITE
    for s in range(64):
        p = b.sq[s]
        if p == '.' or p.isupper() != us_white:
            continue
        r, f = divmod(s, 8)
        pl = p.lower()

        if pl == 'p':
            for m in _pawn_moves(b, s, r, f, us_white):
                yield m
        elif pl == 'n':
            for m in _jump_moves(b, s, r, f, us_white, KNIGHT_STEPS):
                yield m
        elif pl in 'brq':
            dirs = (DIAGONALS if pl == 'b'
                    else ORTHOGONAL if pl == 'r' else KING_STEPS)
            for m in _slide_moves(b, s, r, f, us_white, dirs):
                yield m
        elif pl == 'k':
            for m in _jump_moves(b, s, r, f, us_white, KING_STEPS):
                yield m
            for m in _castle_moves(b, s, us_white):
                yield m


def legal_moves(b):
    """Pseudo moves filtered down to the ones that keep our king safe."""
    us_white = b.turn == WHITE
    moves = []
    for m in pseudo_moves(b):
        nb = b.push(m)
        ksq = nb.wk if us_white else nb.bk
        if not nb.is_attacked(ksq, not us_white):
            moves.append(m)
    return moves


def perft(b, depth):
    """Count leaf nodes at `depth`.  Correctness test for movegen."""
    if depth == 0:
        return 1
    moves = legal_moves(b)
    if depth == 1:
        return len(moves)
    total = 0
    for m in moves:
        total += perft(b.push(m), depth - 1)
    return total
