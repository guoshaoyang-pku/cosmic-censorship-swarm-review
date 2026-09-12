# W041-F0-MIRROR-INDEP-01 — independent test of the F0 mirror conflict

Bounded worker-041 task (instance `worker-041-20260912T002444-968807`), class-bound to
`AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH`, node `F0`,
gate `G-F0`. **Worker measurement only: no node status, no `validation_status=passed`,
no gate verdict.**

## Question

Assignment `astra-life02-publish-f0` requires
`research_map/formulation_taxonomy.yaml` (A, declared F0) and
`artifacts/formulation/formulation_taxonomy.yaml` (B, class-contract supplement) to be
published **byte-identically**. The formulation lead stopped before writing and filed
`leadform-blocker-0007` / `artifacts/formulation/evidence/f0_mirror_conflict.json`
claiming A and B are two *different* artifacts, not two trees of one artifact, so
byte-identical publication would damage a frozen input.

This task independently tests that claim mechanically: is any byte-identical direction
of the two **frozen** revisions admissible against the frozen consumers?

## Pinned inputs (measured at run time, stable across the run — see `hash_stable_across_run`)

| artifact | sha256 |
|---|---|
| A `research_map/formulation_taxonomy.yaml` (rev5) | `0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3` |
| B `artifacts/formulation/formulation_taxonomy.yaml` | `d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1` |
| F1 `schemas/af_wcc_vacuum.yaml` | `cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3` |
| F2a `schemas/af_scc_c2_vacuum.yaml` | `5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce` |
| F2b `schemas/af_scc_c0_vacuum.yaml` | `55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6` |
| `FROZEN.json` rev26 | `2554e276a0db70579ce36f7e665c9af81a1707bdc99e33758e861bec1d2df2e3` |
| frozen checker `artifacts/formulation/tools/check_taxonomy_consistency.py` | see `pinned_inputs` in the report |

A first measurement at A=`276009f4f63d` / F1=`9a8bd4c9` was completed but invalidated before
event emission by the F0 rev5 republish; per this task's own falsifier the measurement was
re-run. This README and the report describe the live binding above.

## Method

Exhaustive case analysis over the only byte-identical candidates of two frozen files —
content(A):=content(B) or content(B):=content(A) — plus a merged-revision control and a
negative control. Each case is materialised in an isolated sandbox root under `sim/`
with the real schemas, `FROZEN.json` and aliases copied in, and evaluated against the
frozen consumers:

| id | consumer |
|---|---|
| E1 | canonical declared-F0 structure: `class_ids` = 4 frozen ids, `classes` = 4, `transfer_rules.allowed/forbidden` |
| E2 | authoring supplement structure: `class_contracts` = 4, `axis_registry.genericity_axis.frozen` = 4, `implication_ledger` |
| E3 | per-class identity-axis agreement A.`classes`[c] vs B.`class_contracts`[c] (family, conclusion_type under the frozen alias policy, exclusions, test cases) |
| E4 | each schema's `class_contract_pointer` `path#fragment` resolves in the case tree |
| E5 | each schema's `f0_binding.declared_f0_sha256` matches the measured A bytes |
| E6 | each schema's `class_contract_supplement` path exists |
| E7 | `FROZEN.json` `logical_artifacts` pins match measured bytes |

E1–E4 and E6 are structural consumers; E5/E7 are frozen-pin freshness. In addition the
real frozen checker runs byte-identically inside each sandbox (it writes its evidence
inside the sandbox only; canonical trees are never touched).

Controls: the merged control (one file carrying both key sets) must pass E1–E4/E6 and
exit 0 while breaking the old pins (it is a new revision); the negative control mutates
one class's censorship family and must be detected.

## Result

| case | structural E1–E4/E6 | frozen pins E5/E7 | checker |
|---|---|---|---|
| baseline (live pair, FROZEN rev27) | pass | pass | `CONSISTENT` exit 0 |
| A := B | **fail** (B loses `class_contracts`, `axis_registry`, `implication_ledger`; all 3 pointers unresolvable) | fail (B pin broken) | `KeyError: 'class_contracts'` |
| B := A | **fail** (A loses `class_ids`, `classes`, `transfer_rules`) | fail (declared-F0 hash no longer matches) | `KeyError: 'class_ids'` |
| merged new revision (control) | pass | fail as expected (new sha256, pins must be re-issued) | `CONSISTENT` exit 0 |
| semantic mutation (negative control) | — | — | `INCONSISTENT` — `AF-WCC-VAC-GEN: family WCC vs SCC` |

**Verdict `CONFIRMED_UNSATISFIABLE_AT_FROZEN_REVISIONS`.** Neither byte-identical
direction preserves the frozen consumers; the freeze-consistency checker requires both
key sets and cannot pass under either direction. The lead's blocker is independently
confirmed. A single merged file carrying both key sets satisfies every consumer and the
checker, but it is a **new revision** (new sha256), so it cannot be produced by
"publish the frozen revision byte-identically".

**Pin discipline (observed).** During the measurement chain `FROZEN.json` moved
`2554e276` → `5fa3b3bf` (rev27) and re-issued both logical-artifact pins to the live
bytes `0abb9ed8`/`d7419b4e`; the baseline is pin-fresh at this measurement (E5 and E7
pass). The earlier mid-chain lag is recorded here as a transient, already repaired.

Constructive reading: the pair is adjudicated as **two logical artifacts** — on record in
`FROZEN.json` rev27 `logical_artifacts` (`F0-declared-taxonomy`, `mirrors: NONE`;
`F0-class-contract-supplement`, `mirrors: NONE`) — or re-frozen as one merged revision
with re-issued pins and pointers. Forcing byte-identity on the frozen revisions is not an
admissible third option.

## Falsifier

Any byte-identical direction (A:=B or B:=A) under which E1–E7 all pass **and**
`check_taxonomy_consistency.py` exits 0; or a frozen consumer that resolves the
class-contract pointer / declared-F0 hash through a path other than the two measured
files; or the pinned hashes moving before adjudication, which voids this binding and
requires re-measurement.

## Reproduce

```bash
python3 artifacts/worker-041/f0_mirror_indep/run_f0_mirror_indep.py
```

Outputs: `f0_mirror_report.json` (+`.sha256`), `raw/<case>.checker.{stdout,stderr}.txt`,
`raw/<case>.structure.json`, and the sandbox trees under `sim/`.
