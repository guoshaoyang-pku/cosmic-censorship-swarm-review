# Worker 12 (deepseek-flash-12) checkpoints — N0 assigned task

Scope: Node N0 / class AF-WCC-SCALAR-SPH, flat-space scalar-wave calibration ONLY.
numerics_lock is LOCKED: no self-gravitating solver, no N1 work, no `numerics/spherical_solver/`.
Assignment: `comms/inbox/deepseek-flash-12.jsonl` event `asg-2026-09-11-N0-deepseek-flash-12-21`
(deadline 2026-09-12T03:15+08:00, gate G-NUM, acceptance: closed-form, 3+ resolutions,
measured order, assert order >= declared - tol, exit code reflects pass/fail).
Completion policy: no node completion claimed by this worker.

## CP0 — recon and proposal (23:15–23:19)
- No assignment in `comms/inbox` at start; immediate queue inspected (`F1, F2, L0/L1, A1, N0, A2`).
- Proposed unassigned F2 draft (see CP1); emitted `status` event `flash-12-status-0001`.

## CP1 — F2 SCC pair draft (23:20–23:22)
- `artifacts/flash-12/f2_scc_split/af_scc_c2_c0.draft.yaml` (sha256 `aca223a6…`):
  two strictly separated SCC documents, C^2 vs C^0 extension regularity, distinct conclusions,
  one-way C0 => C2 implication, quantified-but-unresolved genericity, visibility excluded from
  SCC conclusions, no memory citations.
- `check_f2_separation.py`: 10/10 checks, 8/8 injected mutations caught.
- `audit_regex_probe.py`: reproduces that `audit_evidence.py`'s C0/C2 merge regex false-positives
  on the map label "AF-SCC C2/C0 split"; narrowed conclusion-field rule keeps the true positive.
- Handed off; superseded as an execution path by the N0 assignment. No completion claimed.

## CP2 — N0 assignment; ownership conflict; independent verification (23:22–23:30)
- Assignment received at 23:19:12; on arrival `numerics/tests/flat_wave.py` was already occupied by
  an actively maintained unassigned candidate by `deepseek-flash-20` (assigned A2); the file changed
  3x in 5 minutes. Worker 12 did NOT overwrite it.
- Snapshot preserved: `artifacts/flash-12/n0/flat_wave_candidate_worker20.snapshot.py`
  (sha256 `7fb76088…`, the version that failed its own G1/G4).
- Root cause of that early failure (independently identified): the standing test at `t_end=0.5` sits
  at a turning point where the leading O(h^2) phase error cancels, so the measured order is a fragile
  O(h^4) accident; the gate band [1.8, 2.2] then rejects it. The live candidate now uses `t_end=0.37`
  and adds a temporal-subdominance control; its own 10 gates pass.
- Worker-12 independent adversarial verification, pinned sha `743c73e4e68e3a52…`:
  `artifacts/flash-12/n0/verification_report.json` (sha256 `5b19a34491c48702e1e8a3de97bb580700aa45233ed0c83385566d48f3738ac9`), 9/9 checks PASS,
  `applies_to_canonical: true`:
  V1 order 2.004/2.002 at t=0.29, n=96/192/384 (independent closed form and norms);
  V1b order 2.004/2.003 at t=0.23 with ratio 1.5 (n=100/150/225);
  V2 temporal subdominance (relative change 0.0);
  V3 wrong-operator control collapses order to ~0; V4 wrong-reference control collapses order to ~0;
  V5 black-box `--all` exits 0 twice with numerically identical reports;
  V6 scope guards; V7 pin stability; V8 energy drift at roundoff (1.6e-14 finest).
- CLI stdout + sha256: `artifacts/flash-12/n0/cli_stdout.txt`.
- Emitted: N0 status, artifact, review (accept, score 4/5, scoped), blocker (canonical-ownership).

## CP3 — next (planned, until 03:15 deadline)
- Watch `comms/inbox/deepseek-flash-12.jsonl` and the bus for lead-numerics/Astra decisions:
  frozen canonical sha, author of record, binding confirmation against the now-present F0 taxonomy.
- If the canonical sha changes, re-run `verify_flat_wave.py` and re-pin; a stale verdict is not a pass.
- Do not touch worker-13's `flat_wave_replication.py` (independent method is the point) or N1.
- Report any further falsification (third time point, different scheme) as a status event.

Next falsifier (unchanged): an edit to `numerics/tests/flat_wave.py` invalidates this sha-pinned
verdict; a measured order < 1.8 at a fresh time point/refinement ratio falsifies the 2nd-order claim.

## CP3 — replication adjudication recheck (23:26–23:33)
- Controller adjudication 23:28 flagged `cnfem` (order -0.0773, drift 1.0e+01) as a replication failure.
- Worker-13 revised `numerics/tests/flat_wave_replication.py`; worker-12 independently re-ran it at pinned
  revision `8ade1cdc163ea420790b9fdfdab41157b4f3d4219d6a0bcf827baafe69a6f422`: **ORDER REPRODUCED** (lffd 1.9958,
  cnfd 1.9935, cnfem 1.9863; selftest pass). The cnfem defect is fixed at this revision.
- Independent cross-resolution probe (`replication_finding_probe.py`, sha `ca039f1c4de347c4191729dac5d75ba09125f67dafc6fffd29037ef9c3480bc0`):
  non-leapfrog harness-functional drift fails drift_tol=1e-6 at dr=0.2 (cnfd 1.37e-5, cnfem 1.84e-6),
  passes at dr=0.05 (6.6e-8, 8.5e-9) while own invariants stay ~1e-14. The scheme-specific functional
  limitation is real but resolution-dependent; worker-13's revised `invariant_gate_calibration` block
  states exactly this and is corroborated.
- Emitted: status `flash-12-n0-status-0004`, artifact `flash-12-n0-artifact-0003`,
  review `flash-12-n0-review-0002` (accept, pinned sha).
- Evidence refs now use the controller's required `path#sha256-prefix` form.

## CP4 — planned
- Lead response check; order-4 independent probe; lock-guard re-run; F2a/F2b published-schema separation lint.
- Any canonical sha change invalidates pinned verdicts; re-run `verify_flat_wave.py`.

## CP4 — external gate, order-4, lock guard, F2 schema lint (23:29–23:35)
- Canonical `numerics/tests/flat_wave.py` unchanged at sha `743c73e4e68e3a52f41c060c7e946dae99bdfbe6b9e879bba6a77ebfa4f6c784`; pinned verification still valid.
- Extended `verify_flat_wave.py` with an independent 4th-order probe: order 3.918 / 3.900 at t=0.29, n=64/96/144
  (ratio 1.5). Full report now 10/10 checks PASS (`artifacts/flash-12/n0/verification_report.json` sha `9678482979de3bb62c8268b4d0cce9a4ffe0ff162837d5ef77b9fb5a0d5f4e23`).
- Re-ran worker-04's **external** acceptance harness through `flat_wave_protocol.py` on the pinned candidate:
  verdict **PASS** (order 2.0004 vs 2.0±0.3, invariant drift 3.2e-9 < 1e-6, stability PASS at cfl 0.25/0.5/0.8,
  no failed/inconclusive gates); report `artifacts/flash-12/n0/external_harness_recheck.json` sha `925f801ef42fde6222e646deda189c1412bd02de4d3a74033ec7dd40dc2b0f19`.
- Reproduced worker-13's replication at sha `8ade1cdc163ea420790b9fdfdab41157b4f3d4219d6a0bcf827baafe69a6f422`: ORDER REPRODUCED (lffd 1.9958, cnfd 1.9935, cnfem 1.9863).
- Lock guard (G-NUM criterion) re-run: PASS, no violations, `numerics/spherical_solver` absent (`artifacts/flash-12/n0/lock_guard_run.json`).
- Read-only separation lint of the published SCC schemas (`artifacts/flash-12/f2_scc_split/published_schema_lint.json` sha `d721e42497bbcbc7f5e73476605de4b4b232c206f2578a89c4b631e8c2127add`): PASS.
  Design note: a first version false-positived on `conclusion.forbidden_strengthenings[3]` ("I+ completeness ... (WCC content)"); forbidden blocks must be excluded from lexical leakage scans.
- No N0 completion claim. Remaining G-NUM criteria: protocol review by audit (worker-14) and lead adjudication.

## CP5 — lead revision lnum-rev-20260911T2333-N0-12 (23:35–23:40)
- Added `lock_guard(root=None)` (delegates to `numerics.gates.evaluate`, fails closed on import/map errors),
  CLI `--lock-guard`, gate `G11_n1_lock_guard`, and real provenance assignment id; updated stale
  binding_status (F0 taxonomy now exists) and the header status.
- Revised canonical sha `8b52014dac47f99663c8bf46fb2e65a80db399860d586d63cd73dd1db1454a6c` (was 743c73e4). `--all` exits 0 with **11/11** gates
  (G11 present); `--lock-guard` exits 0 with verdict `N1_BLOCKED`, `guard_correct_for_state: true`,
  6 blocking reasons. Fail-closed paths tested directly: nonexistent root -> FileNotFoundError -> blocked;
  malformed map -> JSONDecodeError -> blocked (see transcript in this checkpoint).
- Re-verified the revised sha: adversarial report `artifacts/flash-12/n0/verification_report.json` 10/10 PASS; external harness PASS
  (order 2.0004, drift 3.2e-9, stability PASS) at `artifacts/flash-12/n0/external_harness_recheck_rev1.json`.
- Note for G-NUM: worker-13's replication pins 743c73e4; the revision changed only lock-guard/provenance
  plumbing, but the gate's sha matching now needs a fresh artifact event / re-run against `8b52014dac47f996`.

## CP6 — protocol-vs-artifact compliance deltas (23:44)
Lead accepted revision 8b52014d (review `lnum-review-e04acbdb815a57c5cfef`). Reading
`numerics/CONVERGENCE_PROTOCOL.md` against the accepted artifact surfaces four deltas for the
G-NUM protocol review (lead-numerics / lead-audit), none of which contradicts a measured value:
- §3.4 spatial order must be measured at fixed small dt (1e-4); artifact uses dt = cfl*h (0.25 / 0.1)
  plus G9 temporal-subdominance control (<2% change when cfl is cut). Measured orders comply.
- §3.5 manufactured data must contain >= 2 modes; the order-2 standing study still uses one mode
  `modes=((2,1.0),)` and avoids the eigenfunction trap by evaluating at t=0.37. The pulse study is broadband.
- §3.6 acceptance band |p-p_design| <= 0.3 for canonical studies; the artifact's order-4 band is [3.6,4.4] = +-0.4
  (measured 3.900/3.918 comply with +-0.3 anyway).
- §7 report schema requires `fitted_order` per study; the artifact reports pairwise `order_l2` only
  (and §3.3 says order claims use the least-squares fit).
Resolution is a protocol waiver note or a second artifact revision; worker 12 makes no edit without a lead request.

## CP7 — protocol-delta closure probe, independent lifecycle (2026-09-12 00:06–00:08)
Took one class-bound task (`AF-WCC-SCALAR-SPH` / N0 / G-NUM) from the C2+C5 deltas filed in CP6,
without editing the frozen artifact (hash pin `8b52014dac47f996` stays valid).
- Fresh headless run at the pin: `python3 numerics/tests/flat_wave.py --all` exit 0, **11/11 gates**;
  `--lock-guard` exit 0, verdict `N1_BLOCKED`, map lock `locked`, guard correct; no
  `numerics/spherical_solver/`. Evidence: `artifacts/flash-12/n0/rev2/all_report.json`,
  `all_stdout.txt`, `lock_guard_stdout.json`.
- New probe `artifacts/flash-12/n0/protocol_fit_check.py` recomputes the missing least-squares
  `fitted_order` from the pinned report's own rows and tests the canonical ±0.3 band:
  standing o2 fit 2.00266 (l2) / 2.00010 (linf); pulse o2 1.99789 / 2.00159;
  standing o4 4.13399 / 4.22894 — **all inside ±0.3**. Stored pairwise orders recompute clean
  (≤1e-9); refinement ratio 2 everywhere. Replication fits agree with the canonical order-2 fit
  mean within 0.014 (protocol tol 0.35). Verdict: `deltas_documentation_only`.
- C5 caveat kept explicit: the strict *pairwise* canonical band fails at the coarsest order-4 pair
  (4.3119, deviation 0.3119 > 0.3), which is why the implemented gate band was ±0.4; the fit
  statistic that §3.3 says order claims use passes. Lead decision item, not a numerical defect.
- Event `flash-12-n0-artifact-0008` (artifact `5a60417a0bdebe3d`) reported to
  `comms/outbox/deepseek-flash-12.jsonl`; ingested. The probe's own `next_falsifier` fired within
  minutes: `numerics/CONVERGENCE_PROTOCOL.md` was edited (rev 2, §4.1 R1–R4) after submission, so
  `flash-12-n0-artifact-0009` (`00af9be8877e021f`, `rev2b/`) re-ran the probe at the stable pin
  `3345e17d2be3e403` and confirmed §3.3/§3.6/§7 semantics unchanged, verdict unchanged.
- Checkpoints: `ckpt-20260912-000706` label `worker12-n0-fitclosure` and the final snapshot
  `worker12-n0-fitclosure-final` via `python3 research_map/checkpoint.py`. No map status, no gate
  verdict and no node completion claimed; G-NUM adjudication stays with lead-numerics/lead-audit.

## CP7 — rev2 patch prepared, NOT applied (00:15)
Under controller P1/P3 freeze the canonical sha stays 8b52014dac47f996. Prepared and tested, in the
worker-12 namespace only, the one revision that would close blocking delta D4 (`fitted_order`):
`artifacts/flash-12/n0/rev2_fitted_order.patch` (sha 94331e4e6bf10f21).
It adds per-study `fitted_order` (least-squares log-log slope over all resolutions), `orders`/`gates`
keys per protocol sec7, and makes the order gate require |fitted - p_design| <= 0.3 (sec3.6) while the
pairwise band stays an internal control. Tested on a temp copy under numerics/tests/: `--all` exit 0,
11/11 gates, fitted orders 2.0027 / 1.9979 / 4.1340; `--lock-guard` exit 0 N1_BLOCKED. Temp copy deleted;
canonical untouched. Apply only on explicit lead request.
