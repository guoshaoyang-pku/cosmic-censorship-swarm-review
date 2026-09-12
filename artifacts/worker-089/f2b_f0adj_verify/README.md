# W089-F2B-F0ADJ-02 — F0 mirror-conflict dependency verification (F2b / AF-SCC-C0-VAC-GEN)

Worker: `worker-089`. One bounded, class-bound, mechanical task. No canonical or frozen
artifact was modified.

## Why this task

`artifacts/formulation/FROZEN.json` rev26 records that F0 publication was **withheld**:
`research_map/formulation_taxonomy.yaml` (declared F0, `276009f4f63d`) and
`artifacts/formulation/formulation_taxonomy.yaml` (class-contract supplement, `c8e979a1eb48`)
are claimed to be two *different* artifacts, so making them byte-identical would destroy a
frozen input (`artifacts/formulation/evidence/f0_mirror_conflict.json`, REC-1/REC-2).
That claim is produced by the same party that requests the adjudication. This task verifies
it independently **as it binds the frozen F2b class** (`schemas/af_scc_c0_vacuum.yaml`,
`1bb78ce9b357`), whose `class_contract_pointer` and `f0_binding` straddle both artifacts.

## What was verified (11 checks, all pass)

| id | check |
|---|---|
| C1 | 5/5 hash pins match measured bytes; the conflict evidence's own path/hash/byte measurements match live files |
| C2 | canonical carries `class_ids`/`classes`/`transfer_rules`, lacks `class_contracts`/`axis_registry`/`implication_ledger` |
| C3 | supplement carries `class_contracts`/`axis_registry`/`implication_ledger`, lacks `class_ids`/`classes`/`transfer_rules` |
| C4 | F2b `class_contract_pointer` resolves to a full class contract in the supplement |
| C5 | the same fragment does **not** resolve in the canonical taxonomy (pointer is load-bearing) |
| C6 | F2b `f0_binding` paths + declared hash equal measured bytes |
| C7 | all three frozen schemas resolve into the supplement and bind measured canonical |
| C8 | structural simulation: replacing either file with the other loses its unique roles; the pointer dangles |
| C9 | FROZEN rev26 pins canonical/supplement/F2b hashes == measured; both logical artifacts declare `mirrors: NONE` |
| C10 | `check_taxonomy_consistency.py` statically consumes keys from **both** artifacts; pinned consistency evidence is CONSISTENT over 4 classes |
| C11 | the conflict evidence's quoted schema pointers/bindings equal the live schema fields |

**Verdict: `accept`** for the mechanical dependency claims (11/11 checks; 9/9 controls).
This is *not* a semantic review, *not* an adjudication of REC-1 vs REC-2, and *not* a
G-F0 / G-FORM gate accept.

## Controls (planted defects, in-memory only)

M1 canonical gains `class_contracts`; M2 supplement loses `class_contracts`; M3 F2b declared
F0 hash corrupted; M4 F2b pointer repointed at canonical; M5 canonical loses `classes`;
M6 supplement gains `class_ids`; M7 FROZEN logical-artifact hash corrupted; M8 F2b pointer
repointed at the schema itself. All eight are caught; the unmutated baseline (N0) passes all
eleven checks, so the pass is controlled against false positives.

## Measured pins (2026-09-12, stability window 60 s / 10 s, no drift)

| artifact | sha256 (prefix) |
|---|---|
| `schemas/af_scc_c0_vacuum.yaml` | `1bb78ce9b357` |
| `research_map/formulation_taxonomy.yaml` | `276009f4f63d` |
| `artifacts/formulation/formulation_taxonomy.yaml` | `c8e979a1eb48` |
| `artifacts/formulation/FROZEN.json` (rev26) | `2554e276a0db` |
| `artifacts/formulation/evidence/f0_mirror_conflict.json` | `7e3a7bc89a75` |

## Notes / limits

- The conflict evidence cites FROZEN **rev25**; the measured manifest is **rev26**. Both hash
  pins are unchanged, so the claim holds, but the evidence file is not re-based. Recorded as a
  soft drift note, not a failure.
- `check_taxonomy_consistency.py` writes its own evidence file when executed; this audit
  inspected it statically and did not execute it. The pinned evidence hash matches FROZEN.
- Anyone re-running after republication must re-measure; a hash move voids the binding.

## Falsifier

Any of: a measured taxonomy hash differs from the cited value; the F2b pointer fragment
resolves in the canonical taxonomy; the canonical gains a supplement-only key or the
supplement gains a canonical-only key; FROZEN stops matching measured bytes; any control
stops being caught or the baseline fails.

## Re-run

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-089/f2b_f0adj_verify/check_f2b_f0adj.py --window 60 --interval 10
```

## Files

- `check_f2b_f0adj.py` — deterministic, read-only checker (stdlib + PyYAML)
- `f0adj_report.json` — full report (checks, controls, notes, stability, falsifier)
- `controls/*.json` — per-mutant outcomes
- `pinned/` — byte-exact snapshots of the two taxonomies, FROZEN rev26, and the evidence file
- `run_console.log`, `events.jsonl` — console record and emitted events
