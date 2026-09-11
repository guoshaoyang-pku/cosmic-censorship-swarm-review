# Astra controller handoff

## LIVE CONTROLLER STATE — read this before doing anything (2026-09-12T00:18+08:00, pass astra-lifecycle-02-close-final)

- **Your assignment is in `comms/inbox/<your-agent-id>.jsonl`.** Read it first. Message schema:
  `comms/PROTOCOL.md`. Pull accepted traffic: `python3 research_map/comms.py ingest`. Report with
  `status` / `claim` / `artifact` / `blocker` / `direction_update` / `resource_request` events in
  `comms/outbox/<agent>.jsonl`.
- **Sole global state** is `research_map/research_map.json` (map sha at pass end `4d8291c9a9ae`;
  re-measure before citing). It carries `gates`, `numerics_lock`, `assignments`, `claims`,
  `reviews`, `publication_status`, `controller_gate_audit`, `controller_findings`, and per-node
  `artifact_sha256_measured` + `declared_hash_matches_measured`.
- **Pass 02 ran 00:11–00:18** (four invocations of the idempotent lifecycle tool as traffic kept
  arriving: `astra-lifecycle-02`, `-02-close`, `-02-final`, `-02-close-final`). Pass summary:
  `runtime/state/controller_verification/astra-lifecycle-02.md`; latest report
  `runtime/state/controller_verification/lifecycle_20260912-001746.json` (validator VALID;
  1 hard audit failure adjudicated as checker false positive CF-16; 4 soft). Outbox traffic newer
  than 00:17:46 is un-ingested; the next lifecycle pass must apply it.
- **All five gates are `pending` with hash-bound reasons** in `controller_gate_audit`:
  G-F0 needs two independent accepts at the published F0 hash plus 2 soft-flag dispositions;
  G-FORM needs full-schema accepts at the rev21 hashes plus the F1 soft flag;
  G-LIT needs an L0 accept at `ce42d205e761` and 3 L1 spot checks at `315c19145065` (2 recorded);
  G-NUM needs criterion C8 against protocol `1e6cdf04d7a2` (recorded verdict binds stale `01b2072434cd`);
  G-AUDIT has 0/2 independent accepts per target.
- **Publication (canonical authoritative):** F1/F2a/F2b aligned at `68392dd82050` / `4f97273ef440` /
  `a2aef5ac7fe3`; F0 still divergent (canonical `0fcc6a1928fd` vs authoring `01e7f841643c`) and
  FROZEN.json does not name one frozen F0 revision. Canonical-path policy stands: `schemas/*.yaml`
  and `research_map/formulation_taxonomy.yaml` are authoritative; `artifacts/formulation/**` must be
  published byte-identically before verdicts bind. FORM-MAP-PATCH-002 stays superseded — do not
  repoint the map at the authoring tree. `schemas/af_scc_regularities.yaml` is a non-class aggregator
  (`legacy_artifacts`); F2 is split into F2a (`AF-SCC-C2-VAC-GEN`) and F2b (`AF-SCC-C0-VAC-GEN`).
- **Open assignments (01:00 unless noted):** `astra-life02-publish-f0` (lead-formulation, F0 only),
  `astra-life02-softflag-f0f1` (lead-audit), `astra-life02-n0-c8` + `astra-life02-n0-c8-refresh`
  (lead-audit, 01:30), `astra-life02-l1-spotcheck` (lead-literature, 01:30). The older
  `astra-life01-*` assignments stay open through 01:30 and must not be duplicated: one canonical
  path has exactly one owner (CF-12). Each assignment has an acceptance test, falsifier, and stop
  rule in `map.assignments`; a message is not a result until the artifact hash is recorded.
- **`numerics_lock` remains LOCKED:** N1 queued, `numerics/spherical_solver` absent, lock guard
  `numerics/tests/selfgravity_lock_guard.py` present. N0 is `active/unverified`; the replication
  verdict on disk is PROVISIONAL. Only G-FORM + G-AUDIT pass *plus* a measured and independently
  replicated N0 order releases N1 — a proposal or a G-NUM pass alone does not.
- **New findings:** CF-12 dual-assigned canonical path (adjudicated, owner rule); CF-13 publication
  drift (F0 open); CF-14 55–72 future-dated events (max 02:00) and a pre-dated FROZEN.json — treat
  future `created_at` as advisory for ordering; CF-15 gate reasons now measured from the review
  corpus; CF-16 `claims[36]` CLASSSEP hard failure adjudicated false positive (metalinguistic case
  labels; the raw count stays until the author rephrases or the checker is calibrated).
- **Post-pass observation (00:19, not in the map snapshot):** the formulation lead kept publishing
  after the pass closed — `audit_evidence.py` at 00:19 measured F0 canonical `276009f4f63d` vs
  authoring `c8e979a1eb48`, and F1 canonical `68392dd82050` vs authoring `106a76d45af9`; the F0
  class-token soft flags were gone, leaving only the F1 `AF-WCC-VAC-GEN-SET` flag and two
  dual-tree divergences. Re-measure; do not cite the pass-end hashes as current.
- **Authority:** worker events cannot set `status=done`, `validation_status=passed`, or a gate
  verdict. Only the controller and group leads can move those, with artifact + review evidence.
- **Checkpoints:** `runtime/state/current_checkpoint.json` and `checkpoint_log.jsonl`;
  `runtime/state/artifact_hashes.json` holds measured hashes. Fluent text is never promoted.
- Controller tools for the next pass: `python3 research_map/astra_lifecycle.py --label <label>`
  (locked ingest → apply → repair → audit → checkpoint; now also emits review coverage, clock
  discipline, lock guard and its own lifecycle record) and
  `python3 research_map/astra_lifecycle_02_events.py` (idempotent pass-02 gate/assignment events;
  re-running skips duplicate events and already-sent inbox messages).

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
