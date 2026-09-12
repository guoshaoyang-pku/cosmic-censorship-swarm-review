# W096-F2B-REV12-GATE-REVIEW-01 — independent class review (F2b / AF-SCC-C0-VAC-GEN)

One bounded class-bound task: an independent, hash-bound structural review of exactly one
frozen class schema. Reviewer `worker-096`; not an author of the target, its mirror, or the
taxonomy. Harness is this worker's own (`run_review.py`); the project checkers are recorded
only as corroboration.

| field | value |
|---|---|
| class | `AF-SCC-C0-VAC-GEN` |
| node / gate | `F2b` / `G-FORM` |
| target | `schemas/af_scc_c0_vacuum.yaml` @ `55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6` |
| frozen pin | `artifacts/formulation/FROZEN.json#2f358f6722d9` revision 28 |
| stable during run | yes (re-measured after the run) |
| verdict | **revise**, score 3.5, `counts_as_full_schema_verdict: true` |
| checks | 13 pass / 2 fail / 1 process info, controls 4/4 pass |

## Findings (both reproduced independently, both owned by lead-formulation)

- **W096-F2B12-01 (hard, R08)** — `f0_binding.consistency_evidence_sha256` pins
  `675a99d0d25b…` while `artifacts/formulation/evidence/taxonomy_consistency.json` measures
  `9e335e9ba1bf…` on disk. The schema's own refresh rule ("if the declared F0 artifact changes
  hash, this binding must be refreshed and the consistency check re-run") is not satisfied by
  these bytes, or the evidence was regenerated after the pin was written.
  *Falsifier:* at schema hash `55d0a1ea…`, show the evidence file measuring `675a99d0…`.
  *Relation:* independently reproduces worker-060 `HF-060-F2B-2`, from a separate harness.

- **W096-F2B12-02 (hard, R09)** — `implication_ledger.forbidden_transfers[0].reason` (line 245)
  says "C2 is a strictly larger extension class". Line 238 defines
  `E_C0 ⊇ E_H2loc ⊇ E_{C^1,1} ⊇ E_C2` and line 231 states H2_loc-inextendibility "entails the C2
  sibling", so the premise is inverted: C2's extension class is the *smallest*, which is what
  makes C2-inextendibility *weaker*. The row's conclusion is right, its stated premise is false —
  a self-contradiction inside the transfer-hygiene surface.
  *Falsifier:* an extension-set reading in which `E_C2` strictly contains `E_C0` under this file's
  own definitions.
  *Relation:* independently reproduces worker-060 `HF-060-F2B-1`, from a separate harness.

## Objection adjudication (record, not a repair)

- **O-GFORM-1** (audit r2: F2a/F2b `data_class` blocks key-identical; C2/C0 separation rests on
  `regularity_token` + `extension_predicate`): **intended encoding, not a defect at these bytes.**
  R11 measures the actual class axis as field-level differentiated —
  `extension_regularity C0 vs C2`, `regularity_token C0 vs C2`,
  `extension_predicate.frozen_regularity C0 vs C2`,
  `frozen_equation_concept none vs classical_ricci`. The shared block is the *initial* data class
  (same AF vacuum data for both classes), which is the correct scope. The only `data_class` leaf
  differences are an L1 locator and a hypotheses note.
  *Falsifier:* a C0/C2 pair whose extension regularity, class token and extension-predicate
  regularity/equation concepts are all identical.

## Repairs confirmed closed at this hash (not re-opened)

Duplicate mapping keys (any scope) 0; `revised_at` ≤ mtime ≤ wall clock; canonical
`class_contract_pointer` and the split `class_contract_supplement_pointer` both resolve on their
declared trees; declared F0 hash equals the measured canonical taxonomy; entailment directions
consistent with the containment chain; own-class identity and falsifier binding; no `AF_{I+}` use
in the body; canonical and mirror bytes identical.

## Process note

`review_status` inside the schema is frozen `verdict: pending` / `independent_reviewers: []` while
verdicts exist at this hash. A hash-frozen artifact cannot list later reviews without changing its
hash, so the ledger — not this field — is authoritative. Recorded as process info (R16), not a
byte defect.

## Corroboration (not the method)

- `artifacts/formulation/tools/check_class_schema.py` `000e09e46b2f` → exit 0, `verdict: pass`,
  `failed_rules: []`.
- `artifacts/formulation/tools/check_taxonomy_consistency.py` `de356d999ea3` → exit 0,
  `CONSISTENT (4 classes, 0 contract-text divergences)`.

## Artifacts

| path | sha256 |
|---|---|
| `artifacts/worker-096/f2b_rev12_gate_review/report.json` | `f48102b3036abf91de313b3dcb35234d1e4862aca34348b16dee4596ddcec89c` |
| `artifacts/worker-096/f2b_rev12_gate_review/run_review.py` | `11b824aba1318175747a3f576c9b3afe0b0ddcbb55ff0fec1b8ed05b1b7ee21c` |
| `artifacts/worker-096/f2b_rev12_gate_review/snapshots/af_scc_c0_vacuum.55d0a1ea9bda.yaml` | `55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6` |

## Falsifier / next falsifier

Re-run `run_review.py --pin 55d0a1ea…`: falsified if any pass check fails on identical bytes, a
control stops firing (P1–P3) or fires on clean input (N1), or the hard findings flip to pass
without a revision. After any new revision this verdict is void (drift, not error) and must be
re-run against the new canonical hash. G-FORM still needs two independent non-author verdicts at
one frozen hash.

**Authority:** worker evidence only. No gate verdict, no node completion, no `validation_status`
promotion; workers cannot set done/passed.
