# W060-CLASSMIX-CONTENT-INVARIANCE-01 — candidate non-conclusion content rules (PROPOSAL)

- **worker**: `worker-060` (one bounded execution pass)
- **classes**: `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN` (control arm `AF-WCC-VAC-GEN`)
- **node / gate**: `F2a`/`F2b` → `G-CLASSBIND` evidence (advisory)
- **authority**: worker measurement evidence only. No node completion, no
  `validation_status=passed`, no gate verdict, no theorem, no canonical byte written.
- **responds to**: `lead-form-20260912T011509-124` / `-011516-124` — "A stage-2 rule set that
  actually catches informative C2/C0 mutants, re-measured on a fresh held-out corpus".

## 1. Why this rule set, and what it deliberately does not do

`FORM-HELDOUT-10` (worker-084, `815e08079aef` FROZEN rev29 / rev13 pins) measured **union escape
1.0 (0 of 26) on the informative C2+C0 arms**: neither canonical stage reads the mutated axes.
Worker-068 has an in-flight candidate for one axis (`conclusion_freeze_check.py`,
`artifacts/worker-068/polarity12/`, sha256 `511eac2f9763…`): `statement_formal`,
`statement_natural_language`, `conclusion_type`.

This candidate covers the **other ten axes** and does not duplicate that one:

| rule | mutated axis | frozen-base invariant it checks |
|---|---|---|
| `CI-CONTAIN` | `containment-reversal` | E-set order and relation kind in `implication_ledger.extension_class_containment` |
| `CI-SOB` | `sobolev-threshold-lowered` | comparator + value of `sobolev_variant.s` / `.delta` |
| `CI-END` | `end-structure-contradiction` | `topology.end_structure` vs `topology.slice_topology` |
| `CI-DEV` | `development-topology-weakened` | global hyperbolicity asserted and not negated |
| `CI-EXT` | `extension-predicate-weakened` | per-clause presence/negation of `extension_predicate.definition` |
| `CI-SRC` | `source-status-flip` | per-source status vs base + top-level `citation_status` |
| `CI-FALS` | `schema-falsifier-erasure` | `falsifier.schema_falsifiers` guard set content |
| `CI-F0` | `f0-binding-stale-hash` | `f0_binding` declared hashes vs frozen base **and** live bytes |
| `CI-EQUIV` | `equivalence-inflation` | claimed-equivalent entries name the class concept, not a foreign family |
| `CI-OBS` | `known-obstruction-erased` | `known_obstruction` still names Kerr and is not negated |

Design rules: every check is **relative to the pinned canonical base of the fixture's own arm**
(no hard-coded arm thresholds), **base-gated** (an axis absent from the base makes the rule skip,
so the WCC arm is not spuriously flagged), and **semantic** (parsed YAML, not text). Rules were
derived from the class contract and the published family rationales, not from individual mutant
strings; the fresh corpus below is the transfer check for that claim.

## 2. Measured result on the preserved corpus (read-only)

Pins (all re-measured at run time; the runner aborts `exit 2` on any drift):

| item | sha256 |
|---|---|
| `artifacts/heldout/heldout-10/manifest.json` | `d026fec40fe4dab9ae51c51a8fa870337224b973418c0139685cf2f3faa0c236` |
| F1 `schemas/af_wcc_vacuum.yaml` | `d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d` |
| F2a `schemas/af_scc_c2_vacuum.yaml` | `e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe` |
| F2b `schemas/af_scc_c0_vacuum.yaml` | `b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c` |
| `research_map/formulation_taxonomy.yaml` (live) | `0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3` |
| `artifacts/formulation/evidence/taxonomy_consistency.json` (live) | `9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b` |

| population | n | caught | escape |
|---|---:|---:|---:|
| informative arms (C2+C0) | 26 | **20** | **0.2308** |
| all mutants (incl. 7 WCC-arm) | 33 | 20 | 0.3939 |
| controls (3 frozen canonicals + 4 authored) | 7 | — | **0 flagged (0 FP)** |

Per family (informative): every one of the **10 non-conclusion families is caught 2/2**;
`conclusion-polarity-inversion`, `conclusion-content-erasure`, `natural-language-inversion`
are 0/2 — exactly the three families owned by worker-068's in-flight axis. No rule catches
more than its own 2 mutants (per-rule counts: each of the ten rules = 2), i.e. no cross-family
over-firing.

**Union with worker-068's candidate** (`511eac2f9763…`, `--variant freeze_statements`,
invoked read-only): **26/26 informative mutants caught (escape 0.0)** — but the union inherits
**one conforming-control false positive**: `c02_conforming_c0_polished.yaml`. That control's
only conclusion change is a faithful rephrase
(`future-inextendible as a continuous Lorentzian manifold` →
`cannot be extended to the future as a continuous Lorentzian manifold`), which a content-freeze
rule cannot distinguish from `m01`–`m06`. So the clean-union claim at these bytes is
**20/26 with 0 FP (this rule set)**, and the residual 6 require a *semantic* conclusion-axis
check, not a byte-freeze one. `c02` is the concrete falsifier for the freeze variant.

## 3. Fresh transfer corpus (built in-script, not reused from worker-084)

`--selftest` builds 10 mutants with independently worded operators (reversed E-labels,
`s > 2`, "the slice possesses two asymptotically flat ends", "no global hyperbolicity is
assumed", dropped clauses (b)/(f), a different source flipped, four "none" guard entries,
a wrong (not stale) evidence hash, a foreign "future geodesically complete" equivalence, a
"no obstruction is known" claim) plus **10 conforming rephrases** of the same fields
(⊆-nesting, "strictly greater than 5/2", "globally hyperbolic … Cauchy surface",
"if and only if", Kerr restated, reversed guard list, reordered sources, …).

Result: **10/10 mutants caught, 0/10 conforming rephrases flagged.**

## 4. Falsifiers (all re-runnable)

1. Re-run `check_class_content_invariance.py --corpus artifacts/heldout/heldout-10 --live
   --compose-w068 artifacts/worker-068/polarity12/conclusion_freeze_check.py` at the pins above:
   any per-fixture verdict disagreement, or any control flag from this rule set, falsifies.
2. Any *non-conclusion-family* informative mutant that escapes this rule set falsifies the
   family table (currently none).
3. Any conforming control (`c01`–`c04`, the three frozen canonicals, or the 10 fresh rephrases)
   flagged by this rule set falsifies the 0-FP claim.
4. The union's 26/26 is falsified as a *clean* union by `c02`; it becomes a clean 26/26 only
   when the conclusion axis is checked semantically and `c02` passes.
5. `CI-F0` is a live-bytes rule: if `research_map/formulation_taxonomy.yaml` or
   `artifacts/formulation/evidence/taxonomy_consistency.json` moves, the `f0_binding` refresh
   obligation fires and the rule must be re-based in the same revision.

## 5. Limits / non-claims

- This is a **proposal instrument**, independent of stage A (`check_class_schema.py`) and stage B
  (`spec_conformance_audit.py`); it is not wired into `run_acceptance.py` and no FROZEN revision
  was touched. Adopting it needs the owner's pin/decision like any stage-2 rule.
- It checks *class-content invariance against the frozen base*, not mathematics, not physical
  truth, and not the R03 binder defect (out of scope; unchanged and still open).
- The WCC arm is deliberately not covered (its families differ); the 0/7 W-arm figure above is
  `not applicable`, not a detection result.
- `CI-SRC` keys sources by their `concept` string; a source concept rewritten past recognition
  would be treated as a new source (fail-closed to a flag, but the detail would say "new source").
- "20/26" and "26/26 union" are detector measurements on one preserved corpus at fixed pins;
  they say nothing about whether the repaired schemas themselves are acceptable.

## 6. Reproduction

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-060/classmix_content_invariance/check_class_content_invariance.py \
  --selftest
python3 artifacts/worker-060/classmix_content_invariance/check_class_content_invariance.py \
  --corpus artifacts/heldout/heldout-10 --live \
  --compose-w068 artifacts/worker-068/polarity12/conclusion_freeze_check.py \
  --json artifacts/worker-060/classmix_content_invariance/evidence.json
# exit 0 = controls all pass; exit 2 = a control was flagged (instrument invalid)
```

Artifacts: `evidence.json` (full per-fixture rows, union rows, fresh-corpus rows),
`SHA256SUMS`, checkpoint `runtime/state/w060_classmix_content_invariance_checkpoint_1.json`.
