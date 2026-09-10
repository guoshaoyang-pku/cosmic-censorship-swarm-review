"""
Main loop. Islands of proposers, a verifier gate, a retractable ledger, a dead-end broadcast,
and instrumentation that can tell exploration from collapse.

Usage:
    python3 run.py erdos64 --calls 120 --islands 5 --families sol,qwenmax,o50
    python3 run.py erdos64 --calls 120 --families sol            # single-family control

The single-family control is not optional garnish. Every claim this project has made about
heterogeneity has been overturned by measurement at least once, in both directions, so any
run that mixes families must be paired with one that does not.
"""
from __future__ import annotations
import sys, os, json, time, random, threading, argparse, importlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core import Archive, Ledger, DeadEnds, Metrics, Candidate
from pool import Pool


def load_task(name):
    m = importlib.import_module(f'tasks.{name}')
    cls = next(v for k, v in vars(m).items()
               if isinstance(v, type) and getattr(v, 'name', None) == name)
    return cls()


def run(task_name, calls, islands, families, seed, outdir, concurrency, parents_per_prompt):
    os.makedirs(outdir, exist_ok=True)
    task = load_task(task_name)
    pool = Pool(families=families, concurrency=concurrency)
    live = [f for f, s in pool.probe().items() if s == 'ok']
    if not live:
        print('no live proposer families; aborting', file=sys.stderr)
        return
    print(f'live families: {live}', flush=True)

    arch = Archive(n_islands=islands)
    ledger = Ledger(os.path.join(outdir, 'ledger.jsonl'))
    dead = DeadEnds(os.path.join(outdir, 'deadends.jsonl'))
    met = Metrics()
    rng = random.Random(seed)
    lock = threading.Lock()
    counter = [0]
    found = threading.Event()

    def worker(wid):
        r = random.Random(seed * 977 + wid)
        while not found.is_set():
            with lock:
                if counter[0] >= calls:
                    return
                i = counter[0]
                counter[0] += 1
            island = i % islands
            fam = pool.pick(r, live)
            parents = arch.sample_parents(island, parents_per_prompt, r)
            raw = pool.chat(fam, [{"role": "user",
                                   "content": task.prompt(parents, dead.recent())}])
            payload = task.parse(raw) if raw else None
            if payload is None:
                met.note(fam)
                continue
            v = task.verify(payload)
            cand = Candidate(payload=payload, source=f'w{wid}', family=fam,
                             parents=[Ledger.aid(p.payload) for p in parents], raw=raw[:2000])
            aid = ledger.record(cand, v)
            adm = arch.admit(island, cand, v)
            dead.add(task.deadend_key(payload, v))
            met.note(fam, parsed=True, verified=v.ok, admitted=adm, solved=v.solved)
            if v.solved:
                json.dump(dict(id=aid, payload=payload, evidence=v.evidence),
                          open(os.path.join(outdir, 'SOLVED.json'), 'w'), indent=1)
                print(f'\n*** SOLVED by {fam} (artifact {aid}) ***\n', flush=True)
                found.set()
            if (i + 1) % 20 == 0:
                s = met.snapshot(arch, dead)
                bs, _ = arch.best()
                print(f"  [{i+1:>4}/{calls}] best={bs:.0f} cov={s['coverage']:>3} "
                      f"redun={s['redundancy']:.2f} late={s['late_growth']:+d} "
                      f"verified={s['verified']}/{s['calls']} "
                      f"deadends={s['deadends']}(hit {s['deadend_hits']})", flush=True)

    ts = [threading.Thread(target=worker, args=(k,)) for k in range(concurrency)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()

    snap = met.snapshot(arch, dead)
    snap['usage'] = pool.report()
    bs, bc = arch.best()
    snap['best_score'] = bs
    if bc:
        snap['best_note'] = bc.payload.get('note', '')
        json.dump(bc.payload, open(os.path.join(outdir, 'best.json'), 'w'), indent=1)
    json.dump(snap, open(os.path.join(outdir, 'metrics.json'), 'w'), indent=1)
    print('\n=== run summary ===')
    print(json.dumps({k: v for k, v in snap.items() if k != 'usage'}, indent=1,
                     ensure_ascii=False))
    print('per-family:', json.dumps(snap['by_family'], ensure_ascii=False))
    return snap


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('task')
    ap.add_argument('--calls', type=int, default=60)
    ap.add_argument('--islands', type=int, default=5)
    ap.add_argument('--families', default='sol,qwenmax,o50')
    ap.add_argument('--seed', type=int, default=0)
    ap.add_argument('--concurrency', type=int, default=6)
    ap.add_argument('--parents', type=int, default=2)
    ap.add_argument('--out', default=None)
    a = ap.parse_args()
    out = a.out or f'/Users/bytedance/ai4math-swarm/runs/{a.task}_{a.families.replace(",","+")}_s{a.seed}_{int(time.time())}'
    run(a.task, a.calls, a.islands, a.families.split(','), a.seed, out,
        a.concurrency, a.parents)
