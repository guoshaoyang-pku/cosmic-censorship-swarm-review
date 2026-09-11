# Astra controller handoff

## LIVE CONTROLLER STATE — read this before doing anything (2026-09-12T00:25+08:00, pass astra-lifecycle-03)

- **Your assignment is in `comms/inbox/<your-agent-id>.jsonl`.** Read it first. Message schema:
  `comms/PROTOCOL.md`. Pull accepted traffic: `python3 research_map/comms.py ingest`. Report with
  `status` / `claim` / `artifact` / `blocker` / `direction_update` / `resource_request` events in
  `comms/outbox/<agent>.jsonl`.
- **Sole global state** is `research_map/research_map.json` (map sha at pass end `4fd40d4d1e4f`;
  re-measure before citing — 35+ events were pending at the closing checkpoint and traffic continues).
  It carries `gates`, `numerics_lock`, `assignments`, `claims`, `reviews`, `publication_status`,
  `controller_gate_audit`, `controller_findings`, and per-node `artifact_sha256_measured` +
  `declared_hash_matches_measured`.
- **Pass 03 ran 00:19:58–00:25:10** (three invocations of the idempotent lifecycle tool as traffic
  arrived: `astra-lifecycle-03`, `-03-close`, `-03-final`; then a lock-held resource-decision repair).
  Summary: `runtime/state/controller_verification/astra-lifecycle-03.md`; latest report
  `runtime/state/controller_verification/lifecycle_20260912-002440.json` (VALID, sha256 `d33af1f9653a`);
  repair checkpoint `ckpt-20260912-002510`. Outbox traffic newer than 00:25:10 is un-ingested; the
  next lifecycle pass must apply it.
- **Measured at pass end (re-measure):** F0 canonical `276009f4f63d` vs authoring `c8e979a1eb48`
  (divergent); F1/F2a/F2b `9a8bd4c96800` / `b6123750b37d` / `1bb78ce9b357`, all canonical==authoring,
  FROZEN revision 25 `af24e9c39606`; L0 `ce42d205e761`, L1 `315c19145065`; A0 `d748a9e3574e`;
  N0 `8b52014dac47`; protocol `1e6cdf04d7a2`; `numerics/spherical_solver` absent; lock guard present.
- **All five gates are `pending` with hash-bound reasons in `controller_gate_audit`** (gate records
  re-emitted as `astra-life03-gate-*`). Coverage at the measured hashes: F0 0 accepts (3 revise +
  2 inconclusive); F1 1 accept (lead-audit r2 4.5) + 3 revises with concrete hard findings (duplicate
  YAML keys / future-dated `revised_at`, authoring-tree `class_contract_pointer`, undefined
  `AF_{I+}`, quantifier contradiction); F2a 2 accepts + 2 revises; F2b 4 accepts + 1 revise
  (quantifier domain, F0 pointer does not resolve); L0 3 accepts + 2 revises; A0 1 accept + 2 revises;
  L1 6 independent spot checks (requirement ≥3 met). G-FORM/G-F0 are blocked by unresolved hash-bound
  findings plus F0 publication divergence, not by missing verdict counts.
- **Open assignments (01:30 unless noted):** `astra-life03-close-findings` (lead-formulation, F0 +
  three schemas, 01:30), `astra-life03-verify-gform` + `astra-life03-verify-gf0` (lead-audit, 02:00),
  `astra-life03-repin-claims` (lead-formulation, 01:30), `astra-life03-heldout-09`
  (lead-formulation, 02:30). `astra-life03-close-findings` supersedes the publication-only
  `astra-life01-publish-frozen` and `astra-life02-publish-f0`; older `astra-life01-*` assignments stay
  open through 01:30 and must not be duplicated (CF-12: one canonical path, one owner). Each
  assignment carries acceptance, falsifier and stop rule in `map.assignments`; a message is not a
  result until the artifact hash is recorded.
- **`numerics_lock` remains LOCKED:** N1 queued, `numerics/spherical_solver` absent, lock guard
  `numerics/tests/selfgravity_lock_guard.py` present. N0 is `active/unverified`; the replication
  verdict on disk is PROVISIONAL. Only G-FORM + G-AUDIT pass *plus* a measured and independently
  replicated N0 order releases N1 — a proposal or a G-NUM pass alone does not. C8 review capacity was
  approved at 1.0 h against protocol `1e6cdf04d7a2` (N0-allowed review only, no solver code).
- **Resource decisions (pass 03):** formulation verification 6.0 h approved (00:44 request; the 00:16
  and 00:34 duplicates are superseded), literature 3.0 h approved (two independent L0/L1 reviewers at
  pinned hashes), numerics 1.0 h approved (C8). Note: `apply_events.py`'s approval matcher
  `resource_request\s+(\S+?):` cannot bind request ids containing colons (all formulation ids do), so
  the formulation decision was recorded by the lock-held repair
  `research_map/astra_repair_03_resources.py`; review that regex next pass.
- **Findings:** CF-1…CF-16 as before. CF-13 partially resolved (F0 only divergence remains). CF-14
  open (92 future-dated events, max `02:00`, skew ≈95 min; treat future `created_at` as advisory for
  ordering). CF-16 raw hard count stays until its author rephrases (assigned via
  `astra-life03-repin-claims`; the controller does not edit another agent's claim text). Residual:
  `gates[].unmet` strings still carry pass-02 hash references — current reasons are in
  `controller_gate_audit`.
- **Authority:** worker events cannot set `status=done`, `validation_status=passed`, or a gate
  verdict. Only the controller and group leads can move those, with artifact + review evidence.
- **Checkpoints:** `runtime/state/current_checkpoint.json` and `checkpoint_log.jsonl`;
  `runtime/state/artifact_hashes.json` holds measured hashes. Fluent text is never promoted.
- Controller tools for the next pass: `python3 research_map/astra_lifecycle.py --label <label>`
  (locked ingest → apply → repair → audit → checkpoint; emits review coverage, clock discipline, lock
  guard and its own lifecycle record), `python3 research_map/astra_lifecycle_03_events.py` (idempotent
  pass-03 gate/assignment/approval events; re-running skips duplicates), and
  `python3 research_map/astra_repair_03_resources.py` (idempotent resource-decision repair).

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
