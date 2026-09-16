"""Position evaluation — the engine's "intuition".

`evaluate(board)` returns a score in centipawns (1/100th of a pawn)
from the perspective of the side to move: positive = good for the
player whose turn it is, negative = bad.

The evaluation is the classic beginner-engine recipe:

    score = material + piece-square tables

Material says WHAT you have; the tables say WHERE it is.  A knight in
the center is worth more than a knight on the rim, pawns get rewarded
for advancing, and the king should hide in the middlegame but come out
fighting in the endgame.  All numbers are tuned by hand — no data, no
libraries, just chess knowledge encoded as tables.
"""

from board import WHITE

# material values in centipawns (the king is always on the board, so its
# value doesn't matter and is omitted)
VALUE = {'P': 100, 'N': 320, 'B': 330, 'R': 500, 'Q': 900, 'K': 0}

# Piece-square tables, written as they appear from White's side of the
# board: first row = rank 8, last row = rank 1.  `_table()` flattens them
# into the board's indexing (a1 = 0 .. h8 = 63).  Black pieces look up
# their square mirrored vertically (square ^ 56).

def _table(*rows):
    t = [0] * 64
    for i, row in enumerate(rows):      # row 0 is rank 8
        for f, v in enumerate(row):
            t[(7 - i) * 8 + f] = v
    return t

PAWN_PST = _table(
    (  0,  0,  0,  0,  0,  0,  0,  0),
    ( 50, 50, 50, 50, 50, 50, 50, 50),
    ( 10, 10, 20, 30, 30, 20, 10, 10),
    (  5,  5, 10, 25, 25, 10,  5,  5),
    (  0,  0,  0, 20, 20,  0,  0,  0),
    (  5, -5,-10,  0,  0,-10, -5,  5),
    (  5, 10, 10,-20,-20, 10, 10,  5),
    (  0,  0,  0,  0,  0,  0,  0,  0),
)

KNIGHT_PST = _table(
    (-50,-40,-30,-30,-30,-30,-40,-50),
    (-40,-20,  0,  0,  0,  0,-20,-40),
    (-30,  0, 10, 15, 15, 10,  0,-30),
    (-30,  5, 15, 20, 20, 15,  5,-30),
    (-30,  0, 15, 20, 20, 15,  0,-30),
    (-30,  5, 10, 15, 15, 10,  5,-30),
    (-40,-20,  0,  5,  5,  0,-20,-40),
    (-50,-40,-30,-30,-30,-30,-40,-50),
)

BISHOP_PST = _table(
    (-20,-10,-10,-10,-10,-10,-10,-20),
    (-10,  0,  0,  0,  0,  0,  0,-10),
    (-10,  0,  5, 10, 10,  5,  0,-10),
    (-10,  5,  5, 10, 10,  5,  5,-10),
    (-10,  0, 10, 10, 10, 10,  0,-10),
    (-10, 10, 10, 10, 10, 10, 10,-10),
    (-10,  5,  0,  0,  0,  0,  5,-10),
    (-20,-10,-10,-10,-10,-10,-10,-20),
)

ROOK_PST = _table(
    (  0,  0,  0,  0,  0,  0,  0,  0),
    (  5, 10, 10, 10, 10, 10, 10,  5),
    ( -5,  0,  0,  0,  0,  0,  0, -5),
    ( -5,  0,  0,  0,  0,  0,  0, -5),
    ( -5,  0,  0,  0,  0,  0,  0, -5),
    ( -5,  0,  0,  0,  0,  0,  0, -5),
    ( -5,  0,  0,  0,  0,  0,  0, -5),
    (  0,  0,  0,  5,  5,  0,  0,  0),
)

QUEEN_PST = _table(
    (-20,-10,-10, -5, -5,-10,-10,-20),
    (-10,  0,  0,  0,  0,  0,  0,-10),
    (-10,  0,  5,  5,  5,  5,  0,-10),
    ( -5,  0,  5,  5,  5,  5,  0, -5),
    (  0,  0,  5,  5,  5,  5,  0, -5),
    (-10,  5,  5,  5,  5,  5,  0,-10),
    (-10,  0,  5,  0,  0,  0,  0,-10),
    (-20,-10,-10, -5, -5,-10,-10,-20),
)

KING_PST_MID = _table(
    (-30,-40,-40,-50,-50,-40,-40,-30),
    (-30,-40,-40,-50,-50,-40,-40,-30),
    (-30,-40,-40,-50,-50,-40,-40,-30),
    (-30,-40,-40,-50,-50,-40,-40,-30),
    (-20,-30,-30,-40,-40,-30,-30,-20),
    (-10,-20,-20,-20,-20,-20,-20,-10),
    ( 20, 20,  0,  0,  0,  0, 20, 20),
    ( 20, 30, 10,  0,  0, 10, 30, 20),
)

KING_PST_END = _table(
    (-50,-40,-30,-20,-20,-30,-40,-50),
    (-30,-20,-10,  0,  0,-10,-20,-30),
    (-30,-10, 20, 30, 30, 20,-10,-30),
    (-30,-10, 30, 40, 40, 30,-10,-30),
    (-30,-10, 30, 40, 40, 30,-10,-30),
    (-30,-10, 20, 30, 30, 20,-10,-30),
    (-30,-30,  0,  0,  0,  0,-30,-30),
    (-50,-30,-30,-30,-30,-30,-30,-50),
)

PST = {'P': PAWN_PST, 'N': KNIGHT_PST, 'B': BISHOP_PST,
       'R': ROOK_PST, 'Q': QUEEN_PST, 'K': KING_PST_MID}


def _is_endgame(b):
    """Endgame heuristic: no queens on the board, or every side that
    still has a queen has at most one minor piece to support it."""
    queens = {}
    minors = {'w': 0, 'b': 0}
    for p in b.sq:
        if p in 'Qq':
            queens['w' if p == 'Q' else 'b'] = True
        elif p in 'NB':
            minors['w'] += 1
        elif p in 'nb':
            minors['b'] += 1
        elif p in 'Rr':
            minors['w' if p == 'R' else 'b'] += 2
    if not queens:
        return True
    return all(minors[side] <= 1 for side in queens)


def evaluate(b):
    """Score the position in centipawns for the side to move."""
    endgame = _is_endgame(b)
    score = 0
    for s, p in enumerate(b.sq):
        if p == '.':
            continue
        table = KING_PST_END if p in 'Kk' and endgame else PST[p.upper()]
        if p.isupper():
            score += VALUE[p] + table[s]
        else:
            # mirror the square so black uses the same tables as white
            score -= VALUE[p.upper()] + table[s ^ 56]
    return score if b.turn == WHITE else -score
