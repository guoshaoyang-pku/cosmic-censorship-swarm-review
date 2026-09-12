# W047-F0-CONSISTENCY-BIND-03 — F0 companion-pair consistency evidence: unbound pin, and a checker blind to the regularity-binder axis

Worker: `worker-047` (instance `worker-047-20260912T003814-968807`). No assignment card existed in
`comms/inbox/worker-047.jsonl` for this slot, so one bounded class-bound task was self-assigned,
with pre-registered criteria, before measurement. Read-only against every canonical input.

**Class binding:** `AF-WCC-VAC-GEN` (F1), `AF-SCC-C2-VAC-GEN` (F2a), `AF-SCC-C0-VAC-GEN` (F2b);
nodes `F0,F1,F2a,F2b`. The object is the F0 companion pair adjudicated in CF-17/REC-3:
`research_map/formulation_taxonomy.yaml` (declared taxonomy) vs
`artifacts/formulation/formulation_taxonomy.yaml` (class-contract supplement), which the controller
ruled must be *consistency-checked, not byte-identical*.

## Pins (measured at run start; all stable through the run)

| artifact | sha256 (12) |
|---|---|
| `research_map/formulation_taxonomy.yaml` (F0 declared taxonomy, rev5) | `0abb9ed8a961` |
| `artifacts/formulation/formulation_taxonomy.yaml` (F0 class-contract supplement) | `d7419b4e8963` |
| `schemas/af_wcc_vacuum.yaml` (F1, rev12) | `cce9c60146d6` |
| `schemas/af_scc_c2_vacuum.yaml` (F2a, rev12) | `5476a3f2c6bc` |
| `schemas/af_scc_c0_vacuum.yaml` (F2b, rev12) | `55d0a1ea9bda` |
| `artifacts/formulation/evidence/taxonomy_consistency.json` (consistency evidence) | `9e335e9ba1bf` |
| `artifacts/formulation/tools/check_taxonomy_consistency.py` (owner checker) | `de356d999ea3` |

## Method

`check_f0_consistency_bind_047.py` snapshots byte copies of all seven inputs, then runs nine
pre-registered criteria and eight synthetic controls. Sandboxed replays of the owner checker use a
byte-identical directory copy; all mutations happen on synthetic copies inside this task directory.
The instrument fails closed (`exit 2`) on missing inputs, `exit 3` on canonical drift, `exit 4` on
control mis-calibration, `exit 1` on any criterion FAIL.

## Result (report.json, exit 1)

| id | criterion | status |
|---|---|---|
| C01 | each schema's `f0_binding.consistency_evidence_sha256` equals the measured evidence sha256 | **FAIL (x3)** |
| C02 | the evidence artifact pins both compared trees by measured sha256 | **FAIL** |
| C03 | each schema's `declared_f0_sha256` equals the measured taxonomy sha256; paths exist | PASS |
| C04 | owner-checker replay reproduces the committed evidence document | PASS |
| C05 | no canonical input changed during the run | PASS |
| C06 | taxonomy `conclusion.text` binder form agrees with the schema quantifier binder form | **FAIL (x3)** |
| C07 | owner checker flips on a binder-axis-only mutation (pair→r) | **FAIL (blind spot)** |
| C08 | owner checker flips on a tested-axis mutation (`regularity_token` C2→C0) | PASS |
| C09 | evidence lists exactly the shared class set | PASS |

Controls: **8/8 PASS**. Canonical drift: none.

## Findings

- **CB-1 (critical, cross-class).** All three rev12 schemas declare
  `consistency_evidence_sha256: 675a99d0d25b…` while the on-disk evidence measures
  `9e335e9ba1bf…`. Every `f0_binding` therefore points at bytes that are not the bytes on disk. The
  evidence file's mtime is later than the schemas' 00:31:41 stamp, and no artifact event registers
  the rewrite — the same in-place-rewrite pattern as CF-19.
- **CB-2 (critical).** The evidence document asserts `consistent: true` but contains **zero** hex
  tokens: no sha256 of either compared tree, no comparison-time pin. The claim cannot be attributed
  to the pinned taxonomy (`0abb9ed8a961`) and supplement (`d7419b4e8963`), so it is not evidence for
  the G-F0 companion-pair criterion as written.
- **CB-3 (critical, class-bound content divergence).** The canonical taxonomy's `conclusion.text`
  for F1/F2a/F2b still binds the pair `(s,delta)` with `G_{s,delta}` (lines 193–194, 274–275,
  346–347), while the rev12 class schemas bind the tagged regularity index `r in D0` with
  `G_r / X^r_vac(AF)`. The companion pair is therefore **not consistent on the regularity-domain
  axis**, and the repair that retyped D0 in the schemas has not propagated to the declared taxonomy.
- **CB-4 (major, instrument defect).** The owner checker reports
  `CONSISTENT (4 classes, 0 contract-text divergences)` at these bytes. Mutation control C07 rewrote
  the three pair-typed class texts to the schema form and the verdict was **unchanged** — the
  checker's `consistent: true` is blind to the axis on which the pair actually diverges. Control C08
  (regularity token C2→C0) shows the sandbox replay is calibrated and the checker does flip on axes
  it tests. The checker also never records compared hashes, which is why C02 fails.

## Minimal repairs (owner: formulation lead; not performed here)

- **R1** Make `taxonomy_consistency.json` self-binding: record the measured sha256 of both compared
  trees (and the checker's own sha), then re-pin `f0_binding.consistency_evidence_sha256` in all
  three schemas to the measured evidence hash and emit an artifact event for the rewrite.
- **R2** Either repair the canonical taxonomy `conclusion.text` for F1/F2a/F2b to the `r in D0`
  binder (matching the rev12 schemas) or revert the schema binders; additionally extend
  `check_taxonomy_consistency.py` with a binder-axis comparison so the mismatch cannot pass green.
- **R3** Register the evidence file and its rewrites as artifact events so declared pins cannot
  silently age out.

## Falsifier

Falsified if, at the pins in `snapshot/PINS.json`: (a) any schema's
`consistency_evidence_sha256` equals the measured evidence sha256; (b) the evidence contains the
measured sha256 of both compared trees; (c) the taxonomy binder form matches the schema binder form
for F1/F2a/F2b; or (d) the owner checker flips on a pair→r binder-axis mutation. A later file write
alone is not a falsifier.

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-047/f0_consistency_bind/check_f0_consistency_bind_047.py; echo $?
```

## Scope, corroboration, increment, authority

**Corroboration (not the basis of this verdict):** `reviews/F2a-rev12-069.json` HF-069R-3 records the
consistency-evidence pin mismatch for F2a only; predecessor `W047-D0-REPAIR-ACCEPT-02` RA-1/A6
records the taxonomy pair-typed conclusion text. This task re-derives both with an independent
instrument and controls.

**Increment:** cross-class measurement over all three schemas; the unbound-evidence property (C02);
the content-level binder-axis divergence taxonomy↔schemas (C06); and a mutation-controlled proof of
the checker's blind spot (C07) with a calibrated negative control (C08).

**Authority limits:** worker events cannot set gate verdicts, `status=done`, or
`validation_status=passed`. The `review` event emitted with this task is marked
`counts_as_full_schema_verdict: false` — it measures the F0 binding/consistency layer, not the full
class contract. Nothing canonical was edited; all writes are under
`artifacts/worker-047/f0_consistency_bind/`.
