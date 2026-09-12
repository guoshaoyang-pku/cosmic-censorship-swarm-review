# Astra checkpoint report 2 — 2026-09-11T23:45+08:00

Run `run-2026-09-11T23:15+08:00`, ~30 min elapsed. Machine state:
`runtime/state/current_checkpoint.json`; loop on `auto-2` (23:35), next at 23:50.
Events applied: 600+; reviews: 61; claims: 22 (all unpromoted except one controller
adjudication); audit hard failures: 0; class-separation regression: PASS.

## 1. Gate board

| gate | verdict | movement this window |
|---|---|---|
| G-F0 | pending | revision 6 declared frozen by lead; canonical publication pending (see §3) |
| G-FORM | pending | F2a: two independent accepts (18: 5.0, lead-audit: 4.0); F2b: accept 4.0 + revise 2.0; F1: revise 3.5 on the previous revision; re-review waits on publication |
| G-LIT | pending | 4 independent re-fetch accepts (flash-10, 5.0 each); 32 unassessed rows across 8 sources; worker web_search tool broken, direct HTTPS works |
| G-NUM | pending — **one item left** | replication defect fixed and independently re-run by the controller: cnfem −0.0773 → 1.9863, verdict ORDER REPRODUCED, three schemes agree; only the protocol review remains |
| G-AUDIT | pending | rubric in place; checker-calibration task open; G-CLASSBIND proposals folded in as evidence, not adopted as a gate |

## 2. Verified progress (controller-executed, not reported)

1. **N0 replication repaired.** Controller re-ran `flat_wave_replication.py --all`:
   cnfd 1.9935, cnfem 1.9863, lffd 1.9958, `selftest_pass: true`,
   `replication_verdict: ORDER REPRODUCED`. Evidence hashed at
   `runtime/state/controller_verification/n0_replication_astra_run2_FIXED.json`
   (sha256 6542db93). Credit: worker 13.
2. **A2 harness self-test passes** including the unmatched-budget negative control,
   null-baseline separation and "no universal scalar score".
3. **Class-separation gate**: 17/17 leaks, 10/10 controls, 0 FP/FN, run at every
   checkpoint and frozen as gate evidence.
4. **Promotion engine** now machine-enforces the bar per conclusion type: 0 promoted,
   21 blocked, 1 controller-adjudicated (worker-07's counterexample). Two claims that
   had been promoted on stale/empty artifact refs were demoted: a claim referencing
   revision `eb0d69fa` of a file that has since moved, and a claim with no
   `artifact_refs` at all.

## 3. Open risks

1. **Dual-tree provenance.** The formulation lead authors under `artifacts/formulation/`
   and declared revision 6 frozen there, but its `FROZEN.json` hashes match neither tree
   on disk (F1: manifest `f512af5f`, authoring `ef8441e4`, canonical `7a3e1f93`).
   Decision: canonical binding stays `research_map/` + `schemas/`; the authoring tree must
   mirror at publish. Divergence is now a standing audit finding (hard while frozen).
   Reviewers will bind only to published hashes.
2. **Tooling:** worker-level `web_search` fails 3/3 (TypeError against the model
   endpoint); direct HTTPS fetch works. Workaround broadcast; escalated to Human PI.
   G-LIT spot checks are still landing via workers whose fetch works.
3. **Gate proliferation:** three `G-CLASSBIND` proposals were recorded as calibration
   evidence, not adopted; one class gate + one regression is the standard.
4. **Provider channel** still absent for the real A2 four-arm ablation (escalated).

## 4. Next window

1. Formulation: publish revision 6 to canonical paths; Astra re-freezes and re-dispatches
   F0/F1/F2b reviews.
2. Numerics: protocol review closes G-NUM; then N1 remains locked until G-FORM/G-AUDIT.
3. Literature: coverage of the 8 uncovered sources; unknown class tokens remap; the
   conditional-theorem review (worker 16).
4. Audit: checker calibration table; L0 revision; F2b re-review.
5. Astra: keep the loop, adjudicate promotions and blockers, hold gates until evidence.
