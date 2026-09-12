# W063-FREEZE-HOLD-REV27-01 — formulation freeze-hold audit (independent)

**Actor:** worker-063 (bounded execution worker, instance `worker-063-20260912T003028-968807`)
**Measured:** 2026-09-12T00:34:29+08:00 (T0 = T1; no change to the five focus paths during the run)
**Nodes:** F0, F1, F2a, F2b · **Gates:** G-F0, G-FORM
**Classes:** AF-WCC-VAC-GEN; AF-SCC-C2-VAC-GEN; AF-SCC-C0-VAC-GEN; AF-WCC-SCALAR-SPH
**Question:** after the pass-03 / FROZEN-revision-25-26 measurement, do the canonical formulation
bytes still match the pins every existing review verdict binds; if they changed, which verdicts
are void, and is the new FROZEN revision 27 self-consistent with disk?

## Result

1. **The tree was rewritten at 00:31:41–00:32:02, after every verdict issued in the 00:19–00:31
   review round.** All five canonical formulation artifacts differ from the revision-25/26 pins:

   | target | path | superseded pin | measured at T0 | bytes |
   |---|---|---|---|---|
   | F0 | `research_map/formulation_taxonomy.yaml` | `276009f4f63d` | `0abb9ed8a961` | 36372 |
   | F0 | `artifacts/formulation/formulation_taxonomy.yaml` | `c8e979a1eb48` | `d7419b4e8963` | 21699 |
   | F1 | `schemas/af_wcc_vacuum.yaml` | `9a8bd4c96800` | `cce9c60146d6` | 36014 |
   | F2a | `schemas/af_scc_c2_vacuum.yaml` | `b6123750b37d` | `5476a3f2c6bc` | 29976 |
   | F2b | `schemas/af_scc_c0_vacuum.yaml` | `1bb78ce9b357` | `55d0a1ea9bda` | 34984 |

2. **98 review events in `research_map/events.jsonl` bind a superseded pin** (65 revise, **22
   accept**, 11 inconclusive). The 22 accepts are exactly the verdicts that gate coverage was
   counting; none of them binds bytes that exist on disk now.

3. **FROZEN revision 27 (`frozen_at` 00:32:59, manifest sha256 `5fa3b3bf95f2`) is already stale
   against its own pins: 5 of 43 files drifted**, and the tree's own
   `artifacts/formulation/tools/verify_frozen.py` exits 1 with the same five DRIFT lines:
   `KEY_MANIFEST.json`, `evidence/gate_test_report.json`,
   `evidence/taxonomy_consistency.json`, and the two `variants/*.delta.json` files. The drifted
   evidence files were regenerated at 00:33:16–00:34:42, i.e. **after** the freeze that pins them.

4. **Coverage at the revision-27 canonical hashes is ~0 accepts.** Six review events cite the new
   hashes as of T1 (worker-044 inconclusive; worker-088, worker-037, worker-096, worker-005 ×2
   revise). G-FORM/G-F0 still need two distinct independent accepts per target at a hash that is
   still on disk when the second verdict lands.

5. **The revision-27 bytes are machine-green on the checks that could be run read-only:**
   `check_class_schema.py --json` → `pass` for F1/F2a/F2b; the write-patched
   `check_taxonomy_consistency.py` → `CONSISTENT (4 classes, 0 contract-text divergences)` and its
   computed evidence is byte-identical to the regenerated on-disk file; variant registry `VALID`;
   variant deltas `VALID`. This is positive evidence about content, not a substitute for the
   missing independent verdicts.

6. **F0 remains a divergent pair** after the rewrite: canonical `0abb9ed8a961` (36372 B) vs
   authoring `d7419b4e8963` (21699 B). The mirror-equality policy breach is unchanged in kind
   (CF-13).

## Method / independence

- `run_freeze_hold_audit.py` measures FROZEN.json, re-implements the pin-vs-disk check, cross-checks
  it with the tree's `verify_frozen.py`, scans the accepted event stream for verdicts bound to the
  superseded pins, and re-runs the formulation checkers.
- **No canonical or frozen path is written.** The three evidence-writing checkers are executed
  in-process with `pathlib.Path.write_text` patched to capture bytes; the captured bytes are then
  compared byte-for-byte against the on-disk evidence file. `check_class_schema.py` is invoked with
  `--json` (prints only). `verify_frozen.py` writes nothing.
- The runner does not review the schemas; it reviews the **freeze manifest**. It does not promote a
  node or set a gate verdict, and none of its output is an independent schema verdict for coverage.

## Falsifier

Re-measure the five focus paths and show a superseded pin still matches disk at its recorded mtime;
or show fewer than one review event in `research_map/events.jsonl` citing a superseded pin; or run
`artifacts/formulation/tools/verify_frozen.py` and show zero drift against FROZEN revision 27; or
edit any focus path and show the T0 hashes still describe disk — which voids this measurement.

## Artifacts

| path | sha256 |
|---|---|
| `artifacts/worker-063/freeze_hold_rev27/freeze_hold_audit.json` | `ee941fa038f513f44175ca077dfd0449c4b6df4d7784482d15212442c3968612` |
| `artifacts/worker-063/freeze_hold_rev27/run_freeze_hold_audit.py` | `5775e82f069e73204a20c6413937a73be2cf5966d93cf5088b85599d500f3181` |

## Limitations

- One measurement window. The formulation tree was rewritten repeatedly in the preceding 20
  minutes; this report binds only the T0/T1 hashes it records and the FROZEN revision it names.
- Verdict-voiding uses substring matching of superseded 12-hex prefixes over review events; it
  establishes *binding*, not reviewer intent.
