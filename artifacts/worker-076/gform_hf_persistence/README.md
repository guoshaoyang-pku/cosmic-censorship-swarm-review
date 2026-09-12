# W076-GFORM-HFBIND-01 — G-FORM hash-rebind + named-hard-failure persistence probe

Worker: `worker-076` (100-slot independent lifecycle, second instance 00:16:57).
Node: `F2` (F2a/F2b), gate `G-FORM`. Classes: `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`
(supporting: `AF-WCC-VAC-GEN` for the F1 pin table).
No assignment card existed in `comms/inbox/worker-076.jsonl`; the task was self-proposed
under the ASTRA_HANDOFF startup rule as one bounded class-bound task.

## Question

The map's `G-FORM.unmet` still pins F1 at `7a3e1f93`, F2a at `23fec0e9`, F2b at `e6b1af2b`
and F2 at the retired merged artifact, and names four hard failures (HF-A1, HF-A2, HF-B1,
HF-B2). The canonical tree was republished at ~00:16 and rewritten again at 00:19:14.
**Do the pins and the four named hard failures still describe the live bytes?**

## Method (read-only, deterministic)

`probe_gform_hf_bindings.py`:

1. sha256 of `research_map/formulation_taxonomy.yaml`, `schemas/af_wcc_vacuum.yaml`,
   `schemas/af_scc_c2_vacuum.yaml`, `schemas/af_scc_c0_vacuum.yaml` before **and** after
   the run; a stable window is required for the result to bind.
2. hash pins harvested from `map.gates[*].unmet`, `map.publication_status`,
   `map.frozen_artifacts`, `runtime/state/artifact_hashes.json`, classified
   MATCH / MATCH_PREFIX / STALE_OR_UNKNOWN.
3. named-hard-failure detectors at the measured revision:
   * HF-A1 `extension_predicate` referenced but never defined (F2a)
   * HF-A2 `conclusion.statement_formal` over undefined `D0`/`D_gen` (F2a)
   * HF-B1 merged-class text (`C0 or C2`) outside the lint block (F2b), with the
     occurrence classified LINT_BLOCK / NEGATED / QUOTED_FORBIDDEN / ASSERTED
   * HF-B2 `node_id` vs filename-derived and map-assignment node (F2b)
4. seven calibration controls (positives must fire, negatives must not). If any control
   fails, `controls_ok=false` and the measurement is void.

## Result at the measured revision (stable across the run)

| item | live sha256 (00:19:14 mtime) | finding |
|---|---|---|
| F1 `schemas/af_wcc_vacuum.yaml` | `9a8bd4c96800…` | map pin `7a3e1f93` stale |
| F2a `schemas/af_scc_c2_vacuum.yaml` | `b6123750b37d…` | HF-A1 **repaired**, HF-A2 **repaired** |
| F2b `schemas/af_scc_c0_vacuum.yaml` | `1bb78ce9b357…` | HF-B1 signature **not reproduced** (2 hits, both NEGATED), HF-B2 **repaired artifact-side** |
| F0 `research_map/formulation_taxonomy.yaml` | `276009f4f63d…` | divergent from authoring tree at `publication_status` |

* `named_hard_failures_persisting = 0/4`, `explicitly_repaired = 3/4`,
  `stale_or_unknown_pins = 6/17`, `controls_ok = true`, hash-stable across the run.
* Residual: the map assignment for both F2a and F2b paths is node `F2` while the artifacts
  declare `F2a`/`F2b`; whether the map or the artifact convention moves is a lead decision.
* Hash churn observed inside a ~2-minute window (three different sha256 readings for the
  same F1/F2a/F2b paths), so review verdicts bound before 00:19:14 no longer bind the live
  artifact. Re-pinning is a controller/lead action; this worker cannot move map state.

## Reproduce

```bash
python3 artifacts/worker-076/gform_hf_persistence/probe_gform_hf_bindings.py
sha256sum artifacts/worker-076/gform_hf_persistence/probe_result.json
```

## Falsifier

Re-run and find (a) any measured hash differing from `measured_canonical`, (b) any control
failing, or (c) a hard-failure verdict opposite to `hard_failures` at the same hash.
Substantively: a reviewer exhibits a still-dangling `extension_predicate` (HF-A1), an
undefined `D0`/`D_gen` in the conclusion (HF-A2), an ASSERTED merged-class hit (HF-B1), or
a `node_id` mismatch against the filename-derived node (HF-B2).

## Limits / claims not made

Textual/structural probe, not a schema review: a REPAIRED verdict means the detector
signature is gone, not that the artifact is acceptable. Valid only for the sha256 values in
`measured_canonical`. Worker event: no `status=done`, no `validation_status=passed`, no gate
verdict, no theorem, no physics claim.
