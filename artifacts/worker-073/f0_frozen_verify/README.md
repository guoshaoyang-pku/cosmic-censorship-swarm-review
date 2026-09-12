# W073-F0-FROZEN-VERIFY-01 — independent G-F0 binding verification (worker-073)

One bounded class-bound task: an independent, hash-pinned verification of the F0
artifact **pair** for gate `G-F0`, taken because the live controller gate audit
reported **0 distinct full-schema verdicts at the current F0 hash** and no inbox
card exists for worker-073 (recycled slot).

## What was reviewed (at the pinned hashes)

| role | path | sha256 (measured) |
|---|---|---|
| declared F0 taxonomy | `research_map/formulation_taxonomy.yaml` | `0abb9ed8a96135c9…` |
| class-contract supplement | `artifacts/formulation/formulation_taxonomy.yaml` | `d7419b4e8963cb71…` |
| pin manifest (rev 28) | `artifacts/formulation/FROZEN.json` | `2f358f6722d92062…` |

Hashes were frozen before the run and re-measured after; the script aborts with
exit 3 on a mid-run move (the assignment's moving-target stop rule). Both stayed
stable.

## Result

- **19/19 pre-committed mechanical criteria pass** at the pinned hashes (four
  frozen class ids; per-class completeness; single-q tail visibility predicate;
  explicit comeager quantifier in all four conclusions; no merged C0/C2 token in
  any quantified/classification slot; six disjointness pairs; no duplicate YAML
  keys; no YAML 1.1 bool coercion; clock discipline; pin agreement).
- **4/4 positive controls fired.** Controls inject a duplicate key, a merged
  `C0 or C2` conclusion type, a missing comeager quantifier, and a missing
  disjointness pair — each is detected by the matching criterion, so the passes
  above are not vacuous.
- **Verdict: `revise`, score 3.5** — one blocking content objection, `F0V-S1`:
  `AF-WCC-SCALAR-SPH` declares `axes.genericity_kind: "unresolved"` while its own
  conclusion quantifies over an explicit comeager set, and the file's
  `field_vocabulary` rule requires a generic-quantified claim to name
  `genericity_kind` **and** `genericity_topology`. `comeager` is exactly
  `baire_residual`; the two fields disagree. (The lead-audit's
  `reviews/G-F0-final-verify.json` records the same defect as open objection
  `O-GF0-1`; it was reached here independently.)
- `F0V-S2` is recorded as an **adjudication, not a defect**: the assignment's
  `canonical == authoring == FROZEN pin` criterion does not hold byte-wise and,
  per FROZEN rev28 `path_policy`, is not intended to hold — the two paths are
  declared distinct logical artifacts. Both are pinned and the pins agree.

## Independence

worker-073 authored none of the reviewed bytes and imports no artifact under
`artifacts/formulation/` or `research_map/`. Parsing, duplicate-key detection
(a `SafeLoader` subclass that refuses duplicate keys and reports line numbers),
the merged-regularity regexes and all controls are re-implemented in
`run_check_073_f0.py`; PyYAML is the only dependency. This is a separate verdict
from `reviews/G-F0-final-verify.json` (astra-lead-audit), which explicitly
declares `counts_as_full_schema_verdict: false`.

## Files

| file | role |
|---|---|
| `run_check_073_f0.py` | the checker (self-contained; fail-closed on hash move) |
| `report.json` | machine-readable verdict, checks, findings, controls |
| `report.json.sha256` | artifact hash |
| `run_stdout.txt` | exact bytes printed by the run |

Reproduce:

```bash
python3 artifacts/worker-073/f0_frozen_verify/run_check_073_f0.py
```

## Scope / non-claims

Binding and completeness verification only — no physics claim, no theorem, no
counterexample, no gate verdict, no node status, no `validation_status` change.
Worker events cannot set those; this artifact is a proposal with evidence.
Intermediate self-corrections (frame revision 1 → 2, and three detector bugs
fixed during the control round) are recorded in `report.json`
(`pins.frame_commitment.frame_note`) rather than hidden, because a checker that
silently changes its own criterion set is not evidence.
