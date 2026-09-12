# W04 F1 post-rebind recheck — F090-04 falsified, three major defects reproduced

| field | value |
|---|---|
| task | `asg-2026-09-11-F1-deepseek-flash-04-13` (node `F1`, class `AF-WCC-VAC-GEN`, gate `G-FORM`) |
| runtime | `worker-004-20260912T002201-968807`, actor `deepseek-flash-04` |
| bound target | `schemas/af_wcc_vacuum.yaml` sha256 `9a8bd4c9680042a4…` (FROZEN manifest revision 26, pin matches) |
| suite rechecked | `schemas/f1_falsifier_tests.jsonl` sha256 `c4c477adcb7ab889…` — 25 rows, all bound to `9a8bd4c9…` |
| report | `artifacts/worker-004/f1_recheck/report.json` sha256 `ed74256cfa26517a…` |
| tool | `artifacts/worker-004/f1_recheck/recheck.py` sha256 `5f680873fda19dc8…` (read-only; only `--out` writes) |
| verdict | advisory **revise** at the bound hash; no gate verdict, no node status, no theorem |

## Headline

1. **Reviewer-090 finding F090-04 is falsified at the current hash.** F090-04 claimed the
   suite still had 24 rows bound to `b65fcc0f` and "cannot be cited as falsifier-exercise
   evidence for these bytes until re-bound". The 00:20:49 rebind did exactly that: the suite
   now has **25 rows, one distinct binding (`9a8bd4c9…`, equal to the frozen canonical F1
   hash), all rows carrying `spacetime_description` + `does_it_satisfy_f1` + `deciding_field`**.
   Any gate or review read that still cites F090-04 as an open defect on the suite is reading
   pre-00:20:49 bytes.
2. **Three major defects reported by reviewers 090/094 are reproduced independently at
   `9a8bd4c9…`** (they are defects of the canonical schema, not of the suite):
   - `class_contract_pointer` (line 38) points at `artifacts/formulation/formulation_taxonomy.yaml#class_contracts.…`
     — the **authoring** tree — and that fragment **does not resolve** in the canonical
     `research_map/formulation_taxonomy.yaml` (top-level key is `classes`). The equivalent
     canonical pointer `classes.AF-WCC-VAC-GEN` does resolve. Two conflicting contract
     references inside one artifact.
   - Seven duplicate top-level `revised_at` keys (lines 8–23) plus two `revised_at_unused`
     keys: PyYAML last-wins yields `2026-09-12T00:30:00+08:00`, which is **future-dated**
     against both the file mtime (`00:19:14`) and wall clock. Two conforming readers can
     disagree on the revision timestamp.
   - The normative symbol `AF_{I+}` (line 251, `conclusion.statement_formal`) has **no
     definition** in the schema, either F0 tree, or `rule_spec.json`.
3. **The 25-row suite does not probe any of the three defect surfaces** (it does probe the
   F0 hash binding). Adding pointer-resolution / clock-and-key-hygiene / symbol-definition
   rows is the smallest suite increment that would have caught them; not applied here,
   because the suite hash `c4c477ad` is the one just rebound and reviewed.
4. **Self-reported drift (D1).** Invoking
   `artifacts/flash-04/f1_ambiguity/verify_freeze_current.py --help` executed the full
   verification (the script has no `argparse`) and rewrote its own hash-pinned report in
   place at `00:25:01`, superseding `frozen_current_verification.json#sha256:9fa4f77c…`
   (cited by `flash-04-art-F1-freeze-verify-20260912T002049`) with
   `#sha256:0e79514a…`. The new report still verifies `verify_pass` at FROZEN rev 26 /
   84/84 probes. A superseding artifact event for the new hash is emitted; the defect is
   recorded rather than hidden.
5. Observed, not adjudicated: the worker-037 `W037-F5` D0-disjunction surface
   (`forall (s,delta) in D0`) is present in all three class schemas; it belongs to
   worker-037's falsifier.

## Reproduction

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-004/f1_recheck/recheck.py --expect-sha 9a8bd4c9 \
    --out artifacts/worker-004/f1_recheck/report.json
```

Exit 0 = report written; exit 2 = fail-closed (a required file is missing or the canonical
F1 hash no longer starts with `--expect-sha`).

## Per-check results

| id | subject | result |
|---|---|---|
| D1 | in-place rewrite of the prior verification report | confirmed (self-inflicted, disclosed) |
| D2 | F090-04 "suite bound to b65fcc0f, 24 rows" | **finding refuted** (25 rows, bound `9a8bd4c9`) |
| D3 | HF090-01 pointer not canonical / fragment unresolved | confirmed |
| D4 | HF090-02 / HF-094-2 duplicate keys + future timestamp | confirmed |
| D5 | HF090-03 `AF_{I+}` undefined | confirmed |
| D6 | F090-05 consistency evidence carries no content hash | confirmed |
| D7 | suite coverage of D3–D5 | confirmed gap |
| X1 | W037-F5 D0-disjunction surface | observed only |

## What this is not

Not a physics verification, not a literature check, not a gate verdict, not a node
transition, and not a review of the ambiguity suite's semantic adequacy. Worker events
cannot set `status=done`, `validation_status=passed`, or a gate verdict; this bundle is
hash-bound machinery evidence for the controller and the F1 owner.

## Next falsifiers

1. F1 owner repoints `class_contract_pointer` to
   `research_map/formulation_taxonomy.yaml#classes.AF-WCC-VAC-GEN`, collapses the duplicate
   `revised_at` keys to one wall-clock-valid value, and defines or inlines `AF_{I+}`; then
   re-run `recheck.py` and D3–D5 must flip to `not_refuted` at the new hash.
2. Any further F1 write voids the `revise` verdict bound to `9a8bd4c9`; the verdict must be
   re-measured, not transferred.
3. If a future gate read cites F090-04 as a suite defect, re-measure the suite first: D2
   shows the citation is stale.
4. Restore or formally retire the `frozen_current_verification.json#9fa4f77c` evidence ref
   cited by the 00:20:49 events; D1 records the superseding hash.
