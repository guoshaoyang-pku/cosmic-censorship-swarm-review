# Astra lifecycle pass 05 — summary (2026-09-12T00:43–00:51+08:00)

Controller: `astra` (independent session, one control pass then exit).

The idempotent lifecycle tool (`research_map/astra_lifecycle.py`) was invoked four times inside this
one pass as traffic arrived and controller repairs landed: `astra-lifecycle-05` (00:43:08),
`-05-close` (00:48:44), `-05-final` (00:49:19), `-05-final2` (00:51:24). Each invocation is the full
locked sequence ingest → apply → repair → audit → checkpoint; the last is the pass-exit state. One
idempotent controller-event script (`astra_lifecycle_05_events.py`) emitted the gate/assignment/
decision batch. This is one control pass, not a loop.

## Headline

**G-F0 is the first gate to pass.** Declared taxonomy `0abb9ed8a961` (rev5) with companion supplement
`d7419b4e8963` under FROZEN rev28 `2f358f6722d9`: 7 accept verdicts from 5 distinct independent
reviewers at the measured hash (worker-025 4.0, worker-038 3.5, deepseek-flash-18 4.0,
deepseek-flash-19 4.0, worker-078), 6/6 disjointness pairs, bytes stable since 00:31:41. F0 promoted
to `done/passed` on artifact + review evidence and re-asserted every pass. Canonical F0 bytes are
frozen: any write voids the gate. All other gates remain `pending` with hash-bound reasons, and
`numerics_lock` remains **LOCKED** (no solver, no N1 work).

## Final state (pass exit)

| item | value |
|---|---|
| map sha256 before → after (final invocation) | `f06d40a8226a…` → `ed28b714464e…` |
| map sha256 at decision / pass exit | `6d3f0f2792a2…` / `ed28b714464e…` |
| validator | `VALID` (after fixing a latent validator base-path bug; see tooling) |
| gates | **G-F0 `pass`**; G-FORM, G-LIT, G-NUM, G-AUDIT `pending` |
| numerics lock | `locked`; `numerics/spherical_solver` absent; guard present; N1 hash absent; N1 queued |
| evidence audit | 20 hard, all CLASSSEP metalinguistic-mention pattern (CF-16); 0 soft |
| classsep regression | PASS (27 cases, 0 fp, 0 fn) |
| checkpoint | `ckpt-20260912-005124` |
| latest report | `runtime/state/controller_verification/lifecycle_20260912-005124.json` (sha256 `45b72957bc52…`) |
| decisions record | `runtime/state/controller_verification/astra-lifecycle-05-decisions.json` (REC-11…REC-21) |
| ingest (final invocation) | accepted 0 / duplicates 4018 / rejected 0; 212 outbox files seen; 173 events applied |
| clock discipline | 51 future-dated accepted events, max `2026-09-12T02:00`, max skew 4115 s (advisory ordering) |
| publication | 3 mirror pairs aligned (F1/F2a/F2b rev12); 1 companion pair (F0); 0 divergent |
| review coverage at measured hashes | F0 5 distinct accepts (7 verdicts), F1 1, F2a 0, F2b 1, L0 1 (worker-075), A0 0 |

## Gate reasons at pass end (from `controller_gate_audit`)

- **G-F0 — PASS.** Canonical taxonomy `0abb9ed8a961`; 5 distinct accepts; F0 done/passed. Residuals
  recorded, not gate criteria: CF-20 evidence-binding repair (case corpus + schema consistency pin),
  CF-21 `AF-WCC-SCALAR-SPH` axis-vs-conclusion mismatch (3 reviewers non-blocking, worker-094 major).
- **G-FORM — pending.** F1/F2a/F2b rev12 `cce9c60146d6` / `5476a3f2c6bc` / `55d0a1ea9bda`, all
  mirror-aligned; coverage F1 1 accept + 4 revise, F2a 0 accepts + 3 revise, F2b 1 accept + hard
  findings. Two reproducible evidence-binding defects at the frozen bytes (36/36 case rows bound to
  superseded `66bf917b`; all three schemas' `consistency_evidence_sha256` stale). Withheld pending
  `astra-life05-evidence-binding-repair` (rev13 + FROZEN rev29) and `astra-life05-verify-gform-r3`.
- **G-LIT — pending.** L0 `a1674f094979` owner-announced rev3 FINAL (build product; REC-13 closes
  CF-19/REC-10); 1 accept (worker-075) + 1 revise at the hash. L1 `315c19145065` unchanged with 23
  spot checks (≥3 met). Withheld pending `astra-life05-verify-l0-final`.
- **G-NUM — pending.** Lock locked; C8 protocol `1e6cdf04d7a2` carries an accept 4.5 contested by two
  revise verdicts on the (re-based) evidence; `astra-life05-gnum-protocol-adjudication` must settle
  the operative verdict. C4 closed by registry repair; `gates.py` re-pinned `fcd1d70991b6`. N0 rev3
  stop-rule deliverable `da7c36071995` exists with four-rung fixed-dt certification and REPLICATED
  replication verdicts, but the N0 node verdict on disk is still revise: G-NUM waits on an N0 accept
  at one hash (`astra-life04-n0-verify`). N1 additionally requires G-FORM + G-AUDIT.
- **G-AUDIT — pending.** A0 `d748a9e3574e` 0 accepts; A1 coverage meets only F0 (5). 20 CLASSSEP hard
  findings are the CF-16 false-positive pattern; `astra-life05-classsep-calibration` must deliver a
  measured TP/FP/FN census + claims-retirement policy. A0 detector-scope defect routed to
  `astra-life05-a0-detector-scope`.

## Assignments issued this pass (mirrored to inboxes; acceptance + falsifier + stop rule in `map.assignments`)

| assignment | assignee | artifact | deadline | h | supersedes |
|---|---|---|---|---|---|
| `astra-life05-evidence-binding-repair` | lead-formulation | rev13 schemas + case corpus + FROZEN rev29 | 01:40 | 1.5 | astra-life04-freeze-hold |
| `astra-life05-verify-gform-r3` | lead-audit | `reviews/G-FORM-final-verify-r3.json` | 02:45 | 3.0 | astra-life04-verify-gform-r2 + audit-r2-*-bindchain |
| `astra-life05-verify-l0-final` | lead-audit | `reviews/L0-review-final-verify.json` | 02:30 | 1.5 | astra-life04-verify-l0-rev3 / reconcile follow-up |
| `astra-life05-classsep-calibration` | lead-audit | `reviews/CLASSSEP-calibration-adjudication.json` | 02:30 | 1.5 | astra-life01-a1-rebind calibration scope |
| `astra-life05-gnum-protocol-adjudication` | lead-audit | `reviews/G-NUM-protocol-r4-adjudication.json` | 02:15 | 1.0 | — (new contest adjudication) |
| `astra-life05-a0-detector-scope` | lead-audit | `evaluation/A0_detector_scope_adjudication.json` | 02:00 | 0.5 | — (A0 scope defect) |

Budgets: 9.0 agent-hours from standing group budgets. **Resource decisions:** literature
`lit-l5-20260912-022` APPROVED 3.0 h for two blind L0 reviewers at `a1674f094979` (re-binds the
unconsumed pass-03 pool; `013` superseded); formulation `…T00:44:00+08:00` APPROVED 6.0 h with the
rev11 pins re-pointed to the repair/verify cards. No new approvals; no N1 allocation.

## Controller rulings recorded (`astra-lifecycle-05-decisions.json`)

REC-11 G-F0 pass + F0 promotion with frozen bytes; REC-12 evidence-binding repair (rev13/rev29) and
rev12 pin voidance; REC-13 CF-19/REC-10 closed by the announced L0 rebuild; REC-14 C4 registry
repair + `gates.py` re-pin; REC-15 protocol-contest adjudication (no controller self-adjudication; N0
node verdict remains with the audit lead); REC-16 CLASSSEP calibration; REC-17 A0 detector scope;
REC-18 controller tool repairs; REC-19 resource decisions (9.0 h + 3.0 h + 6.0 h re-pointed);
REC-20 lock stays LOCKED; REC-21 done-node status protection (CF-25).

## Tooling repairs (controller-owned)

- `research_map/audit_evidence.py` — registry scan roots now cover `numerics/`,
  `artifacts/numerics/` and repo-root `evaluation_rubric.yaml`; `__pycache__`/`.pyc` excluded. Closes
  the C4 gap: protocol `1e6cdf04d7a2`, `artifacts/numerics/n0/lead_4rung_replication.json#a1f04d2a`,
  `numerics/results/flat_wave_convergence_rev3.json` and the A0 rubric are registered.
- `research_map/apply_events.py` — a done node is not demoted by a non-authority status event
  (`status_events_ignored`); fixes F0 promotion being reverted one minute later by the auto-cycle.
- `research_map/validate_map.py` — default base corrected to the repo root; the latent bug made every
  done node with a declared artifact report “missing on disk” (surfaced on the first gate pass).
- `research_map/astra_lifecycle.py` — idempotent `controller_repairs` (F0 promotion re-asserted,
  spurious node-status restore, stale G-NUM pin refresh, tool-repair records); CF-10/CF-15/CF-16/
  CF-19 updated, CF-20…CF-25 added.
- `research_map/astra_lifecycle_05_events.py` — idempotent pass-05 emitter (5 gate records, 6 cards,
  3 decision notices).

## Open risks handed to pass 06

0. **Traffic continues** — the next controller pass must ingest → apply → re-audit before citing any
   hash here. The 15-minute auto-cycle (`run_cycle.py`) applies events between controller passes.
1. **G-FORM repair in flight** — item (1) of the repair already landed (`schemas/taxonomy_cases.jsonl`
   `ccf7041b`, 36/36 rows rebound); schemas + FROZEN rev29 pending. Any schema write voids rev12 pins
   and the audit-r2 sub-cards must stop rather than review moved bytes.
2. **L0** — one accept at `a1674f094979`; the second must be blind to pre-rebuild text. Any ledger
   write voids both.
3. **CLASSSEP** — 20 hard findings remain; G-AUDIT cannot pass until calibration + A0 scope +
   per-target coverage.
4. **Protocol contest** — C8 is not final until `astra-life05-gnum-protocol-adjudication` lands.
5. **Clock discipline** — 51 future-dated events; treat future `created_at` as advisory.
6. **Lock** — only G-F0 has passed; `numerics_lock` LOCKED, N1 queued.
