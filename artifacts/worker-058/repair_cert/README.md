# W058-REPAIR-CERT-02 — full-text order/strength sweep of the SCC canonical pair + pre-registered repair acceptance test

**Worker** `worker-058` (slot 058) · **task** W058-REPAIR-CERT-02 · **node** F2b (class pair F2a/F2b) ·
**classes** `AF-SCC-C0-VAC-GEN`, `AF-SCC-C2-VAC-GEN` · **gate context** G-FORM · read-only on canonical bytes.

**Checker verdict: FAIL — 2 hard findings, 3 advisories, 35 consistent claims, sensitivity self-test 7/7.**
One hard finding is the already-recorded gate-relevant defect (HF-1); the second is a current-hash status
refresh of the recorded **minor** labelling item R2-10 (MINOR-1), which this checker treats as blocking for a
clean sweep but which the gate owner may adjudicate as non-blocking.

## Binding (verified byte-identical to the frozen manifest)

| input | path | sha256 |
|---|---|---|
| C0 schema | `schemas/af_scc_c0_vacuum.yaml` | `1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508` |
| C2 schema | `schemas/af_scc_c2_vacuum.yaml` | `b6123750b37d8bee1e92eeb025979a6afdf3b29a33331a9d8499e21398d13fb2` |
| manifest | `artifacts/formulation/FROZEN.json` | `2554e276a0db70579ce36f7e665c9af81a1707bdc99e33758e861bec1d2df2e3` (revision 26) |

Both SCC files pin-match the rev26 manifest (`frozen_match: true`). Verdicts bind to the hashes above, not to
the revision number: re-run with

```bash
python3 artifacts/worker-058/repair_cert/sweep_scc_order.py --root . --out <path>.json
python3 artifacts/worker-058/repair_cert/run_sensitivity_selftest.py --root .
```

## Scope — what this adds over the prior audits

| prior artifact | coverage | this sweep |
|---|---|---|
| `W058-CONTAIN-01` (this slot, 00:21) | `implication_ledger` only; limitation #3 says statements outside it are not swept | sweeps the **whole YAML scalar content** of both files, including `must_not_conflate`, `anti_scope`, `class_identity_variants`, `conclusion.forbidden_weakenings/strengthenings` |
| `W080-FORM-SEP-05` | re-binds FORM-SEP-04's ledger containment inversion | adds the direction-bucket and non-ledger rules, plus a repair acceptance test |
| `deepseek-flash-08` `FORM-SEP-04` | scanner X2 explicitly flags C0/C2 meaning **outside** `anti_scope`/`variants` | this sweep deliberately includes `anti_scope` and `class_identity_variants` |
| `worker-057` XDATA | recorded the C0:157 denial sentence as needing lead adjudication | re-measured as an **advisory** with an explicit reason (below) |
| `R2_scc_separation_review` R2-10 (rev5) | minor labelling finding, both files, status "open" at rev5 | status-refreshed at rev11: fixed in C2, **still open in C0** |

Independent implementation: fresh code, clause-level comparator/regularity grammar plus explicit rank and
direction tables; it does not import or read the predecessor's, worker-080's, or flash-08's scanners.

## Hard findings

### HF-1 · `class_size_predicate_inverted` · `AF-SCC-C0-VAC-GEN` · line 251

`implication_ledger.forbidden_transfers[0].reason`:

> "C2 is a strictly larger extension class, so C2-inextendibility is strictly weaker"

- The declared chain (same file, line 244) is `E_C0 ⊃ E_H2loc ⊃ E_{C^1,1} ⊃ E_C2`, so **C2 is the smaller**
  extension class. The antecedent is false.
- The consequent (`C2-inextendibility` is strictly weaker) and the forbidden transfer direction are correct;
  the defect is the one-word antecedent.
- **Repair (wording only):** `strictly larger` → `strictly smaller`.
- This is the third independent confirmation at hash `1bb78ce9` (after W058-CONTAIN-01 and W080-FORM-SEP-05)
  and the defect is **unchanged** since flash-08 recorded it at `a8d899d2` (00:11:04).

### MINOR-1 · `strength_bucket_mismatch` · `AF-SCC-C0-VAC-GEN` · line 240

`conclusion.forbidden_weakenings[5]`: `"replacing future by two-sided direction"`.

- Two-sided inextendibility is strictly stronger than future-only inextendibility — the same file says so at
  line 231 (`forbidden_strengthenings`), and the C2 sibling repaired the analogous mislabel
  (`af_scc_c2_vacuum.yaml` line 238).
- Recorded as **minor / labelling** by `R2_scc_separation_review` R2-10 at revision 5 for both files, status
  "open". At revision 11 the C2 side is fixed and the C0 side is not; this is the current-hash refresh.
- **Repair:** move the item to `conclusion.forbidden_strengthenings` (the prohibition itself stays).
- The checker treats any strength-label inconsistency as FAIL so that the acceptance test is unambiguous; the
  underlying severity remains **minor** as recorded by R2.

## Advisories (not hard failures)

1. `denial_tension_with_ledger` — C0 line 157 (`regularity.must_not_conflate[0]`): "No containment with C2 or
   C0 is asserted here" while line 244 asserts the nested containment. Read in context ("here" = the
   curvature-axis definition, and the sentence bans the informal phrase "strictly between"), the sentence is
   defensible; it is reported so a reviewer can decide, not as an inversion. Worker-057 raised the same
   sentence; no repair is forced by this sweep.
2. `variant_class_identity_tension` (C0) — `must_not_conflate` calls H2_loc a "DIFFERENT class" while
   `anti_scope` registers H2LOC as a **variant** of C0, "not a separate class id".
3. `variant_class_identity_tension` (C2) — same tension, plus "separate tokens and nodes" in
   `regularity.must_not_conflate[1]`: `VARIANT_REGISTRY.json` v2.0 registers variants by
   `parent_class + variant_id` and has **no node field**, so "nodes" is not backed by the registry.

These are wording/registry-hygiene items; a reasonable repair is to say "distinct extension predicate /
registered variant", never "separate node".

## Pre-registered repair acceptance test

After the lead re-freezes C0, run the checker. **PASS iff `hard == 0` at the new hash**; the three advisories
may persist or be repaired. The required repairs are exactly the two above (HF-1 wording, MINOR-1 bucket
move), nothing else. Mutant `M1_repair_both` applies both by string surgery and the checker returns PASS with
zero hard findings, so the test is known-achievable before it is applied to canonical bytes.

## Sensitivity (falsifier actually falsifies)

`run_sensitivity_selftest.py` builds mutants under `_scratch/<case>/`, with outcomes pre-registered before the
run; `all_expectations_met = true`, 7/7:

| case | mutation | expected | observed |
|---|---|---|---|
| M0 | canonical | FAIL, HF-1 + MINOR-1 | FAIL, both, lines 251/240 |
| M1 | apply both repairs | PASS, 0 hard | PASS, 0 |
| M2 | plant "C2 is a strictly larger extension class … strictly stronger" in C0 `anti_scope` | FAIL at the planted path | caught (`anti_scope`, size + strength) |
| M3 | flip variant CH relation to "strictly STRONGER" | FAIL `strength_predicate_inverted` | caught (`class_identity_variants`) |
| M4 | truncate C0 chain to `E_C0 contains E_C2` | FAIL `chain_concordance_failure` | caught |
| M5 | byte-identical copy | identical verdict to M0 | identical |
| M6 | plant the two-sided item in C2's `forbidden_weakenings` | FAIL `strength_bucket_mismatch` in C2 | caught |

## Assumptions and limitations

1. The declared chain is the audit axiom; the order is **not re-derived from the C0/C2 regularity
   definitions** (limitation #1 of W058-CONTAIN-01 is carried forward deliberately). A consistently inverted
   declaration in both files would evade this check by construction.
2. The sweep is lexical/semi-structured: it evaluates claims that carry a comparator token and a regularity
   token. Semantic leaks phrased without those tokens are out of scope.
3. `unchecked_incomparable_pair` results are recorded, never silently passed; the distributional-vacuum and
   CH variants are ranked `2.5` and incomparable with `H2_loc`/`C^{1,1}`/`C2`, so those pairs are not used to
   force a verdict.
4. Physical truth, citation scope, class-merge detection (FORM-SEP-04 owns it), and the genericity transfer
   matrix are not audited.
5. This artifact claims **no node completion and no gate verdict**; interpretation and any gate consequence
   belong to `astra-lead-formulation` / G-FORM reviewers.

## Falsifiers

- **Current:** a reader exhibits an order/strength claim this sweep accepts that contradicts the declared
  chain; or shows a reported hard finding is not present in the bound bytes; or shows the chain axiom is
  mis-derived.
- **Next:** re-run at the next canonical C0 hash — falsified if it reports PASS at `1bb78ce9` (the defect must
  remain visible), or FAIL after both repairs at the new hash (repair insufficiency or a new defect).

## Artifacts

| path | role |
|---|---|
| `sweep_scc_order.py` | independent full-text checker (read-only; `--root` for mutants) |
| `scc_order_sweep.json` | machine-readable findings, binding, acceptance test, falsifier |
| `run_sensitivity_selftest.py` | pre-registered mutant harness |
| `sensitivity_selftest.json` | expectations vs observations, 7/7 |
| `_scratch/` | mutant trees + per-case result JSON |
| `README.md` | this report |
