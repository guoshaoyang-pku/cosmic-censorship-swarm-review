# Astra lifecycle pass 03 — summary (2026-09-12T00:19–00:25+08:00)

Controller: `astra` (independent session `controller-01-20260912T001919-…`, one control pass then exit).

The idempotent lifecycle tool (`research_map/astra_lifecycle.py`) was invoked three times inside this
one control pass because traffic kept arriving mid-pass: `astra-lifecycle-03` (00:19:58),
`-03-close` (00:21:55), `-03-final` (00:24:40). Each invocation is the full locked sequence
ingest → apply → repair → audit → checkpoint; the last is the pass end state. One lock-held
controller repair followed at 00:25:10 (`astra_repair_03_resources.py`, resource-request decisions
only). This is one control pass, not a loop.

## Final state (pass end)

| item | value |
|---|---|
| map sha256 before / after | `4d8291c9a9ae…` → `46ae09f0c32c…` (lifecycle final), then `4fd40d4d1e4f…` after the resource repair |
| validator | `VALID` (re-run after repair) |
| gates | G-F0, G-FORM, G-LIT, G-NUM, G-AUDIT all `pending`, hash-bound reasons in `controller_gate_audit` |
| numerics lock | `locked`; `numerics/spherical_solver` absent; `numerics/tests/selfgravity_lock_guard.py` present; N1 hash absent |
| evidence audit | 1 hard (CF-16 `claims[36]` CLASSSEP false positive), 1 soft (F0 dual-tree divergence) — down from 4 soft at pass 02 |
| classsep regression | PASS (27 cases, 0 fp, 0 fn) |
| checkpoint | `ckpt-20260912-002510` (`runtime/state/artifact_hashes.json` records all measured hashes) |
| latest lifecycle report | `runtime/state/controller_verification/lifecycle_20260912-002440.json` (sha256 `d33af1f9653a…`) |
| ingest totals (final invocation) | accepted 48, rejected 0, duplicates 1497, 179 outbox files seen; 301 events applied, 0 demoted |
| clock discipline | 92 accepted events future-dated, max `2026-09-12T02:00:00+08:00`, max skew 5719 s (CF-14 stays open) |

## Publication status (canonical authoritative) — FROZEN revision 25 `af24e9c39606`

| artifact | canonical | authoring | status |
|---|---|---|---|
| `schemas/af_wcc_vacuum.yaml` | `9a8bd4c96800` | `9a8bd4c96800` | aligned (rev11) |
| `schemas/af_scc_c2_vacuum.yaml` | `b6123750b37d` | `b6123750b37d` | aligned (rev11) |
| `schemas/af_scc_c0_vacuum.yaml` | `1bb78ce9b357` | `1bb78ce9b357` | aligned (rev11) |
| `research_map/formulation_taxonomy.yaml` | `276009f4f63d` | `c8e979a1eb48` | **divergent** (rev4) |

FORM-MAP-PATCH-002 remains superseded; the map is not repointed at the authoring tree.

## Gate reasons at pass end (from `controller_gate_audit`)

- **G-F0** — canonical `276009f4f63d`, 0 accepts (3 revise, 2 inconclusive at this hash); publication
  divergent, so no verdict is transferable between trees. Residual content objection is FROZEN
  manifest churn / future-dated `frozen_at`, not class semantics.
- **G-FORM** — F1/F2a/F2b measured `9a8bd4c96800` / `b6123750b37d` / `1bb78ce9b357`, all aligned.
  Independent verdicts at these hashes now exist: F1 1 accept + 3 revises with concrete hard
  findings (duplicate YAML keys / future-dated `revised_at`, authoring-tree `class_contract_pointer`,
  undefined `AF_{I+}`, quantifier contradiction); F2a 2 accepts + 2 revises; F2b 4 accepts + 1 revise
  (quantifier domain, F0 pointer does not resolve). The obstacle is no longer verdict count but
  unresolved hash-bound findings.
- **G-LIT** — L0 `ce42d205e761` has 3 distinct accepts (plus 2 revises) at the measured hash; L1
  `315c19145065` has 6 independent re-fetch spot checks (requirement ≥3). Ledger class-token flag
  cleared. Gate remains pending only until the accept/revise disagreement is adjudicated at one hash.
- **G-NUM** — lock verified locked (solver absent, guard present); protocol measured
  `1e6cdf04d7a2`; the recorded protocol verdict binds `01b2072434cd` (stale), so criterion C8 is the
  exact unmet requirement. N0 replication verdict on disk remains PROVISIONAL. C8 review capacity
  approved (1.0 h); no N1 work.
- **G-AUDIT** — A0 `d748a9e3574e` has 1 accept + 2 revises; A1 binding coverage at the measured
  hashes remains below two independent verdicts per target until the rev25 round closes.

## Assignments issued this pass (all mirrored to assignee inboxes, acceptance + falsifier + stop rule in `map.assignments`)

| event_id | assignee | artifact | deadline | budget |
|---|---|---|---|---|
| `astra-life03-close-findings` | astra-lead-formulation | F0 + three schema paths | 01:30 | 2.0 h |
| `astra-life03-verify-gform` | astra-lead-audit | `reviews/G-FORM-final-verify.json` | 02:00 | 2.0 h |
| `astra-life03-verify-gf0` | astra-lead-audit | `reviews/G-F0-final-verify.json` | 02:00 | 1.5 h |
| `astra-life03-repin-claims` | astra-lead-formulation | `schemas/taxonomy_cases.jsonl`, `schemas/f1_falsifier_tests.jsonl` | 01:30 | 1.0 h |
| `astra-life03-heldout-09` | astra-lead-formulation | `artifacts/heldout/heldout-09/{manifest,report}.json` | 02:30 | 3.0 h |

`astra-life03-close-findings` explicitly supersedes `astra-life01-publish-frozen` and
`astra-life02-publish-f0` (publication goal landed or folded in), respecting CF-12: each new
assignment names a concrete path that no other open assignment names. `astra-life03-heldout-09` is
sequenced after the closure revision and must use an executor other than worker-16.

## Controller decisions

- Five `gate` records re-emitted with `pending` verdicts and current hash-bound criteria
  (`astra-life03-gate-*`), refreshing `gates[].last_verdict_event` / `updated_at`.
- One `direction_update` for formulation: stop publish/freeze churn; close the hash-bound findings,
  re-freeze once, then stop authoring on these paths.
- Resource requests: `leadform-resource-request-2026-09-12T00:44:00+08:00` **approved 6.0 h**
  (verification round); `lit-l3-20260912-010` **approved 3.0 h** (two independent L0/L1 reviewers);
  `lnum-resource-request-c8-rev3-20260912T002107` **approved 1.0 h** (C8 protocol review at
  `1e6cdf04d7a2`; numerics stays locked). Earlier formulation/numerics duplicates marked superseded.
- Tooling gap recorded: `apply_events.py` matches approvals with `resource_request\s+(\S+?):`, which
  cannot capture request ids containing colons (all formulation ids do). The formulation decision was
  bound by the lock-held repair instead; the regex should be reviewed next pass.

## Honest limitations

- The map was already 35 events behind at the 00:25:10 checkpoint and traffic continues; the next
  controller must ingest/apply before citing any number here.
- `review_coverage` scans `reviews/*.json` only; verdicts living only under `artifacts/…` do not count
  toward its advisory tally (binding coverage remains the audit lead's adjudication).
- `gates[].unmet` strings still carry pass-02 hash references; the current reasons live in
  `controller_gate_audit` (`gates[].last_verdict_event` now points at the pass-03 records).
- Pass 03 did not set any gate verdict, node status, or validation status; all verdicts remain
  evidence-bound to artifacts and reviewers.
