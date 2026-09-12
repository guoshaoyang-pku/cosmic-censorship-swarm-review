# W044-F2B-ACCEPTANCE-ORACLE-01

One bounded, class-bound task taken without an inbox card (the live instance prompt is
generic). Node **F2b**, class **AF-SCC-C0-VAC-GEN**, gate **G-FORM**.

## What it decides

A single executable acceptance oracle for F2b covering **both** live blocker families found by
other workers at frozen rev12, plus the interaction between them:

| family | owner | defect |
|---|---|---|
| P — pin binding | worker-041/045/065/086 | `f0_binding.consistency_evidence_sha256` = `675a99d0…` but the declared canonical path measures `9e335e9b…`, which FROZEN rev28 also pins |
| V — vocabulary binding | worker-005 | declared `conclusion_type` / `genericity.kind` are registry-canonical tokens outside the bound F0 rev5 allowed-lists, and F2b binds no reference to the alias registry that establishes equivalence |

The oracle also separates **semantics** from **binding**: F0's `field_vocabulary` allowed-lists
are unions over all classes, so literal membership alone is necessary-not-sufficient; the
discriminating check is canon()-equivalence with the **bound class axis** (controls M3/M4
demonstrate this).

## Result (pinned bytes, no drift during the run)

Current live F2b: **not acceptance-ready**, failing exactly `{A1, A2, A6}` — both blocker
families, all binding-level. `A4b/A5b` (class-axis equivalence), `A7` (canonical structural
gate exit 0) and `A8` (class-separation clean) pass: the mathematics/class identity surface is
not implicated by these two defects.

Candidate minimal repair **R\*** in a sandbox (three edits): restore the enriched, self-verifying
evidence document (`675a99d0`), bind the alias registry under the checker-sanctioned
`extensions.vocabulary_binding` slot, and refresh the two FROZEN pins → **ready: true, all
eight acceptance checks pass**.

**Durability probe:** running the canonical writer `check_taxonomy_consistency.py` once in the
sandbox overwrites the restored evidence with the pin-free lean document
(`675a99d0` → `9e335e9b`) and re-breaks `A1/A2/A3`. So an R2-style byte restore is **not
durable** unless the writer is made non-writing or is changed to emit the enriched schema; a
durable repair must also fix the writer (consistent with worker-086 R1/R3 and worker-041
HF-041-RCA-2).

## Controls (9/9 as designed)

`N1` live bytes reproduce `{A1,A2,A6}`; `N2` candidate repair reaches ready; `M1` wrong declared
hash flips A1; `M2` stripped input pins flip A2; `M3` out-of-class conclusion token flips A4b
while the literal check A4 stays green; `M4` same for genericity A5b; `M5` unbinding the
registry flips A6; `M6` class-separation detector fires on a planted merge assertion; `M7` the
structural gate rejects a schema with `class_id` removed.

## Falsifier

Any of: a current-state check marked fail measures pass (or vice versa) at the pinned hashes;
a control that fails to flip its target check (oracle vacuity); the candidate repair failing to
reach ready in the sandbox; the durability probe leaving the restored evidence byte-identical;
any pinned input moving before adjudication (voids the report).

## Authority and non-claims

Worker measurement only. **No canonical file is written** — every mutation is confined to
`sandbox/` (the writer is run only against the sandbox copy, never the live path). No gate
verdict, no node status, no `validation_status=passed`, no mathematics/physics/literature
claim. This oracle decides structure and binding, not truth, non-vacuity, or physical
correctness. The candidate repair is a demonstration, not the lead's chosen repair. Credit:
worker-005 owns the literal-membership/vocabulary finding; worker-086 owns the collision and
repair matrix; worker-041 owns the derived-output root cause. This artifact integrates them
into one executable acceptance test and adds the semantics-vs-binding separation and the
durability probe.

## Reproduce

```bash
python3 artifacts/worker-044/f2b_acceptance_oracle/f2b_acceptance_oracle.py   # writes report.json
```

Report: `artifacts/worker-044/f2b_acceptance_oracle/report.json`.
