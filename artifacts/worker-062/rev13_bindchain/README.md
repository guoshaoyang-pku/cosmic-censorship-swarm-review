# W062-GFORM-REV13-BINDCHAIN-RETEST-01

Bounded, class-bound worker task by `worker-062` (relaunched slot; no inbox card existed, task
self-selected from the live G-FORM repair/r3 queue). Independent read-only re-test of the
evidence-binding chain of the three frozen formulation class schemas at the **rev13 / FROZEN
rev29** bytes, re-testing the defect *classes* that were blocking at rev12.

**Verdict: `revise` 3.0** — the C06-class consistency-evidence defect is cleared, but the
two-stage acceptance criterion is not reproducible at the frozen revision, and the failure is
not only the stale corpus: after a mechanical rebase the pipeline still fails on canonical F1.

## Pins measured at T0 (all re-measured at T1, drift = [])

| node | class | path | sha256 | rev |
|---|---|---|---|---|
| F1 | AF-WCC-VAC-GEN | `artifacts/formulation/schemas/af_wcc_vacuum.yaml` | `d9cebb9404b2e79e` | 13 |
| F2a | AF-SCC-C2-VAC-GEN | `artifacts/formulation/schemas/af_scc_c2_vacuum.yaml` | `e9a27996dfd308bd` | 13 |
| F2b | AF-SCC-C0-VAC-GEN | `artifacts/formulation/schemas/af_scc_c0_vacuum.yaml` | `b2ab6acb2bbe7f86` | 13 |
| manifest | — | `artifacts/formulation/FROZEN.json` | `815e08079aefbc16` | 29 (frozen_at 00:57:26) |

## Checks (22) and controls (8)

| id | result | what |
|---|---|---|
| B1.F1 / B1.F2a / B1.F2b | PASS | measured hash == FROZEN pin == repo-root mirror, bytes equal, in-file rev 13, one class id |
| B2.* | PASS | declared F0 hash == measured `0abb9ed8a961`; canonical class-contract pointer resolves in F0 `classes`; supplement pointer resolves in the authoring supplement; paths distinct |
| B3.* | PASS | **C06-class cleared**: declared `consistency_evidence_sha256` == measured `9e335e9ba1bf` == FROZEN pin, evidence `consistent=true` |
| B4.literal | **FAIL** | **C10-class persists**: corpus base `1bb78ce9b357` (rev11 C0) != measured C0 `b2ab6acb2bbe` |
| B4.reproduce | PASS | mirror-sandbox run of `run_acceptance.py` exits 3 with `PREFLIGHT FAIL: rebased fixtures are stale` (canonical paths untouched) |
| B4.declared | **FAIL** | FROZEN rev29-pinned `acceptance_pipeline_report.json` (PASS, produced 00:27) records no base hash and predates rev12/rev13 |
| B7.rebase | FAIL (advisory) | sandbox rebase to rev13 bytes: union still catches 31/31 mutants, but the pipeline still returns **FAIL** because the semantic stage rejects canonical F1 on **R03** |
| B7.f1-semantic | PASS (observation) | ran the canonical auditor on canonical F1: `reject`, `failed_rules=[R03]`, `binder '(q,t0)' absent from formal sentence` |
| B5.* | PASS | single class id, own-axis `conclusion_type` under `VOCAB_ALIASES`, single extension-regularity token, SCC siblings disjoint |
| B6.* | PASS | canonical structural gate `verdict=pass`, `failed_rules=[]` on 3/3 |
| T1.drift | PASS | no pinned input moved T0→T1 |
| M1–M8 | 8/8 PASS | flipped F0 hash, wrong consistency hash, missing evidence path, sibling class id, sibling conclusion token, composite regularity, rebased positive control, unmutated positive control |

## Findings

- **HF-W062-REV13-01** (blocking-for-clean-accept): the two-stage acceptance criterion is not
  reproducible at FROZEN rev29/rev13. (a) stale corpus base → preflight exits 3; (b) after a
  mechanical rebase the pipeline still FAILs on canonical F1 R03; (c) the pinned PASS report is
  from 00:27, before rev12 existed, and records no base hash. `astra-life05-evidence-binding-repair`
  fixed the C06-class item but not this one.
- **HF-W062-REV13-02** (evidence-binding): the pinned acceptance report does not record the base
  bytes it was produced from, so its PASS cannot be bound to any revision.
- **O-W062-01** (post-hoc observation, not pre-registered): F1 R03 is an ordered-binder/formal-string
  notation mismatch. `quantifiers.ordered` binders are `[r, G_r, (Sigma,h,K), (Mtilde,gtilde,Omega),
  gamma, (q,t0)]`; the literal `(q,t0)` does not occur in `quantifiers.formal`, which spells it
  `not exists q in I+ and t0 in [0,T)`. The rev11 snapshot `9a8bd4c96800` passed with binder `q`;
  the mismatch entered at rev12 `cce9c60146d6` and persists at rev13. This is a notation-agreement
  fix on one side (schema formal string or the auditor's binder parsing), not a mathematical change.
- **P-W062-01**: C06-class cleared at rev13.
- **P-W062-02**: pin identity, class separation and structural gate all clean; the rebased mutation
  corpus is still caught 31/31 by the union of the two stages, so the rebase itself is safe.

## Repair path (next falsifier)

1. Re-run `measure_semantic_escape.py` at rev13 and republish `semantic_escape_rebased.json` plus an
   acceptance report that records `base_sha256`.
2. Make F1's ordered binders agree literally with `quantifiers.formal` (or adjust the R03 binder
   parsing on the auditor side) so the semantic stage accepts canonical F1.
3. Publish FROZEN rev30 and re-run this harness; only then can the r3 reviewers accept all three
   classes at one hash.

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-062/rev13_bindchain/verify_rev13_bindchain.py
```

Writes only under `artifacts/worker-062/rev13_bindchain/` (including `sandbox/`, a byte copy of the
formulation tree used to reproduce the pipeline). Every canonical path is opened read-only; the
canonical `acceptance_pipeline_report.json` is never rewritten.

## Authority and non-claims

Worker evidence only. This is **not** a full-schema semantic verdict (`counts_as_full_schema_verdict
= false`) and does not consume a G-FORM full-schema verdict slot. It sets no node status, no
`validation_status=passed`, and no gate verdict. It does not edit or re-point any canonical
artifact, ledger, schema or manifest.
