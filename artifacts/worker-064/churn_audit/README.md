# W064-CHURN-01 — publication-stability / binding-consistency audit

Actor: `worker-064`. Node `F0`. Classes: `AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`,
`AF-SCC-C0-VAC-GEN`, `AF-WCC-SCALAR-SPH`. Gate proposed to: `G-F0`.

## What was done

One bounded, read-only measurement: the sha256/size/mtime of the four frozen-class canonical
artifacts, their authoring mirrors, `FROZEN.json` and `VARIANT_REGISTRY.json` were sampled every
5 s for 90 s (18 samples), and each `FROZEN.json` manifest entry and the hashes advertised as
final in `leadform-resource-request-2026-09-12T00:34:00+08:00` were compared per sample.

## Result (report.json)

`verdict = STABLE_FROZEN_BOUND_WITH_BINDING_DEFECTS`

* **F-CHURN-1 stability holds.** All four canonical hashes were constant for the whole window:
  F0 `276009f4f63dbf83`, F1 `9a8bd4c9680042a4`, F2a `b6123750b37d8bee`,
  F2b `1bb78ce9b3572cda`. `FROZEN.json` revision 25 matched all four at 18/18 samples
  (last canonical writes 00:18:26–00:19:14; FROZEN rev25 written 00:19:46).
* **F-CHURN-2 stale advertised pins.** The four hashes advertised as final in
  `leadform-resource-request-2026-09-12T00:34:00+08:00` (also restated in `leadform-blocker-0005`)
  matched the live canonical files in **0/18** samples. Binding to the comms literally binds
  non-canonical bytes — the mechanical cause of the standing blocker "no independent verdict
  binds the FINAL hashes".
* **F-CHURN-3 freeze stamp future-dated.** `FROZEN.json` rev25 `frozen_at = 00:42:00` while its
  own file mtime is `00:19:46` (+1316 s skew vs the window start). Same defect worker-084 flagged
  for rev24 (C1.5); consistent with the controller `clock_discipline` count (72 future-dated
  events, max skew 6133 s).
* **F-CHURN-4 F0 dual-tree divergence persists.** Canonical `research_map/formulation_taxonomy.yaml`
  and authoring `artifacts/formulation/formulation_taxonomy.yaml` diverged in 18/18 samples; the
  three schema mirrors were byte-identical (0/18 divergence).

## Falsifier

Re-run `sample_churn.py` (>= 90 s, 5 s cadence) and check: (a) any canonical hash change with a
constant FROZEN revision falsifies F-CHURN-1; (b) any sample matching all four advertised hashes
falsifies F-CHURN-2; (c) `frozen_at <=` first-sample wall clock falsifies F-CHURN-3;
(d) canonical/authoring F0 byte-identity across all samples falsifies F-CHURN-4.

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-064/churn_audit/sample_churn.py   # appends 18 samples to samples.jsonl
python3 artifacts/worker-064/churn_audit/build_report.py   # rewrites measurements.json, report.json
sha256sum -c artifacts/worker-064/churn_audit/manifest.sha256
```

## Not claimed

No gate verdict, no node completion, no mathematical verdict, no attribution of intent, and no
statement about behaviour outside the 90 s window. Worker events cannot set `status=done` or
`validation_status=passed`; this is reproducible evidence for the controller and the
formulation/audit leads.
