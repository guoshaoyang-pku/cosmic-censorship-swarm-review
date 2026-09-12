# W028-F2A-REV29-VERDICT-01 — independent F2a review verdict at the FROZEN rev29 pin

- **worker**: worker-028 (bounded execution worker; no inbox card existed for this slot).
- **task**: one self-claimed class-bound task from the live immediate queue — the first full-schema
  review verdict at the rev29 F2a pin published by `astra-life05-evidence-binding-repair`.
- **node / class / gate**: `F2a`; `AF-SCC-C2-VAC-GEN` (scope: `AF-WCC-VAC-GEN`, `AF-SCC-C0-VAC-GEN`);
  `G-FORM`.
- **authority**: worker measurement only. No gate verdict, no node status, no
  `validation_status=passed`, no canonical artifact edited. `comms/outbox/worker-028.jsonl` carries
  the artifact / review / status events plus a post-review drift addendum.

## Verdict

**revise, score 3.5** at `schemas/af_scc_c2_vacuum.yaml` = `e9a27996dfd3` (revision 13).

| id | severity | item |
|---|---|---|
| HF-028R-01 | blocking | extension category unpinned: clause (a) embedding regularity, clause (c) / `topology.extension_topology` manifold category, and no `iota_regularity` field anywhere, while the C0 sibling pins SMOOTH manifold + C-infinity iota at lines 91/118/190 for an accepted reason (worker-16 F2b-16-03) |
| F-028R-01 | minor | the 495-byte evidence form drops the input-digest fields of the 728-byte `675a99d0` form; non-blocking given byte-reproducibility, writer guard recommended (worker-022/w074) |
| F-028R-02 | minor | `revision_history` index 9 carries an earlier timestamp than index 8 |
| PC-028-01 | resolved | rev12 evidence-hash defect: declared == measured == `9e335e9b`; FROZEN rev29 pins it |
| PC-028-02 | positive | evidence reproduces byte-for-byte in a sandbox from the frozen F0 pair, and the checker is mutation-sensitive |

## Measured (all machine-checked, controls in `report.json`)

- artifact pins stable across the review window; rev12→rev13 delta is 7 lines, all binding/revision
  metadata, zero class-semantics changes; predecessor `5476a3f2c6bc` verified.
- `f0_binding` chain resolves: F0 `0abb9ed8a961`, evidence `9e335e9ba1bf`, both pointers resolve,
  FROZEN revision 29 pins the reviewed bytes.
- canonical structural gate `check_class_schema.py --json`: exit 0, `failed_rules: []`.
- class separation module: 0 findings; frozen regression instrument: 17/17 leaks, 10/10 controls,
  FP 0 FN 0, PASS.
- evidence sandbox: baseline exit 0 `CONSISTENT (4 classes, 0 contract-text divergences)` and
  reproduces `9e335e9b`; M1–M3 semantic mutations flip it INCONSISTENT; coverage control proves the
  evidence never reads the class schemas (declared scope is taxonomy-vs-contract).

## Files

| path | role |
|---|---|
| `run_review_f2a_rev29_028.py` | the instrument (re-runnable; writes only under this directory) |
| `review_f2a_rev29_028.json` | the review verdict artifact (+ `.sha256`) |
| `report.json` | full machine report: pins, controls, gate/classsep runs (+ `.sha256`) |
| `checkpoint_028.json` | worker checkpoint (+ `.sha256`) |
| `post_review_drift_028.json` | post-window FROZEN regeneration observation (+ `.sha256`) |
| `snapshots/` | read-only copies of every measured input, named `<stem>.<sha12><ext>` |
| `sandbox/` | isolated copies used for the evidence-adequacy controls |

## Falsifier

See `falsifier` in `review_f2a_rev29_028.json`; in short: a different F2a hash, a non-allowlisted
rev13 delta, a failing F0 binding, an extension-category pin at rev13, a sandbox baseline that does
not reproduce `9e335e9b`, a non-zero structural gate, or any reviewed artifact pin drifting.
