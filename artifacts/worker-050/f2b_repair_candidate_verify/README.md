# W050-F2B-REPAIR-CANDIDATE-INDEPENDENT-VERIFY-06

Independent, non-author, fail-closed verification of the F2b two-line repair candidate proposed by
worker-001. Class `AF-SCC-C0-VAC-GEN`, node F2b, gate G-FORM. Read-only over all pinned inputs.

- **Verdict: `CANDIDATE_VERIFIED_MINIMAL_FIX` (exit 0, 9/9 checks, 6/6 controls)**
- Pre-registration: `PREREGISTRATION.md` (frozen before run 1)
- Instrument: `verify_repair_candidate.py` (stdlib + PyYAML; re-run to reproduce)
- Report: `report.json`; per-check: `per_check.jsonl`
- Run 1 + disclosed instrument amendments: `report.run1.json`, `INSTRUMENT_AMENDMENTS.md`

## What was measured

Pins (full sha256 in `report.json::pins`): base F2b rev13 `b2ab6acb2bbe…`, candidate
`90ede5c9516b…` (non-canonical), declared diff `a45fbae3a8af…`, F2a `e9a27996dfd3…`, F1
`d9cebb9404b2…`, F0 `0abb9ed8a961…` + supplement `d7419b4e8963…`, FROZEN `815e08079aef…`, VOCAB
`46cd9f1eb534…`. Pin guard passed at start and end; no input moved.

1. **Minimality (C1, C2, C9).** Recursive key skeleton identical base→candidate; byte diff is
   exactly two 1-for-1 line replacements at lines **152** and **246**; the declared diff file's two
   hunks match the computed diff line-for-line; `must_not_conflate` 5→5, `one_way_entailments` 4→4,
   `forbidden_transfers` 3→3, `conclusion_type` and `extension_class_containment` unchanged.
2. **D1 fixed (C3).** Base line 152 contains `No containment with C2 or C0 is asserted here`;
   candidate does not. Candidate line 152 scopes the denial to the regularity axis and defers
   containment to `implication_ledger.extension_class_containment`, which is present and parses to
   `C0 ⊃ H2loc ⊃ C^1,1 ⊃ C2`.
3. **D2 fixed (C4).** Base line 246 contains `C2 is a strictly larger extension class`; candidate
   does not. Candidate reason: `E_C2 is a strictly smaller extension set than E_C0, …`, mechanically
   consistent with the chain above.
4. **No residual carriers (C6).** None of the D1/D2 carriers remain anywhere in the candidate; the
   only `strictly between` is the quoted prohibition the base file mandates.
5. **Cross-sibling agreement (C7).** F2a's chain (`E_C2 ⊂ E_{C^1,1} ⊂ E_H2loc ⊂ E_C0`), the
   candidate's chain (same, listed largest-first) and candidate line 246 all state the same
   direction; candidate line 152 does not deny extension-set containment in any form.
6. **D3 unchanged — global residual `W050-R1-D3` (C5).** Candidate `conclusion_type` is the
   VOCAB-canonical `scc_c0_future_inextendibility`; it is absent from F0's declared allowed list
   (whose token is `strong_cosmic_censorship_C0`, a declared alias of the canonical token). **F2a is
   in exactly the same representation state** (`scc_c2_future_inextendibility` vs
   `strong_cosmic_censorship_C2`). D3 is therefore a global F0/VOCAB reconciliation item, symmetric
   across the two SCC classes, not an F2b-specific defect and outside the candidate's declared
   two-line scope.
7. **Controls (K1–K6).** Reverting edit A redetects D1; reverting edit B redetects D2; inverting
   `smaller`→`larger` is detected; the pin guard rejects a wrong candidate hash; deleting line 152
   and dropping `implication_ledger` are both detected.

## What this does and does not license

- It **does** establish, at the pinned bytes, that the candidate is a minimal two-line repair of D1
  and D2 with no structural drift and no new contradiction, and that D3 is a global symmetric
  residual rather than an F2b blocker.
- It does **not** count as a full-schema verdict, a node `done`, a `validation_status=passed`, or a
  gate verdict. Worker-050 authored neither F2b, the candidate, F2a, F0 nor VOCAB; it did author the
  D1/D2/D3 defect list and the earlier containment-cluster report (disclosed).

## Falsifiers

VF1 any pinned input moves (exit 3, measurement void). VF2 an independent reader reproduces a
base→candidate diff other than the two declared hunks. VF3 the candidate denies extension-set
containment or states the E_C2/E_C0 order backwards. VF4 F2a is in a different F0-vocabulary
representation state than F2b (would refute the D3 symmetry classification). VF5 re-running the
instrument on identical bytes yields a different report.

## Re-run

```bash
cd <repo root>
python3 artifacts/worker-050/f2b_repair_candidate_verify/verify_repair_candidate.py
# exit 0 verified / 2 check failure / 3 pin drift (void) / 4 control failure
```
