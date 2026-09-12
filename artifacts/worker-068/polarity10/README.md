# W068-FORM-POLARITY-10 — conclusion-polarity blind-spot probe

**Actor:** worker-068 (bounded execution worker, self-claimed task; no inbox card existed for
worker-068 in this fleet wave).
**Status:** measurement complete; `valid=true`; **no gate verdict, no node completion, no theorem.**
**Predecessor:** FORM-HELDOUT-09 / W068-FORM-HELDOUT-09-REPL (union escape 1/35 =
`c0_03_conclusion_negated`).

## Question

FORM-HELDOUT-09 found one union escape: the C0 conclusion statement is logically inverted
while `class_id` / `conclusion_type` stay valid, and neither stage catches it. Is that a
one-off fixture artifact or a general blind spot, and does it extend to C2 and WCC?

## Method

15 probe fixtures, each a plain class-schema YAML derived from a byte snapshot of the
canonical schemas at the revision measured at build time. Each probe inverts conclusion
**content** by exactly one deterministic operation while preserving the class-identifying
tokens and every required slot:

| op | operation | classes |
|---|---|---|
| p1 | inner negation flip in `conclusion.statement_formal` (`not exists` -> `exists`) | W, C2, C0 |
| p2 | outer negation of the whole formal conclusion (`not ( P )`) | W, C2, C0 |
| p3 | negation of `conclusion.statement_natural_language` only (fields now contradict) | W, C2, C0 |
| p4 | `conclusion_type` token polarity flip (`inextendibility` -> `extendibility`, WCC -> negated form) | W, C2, C0 |
| p5 | WCC `complete(I+_D)` conjunct negated in formal + NL | W |
| p6 | WCC visibility conjunct inverted (`no singularity visible` -> `a singularity visible`) | W |
| p7 | exact HELDOUT-09 `c0_03` C0 conclusion inversion, rebuilt on the rev12 base (no stale key) | C0 |

Controls: 3 identity (unmutated) controls, 3 known-rejected liveness controls from
FORM-HELDOUT-07, 1 byte-identical HELDOUT-09 escape reference.

Pipeline: stage A `check_class_schema.py` (`--json`) and stage B `spec_conformance_audit.py`
(`--json`); **escape = accepted by both stages**. A class arm is *informative* only if its
unmutated identity control is accepted by both stages.

## Binding (measured)

| item | sha256 (prefix) |
|---|---|
| `schemas/af_wcc_vacuum.yaml` (rev 12) | `cce9c60146d6` |
| `schemas/af_scc_c2_vacuum.yaml` (rev 12) | `5476a3f2c6bc` |
| `schemas/af_scc_c0_vacuum.yaml` (rev 12) | `55d0a1ea9bda` |
| stage A `artifacts/formulation/tools/check_class_schema.py` | `000e09e46b2f` |
| stage B `artifacts/worker-06/spec_conformance_audit.py` | `c79d8ab8440a` |
| rule spec `artifacts/formulation/rule_spec.json` | `40f9bb9e657b` |
| `artifacts/formulation/FROZEN.json` (rev 28) | `2f358f6722d9` |
| `artifacts/formulation/KEY_MANIFEST.json` (**not pinned by any stage hash**) | `014e2d301978` |
| this corpus `manifest.json` | see event `w068-pol10-02-manifest` |

All inputs were re-measured after the run and were unchanged. The three canonical schema
hashes matched their FROZEN rev-28 entries at build time; live canonical hashes are
recorded in `raw_verdicts.json` as context (no drift during the run).

## Results (valid = true)

- **Liveness:** 3/3 known-rejected controls rejected. **Identity controls:** 2/3 accepted.
- **Informative arms (C2, C0): 9 probes, 7 escapes = 0.778 union escape rate.**
  - p1 inner-negation flip: **escapes** for C2 and C0.
  - p2 outer negation: **escapes** for C2 and C0.
  - p3 natural-language negation: **escapes** for C2 and C0.
  - p4 `conclusion_type` token flip: caught by R11 for C2 and C0.
  - p7 rebuilt HELDOUT-09 C0 inversion: **escapes**.
- **WCC arm is non-informative:** stage B rejects the *unmutated* rev12 WCC base with
  `R03: binder '(q,t0)' absent from formal sentence` (the live canonical
  `schemas/af_wcc_vacuum.yaml` re-run in place returns the same verdict). All 6 WCC probes
  are therefore rejected regardless of the probe op; their catches are **not** evidence
  that polarity is detected.
- **HELDOUT-09 reference is masked, not fixed:** the byte-identical `c0_03` fixture is now
  rejected by stage A with `R22: unknown keys ['revised_at_unused']` — a key removed from
  canonical rev12 and from the current KEY_MANIFEST allowlist — while stage B still accepts
  it. The rebuilt probe p7 (same conclusion inversion, rev12 base) escapes.

## Findings for adjudication

1. **Class-general polarity/content blind spot (C2, C0).** Neither stage compares
   `conclusion.statement_formal` / `statement_natural_language` content against the frozen
   class conclusion; R11 checks the `conclusion_type` token, not the statement. A schema
   asserting the negation of the class conclusion is accepted as class-valid.
2. **Stage A has an unpinned data dependency.** `check_class_schema.py` reads
   `KEY_MANIFEST.json`, whose revision is not covered by the stage tool hash (and was not
   pinned by HELDOUT-09's binding). Verdicts on unchanged fixture bytes are therefore not
   stable across KEY_MANIFEST revisions — demonstrated by the c0_03 reference flipping from
   escape to R22-caught for key-hygiene reasons.
3. **WCC rev12 canonical fails stage B (R03).** The semantic auditor rejects the live
   canonical WCC schema over binder formatting (`(q,t0)` vs the formal sentence's
   `q in I+ and t0 in [0,T)`). Either the canonical has a formatting defect or the auditor
   is over-literal; either way the WCC arm of this measurement — and the pinned pipeline's
   calibration on WCC — is uninformative until resolved.

## Non-claims

- Not a gate verdict; worker events cannot set `validation_status=passed`, `status=done`,
  or any gate verdict.
- Probe labels ("should_be_caught") are the author's, derived from class-binding; an
  **independent** reviewer must adjudicate them before escape families are cited.
- Stage B is worker-06's semantic auditor, not the F2 gate; an escape from this pipeline is
  not proof that a class definition is wrong.
- No R11 extension, no schema edit, no node completion is claimed.

## Falsifier

An independent re-run at the same pinned stage hashes that classifies any probe
differently; an independent reviewer showing a probe is not a well-formed
conclusion-content inversion (or that it is not class-bound); or a gate revision at a new
stage/rule-spec hash that catches probes reported as escaping here.

## Reproduction

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-068/polarity10/build_corpus.py   # rebuilds the byte-frozen corpus
python3 artifacts/worker-068/polarity10/run_polarity10.py # writes raw_verdicts.json + report.json
```

Artifacts: `manifest.json`, `report.json`, `raw_verdicts.json`, `build_corpus.py`,
`run_polarity10.py`, `checkpoint.json`, `bases/`, `probes/`, `controls/`, `known_leaks/`, `diag/`.
