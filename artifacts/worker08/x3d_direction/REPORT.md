# W008-FORMSEP04-X3D-01 — document-relative entailment-direction certification

Worker: worker-008 (`deepseek-flash-08`). Classes `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`.
Node F2b, gate G-CLASSBIND. Worker lifecycle only: **no node done, no gate verdict, no
`validation_status=passed`, no canonical write**; canonical paths were read-only.

## Trigger (self-correction of this slot's own instrument)

`W008-FORMSEP04-CANDIDATE-VALIDATION-01` (01:06) emitted `CANDIDATE_CLEARS_FORMSEP04` for
worker-066's rebased candidate `84b5d3fa29a6`, on a FORM-SEP-04 X1–X5 battery whose X3c
containment-inversion check returned **0 hits**. The sibling lifecycle
`W008-F2B-LINE152-DIRECTION-01` (01:12, `artifacts/worker-008/f2b_line152_direction/evidence/report.json#825718def80b`) then showed the candidate's
`regularity.must_not_conflate[0]` asserts `S_H2loc => S_C0`, the forbidden converse under the
C0 document's own declared order. The assigned acceptance instrument was not repaired by that
run; this run repairs it and re-verdicts the pinned corpus.

## Root cause (exact)

`artifacts/worker08/c2_c0_separation_audit.py` v3 `classify_dual_sentence` special-cases

```
(C0|H2_loc|C^{1,1})[- ]?inextendibility ... (entails?|implies?|subsum\w*) ... (this class|C2)
```

as `correct_direction` **without resolving `this class` against the document that carries the
sentence**. The carrier sentence is true in the C2 schema (own class = C2, rank 3) and false
when transplanted byte-for-byte into the C0 schema (own class = C0, rank 0): same sentence,
different carrier document, opposite truth value. Document-relative self-reference was never
bound.

## Rule implemented (X3d, v1)

1. `size_rank` is parsed from the carrier document's own `implication_ledger.extension_class_containment`
   (`contains` or `subset of` chain). Fail-closed if absent/unparseable or not the frozen order
   `C0 > H2loc > C^1,1 > C2`.
2. `this class` / `this class's conclusion` resolves to the carrier document's own `class_id`.
3. `S_A entails S_B` is licensed iff `size_rank(A) <= size_rank(B)` (A's extension set is a
   superset of B's, so inexistence for A is the stronger statement).
4. Pre-registered carriers: `regularity.must_not_conflate[*]`,
   `implication_ledger.extension_class_containment`, `.subsumption_note`,
   `.forbidden_weakenings[*]`, `.one_way_entailments[*].reason`, `.forbidden_transfers[*].reason`.
5. Negation governs the verb → denial, not assertion; attributed/quoted mentions skipped;
   a strict entailment verb joining two class referents that the primary pattern cannot resolve
   is surfaced as `unresolved` (never silently clean). Any unresolved carrier blocks certification.

## Result — X3d-certified, 8/8 controls

| # | carrier (pin) | expected | observed |
|---|---|---|---|
| K1 | `schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe` (canonical C0) | PASS | PASS |
| K2 | `schemas/af_scc_c2_vacuum.yaml#e9a27996dfd3` (canonical C2; **same sentence as K3**) | PASS | PASS |
| K3 | `artifacts/worker08/rev29_candidate/af_scc_c0_vacuum.repair-candidate.yaml#84b5d3fa29a6` | FAIL | **FAIL, exactly 1 hit** `regularity.must_not_conflate[0]`: `H2loc => C0`, ranks [1, 0] |
| K4 | `artifacts/worker-008/f2b_line152_direction/pinned/candidate_9ab32ee3.yaml#9ab32ee39d00` | PASS | PASS |
| K5 | `artifacts/worker-080/f2b_hf1_direction_census/snapshots/679ab7bc8746__CANDIDATE_schemas_af_scc_c0_vacuum.yaml#679ab7bc8746` | PASS | PASS |
| K6 | synthetic C0: `this class's conclusion ENTAILS H2_loc-inextendibility and C2-inextendibility, never the reverse` | PASS | PASS |
| K7 | synthetic C0 canary: `C2-inextendibility entails this class's conclusion` | FAIL | **FAIL, 1 hit** |
| K8 | synthetic C2: `H2_loc-inextendibility ENTAILS this class's conclusion` | PASS | PASS |

K2 vs K3 is the discriminator: the identical carrier sentence is certified PASS in the C2
document and FAIL in the C0 document, solely by document-relative resolution. Unresolved
carriers: **0**. Instrument verdict: **X3D_CERTIFIED**.

## Hash-bound v3 false negative

`artifacts/worker08/rev29_candidate/battery_candidate.json#2b7b19840256`: battery verdict **PASS**,
`X3c_containment_inversion` hits **0**, measured against candidate
`84b5d3fa29a677ad157b924675bb5a9c08281395920be0221535465a5da44b40`. That is the exact artifact that carried the predecessor's
`CANDIDATE_CLEARS_FORMSEP04`; X3d now returns 1 hit on the same bytes.

## Consequence (worker-level, owner binds interpretation)

- **Withdraw** `W008-FORMSEP04-CANDIDATE-VALIDATION-01`'s `CANDIDATE_CLEARS_FORMSEP04` at
  `84b5d3fa29a6`. X3d-certified: `84b5d3fa29a6` **fails** FORM-SEP-04 (X3d); `9ab32ee39d00`
  and `679ab7bc8746` clear it.
- The **canonical gate has the analogous blind spot, unchanged and not touched here**:
  `artifacts/formulation/tools/check_class_schema.py:367-370` requires a **C2 subject** for the
  R16 prose-converse check, so an `H2_loc`-subject converse against the C0 class escapes; R06
  (`:235-239`) only requires `must_not_conflate` to be non-empty. Reported as a finding for the
  instrument owner; canonical detector writes were frozen (CF-29) and none were attempted.
- Evidence for G-CLASSBIND / F2b landing review. No gate verdict, node status or
  `validation_status` transition is claimed.

## Falsifier

Any pin move voids the run (fail-closed). Certification is falsified if: the same carrier
sentence is classified identically in C0 and C2 documents (document-relative resolution
broken); `84b5d3fa29a6` does not return exactly one inverted hit at
`regularity.must_not_conflate[0]`; `9ab32ee39d00` or `679ab7bc8746` returns any hit; K6/K7/K8
flip; or an unresolved entailment carrier is counted as clean.

## Limitations

- Structural direction consistency only, against each document's **own declared** order; it does
  not re-adjudicate whether that order is the physically right one (normativity remains with
  `astra-lead-formulation`).
- Regex prose classification with a conservative fail-closed path; synonyms outside the
  registered token/verb sets are reported as unresolved rather than interpreted.
- Control fixtures K6–K8 are generated by the instrument itself; the external controls K1–K5 are
  the load-bearing ones.
