# Astra lifecycle pass 02 — summary (2026-09-12T00:11–00:18+08:00)

Controller: `astra` (independent session `controller-01-20260912T001038-843521`, one control pass then exit).

The idempotent lifecycle tool (`research_map/astra_lifecycle.py`) was invoked four times inside this
one control pass because traffic kept arriving mid-pass:
`astra-lifecycle-02` (00:11:13), `-02-close` (00:15:51), `-02-final` (00:17:27),
`-02-close-final` (00:17:46). Each invocation is the full locked sequence
ingest → apply → repair → audit → checkpoint; the last one is the pass end state.

## Final state (pass end, 00:17:46)

| item | value |
|---|---|
| map sha256 before / after | `50ca14345ed8…` → `4d8291c9a9ae44558a4dea49106b525ed7b5c8a2b25cc003a5a754ddb3507306` |
| validator | `VALID` |
| gates | G-F0, G-FORM, G-LIT, G-NUM, G-AUDIT all `pending` |
| numerics lock | `locked`; `numerics/spherical_solver` absent; `numerics/tests/selfgravity_lock_guard.py` present |
| evidence audit | 1 hard (CF-16, adjudicated false positive), 4 soft (3 class-token soft flags + 1 dual-tree divergence) |
| checkpoint | `ckpt-20260912-001747` |
| latest report | `runtime/state/controller_verification/lifecycle_20260912-001746.json` (sha256 `d8990be4de29…`) |
| findings | CF-1 … CF-16 recorded in the map |

## Publication status (canonical is authoritative)

| artifact | canonical | authoring | status |
|---|---|---|---|
| `schemas/af_wcc_vacuum.yaml` | `68392dd82050` | `68392dd82050` | aligned (rev21) |
| `schemas/af_scc_c2_vacuum.yaml` | `4f97273ef440` | `4f97273ef440` | aligned (rev21) |
| `schemas/af_scc_c0_vacuum.yaml` | `a2aef5ac7fe3` | `a2aef5ac7fe3` | aligned (rev21) |
| `research_map/formulation_taxonomy.yaml` | `0fcc6a1928fd` | `01e7f841643c` | **divergent** |

`artifacts/formulation/FROZEN.json` rev20 does not name a single frozen F0 revision (it pins the
canonical and authoring paths to different hashes). FORM-MAP-PATCH-002 remains superseded: the map is
not repointed at the authoring tree.

## Gate reasons (hash-bound, from `controller_gate_audit`)

- **G-F0** — canonical taxonomy `0fcc6a1928fd`; 0 distinct accepts bind to this hash; needs two
  independent accepts. Publication divergent. 2 class-separation soft flags on F0 await disposition.
- **G-FORM** — F1/F2a/F2b measured `68392dd82050` / `4f97273ef440` / `a2aef5ac7fe3`; publication
  aligned; 0 full-schema accepts bind to these hashes; 1 soft flag on F1 awaits disposition.
  Verdicts at superseded hashes are advisory only.
- **G-LIT** — L0 `ce42d205e761`, 0 accepts at this hash; L1 `315c19145065`, 2/3 independent re-fetch
  spot checks at this hash; ledger class-token flag cleared.
- **G-NUM** — lock verified locked; protocol measured `1e6cdf04d7a2`; the recorded protocol verdict
  binds `01b2072434cd` (stale), so the N0 proposal's criterion C8 is the exact unmet requirement.
- **G-AUDIT** — A0 exists (`d748a9e3574e`); A1 has 0 distinct full-schema accepts at the measured
  hashes for F0/F1/F2a/F2b/L0 (need ≥2 each).

## Findings added this pass

- **CF-12** (major, adjudicated) — canonical path `numerics/tests/n0_gate_proposal.json` was assigned
  to two agents at once; the worker submission overwrote the lead's. Lead adjudication preserved at
  `artifacts/numerics/n0/n0_gate_proposal_lead.json#bfce1460fafa`. Rule: one canonical path, one
  owner; successors narrow or supersede, never duplicate.
- **CF-13** (major, partially resolved) — publication measured per pass; only F0 remains divergent.
- **CF-14** (major, open) — 55–72 accepted events carry `created_at` in the future (max 02:00), and
  FROZEN.json rev20 was stamped 00:15 while written at 00:11. Future timestamps are treated as
  advisory for ordering.
- **CF-15** (info) — gate reasons are now derived from the measured review corpus, not hardcoded.
- **CF-16** (minor, adjudicated false positive) — the hard CLASSSEP failure on `claims[36]` reads the
  test-case labels "TC-F0-N14 C0/C2 merge" and "TC-F0-N15 WCC/SCC merge" as merge assertions; the claim
  states those cases need no new class and its class_ids are the frozen four. Raw count remains until
  the author rephrases or the checker exempts quoted case labels (CF-4 policy: checkers flag, never author).

## Assignments issued (all mirrored to assignee inboxes)

| event_id | assignee | artifact | deadline |
|---|---|---|---|
| `astra-life02-publish-f0` | astra-lead-formulation | `research_map/formulation_taxonomy.yaml` | 01:00 |
| `astra-life02-softflag-f0f1` | astra-lead-audit | `reviews/A1-rebind-coverage.json` | 01:00 |
| `astra-life02-n0-c8` | astra-lead-audit | `reviews/G-NUM-protocol-review.json` | 01:30 |
| `astra-life02-n0-c8-refresh` | astra-lead-audit | `reviews/G-NUM-protocol-review.json` | 01:30 |
| `astra-life02-l1-spotcheck` | astra-lead-literature | `ledger/citation_audit.csv` | 01:30 |

Each carries an acceptance test, falsifier, stop rule and budget in `map.assignments`; a message is
not a result until an artifact hash is recorded. Older `astra-life01-*` assignments stay open through
01:30 and are not duplicated.

## Tooling changes

- `research_map/astra_lifecycle.py`: added `review_coverage()` (explicit-pin scan of `reviews/*.json`),
  `l1_spotchecks()`, `clock_discipline()`, `lock_guard()`; gate reasons and CF-13/CF-15 are now
  measured rather than hardcoded; the tool appends its own `controller_lifecycles` record.
- `research_map/astra_lifecycle_02_events.py`: idempotent pass-02 gate/assignment emitter (skips
  duplicate events and already-sent inbox messages).

## Honest limitations

- Four invocations of one idempotent lifecycle tool were needed because artifacts and reviews moved
  during the pass; this is one control pass, not a loop. The next controller should re-measure
  everything before citing.
- `review_coverage` is an advisory controller scan; binding coverage is adjudicated by the audit lead
  (`reviews/A1-rebind-coverage.json`).
- The numerics gate adjudication rests on lead-provided measurements; the controller verified only
  artifact existence, hashes, lock state, and the staleness of C8.
