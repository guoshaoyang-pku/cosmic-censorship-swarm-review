# W067-N0-CNFEM-TRIAGE-VERIFY-01 — independent verification of the cnfem triage

| field | value |
|---|---|
| worker | `worker-067` (bounded, breadth) |
| class / node / gate | `AF-WCC-SCALAR-SPH` / `N0` / `G-NUM` |
| target | open G-NUM unmet item: *"cnfem triage from the N0 adjudication is not closed: fix with root cause, or exclude with evidence"* |
| inputs | `numerics/tests/replication_triage.md` `f27a253ec928`; `numerics/tests/flat_wave_replication.py` `8ade1cdc163e`; `numerics/results/flat_wave_replication.json` `298a4d921c2264`; `numerics/protocol/format_conditions_disposition.json` `e7c05ff33fe2` |
| checker | `check_cnfem_triage.py` (exit 0 verified / exit 2 fail-closed) |
| verdict | **`CNFEM_ROOT_CAUSE_AND_FIX_REPRODUCED_WITH_DOCSTRING_DEFECT`**, controls **10/10** |
| authority | verification evidence only: no gate verdict, no node transition, no `validation_status=passed`, no canonical writes, `numerics_lock` respected |

## What was verified, from bytes rather than prose

| # | measurement | result |
|---|---|---|
| M1 | five pinned inputs hashed before and after; anchors `N0_adjudication.md` `003baf8b`, `fixed_replication_verdict.json` `dcad962324e3`, `formulation_taxonomy.yaml` `0abb9ed8a961` | all match, stable |
| M2 | pre-fix recurrence independently constructed here, `(M + cK) psi^{n+1} = 2M psi^n - (M - cK) psi^{n-1}`, run through the published harness driver at dr 0.2/0.1/0.05 | order **−0.07727** (triage claims −0.0773), non-monotone, amplitude 1.0 → **2.52** at dr 0.2, error *grows* with refinement |
| M3 | live fixed `CrankNicolsonFEM` re-run | order **1.9863235066828981**, pair orders 1.9836 / 1.9891, monotone |
| M4 | published JSON cross-check | order, own drift and harness drift reproduce **bit-exactly** (rel. delta 0.0); all three JSON rows equal the re-run |
| M5 | static doc-consistency of the live class | docstring line 305 still documents the **pre-fix** recurrence; implementation assembles one `B = M + cK` and uses it on both sides (lines 315–318, 329) |

Invariants at dr = 0.05: cnfem own drift `2.04e-14`, harness drift `8.48e-09` (tol `1e-6`); cnfd own `1.11e-14`, harness `6.59e-08`. Reference lffd order `1.99577`.

## Findings

- **F1 (root cause confirmed).** The sign error in the CN/FEM right-hand side is the root cause, as the triage claims: the wrong right-hand side diverges with a negative measured order and secular amplitude growth; the fixed one converges at order 2. This is a reproduction from an independent construction, not a re-read of the triage.
- **F2 (new, minor, non-blocking).** The live module's `CrankNicolsonFEM` docstring still states the buggy recurrence `(M + c K) psi^{n+1} = 2 M psi^n - (M - c K) psi^{n-1}` while the code implements the corrected one. The code is right; the method description is the bug. A reader implementing the docstring reintroduces the defect. This is not recorded in the triage or the disposition artifact.
- **F3 (reproduction).** All published cnfem numbers for the fixed revision reproduce exactly at the pinned hash.
- **F4 (scope).** Verification of an on-disk claim only. It does not accept the triage, close G-NUM, or repair the docstring: an edit would move `8ade1cdc163e`, which is pinned by the triage, the disposition artifact and the chained verdict.

## Minimal recommended action (owner `astra-lead-numerics`)

Record an erratum note pinning line 305 in the triage/protocol provenance set. Repair the docstring only together with re-pinning every dependent hash (triage `f27a253ec928`, disposition `e7c05ff33fe2`, chained verdict `dcad962324e3`); the lock forbids unhashed canonical edits. The separate live defect in `fixed_replication_verdict.json` (contradicted taxonomy pin, `dcad962324e3`) is out of scope here and is not re-litigated.

## Reproduction

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-067/n0_cnfem_triage_verify/check_cnfem_triage.py   # exit 0 = verified
```

## Falsifier

Withdrawn if any of: (a) the wrong-RHS variant constructed here measures order ≥ 0.5 or no amplitude growth at dr = 0.2; (b) the live cnfem order study leaves the harness band or its own-energy drift exceeds `1e-12`; (c) the published JSON's cnfem rows disagree with a re-run at hash `8ade1cdc`; (d) `flat_wave_replication.py` no longer hashes to `8ade1cdc` — then all of M2–M4 are void by hash and no claim transfers to the new revision; (e) the docstring no longer contains the pre-fix recurrence, which voids F2 only.

## Non-claims

No mathematics, physics, WCC/SCC or self-gravity claim. No gate verdict, no node completion, no `validation_status=passed`. The solver was never modified; the only writes are under `artifacts/worker-067/` and `runtime/state/worker-067_checkpoint_8.json`.
