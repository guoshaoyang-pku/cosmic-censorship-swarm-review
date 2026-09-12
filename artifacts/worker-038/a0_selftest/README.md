# W038-A0-SELFTEST-01 — the missing A0 self-test execution record

**Worker:** `worker-038` (bounded execution worker, one class-bound task)
**Node / gate:** `A0` / `G-AUDIT`
**Class scope:** the rubric's four frozen classes — `AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`,
`AF-SCC-C0-VAC-GEN`, `AF-WCC-SCALAR-SPH`
**Measured at:** 2026-09-12T00:23+08:00 (single window; every hash re-measured on disk)
**Result:** `RECORDED` — `selftest_verification.json` sha256 `63ea1452e7d57de5…`

## Why this task

`evaluation_rubric.yaml` declares `validation.validator: artifacts/audit/audit_run.py` and
states (line 46) that "a rubric with no passing self-test is not a gate", but
`validation.last_run` was `null` and no execution record existed. The independent static check
`artifacts/worker-008/a0_rubric_review/a0_check_report.json` recorded
`audit_run_attachment: null` and listed the never-run validator as a blocking finding. G-AUDIT's
unmet list also names "A0 has no recorded reviewer verdict". This directory is the execution
record for the declared validator — not a rubric content verdict.

## Method (null-first, per HANDOFF.md §3)

The workspace has ~100 concurrent agents rewriting `research_map.json` and `comms/outbox`
every few seconds, so a naive before/after cannot attribute mutation to this run. The record
measures a **30 s no-run control window**, then two validator runs:

```
S0 --30 s no run--> S1 --run A (relative --out)--> S2 --run B (absolute --out)--> S3
```

Outputs go only to worker-owned directories (`--quiet` suppresses outbox emission).

## Findings

| id | finding | status |
|---|---|---|
| S1 | `evaluation_rubric.yaml`, `audit_run.py`, `audit_lib.py` unmutated by both runs (0 changes in control and run windows) | pass |
| S1b | 30 s null control window: 0 pinned-file changes; run windows: 0 pinned-file changes; outbox churn present in **both** windows (7 and 8 new files from other agents) → ambient, not mine | info |
| S2a | **Defect:** `audit_run.py` crashes with `ValueError` at line 335 whenever `--out` is relative, after the full scan and before writing any report (`exit 1`, no report) | defect |
| S2b | With an absolute `--out` the validator completes: `exit 0`, report `run_b_absolute_out/audit-20260912T002342.json`, 109 violations (44 critical), `G-AUDIT: fail`, `G-LIT: fail`, `HF-02 ×62`, duplication cluster rate 0.4848, 12.7 s | pass |
| S3 | report binds the canonical rubric: `rubric_sha256 = d748a9e3574e…` = on-disk hash | pass |
| S4 | `--quiet` runs wrote no `worker-038` events; all outbox adds in both windows belong to other workers | pass |
| S5 | **No self-promotion:** `validation.last_run` and `last_run_result` are still `null` after the run | pass |
| S6 | rubric `frozen_classes` == taxonomy class ids == the four frozen classes | pass |
| S7 | **Defect:** rubric line 46 says validation is "Filled by `artifacts/audit/audit_run.py`", but no code path writes `evaluation_rubric.yaml`; the declared self-test can never populate its own record, so the line-46 rule cannot be discharged by invoking the declared validator | defect |
| S8 | `audit_run.py` evaluates the workspace against the rubric; it is not a rubric-field conformance test, so worker-008's static defects are outside it by construction | info |

S2a and S7 are reported in the outbox as a scoped `review` (`revise`) on
`A0/validator-artifact` at the validator's pinned hash. They are **not** a verdict on the A0
rubric content.

## Reproduction

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-038/a0_selftest/run_selftest.py     # rewrites selftest_verification.json
python3 artifacts/worker-038/a0_selftest/emit_events.py     # appends events + checkpoint
```

## Falsifiers

- Re-run `run B` at the same pinned hashes: a different `report_sha256`/`exit_code` falsifies
  reproducibility.
- Any post-run change to `evaluation_rubric.yaml` or the validator tooling falsifies S1.
- A non-null `validation.last_run` set by the run falsifies S5.
- If `report.rubric_sha256` differs from the canonical rubric hash, S3 fails.
- Patch line 335 and re-run `run A`: success then would falsify S2a as environment-specific.
- A future run window that mutates a pinned file the control window did not falsifies the
  ambient-attribution rule for that file.

## Authority

Worker evidence only. This record cannot set `status=done`, `validation_status=passed`, or any
gate verdict; A0/G-AUDIT remain with the controller and the audit lead. Numerics lock respected
(no N1 work, no `numerics/spherical_solver/`).
