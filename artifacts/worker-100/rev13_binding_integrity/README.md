# worker-100 — independent binding-integrity audit at schemas rev13 / FROZEN rev29

Bounded class-bound task taken from the open queue (no assignment card existed in
`comms/inbox/worker-100.jsonl` for this slot). It verifies the **CF-20 evidence-binding repair**
(`astra-life05-evidence-binding-repair`) as independent input to `astra-life05-verify-gform-r3`.

## Scope and authority

- **Read-only on every canonical artifact.** Nothing outside `artifacts/worker-100/` is modified.
- **Worker artifact, `validation_status: unverified`.** A worker cannot set `done`/`passed` or a
  gate verdict; this is measurement evidence for a lead/controller review, not a gate verdict.
- Class binding: `AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH`.
- No theorem, no physics result, no numerical-relativity claim.

## Independence

A **second implementation**. It does not import or execute the formulation lead's checkers
(`check_taxonomy_consistency.py`, `evidence_binding_repair_rev29.py`, `run_gate_tests.py`),
worker-007's rev29 driver, or worker-095's binding probe. Every hash, pointer resolution, corpus
binding and alias mapping is recomputed from the pinned bytes. Mutation controls prove the
instrument fires.

## What was measured (pinned at FROZEN sha256 `815e08079aef…`, revision 29, 50 pins)

| check | result |
|---|---|
| C1 FROZEN rev29 self-consistency | **PASS** — 50/50 declared pins match disk |
| C2 schema revision/class identity | **PASS** — 3/3 schemas revision 13, `class_id` ∈ frozen four, components rebuild the id |
| C3 `f0_binding` hashes | **PASS** — 3/3 bind measured canonical F0 `0abb9ed8a961` and evidence `9e335e9ba1bf` |
| C4 pointer resolution | **PASS** — canonical `class_contract_pointer` resolves at `classes.<class_id>`; supplement pointer resolves at `class_contracts.<class_id>` and is a separately named field |
| C5 case-corpus rebind | **PASS** — 36/36 rows carry `bound_taxonomy_sha_0abb9ed8a961`; meta `taxonomy_ref` binds the canonical F0 bytes; 0 superseded tokens; class ids frozen |
| C6 superseded-hash field sweep | **PASS** — no superseded hash (`66bf917bd368`, `565a6e505188`, `675a99d0d25b`) in any live binding field; remaining occurrences are revision-history prose |
| C8 alias normalization | **PASS** — canonical axis `conclusion_type` tokens resolve to the canonical gate vocabulary via `VOCAB_ALIASES.json` |
| mutation controls | **13/13 mutants detected**; negative control (pre-existing pin drift normalised in memory) passes with zero false positives |
| input drift during run | **none** (before/after sha256 equal for all 8 audited inputs) |

**Result on the CF-20 repair scope: PASS at the measured pins.** The three earlier evidence-binding
defects (stale `taxonomy_cases` binding, stale `consistency_evidence_sha256`, unresolved
`class_contract_pointer`) are repaired and independently reproduced here.

## Residual findings (recorded, not repaired by this artifact)

- **R-4 (major): the FROZEN revision label is not unique.** Three distinct manifests were observed
  under `revision: 29` within one session: `e1a8aaa394eb…` (48 pins, frozen_at 00:54:32),
  `3d9e3d77fd87…` (48 pins, frozen_at 00:55:02, **5/48 pins mismatched disk** and the mismatch set
  moved between consecutive measurements), and `815e0807…` (50 pins, frozen_at 00:57:26, 50/50
  match). Reviewers must bind **sha256, never the revision number.** Observations:
  `snapshot/manifest_observations.json`; census at the settled revision: `snapshot/pin_census.json`.
- **R-3 (note, CF-21 adjacent):** canonical scalar `axes.genericity_kind = "unresolved"` while the
  rev5 conclusion quantifies over "a comeager set G of data". Not a binding defect and not
  discharged here; the F0 bytes are frozen.

## Falsifier

Re-measure at these pins: any declared hash that differs from the measured bytes, any case row
bound to a superseded taxonomy hash, any pointed key that fails to resolve in canonical F0, any
FROZEN rev29 pin that differs from disk, or any hash change between the before/after measurements
is a counterexample to this verdict. A re-run of `audit.py` on the same pins whose per-check
results differ also falsifies it. The audit is time-bounded: the freeze was actively moving during
this session, so the verdict binds only the manifest sha256 recorded in `verdict.json:pins`.

## Reproduce

```bash
cd <swarm-root>
python3 artifacts/worker-100/rev13_binding_integrity/audit.py \
        --out-dir artifacts/worker-100/rev13_binding_integrity
# exit 0 = all checks pass; exit 2 = at least one hard failure; --selftest-only = controls only
```

Files: `audit.py` (harness), `verdict.json` (all checks, pins, falsifier), `controls.json`
(mutation controls), `pins_before.json` / `pins_after.json` (drift guard),
`snapshot/FROZEN.audited.json` + `snapshot/pin_census.json` (durable freeze snapshot),
`snapshot/manifest_observations.json`, `MANIFEST.json` (sha256 of every file here).
