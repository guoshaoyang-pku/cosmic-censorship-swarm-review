# Data-class freeze decision packet (F1 / F2a / F2b)

- **Author:** deepseek-flash-05 (execution worker), advisory only
- **Created:** 2026-09-11T23:40+08:00
- **Trigger:** integration probe `C7-shared-data-class` fails; transfer rule T1 is not licensed
- **Owner of the decision:** lead-formulation (with Astra if it changes F1's canonical block)
- **Status:** open; no class is redefined here and no schema is edited by this packet

## The conflict

All three G-FORM schemas pass or are being brought to the frozen FORM-RULE-SPEC v1.1 layout, but
they do not freeze the same data class:

| schema | revision | frozen class | canonical gate | evidence |
|---|---|---|---|---|
| F1 `af_wcc_vacuum.yaml` | 3 | Sobolev values declared (`s = 4`, `delta = 1/2 + epsilon`, `h in H^4_loc`, `K in H^3_loc`), old layout | **fail** R02-R07, R10, R11, R14 | `schemas/af_wcc_vacuum.yaml#7a3e1f93f77c` |
| F2a `af_scc_c2_vacuum.yaml` | 3 | weighted Sobolev `H^4_{1/2+epsilon}`, smooth data as a sub-case | pass R01-R16 | `schemas/af_scc_c2_vacuum.yaml#23fec0e9cd68` |
| F2b `af_scc_c0_vacuum.yaml` | 5 | smooth-with-decay; Sobolev explicitly **not this class** | pass R01-R16 | `schemas/af_scc_c0_vacuum.yaml#cb897b29db12` |

`C7` compares `data_class.regularity_class.selected`, `sobolev_variant.s` and `sobolev_variant.delta`
between the two SCC components. Current output: C2 `weighted Sobolev H^4_{1/2+epsilon}` vs C0
`smooth-with-decay`; `s`: `4` vs `s > 5/2`; `delta`: `1/2 + epsilon` vs `delta in (1/2, 1)`.
Reproduce: `python3 artifacts/worker-05/check_f2_integration.py --report`; report field
`component_findings[C7-shared-data-class]`.

## Why it blocks

- Transfer rule T1 requires an exact data-class and genericity match before any cross-class
  transfer is licensed. With the mismatch, the one-way SCC implication (continuity-class
  inextendibility entails C2-inextendibility) cannot be exercised across the two documents, and
  G-FORM's "one frozen data class" criterion cannot be checked off.
- Both SCC documents individually pass the canonical gate, so this is **not** a defect in either
  revision; it is an unresolved shared choice.

## Options

**Option A — freeze smooth-with-decay.**
- F2a revises: `regularity_class.selected = smooth-with-decay`, Sobolev demoted to
  `sobolev_variant` with `is_this_class: false` (F2b rev5 shows the exact working pattern that
  satisfies R05); F1 revises to the same block while adopting the rule_spec layout.
- Cost: one revision + re-gate + re-review for a document that currently passes; F1's declared
  Sobolev values are discarded.

**Option B — freeze weighted Sobolev `H^4_{1/2+epsilon}` (advisory recommendation).**
- F2b revises: swap `selected` to the Sobolev class, move smooth-with-decay to an explicit
  sub-case, keep the named `s`/`delta` under `sobolev_variant`; F1 adopts the same block in its
  pending rule_spec rewrite.
- Cost: one revision + re-gate + re-review for the C0 component; F2a unchanged; F1's declared
  values are preserved.
- Reasons: (i) F1 already declares these values, so this is the minimal deviation from the
  formulation lead's own proposal; (ii) `H^4_loc` data produce a `C^2` development, which is the
  regularity the F2a conclusion tests, whereas smooth-with-decay is more regular than needed;
  (iii) the C0 conclusion only needs a development regular enough for the extension predicate to
  be well posed, and a Sobolev class is still sufficient for that in the C0 sibling.

## Consequence of no decision

- `C7` stays red; G-FORM stays pending; the SCC sibling ledger remains formally inert.
- No forced deadline from this worker: the aggregator pins both revisions and will keep flagging
  the mismatch without blocking either component's own review.

## Evidence

- `artifacts/worker-05/f2_integration_report.json` (probe `C7-shared-data-class`)
- `artifacts/worker-05/check_f2_integration.py` (probe implementation)
- `artifacts/formulation/rule_spec.json` (R05 named `s`; T1 exact-match requirement is in the
  lead-audit stop rules and `reviews/F2a-review-lead-audit.json`)
- `reviews/F2a-review-lead-audit.json` (reopened rev2 for the disjunctive domain; asks for one
  shared class with F1/F2b)
