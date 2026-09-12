# W081-GFORM-ACC-MAT-01 — G-FORM acceptance-corpus materiality and the F1 stage-2 rejection

Worker: `worker-081` (instance `worker-081-20260912T004238-968807`)
Class binding: `AF-WCC-VAC-GEN` (F1), measured for scope on `AF-SCC-C2-VAC-GEN` (F2a) and
`AF-SCC-C0-VAC-GEN` (F2b) — node `F1,F2a,F2b`, gate `G-FORM`.
Authority: worker measurement only. No canonical path was written; no node status,
`validation_status`, or gate verdict is set here. The canonical path owner is
`astra-lead-formulation`; the verdict owner is `astra-lead-audit`.

## Question

`artifacts/formulation/evidence/semantic_escape_rebased.json` binds corpus base
`1bb78ce9b357` (rev11 C0) while the live authoring C0 measures `55d0a1ea9bda` (rev12 C0), so
`artifacts/formulation/tools/run_acceptance.py` exits 3 on PREFLIGHT. Reviewers filed this as
`HF-069R-2` / `HF-W063-02` ("blocking-for-clean-accept"). **Is the staleness material to the
acceptance outcome, or only a provenance/ordering defect?** The pipeline fail-closes before
its canonical stage, so the last filed PASS (`acceptance_pipeline_report.json`, 00:27)
predates rev12 and could be hiding a live regression.

## Method (`measure_materiality.py`, rerunnable, read-only on canonical paths)

1. Pin every input hash (three canonical schemas, authoring copies, both stage tools, the
   auditor, `rule_spec.json`, the fixture manifest, the live corpus evidence, the live report).
2. Mirror `artifacts/formulation/` and `artifacts/worker-06/` into `sandbox/` and reproduce the
   live PREFLIGHT FAIL there.
3. Regenerate the rebased corpus against the live rev12 base **inside the sandbox**
   (`measure_semantic_escape.py`), then run the two-stage pipeline on it.
4. Grade each as-frozen canonical schema through both stages.
5. Compare per-mutant verdict class (union-caught / structural / semantic) and fixture bytes,
   stale (rev11 base) vs fresh (rev12 base).
6. Apply the minimal R03 repair to a sandbox copy of F1 and re-run the whole pipeline.
7. Audit every distinct `af_wcc_vacuum*.y*ml` blob on disk with the adopted stage-2 tool to
   locate the revision where R03 started failing.
8. Report declared-vs-measured corpus size.

## Result (live pins at run time; `pins_moved_during_run: []`)

- **P1 — reproduced.** Sandbox `run_acceptance.py` exits 3: corpus base `1bb78ce9b357` vs
  current base `55d0a1ea9bda`.
- **P2/P3 — the stale corpus is material, not just stale.** After rebasing to rev12 the
  preflight clears, all **31/31 measured mutants are union-caught** and both controls pass —
  but the pipeline still exits 1 (`FAIL`): stage 2 (`artifacts/worker-06/spec_conformance_audit.py`)
  **rejects canonical F1** `schemas/af_wcc_vacuum.yaml#cce9c60146d6` with
  `R03: binder '(q,t0)' absent from formal sentence`. F2a and F2b pass both stages.
  The mismatch is visible at `schemas/af_wcc_vacuum.yaml:47` (formal writes
  `not exists q in I+ and t0 in [0,T) with ...`) vs `:54`
  (`{kind: not_exists, binder: "(q,t0)", domain_id: D5}`).
- **P4 — the corpus repair itself is verdict-invariant.** All 31 fixture files change bytes
  across the rev11→rev12 base move, yet **0 of 31 mutants change union-catch class**
  (stale union-caught 31, fresh union-caught 31; structural 30/31 and semantic 11/31 in both).
  So the required corpus repair is re-generation + re-pin, not a semantic revision.
- **P5 — minimal repair verified end-to-end.** Rephrasing the one formal clause to the
  declared tuple, `not exists (q,t0) with q in I+ and t0 in [0,T) such that ...` (same
  binders, same semantics, repaired sha256 `38bd15a68fed`), makes F1 pass both stages and the
  **full pipeline PASS (exit 0)** at the same rev12 mutant corpus.
- **P6 — the R03 rejection is specific to the rev12 cut.** Of 17 distinct F1 blobs on disk,
  14 accept, 2 reject for unrelated older rules, and exactly one rejects on R03: the live
  rev12 `cce9c60146d6`. The pre-rev12 revision `9a8bd4c96800` passes R03 with 6 ordered
  quantifiers. The rev12 delta (revision history index 10) rewrote the visibility clause and
  changed `ordered[5].binder` from `q` to `(q,t0)` without writing that literal in `formal`.
- **P7 — corpus size.** The manifest declares 32 fixtures; the tool measures 31. One fixture,
  `sem18_provenance_overclaim.yaml`, is unparsed (`provenance.sources[0].role = '...'`) and is
  excluded from the union-coverage count in both the stale and fresh corpora.

## What this adds over concurrent work (attribution)

- `worker-016` (`W16-R03-ADJ-01`, 00:46:41) independently found the frozen-F1 R03 literal-binder
  rejection and tested a literal rendering + a variable-wise R03 implementation. That is the
  same rule-level defect; this card is an **independent reproduction** of it plus the
  pipeline-level materiality chain the rule-level card does not measure.
- `worker-064` (`r03_cause`) analyses R03 against the semantic contract corpus/controls.
- `worker-069` measured the PREFLIGHT failure itself. Neither ties the staleness to the
  canonical stage-2 rejection, nor measures the mutant-level invariance.
- New measurement here: the stale corpus **masked** a live canonical FAIL because the
  fail-closed preflight never reaches the canonical stage.

## Consequence (for the owners, not a verdict)

The acceptance criterion ("exit 0 only if the three canonical schemas pass BOTH stages") is
**not met at the frozen rev12 bytes** for two independent reasons: (1) the family-wide
`f0_binding.consistency_evidence_sha256` collision (reported by worker-030/086/096 and others),
and (2) this F1 R03 notation mismatch. Repairing (2) is a one-field canonical edit plus
re-freeze; repairing (1) is a re-generation/re-pin. Neither is a class-semantics change, and
neither may be applied by a worker.

## Falsifier

Re-run `measure_materiality.py` after re-measuring the pins. The finding is falsified if
(a) any of F1 `cce9c60146d6` / F2a `5476a3f2c6bc` / F2b `55d0a1ea9bda` / manifest
`c102445df397` / `spec_conformance_audit.py` has moved and the moved revision passes both
stages; (b) at the pinned rev12 hashes `run_acceptance.py` exits 0; (c) the stage-2 auditor on
canonical F1 returns accept with R03 pass; or (d) a re-measured stale-vs-fresh comparison
shows a mutant whose union-catch class changes. The repair proposal is falsified if the
substituted sentence changes any other stage-1/stage-2 rule outcome or the mutant union count.

## Files

- `measure_materiality.py` — the instrument (sandbox-only writes; exit 2 on pin drift).
- `evidence.json` — machine-readable measurements, pins, per-mutant delta, history, repair.
- `sandbox/` — regenerated corpus + pipeline outputs (disposable mirror, not canonical).
- `stale_corpus/` — snapshot of the live stale corpus the delta is measured against.
- `checkpoint.json` — hashes, status, next falsifier.
