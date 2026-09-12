# W090-F2A-REV12-VERDICT-02 — independent F2a verification at the frozen rev12 bytes

Bounded class-bound task taken by **worker-090** (slot 090). No inbox assignment card existed for
this slot (fleet instance `2026-09-12T00:36:53`); the task was self-selected from the open G-FORM
coverage gap: F2a (`AF-SCC-C2-VAC-GEN`) had no full-schema verdict at its frozen rev12 hash, and
its recorded reviews (`F2a-review-034-repin`, `F2a-rev12-069`, `review_F2a_5476a3f2` by worker-059)
were all `revise` on a recurring set of findings.

**Target** — `node F2a`, `class AF-SCC-C2-VAC-GEN`, `gate G-FORM`.
**Frozen pin** — `schemas/af_scc_c2_vacuum.yaml` @
`5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce` (FROZEN rev28, `2f358f6722d9`).
**Verdict — `revise` (4.0)**: zero class-semantics failures; three blocking
provenance/vocabulary/bookkeeping items survive at the pin.

## What was measured (33 checks; 30 pass / 3 blocking fail)

Independently re-implemented, read-only wrt every canonical path:

| Group | Result |
|---|---|
| Pins: F2a / declared F0 / F0 supplement / FROZEN rev28 all measure their frozen hashes; FROZEN declares all three | PASS |
| Strict YAML: 0 duplicate mapping keys; all 12 required sections present | PASS |
| Clock: exactly one top-level `revised_at` = `2026-09-12T00:31:41+08:00`, not future | PASS |
| Class identity: `AF-SCC-C2-VAC-GEN` = AF/SCC/VAC/GEN/C2 | PASS |
| Quantifiers: first binder `forall r in D0`; `forall r in D0` in formal + statement; no pair-typed binder | PASS |
| D0: tagged disjoint union `r=smooth \| r=(sobolev,s,delta)`; every ordered domain resolves | PASS |
| Visibility: `role=not_in_conclusion`, I+ absent from the conclusion, WCC predicate not imported | PASS |
| No C0/C2 merge: alias-aware canonicalisation keeps C2 and C0 distinct | PASS |
| Pointers: canonical `#classes` and supplement `#class_contracts` anchors both resolve | PASS |
| `f0_binding.declared_f0_sha256` == measured F0 `0abb9ed8a961` | PASS |
| **W090-F2A-01** `f0_binding.consistency_evidence_sha256` declares `675a99d0…`, measured file `9e335e9b…` | **FAIL** |
| **W090-F2A-02** F2a's conclusion token is absent from canonical F0 `field_vocabulary.conclusion_type.allowed` (equivalence lives only in the authoring `VOCAB_ALIASES.json`) | **FAIL** |
| **W090-F2A-03** recorded acceptance corpus is stale (`1bb78ce9…` vs current base `55d0a1ea…`); `run_acceptance.py` fails closed at exit 3 | **FAIL** |

### New evidence that changes how the recurring findings should be read

1. **The consistency evidence is substantive, only its pin is stale.** Running the canonical
   `check_taxonomy_consistency.py` on isolated copies of the frozen F0 pair reproduces the live
   evidence file **byte-for-byte** (`9e335e9b…`, stdout `CONSISTENT (4 classes, 0 contract-text
   divergences)`), and deleting a supplement contract's `exclusions` flips the checker to
   `INCONSISTENT` (exit 1, `exclusions empty on one side`). So `consistent: true` is reproducible
   and falsifiable from the frozen bytes; W090-F2A-01 is a stale declaration + missing embedded
   tree hashes, not a false claim. (The declared `675a99d0…` is not recoverable from any snapshot
   on disk or from git — the evidence tree is untracked — so it cannot be re-verified directly.)
2. **Coverage gap, measured.** The evidence tool never reads the three class schemas (0 references
   to `schemas/`; output unchanged when a garbage schema is dropped into its sandbox). It compares
   only the declared F0 taxonomy against the supplement, so it cannot itself certify the schemas'
   F0-consistency — that burden sits on reviewers (this one included).
3. **The family acceptance criterion is unmet for a rule-vs-text reason in F1, not F2a.** After
   rebasing the corpus in a sandbox, F2a passes both stages and the union catches 31/31 mutants
   with 0 control false positives, but the pipeline verdict is still **FAIL** because the worker-06
   semantic auditor rejects F1 with `R03: binder '(q,t0)' absent from formal sentence` — a literal
   expectation that the rev12 tail-predicate rewording no longer satisfies. Either the auditor rule
   or the F1 sentence must move; F2a is not implicated.

## Falsifiers

- W090-F2A-01 closes only when `consistency_evidence_sha256` equals the measured evidence file and
  that file embeds the sha256 of both compared trees (or a controller ruling binds reproducibility
  instead of the hash).
- W090-F2A-02 closes only on a single-sourced vocabulary: F2a's token listed in canonical F0's
  allowed set (or F0 rewritten to the canonical token it currently treats as an alias).
- W090-F2A-03 closes when `measure_semantic_escape.py` is re-run so the recorded base equals the
  current base; it does **not** close the separate F1 `R03` family-level failure.
- The verdict itself falsifies if any of the 30 passing checks fails on a re-run at the same pin,
  if any of the 4 self-mutants escapes, or if the pins drift.

## Reproduction

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-090/f2a_rev12_verdict/check_f2a_rev12.py   # exit 1 by design: blocking items survive
```

Writes only under `artifacts/worker-090/f2a_rev12_verdict/` plus a throwaway pipeline sandbox in
`tmp/w090_f2a_pipeline_sandbox/`; the five canonical paths are read-only throughout, and the run
re-measures every pin at exit (`pin_drift: []`). Authority: worker evidence only — no gate verdict,
no node status, no canonical-file edit.
