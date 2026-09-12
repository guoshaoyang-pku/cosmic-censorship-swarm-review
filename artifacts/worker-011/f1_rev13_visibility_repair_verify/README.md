# W011-F1-REV13-REPAIR-VERIFY-01

Independent post-repair verification of F1 rev13 (`schemas/af_wcc_vacuum.yaml#d9cebb9404b2`,
class `AF-WCC-VAC-GEN`, node F1, gate G-FORM) by worker-011. Read-only on canonical
artifacts; nothing outside `artifacts/worker-011/f1_rev13_visibility_repair_verify/`
and `reviews/F1-review-011-rev13-visibility-repair.json` was written.

## Question

At rev12 (`cce9c60146d6`) this reviewer raised:

* **HF-011-01** (blocking): D5 asserted whole-curve single-q containment was "strictly
  STRONGER" than the class's tail predicate, and visibility.definition claimed the
  whole-curve reading "would misclassify" an exterior-to-black-hole geodesic. Both are
  false under the schema's declared past-closed `J^-(q)`.
* **F-011-02** (major): the claimed confirmation cited the withdrawn blocker
  `worker-037 W037V2-F1`.
* **F-011-03** (advisory): the variant SET strictness direction was unproven.

rev13 claims all three repaired. This instrument re-measures them at the frozen bytes.

## Method

* sha256 pin table + before/after drift guard; FROZEN declaration check.
* Clause-scoped text detectors on the pinned bytes, run on **assertive text** with
  bracketed revision notes and quoted prior wording stripped, so the rev13
  *mentions* of the old wording are not scored as assertions (CF-16 pattern).
* `LEMMA-W011-1` (tail <=> whole under past-closure) plus exhaustive preorder
  enumeration n <= 5 (positive control OEIS A000798: 1, 4, 29, 355, 6942) and
  fixed-seed samples n = 6,7,8.
* New direction checks for variant SET: tailSet => set; finite-I+ collapse (T3);
  explicit omega-chain witness with infinite I+ and no causal maximum (T4);
  B-containment-strictly-stronger clause of `negation_conclusion`.
* Six teeth controls on in-memory mutants, including a non-past-closed J^- reading
  that must produce divergences.

## Result

`report.json`: valid = `True`, 28/28 checks pass, verdict
**accept_targeted_repair** (targeted; `counts_as_full_schema_verdict = false`).

* HF-011-01: **discharged_at_this_pin**
* F-011-02: **discharged_at_this_pin**
* F-011-03: **discharged_at_order_model_level**

Residuals (advisory, not blocking): the omega-chain witness is an order model, not a
realized spacetime; the consistency-evidence file is regenerated on a loop and its
mtime is later than `FROZEN.json` although its bytes match the declared pin this run.

## Files

| file | role |
|---|---|
| `check_f1_rev13_repair.py` | deterministic checker (stdlib + PyYAML) |
| `report.json` | machine evidence, 28 checks, teeth controls, drift guard |
| `run.log` | checker stdout/stderr for the accepted run |
| `hashes.txt` | sha256 of every file in this directory + the canonical review |
| `checkpoint.json` | worker-local checkpoint |
| `../../reviews/F1-review-011-rev13-visibility-repair.json` | canonical review verdict |

## Falsifier

Re-measure schemas/af_wcc_vacuum.yaml: if it is no longer d9cebb9404b2 the verdict is void. At d9cebb9404b2 the repair findings are falsified (i.e., HF-011-01/F-011-02/F-011-03 would be reinstated) by any of: the condemned rev12 strictness or misclassification sentence reappearing in D5/visibility; a worker-037/W037V2 confirmation citation reappearing; a witness with the standard past-closed J^-(q) separating tail from whole; a finite-I+ model with set-containment but no single-q tail; or a failure of the audited text controls to detect their mutants.
