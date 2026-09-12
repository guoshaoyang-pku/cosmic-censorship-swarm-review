# W045-CONSISTENCY-EVIDENCE-BINDING-01

Bounded class-bound worker task (worker-045, fleet instance 2026-09-12T00:37:14).
Class binding: `AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN` on nodes
F0/F1/F2a/F2b. Read-only on every canonical path.

## Why this task

The three frozen class artifacts (F1, F2a, F2b) each carry an `f0_binding` block
whose rule says the consistency check must be re-run and the binding refreshed
whenever the declared F0 artifact changes hash. Concurrent workers (082, 092, 095)
reported the declared `consistency_evidence_sha256` no longer matching the
canonical evidence file, and one (082) reported the canonical file had lost
fields. Nobody had measured the whole chain at one instant across all three
classes, or asked whether the canonical evidence can bind its inputs at all.
This task does exactly that, with pre-registered controls.

## Pins (one measured instant; all five controls re-hash them at exit)

| path | sha256 (16) |
|---|---|
| `research_map/formulation_taxonomy.yaml` (F0 canonical, rev5) | `0abb9ed8a96135c9` |
| `artifacts/formulation/formulation_taxonomy.yaml` (supplement) | `d7419b4e8963cb71` |
| `schemas/af_wcc_vacuum.yaml` (F1, rev12) | `cce9c60146d6a907` |
| `schemas/af_scc_c2_vacuum.yaml` (F2a, rev12) | `5476a3f2c6bc7196` |
| `schemas/af_scc_c0_vacuum.yaml` (F2b, rev12) | `55d0a1ea9bda96b8` |
| `artifacts/formulation/evidence/taxonomy_consistency.json` | `9e335e9ba1bfcf77` |
| `artifacts/formulation/FROZEN.json` (rev28) | `2f358f6722d92062` |
| `artifacts/formulation/tools/check_taxonomy_consistency.py` | `de356d999ea3b6ae` |

## Result — verdict REVISE (5 findings, 0 controls failed)

Per-class declaration table (all three identical):

| node | class | declared_f0 == live F0 | pointer resolves | frozen rev28 pin matches live | declared evidence pin == live evidence |
|---|---|---|---|---|---|
| F1 | AF-WCC-VAC-GEN | yes | yes | yes | **no** (`675a99d0` vs `9e335e9b`) |
| F2a | AF-SCC-C2-VAC-GEN | yes | yes | yes | **no** |
| F2b | AF-SCC-C0-VAC-GEN | yes | yes | yes | **no** |

- **F-1 (major, uniform).** All three schemas declare `consistency_evidence_sha256
  = 675a99d0d25b2b37`; the canonical path measures `9e335e9ba1bfcf77`.
- **F-2 (major, frozen-corpus contradiction).** `FROZEN.json` rev28 pins the same
  path at `9e335e9b` while the schemas it freezes declare `675a99d0`. One path,
  two mutually exclusive pins inside one frozen revision.
- **F-3 (major, input-unbound evidence).** The canonical evidence records the two
  input *paths* but no `map_taxonomy_sha256` / `lead_contract_sha256`. The enriched
  rev12 variant that the schemas still declare *does* carry both, and they equal
  the live F0 (`0abb9ed8`) and supplement (`d7419b4e`). So the bytes the schemas
  point at can no longer show which F0 revision they evaluated; the bytes that
  can, are no longer at the canonical path.
- **F-4 (info).** The enriched `675a99d0` still exists on disk (e.g.
  `artifacts/worker-086/evidence_collision/restore_candidate/taxonomy_consistency.675a99d0d25b.json`).
  Re-pinning the schemas to the canonical bytes and restoring the enriched
  evidence are mutually exclusive without one further FROZEN move.
- **F-5 (major, control-derived).** Control C3: a re-serialised F0 with an added
  non-compared field leaves the evidence byte-identical to `9e335e9b`. The
  evidence hash is therefore not a byte-binding of F0 at all; the load-bearing
  input binding is each schema's `declared_f0_sha256`, which does equal live F0.

## Controls (pre-registered; `report.json.controls`)

| id | expectation | observed |
|---|---|---|
| C1 | two sandbox runs identical **and** equal to the live evidence hash | `9e335e9b` twice, exit 0 — reproduces live bytes |
| C2 | semantic F0 mutation (F2a `family`) → exit 1, `consistent=false`, new hash | `INCONSISTENT ... SCC_W045_MUTANT vs SCC`, new hash |
| C3 | non-compared edit + full re-serialisation → evidence byte-identical | identical `9e335e9b`, `consistent=true` |
| C4 | binding detector: UNBOUND(live), BOUND(enriched), MISMATCH(tampered) | all four subchecks true |
| C5 | no canonical file changes across the run | 9/9 hashes unchanged |

C3's initial expectation ("hash would move, consistency stay true") was wrong and
is recorded in the report rather than silently corrected; the observed invariance
is stronger evidence for F-5.

## Consequence and repair options (worker measurement, no edit made)

1. **Re-pin to canonical bytes.** Update the three schemas'
   `consistency_evidence_sha256` to `9e335e9b` and re-freeze atomically. Minimal,
   but permanently accepts path-only evidence: any future non-compared F0 edit
   is invisible to the evidence (C3), so the rule in `f0_binding` remains
   discharged only by the separate `declared_f0_sha256` field and by re-running
   the checker at freeze time.
2. **Restore the enriched evidence.** Make `check_taxonomy_consistency.py` emit
   `map_taxonomy_sha256`, `lead_contract_sha256`, and `measured_at` again, run it,
   then pin the resulting bytes (`675a99d0` if byte-identical to the archived
   variant) in all three schemas and FROZEN. Keeps provenance, costs one extra
   freeze cycle.
3. Doing neither leaves the frozen corpus internally contradictory (F-2): a
   hash-bound gate scan that checks schema declarations against FROZEN cannot
   pass.

Because of CF-4 ("checkers flag, never author") the choice is the formulation
lead's; this task changes no canonical byte.

## Falsifier

Falsified if any of: (a) at the pinned hashes some class artifact's
`f0_binding.consistency_evidence_sha256` equals the measured sha256 of its
declared `consistency_evidence` path; (b) FROZEN rev28's pin for
`artifacts/formulation/evidence/taxonomy_consistency.json` differs from the live
measured hash; (c) the canonical evidence file contains
`map_taxonomy_sha256`/`lead_contract_sha256` equal to the live F0/supplement
hashes, or the declared checker's output is changed by a non-compared F0 edit;
(d) the binding detector returns anything other than UNBOUND for the canonical
evidence, BOUND for the enriched variant, or MISMATCH for the tampered variant.

## Reproduction

```bash
cd artifacts/worker-045/consistency_evidence_binding
python3 run_consistency_evidence_binding.py   # exit 0 = all controls behaved; report on stdout
```

The declared checker rewrites its evidence output in place, so the runner never
executes it against the repository root: each run gets a sandbox copy under
`sandbox/`. C5 proves the canonical tree was untouched.

## Limitations / authority

Single instant; concurrent writers can move any pin (the falsifier is stated on
the pinned bytes, not on paths). The runner's glob over `artifacts/**` is used
only to locate archived copies of the declared variant, not as evidence of
authority. This is a worker-level measurement: it sets no node or gate status and
promotes no prose to a theorem.
