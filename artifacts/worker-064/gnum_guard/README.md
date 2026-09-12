# W064-GNUM-GUARD-CENSUS-01 — independent read-only census of `_protocol_review`

**Task (one class-bound task, self-selected; no inbox card existed for worker-064).**
Class `AF-WCC-SCALAR-SPH`, node `N0`, gate `G-NUM`. Independent measurement for
blocker `audit-l06-b4` (audit lead, 00:59:26): `numerics/gates.py::_protocol_review`
still reports `contest=true` at protocol `1e6cdf04d7a2`. Read-only: no solver, no
self-gravity, `numerics_lock` stays LOCKED; no canonical file was written.

**Pins measured at run start and end (unchanged):**

| path | sha256 |
|---|---|
| `numerics/gates.py` | `fcd1d70991b6eade4aa993dc49b6103e338f68320aabb955d97da5a8f55d996e` |
| `numerics/CONVERGENCE_PROTOCOL.md` | `1e6cdf04d7a2431373092b657095bab4edeea9fb32f1d3c8981c50b2156a7274` |
| `reviews/G-NUM-protocol-r4-adjudication.json` | `b836902fa4ae0e57af52d408c09ad03b4a2023b038d8d0cb186c45f8f69ad354` |
| frozen event snapshot (11,587 events) | `2a993a8ca3676611b347facefaf49b644fba969ad83282b5db31972322dd6b75` |

The live module was never imported from its canonical path: a hash-pinned copy
(`pinned/gates_fcd1d70991b6.py`) is imported with `sys.dont_write_bytecode=True`,
so no `__pycache__` was deposited in `numerics/`.

## 1. Census at the pinned bytes — 5 accepts, 5 dissents, 3 advisory

| side | event_id | reviewer | target | subject |
|---|---|---|---|---|
| accept | `w081-20260912T002140-c8-review` | worker-081 | G-NUM-protocol | protocol accept — **withdrawn in prose** |
| accept | `audit-review-gnum-protocol-final-20260912T0027` | astra-lead-audit | G-NUM-protocol | protocol accept 4.5 |
| accept | `w081-20260912T0042050800-adj2-review` | worker-081 | protocol#hash | protocol accept 4.0 |
| accept | `w012-c3-review-0001-adjudication` | deepseek-flash-12 | protocol#hash | protocol accept 4.0 |
| accept | `f13-n0rev3-20260912T005801-review` | deepseek-flash-13 | **N0** | N0 rev-3 accept |
| dissent | `w067-review-gnum-protocol-r3-20260912T002256` | worker-067 | protocol#hash | F1 evidence basis |
| dissent | `w081-2026-09-12T00:29:19+0800-f1-review` | worker-081 | protocol#hash | F1′ evidence basis |
| dissent | `w067-provledger-20260912T005149-20-review` | worker-067 | **N0** | provenance ledger |
| dissent | `w042-n0-stoprule-01-review` | worker-042 | **N0** | stop rule |
| dissent | `w081-20260912T005818-pinsplit-review` | worker-081 | **N0** | pin split |
| advisory | `audit-review-20260912T0009-gnum-protocol` | astra-lead-audit | stale hash | superseded revise |
| advisory | `audit-r2-review-n0` | astra-lead-audit | no hash | uncited |
| advisory | `audit-l06-review-gnum-r4-20260912T005926` | astra-lead-audit | G-NUM-protocol | **the operative r4 adjudication accept** |

The audit lead's 00:59 ruling (`reviews/G-NUM-protocol-r4-adjudication.json`,
verdict `accept 4.5`, F1/F1′ discharged) is **advisory to the guard**, because the
emitted event carries no `reviewed_sha256` and no
`numerics/CONVERGENCE_PROTOCOL.md#<hash>` evidence ref — although the artifact it
cites does carry `reviewed_sha256=1e6cdf04d7a2`. Arm `arm_hash_repair_only` shows
that adding that one field binds the accept (6 accepts) and **does not clear
contest** (5 dissents persist).

## 2. Findings

- **F-GUARD-1 — the operative adjudication does not bind the guard.** One-field
  event-layer repair demonstrated in memory; necessary, not sufficient.
- **F-GUARD-2 — target conflation.** `PROTOCOL_REVIEW_TARGETS` contains `N0`, so
  3 of 5 dissents and 1 of 5 accepts are N0 *node* verdicts, not protocol reviews.
  The r4 card explicitly claims no N0 node-status verdict.
- **F-GUARD-3 — a withdrawn accept keeps voting, and the withdrawal is prose-only.**
  `w081-2026-09-12T00:29:19+0800-complete` says "prior W081-N0-C8-01 accept
  withdrawn", but no `withdraws`/`withdraws_event_ids`/`withdrawn_event_ids` field
  exists anywhere in the stream. A withdrawal-aware rule is therefore inert today
  (positive control E8P: emits the field → accept count 5→4… in the scoped arm 4→3).
- **F-GUARD-4 — one reviewer counts on both sides.** worker-081 is both a counted
  accept and a counted dissent at the same protocol hash.
- **F-GUARD-5 — clearing contest is necessary, not sufficient.** The controller's
  own G-NUM audit (`runtime/state/controller_verification/lifecycle_20260912-010044.json#14367b7196ad`)
  keeps G-NUM pending until the N0 node verdict is an accept; the on-disk N0
  verdict is `reviews/N0-pin-split-adjudication-worker-081.json#a39c7178c008`
  revise 3.5. `production_allowed` also requires the other lock reasons.

## 3. Candidate rule (PROPOSAL ONLY — not applied; owner: controller)

- **R1 scope** — protocol review state excludes N0-targeted reviews.
- **R2 withdrawal** — a later event naming a counted review removes it, but only
  when the withdrawing actor is that review's own author.
- **R3 discharge** — a later *binding* review at the same hash may carry
  `discharges` / `discharged_event_ids` / `supersedes_event_ids`; listed dissents
  are recorded as `discharged_dissents` and do not set contest. Fail-closed:
  unknown ids, stale-hash carriers, pre-dated carriers and uncited carriers never
  discharge.

Arm results (frozen snapshot):

| arm | accepts | dissents | contest |
|---|---|---|---|
| current bytes | 5 | 5 | true |
| hash-repair only | 6 | 5 | true |
| R1 scope | 4 | 2 | true |
| R1+R2 (live stream; prose-only withdrawal) | 4 | 2 | true |
| R1+R2 with structured field (positive control) | 3 | 2 | true |
| R1+R2+R3 (discharge field on the r4 event) | 5 | 0 | **false** |

Negative controls (all hold): unknown-id discharge, stale-hash carrier,
pre-dated carrier, uncited carrier, third-party withdrawal, fresh unlisted
dissent — each leaves contest true. The shadow implementation reproduces the
pinned guard exactly with all hooks off (equivalence control E0).

## 4. Reproduction

```bash
python3 artifacts/worker-064/gnum_guard/w064_gnum_guard_census.py   # exit 0
```

Exit 2 = tool/protocol pin moved (counts void at the new bytes); exit 3 = a
preregistered expectation falsified. The harness re-reads the live stream after
the frozen run and records drift (`raw/live_recheck.json`).

## 5. Falsifiers

- Re-measure `numerics/CONVERGENCE_PROTOCOL.md`: any hash other than
  `1e6cdf04d7a2` voids every count here at the new bytes.
- Any predicted census row missing, or counted on the other side, falsifies the
  census. (Two preregistered predictions *were* falsified as written and are
  recorded verbatim in `report.json#prereg_falsified`: E5 assumed a structured
  withdrawal; E8 assumed R2 would bind on the live stream.)
- Any negative control clearing `contest` would falsify the candidate rule; none does.
- A rerun on the frozen snapshot producing a different verdict falsifies
  determinism (E12 holds).

## 6. Not claimed

No gate verdict, no gate self-pass, no N0 node completion; no physics claim; no
solver or self-gravity work; no canonical file modified; R1–R3 are not adopted.
