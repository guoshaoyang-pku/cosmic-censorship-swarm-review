# B/N triage — formulation group, revision 20 (astra-classscope-02)

Directive: `astra-conv-01` ("apply P1–P5, publish, then answer findings by triage table, not by
another rewrite loop") and `astra-classscope-02` (variant finding accepted; new class ids rejected
pending Human PI).

Frozen revision: the `revision` field of `artifacts/formulation/FROZEN.json` is authoritative, and
`FROZEN.json#files` carries the current sha256 of every canonical path
(`research_map/formulation_taxonomy.yaml`, `schemas/af_wcc_vacuum.yaml`,
`schemas/af_scc_c2_vacuum.yaml`, `schemas/af_scc_c0_vacuum.yaml`). Hash literals are deliberately
not repeated here: a hand-copied table in this file went stale twice during the classscope-02
cycle, which is precisely the drift `FROZEN.json` exists to prevent.

## Blocking findings (gate cannot be adjudicated until closed)

| ID | finding | blocking? | why / line reference |
|---|---|---|---|
| B1 | **No independent reviewer verdict at the current F1/F2a/F2b hashes.** Reviews 16/17/18 and the A1 re-run dispatched at 00:05:13 all bind earlier sha256 values; rev9/rev20 changed them. | **BLOCKING** | `G-FORM` criteria require "reviewers 17,18 accept with cited sha256". Current pins: `schemas/af_wcc_vacuum.yaml` rev9 (`…f962c117`→`b65fcc0f`), `af_scc_c2_vacuum.yaml` rev9, `af_scc_c0_vacuum.yaml` rev9. |
| B2 | **No independent verdict at the current declared-F0 hash** (`565a6e50`; reviews 17/19 bound `579608b1c6a4`/earlier). | **BLOCKING (G-F0)** | `G-F0` criteria require 2 independent reviewer verdicts; both predate the D1/D3 text amendment (`research_map/formulation_taxonomy.yaml:50-95`). |
| B3 | **FORM-HELDOUT-08 (worker-16) is pinned to FROZEN revision 13 hashes**, which revision 20 supersedes. The out-of-sample escape estimate for the *current* pipeline is therefore absent. | **BLOCKING for the pipeline-generalisation claim only**; not for class-boundary correctness | assignment `assign-FORM-HELDOUT-08-…` acceptance H1 names revision-13 hashes. The rebased corpus (`evidence/semantic_escape_rebased.json`) is *not* independent of rules R26–R31. |

## Non-blocking findings (recorded, with owner)

| ID | finding | blocking? | status / line reference |
|---|---|---|---|
| N1 | F2a/F2b `falsifier.tier_1.machine_checkable_steps` overstates machine-checkability (F-A7, F-B3). | non-blocking | Open documentation-precision item; it does not move a class boundary. Re-check when B1 closes. |
| N2 | F2a `citation_status` / unresolved locators (F-A6). | non-blocking | No blanket `citation_status: verified` remains in the current F2a (0 exact matches); residual locators are L1-owned (`ledger/theorems.jsonl`). |
| N3 | worker-06 held-out escape `h03` (WCC content rephrased inside `visibility.reason`). | non-blocking | Principled blind spot: the field is deliberately exempt so SCC schemas can name visibility. `artifacts/worker-06/heldout_corpus/report.json`. |
| N4 | Canonical escape `struct12_i_plus_completeness_lexical` (1/31; rebased 30/31 caught). | non-blocking | Known lexical blind spot, recorded in `FROZEN.json#independent_replication`; unchanged by rev20. |
| N5 | D1 (WCC visibility form) and D3 (comeager quantifier placement). | non-blocking | **RESOLVED** this pass: F0 amended to the single-q tail predicate + explicit comeager (`research_map/formulation_taxonomy.yaml:115-127`, `:203-215`, `:271-281`); consistency gate `CONSISTENT (4 classes, 0 contract-text divergences)`. |
| N6 | HF-A1 dangling `extension_predicate` reference (F2a). | non-blocking | **RESOLVED**: `extension_predicate` is defined with clauses (a)–(f) at `artifacts/formulation/schemas/af_scc_c2_vacuum.yaml:88-100`. |
| N7 | HF-B1 false self-description in C0 `composite_regularity_lint.exemption`. | non-blocking | **RESOLVED**: no `composite_regularity_lint`/`exemption` block exists in the current C0 (grep: 0 hits). |
| N8 | F1 `unresolved_items`: excluded-family meagerness, non-vacuity witness membership, diffeomorphism quotient. | non-blocking | Declared proof obligations; may not be cited as established. `artifacts/formulation/schemas/af_wcc_vacuum.yaml#unresolved_items`. |
| N9 | L1 residual gaps (weighted Sobolev thresholds s>5/2 and delta, positive mass theorem, predictability equivalence; Grant et al. arXiv:1901.07996 and Rendall gr-qc/0503112 absent). | non-blocking for G-FORM; **blocking for any theorem-level citation** | L1-owned; recorded by `leadform-review-0014`. |
| N10 | F0 coverage gap CG1: `AF-WCC-SCALAR-SPH` has no schema node and its genericity stays unresolved. | non-blocking for G-FORM (scope F1,F2a,F2b) | Recorded in the F0 taxonomy and in `VARIANT_REGISTRY.json` parent-class entry (`node: unmapped`). |

## Class-scope adjudication result (astra-classscope-02)

| requirement | result | evidence |
|---|---|---|
| variant registry uses `{parent_class, variant_id, definition, evidence, status}` | DONE — registry v2.0, 4 parent classes, 7 variants | `artifacts/formulation/VARIANT_REGISTRY.json`; `check_variant_registry.py` → VALID |
| `class_ids` everywhere remain the frozen four | DONE — validator scans every `class_ids` field and rejects non-frozen values | `evidence/variant_registry_check.json` (`class_ids_frozen_four_only: true`) |
| F1 carries ONE canonical visibility predicate, other form a variant pointer | DONE — single-q TAIL predicate is the only predicate; SET registered under `class_identity_variants` | `schemas/af_wcc_vacuum.yaml:214-218` (predicate), `:227-240` (variant pointer) |
| P1–P5 publication | DONE — aggregator re-pinned; P1–P5 pass | `evidence/aggregator_pin_check_rev3.json` |
| freeze after publication | DONE — FROZEN revision 20, 37 files, 0 drift | `FROZEN.json`; `verify_frozen.py` |

Falsifiers of this triage: a new class id appearing in a `class_ids` field; loss of the
`parent_class` link in the registry; or an independent reviewer showing that a variant reference
in the frozen schemas is read as a class.
