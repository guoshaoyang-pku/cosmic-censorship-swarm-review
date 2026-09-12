# Astra checkpoint report 1 — 2026-09-11T23:30+08:00

Run: `run-2026-09-11T23:15+08:00`, 4 h invocation, 25 agents (1 controller, 4 leads,
20 Flash workers), checkpoint loop every 15 min (`runtime/logs/astra-cycle.log`).
Sole global state: `research_map/research_map.json`. Machine checkpoint:
`runtime/state/current_checkpoint.json`.

## 1. Gate board

| gate | scope | verdict | reason |
|---|---|---|---|
| G-F0 | F0 taxonomy | pending | two independent `revise` verdicts (17: 3.0; 19: 1.0); consolidated revision directive R1–R9 issued |
| G-FORM | F1, F2a, F2b | pending | F1 `revise` 3.5 (predicate mismatch, unproved "equivalently", checker-driven wording); F2a `accept` 5.0; F2b `revise` 2.0 |
| G-LIT | L0, L1 | pending | ledger landed (37 rows, 60 citations, 58 verified / 2 unresolved); controller spot-check of SRC-002 confirmed verbatim; L0 `revise` 3.0 from audit lead |
| G-NUM | N0 | pending | order reproduced by lffd 1.9958 + cnfd 1.9935, but cnfem broken (order −0.077, drift 1e1) and the harness invariant is leapfrog-specific |
| G-AUDIT | A0, A1 | pending | rubric landed without a universal scalar score; A1 reviews in flight |

`numerics_lock`: **locked** (N1 queued; N1-BLOCK carries the contract work). No
self-gravitating code exists; the lock guard passes.

## 2. Hard findings this window

1. **Unbacked done nodes.** The map marked F0 and A0 `done`/`passed` with no artifact on
   disk; `validate_map.py` returned VALID because it never checked. Both demoted to
   `active`/`unverified`; `audit_evidence.py` added; worker-19's artifact/evidence patch
   integrated into `validate_map.py`; declared-hash drift now checked.
2. **N0 replication defect.** Controller-executed replication returned `ORDER DISAGREES`:
   lffd 1.9958 PASS, cnfd 1.9935 PASS (energy self-check marginal), cnfem −0.0773 FAIL
   (self-test false, drift 1.0e+01). Adjudication: cnfem is an implementation defect, not
   counter-evidence; harness invariant functional is scheme-specific. G-NUM withheld.
   Triage assigned to workers 13/14.
3. **Class-separation gate was defective — falsified by worker 07.** The old checker caught
   3/17 genuine merges and produced 1 spurious flag on a 27-fixture corpus. Rebuilt as
   `research_map/class_separation.py` with declaration/prose modes, local negation handling,
   WCC/SCC family and conclusion-inflation rules; regression now runs every checkpoint:
   **17/17 leaks, 10/10 controls, 0 FP, 0 FN**. Frozen as gate evidence.
4. **Tool-driven formulation drift.** An F1 conclusion predicate was moved away from the F0
   canonical wording to satisfy a linter whose false-positive rate on the real artifact was
   22 shape + 4 leak flags with zero true positives. Policy recorded: checkers may flag,
   never author; a statement change needs a named lead decision and reason. Calibration task
   assigned to the audit lead (`evaluation/checker_calibration.csv`).
5. **Two class tokens outside the frozen four** in `ledger/theorems.jsonl`
   (`AF-WCC-VAC-BH-FORM`, `AF-WCC-VAC-NS-CONSTR`). Directive: remap or rename as ledger tags;
   no new classes without Human PI approval.

## 3. Portfolio state

- Measured: 25 live agents at start, 24 live at 23:27 (worker 19 exited 0 after a bounded
  increment; its items reassigned); ~4.9–6 agent-hours measured in-run.
- Artifacts on disk by group (measured): formulation 8, literature 8, numerics 41, audit 60.
- Claims recorded: 11, all `promotion_status: unpromoted`; highest-risk is a literature
  `conditional_theorem` (C0 SCC falsity conditional on Kerr stability) awaiting review.
- Comms: 355 applied events, 1 persistent reject (an availability note with no node_id),
  0 pending.
- Frozen artifacts: F0 a82f249c (superseded by directed revision), F1 f15ea523 (superseded),
  class_separation.py c266dbce, classsep_regression.py 9f1cf9c3.

## 4. Escalations to Human PI

- **A2 four-arm ablation cannot execute**: no provider channel/API budget in this workspace.
  The harness and matched-budget dry-run exist (`evaluation/ablation_report.json`); real
  inference needs credentials and a spend cap. No swarm-advantage claim may cite the
  synthetic run.
- **No new formulation classes** without PI approval (hard decision 1 stands).

## 5. Next window

1. Formulation lead: revision 3 of F0 and F1; then Astra re-freezes and re-dispatches reviews.
2. Audit: checker calibration table; F2a second verdict; L0 revision.
3. Numerics: cnfem root cause, scheme-appropriate invariant, clean replication; then G-NUM
   proposal.
4. Literature: L1 spot-checks (workers 10/11), unknown-token remap, `conditional_theorem`
   scope review.
5. Astra: keep the 15-min loop, adjudicate incoming claims, hold all gates until evidence.
