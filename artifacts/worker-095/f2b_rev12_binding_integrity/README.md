# W095-F2B-BIND-INTEGRITY-02 — binding/publication integrity receipt, F2b rev12

- **Worker**: worker-095 (slot 095)
- **Node**: F2b — **Class**: `AF-SCC-C0-VAC-GEN` — **Gate**: G-FORM (FORM-GATE-01)
- **Reviewed**: `schemas/af_scc_c0_vacuum.yaml` rev 12, sha256 `55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6`
- **Journal**: FROZEN revision 28 (`frozen_at 2026-09-12T00:35:08+08:00`)
- **Verdict**: `revise` (score 2/5) — 15 checks, 13 pass, 0 blocking, 1 major, 1 minor, zero hash drift
- **Supersedes**: `W095-F2B-BIND-INTEGRITY-01` (rev11 `1bb78ce9b357`)
- **Not** a full-schema content verdict (`counts_as_full_schema_verdict: false`); worker events cannot
  set node status, `validation_status=passed`, or a gate verdict.

## Findings

| ID | Severity | Finding | Falsifier |
|---|---|---|---|
| **F-EVID-1** | major | F2b.f0_binding declares consistency evidence `675a99d0d25b` (enriched rev12 run, coherent, present at `artifacts/worker-086/gform_rev12/pinned/taxonomy_consistency.675a99d0d25b.json`), but the canonical path measures `9e335e9ba1bf` and FROZEN rev28 pins `9e335e9ba1bf`. The schema declaration is stale versus the freeze. The canonical checker rewrites the path unconditionally (`check_taxonomy_consistency.py:80`) in a summary format lacking the hash fields (observed live transition `675a99d0 → 9e335e9ba1bf`, 00:33:08–00:33:14). | A stable revision where declared == canonical-path == FROZEN pin (restore enriched bytes + re-freeze, or refresh the three schemas' evidence hash + re-freeze/re-review); re-probed at C5b pass. |
| **F-VOCAB-1** | minor | Canonical F0 rev5 `classes.AF-SCC-C0-VAC-GEN.axes` still stores accepted aliases (`strong_cosmic_censorship_C0` / `provisional_baire_residual`) while schema and gate use canonical tokens (`scc_c0_future_inextendibility` / `residual_comeager`); policy forbids aliases in a new canonical artifact. Alias-equivalent, 0 consistency errors — hygiene, not contradiction. | A canonical F0 revision storing the canonical tokens verbatim; re-probed at C4b pass. |
| **F-CLOSE-1** | info | Prior receipt's grounds are closed: F-BIND-1 pointer now resolves on the declared canonical F0 for all three schemas; F-PROV-1 duplicate keys 7 → 0; F-TIME-1 `revised_at 00:31:41+08:00` ≤ mtime ≤ wall. | A revision reopening the pointer, duplicate-key, or future-stamp defect (C3/C7/C8 fail). |
| **F-PUB-1** | info | Apart from F-EVID-1, publication is coherent: FROZEN rev28 pins all six schema paths and both F0 logical artifacts at measured bytes; F2b canonical == authoring; pinned gate passes; class-separation clean. | Any rev28 pin not matching a re-measured path, or an F0 logical-role collapse. |

## Checks (15)

C1 snapshot · C2 identity · C3 pointer closure · C3b pointer scope · C4 alias equivalence ·
C4b token hygiene · C5a F0 hash binding · C5b evidence binding · C6 publication pins ·
C7 duplicate-key closure · C8 timestamp closure · C9 gate corroboration · C10 class separation ·
C11 stability/drift · C12 consistency semantics + generator write hazard.

## Evidence

- `verdict.json` — full machine-readable receipt (checks, per-check falsifier, findings, task falsifier)
- `evidence/raw/*.json` — 14 measured evidence files (snapshot, identity, pointer matrix, vocabulary,
  f0 binding, evidence binding, publication pins, duplicate keys, timestamps, gate run, class
  separation, stability, consistency run)
- Reproduce: `python3 artifacts/worker-095/f2b_rev12_binding_integrity/measure_binding.py`

## Canonical-artifact disclosure

The pinned consistency checker was invoked **once during reconnaissance** (00:34:55) to observe its
semantics. It unconditionally rewrites `artifacts/formulation/evidence/taxonomy_consistency.json`;
the write was **byte-identical** to the pre-existing file (`9e335e9ba1bf`), so no canonical byte
changed (only mtime). The probe itself does not invoke it. No other canonical artifact, the map, or
the accepted event stream was modified by this task.
