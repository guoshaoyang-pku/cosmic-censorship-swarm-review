# worker-091 checkpoint — F0 rev5 named-blocker re-verification

- **Task**: re-test the named F0 blocking findings (K1a/K1b/K2/K3/K4/K5/K6) at the canonical F0
  revision published 2026-09-12T00:31:41+08:00, closing the falsifier recorded by the previous
  worker-091 run (`artifacts/worker-091/f0_blocking_verify/results.json`, revise 3.5 at `276009f4`).
- **Node / gate / classes**: F0 / G-F0 / `AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`,
  `AF-SCC-C0-VAC-GEN`, `AF-WCC-SCALAR-SPH`.
- **Verdict**: **accept, 4.0** — no blocking content defect among the measured items at the pinned hash.
- **Reviewed bytes**: `f0_rev5_snapshot.yaml` sha256 `0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3`
  (36 372 B), byte-identical to `research_map/formulation_taxonomy.yaml`; pre/post digests equal; no
  measured input drifted during the run.
- **Reproduce**: `python3 verify_rev5.py` (exit 0; exit 3 = UNMEASURED on drift/integrity failure).

| check | item | status at rev5 |
|---|---|---|
| K0 / K0-post | snapshot + no drift | CONFIRMED / no drift |
| K1a | canonical `0abb9ed8` != authoring `d7419b4e` | CONFIRMED_FACT — declared two-artifact split, not undeclared drift |
| K1b | mirror discharge by overwriting | PENDING controller adjudication (REC-1 recommended); overwrite method REFUTED |
| K2 | set-based sentence in SPH conclusion | REFUTED — only remaining occurrence is the labelled historical quotation at line 84 |
| K3 | `equivalently` bridge | REFUTED — token absent from all four conclusions; residual unsourced gloss recorded non-blocking |
| K4 | D3 comeager discharge | REFUTED — all four conclusions carry a comeager quantifier bound before the data |
| K5 | C2/C0 `schema_owner` legacy pointers | REFUTED — C2→F2a/`schemas/af_scc_c2_vacuum.yaml`, C0→F2b/`schemas/af_scc_c0_vacuum.yaml`, both exist and are FROZEN-pinned |
| K6 | `genericity_topology` slot absent from axes | CONFIRMED, non-blocking (pre-existing) |
| K7 | SPH `axes.genericity_kind=unresolved` vs comeager conclusion | CONFIRMED, non-blocking, confirms lead-audit O-GF0-1 |
| K8 | FROZEN rev28 pins live F0/F0-R/schemas | CONFIRMED — worker-038 stale-pin blocker discharged at manifest level |
| K9 | duplicate YAML keys | REFUTED — none |

- **Controls**: the K2 and K3 detectors fire on injected mutants and stay quiet on the real rev5
  bytes, so "fixed" is not a false negative.
- **Condition**: the accept is conditional on the controller's mirror disposition — REC-1
  (pair-check exception) leaves these bytes valid; REC-2 rewrites the artifact and voids this verdict.
  This verdict binds only `0abb9ed8a961`; any further edit makes it UNMEASURED.
- **Authority**: worker verdict is evidence only. No gate verdict, no `status=done`, no
  `validation_status=passed`, no theorem claim. Independent non-author verdict at the pinned hash
  (lead-audit B-GF0-1 asks for two); whether it counts as a full schema verdict is the controller's call.
- **Falsifier**: see `results.json:falsifier` (bidirectional, re-runnable at the recorded hashes).

Artifacts: `results.json`, `validation.json` (all 7 evidence refs hash-match disk), `MANIFEST.json`
(all files hashed), `runs.jsonl`, `f0_rev5_snapshot.yaml`, `verify_rev5.py`.
