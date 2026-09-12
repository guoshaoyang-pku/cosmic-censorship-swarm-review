# W080-F2B-HF1-DIRECTION-CENSUS-01

**Slot** `worker-080` · **Class** `AF-SCC-C0-VAC-GEN` · **Node** `F2b` · **Gate** `G-FORM`
**Pins** live F2b `b2ab6acb2bbe`, F2a `e9a27996dfd3`, F0 `0abb9ed8a961`, FROZEN rev29 `815e08079aef`,
worker-070 candidate frame/report `20687555b7f5` / `1be0cdb611fa`
**Verdict at worker level** 7/10 declared repair candidates are semantically landable; 2 carry the
inverted entailment direction; 1 still carries the HF1 denial. No gate verdict, no node status.

## Why this task

worker-070's candidate census (`artifacts/worker-070/f2b_candidate_census/report.json#1be0cdb611fa`)
measured the 10 declared F2b rev29 repair candidates byte-wise and found 9/10 discharge both
standing carriers. Its predicates `P1`/`P2` only require the defective phrases to be **absent**:
they do not check the **direction** of the replacement sentence. The repair that was circulated
first (`84b5d3fa29a6`) failed exactly there, and worker-070 explicitly recorded that "HF1 wordings
do not converge" (9 distinct texts). This instrument closes that gap: it classifies each
candidate's HF1/HF2 prose against the entailment order derived from **that candidate's own
machine-readable `implication_ledger.one_way_entailments`**.

## Method

1. Pin and byte-snapshot every input (`snapshots/`); fail closed on any pre-run hash drift.
2. Strict `yaml.safe_load` each candidate at its declared sha256 (all 10 resolved).
3. Derive ground truth from the bytes under test, never hardcoded:
   `own -> C2` gives `E_C2 ⊂ E_C0`; `own -> H2LOC` gives "this class's conclusion entails
   H2_loc-inextendibility"; `H2LOC -> C2` gives "H2_loc-inextendibility entails the C2 sibling".
4. HF1 (`regularity.must_not_conflate[0]`): strip `[...]` editorial brackets, detect the
   registered denial pattern, otherwise parse asserted directed pairs (`X entails Y`,
   passive reversal, negated objects such as "not this class" excluded) and compare with the
   ledger set. Labels: `CORRECT` / `INVERTED` / `UNSUPPORTED` / `NEUTRAL_NESTING` / `DENIAL` /
   `AMBIGUOUS`.
5. HF2 (`implication_ledger.forbidden_transfers[0].reason`): classify the size claim
   (`C2_LARGER` / `C2_SMALLER`) and compare with the derived order; also require
   `from = C2` and `to = this class`.
6. Invariants compared to live: `class_id`, `node_id`, `conclusion.conclusion_type`,
   `conclusion.statement_formal`, `implication_ledger.extension_class_containment`,
   `implication_ledger.one_way_entailments`, `f0_binding.declared_f0_sha256`,
   `regularity.extension_regularity`. A variant-registry claim in HF1 (candidate `679ab7bc8746`)
   is checked against the pinned `VARIANT_REGISTRY.json`.
7. Landable = HF1 ∈ {CORRECT, NEUTRAL_NESTING} ∧ HF2 = CORRECT ∧ invariants preserved ∧
   registry claim (if any) verified.
8. Nine controls, including a **ledger-flip control** (K8) proving the ground truth is read
   from the candidate bytes and not hardcoded, and a determinism re-classification (K9).

## Result

| sha256 | author | HF1 | HF2 | landable |
|---|---|---|---|---|
| `a110f8e875af` | worker-022 | NEUTRAL_NESTING | CORRECT | yes |
| `84b5d3fa29a6` | worker-002 | **INVERTED** (`H2LOC->C0`) | CORRECT | **no** |
| `9ab32ee39d00` | worker-023 | **CORRECT** (`C0->H2LOC`) | CORRECT | yes |
| `679ab7bc8746` | worker-024 | NEUTRAL_NESTING | CORRECT | yes |
| `51c253c46306` | worker-080 | **CORRECT** (`C0->H2LOC`, `H2LOC->C2`) | CORRECT | yes |
| `4951cc969803` | worker-080 | NEUTRAL_NESTING | CORRECT | yes |
| `1315427fbc92` | worker-083 | NEUTRAL_NESTING | CORRECT | yes |
| `3cdcaa44e6f1` | worker-047 | **DENIAL** | CORRECT | **no** |
| `48cadb72e507` | worker-044 | **INVERTED** (`H2LOC->C0`) | CORRECT | **no** |
| `b598b59e09e5` | worker-088 | NEUTRAL_NESTING | CORRECT | yes |

* **New finding, beyond `W080-F2B-REPAIR-H2E-01`:** `48cadb72e507` (worker-044's "rev13
  integration") carries the *same* HF1 inversion as `84b5d3fa29a6`. Both pass worker-070's
  byte predicates because the denial phrase is gone — the replacement asserts the reverse of
  their own `one_way_entailments`.
* **Consequence for the standing rev30 rehearsal:** `artifacts/worker-058/rev30_freeze_rehearsal/report.json#1e31bbe5e933`
  rehearses the freeze chain with `84b5d3fa29a6` as the C0 candidate (dual/battery PASS). That
  candidate is semantically unsafe; it must not be frozen as rev30.
* **Direction-explicit and safe set:** `9ab32ee39d00` and `51c253c46306`. The remaining five
  landable candidates state the nesting and defer the direction (safe, less explicit).
* **Soft flag:** `a110f8e875af` uses "strictly between" descriptively inside the slot that
  declares the phrase not used; advisory only, not a blocking defect.

## Reproduction

```bash
python3 artifacts/worker-080/f2b_hf1_direction_census/census_hf1_direction.py   # exit 0
```

Deterministic; 10/10 candidates resolved, 9/9 controls pass, no pin drift.

## Falsifier

Re-run at the same pins. Falsified if any candidate's declared sha256, HF1/HF2 classification,
asserted-pair set, registry claim or invariant diff differs; if a candidate asserting
`H2_loc-inextendibility => own conclusion` is classified CORRECT (or the reverse direction
INVERTED) while its own `one_way_entailments` carries the corresponding row; if a control fails.
Any pinned byte moving voids the run rather than falsifying it.

## Not claimed

No gate verdict, no node status, no `validation_status=passed`, no canonical write. No mathematics
claim beyond prose-vs-ledger direction consistency. No adjudication of the sidecar /
consistency-evidence binding defects (outside the schema bytes). No ranking of candidates beyond
the semantic landability predicate.
