# Astra lifecycle pass 04 — summary (2026-09-12T00:30–00:38+08:00)

Controller: `astra` (independent session `controller-01`, one control pass then exit).

The idempotent lifecycle tool (`research_map/astra_lifecycle.py`) was invoked three times inside this
one pass as traffic arrived: `astra-lifecycle-04` (00:33:16), `-04-close` (00:36:03), `-04-final`
(00:37:18). Each invocation is the full locked sequence ingest → apply → repair → audit →
checkpoint; the last is the pass end state. One idempotent controller-event script
(`astra_lifecycle_04_events.py`, run twice: gate/assignment batch, then the CF-19 addendum) and three
controller-owned tool repairs ran inside the pass. This is one control pass, not a loop.

## Final state (pass end)

| item | value |
|---|---|
| map sha256 before / after | `4fd40d4d1e4f…` → `3d45be5969ec…` (final invocation) |
| validator | `VALID` |
| gates | G-F0, G-FORM, G-LIT, G-NUM, G-AUDIT all `pending`, hash-bound reasons in `controller_gate_audit` |
| numerics lock | `locked`; `numerics/spherical_solver` absent; lock guard present; N1 hash absent |
| evidence audit | 10 hard (all CLASSSEP metalinguistic mentions, CF-16 pattern), 0 soft |
| classsep regression | PASS (27 cases, 0 fp, 0 fn) |
| checkpoint | `ckpt-20260912-003718`; registry now includes `runtime/state/controller_verification/` (C4) |
| latest lifecycle report | `runtime/state/controller_verification/lifecycle_20260912-003718.json` (sha256 `dae3e6fbda02…`) |
| ingest totals (final invocation) | accepted 19, rejected 0, duplicates 2513, 203 outbox files seen; 127 events applied, 0 demoted |
| clock discipline | 58 accepted events future-dated, max `2026-09-12T02:00:00+08:00`, max skew 4961 s (CF-14 partially repaired) |

## Publication status — FROZEN revision 27 `frozen_at 00:32:59` (wall clock)

| artifact | canonical | authoring | classification | status |
|---|---|---|---|---|
| `schemas/af_wcc_vacuum.yaml` | `cce9c60146d6` | `cce9c60146d6` | mirror | aligned (rev12) |
| `schemas/af_scc_c2_vacuum.yaml` | `5476a3f2c6bc` | `5476a3f2c6bc` | mirror | aligned (rev12) |
| `schemas/af_scc_c0_vacuum.yaml` | `55d0a1ea9bda` | `55d0a1ea9bda` | mirror | aligned (rev12) |
| `research_map/formulation_taxonomy.yaml` | `0abb9ed8a961` | `d7419b4e8963` | **companion** | companion-pinned (REC-3) |

0 divergent mirror pairs; 1 companion pair. The F0 pair is two distinct artifacts (declared taxonomy
+ class-contract supplement F0-R); byte-identity is impossible without destroying a frozen input, so
`astra-life02-publish-f0` is closed as impossible-as-written.

## Gate reasons at pass end (from `controller_gate_audit`)

- **G-F0** — declared taxonomy `0abb9ed8a961` (rev5) with companion supplement `d7419b4e8963`;
  review scan at this hash: 0 accepts (all verdicts at 276009f4/565a6e50/0fcc6a19 are void).
  Withheld pending two independent accepts at the rev5 hash.
- **G-FORM** — F1/F2a/F2b measured `cce9c60146d6` / `5476a3f2c6bc` / `55d0a1ea9bda`, all mirror
  aligned at FROZEN rev27. The rev27 closure repaired the duplicate `revised_at` keys, repointed
  `class_contract_pointer` at the canonical taxonomy, retyped D0 and defined `AF_{I+}`; every rev11
  verdict is void. Zero accepts at rev12 — withheld pending two independent accepts per class.
- **G-LIT** — L1 `315c19145065` has 22 independent spot checks (requirement ≥3 met, bytes unchanged).
  L0 moved twice in-pass: rev3 `3e3d3553` (announced 00:31:30) was overwritten at 00:35:19 by
  unannounced bytes `a1674f094979` (CF-19), so no L0 verdict is binding. Withheld pending the owner's
  freeze reconciliation, then two independent accepts at the reconciled hash.
- **G-NUM** — lock locked (solver absent, guard present). **C8 is MET**: the rev3 protocol review
  (accept 4.5) binds protocol `1e6cdf04d7a2`. C4 registration repaired (registry includes
  `runtime/state/controller_verification/` → `n0_replication_astra_run2_FIXED.json#6542db93eebc`).
  Still pending on the N0 node verdict (`reviews/N0-review-lead-audit.json` is revise 3.5 with open
  stop-rule items). G-NUM passing would certify N0 only; N1 additionally requires G-FORM + G-AUDIT.
- **G-AUDIT** — A0 `d748a9e3574e` zero accepts; A1 coverage at measured target hashes F0 0, F1 0,
  F2a 0, F2b 0, L0 0 (need ≥2 each). CLASSSEP hard findings are the CF-16 metalinguistic pattern
  (claims[36,94,96,97,101,112,127,144]); audit-lead checker calibration is the disposition path.

## Assignments issued this pass (mirrored to inboxes; acceptance + falsifier + stop rule in `map.assignments`)

| assignment | assignee | artifact | deadline | supersedes |
|---|---|---|---|---|
| `astra-life04-freeze-hold` | lead-formulation | FROZEN.json + 3 schemas + F0 taxonomy | 01:15 | astra-life03-close-findings; astra-life01-publish-frozen; astra-life02-publish-f0 (REC-3) |
| `astra-life04-verify-gform-r2` | lead-audit | `reviews/G-FORM-final-verify-r2.json` | 02:15 | astra-life03-verify-gform (rev25 pin) |
| `astra-life04-verify-gf0-r2` | lead-audit | `reviews/G-F0-final-verify-r2.json` | 02:15 | astra-life03-verify-gf0 (276009f4 pin) |
| `astra-life04-verify-l0-rev3` | lead-literature | `reviews/L0-review-rev3-final.json` | 02:00 | astra-life01-l0-revise (rev2 pin) — **pin voided by CF-19** |
| `astra-life04-l0-freeze-reconcile` | lead-literature | `reviews/L0-freeze-reconciliation.json` | 01:30 | supersedes the verify-l0-rev3 pin (CF-19/REC-10) |
| `astra-life04-n0-stoprule` | lead-numerics | `numerics/results/flat_wave_convergence_rev3.json` | 02:30 | — (N0-only, lock-compatible) |
| `astra-life04-n0-verify` | lead-audit | `reviews/N0-review-final-verify.json` | 03:00 | reviews/N0-review-lead-audit.json |
| `astra-life04-verify-a0` | lead-audit | `reviews/A0-review-final-verify.json` | 02:00 | — |

Budgets: 0.5 + 3.0 + 1.5 + 3.0 + 0.5 + 2.0 + 1.0 + 1.0 = 12.5 agent-hours, drawn from the already
approved formulation (6.0 h) and literature (3.0 h) pools and the standing group budgets. No new
resource approval; no N1 allocation.

## Controller rulings recorded (`astra-lifecycle-04-decisions.json`)

REC-3 F0 companion pair; REC-4 literature rev-4 deferral (bounded metadata patch after verdicts);
REC-5 abstract-level evidence sufficient for G-LIT if honestly marked; REC-6 `evidence_url` is the
locator column, `exact_locator` is query-provenance (no hash-moving patch); REC-7 C4 registration
repaired, C8 met, lock unchanged; REC-8 F2b map-field report stale; REC-9 FROZEN rev27 pins are the
review pins; REC-10 L0 freeze breach reconciliation.

## Tooling repairs (controller-owned)

- `research_map/apply_events.py` — resource-request approval matcher tokenizes the full
  whitespace-delimited id, so colon-bearing ids (`…T00:44:00+08:00`) bind; superseded requests are
  never resurrected.
- `research_map/astra_lifecycle.py` — `publication_status` supports `companion` pairs;
  G-NUM reason reads `reviewed_sha256`/`artifact_sha256`, reports C8 met and surfaces the N0 node
  verdict; findings CF-7/CF-10/CF-13/CF-14 updated, CF-17/CF-18/CF-19 added.
- `research_map/audit_evidence.py` — F0 companion pair no longer flagged as dual-tree divergence;
  registry extended to `runtime/state/controller_verification/` (numerics C4).

## Open risks handed to pass 05

0. **Un-ingested traffic** — 169 accepted-stream events were pending at pass exit (00:38); the next
   lifecycle pass must ingest → apply → re-audit before citing any hash in this file.
1. **Moving target (REC-9/CF-19)** — FROZEN rev27 held through pass end, but L0 was rewritten
   unannounced mid-pass. Review dispatch is worth nothing until the L0 reconciliation holds.
2. **Announce-and-hold** — the five rev27 formulation paths still need artifact events at the frozen
   hashes (astra-life04-freeze-hold) before G-FORM/G-F0 verdicts can be recorded.
3. **Clock discipline** — 58 future-dated events remain; authors must stamp wall-clock.
4. **CLASSSEP calibration** — 10 hard findings are the CF-16 false-positive pattern; the checker or
   the claim prose must change before G-AUDIT can pass.
5. No gate passed this pass; all five remain `pending` with hash-bound reasons. `numerics_lock`
   remains LOCKED.
