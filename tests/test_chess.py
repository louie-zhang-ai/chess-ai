"""Test suite for the chess engine.

The perft tests are the important part: they count every node in the
move tree to a fixed depth and compare against reference values that
are published and cross-checked by every serious chess engine.  If
movegen passes these, castling/en-passant/promotion/pins are correct.

Run from the project root:

    python3 -m unittest discover -s tests
    python3 tests/test_chess.py
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from board import Board, parse_square, move_to_uci   # noqa: E402
from movegen import legal_moves, perft              # noqa: E402
from evaluate import evaluate                       # noqa: E402
from engine import find_best_move, MATE_THRESHOLD   # noqa: E402


def uci_set(b):
    return {move_to_uci(m) for m in b.legal_moves()}


class Perft(unittest.TestCase):
    """Known node counts from the chess programming wiki test suite."""

    def check(self, fen, counts):
        b = Board.from_fen(fen)
        for depth, expected in counts.items():
            self.assertEqual(perft(b, depth), expected,
                             'perft(%d) failed for %s' % (depth, fen))

    def test_startpos(self):
        self.check(Board.startpos().fen(), {1: 20, 2: 400, 3: 8902})

    def test_startpos_deep(self):
        self.check(Board.startpos().fen(), {4: 197281})

    def test_kiwipete(self):
        # dense middlegame position; heavy on castling and captures
        self.check(
            'r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/'
            'R3K2R w KQkq - 0 1',
            {1: 48, 2: 2039, 3: 97862})

    def test_position3(self):
        # en passant edge cases, including the pinned-ep-capture
        self.check('8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1',
                   {1: 14, 2: 191, 3: 2812, 4: 43238})

    def test_position4(self):
        # promotions and castling rights
        self.check('r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/'
                   'Pp1P2PP/R2Q1RK1 w kq - 0 1',
                   {1: 6, 2: 264, 3: 9467})

    def test_position5(self):
        self.check('rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/'
                   'RNBQK2R w KQ - 1 8',
                   {1: 44, 2: 1486, 3: 62379})

    def test_position6(self):
        self.check('r4rk1/1pp1qppp/p1np1n2/2b1p1B1/2B1P1b1/'
                   'P1NP1N2/1PP1QPPP/R4RK1 w - - 0 10',
                   {1: 46, 2: 2079, 3: 89890})


class Fen(unittest.TestCase):
    def test_roundtrip(self):
        for fen in (Board.startpos().fen(),
                    'r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/'
                    'PPPBBPPP/R3K2R w KQkq - 0 1',
                    '8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1'):
            self.assertEqual(Board.from_fen(fen).fen(), fen)


class Rules(unittest.TestCase):
    def test_castle_through_check_illegal(self):
        # black rook on d8 controls d1 -> white may not castle queenside
        b = Board.from_fen('3rk3/8/8/8/8/8/8/R3K2R w KQ - 0 1')
        moves = uci_set(b)
        self.assertIn('e1g1', moves)
        self.assertNotIn('e1c1', moves)

    def test_castle_moves_rook(self):
        b = Board.from_fen('r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1')
        nb = b.push(next(m for m in b.legal_moves()
                         if move_to_uci(m) == 'e1g1'))
        self.assertEqual(nb.sq[6], 'K')   # g1
        self.assertEqual(nb.sq[5], 'R')   # f1
        self.assertNotIn('K', nb.castling)
        self.assertNotIn('Q', nb.castling)

    def test_castling_rights_lost_on_rook_capture(self):
        b = Board.from_fen('r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1')
        nb = b.push(next(m for m in b.legal_moves()
                         if move_to_uci(m) == 'a1a8'))  # Rxa8
        self.assertNotIn('q', nb.castling)
        self.assertIn('k', nb.castling)

    def test_en_passant_capture(self):
        # black just played d7d5; white e5 may capture e.p. to d6
        b = Board.from_fen('7k/8/8/3pP3/8/8/8/K7 w - d6 0 1')
        m = next(m for m in b.legal_moves() if move_to_uci(m) == 'e5d6')
        nb = b.push(m)
        self.assertEqual(nb.sq[parse_square('d6')], 'P')
        self.assertEqual(nb.sq[parse_square('d5')], '.')

    def test_en_passant_pinned_is_illegal(self):
        # famous edge case: capturing e.p. would expose the king on rank 5
        b = Board.from_fen('8/8/8/KPp4r/8/8/8/4k3 w - c6 0 1')
        self.assertNotIn('b5c6', uci_set(b))

    def test_promotion_generates_four_moves(self):
        b = Board.from_fen('8/P7/8/8/8/8/8/K6k w - - 0 1')
        promos = {m for m in b.legal_moves() if m.frm == parse_square('a7')}
        self.assertEqual(len(promos), 4)
        self.assertEqual({m.promo for m in promos}, {'q', 'r', 'b', 'n'})

    def test_pinned_piece_cannot_move(self):
        # white knight on e2 is pinned against its king by the e8 rook
        b = Board.from_fen('4r3/8/8/8/8/8/4N3/4K3 w - - 0 1')
        self.assertTrue(all(m.frm != parse_square('e2')
                            for m in b.legal_moves()))

    def test_checkmate(self):
        # fool's mate: white to move is checkmated
        b = Board.from_fen('rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/'
                           'PPPPP2P/RNBQKBNR w KQkq - 1 3')
        self.assertEqual(b.legal_moves(), [])
        self.assertEqual(b.result(), ('0-1', 'checkmate'))

    def test_stalemate(self):
        b = Board.from_fen('7k/5Q2/6K1/8/8/8/8/8 b - - 0 1')
        self.assertEqual(b.legal_moves(), [])
        self.assertEqual(b.result(), ('1/2-1/2', 'stalemate'))

    def test_insufficient_material(self):
        b = Board.from_fen('8/8/8/8/8/8/7k/K6B w - - 0 1')
        self.assertEqual(b.result(), ('1/2-1/2', 'insufficient material'))


class Evaluation(unittest.TestCase):
    def test_startpos_is_equal(self):
        self.assertEqual(evaluate(Board.startpos()), 0)

    def test_extra_material_scores_positive(self):
        b = Board.from_fen('6k1/8/6K1/8/8/8/8/3R4 w - - 0 1')
        self.assertGreater(evaluate(b), 400)  # white is up a rook


class Engine(unittest.TestCase):
    def test_mate_in_one(self):
        # Rd8 is back-rank mate (white king covers the escape squares)
        b = Board.from_fen('6k1/8/6K1/8/8/8/8/3R4 w - - 0 1')
        move, score, info = find_best_move(b, depth=1)
        self.assertEqual(move_to_uci(move), 'd1d8')
        self.assertGreater(score, MATE_THRESHOLD)

    def test_mate_in_two(self):
        # king and queen vs king: Qg7 is mate... let the engine find it
        b = Board.from_fen('6k1/8/5K2/8/8/8/8/4Q3 w - - 0 1')
        move, score, info = find_best_move(b, depth=3)
        self.assertGreater(score, MATE_THRESHOLD)

    def test_captures_hanging_piece(self):
        # black queen on d5 is attacked by the c3 knight and undefended
        b = Board.from_fen('rnb1kbnr/pppp1ppp/8/3q4/8/2N5/'
                           'PPPP1PPP/R1BQKBNR w KQkq - 0 1')
        move, score, info = find_best_move(b, depth=1)
        self.assertEqual(move_to_uci(move), 'c3d5')


if __name__ == '__main__':
    unittest.main()
