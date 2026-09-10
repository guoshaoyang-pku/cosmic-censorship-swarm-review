"""
Sweep over n. Two changes that matter:

1. LEXICOGRAPHIC objective with early exit. The cost of counting cycles explodes with length,
   so counting C16 on a graph that still has C4s is wasted work. Drive c4 to 0 first (cheap),
   then c8, then c16. Comparing (c4, c8, c16) as a tuple does exactly that, and short-circuiting
   the count when a cheaper term is already nonzero makes each step ~10x cheaper.

2. One process per n, so the sweep is embarrassingly parallel -- which is itself the point:
   this problem is MAP-REDUCE shaped, not organisation shaped. Independent restarts share
   nothing. That is the classification my own criteria predicted, now being tested.
"""
import sys, os, json, random, time, multiprocessing as mp
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from search import count_cycles_of_length, random_cubic, two_swap, apply_swap, undo_swap

FORB = (4, 8, 16)

def obj_lex(adj, n, cap=None):
    """(c4, c8, c16), stopping early once a term is nonzero -- the later terms cannot rescue
    a graph that already fails an earlier one, and they are the expensive ones."""
    out = []
    for L in FORB:
        if L > n:
            out.append(0); continue
        c = count_cycles_of_length(adj, n, L)
        out.append(c)
        if c > 0:
            out.extend([10**6] * (len(FORB) - len(out)))   # sentinel: unknown but irrelevant
            break
    return tuple(out)

def score(t):
    return t[0] * 10**12 + min(t[1], 10**6) * 10**6 + min(t[2], 10**6)

def anneal(args):
    n, seed, steps = args
    rng = random.Random(seed * 7919 + n)
    adj = random_cubic(n, rng)
    if adj is None:
        return None
    adj = [list(a) for a in adj]
    cur = score(obj_lex(adj, n)); best = cur; best_adj = [list(a) for a in adj]
    T0, T1 = 3.0, 0.05
    for t in range(steps):
        if best == 0:
            break
        e = two_swap(adj, n, rng)
        if e is None: continue
        apply_swap(adj, e)
        new = score(obj_lex(adj, n))
        T = T0 * (T1 / T0) ** (t / steps)
        d = (new - cur) / max(1.0, abs(cur) or 1.0)
        if new <= cur or rng.random() < pow(2.718281828, -min(50, d / T)):
            cur = new
            if new < best: best, best_adj = new, [list(a) for a in adj]
        else:
            undo_swap(adj, e)
    return dict(n=n, seed=seed, best=best, spectrum=obj_lex(best_adj, n), adj=best_adj)

if __name__ == '__main__':
    NS = [int(x) for x in sys.argv[1].split(',')]
    RESTARTS = int(sys.argv[2]); STEPS = int(sys.argv[3])
    jobs = [(n, s, STEPS) for n in NS for s in range(RESTARTS)]
    t0 = time.time()
    with mp.Pool(min(8, os.cpu_count())) as p:
        res = [r for r in p.imap_unordered(anneal, jobs) if r]
    by = {}
    for r in res: by.setdefault(r['n'], []).append(r)
    print(f"{'n':>4} {'restarts':>9} {'best (c4,c8,c16)':>20} {'#hit best':>10}")
    out = []
    for n in sorted(by):
        rs = sorted(by[n], key=lambda r: r['best'])
        b = rs[0]
        nhit = sum(1 for r in rs if r['best'] == b['best'])
        print(f"{n:>4} {len(rs):>9} {str(b['spectrum']):>20} {nhit:>10}", flush=True)
        out.append(dict(n=n, best=b['best'], spectrum=list(b['spectrum']), adj=b['adj'], nhit=nhit))
        if b['best'] == 0:
            print(f"  *** n={n}: ZERO forbidden cycles -- CANDIDATE COUNTEREXAMPLE ***")
            json.dump(b['adj'], open(f'candidate_n{n}.json', 'w'))
    json.dump(out, open('sweep_results.json', 'w'))
    print(f"elapsed {time.time()-t0:.0f}s over {len(jobs)} restarts")
