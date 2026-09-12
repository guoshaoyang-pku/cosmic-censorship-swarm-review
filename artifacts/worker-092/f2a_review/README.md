# W092-F2A-CLASSBIND-REVIEW-01 — independent F2a class-binding review

**Reviewer:** worker-092 (bounded execution worker; not an author of the target or of any
`artifacts/formulation/**` input).
**Target:** `schemas/af_scc_c2_vacuum.yaml` = class `AF-SCC-C2-VAC-GEN` (node F2a, gate G-FORM)
at the FROZEN rev28 pin
`5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce`.
**Verdict:** `revise`, score **3.5** — verdict file `reviews/F2a-review-rev27-c.json`.
**Why revise:** one hard provenance defect (`HF-W092-F2A-01`); the class contract itself passes all
16 structural rules and the C2/C0 separation is content-carried.

## Method

`verify_f2a.py` is an **independent re-implementation** of the structural acceptance rules in
`artifacts/formulation/rule_spec.json` (R01–R16). It does not import the author's checker
(`artifacts/formulation/tools/check_class_schema.py`); that checker is invoked separately and only
its verdict is recorded as triangulation. The instrument is **read-only on every canonical path**:
entry and exit sha256 are recorded for all 9 pinned inputs and any drift invalidates the run.
Negative controls are text mutations written to a temporary directory, never to the repository.

Checks: pin discipline (P01–P03), the 16 rule_spec rules (R01–R16), C2/C0 separation (S01–S01b),
contract-pointer resolution (S02–S02b), binding chain (S03a–S03c), cross-artifact shared fields
(S04), three negative controls (C00), hash drift (D00), author-checker triangulation (T00).

## Result: 29 PASS / 3 DEFECT / 0 FAIL (3/3 controls detected, 0 drift)

**C2/C0 separation is carried by content, not naming** (S01 PASS):

| field | AF-SCC-C2-VAC-GEN (F2a) | AF-SCC-C0-VAC-GEN (F2b) |
|---|---|---|
| `conclusion.conclusion_type` | `scc_c2_future_inextendibility` | `scc_c0_future_inextendibility` |
| `regularity.extension_regularity` | `C2` | `C0` |
| `extension_solution_concept` | `classical_ricci` | `none` |
| `extension_predicate.frozen_*` | `C2` / `classical_ricci` | `C0` / `none` |
| implication ledger | C0-inext **entails** C2-inext; converse forbidden | C2-inext does **not** entail C0-inext |

**D0 is instantiable on both disjuncts** (R03 PASS): `r = smooth` or `r = (sobolev,s,delta)` with
`s > 5/2`, `delta in (1/2,1)`; every `definition_ref` resolves. This is the rev12 well-typedness
repair the audit-r2-F2a card asked to verify.

**No conclusion inflation** (R11/R14/R15 PASS): `epistemic_status=open_problem`, promotion requires
a checked proof artifact, the vacuity argument is marked `unverified_proof_obligation`, the tier-1
falsifier is an extension witness with a genericity requirement, and tier-2 is labelled
`refutes_strengthening_only`.

## Hard failure HF-W092-F2A-01 (blocks a clean accept)

`f0_binding.consistency_evidence_sha256` = `675a99d0d25b…`, but the canonical path it names
(`artifacts/formulation/evidence/taxonomy_consistency.json`) measures `9e335e9b…`, which is **also
the FROZEN rev28 pin**. The declared evidence hash does not resolve at the frozen revision. The
live/frozen document is a strict superset of the declared one (it adds `map_taxonomy_sha256`,
`lead_contract_sha256`, `measured_at`), so **class semantics are unaffected**; what fails is the
schema's own binding rule and frozen-revision provenance.

Repair options (owner decision; see verdict file):
1. **Preserving the rev12 pins** — restore the `675a99d0` bytes at the canonical path (hash-verified
   copy: `artifacts/worker-086/gform_rev12/pinned/taxonomy_consistency.675a99d0d25b.json`) and
   re-freeze the evidence pin. The three rev12 schema bytes and their bound reviews stay valid.
2. **Retiring the pins** — re-stamp the declared hash in all three schemas to `9e335e9b` and
   re-freeze; every verdict bound to the rev12 pins is void and must be re-run.

## Soft defects (reported, not blocking)

- `S02b` — the canonical F0 contract uses the alias token `strong_cosmic_censorship_C2` where
  `VOCAB_ALIASES.json` names `scc_c2_future_inextendibility` canonical and states aliases "must
  never appear in a new canonical artifact" (F0-owned).
- `R07b` — `genericity.ambient_space` justifies Baire-ness via "closed subset of a Banach space"
  while the smooth branch is Fréchet; Fréchet spaces are Baire, so the conclusion holds but the
  stated reason is incomplete for that disjunct.

## Reproduction

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-092/f2a_review/verify_f2a.py    # writes report.json, controls.json, acceptance_run.log
python3 artifacts/worker-092/f2a_review/make_verdict.py  # rewrites reviews/F2a-review-rev27-c.json
```

The report is deterministic modulo its two timestamps (verified by two consecutive runs, digest
`0afb9ccd6ee4aee7`).

## Scope limits

Structural acceptance only; no judgement of physical truth, no theorem promotion. Machine-checkable
rules do not certify the mathematical content of the genericity or vacuity arguments. The hash
defect is a provenance finding, not a class-semantics finding.
