"""
2x2x2 factorial over the axes that actually exist, replacing the seven-policy beauty contest.

The seven policies (islands / map_elites / novelty / flat_elite / ...) all vary ONE thing --
which subset of past attempts goes in the prompt. That is a variation on a published system's
garnish, not a first-principles decomposition. Strip it down and there are three axes:

  H  history   does a call see anything from previous calls?
  D  depth     200 independent shots, or 20 lineages refined 10 deep?
  E  effort    how much compute inside a single call?

Two of the three have never been tested in this project. Worse, E was silently pinned: every
one of the ~1400 calls so far ran at reasoning_effort=low, because an early bug (the model
burning its whole budget on hidden reasoning and returning empty content) was fixed by pinning
effort low and then never revisited. A variable that was turned into a constant by a bugfix is
the most dangerous kind of uncontrolled variable, because nothing in the logs looks wrong.

D is the axis the "nobody lets them run long enough" argument is actually about. Everything
measured here so far is breadth: independent shots, no lineage deeper than one refinement step.

Design: 8 cells, equal call budget per cell so wall-clock differences do not confound. Depth
cells spend the same number of calls, arranged as lineages instead of singletons.
"""
from __future__ import annotations
import sys, os, json, time, random, threading, itertools, argparse, statistics
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core import Archive, Ledger, DeadEnds, Metrics, Candidate
from pool import Pool
from run import load_task


def run_cell(task, pool, family, calls, history, depth, effort, seed, outdir, concurrency,
             lineage_len=10):
    """One factorial cell. `calls` is the budget and is identical across cells."""
    os.makedirs(outdir, exist_ok=True)
    arch = Archive(n_islands=5)
    ledger = Ledger(os.path.join(outdir, 'ledger.jsonl'))
    dead = DeadEnds(os.path.join(outdir, 'deadends.jsonl'))
    met = Metrics()
    pool.effort = effort
    lock = threading.Lock()
    counter = [0]
    scores, sigs = [], set()
    traj = []

    def one_call(parents, r, fam):
        raw = pool.chat(fam, [{"role": "user", "content": task.prompt(parents, [])}])
        payload = task.parse(raw) if raw else None
        if payload is None:
            met.note(fam)
            return None, None
        v = task.verify(payload)
        c = Candidate(payload=payload, source='w', family=fam,
                      parents=[Ledger.aid(p.payload) for p in parents])
        ledger.record(c, v)
        met.note(fam, parsed=True, verified=v.ok, solved=v.solved)
        if v.ok:
            with lock:
                scores.append(v.score)
                sigs.add(v.descriptor)
                traj.append((len(scores), max(scores), len(sigs)))
        return c, v

    def worker(wid):
        r = random.Random(seed * 977 + wid)
        while True:
            with lock:
                if counter[0] >= calls:
                    return
                budget = min(lineage_len if depth else 1, calls - counter[0])
                counter[0] += budget
            fam = family
            if depth:
                # one lineage: each step refines THIS worker's own previous attempt.
                # Distinct from `history`, which samples a shared population.
                chain = []
                for _ in range(budget):
                    parents = chain[-1:] if (history and chain) else []
                    c, v = one_call(parents, r, fam)
                    if c is not None and v is not None and v.ok:
                        island = wid % arch.n_islands
                        arch.admit(island, c, v)
                        chain.append(c)
            else:
                island = wid % arch.n_islands
                parents = arch.sample_parents(island, 2, r) if history else []
                c, v = one_call(parents, r, fam)
                if c is not None and v is not None and v.ok:
                    arch.admit(island, c, v)

    ts = [threading.Thread(target=worker, args=(k,)) for k in range(concurrency)]
    t0 = time.time()
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    snap = met.snapshot(arch, dead)
    snap.update(history=history, depth=depth, effort=effort, seed=seed,
                wall=round(time.time() - t0), usage=pool.report(),
                best=max(scores) if scores else 0.0,
                mean=statistics.mean(scores) if scores else 0.0,
                n_valid=len(scores), n_sigs=len(sigs))
    json.dump(snap, open(os.path.join(outdir, 'metrics.json'), 'w'), indent=1)
    json.dump(traj, open(os.path.join(outdir, 'traj.json'), 'w'))
    return snap


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('task')
    ap.add_argument('--calls', type=int, default=100)
    ap.add_argument('--seeds', type=int, default=2)
    ap.add_argument('--family', default='sol')
    ap.add_argument('--concurrency', type=int, default=16)
    ap.add_argument('--out', default=os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'runs', 'factorial'))
    a = ap.parse_args()

    task = load_task(a.task)
    rows = []
    for hist, dep, eff in itertools.product((False, True), (False, True), ('low', 'high')):
        cell = f"H{int(hist)}D{int(dep)}E{eff}"
        per = []
        for s in range(a.seeds):
            # NB: no max_tokens override. An earlier version pinned high effort to 6000 and
            # every high-effort cell scored 0/8 -- the model spent all 6000 tokens on hidden
            # reasoning and returned empty content, which the main-effect table then read as
            # "high effort is worse". Pool derives the budget from effort; let it.
            pool = Pool(families=(a.family,), concurrency=a.concurrency, effort=eff)
            snap = run_cell(task, pool, a.family, a.calls, hist, dep, eff, s,
                            os.path.join(a.out, f'{cell}_s{s}'), a.concurrency)
            per.append(snap)
            print(f"  {cell} s{s}  best={snap['best']:.4f} mean={snap['mean']:.4f} "
                  f"valid={snap['n_valid']}/{a.calls} sigs={snap['n_sigs']} "
                  f"wall={snap['wall']}s", flush=True)
        rows.append(dict(cell=cell, history=hist, depth=dep, effort=eff,
                         best=statistics.mean(r['best'] for r in per),
                         best_sd=statistics.pstdev([r['best'] for r in per]),
                         mean=statistics.mean(r['mean'] for r in per),
                         valid=statistics.mean(r['n_valid'] for r in per),
                         sigs=statistics.mean(r['n_sigs'] for r in per),
                         wall=statistics.mean(r['wall'] for r in per)))
        json.dump(rows, open(os.path.join(a.out, 'summary.json'), 'w'), indent=1)

    print(f"\n{'cell':>10} {'hist':>5} {'depth':>6} {'effort':>7} {'best':>8} {'sd':>7} "
          f"{'mean':>7} {'valid':>6} {'sigs':>5} {'wall':>6}")
    for r in sorted(rows, key=lambda x: -x['best']):
        print(f"{r['cell']:>10} {str(r['history']):>5} {str(r['depth']):>6} {r['effort']:>7} "
              f"{r['best']:>8.4f} {r['best_sd']:>7.4f} {r['mean']:>7.4f} {r['valid']:>6.0f} "
              f"{r['sigs']:>5.0f} {r['wall']:>6.0f}")
    # main effects: the point of a factorial is that each axis is estimated from all 8 cells
    print("\n--- main effects on best (averaged over the other two axes) ---")
    for name, key in (('history', 'history'), ('depth', 'depth'), ('effort', 'effort')):
        vals = {}
        for r in rows:
            vals.setdefault(r[key], []).append(r['best'])
        parts = '  '.join(f"{k}={statistics.mean(v):.4f}" for k, v in sorted(vals.items(), key=str))
        lo, hi = [statistics.mean(v) for _, v in sorted(vals.items(), key=str)]
        print(f"  {name:>8}: {parts}   delta={hi-lo:+.4f}")
