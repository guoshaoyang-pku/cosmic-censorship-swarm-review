# Worker-17 proposal — F1/F2 class-binding acceptance gate (form-only)

> **SUPERSEDED at 2026-09-11T23:19:12+08:00** by assignment
> `asg-2026-09-11-A1-deepseek-flash-17-26` (node A1, gate G-AUDIT: independent review of F0/F1,
> deliverable `reviews/F0-F1-review-17.json`). The gate is retained as auxiliary review tooling
> and its measured false positives are recorded in
> `class_binding_gate/README.md#measured-false-positives-on-the-real-f1-artifact`.
> No part of this proposal was accepted as a node artifact.

* **Worker:** execution worker 17 (`flash-17`), DeepSeek Flash breadth executor
* **Group:** unassigned at proposal time; requested binding: formulation (`lead-formulation`)
* **Node IDs:** `F1` (primary), `F2` (secondary); feeds the `A1` review gate
* **Class IDs:** `AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`, `AF-WCC-SCALAR-SPH`
* **Status:** `proposal_emitted_artifact_in_progress`; **no completion claimed**
* **Deliverable:** `artifacts/worker-17/class_binding_gate/` (`validation_status: unverified`)
* **Created:** 2026-09-11T23:2x+08:00

## 1. Why this task

`comms/inbox` contained no lead assignment at 23:18:40+08:00. The immediate queue
(`ASTRA_HANDOFF.md#Immediate queue`) lists F1, F2, L0/L1, A1, N0, A2. F1 and F2 are
class-bound, active/queued, and on the critical path (`F1 -> L1`, `F2 -> L1`,
`F1 -> N0`). Their two named failure modes are exactly the ones a cheap worker can
machine-check without authoring the physics: missing quantifier/regularity slots and
cross-class leakage. ASTRA_HANDOFF hard decisions 1, 3, and 4 make this a gate, not a
draft: keep classes separate, bind Flash workers to explicit acceptance tests, and
accept no node without artifact + validation evidence.

Evidence that the gate is not redundant: the same map currently reports `VALID` while
nodes **F0** and **A0** are marked `done/passed` with declared artifacts
`research_map/formulation_taxonomy.yaml` and `evaluation_rubric.yaml` that **do not
exist**. `validate_map.py` checks only that the artifact *field* is non-empty, not that
the file exists, parses, or hashes. Form checks need to be executable.

## 2. Deliverable and artifact schema

```
artifacts/worker-17/class_binding_gate/
  class_binding_gate.py        # check(doc) -> violations; CLI over YAML/JSON
  make_fixtures.py             # deterministic good+mutant fixture generator
  selftest_gate.py             # mutation self-test -> selftest_report.json
  adversarial_probe.py         # boundary probe -> adversarial_probe_report.json (3 declared limits)
  fixtures/                    # 4 good + 21 mutants + EXPECTED.json
  README.md                    # rules, usage, limits
  MANIFEST.json                # sha256 of every bundle file
```

Artifact schema (one JSON object per gate run):

```json
{"overall_ok": true,
 "reports": [{"source": "...", "class_id": "AF-WCC-VAC-GEN", "ok": false,
              "violations": [{"code": "R_NO_LEAK", "path": "conclusion.statement",
                              "message": "...", "source": "..."}]}]}
```

## 3. Acceptance tests (all runnable in this workspace)

| # | test | command | expected | observed |
|---|---|---|---|---|
| T1 | good fixtures pass | `python3 selftest_gate.py` | 4/4 with zero violations | **4/4 pass** |
| T2 | every mutant is caught with its declared code | `python3 selftest_gate.py` | 21/21, no silent mutant | **21/21 caught** |
| T3 | every implemented rule is exercised | `python3 selftest_gate.py` | 17/17 rule codes | **17/17 covered** |
| T4 | gate boundary is declared, not hidden | `python3 adversarial_probe.py` | 4/4 probes match declared outcomes | **4/4 match; 3 limits declared** |
| T5 | CLI exit codes usable in a check step | `python3 class_binding_gate.py <good> <mutant>` | 0 then 1 | **0 / 1 as expected** |
| T6 | applies unchanged to the lead's real schemas | `python3 class_binding_gate.py schemas/af_wcc_vacuum.yaml schemas/af_scc_regularities.yaml` | verdict per file, no schema edit | **pending: files do not exist yet** |

T6 is the acceptance test that actually binds to F1/F2 and is deliberately unresolved.

## 4. Scope boundaries (non-claims)

* Form and class separation only. No claim about physical correctness, theorem truth,
  or formulation sufficiency.
* Three declared limits remain (semantic vacuity, cross-slot incoherence, exempt
  `source_refs`), reproduced in `adversarial_probe_report.json`. They are inputs to the
  A1 human review, not defects to be papered over.
* This worker does not edit `research_map.json`, does not set any node to `done`, and
  does not author F1/F2 schema text.
* `validation_status: unverified` until the formulation lead (or A1) accepts it.

## 5. Evidence refs

* `research_map/ASTRA_HANDOFF.md#Hard decisions` 1, 3, 4 and `#Immediate queue`
* `research_map/ARCHITECTURE.md#Verification by task type`
* `research_map/research_map.json` sha256 `82b96a7d8085d82c95c93a7f82d9ffafa085e20287df536215cb7e0550139d71`
* `research_map/validate_map.py` lines 23–26 (artifact field only)
* `artifacts/worker-01/artifact_integrity_recon.json` sha256 `5ad9741c0d186e79a3edd2520b544f5a9d0a83f180c7f8ba26f7d818f1ae440d`
  (independently confirms F0/A0 declared artifacts missing)
* `artifacts/worker-17/class_binding_gate/selftest_report.json`,
  `adversarial_probe_report.json`, `MANIFEST.json`

## 6. Expected information gain and stop rule

* **EPIG:** converts two review opinions per schema ("are the quantifiers exact?",
  "is this class leaking into another?") into one deterministic verdict with a JSON
  path per violation, on the F1/F2 -> L1/N0 critical path. Cheap (no model calls),
  re-runnable on every schema revision.
* **Stop rule:** 2 agent-hours, or when the lead's F1/F2 artifacts land and one gate
  verdict is recorded — whichever is first.

## 7. Next falsifier

Run the gate on a schema that passes every structural rule but is still class-mixed in
substance — e.g. an `AF-WCC-VAC-GEN` schema whose falsifier secretly requires a
`C^2`-inextendible extension (already caught: `R_NO_LEAK`), or the harder case where the
mixing is expressible **only semantically** (vacuous `visible_predicate`, incoherent
genericity statement). The latter currently passes and is recorded as a declared limit;
if a reviewer can construct a *materially* misleading schema that passes all 17 rules
with no semantic incoherence, the gate is insufficient and the rule set must grow.

## 8. Requested action

`lead-formulation`: bind or reject this proposal, and if bound, run T6 against the real
`schemas/af_wcc_vacuum.yaml` / `schemas/af_scc_regularities.yaml` when they land. If
rejected, record the reason so worker 17 is redirected rather than idling.
