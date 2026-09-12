# W060-F2A-EXT-NESTING-MATERIALITY-01 — independent report

**Worker:** worker-060 (advisory evidence only; no gate verdict, no node status)
**Node / class / gate:** F2a / `AF-SCC-C2-VAC-GEN` (+ sibling `AF-SCC-C0-VAC-GEN`) / G-FORM
**Trigger:** worker-091 review `w091-f2a-review-rev29-b-20260912T0103`, hard failure HF-091-02
(extension predicate under-frozen relative to the C0 sibling).
**Measured pins** (T0 = T1, both mirrors byte-aligned):

| path | sha256 |
|---|---|
| `schemas/af_scc_c2_vacuum.yaml` (rev13) | `e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe` |
| `schemas/af_scc_c0_vacuum.yaml` (rev13) | `b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c` |
| `artifacts/formulation/formulation_taxonomy.yaml` (supplement) | `d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1` |
| `research_map/formulation_taxonomy.yaml` (declared F0) | `0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3` |
| `artifacts/formulation/FROZEN.json` (rev29) | `815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0` |
| `artifacts/formulation/VARIANT_REGISTRY.json` | `6bac9adea19e17efe625342ef4d2098e3775491aa3d0e06596cd5d75912348fb` |

## Object decided

With `P_X` = the X schema's extension predicate and `E_X` = the data admitting an
X-extension, the licensed transfer

> no proper future C0 extension ⇒ no proper future C2 extension

holds iff `P_C2 ⇒ P_C0`, i.e. every triple satisfying F2a's predicate also satisfies
F2b's. The question is whether that implication is **derivable from the frozen bytes**.

## Result

**H1 CONFIRMED — the asymmetry is present on all three reported axes.**
**H2 MATERIAL — the licensed transfer is not derivable at these bytes.**
**F2a review verdict: revise.**

| axis | F2a (C2) | F2b (C0) | status |
|---|---|---|---|
| A1 `M''` manifold category | clause (c) "`M''` is connected and time-orientable"; `topology.extension_topology` "a connected 4-manifold" | "`M''` is a SMOOTH (C-infinity) connected 4-manifold" with the accepted rationale that a merely topological `M''` cannot carry a tensor field | asymmetry present; **immaterial under standard typing** (a C2 metric tensor field presupposes a differentiable structure) but the rationale was not propagated |
| A2 `iota` regularity | clause (a) "isometric embedding" only; **no** `iota_regularity` field anywhere in F2a or its cross-references | `non_vacuity.iota_regularity` freezes a C-infinity isometric embedding to remove the R2-04 ambiguity | asymmetry present; **MATERIAL as a freeze gap**: the declared F0 taxonomy itself records the embedding-vs-metric regularity subtlety as unresolved and assigns the fix to F2/L1. Under the loose admissible reading a C2-metric extension with a non-smooth `iota` satisfies F2a but not F2b, so `P_C2 ⇒ P_C0` is not derivable |
| A3 clause (f) interior | "there exist q ∈ iota(M) and p ∈ M''∖iota(M) with p ∈ I⁺(q; g'')" | additionally `int(M''∖iota(M)) ≠ ∅` and `p ∈ int(M''∖iota(M))`, with the accepted R2-major note that the unqualified clause "was escapable" by extensions adding only boundary/dense-open points | asymmetry present; **MATERIAL**: F2b's own accepted repair establishes the escape schema, and F2a retains the escapable form, so a C2 extension can satisfy F2a's (f) and fail F2b's |

Two independent material axes (A3 dominant, A2 freeze gap). Consequently the F2a
ledger rows `implication_ledger.one_way_entailments[0]` and
`class_boundary.one_way_implication` ("every C2 extension is a C0 extension") are not
sound as written at these bytes, and the same dependency sits in F2b's transfer row
(`one_way_entailments[2]`, by transitivity).

**Minimal repair (formulation-owned, not performed here):** propagate F2b's clause-(f)
interior condition and an explicit `iota_regularity` convention into F2a (or freeze both
centrally in the class contract), then re-review F2a. A hash-only rebind does not close
either axis.

## Relation to the earlier worker-060 data_class verdict

The prior worker-060 adjudication measured F2a/F2b **strictly equal on all 15
data-space-core keys**, so the transfer was not disabled by a `data_class` divergence.
This task measures a different surface — `extension_predicate` clauses and the `iota`
convention. A MATERIAL verdict here does not reverse that verdict; the two are
independent and both are needed for the transfer.

## Controls (all pass; any failure would have made the run INVALID)

- **K3a/K3b** wrong pre-registered pin and byte-mutated sandbox each fail closed with
  exit 2 (VOID), writing no verdict.
- **K1** injecting F2b's interior phrase into an F2a sandbox copy flips check A3 from
  fail to pass (positive detector control) and drops H1 to NOT_CONFIRMED.
- **K2** A3 fires on content, not path: F2b has the interior phrase, F2a does not.
- **K4** clause slots align ((a)–(f), same "adds points to the future" intro) so the
  comparison is apples-to-apples.
- **K6** independence: F2a/F2b/supplement are authored/owned by
  `astra-lead-formulation`/`lead-formulation`; worker-060 authored none of them and
  imported no other worker's checker (stdlib + PyYAML only).

## Limitations

- Materiality is decided at the level of the frozen bytes (derivability of
  `P_C2 ⇒ P_C0`). No vacuum extension realising the A3 escape is constructed here;
  F2b's accepted R2-major note supplies the escape schema and is the primary evidence.
- A2 is reading-dependent: "isometric embedding" may be read as smooth by convention,
  in which case A2 is immaterial — the point is precisely that the bytes do not decide.
- Out of scope: the F2b line-246 inverted-containment hard failure (HF-060-CS-01),
  the F2a moving-target pins of assignments `audit-r2-F2a-a/-b`, mathematics,
  non-vacuity, and citation scope.

## Next falsifier

Re-run `verify_f2a_ext_nesting.py` at any new pin. H2 flips to IMMATERIAL iff F2a
supplies all three axes (an `iota_regularity` convention, the clause-(f) interior
requirement, and the `M''` smooth category) or the transfer row is withdrawn, so that
`P_C2 ⇒ P_C0` is derivable from the F2a bytes alone. Any drift of the six pins voids
the measurement (the script exits 2 without writing a verdict).
