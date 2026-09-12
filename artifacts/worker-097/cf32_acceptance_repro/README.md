# W097-CF32-ACCEPTANCE-REPRO-01 — independent reproduction of CF-32(i) and live-byte materiality check

- **worker:** worker-097 (bounded execution slot; no inbox card existed for this slot)
- **node / gate:** F2b / G-FORM (secondary: F2a)
- **class_id:** `AF-SCC-C0-VAC-GEN` (primary; corpus base), `AF-SCC-C2-VAC-GEN` (secondary)
- **status:** worker evidence only, `unverified`. No gate verdict, no node status, no
  `validation_status=passed`, no canonical write, no ingest.
- **pre-registration:** `PREREGISTRATION.md` (hashed before the measurement run)

## Why this task

Controller finding **CF-32(i)** (pass-08, 01:17): the G-FORM acceptance pipeline is not
reproducible at the rev29/rev13 pins — `artifacts/formulation/tools/run_acceptance.py` exits 3
at preflight because the semantic-escape corpus binds a stale C0 base hash, while
`evidence/acceptance_pipeline_report.json` still records PASS with `union_caught 31/31`.
CF-32 is scheduled into the one authorized rev14 revision (REC-36 item 7). This artifact
reproduces the finding independently and measures the question CF-32 leaves open: **do the
recorded numbers actually transfer to the live canonical bytes, or is the measurement itself
stale?**

## Method (sandbox-only; canonical paths pinned and never written)

1. Pin 13 read-only inputs by sha256 at T0 (snapshots of the small ones under `pins/`).
2. Reproduce `python3 artifacts/formulation/tools/run_acceptance.py`; record exit + stdout.
3. Re-implement the recorded `path = value` / `delete path = None` operation independently,
   apply it to a deep copy of the **live** canonical C0, write fixtures only under
   `sandbox_fixtures/`, and run both stages (`check_class_schema.py --json`,
   `spec_conformance_audit.py`) on every manifest fixture.
4. Control: cross-check the independent parser against `measure_semantic_escape.py
   ::parse_mutation` on all 32 manifest fixtures (31/31 agreement; the tool's parser returns
   `None` for the one indexed-path op — see Finding 3).
5. Compare every live-rebased verdict against the verdict stored in the stale corpus.
6. Re-pin all 13 inputs at T1; empty drift is required for any result to stand.

## Results (all pins stable before/after; `canonical_drift = {}`)

**Finding 1 — CF-32(i) reproduces exactly.**
`run_acceptance.py` → **exit 3**, stdout:
`corpus base 1bb78ce9b357…` vs `current base b2ab6acb2bbe…`.
Stored corpus `semantic_escape_rebased.json#7e44de0e3906` binds rev11 C0; live C0 measures
`b2ab6acb2bbe`; `acceptance_pipeline_report.json#9b7d6c8208d3` still says
`"verdict": "PASS"`, `union_caught 31/31`.

**Finding 2 — the recorded numbers transfer; the defect is the binding, not the measurement.**
Re-basing the same recorded operations onto live C0 yields **zero** per-fixture verdict
changes (`changed_vs_stored = []`):

| stage | stored (rev11 base) | live rebase (rev29 base) |
|---|---|---|
| canonical structural catch | 30/31 | 30/31 |
| worker-06 semantic catch | 11/31 | 11/31 |
| union catch | 31/31 | 31/31 |

The single canonical escape is `struct12_i_plus_completeness_lexical.yaml` (caught by the
semantic stage); generated controls `control_canonical_base` and `control_quoted_phrase` pass
both stages (0 false positives). So the rev14 rebind is a **hash/pinning repair**, and the
acceptance claim itself is reproducible — but it cannot be regenerated from live bytes until
the corpus is regenerated.

**Finding 3 — one manifest mutant is silently dropped by the recorded-op parser.**
`sem18_provenance_overclaim.yaml` records
`provenance.sources[0].role = 'establishes the conclusion of this class'`; the tool's regex
parser does not accept indexed paths, so the corpus carries 31/32 mutants. The exclusion is
recorded in `semantic_escape_rebased.json["unparsed_mutations"]`, but
`acceptance_pipeline_report.json` reports `"total": 31` with no exclusion note. With an
indexed-path parser the manifest is **32/32** and the union still catches **32/32**
(`sem18`: canonical=fail, semantic=pass, union=fail). The rev14 rebind should either extend
the parser or declare the exclusion explicitly in the regenerated report.

**Finding 4 — the pipeline is not fully pinned even after a hash rebind.**
FROZEN rev29 (`815e08079aefbc`) pin-set membership for the pipeline components:

| component | in FROZEN rev29 pin set |
|---|---|
| `artifacts/formulation/tools/run_acceptance.py` | yes |
| `artifacts/formulation/tools/check_class_schema.py` | yes |
| `artifacts/formulation/tools/measure_semantic_escape.py` | yes |
| `artifacts/formulation/evidence/semantic_escape_rebased.json` | yes |
| `artifacts/formulation/evidence/acceptance_pipeline_report.json` | yes |
| `artifacts/worker-06/spec_conformance_audit.py` (stage-2 rule engine) | **no** |
| `artifacts/worker-06/semantic_fixtures/manifest.json` (corpus source) | **no** |
| `artifacts/formulation/evidence/rebased_fixtures/` | **no** |

Also note the read-only inputs `aggregator_pin_check_rev3.json` and
`lead_formulation_lifecycle_07_independent_verify.json` contain the stale digest (historical
records; not rebind targets).

## Control checklist (8/8)

| id | check | result |
|---|---|---|
| C1 | preflight failure reproduced | pass (exit 3) |
| C2 | stale-binding predicate (stored ≠ live, live = rev29 pin) | pass |
| C3 | independent vs tool parser equivalence on the 31 common rows | 31/31, 0 disagreements |
| C4 | generated controls zero false positives | 0/2 rejected |
| C5 | canonical read-only proof (13 inputs re-hashed at T1) | no drift |
| C6 | live union catch full comparison set | 31/31 |
| C7 | stored-vs-live per-fixture verdict delta | empty |
| C8 | hidden manifest mutant caught by union (extended parser) | 32/32 |

## Minimal rebind actions for rev14 item (7)

1. Re-generate the corpus against live C0 `b2ab6acb2bbe` so `base_sha256` matches canonical.
2. Extend the recorded-op parser to indexed paths (`provenance.sources[0].role`) **or** carry
   `sem18_provenance_overclaim.yaml` as a declared exclusion with a reason, and state the
   denominator explicitly (31-parsed vs 32-manifest).
3. Add `spec_conformance_audit.py` and `semantic_fixtures/manifest.json` to the FROZEN pin
   set (and pin the generated `rebased_fixtures/` manifest), so the two-stage pipeline is
   reproducible from pinned bytes.
4. Re-run `run_acceptance.py` to exit 0 and re-issue `acceptance_pipeline_report.json` at the
   new hashes.

## Falsifiers (what would overturn this artifact)

- `run_acceptance.py` exits 0 on the T0 bytes, or the stored corpus already binds live C0.
- Any canonical sha256 differs before vs after the run (would void every number here).
- A per-fixture verdict in `live_rebase.rows` shown to differ from a faithful re-run under the
  pinned tool hashes.
- The indexed-path extension shown to mis-apply `sem18`'s recorded op (it is reported
  separately, labeled `ext__`).

## Files

`PREREGISTRATION.md`, `run_repro.py` (measurement), `report.json` (full machine record),
`run_output.txt`, `pins_t0.json`, `pins/pins_snapshot.json`, `pins/` (input snapshots),
`sandbox_fixtures/` (generated fixtures — no canonical path touched), `SHA256SUMS.txt`.
