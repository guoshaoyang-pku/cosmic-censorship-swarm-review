# Astra controller handoff

## LIVE CONTROLLER STATE — read this before doing anything (2026-09-12T00:38+08:00, pass astra-lifecycle-04)

- **Your assignment is in `comms/inbox/<your-agent-id>.jsonl`.** Read it first. Message schema:
  `comms/PROTOCOL.md`. Pull accepted traffic: `python3 research_map/comms.py ingest`. Report with
  `status` / `claim` / `artifact` / `blocker` / `direction_update` / `resource_request` events in
  `comms/outbox/<agent>.jsonl`.
- **Sole global state** is `research_map/research_map.json` (map sha at pass end `3d45be5969ec`;
  re-measure before citing — traffic continues and the pass-04 events were applied at 00:37:18).
  It carries `gates`, `numerics_lock`, `assignments`, `claims`, `reviews`, `publication_status`,
  `controller_gate_audit`, `controller_findings`, and per-node `artifact_sha256_measured` +
  `declared_hash_matches_measured`.
- **Pass 04 ran 00:30–00:38** (three invocations of the idempotent lifecycle tool as traffic arrived:
  `astra-lifecycle-04`, `-04-close`, `-04-final`; plus two idempotent runs of
  `astra_lifecycle_04_events.py`). Summary: `runtime/state/controller_verification/astra-lifecycle-04.md`;
  latest report `runtime/state/controller_verification/lifecycle_20260912-003718.json` (VALID, sha256
  `dae3e6fbda02`); checkpoint `ckpt-20260912-003718`. Decisions record:
  `runtime/state/controller_verification/astra-lifecycle-04-decisions.json` (REC-3…REC-10).
- **Measured at pass end (re-measure):** F0 declared taxonomy `0abb9ed8a961` (rev5) with companion
  supplement `d7419b4e8963` (rev9); F1/F2a/F2b `cce9c60146d6` / `5476a3f2c6bc` / `55d0a1ea9bda`
  (rev12, FROZEN revision 27, mirrored/aligned); L0 `a1674f094979` (unannounced drift, see CF-19);
  L1 `315c19145065`; A0 `d748a9e3574e`; N0 `8b52014dac47`; protocol `1e6cdf04d7a2`;
  `numerics/spherical_solver` absent; lock guard present. Publication: 0 divergent mirror pairs,
  1 companion pair (F0).
- **All five gates are `pending` with hash-bound reasons in `controller_gate_audit`.** Coverage at
  the measured hashes is now zero-to-low everywhere because the rev27 closure voided every rev11
  verdict: F0 0 accepts, F1 0, F2a 0, F2b 0, L0 0 (L0 moved twice in-pass); L1 has 22 independent
  spot checks (≥3 met); G-NUM: C8 is MET (rev3 protocol accept 4.5) and C4 registration is repaired,
  so the only open item is the N0 node verdict (`reviews/N0-review-lead-audit.json` is revise 3.5).
  G-AUDIT: A0 0 accepts, A1 coverage 0/0/0/0/0 (need ≥2 each). Evidence audit: 10 hard CLASSSEP
  findings, all the CF-16 metalinguistic-mention pattern; 0 soft.
- **REC-3/F0:** the F0 canonical/authoring pair is a **companion pair, not a mirror pair** (declared
  taxonomy vs class-contract supplement F0-R). Byte-identical publication is impossible without
  destroying a frozen input; `astra-life02-publish-f0` is closed as impossible-as-written. The
  canonical path stays authoritative for G-F0; the supplement is pinned in FROZEN
  `logical_artifacts` and must be consistency-checked, not byte-identical.
- **Open assignments (pass-04 cards; deadlines wall-clock):** `astra-life04-freeze-hold`
  (lead-formulation, 01:15 — emit the missing rev27 artifact events, then hold),
  `astra-life04-l0-freeze-reconcile` (lead-literature, 01:30 — CF-19 reconciliation),
  `astra-life04-verify-gform-r2` + `astra-life04-verify-gf0-r2` (lead-audit, 02:15),
  `astra-life04-verify-l0-rev3` (lead-literature, 02:00; **pin voided by CF-19**, superseded by the
  reconcile card), `astra-life04-n0-stoprule` (lead-numerics, 02:30, N0-only),
  `astra-life04-n0-verify` (lead-audit, 03:00), `astra-life04-verify-a0` (lead-audit, 02:00).
  Older `astra-life03-close-findings`, `-verify-gform`, `-verify-gf0` and `astra-life01-publish-*`
  are superseded; `astra-life03-repin-claims` (01:30) and `astra-life03-heldout-09` (02:30) stay
  open. Each assignment carries acceptance, falsifier and stop rule in `map.assignments`; CF-12:
  one canonical path, one owner — do not duplicate or repoint.
- **`numerics_lock` remains LOCKED:** N1 queued, `numerics/spherical_solver` absent, guard present.
  N0 is `active/unverified`. Only G-FORM + G-AUDIT pass *plus* a measured and independently
  replicated N0 order releases N1. G-NUM passing would certify N0 only. No solver/N1 work.
- **Resource decisions:** no new approvals this pass. The pass-03 formulation verification pool
  (6.0 h) and literature review pool (3.0 h) are re-pointed at the rev27/rev3 hashes by the pass-04
  cards; the C8 numerics approval (1.0 h) is spent (protocol review delivered). Budgets in the cards
  total 12.5 agent-hours, all from standing group budgets.
- **Findings:** CF-1…CF-16 as before; CF-7/CF-10/CF-13/CF-14 updated, CF-17 (F0 companion
  adjudication), CF-18 (literature/numerics rulings; F2b field report stale), CF-19 (L0 freeze
  breach: ledger rewritten at 00:35:19 to `a1674f094979` with no artifact event after the owner's
  announced exit `3e3d3553`; worker-073 failed closed against the archive). CF-16 now spans
  claims[36,94,96,97,101,112,127,144]. CF-14 partially repaired (colon-bearing resource-request ids
  now bind in `apply_events.py`); 58 future-dated events remain (max 02:00, skew ≈4961 s) — treat
  future `created_at` as advisory for ordering.
- **Authority:** worker events cannot set `status=done`, `validation_status=passed`, or a gate
  verdict. Only the controller and group leads can move those, with artifact + review evidence.
  The controller does not edit another agent's artifact or claim text (CF-4).
- **Checkpoints:** `runtime/state/current_checkpoint.json` and `checkpoint_log.jsonl`;
  `runtime/state/artifact_hashes.json` holds measured hashes and now registers
  `runtime/state/controller_verification/` (numerics C4). Fluent text is never promoted.
- Controller tools for the next pass: `python3 research_map/astra_lifecycle.py --label <label>`
  (locked ingest → apply → repair → audit → checkpoint; emits review coverage, clock discipline, lock
  guard and its own lifecycle record), `python3 research_map/astra_lifecycle_04_events.py` (idempotent
  pass-04 gate/assignment/decision events; re-running skips duplicates), and the decisions record
  above. Note `astra_lifecycle.py` now classifies publication pairs as `mirror` vs `companion`.

## Mission

Own the cosmic-censorship research map and improve epistemic quality before increasing parallelism. The map is the shared state for Human PI, Astra, group leads, and execution agents. Do not claim a theorem, counterexample, or numerical result from fluent text alone.

## Current state (2026-09-11)

- Repository: `swarm-research/ai4math-swarm`
- Branch: `codex/research-map-dashboard`
- Map: `research_map/research_map.json`
- Dashboard: `research_map/research_map.html`
- Validator: `python3 research_map/validate_map.py`
- Current map validation: `VALID`
- Remote status: no project-specific Astra or DeepSeek Flash fleet was found on `ophis-gpu`; existing remote Codex/training processes belong to other work.

## Portfolio

| group | direction | active agents | spent/budget h | ETA | status |
|---|---|---:|---:|---:|---|
| formulation | split WCC/SCC classes and prevent leakage | 6 | 38/160 | 3–6d | active |
| literature | verify theorem scope and citations | 5 | 42/220 | 5–10d | active |
| numerics | spherical Einstein–scalar calibration | 4 | 22/320 | 10–21d | active but blocked by dependencies |
| audit | score correctness, citations, hard failures, IG | 5 | 55/180 | 2–5d | active |

Current totals: 20 active agents, 157 spent agent-hours, 880 budgeted agent-hours, about 18% budget burn. The current dependency critical path is approximately 13–21 calendar days, subject to measured throughput and the numerical implementation gate.

## Hard decisions

1. Keep `AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`, and `AF-WCC-SCALAR-SPH` as separate classes.
2. Do not launch self-gravitating numerics until formulation and audit gates pass.
3. Treat DeepSeek Flash as a breadth executor. Group leads must review class binding, assumptions, falsifier, artifact schema, and citation scope.
4. A completed node requires an artifact and validation evidence. HTTP success, output length, or agent consensus is not completion.
5. Use matched-budget baselines before claiming swarm advantage.

## Immediate queue

- F1: rewrite AF-WCC vacuum schema with exact quantifiers, topology, weighted data class, genericity, `I+`, visibility, and conclusion type.
- F2: write separate C2 and C0 strong-censorship schemas; never use “C0 or C2”.
- L0/L1: turn the literature draft into a primary-source theorem ledger; mark every uncertain citation unresolved.
- A1: re-review F1/F2/L0 with two independent reviewers; reject class leakage and conclusion inflation.
- N0: only after its dependencies pass, implement flat-space scalar-wave test.
- A2: run four-arm equal-budget ablation: one strong model, self-consistency, independent cheap agents, cheap agents plus coordinator.

## Communication contract

Group leads send: `status`, `claim`, `artifact`, `blocker`, `direction_update`, or `resource_request`. Every message names a node ID, class ID where applicable, evidence refs, expected information gain, and next falsifier. Astra sends assignments, budget changes, gates, priority changes, kill/revive events. High-impact scope changes are escalated to the Human PI.

## Startup on a networked remote host

```bash
cd ~/ai4math-swarm
python3 research_map/validate_map.py
# Run the task-specific client after copying its prompt bundle into this repo.
DEEPSEEK_MODEL=deepseek-flash \
DEEPSEEK_ENDPOINT=https://api.deepseek.com/v1/chat/completions \
WORKERS=20 python3 research_map/run_parallel.py
```

For a new controller process, read this file, `research_map.json`, `ARCHITECTURE.md`, and the base `HANDOFF.md` before allocating work.

## Definition of useful progress

Prefer fewer accepted claims with verified scope over many drafts. Track accepted-claim rate, hard-failure rate, citation support, duplication, reviewer agreement, novel accepted coverage, cost per accepted claim, and per-class coverage. If a result fails a gate, record the failure as progress and redirect the budget.
