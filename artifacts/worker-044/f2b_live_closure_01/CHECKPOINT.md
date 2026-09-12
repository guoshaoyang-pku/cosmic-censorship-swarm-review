# CHECKPOINT — W044-F2B-LIVE-CLOSURE-01

- **worker:** worker-044 · **node:** F2b · **class:** `AF-SCC-C0-VAC-GEN` · **gate:** G-FORM
- **status:** complete at worker level (no gate verdict / node status / validation_status)
- **probe snapshot:** 2026-09-12T01:00:24+08:00 · **checkpoint:** 2026-09-12T01:02:13+08:00
- **decision:** `F2B_BLOCKED_AT_MEASURED_PINS`
- **blocking families:** H1_false_containment_denial, H2_inverted_size_premise, A2_evidence_not_self_verifying, A6_alias_registry_unbound, SEP6_aggregator_component_pins_stale
- **prediction match:** True (0 mismatches) · **controls:** True (K1-K8)

## Artifacts (sha256)

- `artifacts/worker-044/f2b_live_closure_01/report.json` — `126cf7aef7fbe5dd95a0c711f1a147daef0dabc7f8189029b43c3a90dcfeb7d3`
- `artifacts/worker-044/f2b_live_closure_01/closure_summary.json` — `7bd2b25cd6fa8d02fd5117d4220cf28867c8aecdc2117816c230c30b7f8bd5a2`
- `artifacts/worker-044/f2b_live_closure_01/PREREGISTRATION.json` — `707ba8cfde131970276dabec2ee54b1ae04f7a28b594dc1c574131edd95d0ee2`
- `artifacts/worker-044/f2b_live_closure_01/PROVENANCE.json` — `24b03e0ce30fa8a7b4c5858b585fe9e2f00bcb7e82542c89de7bdfb4a49e4c30`
- `artifacts/worker-044/f2b_live_closure_01/live_closure.py` — `291e4403443015cc08a2e6d8fe1fbd898e4d84fd4b827003185e7363b8478997`
- `artifacts/worker-044/f2b_live_closure_01/adjudicate.py` — `d5ad229871d1537a374cc4b31a8a192519717fa56ad95a949dbf5f2367101f6e`
- `artifacts/worker-044/f2b_live_closure_01/README.md` — `23babd37480b88b68b07fc2db9dd2869295eeed8981ddd670b9e84e53faed000`
- `artifacts/worker-044/f2b_live_closure_01/run.log` — `86595f66ba12d8345463dd0e1acec08d2dc755ae3c76bf7ae22daf95a74da5d4`
- `artifacts/worker-044/f2b_live_closure_01/adjudicate.log` — `5269bc4a623256c497872d12186be3161d605b23953237e7687f3ccd6afcaa30`
- `runtime/state/w044_f2b_live_closure_01_checkpoint.json` — `86010b433a8e1ee49cbe372dabc4c0ec92a01b524de2381cab54406c94bc78ae` (this checkpoint)

## Next falsifier

Re-run `live_closure.py` + `adjudicate.py`: the closure decision is void if any pre-registered
snapshot check changes at the same pins, if any K1-K8 control stops discriminating, or if
H1H2/A2/A6 passes or SEP-6 becomes ok at C0 `b2ab6acb2bbe` / FROZEN `815e08079aef` — in those
cases F2b is no longer blocked by these families. Drift of any pinned input voids live
applicability only, not the snapshot measurement.

## Exit

One bounded class-bound task taken, measured, adjudicated and emitted. Worker exits for recycling.
