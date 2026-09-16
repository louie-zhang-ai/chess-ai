"""The chess engine: negamax search with alpha-beta pruning.

The idea
--------
We generate every legal move, recursively explore the replies, and pick
the move that leads to the best guaranteed outcome.  `evaluate()` scores
the leaf positions.

  - negamax: minimax rewritten to always maximize, negating the score
    between turns ("what's bad for me is good for you")
  - alpha-beta pruning: skip branches that can never change the answer
    (if I already have a move worth +2, and a different move lets my
    opponent force +3 for them, I don't need to see the rest of that
    branch's replies)
  - quiescence search: at the horizon, keep searching captures only, so
    we never evaluate a position in the middle of a trade (avoids the
    "horizon effect" where a hanging piece looks fine because its
    capture is one move past the search depth)
  - move ordering: try captures of big pieces by small pieces first
    (MVV-LVA).  Good guesses early = more pruning later
  - iterative deepening: search depth 1, then 2, then 3... so a best
    move is always available if the clock runs out
"""

import time

from board import WHITE
from evaluate import evaluate, VALUE

MATE = 100000          # checkmate score; distance-to-mate is subtracted
INF = MATE * 2
MATE_THRESHOLD = MATE - 1000   # scores above this are mates


class SearchTimeout(Exception):
    """Raised when the search runs out of time mid-iteration."""
    pass


def order_moves(b, moves):
    """Sort moves so the most promising are searched first.

    MVV-LVA: Most Valuable Victim - Least Valuable Attacker.
    Capturing a queen with a pawn is probably better than the reverse.
    """
    def score(m):
        victim = b.sq[m.to]
        if victim != '.':
            s = 10 * VALUE[victim.upper()] - VALUE[b.sq[m.frm].upper()]
        elif b.sq[m.frm] in 'Pp' and m.to == b.ep:
            s = 10 * VALUE['P'] - VALUE['P']   # en passant capture
        else:
            s = 0
        if m.promo:
            s += VALUE[m.promo.upper()]
        return s
    moves.sort(key=score, reverse=True)


def quiesce(b, alpha, beta, ply, stats):
    """Search captures until the position is "quiet" enough to evaluate.

    When in check we search ALL evasions instead — otherwise a checkmate
    at the search horizon would be misjudged as a material score.
    """
    stats['nodes'] += 1
    in_check = b.in_check(b.turn)
    moves = b.legal_moves()
    if not moves:
        return -MATE + ply if in_check else 0

    if not in_check:
        stand_pat = evaluate(b)
        if stand_pat >= beta:
            return beta
        if stand_pat > alpha:
            alpha = stand_pat
        moves = [m for m in moves if b.is_capture(m) or m.promo]
        order_moves(b, moves)
    else:
        order_moves(b, moves)

    for m in moves:
        score = -quiesce(b.push(m), -beta, -alpha, ply + 1, stats)
        if score >= beta:
            return beta
        if score > alpha:
            alpha = score
    return alpha


def negamax(b, depth, alpha, beta, ply, stats, deadline):
    """Return the best score for the side to move, searching `depth`
    plies ahead.  `ply` is the distance from the root (used to prefer
    faster checkmates)."""
    stats['nodes'] += 1
    if deadline and stats['nodes'] & 4095 == 0 and time.time() > deadline:
        raise SearchTimeout

    if depth == 0:
        return quiesce(b, alpha, beta, ply, stats)

    moves = b.legal_moves()
    if not moves:
        # no legal moves: checkmate (bad for us) or stalemate (draw)
        return -MATE + ply if b.in_check(b.turn) else 0

    order_moves(b, moves)
    for m in moves:
        score = -negamax(b.push(m), depth - 1, -beta, -alpha,
                         ply + 1, stats, deadline)
        if score >= beta:
            return beta     # opponent won't allow this branch: cut it
        if score > alpha:
            alpha = score
    return alpha


def _root(b, depth, deadline, stats):
    """One iteration of the search at the root.  Returns (move, score)."""
    moves = b.legal_moves()
    order_moves(b, moves)
    best_move = None
    alpha = -INF
    for m in moves:
        score = -negamax(b.push(m), depth - 1, -INF, -alpha,
                         1, stats, deadline)
        if score > alpha:
            alpha = score
            best_move = m
    return best_move, alpha


def find_best_move(b, depth=4, max_time=None):
    """Search for the best move.

    depth:    max plies to search (ignored if None)
    max_time: seconds before we stop and use the best move found so far

    Returns (move, score, info).  Score is in centipawns for the side to
    move; info carries 'depth' reached, 'nodes' searched and 'seconds'.
    """
    deadline = time.time() + max_time if max_time else None
    stats = {'nodes': 0}
    moves = b.legal_moves()
    if not moves:
        return None, -MATE if b.in_check(b.turn) else 0, \
            {'depth': 0, 'nodes': 0, 'seconds': 0.0}
    best_move = moves[0]
    best_score = -INF
    completed = 0

    started = time.time()
    for d in range(1, (depth or 64) + 1):
        try:
            move, score = _root(b, d, deadline, stats)
        except SearchTimeout:
            break
        if move is None:
            break                      # no legal moves (mate/stalemate)
        best_move, best_score = move, score
        completed = d
        if deadline and time.time() > deadline:
            break

    info = {'depth': completed, 'nodes': stats['nodes'],
            'seconds': time.time() - started}
    return best_move, best_score, info


def score_str(score, turn):
    """Human-readable score: '+2.40', '-0.75', 'mate in 3'."""
    if abs(score) > MATE_THRESHOLD:
        plies = MATE - abs(score)
        n = (plies + 1) // 2
        return ('mate in %d' % n) if score > 0 else ('mated in %d' % n)
    pawns = score / 100.0
    if turn != WHITE:
        pawns = -pawns   # report from white's perspective
    return '%+.2f' % pawns
