# W075-GFORM-REV29-REVIEW-08

Independent full-schema reviews of the three canonical class schemas at the FROZEN rev29 pins,
taken by `worker-075` (no inbox card for slot 075). Gate **G-FORM**; classes
**AF-WCC-VAC-GEN** (F1), **AF-SCC-C2-VAC-GEN** (F2a), **AF-SCC-C0-VAC-GEN** (F2b).

## Verdicts (cited hashes measured at verdict time)

| class | pin (sha256) | verdict | score | hard failures |
|---|---|---|---|---|
| F1 | `d9cebb9404b2…` | **accept** | 4.0 | none |
| F2a | `e9a27996dfd3…` | **revise** | 3.5 | `HF-075-F2a-VOCAB`, `HF-075-F2a-EXTCAT` |
| F2b | `b2ab6acb2bbe…` | **revise** | 3.5 | `HF-075-F2b-VOCAB`, `HF-075-F2b-LARGER` |

Verdict files: `reviews/F1-review-rev29-075.json`, `reviews/F2a-review-rev29-075.json`,
`reviews/F2b-review-rev29-075.json`. Manifest bound: FROZEN rev29 sha256 `815e08079aef…`
(50/50 pins matching disk at review time; target and manifest hashes stable across the window).

## Hard failures (all hash-bound, all still visible at the rev13 pins)

- **VOCAB (F2a, F2b).** `conclusion.conclusion_type` is `scc_c2_future_inextendibility` /
  `scc_c0_future_inextendibility`, but the bound F0 declared taxonomy
  (`research_map/formulation_taxonomy.yaml`, `field_vocabulary.conclusion_type.allowed`) allows
  only `[weak_cosmic_censorship, strong_cosmic_censorship_C2, strong_cosmic_censorship_C0]`, and
  the F0 class entries use `strong_cosmic_censorship_C2/C0`. `VOCAB_ALIASES.json` declares the
  `scc_*` tokens canonical, so two frozen artifacts disagree on the canonical token, and the alias
  policy forbids aliases in canonical artifacts. Needs gate-owner adjudication and one re-stamp.
- **EXTCAT (F2a).** `extension_predicate.definition` clause (c) and
  `topology.extension_topology` leave the extension manifold category unpinned ("a connected
  4-manifold"), while the F2b sibling pins SMOOTH (C-infinity) with a stated reason. The class
  asserts non-existence of extensions, so the extension category is load-bearing. Independently
  reproduces worker-091 `HF-091-02` (rev12); still present at rev13.
- **LARGER (F2b).** `implication_ledger.forbidden_transfers[0].reason` says "C2 is a strictly
  larger extension class" while the same file's containment chain has E_C2 as the smallest class.
  The row's conclusion is correct; the justification premise is inverted. Independently
  reproduces lead blocker L-FORM-01 / worker-060 / worker-096.

Soft finding on all three: `semantic_escape_rebased.json` binds the superseded C0 base
`1bb78ce9b357…` while the canonical C0 measures `b2ab6acb2bbe…`, so `run_acceptance.py` preflight
fails closed (exit 3) at the rev29 pins — schema content is unaffected, the lead tool suite is not
reproducible until `measure_semantic_escape.py` is re-run.

## Checks per class

Hash pin + mirror byte-identity; whole-manifest pin check; F0/evidence binding + redirected
checker replay; class identity/components vs the F0 declared axes; assertive-field class
isolation (foreign tokens and composite phrases); conclusion integrity (open_problem, promotion
rule, no proof inflation); F0 `conclusion_type` vocabulary; quantifier order/comeager domain and
extension direction/regularity; extension-category pinning; implication-ledger direction;
rev12→rev13 repair minimality; window stability. Seven negative controls on copies
(stale evidence hash, foreign class id, foreign token in an assertive field, composite phrase,
tampered FROZEN pin, inverted containment premise, hash-move sensitivity): **7/7 detected**.

## Reproduce

```bash
cd <repo>
python3 artifacts/worker-075/rev29_review/review_gform_rev29_075.py          # all three
python3 artifacts/worker-075/rev29_review/review_gform_rev29_075.py F2a      # one class
```

## Falsifier

Re-run the instrument at the same bytes: any check that flips, any control not detected, any
target/manifest hash move, any change outside the authorised repair set, or a demonstration that
the VOCAB/EXTCAT/LARGER findings are adjudicated and repaired at a new pin falsifies these
verdicts. Worker reviews only; the audit lead and controller own promotion and gate verdicts.
