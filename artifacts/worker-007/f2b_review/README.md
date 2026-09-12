# Worker-007 review bundle — F2b (AF-SCC-C0-VAC-GEN), rev11

Bounded task: independent full-schema review of `schemas/af_scc_c0_vacuum.yaml` at
sha256 `1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508` (revision 11).

**Corrected verdict (revision 2): `revise`, score 3, two hard failures.**
Revision 1 reported `accept`; it was superseded after two additional hard checks failed on the
artifact bytes. The correction is recorded in `reviews/F2b-review-07.json` (`supersedes`) and in
events `w07-review-F2b-rev11-corrected-20260912T0032` / `w07-status-F2b-correction-20260912T0033`.
The canonical schema was never modified.

## Hard failures (revision 2)

- **F2B-07-H1** — `class_contract_pointer` (line 35) points at
  `artifacts/formulation/formulation_taxonomy.yaml#class_contracts.AF-SCC-C0-VAC-GEN`, while
  `f0_binding` declares the canonical `research_map/formulation_taxonomy.yaml` at
  `276009f4f63d`. The declared artifact has no `class_contracts` key (the contract sits under
  `classes.*` and has no `data_class_freeze`); the pointer resolves only against the divergent,
  unpinned authoring tree `c8e979a1eb48`. Class binding to F0 is therefore unverifiable under
  the canonical-path policy.
- **F2B-07-H2** — `D0` is a two-branch regularity disjunction (weighted Sobolev vs
  smooth-with-decay) with two ambient topologies; the Sobolev branch is *claimed* registered but
  `VARIANT_REGISTRY.json` has no Sobolev entry for this parent
  (`[CH, DISTRIBUTIONAL, H2LOC, L2CONN, LIP]`), and the schema registers only the CH reading.
  `tier_1` refutation semantics split across the branches.

Correlation: these are the same underlying observations as HF-034-2 / HF-034-1 in
`reviews/F2b-review-034.json`, verified independently here — count as correlated, not as
independent discoveries.

## Files

| file | role |
|---|---|
| `independent_checks.py` | reviewer-authored invariant checker (18 pass, 3 warn, 2 hard fail); does not import the lead's tools |
| `checks_output.json` | checker output: verdict FAIL, fails = `f0_contract_pointer_resolves`, `sobolev_variant_registered` |
| `project_structural_gate.json` | re-run of `artifacts/formulation/tools/check_class_schema.py` → pass, 0 failed rules |
| `project_classsep.json` | re-run of context-aware `research_map/class_separation.py` → 0 findings |
| `project_registry_taxonomy.txt` | variant registry VALID (4 classes, 7 variants), taxonomy CONSISTENT (0 divergences), variant deltas VALID (2) |
| `project_binding_gate_stale.json` | `artifacts/worker-06/check_class_binding.py` (rules w06-draft-3) → 3 fails, each a stale-rule false positive |
| `SHA256SUMS.txt` | hashes of this bundle |

## Controls that pass

Structural gate pass; context-aware class separation clean; variant registry / taxonomy / deltas
consistent; `f0_binding` hash itself matches measured F0 `276009f4f63d`; canonical schema ==
authoring schema at the pinned hash; no conclusion inflation; no class leakage.

## Falsifier

Repoint `class_contract_pointer` to a key that resolves in the declared canonical F0 (or publish
the authoring tree byte-identically and pin its hash), and register the Sobolev data-class
reading with a branchwise topology and a split tier-1 rule; then re-run `independent_checks.py`.
The review returns to accept only when both hard checks pass at the new hash.

## Evidence supersession

Revision-1 copies of `independent_checks.py` (`dded62d6dd0e`) and `checks_output.json`
(`9a6176394a68`) were replaced in place by revision 2 (`538c09a34644`, `d1b088d06cef`). Their
hashes remain pinned in the ingested revision-1 artifact event
`w07-artifact-F2b-checks-20260912T0024` and in checkpoint 1
(`runtime/state/w07_f2b_review_checkpoint_20260912T0026.json`), so those two pins no longer
resolve on disk; the revision-2 pins are the live ones.

## Non-claims

Not a node done; not a gate verdict; no canonical artifact edited; does not assert the D0
disjunction is mathematically illegitimate; physics and the truth of the class conclusion are not
certified.
