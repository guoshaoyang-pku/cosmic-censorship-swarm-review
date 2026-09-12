# W094F-CF21-REV13-RECHECK-01 — CF-21 re-measured at FROZEN rev29

**Agent:** worker-094 (bounded execution worker) · **Gate scope:** G-F0 / G-FORM (advisory evidence only)
**Class binding:** `AF-WCC-SCALAR-SPH` (primary, hard failures); `AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN` (checked)
**Node:** F0 · **Created:** 2026-09-12T01:1x+08:00 · **Verdict:** `CF21_LIVE_AT_REV13_INVARIANT`

## Why

Worker-094's `W094-GENERICITY-CONSISTENCY-01` (report `10a92ff3c9c1d4`) supplied the declared
checker for controller finding **CF-21** and measured it at the **rev12** schema bytes with the
taxonomy at `0abb9ed8a961`. Its declared `next_falsifier` was to re-run the checker once the
formulation owner repinned or repaired the taxonomy.

Between 00:52:15 and 00:57:26 the three class schemas moved **rev12 → rev13** under **FROZEN
revision 29** (`815e0807`, evidence-binding repair, CF-20). The taxonomy did not move. This task
executes the declared re-run against the live gate-relevant bytes, without editing or copying the
instrument: the byte-identical declared checker is **imported** (pinned `4adcfcbe9884`) and its own
declared rules and 7 in-memory controls are applied to the live inputs, then the per-class verdicts
are diffed against the rev12-pinned report.

## Live pins (measured at run time; 0 drift before/after)

| input | sha256 |
|---|---|
| `research_map/formulation_taxonomy.yaml` (F0 rev5, G-F0-pass bytes) | `0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3` |
| `schemas/af_wcc_vacuum.yaml` (F1 rev13) | `d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d` |
| `schemas/af_scc_c2_vacuum.yaml` (F2a rev13) | `e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe` |
| `schemas/af_scc_c0_vacuum.yaml` (F2b rev13) | `b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c` |
| `artifacts/formulation/VOCAB_ALIASES.json` | `46cd9f1eb534df735daf221cfe6a877a54d7356d01229298f6efdcad8d50beba` |
| `artifacts/formulation/FROZEN.json` (rev29) | `815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0` |
| instrument: declared CF-21 checker | `4adcfcbe98842c20d5ccaf236377e3bae3caccbdd1024c66956bf88ac887789c` |
| rev12 reference report | `10a92ff3c9c1d4271a584b8fa6c79fe94ac505fcfe1db74189a256f76708f282` |

`report.json.pin_status` is 6/6 match; `drift_after_run` is empty.

## Result

**`baseline.verdict = FAIL`**, unchanged from the rev12 run, with the identical hard-rule set
(`hard_rule_set_identical: true`, `findings_identical_to_rev12_run: true`):

| rule | class | live evidence |
|---|---|---|
| **G2** (hard) | `AF-WCC-SCALAR-SPH` | `axes.genericity_kind: "unresolved"` (taxonomy line 393) while `conclusion.text` asserts a residual/comeager quantifier (line 414); no provisional/blocked marker |
| **G5** (hard) | `AF-WCC-SCALAR-SPH` | hypothesis `H4` (line 407) is `unresolved: true` and says the genericity notion "must be named before any claim is filed", yet the class carries a specific-quantifier conclusion and no machine-readable claim block |
| G1b (soft) | all four classes | F0 carries no per-class `genericity_topology` field (the three owned classes discharge it in their binding schemas) |

Per-class: `AF-WCC-VAC-GEN` PASS, `AF-SCC-C2-VAC-GEN` PASS, `AF-SCC-C0-VAC-GEN` PASS,
`AF-WCC-SCALAR-SPH` **FAIL** (G2+G5). Controls: **7/7 PASS** (C01–C07 as pre-registered). No input
drift during the run.

## What this does and does not say

- **Does say:** the rev13 evidence-binding repair (CF-20) is *invariant* for CF-21. The taxonomy
  bytes that carry the defect are byte-identical to the finding's original pin
  (`taxonomy_unchanged: true`), and although all three schemas moved rev12 → rev13, the declared
  checker returns exactly the same per-class verdicts and the same two hard failures. So CF-21 is
  **still live at the FROZEN rev29 gate-relevant bytes** and is not an artifact of the superseded
  rev12 pins.
- **Does not say:** anything mathematical about `AF-WCC-SCALAR-SPH`; and it is **not** a gate
  verdict. It is a declaration-level consistency measurement: the class's own machine-readable
  axis and hypothesis block contradict the quantifier in its own conclusion, and the D3 record
  "confirmed discharged for ALL FOUR classes" (taxonomy line 81) is unsupported for this class,
  which has no binding F-node schema.

## Falsifier

Void on any pinned byte change (re-measure), on a control deviation, or on a live repair: declare a
concrete/provisional `genericity_kind` with a binding schema — or an explicit provisional/blocked
marker on the conclusion — and clear or machine-readably block `H4`; the declared checker must then
return **baseline PASS with 7/7 controls**. A file rewrite alone is not a falsifier: the finding
binds the `sha256` values in `report.json.inputs` and must be re-run at any new bytes.

## Authority

Worker evidence only. No gate verdict, no node `status=done`, no `validation_status=passed`; no
frozen or canonical byte was written. `counts_as_full_schema_verdict: false` for the accompanying
review event.

## Re-run

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-094/cf21_rev13_recheck/run_cf21_rev13.py \
  --out artifacts/worker-094/cf21_rev13_recheck/run/report.json
python3 artifacts/worker-094/cf21_rev13_recheck/run_cf21_rev13.py --manifest-only
```

## Files

- `run_cf21_rev13.py` — re-check driver (imports the pinned declared checker; read-only on inputs)
- `run/report.json` — verdict, pins, findings, controls, rev12↔rev13 delta
- `run/manifest.json` — sha256 manifest of deliverables, instrument and pinned inputs
- `README.md` — this file
