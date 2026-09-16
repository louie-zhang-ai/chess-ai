"""Board representation and the rules of chess.

Squares are numbered 0..63: 0 = a1, 7 = h1, 56 = a8, 63 = h8.
Pieces are single characters: uppercase = white ('PNBRQK'),
lowercase = black, '.' = empty square.

A Board is treated as immutable: ``push(move)`` returns a NEW board.
Copying a 64-element list is cheap, and this design removes an entire
class of make/unmake bugs.  Correctness first, speed second.
"""

from collections import namedtuple

WHITE = 'w'
BLACK = 'b'

START_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'

FILES = 'abcdefgh'

# A move is fully described by (from square, to square, promotion piece).
# Castling, en passant and double pawn pushes are inferred from the
# position when the move is applied, so no extra flags are needed.
Move = namedtuple('Move', ['frm', 'to', 'promo'], defaults=[None])

KNIGHT_STEPS = ((1, 2), (1, -2), (-1, 2), (-1, -2),
                (2, 1), (2, -1), (-2, 1), (-2, -1))
KING_STEPS = ((1, 0), (-1, 0), (0, 1), (0, -1),
              (1, 1), (1, -1), (-1, 1), (-1, -1))
DIAGONALS = ((1, 1), (1, -1), (-1, 1), (-1, -1))
ORTHOGONAL = ((1, 0), (-1, 0), (0, 1), (0, -1))

UNICODE_PIECES = {
    'P': '♙', 'N': '♘', 'B': '♗', 'R': '♖', 'Q': '♕', 'K': '♔',
    'p': '♟', 'n': '♞', 'b': '♝', 'r': '♜', 'q': '♛', 'k': '♚',
    '.': '·',
}


def square_name(sq):
    """0 -> 'a1', 63 -> 'h8'."""
    return FILES[sq & 7] + str((sq >> 3) + 1)


def parse_square(name):
    """'e4' -> 28."""
    return FILES.index(name[0]) + (int(name[1]) - 1) * 8


def move_to_uci(move):
    """Move -> 'e2e4' (or 'e7e8q' for promotions)."""
    return square_name(move.frm) + square_name(move.to) + (move.promo or '')


class Board(object):
    __slots__ = ('sq', 'turn', 'castling', 'ep', 'halfmove', 'fullmove',
                 'wk', 'bk')

    def __init__(self, squares, turn=WHITE, castling=frozenset(),
                 ep=None, halfmove=0, fullmove=1, wk=None, bk=None):
        self.sq = squares          # list of 64 single-char strings
        self.turn = turn           # WHITE or BLACK
        self.castling = castling   # frozenset subset of {'K','Q','k','q'}
        self.ep = ep               # en passant target square or None
        self.halfmove = halfmove   # moves since last pawn move/capture
        self.fullmove = fullmove   # increments after black's move
        self.wk = wk               # white king square (cached)
        self.bk = bk               # black king square (cached)
        if wk is None or bk is None:
            self.wk = squares.index('K') if 'K' in squares else -1
            self.bk = squares.index('k') if 'k' in squares else -1

    # ------------------------------------------------------------------
    # construction
    # ------------------------------------------------------------------

    @classmethod
    def startpos(cls):
        return cls.from_fen(START_FEN)

    @classmethod
    def from_fen(cls, fen):
        """Build a board from a FEN string."""
        fields = fen.split()
        squares = ['.'] * 64
        ranks = fields[0].split('/')
        for i, rank_str in enumerate(ranks):
            r = 7 - i  # FEN lists rank 8 first
            f = 0
            for ch in rank_str:
                if ch.isdigit():
                    f += int(ch)
                else:
                    squares[r * 8 + f] = ch
                    f += 1
        turn = fields[1] if len(fields) > 1 else WHITE
        castling = frozenset() if len(fields) <= 2 or fields[2] == '-' \
            else frozenset(fields[2])
        ep = None if len(fields) <= 3 or fields[3] == '-' \
            else parse_square(fields[3])
        halfmove = int(fields[4]) if len(fields) > 4 else 0
        fullmove = int(fields[5]) if len(fields) > 5 else 1
        return cls(squares, turn, castling, ep, halfmove, fullmove)

    def copy(self):
        return Board(self.sq[:], self.turn, self.castling, self.ep,
                     self.halfmove, self.fullmove, self.wk, self.bk)

    def fen(self):
        """Serialize back to FEN."""
        rows = []
        for r in range(7, -1, -1):
            row, empty = '', 0
            for f in range(8):
                p = self.sq[r * 8 + f]
                if p == '.':
                    empty += 1
                else:
                    row += (str(empty) if empty else '') + p
                    empty = 0
            row += str(empty) if empty else ''
            rows.append(row)
        return ' '.join((
            '/'.join(rows),
            self.turn,
            ''.join(sorted(self.castling)) or '-',
            square_name(self.ep) if self.ep is not None else '-',
            str(self.halfmove),
            str(self.fullmove),
        ))

    # ------------------------------------------------------------------
    # applying moves
    # ------------------------------------------------------------------

    def push(self, move):
        """Return a new Board with `move` applied."""
        b = self.copy()
        piece = b.sq[move.frm]
        target = b.sq[move.to]
        us_white = piece.isupper()

        b.ep = None
        b.halfmove += 1
        if piece in 'Pp' or target != '.':
            b.halfmove = 0

        # en passant capture: a pawn moved diagonally onto the ep square
        if (piece in 'Pp' and self.ep is not None and move.to == self.ep
                and target == '.' and (move.to & 7) != (move.frm & 7)):
            b.sq[move.to - 8 if us_white else move.to + 8] = '.'

        # castling: a king moving two squares drags its rook along
        if piece in 'Kk' and abs(move.to - move.frm) == 2:
            if move.to > move.frm:        # king side
                rook_frm, rook_to = move.frm + 3, move.frm + 1
            else:                          # queen side
                rook_frm, rook_to = move.frm - 4, move.frm - 1
            b.sq[rook_to] = b.sq[rook_frm]
            b.sq[rook_frm] = '.'

        b.sq[move.frm] = '.'
        b.sq[move.to] = piece
        if move.promo:
            b.sq[move.to] = move.promo.upper() if us_white \
                else move.promo.lower()

        # double pawn push -> new en passant square behind the pawn
        if piece in 'Pp' and abs(move.to - move.frm) == 16:
            b.ep = (move.frm + move.to) // 2

        # castling rights: king move loses both, rook move/capture on a
        # corner square loses that side
        rights = set(b.castling)
        if piece == 'K':
            rights.discard('K')
            rights.discard('Q')
        elif piece == 'k':
            rights.discard('k')
            rights.discard('q')
        for corner, flag in ((0, 'Q'), (7, 'K'), (56, 'q'), (63, 'k')):
            if move.frm == corner or move.to == corner:
                rights.discard(flag)
        b.castling = frozenset(rights)

        if piece == 'K':
            b.wk = move.to
        elif piece == 'k':
            b.bk = move.to

        if self.turn == BLACK:
            b.fullmove += 1
        b.turn = BLACK if self.turn == WHITE else WHITE
        return b

    def is_capture(self, move):
        """True if `move` captures a piece (including en passant)."""
        return (self.sq[move.to] != '.' or
                (self.sq[move.frm] in 'Pp' and move.to == self.ep))

    # ------------------------------------------------------------------
    # attack detection
    # ------------------------------------------------------------------

    def is_attacked(self, s, by_white):
        """Is square `s` attacked by the given side?"""
        r, f = divmod(s, 8)
        sq = self.sq

        # pawns: a white pawn attacks one rank above itself
        pr = r - 1 if by_white else r + 1
        if 0 <= pr < 8:
            pawn = 'P' if by_white else 'p'
            for df in (-1, 1):
                pf = f + df
                if 0 <= pf < 8 and sq[pr * 8 + pf] == pawn:
                    return True

        # knights
        knight = 'N' if by_white else 'n'
        for dr, df in KNIGHT_STEPS:
            nr, nf = r + dr, f + df
            if 0 <= nr < 8 and 0 <= nf < 8 and sq[nr * 8 + nf] == knight:
                return True

        # king (adjacent squares)
        king = 'K' if by_white else 'k'
        for dr, df in KING_STEPS:
            nr, nf = r + dr, f + df
            if 0 <= nr < 8 and 0 <= nf < 8 and sq[nr * 8 + nf] == king:
                return True

        # sliding pieces: walk each ray until we hit something
        for dr, df in DIAGONALS:
            nr, nf = r + dr, f + df
            while 0 <= nr < 8 and 0 <= nf < 8:
                p = sq[nr * 8 + nf]
                if p != '.':
                    if p.isupper() == by_white and p.lower() in 'bq':
                        return True
                    break
                nr += dr
                nf += df
        for dr, df in ORTHOGONAL:
            nr, nf = r + dr, f + df
            while 0 <= nr < 8 and 0 <= nf < 8:
                p = sq[nr * 8 + nf]
                if p != '.':
                    if p.isupper() == by_white and p.lower() in 'rq':
                        return True
                    break
                nr += dr
                nf += df
        return False

    def in_check(self, color):
        """Is `color`'s king attacked right now?"""
        ksq = self.wk if color == WHITE else self.bk
        return self.is_attacked(ksq, color != WHITE)

    # ------------------------------------------------------------------
    # game status
    # ------------------------------------------------------------------

    def legal_moves(self):
        import movegen  # local import: movegen needs Move from this file
        return movegen.legal_moves(self)

    def insufficient_material(self):
        """Neither side can possibly checkmate (K v K, K+minor v K,
        K+B v K+B with same-colored bishops)."""
        rest = [(s, p) for s, p in enumerate(self.sq)
                if p != '.' and p not in 'Kk']
        if any(p in 'PpRrQq' for _, p in rest):
            return False
        if len(rest) <= 1:
            return True
        if len(rest) == 2 and all(p in 'Bb' for _, p in rest):
            colors = {((s >> 3) + (s & 7)) & 1 for s, _ in rest}
            if len(colors) == 1:
                return True
        return False

    def position_key(self):
        """A string identifying this position (for repetition draws)."""
        return (''.join(self.sq) + self.turn +
                ''.join(sorted(self.castling)) + str(self.ep))

    def result(self):
        """(result, reason) e.g. ('1-0', 'checkmate'), or None."""
        if self.legal_moves():
            if self.halfmove >= 100:
                return '1/2-1/2', 'fifty-move rule'
            if self.insufficient_material():
                return '1/2-1/2', 'insufficient material'
            return None
        if self.in_check(self.turn):
            return ('0-1' if self.turn == WHITE else '1-0'), 'checkmate'
        return '1/2-1/2', 'stalemate'

    # ------------------------------------------------------------------
    # display
    # ------------------------------------------------------------------

    def __str__(self):
        lines = []
        for r in range(7, -1, -1):
            row = ' '.join(UNICODE_PIECES[self.sq[r * 8 + f]]
                           for f in range(8))
            lines.append('%d  %s' % (r + 1, row))
        lines.append('   a b c d e f g h')
        return '\n'.join(lines)
