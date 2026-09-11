"""
Erdos problem #64 / Erdos-Gyarfas conjecture ($1000, still open, Lean-formalised, no AI
solution on record) as a swarm task.

    Does every finite graph with minimum degree >= 3 contain a cycle of length 2^k, k >= 2?

A counterexample is a finite graph with min degree >= 3 and no cycle of length 4, 8, 16, 32...
C3 is allowed; only powers of two from 4 up are forbidden.

The proposer does NOT emit a graph. It emits a *constructor* -- a Python function that builds
a graph for a given n. That is the FunSearch shape and it is the right one here: a raw
adjacency list is a point, a constructor is a region, and the LLM's real advantage is in
writing structured code rather than in emitting 90 integers without a typo.

The verifier is the whole gate, so it is the part that must be right. Cycle counting is done
by explicit path enumeration with a canonical representative rather than any algebraic
shortcut that could silently count closed walks instead of cycles, and it is self-tested
against three graphs with published cycle spectra (K4, K_{3,3}, Petersen) before use.
"""
from __future__ import annotations
import sys, os, re, multiprocessing as mp
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'erdos64'))
from core import Task, Verdict, Candidate
from search import count_cycles_of_length          # the audited counter

FORBIDDEN = (4, 8, 16, 32)
NS = (20, 26, 30)                                   # sizes every constructor is scored on

SAFE_BUILTINS = {'range': range, 'len': len, 'sum': sum, 'abs': abs, 'min': min, 'max': max,
                 'sorted': sorted, 'enumerate': enumerate, 'int': int, 'float': float,
                 'list': list, 'set': set, 'tuple': tuple, 'dict': dict, 'zip': zip,
                 'any': any, 'all': all, 'pow': pow, 'round': round, 'divmod': divmod,
                 'reversed': reversed, 'map': map, 'filter': filter}


def _selftest():
    K4 = [[1, 2, 3], [0, 2, 3], [0, 1, 3], [0, 1, 2]]
    K33 = [[3, 4, 5], [3, 4, 5], [3, 4, 5], [0, 1, 2], [0, 1, 2], [0, 1, 2]]
    PET = [[1, 4, 5], [0, 2, 6], [1, 3, 7], [2, 4, 8], [0, 3, 9],
           [0, 7, 8], [1, 8, 9], [2, 5, 9], [3, 5, 6], [4, 6, 7]]
    assert count_cycles_of_length(K4, 4, 4) == 3
    assert count_cycles_of_length(K33, 6, 4) == 9 and count_cycles_of_length(K33, 6, 6) == 6
    assert count_cycles_of_length(PET, 10, 4) == 0 and count_cycles_of_length(PET, 10, 5) == 12
    return True


def _run_child(src, n, q):
    ns = {'__builtins__': SAFE_BUILTINS}
    try:
        exec(compile(src, '<proposal>', 'exec'), ns)
        g = ns['build'](n)
        g = [sorted(set(int(x) for x in row)) for row in g]
        q.put(g)
    except Exception as e:
        q.put(('ERR', f'{type(e).__name__}: {str(e)[:120]}'))


def _build(src, n, timeout=10.0):
    """Generated code runs in a forked child: there is no way to bound arbitrary Python from
    inside the same process, so the timeout has to live at the process boundary. 5% of
    LLM-generated functions in the earlier run were pathological enough to wedge the evaluator."""
    q = mp.Queue()
    p = mp.Process(target=_run_child, args=(src, n, q))
    p.start(); p.join(timeout)
    if p.is_alive():
        p.terminate(); p.join(1)
        return ('ERR', 'timeout')
    try:
        return q.get_nowait()
    except Exception:
        return ('ERR', 'no output')


def _check_graph(g, n):
    if not isinstance(g, list) or len(g) != n:
        return f'expected {n} adjacency rows, got {len(g) if isinstance(g, list) else type(g).__name__}'
    for v, row in enumerate(g):
        for w in row:
            if not (0 <= w < n):
                return f'vertex {v} adjacent to out-of-range {w}'
            if w == v:
                return f'self-loop at {v}'
            if v not in g[w]:
                return f'asymmetric: {v}-{w} present one way only'
    d = min(len(r) for r in g)
    if d < 3:
        return f'min degree {d} < 3'
    return None


class Erdos64(Task):
    name = 'erdos64'
    descriptor_axes = ('girth', 'log2(c8+1)', 'degree profile')

    def __init__(self):
        _selftest()

    def prompt(self, parents: list[Candidate], deadends: list[str]) -> str:
        p = f"""Erdos-Gyarfas conjecture: every finite graph with minimum degree >= 3 contains a
cycle whose length is a power of two (4, 8, 16, 32, ...). It is open and carries a $1000 prize.

A counterexample would be a finite graph with minimum degree >= 3 and NO cycle of length
4, 8, 16 or 32. Cycles of length 3, 5, 6, 7, 9, ... are all fine -- only powers of two are forbidden.

Write a Python function, and nothing else:

    def build(n):
        # returns an adjacency list: a list of n lists, build(n)[v] = neighbours of v
        # every vertex must have degree >= 3; the graph must be simple and undirected

It will be scored on n = {', '.join(map(str, NS))} by counting cycles of forbidden length.
Fewer is better; zero at any n settles the conjecture.

Only Python builtins, no imports. Be concrete and structural -- name the construction you are
using (cage graph, incidence graph of a generalised polygon, Cayley graph of some group,
lift of a small graph, girth-5 cubic construction, etc). Deterministic output."""
        if deadends:
            p += ("\n\nThese construction families have already been refuted by the verifier -- "
                  "they produce forbidden cycles, do not propose them again:\n"
                  + "\n".join(f"  - {d}" for d in deadends))
        if parents:
            p += "\n\nPrevious constructions and their forbidden-cycle counts:\n"
            for i, c in enumerate(parents):
                ev = c.payload.get('note', '')
                p += f"\n# attempt {i}: {ev}\n{c.payload['src']}\n"
            p += "\nWrite a better one. Code only."
        return p

    def parse(self, raw: str):
        t = re.sub(r'^```(?:python)?|```$', '', raw.strip(), flags=re.M).strip()
        m = re.search(r'(def build\s*\(.*)', t, re.S)
        if not m:
            return None
        return dict(src=m.group(1), note='')

    def verify(self, payload) -> Verdict:
        src = payload['src']
        per_n, total = {}, 0
        girths = []
        for n in NS:
            g = _build(src, n)
            if isinstance(g, tuple):
                return Verdict(False, False, -1e9, (), reason=f'n={n}: {g[1]}')
            err = _check_graph(g, n)
            if err:
                return Verdict(False, False, -1e9, (), reason=f'n={n}: {err}')
            counts = {}
            for L in FORBIDDEN:
                if L <= n:
                    counts[L] = count_cycles_of_length(g, n, L)
                    if counts[L] > 0:
                        break                      # cheap terms first, expensive ones skipped
            per_n[n] = counts
            total += sum(counts.values())
            gi = next((L for L in range(3, min(n, 12) + 1)
                       if count_cycles_of_length(g, n, L) > 0), 99)
            girths.append(gi)
        solved = total == 0
        payload['note'] = ' '.join(f'n={n}:{per_n[n]}' for n in NS)
        # LEXICOGRAPHIC score, not a plain sum. A plain sum plus early exit is actively wrong:
        # a graph with three 4-cycles stops counting there and scores -3, beating a graph that
        # has killed C4 and C8 entirely but still has 200 C16s. That ranks the worse graph
        # higher and would steer the whole search backwards. Weight by cycle length so that
        # eliminating a shorter forbidden cycle always dominates.
        lex = 0.0
        for n in NS:
            for L, c in per_n[n].items():
                lex += c * (10.0 ** (12 - 2 * FORBIDDEN.index(L)))
        desc = (min(girths), min(6, int(total).bit_length()),
                tuple(sorted(per_n[NS[0]].keys()))[:1])
        return Verdict(True, solved, -lex, desc,
                       evidence=dict(per_n={str(k): v for k, v in per_n.items()},
                                     girth=min(girths)),
                       reason='' if solved else f'{total} forbidden cycles')

    def deadend_key(self, payload, v: Verdict) -> str | None:
        if not v.ok:
            # malformed proposals are noise, not refuted mathematics
            return None
        if v.solved:
            return None
        ev = v.evidence.get('per_n', {})
        first = next(iter(ev.values()), {})
        L = next(iter(first), None)
        g = v.evidence.get('girth')
        if L is None:
            return None
        head = payload['src'].split('\n')[1:4]
        hint = next((h.strip('# ').strip() for h in head if h.strip().startswith('#')), '')
        return (f'girth-{g} construction'
                + (f' ({hint[:60]})' if hint else '')
                + f' -> has {L}-cycles')
