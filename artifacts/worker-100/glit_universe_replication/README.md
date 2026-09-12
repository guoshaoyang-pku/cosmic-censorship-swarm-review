# artifacts/worker-100/glit_universe_replication

Bounded class-bound task **W100-GLIT-UNIVERSE-REPL-01** (worker-100, node L1, gate G-LIT):
independent non-author replication of worker-075's source-meta / "measured universe" census at
the pinned bytes. Read `REPLICATION.md` first.

| file | role |
|---|---|
| `PREREGISTRATION.json` | rules, comparisons, controls and the A1 control amendment, fixed before the full measurement |
| `replicate_census_100.py` | independent stdlib-only instrument (`--selftest`, `--verify`) |
| `replication_report.json` | machine result: pins T0/T1, universes, comparisons, controls, 201 reconciliation |
| `REPLICATION.md` | human summary, findings, falsifier, recommended gate denominators |
| `raw/inputs_hashes_t0.json`, `raw/inputs_hashes_t1.json` | per-file sha256 of the 43 census inputs before/after |
| `make_manifest.py`, `MANIFEST.json` | deliverable hashes |

Reproduce:

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-100/glit_universe_replication/replicate_census_100.py --selftest
python3 artifacts/worker-100/glit_universe_replication/replicate_census_100.py
python3 artifacts/worker-100/glit_universe_replication/replicate_census_100.py --verify
```

Verdict: `PARTIAL` under the pre-registered rule (primary per-class reading differs); all nine
headline universes, the 0-axis result, record-kind classification and the "201 is not a universe"
reconciliation reproduce exactly, and the per-class split reproduces exactly under the target's
own exact-token rule. No gate verdict; worker evidence only.
