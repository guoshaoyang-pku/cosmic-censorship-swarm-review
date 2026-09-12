# W060-LFORM04-STALE-BINDING-MATERIALITY-01

- actor: `worker-060`; class `AF-WCC-VAC-GEN`; node `F1`; gate `G-FORM`
- created_at: 2026-09-12T01:05:53+08:00
- run status: **VALID**
- H1 (L-FORM-04a, mechanical stale binding): **CONFIRMED**
- H2 (L-FORM-04b, materiality): **MATERIAL**

## Measured pins

| input | sha256 (12) | mtime |
|---|---|---|
| `schemas/af_wcc_vacuum.yaml` | `d9cebb9404b2` | 2026-09-12T00:53:40+08:00 |
| `schemas/f1_falsifier_tests.jsonl` | `56bcb4b3234b` | 2026-09-12T00:32:31+08:00 |
| `artifacts/formulation/FROZEN.json` | `815e08079aef` | 2026-09-12T00:57:26+08:00 |
| `research_map/research_map.json` | `5ab4bed18107` | 2026-09-12T01:05:09+08:00 |
| `artifacts/worker-060/rev29_binding_acceptance/snapshots/f1__af_wcc_vacuum.cce9c60146d6.yaml` | `cce9c60146d6` | 2026-09-12T00:32:02+08:00 |

## Verdict rules (fixed before run)

- **H1**: CONFIRMED iff H1a-H1c all pass and controls pass.
- **H2**: MATERIAL iff >=1 probe flip at rev13, >=1 direction-bearing deciding delta, >=1 deciding field missing at rev13, or >=1 recorded pass not reproducible at the bound rev12; else IMMATERIAL_PROBE_STABLE.
- **controls**: any K failure -> run INVALID.

## Material rows (rebind + re-adjudication required)

- `F1-AMB-11` deciding=`visibility.definition` reasons=['DIRECTION_BEARING_DELTA'] delta_leaves=['visibility.definition'] true_rev13_flips=0 nonreproducible_at_rev12=0 excerpt_drift=[]
- `F1-AMB-17` deciding=`visibility.definition` reasons=['DIRECTION_BEARING_DELTA'] delta_leaves=['visibility.definition'] true_rev13_flips=0 nonreproducible_at_rev12=0 excerpt_drift=[]
- `F1-AMB-23` deciding=`class_identity_variants` reasons=['DIRECTION_BEARING_DELTA'] delta_leaves=['class_identity_variants[0].relation', 'visibility.definition'] true_rev13_flips=0 nonreproducible_at_rev12=0 excerpt_drift=['class_identity_variants']
- `F1-AMB-25` deciding=`f0_binding.declared_f0_sha256` reasons=['DIRECTION_BEARING_DELTA', 'RECORDED_PASS_NONREPRODUCIBLE_AT_BOUND_REV12'] delta_leaves=['class_identity_variants[0].relation', 'f0_binding.binding_note'] true_rev13_flips=0 nonreproducible_at_rev12=2 excerpt_drift=['class_identity_variants', 'f0_binding.binding_note', 'f0_binding.declared_f0_sha256']

## Findings

- True rev12->rev13 probe flips: **0**; recorded passes not reproducible at the declared rev12 binding: **2** (row F1-AMB-25: expected F0 hash `276009f4f63dbf83` vs actual `0abb9ed8a961`, and `binding_note` no longer contains `astra-classscope-02`).
- 15 recorded probe excerpts across 10 rows no longer occur in the live values (including `class_identity_variants`, `visibility.definition`, `f0_binding.*`, `adjudication_queue.open_rows`, `l1_ledger_refs`).
- The stale hash pointer is therefore not the only defect: at least one row's recorded verdicts were never re-derived after the 00:32:31 rev11->rev12 rebind (`rebound_at` on all 25 rows). A hash-only rebind to rev13 would carry that defect forward.
- Direction-bearing rev12->rev13 leaves with no row currently deciding on them: `quantifiers.domains.D5.definition` (census only).


## Stale-binding-only rows

`F1-AMB-01`, `F1-AMB-02`, `F1-AMB-03`, `F1-AMB-04`, `F1-AMB-05`, `F1-AMB-06`, `F1-AMB-07`, `F1-AMB-08`, `F1-AMB-09`, `F1-AMB-10`, `F1-AMB-12`, `F1-AMB-13`, `F1-AMB-14`, `F1-AMB-15`, `F1-AMB-16`, `F1-AMB-18`, `F1-AMB-19`, `F1-AMB-20`, `F1-AMB-21`, `F1-AMB-22`, `F1-AMB-24`


## Checks

| id | pass | expected | observed | falsifier |
|---|---|---|---|---|
| M1 | True | 64-hex sha256 present | "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d" | Live F1 file unreadable (sha256 None). |
| M2 | True | d9cebb9404b2 prefix | "d9cebb9404b2" | Live F1 hash equals rev12 or some third value, invalidating the supersession premise. |
| M3 | True | cce9c60146d6 | "cce9c60146d6" | Snapshot hash differs from the row binding, so rev12 re-execution would test the wrong bytes. |
| M4 | True | >=2 witnesses == cce9c60146d6 | "3 agree of 3" | Fewer than two independent witnesses: the rev12 bytes rest on a single (self-owned) snapshot. |
| M5 | True | pins match measured live hashes | {"pinned_f1": "d9cebb9404b2", "measured_f1": "d9cebb9404b2", "pinned_suite": "56bcb4b3234b", "measured_suite": "56bcb4b3234b", "frozen_revision": 29, "frozen_at": "2026-09-12T00:57:26+08:00"} | FROZEN pins diverge from measured live bytes: the freeze is already broken. |
| M6 | True | 815e08079aef | "815e08079aef" | FROZEN.json changed after pass-05 recorded it, so rev29 is no longer the frozen revision under test. |
| M7 | True | 25 | 25 | Row count differs from the blocker text; the blocker is then misdescribed. |
| H1a | True | single binding == cce9c60146d6 | {"schemas/af_wcc_vacuum.yaml#sha256:cce9c60146d6a907": 25} | Any row binds another revision, or rows disagree, falsifying the uniform-staleness claim. |
| H1b | True | differ | {"bound": "cce9c60146d6", "live": "d9cebb9404b2"} | Bound hash equals the live hash: no staleness, L-FORM-04a is false. |
| H1c | True | suite pinned with superseding F1 in one freeze | {"frozen_revision": 29, "f1_pin": "d9cebb9404b2", "suite_pin": "56bcb4b3234b", "rows_bound_to": "cce9c60146d6"} | Suite not pinned in rev29, or pins a different F1: the blocker's freeze claim fails. |
| SNAP | True | 4 copies byte-identical | ["f1_rev12", "f1_rev13", "frozen_rev29", "suite_rev29"] | Any snapshot hash mismatch voids durable re-verification. |
| D1 | True | delta list recorded | {"all": ["class_identity_variants[0].relation", "f0_binding.binding_note", "f0_binding.checked_at", "f0_binding.consistency_evidence_sha256", "quantifiers.domains.D5.definition", "revised_at", "revision", "revision_histo | No delta at all between rev12 and rev13, falsifying that rev13 changed deciding semantics. |
| B1 | False | 0 mismatches | {"mismatches": [{"test_id": "F1-AMB-25", "probe_index": 0, "path": "f0_binding.declared_f0_sha256", "recorded": true, "recomputed": false, "observed_prefix": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c627909 | Any mismatch means the suite's own records are not reproducible at its declared binding. |
| C1 | True | flips recorded | {"true_rev13_flips": [], "nonreproducible_at_bound_rev12": [{"test_id": "F1-AMB-25", "probe_index": 0, "path": "f0_binding.declared_f0_sha256", "kind": "equals", "expected": "276009f4f63dbf838f32f368eed982f5e353d69970ca3 | Executing a stored probe against both revisions must be possible; a silent skip would invalidate the run. |
| C2 | True | 0 missing paths | [] | A missing deciding path at rev13 is direct evidence of material drift. |
| D2 | True | classification table produced | {"material": ["F1-AMB-11", "F1-AMB-17", "F1-AMB-23", "F1-AMB-25"], "stale_only": ["F1-AMB-01", "F1-AMB-02", "F1-AMB-03", "F1-AMB-04", "F1-AMB-05", "F1-AMB-06", "F1-AMB-07", "F1-AMB-08", "F1-AMB-09", "F1-AMB-10", "F1-AMB- | If no row is materially exposed, the stale binding is a documentation defect only. |
| H2 | True | MATERIAL iff >=1 row exposed | {"verdict": "MATERIAL", "material_rows": ["F1-AMB-11", "F1-AMB-17", "F1-AMB-23", "F1-AMB-25"]} | All 25 rows re-derive identically at both revisions and decide on unchanged leaves: L-FORM-04b would then be falsified as immaterial (documentation-only). |
| K | True | K1,K1b,K2,K3,K4,K5,K6 true | {"K1_rebind_positive": true, "K1b_hash_only_rebind_insufficient": true, "K2_detector_no_false_fire": true, "K3_probe_executor_live": true, "K4_drift_detected": true, "K5_stable_row_reproduces": true, "K6_kind_semantics": | Any failed control voids the run (INVALID), never a silent pass. |

## Controls

- `K1_rebind_positive`: pass=True — hash predicate can return true for a correct rebind
- `K1b_hash_only_rebind_insufficient`: pass=True — candidate rebind of MATERIAL rows still requires re-adjudication of deciding fields
- `K2_detector_no_false_fire`: pass=True — identical docs yield zero delta
- `K3_probe_executor_live`: pass=True — planted token removal for F1-AMB-01 path=non_vacuity.condition expected='future geodesically incomplete' flips the probe to fail
- `K4_drift_detected`: pass=True — single-byte mutation changes sha256
- `K5_stable_row_reproduces`: pass=True — ['F1-AMB-01']
- `K6_kind_semantics`: pass=True — path_exists/nonnull semantics pinned on a synthetic doc

## Falsifier of this report

Re-measure: if schemas/f1_falsifier_tests.jsonl is rebound to the live F1 hash and its deciding-field probes re-adjudicated (esp. visibility.definition and class_identity_variants), H1 becomes historical and H2's material rows close. If instead live F1 reverts to cce9c60146d6 while the suite stays at 56bcb4b3, H1 is void. Any future change to FROZEN.json, the suite, or schemas/af_wcc_vacuum.yaml requires re-running this verifier; hashes above are the only pins.

## Limitations

- Materiality is judged from stored probe text and JSON-path deltas; it does not re-adjudicate the mathematical reading of the changed leaves (that is the formulation lead's authority).
- Row classifications bind only the measured hashes in inputs/snapshots.
