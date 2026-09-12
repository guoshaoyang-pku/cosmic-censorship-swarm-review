# W067-N0-F0-REBIND-01 — independent re-bind check of the N0 → F0 class pin

**Worker:** worker-067 (bounded execution worker, DeepSeek Flash breadth executor)
**Node / gate / class:** `N0` / `G-NUM` / `AF-WCC-SCALAR-SPH`
**Checked at:** 2026-09-12T00:37:57+08:00
**Verdict:** `REBIND_INERT_FOR_CLASS_MEMBERSHIP` (5/5 controls)
**Authority:** worker-level evidence only. No gate verdict, no node transition, no canonical write, no self-pass.

## Question

The live controller gate reason (`runtime/state/controller_verification/lifecycle_20260912-003316.json`,
G-NUM) names the stop-rule item **"F0 re-bind"** as open: the N0/G-NUM evidence chain pinned the F0
formulation taxonomy at `66bf917bd368…`, which is superseded on disk. Is the current canonical F0
(rev5, `0abb9ed8a961…`) still the same class `AF-WCC-SCALAR-SPH` — i.e. is the re-bind **inert for
class membership**?

No `comms/inbox/worker-067.jsonl` assignment exists; the task was claimed from that live gate reason.

## Method (read-only on every canonical path)

1. Snapshot and hash the current canonical F0 rev5 and the last byte-preserved predecessor
   (`276009f4f63d…`, from `artifacts/worker-060/.../snapshots/`).
2. Extract `classes["AF-WCC-SCALAR-SPH"]` from both; deep-compare the membership-bearing fields
   (`label`, `axes`, `hypotheses`, `exclusions`, `conclusion.type`) plus the non-membership
   `conclusion.text` / `forbidden_inflation`.
3. **Transitivity leg** for the segment with no byte copy (`66bf917b → 565a6e50`): require the
   certified canonical axis block in `artifacts/flash-02/frozen_rebind_report.json` (measured at the
   `565a6e50`-era) to equal the rev5 axes, and the `schemas/taxonomy_cases.jsonl` meta to certify
   `66bf917b → 565a6e50` axis-vector identity (0/4 divergent).
4. Controls C1–C5 below; canonical no-write drift canary; duplicate-YAML-key scan.
5. Inventory every F0 hash occurrence in the N0 chain and classify each as an **active pin** or a
   narrative mention of a superseded hash.

## Result

| field | 276009f4 → rev5 |
|---|---|
| label | equal |
| axes | **equal** (family WCC, matter_model massless_scalar_field, symmetry spherical, asymptotics asymptotically_flat_3p1, regularity_token null, genericity_kind unresolved, conclusion_type weak_cosmic_censorship) |
| hypotheses H1–H4 | **equal** |
| exclusions | **equal** |
| conclusion.type | **equal** (`weak_cosmic_censorship`) |
| conclusion.text | **changed** (set-based `J-(I+)` wording → rev5 single-q tail predicate with comeager set; rev5 explicitly demotes the set-based variant) |
| forbidden_inflation | equal |

- Axes at `66bf917b` = axes at `565a6e50` (certified) = axes at `276009f4` = axes at rev5 (byte
  extraction) ⇒ the class-membership axis vector is invariant across the whole stale-pin segment.
- rev5 still contains exactly the four frozen class ids; the classsep regression is 17/17 leaks,
  10/10 controls, `VERDICT: PASS`; no duplicate YAML keys in either revision.
- `conclusion.text` is the only changed field and is **not load-bearing for N0**: the N0 proposal
  declares `conclusion_type: numerical_evidence` (flat-space calibration sub-case) and asserts no
  class conclusion.

### Controls

| id | control | observed | pass |
|---|---|---|---|
| C1 | mutate `axes.matter_model` in a temp copy — detector must fire | detected | ✅ |
| C2 | mutate `axes.conclusion_type` in a temp copy — detector must fire | detected | ✅ |
| C3 | no-write drift canary over 8 canonical paths | no drift | ✅ |
| C4 | four-class invariant on rev5 | pass | ✅ |
| C5 | `python3 runtime/bin/classsep_regression.py` | 17/17, 10/10, PASS | ✅ |

### Concurrent update (disclosed)

`numerics/tests/n0_gate_proposal.json` was rewritten by the numerics lead **while this check ran**
(observed sha256 sequence `58a175b52fbe → 599f5f729131 → 3124938e683d → b4192221ff7d`, mtime
00:36:37). Its current `class_binding_note` already names `66bf917b → 565a6e50 → 276009f4 →
0abb9ed8a961`, and its chained hash now equals the measured canonical rev5 hash. This check
independently verifies that published re-bind is inert for class membership. The verdict binds to
the chain state `chain_state_sha256 = 050c0517abe9ebb85cf674a904cccc2a8417d1137ca01c2f0216ac7a86b610d1`.

### Residual active stale pins (proposed updates, not applied)

| path | line(s) | stale token | owner |
|---|---|---|---|
| `numerics/protocol/fixed_replication_verdict.json` | 7, 39 | `66bf917bd368…` (chained hash + `provenance.taxonomy_sha256`) | astra-lead-numerics / controller checkpoint |
| `numerics/CONVERGENCE_PROTOCOL.md` | 7 | `research_map/formulation_taxonomy.yaml#66bf917bd368` | astra-lead-numerics |

The `scheme_independence_review.md:272` occurrence and `CONVERGENCE_PROTOCOL.md:159` are narrative
mentions of superseded hashes, not active pins. The N0 proposal file itself is already re-bound.

## Scope limits

- Hypotheses/exclusions were byte-compared `276009f4 → rev5` only; the earlier `66bf917b → 565a6e50`
  segment is certified at axis-vector level (no byte copy of either revision exists in the workspace).
- The independent replication verdict (`fixed_replication_verdict.json`, `binding_status:
  PROVISIONAL`) is a separate stop-rule item and is **not** addressed here.
- The C5 regression writes only to `runtime/state/classsep_regression` (its standard scratch dir).

## Falsifier

Withdrawn if any of: (a) a byte copy of F0 `#66bf917b` or `#565a6e50` surfaces whose
`AF-WCC-SCALAR-SPH` label/axes/hypotheses/exclusions/conclusion_type differ from rev5; (b)
`research_map/formulation_taxonomy.yaml` no longer hashes to `0abb9ed8a961` at read time; (c)
`frozen_rebind_report.json`'s canonical axis block for the target no longer equals the rev5 axes;
(d) the N0 chain is shown to assert the class conclusion text, which would make the rev5
conclusion-text change load-bearing.

## Files

- `check_rebind.py` — `b08b4b412f7281b8f5caf7ca38dd2567eb087acc11591c2fae3cee7c052c7eb1`
- `rebind_check.json` — `22afbea8a137ceb10e65be1f4ccd3cd9cd975ce6986330faeb311372df7e4540`
- `pinned/F0_rev5_0abb9ed8.yaml` — `0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3`
- `pinned/F0_prev_276009f4.yaml` — `276009f4f63dbf838f32f368eed982f5e353d69970ca3227090aed14d26006dc`
