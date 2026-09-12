# PRE-REGISTRATION — W014-GNUM-N0-L09-CROSSVERIFY-01

Written before any measurement is run. Actor: `worker-014`. Class: `AF-WCC-SCALAR-SPH`.
Node: `N0`. Gate: `G-NUM` (proposal only; no gate verdict, no node transition).
Lock: `numerics_lock` is LOCKED — flat-space N0 only, no `numerics/spherical_solver/`, no N1.

## Task (one class-bound task, taken from the live queue — no inbox card exists for this slot)

Second, independent, read-only cross-verification of the lifecycle-09 lead verification
`numerics/protocol/lifecycle09_lead_verify.json` (declared sha256 `baa93446d370…`), which
claims (1) stop-rule item 1 order-measured MET, (2) item 2 F0 re-bind MET, (3) item 3
independent replication MET, and files finding `L09-F1` that the live map's G-NUM
`unmet[1]` still calls items 1–3 open.

Why this task: it is the only N0 evidence package produced since worker-014's last task
(`W014-GNUM-N0-CLOSURE-CROSSVERIFY-01`, lifecycle-08 package) and no worker has independently
cross-verified it. It is bounded, deterministic and hash-pinned. It does not touch the
contested protocol review or the lead-audit-owned N0 verdict.

## Pinned inputs (bytes are the verification surface; any drift voids the verdict)

| path | declared sha256 (prefix) |
|---|---|
| `numerics/protocol/lifecycle09_lead_verify.json` (target) | `baa93446d3702180` |
| `numerics/protocol/n0_fixed_dt_certification.json` | `1677822ceb9c81e8` |
| `numerics/results/flat_wave_convergence_rev3.json` | `da7c360719950f7e` |
| `research_map/formulation_taxonomy.yaml` | `0abb9ed8a96135c9` |
| `artifacts/worker-046/n0_fixed_dt_independent/verification.json` | `814452111bc8912b` |
| `artifacts/worker-057/n0_fixeddt_verify/report.json` | `b906445878f3130d` |
| `artifacts/worker-081/n0_c8_adjudication_rev2/adjudication.json` | `65ae766d9e4c2057` |
| `numerics/protocol/lifecycle08_stoprule_closure_verify.json` | `88ec0bf298cbc4de` |
| `research_map/research_map.json` (live map) | measured, no pin; drift-guarded |

## Predictions (declared before running; deviations are findings, not repairs)

- **P1** — target exists, parses, `schema == "lifecycle09-lead-verify/v1"`, `class_id ==
  AF-WCC-SCALAR-SPH`, `node_id == N0`, `gate == G-NUM`.
- **P2** — each scheme has exactly 4 rungs, `dt == 1e-4` on every rung, `dr` ladder
  `[0.2, 0.1, 0.05, 0.025]`; L2 errors strictly positive and strictly decreasing.
- **P3** — my own pure-Python OLS log-log fit (implemented independently, not imported from
  any project module) reproduces every declared `fit_order` and `least_squares_se` in the
  certification to `<= 1e-12` absolute; `|p - 2| <= 0.3` for lffd, cnfd, cnfem.
- **P4** — consecutive-pair orders and R5 `delta = max(pair half-range, OLS SE)` reproduce
  the declared values; cross-scheme spread `<= 0.25` and each pair satisfies
  `|p_A - p_B| <= max(0.25, sqrt(delta_A^2 + delta_B^2))` (protocol §3.8).
- **P5** — live `research_map/formulation_taxonomy.yaml` hashes to `0abb9ed8a961…`,
  `revision == 5`, and lists class id `AF-WCC-SCALAR-SPH`.
- **P6** — the three replication verdict files hash to their declared pins and carry tokens
  SUPPORTED / REPRODUCED / `binding_accept_at_current_hash == true` with
  `blocks_gate_pass == false`; `frozen_run_hash` equals the sha256 of
  `numerics/results/flat_wave_convergence_rev3.json`.
- **P7** — lock compliance: `numerics/spherical_solver/` absent, live map lock `locked`,
  N1 `queued`, lead's lock booleans match live.
- **P8** — map-state finding confirmed with a refinement: the live map's G-NUM `criteria`
  already carries the lifecycle-09 closing text (refreshed by the controller after the
  lead's 01:17:26 snapshot), while `unmet[1]` still reads "Stop-rule items 1-3 above are
  open". So `L09-F1` is confirmed in the `unmet` field and only there; the lead's
  `map_updated_at` snapshot is superseded.
- **P9** — 12/12 controls fire (known-answer LSQ, monotonicity, band, cross-scheme spread,
  hash mismatch, token mutation, class-id absence, lock absence, stale-map positive +
  consistent-map negative, drift guard, pin-guard before/after).

## Verdict rule (fail-closed)

`ACCEPT` iff A1–A4, B1–B7, C1–C4, D1–D4, E1–E3, F1–F5 hold and all controls fire; the P8
map staleness is a confirmed finding, not a check failure. Any pinned-input hash mismatch,
parse failure, non-monotone ladder, band violation, spread violation, or unfired control
yields `REVISE`/`INCONCLUSIVE` with the exact check id — never a repaired artifact.

## Non-claims

Not a G-NUM gate verdict; not an N0 node completion or status transition; no
`numerics_lock` release; no adjudication of the contested protocol review
(`reviews/G-NUM-protocol-review.json`); no canonical-path write; no physics / self-gravity /
WCC / SCC claim. Worker-level only; gate authority stays Astra / lead-audit.
