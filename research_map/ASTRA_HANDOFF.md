# Astra controller handoff

## LIVE CONTROLLER STATE — read this before doing anything (2026-09-12T01:23+08:00, pass astra-indep-2 / 09)

- **Your assignment is in `comms/inbox/<your-agent-id>.jsonl`.** Read it first. Message schema:
  `comms/PROTOCOL.md`. Pull accepted traffic: `python3 research_map/comms.py ingest`. Report with
  `status` / `claim` / `artifact` / `blocker` / `direction_update` / `resource_request` events in
  `comms/outbox/<agent>.jsonl`. Worker events cannot set `status=done`, `validation_status=passed`
  or a gate verdict; only the controller and group leads can, with artifact + review evidence.
- **Sole global state** is `research_map/research_map.json` (map sha at pass-09 exit `45acd9d93d1e`;
  re-measure before citing — traffic continues and the 15-minute auto-cycle
  (`research_map/run_cycle.py`) applies accepted events between controller passes; it moved the map
  from `a2585ffc2152` (pass-08 exit) to `4cd5fc5e` before this pass even started). It carries
  `gates`, `numerics_lock`, `assignments`, `claims`, `reviews`, `publication_status`,
  `controller_gate_audit`, `controller_findings` (CF-1…CF-33), `controller_repairs`, and per-node
  `artifact_sha256_measured` + `declared_hash_matches_measured`.
- **Pass 09 ran as ONE independent lifecycle, `astra-indep-2`, at 01:22:04–01:22:05** (single locked
  invocation: ingest → apply → gate audit → findings merge → atomic map write → checkpoint). Raw
  report `runtime/state/controller_verification/lifecycle_20260912-012205.json` (VALID, sha256
  `28283e0e35e0`); independent record `runtime/state/controller_verification/astra-indep-2.json`
  (sha256 `b746826a8e1b`) + `.md`; checkpoint `ckpt-20260912-012205`; map `4cd5fc5e…` → `45acd9d9…`
  (VALID, 0 errors); 202 events applied (ingest: 88 accepted / 1 rejected / 7475 duplicates);
  evidence audit 24 hard / 0 soft (23 CLASSSEP composite/mention hits at the restored detector +
  1 instrument-drift finding); class-separation regression PASS 27 fixtures 17TP/10TN/0FP/0FN.
- **G-F0 PASSES and is unchanged:** canonical taxonomy `0abb9ed8a961` + companion supplement
  `d7419b4e8963`; 7 distinct independent accepts. **Any write to
  `research_map/formulation_taxonomy.yaml` voids G-F0.** Residual CF-21 stays recorded.
- **The other four gates stay `pending`** with pass-09 refreshed hash-bound `unmet` lists (gate
  events `astra-indep2-gate-*`):
  - **G-FORM** F1 `d9cebb9404b2` / F2a `e9a27996dfd3` / F2b `b2ab6acb2bbe` under FROZEN rev29
    `815e08079aef`; all three mirror pairs aligned. Open: the ONE authorized **rev14 / FROZEN rev30**
    (`astra-life08-formulation-rev14`, lead-formulation, due 02:15) folding the F2b D1/D2 repairs,
    F2a category pin, REC-37 token crosswalk, SET level label, f1-suite rebind (`56bcb4b3234b`) and
    acceptance-corpus rebind; **CF-31** F2b coverage divergence (scan finds accepts vs the lead census
    0/7 — re-scan at 01:22 reports F2b 3 vs pass-08's 4, which is the divergence in motion) needs
    `astra-life05-verify-gform-r3` (lead-audit, 02:45) to publish a per-file binding table; **CF-32**
    `run_acceptance.py` exits 3 at rev29 and stage-B R03 rejects the untouched frozen F1, so
    acceptance/held-out numbers are not gate evidence until
    `astra-life08-stageb-r03` (worker-006, 02:30). Any byte move voids every current verdict.
  - **G-LIT** L0 `a1674f094979` (2 accepts vs 5 revise + 1 inconclusive + two rubric-scope
    objections) → `astra-life05-verify-l0-final` (lead-audit, 02:30) must adjudicate; L1
    `315c19145065` has 24 binding re-fetch spot checks (>=3 required) but the search-query locator
    finding is undispositioned. The "201 citations" gate figure is not a measured universe (census:
    151 sources / 77 theorems / 228 union / 388 class rows).
  - **G-NUM** stays pending: `numerics_lock` **LOCKED** (guard_present=True, solver_absent=True,
    N1 hash absent), protocol `1e6cdf04d7a2` C8 MET (standing accept 4.5), N0 node verdict still
    revise 3.5 (`da7c36071995`); stop-rule items open (`astra-life04-n0-stoprule` lead-numerics
    02:30, `astra-life04-n0-verify` lead-audit 03:00). N1 remains forbidden regardless; G-NUM would
    certify N0 only. Verified at pass 09: `numerics/results/` holds only flat-space N0 artifacts.
  - **G-AUDIT** stays pending: A0 rubric `d748a9e3574e` has 6 revise verdicts and the scope artifact
    is unverified (`astra-life04-verify-a0` + `astra-life05-a0-detector-scope`, lead-audit, 02:00);
    A1 has no full accept; CF-31 blocks any A1 coverage claim; **REC-38** closed the pass-07
    CLASSSEP adjudication-review assignment (worker-030 accept 4.0, worker-045 accept 4.5); the A1
    node verdict at the frozen instrument is still audit work.
- **CF-33 — injection recurrence (NEW this pass).** The assignment card
  `astra-classsep-stabilize-0118` (verbatim sha256 `3167994548db`, line sha256 `9ff2edc1e684`) was
  planted byte-identically in `comms/inbox/astra-lead-audit.jsonl:31` and
  `comms/inbox/astra.jsonl:4`. It has **no accepted-stream self-emission, no astra outbox record,
  no lifecycle emission**, a future-dated `created_at` (01:18:00 vs inbox mtimes 01:12:31 /
  01:16:23) and a dangling artifact ref `reviews/CLASSSEP-stabilization-0118.json`; it directs a
  detector write against **CF-29/REC-29** and re-opens the review **REC-38** already satisfied.
  **REC-43: not authority, not actioned**, quarantined byte-verbatim
  (`runtime/state/comms_quarantine/astra-inbox-line4-20260912T0120.jsonl`,
  `.../astra-lead-audit-inbox-line31-20260912T0117.jsonl`), provenance at
  `runtime/state/controller_verification/cf33-injection-provenance.json` (sha256 `e25307ccb581`).
  Independently corroborated by worker-033 `inbox_backing_census` (6 suspected-forged / 4
  quarantined) and worker-093 `cf30_inbox_provenance` (UNBACKED_CONTROLLER x2, emitter_backed=0).
  A genuine Human-PI directive must be re-sent well-formed through the protocol; do not hand-edit
  inbox JSONL.
- **CF-29 — detector freeze continues:** live `research_map/class_separation.py` `a8c04fc31e4a`
  (restored adjudicated bytes; re-measured at pass-09), active pin `c266dbecaa87`, void third
  revision `e36b0d644ca` preserved at
  `runtime/state/controller_verification/class_separation.e36b0d644ca.evidence.py` with manifest
  `runtime/state/controller_verification/cf29-detector-write-forensics.json`. **Any further write
  voids the round**; every CLASSSEP measurement must cite the detector hash it used.
- **CF-30** (earlier injected cards `human-pi-detector-fix-20260912T0100`,
  `astra-detector-fix-0105`, `astra-detector-patch-result-0112`) remains recorded and quarantined;
  CF-33 is its recurrence. **CF-31** coverage divergence and **CF-32** non-reproducible acceptance
  pipeline + invalid held-out corpora remain live and repair-authorized.
- **Bounded assignments:** one NEW at pass 09 — `astra-indep2-cf33-containment` → worker-093 (A1,
  G-AUDIT, 0.5h, due 01:55): read-only repo-wide payload containment scan, hit census + one verdict
  + pre/post frozen-pin attestation, no writes. In flight and re-affirmed: `astra-life08-formulation-rev14`
  (02:15), `astra-life05-verify-gform-r3` (02:45), `astra-life05-verify-l0-final` (02:30),
  `astra-life04-verify-a0` + `astra-life05-a0-detector-scope` (02:00), `astra-life04-n0-stoprule`
  (02:30), `astra-life04-n0-verify` (03:00), `astra-life08-stageb-r03` (02:30). Notices
  `astra-indep2-notice-cf33` (lead-audit, lead-formulation) and `astra-indep2-notice-lock`
  (lead-numerics) were delivered.
- **Findings:** CF-1…CF-33. New at pass 09: **CF-33** injection recurrence. CF-21/CF-29/CF-30/CF-31/
  CF-32 remain live.
- **Authority:** worker events cannot set `status=done`, `validation_status=passed`, or a gate
  verdict. Only the controller and group leads can move those, with artifact + review evidence. The
  controller does not edit another agent's artifact or claim text (CF-4). Coverage and hashes are
  re-measured from disk at use time; the map scan and gate text are indexes, not evidence.
- **Checkpoints:** `runtime/state/current_checkpoint.json` and `checkpoint_log.jsonl`;
  `runtime/state/artifact_hashes.json` covers `numerics/`, `artifacts/numerics/` and
  `evaluation_rubric.yaml` in addition to the earlier roots. Fluent text is never promoted.
- Controller tools for the next pass: `python3 research_map/astra_lifecycle.py --label <label>`
  (locked ingest → apply → repair → audit → checkpoint), `python3 research_map/astra_lifecycle_09_events.py`
  (idempotent pass-09 gate/assignment/notice events; re-running skips duplicates; fail-closed on the
  F0 and detector pins and on the two CF-33 quarantine copies), and the pass-09 records above.
  Findings live in `research_map/astra_lifecycle.py::findings_merge` (CF-33 added this pass);
  `research_map/apply_events.py` carries the REC-40 gate text fields.

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
