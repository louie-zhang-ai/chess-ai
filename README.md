# chess-ai

A chess engine written from scratch in pure Python 3 — **zero
dependencies, standard library only**.  Every part is implemented from
first principles: move generation, the full rules of chess, search, and
evaluation.  It's built to be read and learned from.

```
python3 play.py        # play against the engine
python3 perft.py 4     # move-generation benchmark
python3 -m unittest discover -s tests   # run the test suite
```

Requires Python 3.8+.  There is nothing to install.

## Playing a game

You choose a search depth and a color, then enter moves in long
algebraic form:

```
your move> e2e4      # move the piece on e2 to e4
your move> e7e8q     # promote a pawn to a queen
your move> e1g1      # castle king side
```

Commands: `moves` (list legal moves), `board`, `undo`, `help`, `quit`.

## What's implemented

**The complete rules of chess**

- Legal move generation: pins, checks, and check evasions are handled
  correctly by filtering pseudo-legal moves through king safety
- Castling (with rights tracking, including "can't castle through check")
- En passant — including the edge case where the capture is illegal
  because it exposes the king
- Pawn promotion to queen, rook, bishop, or knight
- Checkmate, stalemate, fifty-move rule, insufficient material, and
  threefold repetition detection
- FEN import/export

**The engine**

- Negamax search with **alpha-beta pruning**
- **Quiescence search**: at the search horizon, captures (and check
  evasions) are resolved before evaluating, which avoids the classic
  horizon effect where a hanging piece looks safe because its capture is
  one move too deep
- **Move ordering** (MVV-LVA: capture the most valuable victim with the
  least valuable attacker) so the good moves are tried first and the
  bad branches get pruned
- **Iterative deepening** so a best move is always on hand when a time
  limit cuts the search short
- Evaluation = material + piece-square tables, with a separate king
  table for the endgame

## How it works

```
board.py      squares, pieces, move application, attack detection, FEN
movegen.py    pseudo-legal + legal move generation, perft
evaluate.py   material values + piece-square tables
engine.py     negamax + alpha-beta + quiescence + move ordering
play.py       terminal interface
perft.py      node-count benchmark for movegen
tests/        perft reference counts, rules tests, engine tests
```

### The search

Chess is a game of perfect information, so the "best" move is the one
that leads to the best outcome *assuming your opponent also plays
perfectly*.  That's minimax: on your turn take the max-scoring reply,
on their turn assume they take the min.  Negamax is the same idea
written more elegantly — always maximize, and negate the score between
plies.

Alpha-beta pruning makes it affordable.  It tracks two bounds:

- **alpha** — the best score you can already guarantee yourself
- **beta** — the score your opponent can already force on you

If a branch would let the opponent do better than beta allows, the rest
of that branch is skipped: it can't change the decision.  With good
move ordering, alpha-beta explores roughly the square root of the
brute-force tree — depth 5–6 becomes practical where plain minimax
drowned at depth 3.

### The evaluation

When the search runs out of depth, it needs a human-like opinion about
the position.  Ours is:

    material + where the pieces are standing

A knight on a central square is worth more than a knight in the corner;
pawns are rewarded for advancing; the king is encouraged to castle early
and to centralize in the endgame.  These opinions live in the
piece-square tables in `evaluate.py` — tweak them and watch the engine's
"style" change.

## How correct is it?

The move generator is verified with **perft** — counting every node in
the move tree to a fixed depth and comparing against reference values
cross-checked by dozens of chess engines:

| position | depth | nodes |
|---|---|---|
| startpos | 4 | 197,281 |
| kiwipete (castling heavy) | 3 | 97,862 |
| en passant edge cases | 4 | 43,238 |
| promotions | 3 | 9,467 |
| pins & checks | 3 | 62,379 |
| middlegame | 3 | 89,890 |

All counts match exactly.  The same test suite also checks that
castling through check is illegal, en passant pins are handled,
promotion generates all four pieces, and the engine finds forced mates.

## Honest strength assessment

This engine will beat a casual beginner and lose to a club player.
Depth is the bottleneck: pure Python reaches ~50k–150k nodes/second,
so the practical limit is depth 4–6 depending on patience.  That's
enough for sound tactics a few moves deep, not enough for deep
strategy — which is exactly what you'd expect from a readable
teaching engine.

## Ideas for where to take it next

- **Transposition table** — hash positions so repeated subtrees are
  searched once (biggest strength gain per line of code)
- **Killer moves & history heuristic** — remember which quiet moves
  caused cutoffs elsewhere and try them earlier
- **Null-move pruning, late-move reductions** — prune more aggressively
- **Opening book** — a dict of known positions mapped to good replies
- **A learned evaluation** — replace the hand-tuned tables with a small
  neural net; training a tiny network in pure Python is slow but very
  instructive
- **UCI protocol mode** — so the engine can plug into a real chess GUI

## A note on history

This project started as a Python 2 experiment with a hard-coded
heuristic, a brute-force tree that materialized every node in memory,
and a Theano-based neural evaluator that was never wired up.  It has
since been rewritten from scratch: Python 3, no dependencies, correct
rules, real alpha-beta pruning, and a test suite that proves the move
generator is right.
