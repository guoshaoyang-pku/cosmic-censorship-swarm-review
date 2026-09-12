# W090-C2C0-TRANSLICENSE-VERIFY-01 — independent verification of the C0→C2 predicate-containment justification gap

**Actor** `worker-090` · **Class** `AF-SCC-C2-VAC-GEN` (cross `AF-SCC-C0-VAC-GEN`) · **Node** F2a · **Gate** G-FORM
**Target** `W047-C2C0-PRED-CONTAINMENT-01` (worker-047), report sha256 `8323187988f1…`
**Pins** F2a `e9a27996dfd3` · F2b `b2ab6acb2bbe` · F1 `d9cebb9404b2` · F0 `0abb9ed8a961` · supplement `d7419b4e8963` · FROZEN rev29 `815e08079aef`
**Verdict** `accept` (4.0), blocker confirmed, **advisory**, no hard failures, `counts_as_full_schema_verdict = false`

## Question

At the FROZEN rev29 pins, is the declared containment **E_C2 ⊆ E_C0** entailed by the two
sibling `extension_predicate` definitions as literally declared, or is it conditional on an
undeclared cross-class convention?

## Answer

**Not entailed under the literal reading.** The declared clause pair differs on two
convention axes:

| axis | F2a `e9a27996` | F2b `b2ab6acb` |
|---|---|---|
| manifold category of `M'` in clause (c) | silent (no SMOOTH/C-infinity token) | `SMOOTH (C-infinity) connected 4-manifold` |
| future witness in clause (f) | `p ∈ M'∖iota(M)`, boundary admitted | `int(M'∖iota(M)) ≠ ∅` **and** `p ∈ int(M'∖iota(M))` |

Reading each predicate literally (an attribute is admitted iff the text does not exclude it),
three of the four `(smooth, interior)` quadrants satisfy F2a and fail F2b, so
`E_C2_literal ⊄ E_C0_literal`. Under the aligned convention (F2a read with F2b's two pins)
the containment holds. The premise is asserted or used at **4 operative loci** (F2a
`class_boundary.one_way_implication` :78, F2a `implication_ledger` :239, F0 supplement :191,
F0 canonical transfer rule T1 :499), and **T1's guard set covers only data_class, genericity
and artifact_refs** — no guard names the predicate-convention axis. No pinned artifact
declares the alignment.

F2b's own clause (f) annotation ("The interior requirement blocks an extension that only adds
boundary/dense-open points") is document-internal evidence that the missing F2a guard is
load-bearing; F2a has no equivalent guard.

## What this is and is not

- It is a **text-level licensing check**: the decision table models what the declared bytes
  license, with the interpretation rule stated above.
- It is **not** a mathematics claim and **not** a claim that a boundary-only extension exists.
- It is **not** a full-schema verdict for F2a or F2b and does not count toward G-FORM coverage.
- No canonical file was written or edited; only hashed. The class-separation probe uses the
  pinned `c266dbec` detector copy (live detector drifted, CF-29); probe findings: 0.

## Divergence from worker-047

Worker-047's `C06` (clause (d) well-posedness: a C2 metric presupposes a differentiable
structure that clause (c) does not name) is recorded here as **INFO V12**, not a hard defect;
the core gap needs only `C01`/`C02`/`C11`. All other failing checks (`C01`, `C02`, `C09`,
`C10`, `C11`) are independently reproduced.

## Checks / controls

16 checks (`V01`–`V16`), 8/8 sandbox controls (`K1`–`K8`; mutations applied only to copies),
pin-stable entry and exit, exit code 0. Full tables in `results.json` / `controls.json`.

## Reproduce

```bash
cd <repo root>
python3 artifacts/worker-090/c2c0_transfer_license/check_c2c0_transfer_license.py   # exit 0
```

## Falsifier

At the pins of this run: (a) F2a clause (c) is shown to entail a smooth manifold category from
the pinned bytes; (b) F2a clause (f) is shown to entail the interior-witness condition;
(c) T1's guard set is shown to include the extension-predicate convention axis; or (d) a pinned
artifact is shown to declare the F2a/F2b alignment. A later write at a new hash is not a
falsifier; the new bytes must be measured and this instrument re-run.

## Next falsifier

Re-run the checker after the owner publishes an F2a revision (R1) or a T1/alignment declaration
(R2); the gap closes only when `V02`/`V03` (or `V09`/`V10`) resolve while `V06` passes under
the literal reading at the new bytes.

## Authority

Advisory worker verification. Workers cannot set `status=done`, `validation_status=passed` or a
gate verdict. The blocker belongs to the formulation owner to repair or rule on; a fresh F2a
revision voids the r3 pins and needs fresh review.
