# W095-F2B-STREAM-BINDING-R6-VERIFY-01

Worker-095 bounded, class-bound, READ-ONLY probe. Node **F2b**, class
**AF-SCC-C0-VAC-GEN**, gate **G-FORM**. It does not set a node status, a
`validation_status`, or a gate verdict.

## Question

r4 (`artifacts/worker-095/freeze_hold_binding_integrity_r4/`) left one condition open:
is the accepted event stream, the stream that resolves "latest artifact per path" and
feeds `research_map.json`, able to bind bytes other than the FROZEN rev29 pin for the
held F2b artifact - and are the offending events already applied to the sole global
state?

## Answer (pinned at 2026-09-12T01:16:39+08:00, FROZEN rev29 `815e08079aef`)

Verdict **revise** (worker level).

- **R1 PASS.** 6/6 pinned paths match the manifest; 115 events in the
  pinned stream snapshot claim `created_at` after the probe instant, and
  97 of them are applied; 17 are
  materialized in map content (claims/reviews).
- **R2 FAIL.** `schemas/af_scc_c0_vacuum.yaml` resolves to the pin under file order
  (`lead-form-20260912T005743-02`, line 4832),
  `_received_at` max, and the fail-closed rule, but **created_at-max resolves to
  `e6b1af2bd692`** from `w06-20260912T0115-f2b-rev6` (line 712, no `_received_at`,
  outbox write time 00:42:23 vs claimed created_at 01:15:00, supersedes
  `cb897b29db12`). The F2b mirror resolves to the pin under all rules.
- **R4.** The deepseek-flash-06 block is 15/15 events at stream
  lines 712-762, entirely inside the
  790-line unstamped prefix (first `_received_at`
  line 791); written to
  `comms/outbox/worker-06.jsonl` at 2026-09-12T00:42:23+08:00 with claimed created_at up to
  2026-09-12T02:00:00+08:00 (max lead 4657 s); all 15 applied,
  2 materialized as claims.
- **R6 PASS**: synthetic benign stream not flagged; synthetic pre-dated shadow flagged;
  double-run identical. **R7 PASS**: no canonical pin moved in the window.

Hard failures: HF-R6-01, HF-R6-02, HF-R6-03.

## Files

- `run_probe_r6.py` - deterministic, read-only probe (writes only under this directory).
- `assemble_verdict_r6.py` - builds `verdict.json`, this README and `MANIFEST.json`.
- `evidence/raw/*.json` - raw measurements with their own sha256 in `MANIFEST.json`.
- `verdict.json` - worker-level verdict and falsifier.

## Falsifier

Withdrawn if, under a read path declared in the repo: (a) every held path and the F2b mirror resolve to the FROZEN rev29 pin, with events lacking _received_at and events whose created_at is future-dated unable to confer precedence; (b) no event whose created_at post-dates the probe instant is applied to research_map.json or materialized in its claims/reviews while contending a frozen pin; (c) the deepseek-flash-06 block is either re-timestamped to its write time or excluded from pin resolution; (d) a re-probe from a second instance at the same pinned inputs reproduces these counts. Any canonical byte move voids this window, not the finding.

Any canonical byte move voids this window, not the finding. Worker measurement cannot
promote a gate or mark a node done.
