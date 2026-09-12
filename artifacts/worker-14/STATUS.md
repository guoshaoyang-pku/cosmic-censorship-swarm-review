# worker-14 status (deepseek-flash-14)

Run: cosmic-censorship swarm, session 2026-09-11T23:15+08:00.
Authority: execution worker, DeepSeek Flash breadth tier. No node completion,
no gate verdict, no map mutation claimed anywhere in this directory.

## Assignments received (comms/inbox/deepseek-flash-14.jsonl)

| event | node | artifact (canonical) | status |
|---|---|---|---|
| `asg-2026-09-11-N0-deepseek-flash-14-23` | N0 / G-NUM | `numerics/protocol/convergence_protocol.md` | draft delivered, unverified |
| `astra-adj2-03-assignment` | N0 / G-NUM | `numerics/protocol/scheme_independence_review.md` | draft delivered, unverified |

## Deliverables

`numerics/protocol/`:

- `convergence_protocol.md` — V1–V6 validity conditions, T1–T7 tests, FC0–FC9
  failure criteria, resolution ladder, report schema `n0-convergence-report/v1`,
  worked synthetic example E1–E6, in-situ finding on `G1_standing_order2`.
- `convergence_demo.py`, `demo_output.json`, `demo_report_standard.json`,
  `demo_report_wrong_order.json` — worked example; audit PASS/exit 0 for the
  order-2 scheme, FAIL/exit 1 for the stable wrong-order control.
- `audit_convergence_report.py` — reference enforcement of C0–C9, functional
  aware (R1–R4), plus `--compare` for cross-scheme order agreement.
- `scheme_independence_review.md`, `scheme_independence_check.py`,
  `scheme_independence_evidence.json` — review `astra-adj2-03`.

Outbox: `comms/outbox/deepseek-flash-14.jsonl` (8 schema-valid events:
status, claim, 2 artifacts, review, 2 blockers, resource_request).

## Headline findings (all reproducible, none a completion claim)

1. `G1_standing_order2: false` in the candidate results is a turning-point
   degeneracy: order 4.00 at t=0.5 vs 2.00 at t=0.4 for the same single-mode
   scheme. A two-mode family reads 2.00 at t=0.5. Root cause: leading phase
   error ∝ sin(k t) vanishes at the mode turning point.
2. The pinned n0 replication "cnfd own energy" is algebraically the leapfrog
   staggered energy (identity gap 2.07e-15); the 6.6e-8 vs 3.4e-15 gap is a
   functional mismatch, not solver quality. Current code's CN invariant drifts
   1.11e-14. Cross-functional mismatch converges at ~4th order.
3. The candidate's G3 `1e-8` drift gate flips to PASS for cnfd at dr=0.025
   (4.170e-09) and is unreachable with its own `np.gradient` diagnostic
   (finest drift 9.41e-06 at n=1024).
4. The adjudication's own falsifier is triggered at the harness threshold:
   cnfd records `harness_gate_would_pass = true` at `drift_tol = 1e-6`.
5. `numerics/gates.py:evaluate()` crashes at line 149 on
   `artifacts/numerics/n0/lead_calibration_report.json` (`studies` is a dict);
   G-NUM is not evaluable while that file is present. Reported as a blocker;
   no edit made.
6. End-to-end G-NUM workflow added (`build_gate_reports.py`): conformant
   reports for the two real replication schemes both audit PASS C0–C9 with
   their own structural invariants (lffd 1.9977, δ=4.2e-05, drift 3.19e-15;
   cnfd 1.9948, δ=1.2e-03, drift 1.22e-14) and agree at |Δp| = 0.00286.
   The same cnfd pair fails the candidate's fixed `1e-8` threshold, which is
   the concrete demonstration of R1–R4.
7. Peer context recorded, not re-adjudicated: flash-12 recheck reports cnfem
   fixed at revision `8ade1cdc…` (order 1.9863, selftest pass), superseding
   the pinned adjudication's cnfem reading.

## Open falsifiers

- Protocol: a stable declared-order-2 scheme that passes C0–C9 at every
  V2-valid time while its truncation-residual order is below 2.
- Review F2: cnfd leapfrog-functional drift at dr=0.025 above 1e-8.
- Review F4: the pinned run reproducible from `script_sha256 = 07e5a39b…`.

## Checkpoint additions (CP6, 23:40)

- **Protocol bug found and fixed:** C7 required every drift pair to converge,
  which fails on roundoff noise; added the `1e-12` roundoff floor
  (`audit_convergence_report.py`). Re-ran all audits: demo standard PASS, demo
  wrong-order FAIL, replication pair PASS + agree.
- **Candidate re-pin:** the candidate regenerated its results during the
  checkpoint. Pinned snapshot
  `artifacts/worker-14/candidate_results_snapshot_e9e124227c4d2932.json`
  (generated 23:36:43, generator `8b52014d…` matches on-disk); all candidate
  gates now true (G1/G3/G9 resolved; standing `t_end = 0.37`, drift order ≈ 5).
- **Self-correction:** the review had paired the new results hash with
  pre-revision numbers. Review §4 and protocol §9 now carry explicit revision
  notes; the pinned snapshot is the reference.
- **Protocol applied to candidate results:** pulse study PASS C0–C9; single-mode
  standing study fails C2 only (V2 supporting-evidence rule) — the protocol
  rejects the configuration, not the scheme.

## Checkpoints

See `checkpoints.jsonl` (appended by the inbox watcher and manual checkpoints).
`verify_checkpoint.py` compares current hashes against the CP4 record, the
replication/candidate/gates hashes, and the gate evaluation; `gate_report_cp5.json`
is the raw gate report at checkpoint 5.

## Next-round checklist (for a cold or resumed session)

1. Read `comms/inbox/deepseek-flash-14.jsonl` for new or revised assignments;
   do not act on stale ones.
2. If `numerics/tests/flat_wave_replication.py` changed from `8ade1cdc…`,
   re-run `scheme_independence_check.py` and `build_gate_reports.py`; the
   review's numbers are pinned to that hash.
3. Do not edit other workers' artifacts. Deliver new work under
   `numerics/protocol/` and emit schema-valid events to
   `comms/outbox/deepseek-flash-14.jsonl`.
4. Never set node status/validation or a gate verdict; worker events are
   proposals only.
