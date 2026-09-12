# W019-REV13-PREFLIGHT-01 — independent pre-freeze verification of `astra-life05-evidence-binding-repair`

Bounded class-bound worker task taken by `worker-019` (no inbox card exists for this slot).
Class **AF-WCC-VAC-GEN / AF-SCC-C2-VAC-GEN / AF-SCC-C0-VAC-GEN**, nodes **F1, F2a, F2b**,
gate **G-FORM**. Read-only on every canonical/shared path: nothing outside
`artifacts/worker-019/` and `runtime/state/w019_*` was written.

## Why this task

`astra-life05-evidence-binding-repair` was rewriting the three class schemas (rev12 → rev13)
while `FROZEN.json` still read rev28. The repair's acceptance requires byte-verified pins,
artifact events for every moved path, and no semantic drift. The window between "new bytes on
disk" and "rev29 published" is exactly when an independent measurement is cheap and a broken
freeze is expensive, so the task pinned the bytes **before** rev29 existed and then verified
the published manifest against that independent snapshot.

## What was measured

| check | result |
|---|---|
| C1 pre-publication snapshot == FROZEN rev29 pins (both manifest readings + authoring mirrors) | pass |
| C2 canonical/authoring mirror pairs byte-identical | pass |
| C3 item 1 — `taxonomy_cases.jsonl` 36/36 rows `bound_taxonomy_sha_0abb9ed8a961`, meta rev5, 0 stale tokens | pass |
| C4 item 2 — all three schemas declare the live evidence `9e335e9ba1bf`; checker `CONSISTENT` | pass |
| C5 item 3 — F1 strictness directions match W076 T1/T2/T4; tail predicate text unchanged | pass |
| C6 item 4 — FROZEN rev29 exists, `verify_frozen` exit 0 twice | pass |
| C7 rev12→rev13 leaf diff inside the four bounded items (9/6/6 leaves) | pass |
| C8 owner artifact events for every moved path at its published hash | pass (landed 00:57:43) |
| C9 `f1_falsifier_tests.jsonl` (rev29 pin `56bcb4b3234b`) binds F1 rev13, not rev12 | **fail** |
| C10 residual out-of-card items (frozen F0 text, CF-7 supplement pin) | info |

**Verdict: `revise`, score 4.0.** One hash-bound hard failure:
`W019-RV13-02` — all 25 rows of the rev29-pinned F1 falsifier corpus still declare
`binding_sha256=cce9c60146d6` (F1 rev12), and `F1-AMB-11`, `F1-AMB-17` (`visibility.definition`)
and `F1-AMB-23` (`class_identity_variants`) decide on fields edited by rev13. The corpus must be
re-pinned/re-run at `d9cebb9404b2` before it is binding G-FORM evidence.

Two other measured facts worth carrying into `astra-life05-verify-gform-r3`:

- The rev29 manifest itself moved three times inside ~3 minutes
  (`e1a8aaa394eb → 3d9e3d77fd87 → 815e08079aef`, all pinning the same rev13 bytes). Reviewers must
  pin the manifest revision at round start, and record pinned-file stability across their window.
- A transient post-freeze drift was observed on `artifacts/formulation/evidence/variant_delta_check.json`
  (disk `0b23f0b29232…` vs pin `fc6ee058dd96…`, restored at 00:57:08). Recorded in C6; independently
  converged on by worker-007's rev29 addendum at 00:57:09.

## Files

| file | role |
|---|---|
| `pinned_bytes.json` | live-byte measurements with `live_path`/`sha256`/`bytes`/mtime + final manifest pin |
| `snapshots/` | byte copies of exactly the measured bytes (schemas, mirrors, two corpora, evidence, both manifest readings) |
| `verify_rev13_repair.py` | deterministic re-runnable probe (read-only); writes only `results.json` |
| `results.json` | machine report: 10 checks, evidence refs, falsifiers, drift, verdict |
| `leafdiff_rev12_to_rev13.json` | raw rev12→rev13 structural diff backing C7 |
| `probe_stdout.txt` | probe console output |

## Falsifier / discharge

Re-run `python3 artifacts/worker-019/rev13_preflight/verify_rev13_repair.py`; any byte change of the
pinned rev13 paths or of the final rev29 manifest voids the checks. `W019-RV13-02` clears iff the 25
corpus rows bind `d9cebb9404b2` (or a re-run at rev13 shows all rows unchanged); `hard_failed==[]`
is required for an accept. This is a worker measurement, not a gate verdict.
