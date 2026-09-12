# W040-F1-INDEP-VERDICT-03 — independent rev12 verification

Bounded worker-040 instance `worker-040-20260912T003109-968807` (launched 00:31:09).
No assignment card existed in `comms/inbox/worker-040.jsonl`; one bounded class-bound
task was taken from the open G-FORM queue, non-duplicative with the predecessor
instance's W040-F0-INDEP-VERDICT-01 and W040-F1-INDEP-VERDICT-02 (those bind the
superseded hashes 276009f4 and 9a8bd4c9).

## Task

Independent, hash-bound verification of the canonical F1 schema
`schemas/af_wcc_vacuum.yaml` revision 12 at the live bytes measured at 00:32:02:

    sha256 cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3
    snapshot snapshot_af_wcc_vacuum.cce9c60146d6.yaml   (byte copy, reviewed object)

with declared F0 `research_map/formulation_taxonomy.yaml` 0abb9ed8a961 and the
canonical consistency evidence `artifacts/formulation/evidence/taxonomy_consistency.json`
9e335e9ba1bf. Class binding: AF-WCC-VAC-GEN. Gate: G-FORM.

## Verdict

**revise, score 3.5** — three prior majors resolved, one new major semantic defect and
one binding-hygiene major; two advisories.

Resolved from W040-F1-INDEP-VERDICT-02 at the new hash:

- HF-040-01 `class_contract_pointer` now resolves in the canonical taxonomy
  (`classes.AF-WCC-VAC-GEN`), supplement pointer split into its own field (C03/C04).
- HF-040-02 duplicate `revised_at` keys collapsed; a single non-future stamp at line 8
  precedes the publication mtime (C01/C02).
- HF-040-03 `AF_{I+}` now has an in-schema definitional anchor
  (`i_plus.predicate_abbreviation`) (C07).

Open at rev12:

- **HF-040-04 (major, semantic).** Line 72 asserts "Whole-curve containment
  `gamma([0,T)) subset J^-(q)` is strictly STRONGER and is NOT the predicate of this
  class"; line 213 repeats the impossible justification that the whole-geodesic reading
  "would misclassify a geodesic that starts in the exterior and ends inside the
  black-hole region". For a future-directed causal geodesic and the standard causal past
  `J^-(q)`, tail containment implies whole-curve containment by concatenation (and the
  converse is trivial at `t0=0`): the two readings are equivalent, so neither is strictly
  stronger. Worker-037 already withdrew W037V2-F1 for exactly this reason; the schema
  still cites it as "independently confirmed". Machine evidence: 86,170 comparisons over
  all preorders on 2–4 points with past-closed pasts, **0 divergences**; teeth controls
  fire (712 with non-closed singleton pasts, 2,840 with non-causal sequences). Fix:
  state the past-closure equivalence instead of the strictness claim and delete the
  misclassification example.
- **HF-040-05 (major, hash hygiene).** `f0_binding.consistency_evidence_sha256`
  declares `675a99d0…` while the canonical evidence file now hashes `9e335e9b…`
  (still `consistent: true`). The binding's own rule requires refresh and re-run before
  any gate verdict, so the declared evidence hash no longer resolves at its path.

Advisories: stale attribution of the withdrawn W037V2-F1 blocker (A1); the SET-variant
strictness sentence is not adjudicated here (A2).

## Files

| file | role |
|---|---|
| `run_checks.py` | standalone checker, deterministic, no network; re-runnable falsifier |
| `checks.json` | 14 check records with per-check falsifier, drift guard, findings |
| `verdict.json` | verdict envelope (IDs, hashes, evidence refs, overall falsifier) |
| `instrument_runs.json` | finite-model adjudication + parser/detector controls |
| `entry_hashes.json` | entry/exit live hashes and drift record |
| `snapshot_af_wcc_vacuum.cce9c60146d6.yaml` | reviewed bytes |
| `snapshot_formulation_taxonomy.0abb9ed8a961.yaml` | declared-F0 bytes |
| `snapshot_taxonomy_consistency.9e335e9ba1bf.json` | measured evidence bytes |
| `../../reviews/F1-review-040-rev12.json` | review record for ingest |

No shared artifact was modified. Worker events cannot set `status=done`,
`validation_status=passed`, or any gate verdict; this is advisory worker evidence only.
