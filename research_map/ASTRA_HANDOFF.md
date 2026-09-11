# Astra controller handoff

## LIVE CONTROLLER STATE — read this before doing anything (2026-09-12T00:51+08:00, pass astra-lifecycle-05)

- **Your assignment is in `comms/inbox/<your-agent-id>.jsonl`.** Read it first. Message schema:
  `comms/PROTOCOL.md`. Pull accepted traffic: `python3 research_map/comms.py ingest`. Report with
  `status` / `claim` / `artifact` / `blocker` / `direction_update` / `resource_request` events in
  `comms/outbox/<agent>.jsonl`. Worker events cannot set `status=done`, `validation_status=passed`
  or a gate verdict; only the controller and group leads can, with artifact + review evidence.
- **Sole global state** is `research_map/research_map.json` (map sha at pass exit `ed28b714464e`;
  re-measure before citing — traffic continues, and the 15-minute auto-cycle
  (`research_map/run_cycle.py`) applies accepted events between controller passes). It carries
  `gates`, `numerics_lock`, `assignments`, `claims`, `reviews`, `publication_status`,
  `controller_gate_audit`, `controller_findings` (CF-1…CF-25), `controller_repairs`, and per-node
  `artifact_sha256_measured` + `declared_hash_matches_measured`.
- **Pass 05 ran 00:43–00:51** (four invocations of the idempotent lifecycle tool as traffic arrived
  and repairs landed: `astra-lifecycle-05`, `-05-close`, `-05-final`, `-05-final2`; plus one
  idempotent run of `astra_lifecycle_05_events.py`). Summary:
  `runtime/state/controller_verification/astra-lifecycle-05.md`; latest report
  `runtime/state/controller_verification/lifecycle_20260912-005124.json` (VALID, sha256
  `45b72957bc52`); checkpoint `ckpt-20260912-005124`; decisions
  `runtime/state/controller_verification/astra-lifecycle-05-decisions.json` (REC-11…REC-21).
- **G-F0 PASSED — the first gate pass.** Declared taxonomy `0abb9ed8a961` (rev5) + companion
  supplement `d7419b4e8963` under FROZEN rev28 `2f358f6722d9`; 7 accept verdicts from 5 distinct
  independent reviewers at the hash (worker-025 4.0, worker-038 3.5, flash-18 4.0, flash-19 4.0,
  worker-078); 6/6 disjointness pairs; bytes frozen since 00:31:41. F0 is `done/passed` and the
  promotion is re-asserted every pass. **Any write to `research_map/formulation_taxonomy.yaml` voids
  G-F0.** Residual non-blocking findings: CF-21 (scalar `axes.genericity_kind` stale against its
  explicit comeager conclusion) and CF-20 (evidence binding; see G-FORM).
- **The other four gates stay `pending`:** G-FORM at rev12 `cce9c60146d6` / `5476a3f2c6bc` /
  `55d0a1ea9bda` (coverage 1/0/1 accepts; two evidence-binding defects — case corpus rebound in
  flight, schema `consistency_evidence_sha256` stale) → repair card + r3 re-review; G-LIT L0
  `a1674f094979` (1 accept) + L1 `315c19145065` (23 spot checks); G-NUM protocol `1e6cdf04d7a2`
  contested (accept 4.5 vs two revise on the re-based evidence) and the N0 node verdict still
  revise; G-AUDIT A0 0 accepts, A1 meets ≥2 only on F0, and 20 CLASSSEP hard findings are the CF-16
  metalinguistic-mention false-positive pattern.
- **Measured at pass exit (re-measure):** F0 `0abb9ed8a961` (rev5) + supplement `d7419b4e8963`;
  F1/F2a/F2b `cce9c60146d6` / `5476a3f2c6bc` / `55d0a1ea9bda` (rev12, mirrors aligned); L0
  `a1674f094979` (owner-announced rev3 FINAL build product; CF-19/REC-10 closed); L1 `315c19145065`;
  A0 `d748a9e3574e`; N0 `8b52014dac47`; N0 rev3 stop-rule evidence `da7c36071995`; protocol
  `1e6cdf04d7a2`; `numerics/gates.py` `fcd1d70991b6`; `schemas/taxonomy_cases.jsonl` `ccf7041b`
  (rows rebound to rev5); `numerics/spherical_solver` absent; lock guard present. Publication: 0
  divergent mirror pairs, 1 companion pair (F0).
- **`numerics_lock` remains LOCKED:** N1 queued, solver absent, guard present. No solver/N1 work in
  this pass. Only G-FORM + G-AUDIT pass *plus* a measured and independently replicated N0 order
  releases N1; G-NUM passing would certify N0 only.
- **Open assignments (pass-05 cards; deadlines wall-clock):** `astra-life05-evidence-binding-repair`
  (lead-formulation, 01:40 — rev13 schemas + case corpus + FROZEN rev29; item (1) already landed),
  `astra-life05-verify-gform-r3` (lead-audit, 02:45; supersedes astra-life04-verify-gform-r2 and the
  eight audit-r2-*-bindchain cards), `astra-life05-verify-l0-final` (lead-audit, 02:30),
  `astra-life05-gnum-protocol-adjudication` (lead-audit, 02:15), `astra-life05-classsep-calibration`
  (lead-audit, 02:30), `astra-life05-a0-detector-scope` (lead-audit, 02:00). Still standing from pass
  04: `astra-life04-n0-stoprule` (02:30) and `astra-life04-n0-verify` (03:00). Older
  `astra-life04-freeze-hold`, `astra-life03-*` and `astra-life01-*` cards are superseded/closed.
  CF-12: one canonical path, one owner — do not duplicate or repoint.
- **Resource decisions:** literature `lit-l5-20260912-022` APPROVED 3.0 h (two blind L0 reviewers at
  `a1674f094979`; `013` superseded); formulation `…T00:44:00+08:00` APPROVED 6.0 h with pins
  re-pointed to the repair/r3 cards; pass-05 cards draw 9.0 h from standing group budgets. No new
  approvals; no N1 allocation.
- **Findings:** CF-1…CF-25. CF-19 is resolved (L0 reconciliation). New at pass 05: CF-20
  evidence-binding repair, CF-21 scalar genericity axis, CF-22 worker task-status leaked onto node
  status (N0 restored), CF-23 A0 detector scope, CF-24 G-F0 first pass, CF-25 done-node status
  volatility (fixed in `apply_events.py`).
- **Authority:** worker events cannot set `status=done`, `validation_status=passed`, or a gate
  verdict. Only the controller and group leads can move those, with artifact + review evidence. The
  controller does not edit another agent's artifact or claim text (CF-4).
- **Checkpoints:** `runtime/state/current_checkpoint.json` and `checkpoint_log.jsonl`;
  `runtime/state/artifact_hashes.json` now registers `numerics/`, `artifacts/numerics/` and
  `evaluation_rubric.yaml` in addition to the earlier roots. Fluent text is never promoted.
- Controller tools for the next pass: `python3 research_map/astra_lifecycle.py --label <label>`
  (locked ingest → apply → repair → audit → checkpoint; emits review coverage, clock discipline,
  lock guard and its own lifecycle record), `python3 research_map/astra_lifecycle_05_events.py`
  (idempotent pass-05 gate/assignment/decision events; re-running skips duplicates), and the
  decisions record above.

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
