# Adjudication of flash-04 F1 ambiguity findings — lead-formulation

Date: 2026-09-11T23:32:53+08:00. Target: F1 class schema (canonical `artifacts/formulation/schemas/af_wcc_vacuum.yaml`;
flash-04 audited the worker draft `schemas/af_wcc_vacuum.yaml`, which is superseded as declared
artifact). Every finding is ruled; none is silently closed by re-wording.

| id | finding | ruling |
|---|---|---|
| AMB-01 | Minkowski data and non-vacuity | **Accepted as declared open.** Minkowski-type data lie in the ambient space and outside the generic set; non-vacuity is gated on a future-incomplete development, and the existence of such data inside G remains an explicit proof obligation. |
| AMB-02 | fine-tuned critical-collapse families | **Accepted as declared open.** Whether residual sets exclude critical families is a theorem obligation, not a schema field. Recorded, not assumed. |
| AMB-03 | finite-dimensional Kerr outside the generic set | **Accepted as an obligation.** The closed-proper-subspace argument is not stated by the schema and must not be assumed; `genericity.excluded_set_status` stays `unresolved`. |
| AMB-07 | a symmetric (e.g. exactly stationary) single datum: in or out? | **Ruled: membership is set-level only.** The class quantifies over a comeager set G; the schema does not decide membership of an individual datum. Symmetric data are *expected* to lie outside G in the vacuum class, but that expectation is a proof obligation. New field `genericity.membership_ruling` records this; `symmetry` is added to the excluded-set candidate list. |
| AMB-09 | data space vs development space in the ambient topology | **Ruled: the ambient space is the data space.** `genericity.ambient_space_is_data_space: true` is now explicit; the development is not an element of the ambient space. |
| AMB-10 | token mismatch `residual_comeager` (rule spec) vs `baire_residual` (F0 draft) | **Ruled: one canonical token, `residual_comeager`**, with `baire_residual`/`provisional_baire_residual` accepted aliases in `VOCAB_ALIASES.json`. F0 and R07 now map to the same notion; see the consistency check. |
| AMB-15 | equivalence with future asymptotic predictability | **Accepted as declared unresolved.** The class is bound to `statement_formal`; the equivalent phrasing may not be cited until L1 verifies it. |
| hash drift | same revision label at four contents | **Resolved.** Canonical artifacts are pinned in `FROZEN.json`; any change bumps `revision`, updates `revised_at`, re-emits an artifact event and re-runs the gate harness. A G-FORM verdict must cite the sha256, never the revision label. |

Residual scope limits that remain **open by design** (not defects): genericity meagerness
obligations, non-vacuity witness membership, and the diffeomorphism-quotient construction. They are
listed in the schema's `unresolved_items` and may not be cited as established.
