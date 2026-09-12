# W015 — AF-WCC-VAC-GEN (F1) visibility-quantifier adjudication

**Task ID:** `w015-f1-visibility-adjudication-20260912T0028+0800`
**Worker:** `deepseek-flash-15` (slot 015)
**Class:** `AF-WCC-VAC-GEN` (exactly one class; node `F1`, gate `G-FORM`)
**Pinned target:** `schemas/af_wcc_vacuum.yaml` sha256 `9a8bd4c9680042a40894f6085f183661500966f2d787a6bf28a7098a271ed503` (revision 11, the lead-declared FINAL rev11 hash)
**Pinned siblings (context only):** F2a `b6123750b37d8bee1e92eeb025979a6afdf3b29a33331a9d8499e21398d13fb2`, F2b `1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508`, canonical F0 `276009f4f63dbf838f32f368eed982f5e353d69970ca3227090aed14d26006dc`.

## Question adjudicated

`F1-review-19` (worker-19) records a critical HF: the operative `quantifiers.formal` clause

```
not exists q in I+ with gamma subset J^-(q) intersect M        # whole-curve containment
```

contradicts the class's own canonical `visibility.definition` (single-q **TAIL** predicate) and is therefore not the expansion of `conclusion.statement_formal`, which uses `visible_singularity_from_I_plus(M_D)`. Is that finding true at the frozen bytes, or is the two-reading equivalence real?

## Result — finding CONFIRMED (blocking, content-level)

`probe_report.json` (sha256 `e94e578d61ea`) records, on the pinned bytes:

| Check | Measured |
|---|---|
| `quantifiers.formal` uses whole curve | `true` |
| `quantifiers.domains.D5` uses whole curve | `true` |
| `visibility.definition` is the tail predicate | `true` |
| `visibility.negation_conclusion` is the tail negation | `true` |
| `conclusion.statement_formal` uses `visible_singularity_from_I_plus` | `true` |
| artifact internally incoherent | `true` |

**Machine proof of non-equivalence** (`finite_model_check`, 12 geodesics × 44 causal-past assignments = 528 finite models, exhaustive):

* `canonical_fail ⇒ formal_fail`: **true** (the class conclusion implies the formal clause);
* `formal_fail ⇒ canonical_fail`: **false**;
* minimal witness: `gamma = [0,1]`, `J⁻(q) = {1}`, `tail_t0 = 1`. Here the canonical predicate is **true** (the tail `gamma([1,T))` lies in `J⁻(q)`, so there *is* a visible singularity) while the formal clause is also **true** (no `q` contains the *whole* curve). The formal prefix therefore admits a countermodel that the class predicate rejects: it states a strictly weaker condition than the class.

## Gate blindness (G-AUDIT relevant)

`artifacts/formulation/tools/check_class_schema.py` (sha256 `000e09e46b2f`) returns `PASS ... failed_rules=[]` (rc=0) on the pinned bytes. Its R10 visibility rule checks field presence/role only, not coherence between `quantifiers.formal` and `visibility.definition`, so the defect escapes the canonical gate.

## Repair proposal (not applied — schemas/ is lead-owned)

`repaired_proposal.af_wcc_vacuum.yaml` (sha256 `303705c46834`) applies the three coordinated edits that make the quantifier expand the canonical predicate:

1. `quantifiers.formal`: `not exists q in I+ with gamma subset J^-(q) intersect M.` → `not exists q in I+ and t0 in [0,T) with gamma([t0,T)) subset J^-(q) intersect M.`
2. `quantifiers.domains.D5.definition`: `points q ... gamma([0,T)) is contained ...` → `pairs (q,t0) ... the tail gamma([t0,T)) is contained ...`
3. `quantifiers.ordered` not_exists binder `"q"` → `"(q,t0)"`.

The repaired copy still passes `check_class_schema.py` (`PASS`, rc=0, `failed_rules=[]`), i.e. the repair is gate-compatible. Applying it to the canonical path is a lead-formulation decision.

## Hygiene findings (recorded, lower severity)

* duplicate top-level YAML keys: `revised_at` ×7, `revised_at_unused` ×2; a strict duplicate-key loader **rejects** the file, while PyYAML last-wins yields `revised_at = 2026-09-12T00:30:00+08:00`, which is **future-dated** against the probe wall clock — two conforming readers disagree on the revision timestamp;
* `class_contract_pointer` = `artifacts/formulation/formulation_taxonomy.yaml#class_contracts.AF-WCC-VAC-GEN` does **not** resolve in the declared canonical F0 artifact (`research_map/formulation_taxonomy.yaml#276009f4`, top-level key is `classes`, not `class_contracts`); it resolves only in the authoring-tree mirror `artifacts/formulation/formulation_taxonomy.yaml` (sha `c8e979a1eb48`, unpinned). `f0_binding.declared_f0_sha256` itself **does** match the measured canonical F0 hash.

## Falsifiers

* **HF-15-1:** exhibit a reading of the pinned bytes under which the whole-curve clause and the tail predicate are equivalent, or show the witness model `gamma=[0,1], J⁻(q)={1}` is inadmissible for `AF-WCC-VAC-GEN`; or produce a revision with measured sha256 ≠ `9a8bd4c9` whose `quantifiers.formal` uses the tail form — any of these voids this finding at this hash.
* **HF-15-2:** resolve `#class_contracts.AF-WCC-VAC-GEN` inside `research_map/formulation_taxonomy.yaml#276009f4` (or show the pointer is not normative) — that would clear the dual-tree finding.
* **Hygiene:** produce a strict YAML parser that accepts the duplicate-key file *and* a reader that agrees with PyYAML's effective `revised_at` — that would clear the parser-disagreement finding.

## Authority boundary

This is a reviewer artifact and a repair proposal. No canonical schema byte was modified; no node status and no gate verdict is claimed (worker authority limit). Event: `comms/outbox/deepseek-flash-15.jsonl` (review `w015-f1-visibility-review-20260912T0028`).
