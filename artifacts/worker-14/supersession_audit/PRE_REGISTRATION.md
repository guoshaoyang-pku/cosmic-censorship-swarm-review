# W014-GNUM-SUPERSESSION-AUDIT-01 — pre-registration

- worker: worker-014 (slot 014, instance 2026-09-12T010618-968807)
- class_id: AF-WCC-SCALAR-SPH | node: N0 | gate: G-NUM
- task: independent, read-only audit of the withdrawal/supersession behaviour of the G-NUM
  protocol-review guard `numerics/gates.py::_protocol_review` at the pinned bytes
  `numerics/gates.py#fcd1d70991b6eade`, protocol of record
  `numerics/CONVERGENCE_PROTOCOL.md#1e6cdf04d7a24313`.
- why: open queue item, not owned by any worker. Flagged by worker-042 F-042-N0-2, worker-067
  (G-NUM C8 binding), worker-081 (adj2 + pin-split), worker-012 OI-2, and by the numerics lead's
  own blocker `lnum-blocker-e9e939acc0856fa77127` ("PROTOCOL REVIEW CONTEST and a measured guard
  defect"). Astra pass-06 records it as "needs a controller disposition or guard supersession
  rule". No worker has produced a pinned reproduction of the defect set plus a control-tested
  candidate rule.
- scope: read-only on every canonical path. Writes only under
  `artifacts/worker-14/supersession_audit/` and `runtime/state/w014_*`. No gate verdict, no node
  completion, no canonical write, no fix to `numerics/gates.py` (owner: numerics lead / controller;
  a rewrite moves the hash and voids bound verdicts).

## Inputs pinned before measurement

| input | sha256 |
|---|---|
| `numerics/gates.py` | `fcd1d70991b6eade4aa993dc49b6103e338f68320aabb955d97da5a8f55d996e` |
| `numerics/CONVERGENCE_PROTOCOL.md` | `1e6cdf04d7a2431373092b657095bab4edeea9fb32f1d3c8981c50b2156a7274` |
| event stream | merged by `gates.load_event_stream` (accepted stream + outbox + inbox), snapshotted by the instrument and hashed in the report |

## Predictions (declared before the candidate rule was implemented or run)

A read-only recon probe of the *live* evaluator was run before this file (it produced the defect
hypotheses). The predictions below concern the candidate rule and the controls, which were not
run before this file.

- **P1** the live evaluator at the pinned hash reproduces exactly 5 `accepting_reviews`, 5
  `dissenting_reviews`, `contest=true`, 3 advisory reviews.
- **P2 (D1)** `w081-20260912T002140-c8-review` is counted as an accepting review although its
  author withdrew it in `w081-2026-09-12T00:29:19+0800-complete` ("prior W081-N0-C8-01 accept
  withdrawn") and later issued both a revise and an accept at the same hash.
- **P3 (D2)** same reviewer + same protocol hash holds both `w081-2026-09-12T00:29:19+0800-f1-review`
  (revise) and `w081-20260912T0042050800-adj2-review` (accept); no per-reviewer ordering exists.
- **P4 (D3)** the operative lead-audit accept `audit-l06-review-gnum-r4-20260912T005926`
  (00:59:26, "operative protocol verdict at 1e6cdf04d7a2") is not counted — it lands in
  `advisory_reviews_at_other_hashes` with `cited=[]` because the hash appears only in its prose.
- **P5 (D4)** the guard target set includes the bare token `N0`, so N0-artifact reviews that
  merely cite the protocol hash are counted as protocol verdicts:
  `f13-n0rev3-20260912T005801-review` (accept of rev3) as an accept, and
  `w067-provledger-20260912T005149-20-review` / `w042-n0-stoprule-01-review` /
  `w081-20260912T005818-pinsplit-review` as dissents.
- **P6** candidate rule R-A (explicit author withdrawal + latest bound verdict per reviewer and
  target class + prose-hash citation) yields accepts `{audit-l06-review-gnum-r4-20260912T005926,
  w081-20260912T0042050800-adj2-review, w012-c3-review-0001-adjudication,
  f13-n0rev3-20260912T005801-review}`, dissents `{w067-review-gnum-protocol-r3-20260912T002256,
  w067-provledger-20260912T005149-20-review, w042-n0-stoprule-01-review,
  w081-20260912T005818-pinsplit-review}`, and withdrawn/superseded
  `{w081-20260912T002140-c8-review, w081-2026-09-12T00:29:19+0800-f1-review,
  audit-review-gnum-protocol-final-20260912T0027}`. Contest stays true (fail-closed).
- **P7** candidate rule R-B (R-A with strict protocol targets, bare `N0` dropped) yields accepts
  `{audit-l06-review-gnum-r4-20260912T005926, w081-20260912T0042050800-adj2-review,
  w012-c3-review-0001-adjudication}` and dissents `{w067-review-gnum-protocol-r3-20260912T002256}`;
  contest stays true.
- **P8** controls C1–C11: the live evaluator fires the expected defect on C1 (withdrawn accept),
  C2 (self-supersession), C8 (prose-hash accept), C9 (N0-artifact accept), C11 (withdrawn
  dissent); the candidate rule passes all eleven and stays fail-closed on C7 (two reviewers
  disagree) and C10 (live reject).
- **P9** both the candidate rule and the whole instrument are deterministic: two runs produce
  byte-equal substantive payloads.
- **P10** no canonical file is modified; `numerics_lock` stays LOCKED, `numerics/spherical_solver`
  stays absent, N1 untouched.

## Falsifier

Re-run `python3 verify_supersession.py --out report.json` at the pinned inputs. The verdict is
falsified if any live-state count differs, if any D1–D4 classification does not reproduce from
the named event IDs, if the candidate rule fails any control or fails to remain fail-closed on
C7/C10, if the two deterministic runs differ, if any canonical input hash drifts, or if the lock
guard no longer reports N1 blocked. A moved `gates.py` or protocol hash voids the audit for the
new bytes.
