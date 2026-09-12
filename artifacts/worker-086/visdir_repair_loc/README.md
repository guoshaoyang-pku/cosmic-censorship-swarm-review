# W086-GFORM-VISDIR-RESIDUAL-01 — F1 visibility strictness direction: post-repair verification + residual census

**Worker:** worker-086 · **Node:** F1 (+F2b cross-check) · **Classes:** `AF-WCC-VAC-GEN`, `AF-SCC-C0-VAC-GEN` · **Gate:** G-FORM
**Task:** one bounded class-bound task, self-selected (no inbox card for worker-086 at launch 2026-09-12T00:50:04).
**Serves:** REC-12 item 3 of `astra-lifecycle-05` (`runtime/state/controller_verification/astra-lifecycle-05-decisions.json`), whose wording is *"correct the F1 variant SET/CH strictness text at the worker-076 lines (assertion direction only)"*.

## Result

`verdict = REV13_F1_DIRECTION_VERIFIED__MECHANICAL_CLEAN__F0_DECISIONS_PENDING`

1. **Direction verified independently.** For a future-directed causal geodesic and past-closed `J^-(q)`:
   fixed-`q` whole-curve containment **⇔** fixed-`q` tail containment (L1), and `VIS_tail ⇒ VIS_set` (L2) while
   `VIS_set ⇒ VIS_tail` fails on an ω-chain (L4). Hence **`VIS_tail` is strictly stronger and variant SET is strictly
   weaker** than the class predicate. Checked exhaustively over all 389 preorders with ≤4 points, all chains and all
   non-empty `Q` (60 598 chain×Q evaluations; 0 violations in L1/L2/L3/L5) plus a symbolic ω-chain certificate.
   This confirms the rev13 correction and falsifies both the rev12 `strictly STRONGER` labels.
2. **rev13 repair verified at the live bytes.** F1 canonical and authoring mirror (`d9cebb9404b2e79e`): the variant-SET
   relation now reads `strictly WEAKER`; the D5 note now proves whole ⇔ tail EQUIVALENT instead of `strictly STRONGER`;
   the unsound "misclassification" rationale is removed; the negation line (`B`-containment stronger) and the strictness
   falsifier are correct as written. The CH leg is correct in both the C0 schema and the registry.
3. **Mechanical residual clean.** The lead's `variant_rebase_rev29.py` landed at 00:57:02, re-basing SET/CH deltas and the
   registry to the rev13 bases and flipping the SET strength. Independently re-checked here: 9/9 re-base assertions
   (base pins, `from` == live F1 definition, direction text, w076 evidence ref, `check_variant_deltas` VALID,
   `check_variant_registry` VALID, both evidence files matching their FROZEN pins).
4. **Two F0 decision items remain** (corroborating lead blocker L-FORM-03, not a first report):
   * **R1** `research_map/formulation_taxonomy.yaml:200` still says the set-based reading *"is strictly stronger"*.
     This is **G-F0 canonical** (`0abb9ed8a961`, REC-11-frozen): any write voids G-F0 and needs fresh accepts.
   * **R2** `artifacts/formulation/formulation_taxonomy.yaml:176` (D1 ledger): `(strictly stronger)` attaches to the
     **negation** reading ¬SET, which *is* strictly stronger than ¬tail. The row is not a plain inversion; propose a
     clarification, not a flip. Supplement is companion-pinned and consistency-checked.
5. Exhaustive quote-normalized census (schemas/, artifacts/formulation/, research_map/, reviews/): **1 residual assertion**
   (R1), 1 negation-level decision (R2), 3 tool-constant mentions, 11 event-record mentions, 2 historical snapshots.
   Nothing else live asserts the inverted direction; `ledger/ evaluation/ numerics/ framework/ proposals/ proposed/ runs/
   data/ _out/ erdos64/` are clean.

## Files

| file | role |
|---|---|
| `probe_visdir.py` | deterministic, read-only, fail-closed probe (exit 0 clean, 2 unmeasurable, 3 pin drift) |
| `report.json` | full measurement: pins, carriers, math check, census, re-base checks, decision items |
| `candidate/candidate_patch.json` | residual patch state — all three mechanical carriers `ALREADY_APPLIED` at the pinned bytes |
| `patch_candidate.diff` | empty: nothing left to patch mechanically |
| `MANIFEST.sha256` | sha256 of every file in this directory |

## Reproduce

```bash
python3 artifacts/worker-086/visdir_repair_loc/probe_visdir.py
```

## Falsifier / next falsifier

**Falsifier:** an asserting live carrier of the inverted direction beyond the two F0 artifacts; any finite causal chain
with `VIS_set ∧ ¬VIS_tail`; any `q` with `tail ⊆ J^-(q)` but `whole ⊄ J^-(q)`; or a frozen pin that stops matching live bytes.
**Next falsifier:** re-run after any F1 / registry / taxonomy / FROZEN revision — a changed sha256 voids this snapshot.
**Acceptance:** R1/R2 closed by an explicit controller ruling (R1 authorized edit + F0 re-round, or a documented waiver;
R2 clarified + consistency re-run + FROZEN re-pin, or explicitly accepted as negation-level wording).

## Authority

Worker artifact only. No canonical, frozen, review, or comms path was written by the probe. This record cannot set a node
`done`, a `validation_status=passed`, or a gate verdict. The run of `check_variant_deltas.py` during the session rewrote
`artifacts/formulation/evidence/variant_delta_check.json` byte-identically (sha256 `fc6ee058dd96…`, the FROZEN rev29 pin).
