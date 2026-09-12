# W003-CLASSSEP-D0-COVERAGE-01 — detector coverage for the live D0 disjunction

**Worker:** worker-003 · **Node:** F2 · **Class:** `AF-SCC-C2-VAC-GEN`
(shared D0 also present in `AF-SCC-C0-VAC-GEN`, `AF-WCC-VAC-GEN`) · **Gate:** G-FORM
**Task:** one bounded, class-bound, evidence-only measurement.
**No gate verdict, no review verdict, no edit to the detector or the corpus.**

## Question

The standing class-separation detector (`research_map/class_separation.py`) plus its
27-fixture corpus is reported PASS (`tp 17 / tn 10 / fp 0 / fn 0`) by the controller
lifecycle. A live G-FORM concern, documented independently as **W037-F5**
(`artifacts/worker-037/gform_freeze_verification/report.json`), says the three schemas
quantify their class statement over a two-branch regularity domain:

```
quantifiers.domains.D0.definition:
  "admissible regularity pairs: Sobolev variant s > 5/2 and delta in (1/2,1),
   or the smooth-with-decay default"
```

Does that PASS provide any coverage for this failure mode?

## Answer (measured, 7/7 checks pass, zero drift)

**No.** Three mechanisms are measured, not asserted:

1. **Vocabulary.** R1's `_MERGE_PAT` matches only bare `C0 or C2` composites.
   The regularity-setting disjunction in D0 is outside its vocabulary.
2. **Key scope.** `definition` is not in `ASSERTED_LINE_KEYS`, so the D0 definition
   is never declaration-scanned. The detector *is* alive in that text region: the same
   D0 slot carrying `"C0 or C2 are one class"` **is** flagged (control P1) — so the
   silence is specificity, not a dead scan.
3. **Corpus.** 0 of 27 fixtures exercise a D0-style regularity-setting disjunction.
   The corpus PASS therefore cannot cover it.

**Sensitivity is zero:** replacing the live disjunction with the single-branch form
`"admissible regularity pairs: Sobolev variant s > 5/2 and delta in (1/2,1)"` changes
no detector output on any of F1 / F2a / F2b (findings delta 0/0/0).

Baseline independently reproduced: `tp 17 / tn 10 / fp 0 / fn 0`, `corpus_size 27`, PASS.

**Secondary observation (not needed for the claim):** a full known class-id
disjunction `AF-SCC-C2-VAC-GEN or AF-SCC-C0-VAC-GEN are one class` in the D0 slot is
also silent (control P4) — adjacent to W027-CLASSSEP-ARITY-01, flagged for the detector owner.

## Consequence (scope-limited)

`classsep PASS` is **not** coverage for the G-FORM single-frozen-data-class criterion
and is **neither evidence for nor against** W037-F5. It neither confirms nor refutes the
two F2a accepts that conflict with F2a-review-088's HF-088-1.

## Falsifier

Re-run:

```bash
python3 artifacts/worker-003/classsep_d0_coverage/probe_classsep_d0.py
```

Falsified if (a) any canonical D0 line or D0 mention produces a class-separation
finding, (b) a corpus fixture contains a D0-style regularity-setting disjunction,
(c) control P1 (shorthand in the D0 slot) fails to flag, or (d) the single-branch
rewrite changes any finding. Any input-hash drift voids the run (exit 3) rather than
falsifying it.

## Frozen inputs / artifacts (sha256)

| role | path | sha256 |
|---|---|---|
| probe | `artifacts/worker-003/classsep_d0_coverage/probe_classsep_d0.py` | `cd8f67b1d8fa73fd8cfd3644bd7aba9396aa8930d0a080963c083f20d193a905` |
| report | `artifacts/worker-003/classsep_d0_coverage/report.json` | `ee263b42fd143daafd1ae8f49fb983327f0e3053315849b96ff8475cfed1c987` |
| detector | `research_map/class_separation.py` | measured in report |
| corpus | `artifacts/worker-07/class_separation_falsification/results.json` | measured in report |
| F1 | `schemas/af_wcc_vacuum.yaml` | measured in report |
| F2a | `schemas/af_scc_c2_vacuum.yaml` | measured in report |
| F2b | `schemas/af_scc_c0_vacuum.yaml` | measured in report |

`report_payload_sha256` in `report.json` covers the record with that field removed;
`generated_at` is the only non-deterministic field (two runs gave identical decision
fields and identical checks).
