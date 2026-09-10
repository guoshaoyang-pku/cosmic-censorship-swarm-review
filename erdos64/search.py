"""
Erdos problem #64 (Erdos-Gyarfas conjecture, $1000):
    does every finite graph with minimum degree >= 3 contain a cycle of length 2^k, k >= 2?

A counterexample is a finite graph, min degree >= 3, with NO cycle of length 4, 8, 16, 32, ...
Note C3 is allowed -- only powers of two from 4 up are forbidden.

Cubic (3-regular) graphs are the extremal case: adding any edge only creates more cycles, so
if a counterexample exists a cubic one is the natural place to look. On n < 32 vertices the
only forbidden lengths that fit are 4, 8 and 16, which makes the objective exactly computable.

This file is the verifier plus a local search. The verifier is the part that has to be right:
the search is allowed to be dumb, the verifier is not. So cycle counting is done by explicit
path enumeration with a canonical representative (smallest vertex first, second < last) rather
than by any clever algebraic shortcut that could silently count walks instead of cycles.
"""
from __future__ import annotations
import random, sys, json, time
from collections import defaultdict

FORBIDDEN = (4, 8, 16)          # powers of two >= 4 that fit in n < 32 vertices


def count_cycles_of_length(adj, n, L):
    """Exact number of cycles of length exactly L. Canonical form: the cycle is counted from
    its smallest vertex, and only in the direction where the second vertex is smaller than the
    last, so each cycle is counted exactly once."""
    total = 0
    for start in range(n):
        # paths start at `start`, never revisit, all vertices > start
        stack = [(start, 1 << start, 1, -1)]     # (vertex, visited mask, length, second vertex)
        while stack:
            v, mask, ln, second = stack.pop()
            if ln == L:
                if start in adj[v] and (second != -1):
                    # close the cycle; direction tiebreak on (second < last)
                    last = v
                    if second < last:
                        total += 1
                continue
            for w in adj[v]:
                if w < start or (mask >> w) & 1:
                    continue
                stack.append((w, mask | (1 << w), ln + 1, w if ln == 1 else second))
    return total


def objective(adj, n):
    """Number of forbidden cycles. Zero means a counterexample (for this n)."""
    return sum(count_cycles_of_length(adj, n, L) for L in FORBIDDEN)


def per_length(adj, n):
    return {L: count_cycles_of_length(adj, n, L) for L in FORBIDDEN}


def min_degree(adj):
    return min(len(a) for a in adj)


def random_cubic(n, rng, tries=400):
    """Random 3-regular simple graph by pairing model with rejection."""
    for _ in range(tries):
        stubs = [v for v in range(n) for _ in range(3)]
        rng.shuffle(stubs)
        adj = [set() for _ in range(n)]
        ok = True
        for i in range(0, len(stubs), 2):
            a, b = stubs[i], stubs[i + 1]
            if a == b or b in adj[a]:
                ok = False
                break
            adj[a].add(b)
            adj[b].add(a)
        if ok and all(len(s) == 3 for s in adj):
            return [sorted(s) for s in adj]
    return None


def two_swap(adj, n, rng):
    """(a,b),(c,d) -> (a,c),(b,d). Keeps 3-regularity and simplicity. Returns the edit or None."""
    edges = [(u, v) for u in range(n) for v in adj[u] if u < v]
    for _ in range(60):
        (a, b), (c, d) = rng.sample(edges, 2)
        if rng.random() < 0.5:
            c, d = d, c
        if len({a, b, c, d}) != 4:
            continue
        if c in adj[a] or d in adj[b]:
            continue
        return (a, b, c, d)
    return None


def apply_swap(adj, e):
    a, b, c, d = e
    adj[a].remove(b); adj[b].remove(a); adj[c].remove(d); adj[d].remove(c)
    adj[a].append(c); adj[c].append(a); adj[b].append(d); adj[d].append(b)


def undo_swap(adj, e):
    a, b, c, d = e
    apply_swap(adj, (a, c, b, d))


def anneal(n, seed, steps=40000, T0=2.0, T1=0.02):
    rng = random.Random(seed)
    adj = random_cubic(n, rng)
    if adj is None:
        return None
    adj = [list(a) for a in adj]
    cur = objective(adj, n)
    best, best_adj = cur, [list(a) for a in adj]
    for t in range(steps):
        if best == 0:
            break
        e = two_swap(adj, n, rng)
        if e is None:
            continue
        apply_swap(adj, e)
        new = objective(adj, n)
        T = T0 * (T1 / T0) ** (t / steps)
        if new <= cur or rng.random() < pow(2.718281828, -(new - cur) / T):
            cur = new
            if new < best:
                best, best_adj = new, [list(a) for a in adj]
        else:
            undo_swap(adj, e)
    return dict(n=n, seed=seed, best=best, adj=best_adj)


if __name__ == '__main__':
    # self-test the verifier on graphs whose cycle spectrum is known
    K4 = [[1, 2, 3], [0, 2, 3], [0, 1, 3], [0, 1, 2]]
    assert count_cycles_of_length(K4, 4, 3) == 4, count_cycles_of_length(K4, 4, 3)
    assert count_cycles_of_length(K4, 4, 4) == 3, count_cycles_of_length(K4, 4, 4)
    # K_{3,3}: 9 four-cycles, 6 six-cycles, no odd cycles
    K33 = [[3, 4, 5], [3, 4, 5], [3, 4, 5], [0, 1, 2], [0, 1, 2], [0, 1, 2]]
    assert count_cycles_of_length(K33, 6, 4) == 9, count_cycles_of_length(K33, 6, 4)
    assert count_cycles_of_length(K33, 6, 6) == 6, count_cycles_of_length(K33, 6, 6)
    assert count_cycles_of_length(K33, 6, 3) == 0
    # Petersen graph: girth 5, 12 five-cycles, no 4-cycles, 10 six-cycles
    PET = [[1, 4, 5], [0, 2, 6], [1, 3, 7], [2, 4, 8], [0, 3, 9],
           [0, 7, 8], [1, 8, 9], [2, 5, 9], [3, 5, 6], [4, 6, 7]]
    assert count_cycles_of_length(PET, 10, 4) == 0
    assert count_cycles_of_length(PET, 10, 5) == 12, count_cycles_of_length(PET, 10, 5)
    assert count_cycles_of_length(PET, 10, 6) == 10, count_cycles_of_length(PET, 10, 6)
    print("verifier self-test PASSED (K4, K_{3,3}, Petersen)")

    n = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    nseeds = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    t0 = time.time()
    print(f"Petersen forbidden-cycle count = {per_length(PET, 10)}  (a known min-deg-3 graph)")
    res = []
    for s in range(nseeds):
        r = anneal(n, s, steps=6000)
        if r:
            res.append(r['best'])
            print(f"  n={n} seed={s} best={r['best']}", flush=True)
    print(f"n={n}  min over {len(res)} restarts = {min(res) if res else 'NA'}"
          f"  ({time.time()-t0:.0f}s)")
