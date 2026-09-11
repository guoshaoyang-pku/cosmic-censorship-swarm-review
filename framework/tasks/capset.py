"""
Cap set as a framework task -- the CALIBRATION instrument, not the target.

Methodology: characterise the architecture tournament on a problem whose landscape is already
mapped (this project has ~2000 LLM calls of history on it, a known iid-random floor of 0.824,
and a known LLM ceiling around 0.870-0.89), then point the winning architecture at the real
open problem. Running the tournament directly on Erdos #64 would confound "which architecture
is better" with "how hard is #64".

A cap set in Z_3^n has no three distinct elements summing to zero. Greedy construction ordered
by a priority function; the proposer writes the priority function. This is the original
FunSearch task, so the numbers are comparable to published work and to everything measured
here earlier.
"""
from __future__ import annotations
import sys, os, re, itertools, multiprocessing as mp
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import Task, Verdict, Candidate

NS = (4, 5, 6)
OPTIMA = {4: 20, 5: 45, 6: 112}
SAFE = {'range': range, 'len': len, 'sum': sum, 'abs': abs, 'min': min, 'max': max,
        'sorted': sorted, 'enumerate': enumerate, 'float': float, 'int': int, 'pow': pow,
        'zip': zip, 'tuple': tuple, 'list': list, 'set': set, 'dict': dict, 'any': any,
        'all': all, 'round': round, 'divmod': divmod, 'map': map, 'filter': filter}

_VEC = {}


def all_vectors(n):
    if n not in _VEC:
        _VEC[n] = list(itertools.product((0, 1, 2), repeat=n))
    return _VEC[n]


def _child(body, q):
    src = "def priority(v, n):\n" + body + "\n"
    ns = {'__builtins__': SAFE}
    try:
        exec(compile(src, '<p>', 'exec'), ns)
        f = ns['priority']
        sizes = []
        for n in NS:
            vs = sorted(all_vectors(n), key=lambda v: -float(f(v, n)))
            chosen, cs = [], set()
            for v in vs:
                ok = True
                for a in chosen:
                    t = tuple((-(v[i] + a[i])) % 3 for i in range(n))
                    if t in cs and t != a:
                        ok = False
                        break
                if ok:
                    chosen.append(v)
                    cs.add(v)
            sizes.append(len(chosen))
        q.put(tuple(sizes))
    except Exception as e:
        q.put(('ERR', f'{type(e).__name__}: {str(e)[:100]}'))


def _evaluate(body, timeout=8.0):
    q = mp.Queue()
    p = mp.Process(target=_child, args=(body, q))
    p.start(); p.join(timeout)
    if p.is_alive():
        p.terminate(); p.join(1)
        return ('ERR', 'timeout')
    try:
        return q.get_nowait()
    except Exception:
        return ('ERR', 'no output')


class CapSet(Task):
    name = 'capset'
    descriptor_axes = ('cap set sizes at n=4,5,6',)

    def prompt(self, parents, deadends) -> str:
        p = f"""A cap set in Z_3^n is a subset with no three DISTINCT elements summing to
(0,...,0) mod 3. Build one greedily: sort all 3^n vectors by a priority function (descending),
add each vector if it keeps the set a cap set. Larger is better.
Known optima: n=4 -> 20, n=5 -> 45, n=6 -> 112.

Write the BODY of this function (no def line, no imports, no markdown fence, no prose):

    def priority(v: tuple[int, ...], n: int) -> float:

`v` is a tuple of n values in {{0,1,2}}. Return a float. Deterministic. Builtins only.
Use exactly 4-space indentation on every line."""
        if deadends:
            p += ("\n\nThese scoring patterns have already been reached and are not improvements;"
                  " do not reproduce them:\n" + "\n".join(f"  - {d}" for d in deadends))
        if parents:
            p += "\n\nPrevious attempts and the cap set sizes they produced:\n"
            for i, c in enumerate(parents):
                p += f"\n# version {i}, sizes at n=4,5,6: {c.payload['sig']}\ndef priority_v{i}(v, n):\n{c.payload['body']}\n"
            p += "\nWrite an improved version. Body only."
        return p

    def parse(self, raw: str):
        t = re.sub(r'^```(?:python)?|```$', '', raw.strip(), flags=re.M).strip()
        t = re.sub(r'^\s*def priority[^\n]*\n', '', t)
        lines = [l for l in t.split('\n') if l.strip() and not l.strip().startswith('#')]
        if not lines:
            return None
        body = '\n'.join('    ' + l.lstrip() if not l.startswith('    ') else l for l in lines)
        return dict(body=body, sig=None)

    def verify(self, payload) -> Verdict:
        r = _evaluate(payload['body'])
        if isinstance(r, tuple) and r and r[0] == 'ERR':
            return Verdict(False, False, -1e9, (), reason=r[1])
        sizes = r
        payload['sig'] = sizes
        score = sum(s / OPTIMA[n] for s, n in zip(sizes, NS)) / len(NS)
        # descriptor IS the score signature, exactly as FunSearch does it: behaviour is what
        # the object does on the tests, not a hand-designed axis. On this task that is known
        # to have real resolution because the three n give an ordered triple.
        return Verdict(True, sizes[-1] >= OPTIMA[6], score, tuple(sizes),
                       evidence=dict(sizes=list(sizes)))

    def deadend_key(self, payload, v: Verdict):
        if not v.ok or v.score > 0.86:
            return None
        return f"sizes {payload['sig']} (score {v.score:.3f})"
