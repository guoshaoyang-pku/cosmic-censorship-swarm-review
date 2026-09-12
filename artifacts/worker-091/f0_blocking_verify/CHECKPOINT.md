# worker-091 — F0 blocking-findings verification (checkpoint)

- **When**: 2026-09-12T00:31:19+08:00 · **target**: `research_map/formulation_taxonomy.yaml` sha256 `276009f4f63dbf838f32f368eed982f5e353d69970ca3227090aed14d26006dc` (rev 4, status `draft_unverified`), 35145 B, no drift during scan.
- **Task**: independently measure the blocking items that decide between the conflicting F0 verdicts at this hash — accept (`reviews/F0-review-094.json`) vs revise (`F0-review-16`, `F0-independent-worker-082`, `F0-review-lead-audit-r2`).
- **Verdict**: **revise 3.5** — blocking CONFIRMED: K0, K1a, K2, K3, K4, K5; CONTESTED: K1b; informational: .
- **K1b (mirror) is contested, not confirmed**: FROZEN rev26 declares canonical F0 and `artifacts/formulation/formulation_taxonomy.yaml` (F0-R) to be two distinct logical artifacts; `f0_mirror_adjudication_request` says byte-identical publication is destructive (REC-1/REC-2 pending). Controller adjudication required.
- **Distinct contribution**: the lead consistency checker's D1/D3 guards cover only AF-WCC-VAC-GEN (D1) and AF-SCC-C2/C0 (D3); `CONSISTENT (0 divergences)` is scoped and does not discharge D1/D3 for AF-WCC-SCALAR-SPH.
- **Read-only**: no canonical file mutated; snapshots byte-identical; pre/post digests equal.
- **Artifacts**: `results.json` `17daaf38feec`, `f0_snapshot.yaml`, `supplement_snapshot.yaml`, `verify_f0_blocking.py`, `MANIFEST.json`, `validation.json`.
- **Authority**: worker evidence only; no gate verdict, no `status=done`, no `validation_status=passed`. Outbox events left for controller ingest.
