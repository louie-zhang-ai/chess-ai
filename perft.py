#!/usr/bin/env python3
"""Move-generation benchmark: count every node in the move tree.

    python3 perft.py [depth] [fen]

The starting position should produce:
    depth 1:        20
    depth 2:       400
    depth 3:     8,902
    depth 4:   197,281
    depth 5: 4,865,609
"""

import sys
import time

from board import Board
from movegen import legal_moves, perft


def divide(b, depth):
    """Node counts broken down by root move — handy for debugging."""
    from board import move_to_uci
    total = 0
    for m in legal_moves(b):
        n = perft(b.push(m), depth - 1)
        total += n
        print('%s: %d' % (move_to_uci(m), n))
    return total


def main():
    depth = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    fen = sys.argv[2] if len(sys.argv) > 2 else None
    b = Board.from_fen(fen) if fen else Board.startpos()

    print(b)
    print()
    t0 = time.time()
    nodes = perft(b, depth)
    dt = time.time() - t0
    print('perft(%d) = %d   (%.2fs, %.0f nodes/sec)'
          % (depth, nodes, dt, nodes / dt if dt else 0))


if __name__ == '__main__':
    main()
