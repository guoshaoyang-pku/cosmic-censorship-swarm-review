# W094G-CF21-SCOPE-PRECISION-01 — CF-21 disposition-scope audit (AF-WCC-SCALAR-SPH)

Bounded execution worker `worker-094`, one class-bound task taken from live state (no inbox card
exists for slot 094). Read-only on every shared/canonical input; the only write is
`run/report.json` under this directory.

## Why this task exists

CF-21 is the live controller finding that `AF-WCC-SCALAR-SPH` declares
`axes.genericity_kind: unresolved` / `genericity_value_status: unresolved_pending_L1` and an
unresolved `H4` while its conclusion asserts a comeager quantifier. It is recorded
`recorded-open`, not discharged, and it is the only unresolved declaration-level finding on a
frozen gate artifact (`G-F0` pass at `0abb9ed8a961`; any write voids the gate).

worker-094's own accepted-stream claims about CF-21 contain a sub-clause that had never been
audited:

> “…the class_scope_adjudication D3 record (line 81) claiming discharge for all four classes is
> therefore unsupported for this class.” — `w094-gencons-20260912T005630-claim-declaration-consistency`
>
> “Therefore CF-21 -- the D3 record ‘confirmed discharged for ALL FOUR classes’ (taxonomy:81) is
> unsupported for AF-WCC-SCALAR-SPH…” — `w094f-cf21rev13-20260912T011015-claim`

A finding that mis-attributes its evidence is a liability for the controller's disposition: if D3
is in fact satisfied for its own scope, then “D3 is unsupported” would trigger an unnecessary D3
re-adjudication, while the real residual (axis/H4 vs conclusion) is unchanged. The task is
therefore to **separate CF-21 into independently measurable sub-claims and issue a scope
correction where one is mis-attributed** — and, while doing that, to measure two evidence
surfaces CF-21's record does not cite: the companion class-contract supplement and the bound
class-separation case corpus.

## Pins (all re-measured before and after the run; 0 drift)

| input | sha256 (prefix) |
|---|---|
| `research_map/formulation_taxonomy.yaml` (F0 canonical, rev5) | `0abb9ed8a961` |
| `artifacts/formulation/formulation_taxonomy.yaml` (companion supplement) | `d7419b4e8963` |
| `schemas/taxonomy_cases.jsonl` (class-separation corpus, rev5-bound) | `ccf7041bd0ff` |
| `artifacts/formulation/VOCAB_ALIASES.json` | `46cd9f1eb534` |
| `artifacts/formulation/evidence/taxonomy_consistency.json` | `9e335e9ba1bf` |
| `numerics/N0_CLASS_BINDING_AUTHORITY.json` | `effd20b0ea09` |
| `numerics/results/flat_wave_convergence_rev3.json` (N0 carrier) | `da7c36071995` |
| prior report `artifacts/worker-094/genericity_consistency/run/report.json` | `10a92ff3c9c1` |
| prior report `artifacts/worker-094/cf21_rev13_recheck/run/report.json` | `629a3232bb84` |

## Result — `CF21_STANDS_D3_ATTRIBUTION_CORRECTED`

Sub-claim decomposition at the frozen bytes (line numbers at the canonical pin):

| id | sub-claim | measured |
|---|---|---|
| C1 | scalar `axes.genericity_kind == "unresolved"` (`:393`) | **true** |
| C2 | scalar `genericity_value_status == "unresolved_pending_L1"` (`:395`) | **true** |
| C3 | `H4` unresolved, not machine-checkable, “must be named before any claim is filed” (`:407`) | **true** |
| C4 | conclusion asserts a comeager quantifier (`:414`) with no machine-readable provisional/blocked marker | **true** |
| C5 | D3's resolution text is scoped to the comeager quantifier in the conclusion text (`:81`) | **true** |
| C6 | D3's text claims a genericity-**notion** discharge | **false** |
| C7 | the scalar conclusion satisfies D3's stated scope (“for a comeager set G of data … chosen before and independently of the data”) | **true** |

**Withdrawn:** the D3 sub-clause of the two prior worker-094 claims
(`w094-gencons-20260912T005630-claim-declaration-consistency`,
`w094f-cf21rev13-20260912T011015-claim`, plus their review/blocker events) is **mis-attributed**.
D3 discharges the *D1/D3 conclusion-wording divergence* — and that divergence is repaired at
rev5. D3 does not claim to resolve the genericity axis, and its text does not say it does. No D3
re-adjudication is needed.

**Not withdrawn — CF-21 core:** the axis/H4-vs-conclusion tension stands (C1–C4 all true). The
correct statement of the residual is therefore narrower and sharper than the earlier text:

> `AF-WCC-SCALAR-SPH` commits its class predicate to a comeager quantifier while its own
> `axes.genericity_kind` and `H4` declare that quantifier's notion unresolved; D3 is neither the
> cause nor the discharge of that tension.

Two new measurements that the CF-21 record did not carry:

- **Supplement does not discharge (C8 false, C9 true).** The companion supplement
  `d7419b4e8963` declares the scalar genericity only as the uniform token `GEN` inside
  `components` plus a qualitative ambient-space hypothesis; it provides no kind/topology/value.
  All four class contracts carry the same `GEN` token, so this is a convention, not a
  scalar-class discharge. There is **no third repair path** via the supplement.
- **The unresolved axis is load-bearing, not stale metadata.** In the rev5-bound corpus
  `schemas/taxonomy_cases.jsonl` (`ccf7041bd0ff`), all 4 scalar rows carry
  `axis_vector.genericity_kind: unresolved` in their statement/axis vector, and 3 of 4 list
  `genericity_kind` in `decisive_axes`; `TC-F0-P15` explicitly files Christodoulou 1999 with
  `genericity_kind=unresolved` and defers the codimension→Baire mapping to L1. The controller's
  “stale metadata” rationale is therefore not supported by the class-separation corpus that
  binds the same taxonomy hash.
- **N0 binding is materially independent but names the inconsistent bytes.** The N0
  class-binding record `effd20b0ea09` and carrier `da7c36071995` both bind
  `research_map/formulation_taxonomy.yaml#0abb9ed8a961`; the carrier contains **0**
  genericity/comeager tokens, so the certified second-order result is unaffected. But any G-NUM
  ratification inherits the residual as a **named binding**, which is a reason to record the
  disposition, not to withhold the numerics evidence.

## Controls (12/12 behaved as pre-registered)

M0 predicate-independence, M1 axis-resolved flip, M2 value-status flip, M3 H4-resolved flip,
M4 comeager-removed flip, M5 blocked-marker flip, M6 supplement-discharge flip,
M7 supplement-uniformity flip, M8 corpus load-bearing count sensitivity, M9 D3-text rewrite
(distinguishes “conclusion wording” from “genericity notion” — proves the correction is
text-measured, not assumed), M10 control-class isolation, M11 pin-drift gate.

## Falsifier

Re-run `audit_cf21_scope.py` at unchanged pins. The audit is falsified if any pinned sha256
differs; if the scalar axis/value-status/H4/conclusion no longer measure as recorded; if D3's
text is shown to claim a genericity-notion discharge; if the supplement is shown to resolve the
kind; if any control departs from its pre-registered expectation; or if the prior worker-094
claims are shown not to carry the D3-unsupported sub-clause. A genuine repair of the scalar
axis/conclusion flips the verdict to `CF21_CORE_NOT_REPRODUCED`, which voids the residual — not
the D3 correction, which is a statement about the prior claim text.

## What this does and does not say

- It asserts no mathematical theorem, no numerical result, and no gate verdict. It sets no node
  status and no `validation_status=passed`.
- It does not re-adjudicate any schema, and it does not edit the taxonomy, the supplement, the
  corpus, the N0 record, the carrier, or any prior claim text (CF-4: the controller does not edit
  another agent's claim text; here the author corrects his own record by issuing a new claim).
- It does not reopen `G-F0`; it measures the frozen bytes the gate passed on.

## Reproduction

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-094/cf21_scope_audit/audit_cf21_scope.py   # exit 0, verdict as above
```
