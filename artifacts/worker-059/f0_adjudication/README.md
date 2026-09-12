# W059-F0-ADJUDICATE-01 — F0 accept/revise adjudication at `276009f4f63d`

Worker `worker-059`, node **F0** (`AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH`),
gate `G-F0`. One bounded class-bound task, taken without an inbox card (none exists for worker-059;
the prior worker-059 task `W059-F1-INDEP-VERDICT-01` is complete and is **not** reused here).

## Why this task

Two independent verdicts on the same canonical F0 hash disagree:

| reviewer | verdict | score | date |
|---|---|---|---|
| `worker-040` (`W040-F0-INDEP-VERDICT-01`) | accept | 4.0 | 00:22:41 |
| `worker-082` (F0 independent verdict) | revise | 3.5 | 00:23:10 |

G-F0 needs two independent accepts at one hash, so the split is decision-relevant. This task
adjudicates it by re-measuring the disputed claims from pinned bytes — not by counting votes.

## What was measured (all at `276009f4f63d`, 35 145 bytes)

**Green baseline (independently reproduced, and by canonical tools as support):** strict
duplicate-key-free parse; exactly the four frozen class ids; 6/6 disjointness pairs separated on
their declared decisive axes; every class complete (hypotheses, exclusions, conclusion_type,
positive + negative test case); class-separation text scan `[]`; `validate_taxonomy.py` 253/253
over 37 cases; `classsep_regression.py` 17/17 leaks, 10/10 controls, FP 0 / FN 0.

**The two disputed defects are substantiated:**

1. **HF-059-F0-01** — `class_scope_adjudication.resolved_divergences[D3]` records status
   `resolved` with "the comeager quantifier is now stated explicitly in **each** class conclusion
   text". Only 3/4 do. The `AF-WCC-SCALAR-SPH` conclusion (lines 404–407) says "For generic data in
   the class…" while its own H4 (lines 397–401) declares the genericity notion unresolved, and
   `field_vocabulary.genericity_kind.rule` says "'generic' alone is not a machine-readable value".
2. **HF-059-F0-02** — the same conclusion asserts "…is complete; **equivalently**, the
   singularities that form are hidden behind an event horizon…", while `AF-WCC-VAC-GEN` states the
   same surface is "a definition, not an asserted equivalence (review HF-06)" and files the
   black-hole-interior statement as unresolved candidate consequence C1. Two WCC classes bind
   different conclusion strengths with no source and no bridge artifact.
3. **HF-059-F0-03 (certification)** — `check_taxonomy_consistency.py:59` hardcodes only
   `AF-SCC-C2-VAC-GEN`/`AF-SCC-C0-VAC-GEN` in its D3 condition and never passes
   `AF-WCC-SCALAR-SPH` to `ctext()` anywhere (AST coverage). Controlled experiment: the scalar
   D3 regression returns exit 0 `CONSISTENT`, while the identical C2/C0 regression returns exit 1
   `INCONSISTENT` (positive control fires). The `CONSISTENT` certification therefore cannot support
   an accept of D3 at this hash.

**Verdict: `revise`, score 3.0** — the taxonomy's structural surface is green, but two content
failures sit on the class-binding surface itself and the instrument that certified one of them is
blind to the class it certified.

## Artifacts

| artifact | purpose |
|---|---|
| `snapshot/f0.276009f4f63d.yaml` | immutable reviewed bytes |
| `adjudicate_f0.py` + `adjudication_checks.json` | independent checker (no canonical-tool imports) and its raw measurements |
| `blindspot_test.py` + `blindspot_test/blindspot_result.json` | control / mutant / positive-control experiment + AST coverage |
| `canonical_validate_taxonomy.json`, `canonical_classsep_findings.json`, `classsep_regression.stdout.txt` | supporting canonical-tool replays |
| `review_F0_276009f4.json` | review verdict, hard failures, findings, falsifier |
| `adjudication_report.json`, `hashes.json` | machine evidence + artifact hash table |
| `checkpoint_w059_f0adj.json` | worker-level checkpoint (`w059-ckpt-f0adj-20260912T0028`) |

## Reproduction

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-059/f0_adjudication/adjudicate_f0.py \
  artifacts/worker-059/f0_adjudication/snapshot/f0.276009f4f63d.yaml \
  /tmp/recheck.json
python3 artifacts/worker-059/f0_adjudication/blindspot_test.py
```

## Limits

- The verdict binds only `sha256 276009f4f63d`; any republication (including the pending F0 mirror
  sync) retires it.
- Worker review only: no node completion, no `validation_status=passed`, no gate verdict, and no
  global state was mutated. The checkpoint is worker-level.
- Independence: checker authored for this task, reads only the pinned snapshot, imports no
  canonical gate/tool module. Canonical tools were replayed as *supporting* evidence only.
