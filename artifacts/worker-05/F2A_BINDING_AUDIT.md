# F2a binding audit — AF-SCC-C2-VAC-GEN at `4f97273e` (worker-05, 2026-09-12T00:18+08:00)

**Bounded task.** Verify that the frozen `AF-SCC-C2-VAC-GEN` artifact's declared F0
class-contract binding actually resolves against the authoritative files, and that the
consistency evidence discharges the artifact's own refresh rule. Tool:
`artifacts/worker-05/verify/check_class_binding_drift.py` (new, selftest pass: null control
clean, 3/3 planted defects caught). Report: `artifacts/worker-05/verify/f0_binding_drift_report.json`.
Verdict artifact: `artifacts/worker-05/verify/f2a_binding_review_20260912T0018.json`.

## Pinned instant (all hashes measured at 2026-09-12T00:18:00+08:00)

| target | sha256 | note |
|---|---|---|
| `schemas/af_scc_c2_vacuum.yaml` | `4f97273ef440` | rev10, gate **PASS** R01–R16 |
| `schemas/af_scc_c0_vacuum.yaml` | `a2aef5ac7fe3` | sibling |
| `schemas/af_wcc_vacuum.yaml` | `68392dd82050` | sibling |
| `research_map/formulation_taxonomy.yaml` | `0fcc6a1928fd` | canonical F0 rev4 |
| `artifacts/formulation/formulation_taxonomy.yaml` | `01e7f841643c` | authoring F0 (divergent) |
| `artifacts/formulation/evidence/taxonomy_consistency.json` | `9e335e9ba1bf` | unbound evidence |

## Verdict: revise (3.5), binding/evidence dimension only

The earlier stale binding is fixed: all three schemas now declare the live canonical F0 hash
`0fcc6a19` (B1 pass; it was `66bf917b` at 00:15 and `565a6e50` at 00:11). Two defects remain.

1. **Hard — consistency evidence is revision-independent (B7 fail).**
   `taxonomy_consistency.json` (`9e335e9b`) records only paths and `consistent: true`; it contains
   no sha256 of either compared file. An output that is byte-identical no matter which revisions
   were compared cannot discharge the artifact's rule *"if the declared F0 artifact changes hash,
   refresh this binding and re-run the consistency check before any gate verdict"*.
   Fix: have the consistency tool write the measured `map_taxonomy` and `lead_contract` hashes
   into the evidence file and re-run it.
2. **Warn — contract pointer resolves only in the authoring tree (B4 warn, B2 fail).**
   `class_contract_pointer` = `artifacts/formulation/formulation_taxonomy.yaml#class_contracts.AF-SCC-C2-VAC-GEN`
   resolves in the authoring file but not in canonical F0 rev4, which stores the same class under
   `classes.AF-SCC-C2-VAC-GEN`; canonical (`0fcc6a19`) and authoring (`01e7f841`) are still
   divergent, and the canonical-path policy says the authoring tree must be published
   byte-identically before verdicts bind.

Minor, same pattern in all three schemas: the inline comment says the binding was refreshed to
`565a6e50` while the field declares `0fcc6a19`; and `f0_binding.checked_at` is
`2026-09-12T00:30:00+08:00`, 12 minutes ahead of the measurement clock.

Content adjudication unchanged at this hash: the gate passes; probe S6-C2 fires on
`forall (s,delta) in D0`, which canonical F0 rev4 itself sanctions (*"For every admissible
(s,delta) there is a comeager set G_{s,delta}"*); probe S5-C2 fires on the R13-exempt prohibition
phrase in `anti_scope.phrases_that_are_not_this_class`.

## Independence and limits

Not a blind review. The reviewer authored revisions 1–3 of this schema and wrote the checker, so
this **does not count as the second independent verdict** G-FORM requires. The checker encodes the
reviewer's reading of the binding rule (literal hash/anchor/substring checks); it audits binding
hygiene, not class semantics.

## Falsifiers

- Recompute `sha256(research_map/formulation_taxonomy.yaml)`: if it is not `0fcc6a1928fd…`, the
  B1 pass and this pin are void.
- Regenerate the evidence with measured input hashes; if B7 still fails, the hard finding is a
  checker defect.
- Add `class_contracts.<class_id>` to canonical F0 (or repoint the pointer); if B4 still warns,
  the warn is a checker defect.
- Any change to a pinned schema voids this review for that target (freeze-first enforcement).
