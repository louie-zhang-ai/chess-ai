#!/usr/bin/env python3
"""Play chess against the engine in your terminal.

    python3 play.py

Moves are entered in long algebraic form:  e2e4, g1f3, e7e8q.
Commands:  moves, board, undo, help, quit
"""

import sys
import time
from collections import Counter

from board import Board, WHITE, move_to_uci
from engine import find_best_move, score_str

HELP = """\
  Enter a move in long algebraic form:
    e2e4     move the piece on e2 to e4
    e7e8q    promote the pawn on e7 to a queen
    e1g1     castle king side (as white)

  Commands:
    moves    list all legal moves
    board    print the board again
    undo     take back your last move (and the engine's reply)
    help     show this text
    quit     exit the game
"""


def parse_move(b, text):
    """Match user input like 'e2e4' against the legal move list."""
    for m in b.legal_moves():
        if move_to_uci(m) == text:
            return m
    return None


def ask(prompt, default):
    answer = input('%s [%s]: ' % (prompt, default)).strip()
    return answer or default


def human_turn(b, history):
    """Prompt until the human makes a legal move.  Returns the board."""
    while True:
        text = input('your move> ').strip().lower()

        if text in ('quit', 'exit'):
            sys.exit(0)
        elif text == 'help':
            print(HELP)
        elif text == 'moves':
            print(' '.join(sorted(move_to_uci(m)
                                  for m in b.legal_moves())))
        elif text == 'board':
            print(b)
        elif text == 'undo':
            # rewind past the human's last move and the engine's reply
            if len(history) >= 3:
                history.pop()
                history.pop()
            elif len(history) > 1:
                history.pop()
            else:
                print('nothing to undo')
                continue
            b = history[-1]
            print(b)
        else:
            move = parse_move(b, text)
            if move:
                return b.push(move)
            print("'%s' is not a legal move. "
                  "Type 'moves' to see the options." % text)


def engine_turn(b, depth):
    print('engine is thinking...')
    t0 = time.time()
    move, score, info = find_best_move(b, depth=depth)
    print('engine plays %s   (%s, depth %d, %d nodes, %.1fs)'
          % (move_to_uci(move), score_str(score, WHITE),
             info['depth'], info['nodes'], time.time() - t0))
    return b.push(move)


def main():
    print('chess-ai — a from-scratch chess engine')
    print("type 'help' at the move prompt for instructions\n")

    try:
        depth = int(ask('search depth', '3'))
        human = ask('play as white or black? (w/b)', 'w')
    except (EOFError, KeyboardInterrupt):
        print()
        return
    human = WHITE if human != 'b' else 'b'

    board = Board.startpos()
    history = [board]

    while True:
        print()
        print(board)

        seen = Counter(h.position_key() for h in history)
        res = board.result()
        if res is None and seen[board.position_key()] >= 3:
            res = '1/2-1/2', 'threefold repetition'
        if res:
            print('\nGame over: %s (%s)' % (res[0], res[1]))
            return

        if board.turn == human:
            board = human_turn(board, history)
        else:
            board = engine_turn(board, depth)

        if board is not history[-1]:
            history.append(board)


if __name__ == '__main__':
    main()
