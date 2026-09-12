# W014-GNUM-N0-L09-CROSSVERIFY-01 — result README

Second, independent, **read-only** cross-verification of the lifecycle-09 lead verification
record `numerics/protocol/lifecycle09_lead_verify.json`
(sha256 `baa93446d3702180b8a8f39ea285dcfff3eab4980c7d77a82e60abc6778e8a62`) for
N0 / `G-NUM`, class `AF-WCC-SCALAR-SPH`.

**Verdict:** `LIFECYCLE09_LEAD_VERIFY_CROSSVERIFIED_ACCEPT_MAP_UNMET_REFRESHED` —
28/28 checks pass, 12/12 controls fire, 0 hard failures, all 9 pinned inputs byte-stable
across the run, deterministic on re-run (identical except `generated_at`).

Worker-level only: **no gate verdict, no node transition, no lock release, no canonical write.**

## What was independently reproduced

| scheme | 4-rung fit p (mine = declared) | OLS SE | R5 delta = max(half-range, SE) | \|p−2\| |
|---|---|---|---|---|
| lffd | 1.999943173893314 | 2.752317054506189e-05 | 8.443728170604015e-05 | 5.68e-05 |
| cnfd | 1.9998635927240203 | 2.9589985913245132e-05 | 9.317737622183131e-05 | 1.36e-04 |
| cnfem | 1.9999163079874884 | 8.498445337728289e-05 | 2.4634e-04 | 8.37e-05 |

Cross-scheme spread `7.958116929374093e-05 <= 0.25`; every pair also satisfies the protocol §3.8
rule `|p_A − p_B| <= max(0.25, sqrt(δ_A²+δ_B²))`. Absolute differences vs the declared
certification values are **0.0** for fit order, SE, pair orders and R5 delta in all three
schemes. The fit was re-derived with a pure-Python OLS implementation written for this task
(no project import, no numpy), so the agreement is independent of the lead's code path.

- **Item 2 (F0 re-bind):** live `research_map/formulation_taxonomy.yaml` hashes to
  `0abb9ed8a961…`, `revision: 5`, class `AF-WCC-SCALAR-SPH` present.
- **Item 3 (replication):** the three cited verdicts hash to their pins and carry the expected
  tokens — worker-046 `SUPPORTED`, worker-057 `REPRODUCED`, worker-081
  `binding_accept_at_current_hash=true` / `blocks_gate_pass=false`. `frozen_run_hash` equals the
  sha256 of `numerics/results/flat_wave_convergence_rev3.json`.
- **Lock:** `numerics/spherical_solver/` absent; live map lock `locked`, `N1` locked, `N0`
  allowed; lead's lock fields match live bytes. `numerics/spherical.py` is the N0 flat-space
  scalar-wave harness imported by the N0 calibration, not a self-gravitating solver (advisory
  `W14-L09-R1`).

## Deviation from pre-registration (reported, not repaired)

`PRE_REGISTRATION.md` prediction **P8** expected the live map to still show the criteria-vs-unmet
contradiction the lead filed as `L09-F1`. It does not. The controller refresh at
**01:22:04** (between pre-registration and measurement) rewrote the G-NUM `criteria`/`unmet`
into a consistent state; `unmet` now names only the two remaining lead-owned stop-rule
assignments (`astra-life04-n0-stoprule`, `astra-life04-n0-verify`). Cross-check F2 verifies the
lead's *own* recorded snapshot (map_updated_at `01:16:26`, unmet contains the items-1-3-open
text) and F3/F4 verify the live map is now contradiction-free. Net: `L09-F1` was valid for the
bytes it measured and is superseded, not wrong — recorded as finding `W14-L09-F1` (info).
The prediction is left unedited in the pre-registration.

## Files

| file | sha256 |
|---|---|
| `report.json` | `083f67f18a7da35a54c8b92bb0532e125ddb24dbc24f72d5e0c94d223d8c2937` |
| `verify_l09.py` | `ffe8b420e0823e018b6e6780fdc927a132f7f0a7f3b5c32f037ab5a0078c1697` |
| `PRE_REGISTRATION.md` | `89a5affacda23fb343b9f7133080b40d3dfd81f169ca1941b02c6c1f22931698` |
| `emit_events.py` | emitted below |
| `events_emitted.jsonl` | outbox events as written |

Re-run: `python3 verify_l09.py --out report.json` (read-only over all pinned inputs).

## Falsifier (carried into the events and checkpoint)

Re-run this script at the pinned inputs. Falsified if any declared pin moves, any recomputed fit
leaves `|p-2|>0.3`, a ladder is non-monotone, cross-scheme spread `>0.25` or the per-pair R5 rule
fails, a cited verdict loses its token, live taxonomy `!= 0abb9ed8a961` or lacks
`AF-WCC-SCALAR-SPH`, `numerics_lock != locked` or `numerics/spherical_solver` appears, the
record's map-snapshot claim or the live G-NUM criteria/unmet state is not as reported, any
control fails to fire, or any pinned input drifts pre/post. A later write to any pinned path
voids the verdict for the new bytes.

## Non-claims

Not a G-NUM gate verdict; not an N0 node completion or status transition; no `numerics_lock`
release; no adjudication of the contested protocol review (`reviews/G-NUM-protocol-review.json`);
no canonical-path write; no physics / self-gravity / WCC / SCC claim. Gate authority stays
Astra / lead-audit.
