# W039-F1-REV12-REVIEW-01 — independent F1 review at `cce9c60146d6`

Worker `worker-039`, 2026-09-12. Class **AF-WCC-VAC-GEN**, node **F1**, gate **G-FORM**.

Artifact under review: `schemas/af_wcc_vacuum.yaml`, measured
`sha256:cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3`
(revision 12, republished 00:31:41, rewritten byte-differently at 00:32:02).
The hash was re-measured after all checks and is unchanged (`hash_stable: true`).

## Verdict

**`revise`, score 3.5** — one blocking finding, four minor wording/metadata findings.
No class-semantics defect was found, and the machine checks confirm the rev12
visibility repair is semantics-neutral.

### Blocking finding

**S8_EVIDENCE_BINDING — stale declared consistency-evidence hash.**
`f0_binding.declared_f0_sha256` matches the measured canonical taxonomy
(`0abb9ed8a961`), but `f0_binding.consistency_evidence_sha256` declares
`675a99d0d25b…` while the pointed-to file
`artifacts/formulation/evidence/taxonomy_consistency.json` measures
`9e335e9ba1bf…`. The file was regenerated twice during the review window
(00:33:16 and 00:34:55) and both regenerations measure `9e335e9b…`, so the
declaration is stale, not racing. No file in `artifacts/formulation/` carries the
declared hash.
**Remedy (one line, lead-formulation):** re-pin
`consistency_evidence_sha256` to `9e335e9ba1bf…` in the next revision, or freeze
the evidence file at the declared bytes. The gate cannot cite the binding as
auditable until the declaration matches the artifact.

### Minor findings (non-blocking)

| id | where | finding |
|---|---|---|
| W1 | `domains.D5` and `visibility.definition` | Both call whole-curve containment "strictly STRONGER" / a misclassification relative to the tail predicate. **False for causal curves** (check S10): the two are equivalent, because `J^-(q)` is past-closed and `gamma` is causal. The operative predicate is correct; the rationale sentence should state the equivalence (or be reworded). |
| W2 | `class_contract_pointer` | rev12 retypes `D0` to a tagged index `r`, while the canonical F0 contract text still says "for every admissible `(s,delta)`". Contract hypothesis H4 delegates the regularity axis to F1, so this is a refinement, not a class change; align the F0 wording at its next publication. |
| W3 | `revision_history` | Two `unused: true` residue entries; the index column ends at 10 while `revision: 12`; `supersedes: null`, so lineage is prose-only. |
| W4 | `revised_at` | 21 s behind the file mtime (00:31:41 vs 00:32:02 republication). Not future-dated; re-stamp or record the skew. |

### Transient (remediated, not an F1 defect)

At 00:33 the frozen binding gate `check_class_schema.py` (file sha `000e09e46b2f`,
unchanged) returned **fail R22** on these same schema bytes because
`KEY_MANIFEST.json` had not yet been updated for the new keys
(`revision_history`/`at`/`index`/`notes`, `predicate_abbreviation`,
`class_contract_supplement_pointer`, `consistency_evidence_sha256`). The manifest
was updated at 00:34:42 and the gate now returns **pass** on the same bytes. The
same R22 was measured on F2a/F2b at that time. Recorded for the controller's
ordering record only.

## What was machine-checked

`review_f1_rev12.py` (fail-closed, read-only) runs 12 checks; `checks.json` carries
the full evidence, `run.log` the stdout, `review.json` the review event body.

| check | result |
|---|---|
| S1 strict YAML (duplicate keys) | pass — rev12's duplicate `revised_at` keys are gone |
| S2 required slots | pass — 12/12 present |
| S3 binder order/domains | pass — 6 binders, `[forall, exists, forall, exists, forall, not_exists]`, all domains declared |
| S4 tail predicate | pass — `formal` and `D5` use `t0`/tail; `statement_formal` names `visible_singularity_from_I_plus` |
| S5 negation block | pass — tail-based, normal form present |
| S6 class binding | pass — id/conclusion type match the canonical contract; other three classes in anti-scope; `extension_regularity: null`; no asserted C0/C2 composite |
| S7 contract pointer | pass — resolves to `classes.AF-WCC-VAC-GEN`; supplement pointer is a separate field |
| S8 evidence binding | **fail** — see above |
| S9 timestamps | pass (hard); W4 skew noted |
| S10 tail/whole semantics | pass — 296 817 admissible finite models (all posets ≤ 5 elements + random 6), **0** models with tail containment but not whole-curve containment |
| S11 frozen binding gate | pass at exit (see transient note) |
| S12 openness declared | pass — vacuity falsifier, 4 unresolved items, 5 L1 ledger refs |

### S10 lemma (why W1 and the earlier F-1 are wrong)

For a future-directed causal curve `gamma` in a transitive causal order with
`J^-(q) = {x : x <= q}`:
`(A) gamma([0,T)) ⊆ J^-(q)` and `(B) ∃t0: gamma([t0,T)) ⊆ J^-(q)` are equivalent.
`A ⇒ B` is `t0 = 0`; `B ⇒ A` follows because `gamma(t0) <= q`, and for `t < t0`
causality gives `gamma(t) <= gamma(t0)`, so transitivity gives `gamma(t) <= q`.
Prior F-1 ("`formal` is strictly weaker") and rev12's "whole-curve is strictly
STRONGER" wording are both incorrect; neither changes F1's class extension.

## Falsifiers

- **Against the verdict:** a binding-gate `pass` together with a measured
  consistency-evidence hash equal to the declared `675a99d0…` at these exact
  bytes (S8), or `check_class_schema.py` returning `pass` while the declaration
  still mismatches (would make S8 advisory rather than blocking).
- **Against W1/S10:** one admissible finite model — transitive order, causal
  chain, past-closed `J^-(q)` — with tail containment but not whole-curve
  containment. S10 searched all posets up to 5 elements exhaustively and found
  none; a model must name which hypothesis (causality, transitivity,
  past-closure) it relaxes.
- **Against the whole review:** `schemas/af_wcc_vacuum.yaml` no longer hashing
  `cce9c60146d6…`; the verdict binds only to the measured entry hash.

## Authority and provenance

Worker evidence only. This review does not set a gate verdict, node status, or
`validation_status`, and no canonical artifact was edited. It was produced after
an earlier attempt (`W039-F1-QUANT-01`, a pre-repair quantifier adjudication
against `9a8bd4c9…`) was voided by the 00:31:41 republication through the same
fail-closed guard; that attempt is not cited here. The equivalence lemma was also
reached independently in the corpus (worker-026 `LEMMA-W026-1`, worker-037
`f1_visibility_equivalence_adjudication`, worker-040 HF-06 refuted); S10 is an
independent machine re-check, not a claim of priority.

## Reproduce

```bash
python3 artifacts/worker-039/f1_rev12_review/review_f1_rev12.py   # writes review.json/checks.json
python3 artifacts/formulation/tools/check_class_schema.py schemas/af_wcc_vacuum.yaml --json
sha256sum schemas/af_wcc_vacuum.yaml                              # expect cce9c60146d6…
```
