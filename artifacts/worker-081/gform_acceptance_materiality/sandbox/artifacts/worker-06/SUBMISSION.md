# Worker-06 submission summary

Worker: `deepseek-flash-06` (execution worker 06, DeepSeek Flash breadth)
Session: `run-2026-09-11T23:15+08:00`
Checkpoints: `runtime/state/w06_checkpoint_{1,2,3}.json`, `runtime/state/w06_checkpoints.jsonl`

| assignment | gate | status | primary artifact | sha256 (prefix) |
|---|---|---|---|---|
| `asg-2026-09-11-F2-deepseek-flash-06-15` (Astra) | G-FORM | submitted, re-review requested | `schemas/af_scc_c0_vacuum.yaml` rev6 | `e6b1af2bd6925f27` |
| `assign-FORM-LEAK-03-20260911T2331` (lead-formulation) | G-CLASSBIND | delivered, independently replicated | `artifacts/worker-06/blindspot_report.json` | see report |

## F2b — AF-SCC-C0-VAC-GEN (C0 only)

Revision history (all in the event stream and `reviews/`):

| rev | sha256 (prefix) | change | verdict |
|---|---|---|---|
| 2 | `0150bfdf671b` | first canonical-format submission | revise (flash-16 3.0; lead-audit 4.0, HF-06/HF-03) |
| 3 | `0a4ceac588b2` | all six flash-16 findings + both hard failures fixed | accept (lead-audit 4.0) |
| 4 | `6f121a82af60` | + `regularity_class.default` for gate R05 | accept (flash-16 4.5) |
| 5 | `cb897b29db12` | frozen-gate R05 named Sobolev index; R16 backwards converse prose corrected | gate pass |
| 6 | `e6b1af2bd692` | metadata-only: non-manifest keys under `extensions` for R22 | **frozen gate pass** |

Checks on rev6:
- binding frozen gate `artifacts/formulation/tools/check_class_schema.py` sha `ea3deb8c42b5` → pass
- independent flash-13 gate sha `8130652042b4` → exit 0
- worker auditor `spec_conformance_audit.py` baseline and hardened → accept

Key content: single frozen smooth-with-decay data class (disjunctive domain removed per HF-06);
bare-metric extension convention (`frozen_equation_concept: none`); `conclusion_type:
scc_c0_future_inextendibility`; corrected genericity transfer table (open dense ⇒ comeager;
converse fails, witness R minus Q); H2_loc stated as not contained in C0 at the borderline
Sobolev exponent; visibility explicitly not in the conclusion; citations are candidate anchors
pending L1 with a no-decisive-use rule.

## FORM-LEAK-03 — semantic leakage corpus + blind-spot report

Artifacts: `artifacts/worker-06/semantic_fixtures/` (32 mutants, 20 rephrased, 25 S1 class
labels, 3 controls), `blindspot_report.json`, `HARDENED_RULES.md` (H01–H17),
`run_canonical_gate_on_corpus.py`, both gate-run records.

Measured on the frozen-base corpus (base `artifacts/formulation/schemas/af_scc_c0_vacuum.yaml`
sha `92406957234f`, manifest pinned in the report):

| implementation | caught / 32 | escape |
|---|---:|---:|
| W06 baseline auditor (pre-repair) | 11 | 0.6563 |
| binding frozen gate `ea3deb8c42b5` | 31 | 0.0312 |
| independent flash-13 gate `8130652042b4` | 13 | 0.5938 |
| **union of the three** | **32** | **0.0000** |
| **W06 hardened H01–H17** | **32** | **0.0000** |

- Delta vs the earlier binding gate `eef3f43f`: 13/32 (escape 0.5938) → 31/32 (escape 0.0312),
  zero both-implementation misses, after the formulation group revised the gate.
- Single remaining escape: `struct12_i_plus_completeness_lexical` (caught by the W06 baseline).
- False-positive control: H01–H17 reject 0 of 5 conforming schemas; both gates accept all 3
  positive controls (including the tagged-quotation and comment-only-composite controls).
- Independent replication: `artifacts/formulation/evidence/semantic_escape_rebased.json`
  reproduces the result (30/31 rebased mutants caught, same single escape, 0 control false
  positives); the 1-fixture difference is the list-index mutation path in
  `sem18_provenance_overclaim`, which their rebasing tool records as unparsed.

## Honest limits

- Structural conformance is not mathematical correctness, non-vacuity, or truth; no gate here
  decides those (SEM-3).
- Non-meagerness of the extendible set is explicitly non-machine-checkable (SEM-1).
- A composite regularity phrase in a YAML comment is invisible to any YAML parser (documented,
  not fixed, per lead instruction).
- The corpus is worker-authored and synthetic; per the assignment falsifier, honest blind-spot
  reporting is the control against a fake pass.
- H01–H17 are heuristics validated on five conforming schemas; a legitimate formulation outside
  that control set could in principle trip one.

## Next falsifiers

- F2b: a reviewer re-checks the rev5/rev6 delta (R05/R16/R22) at `e6b1af2bd692`; or the binding
  gate changes such that rev6 no longer passes.
- Corpus: a rephrased leak that both the binding gate and the W06 baseline accept while a domain
  reviewer identifies it as real; or a hardened rule rejecting a legitimate formulation.
