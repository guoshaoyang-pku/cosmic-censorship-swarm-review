# W043D — R2 durability + acceptance test for the F0 consistency-evidence binding

**Worker:** worker-043  **Gate:** G-FORM  **Nodes:** F0, F1, F2a, F2b
**Classes:** AF-SCC-C2-VAC-GEN (primary), AF-WCC-VAC-GEN, AF-SCC-C0-VAC-GEN
**Verdict:** `accept_for_repair_R2` — all six pre-registered expectations hold.
**Authority:** measurement only. No canonical file was written, no gate verdict, no review verdict.

## The defect this task closes out

All three rev12 class schemas declare

```
f0_binding.consistency_evidence_sha256 = 675a99d0d25b2b37...
```

but the canonical path `artifacts/formulation/evidence/taxonomy_consistency.json`
measures `9e335e9ba1bfcf77...` (495 B). Worker-086 (`reviews/G-FORM-evidence-collision-086.json`)
identified the cause as a two-writer collision: `close_findings_rev27.py:391` writes the
pin-bearing document under `--apply`, while `check_taxonomy_consistency.py:80` unconditionally
rewrites the same path with a pin-free document every time the consistency check is run.

This task does not re-diagnose that (it is already the third independent measurement). It tests
the **minimal-churn repair R2** end to end and measures whether it holds:

1. **Restore** the declared bytes at the canonical path — no class-schema edit;
2. **Re-freeze** FROZEN to rev29 moving *only* the evidence pin;
3. **Patch the writer** so a verification run can never move the evidence hash again.

## Results (all on sandbox copies; canonical tree read-only)

| id | expectation | result | evidence |
|---|---|---|---|
| E1 | lean document + 3 insertion-ordered fields (`map_taxonomy_sha256`, `lead_contract_sha256`, `measured_at=2026-09-12T00:32:02+08:00`) reconstructs the declared `675a99d0`, 728 B | PASS | `raw/reconstruction.json`, `raw/evidence_restored_675a99d0.json` |
| E2 | the owner checker's unconditional write destroys the declared bytes in one run (`675a99d0` -> `9e335e9b`, exit 0) | CONFIRMED | `report.json` E2 |
| E3 | R2 + FROZEN rev29 (evidence pin only) flips the independent W043C checker to **accept / 0 FAIL**, R15+R16 PASS, schemas byte-identical | PASS | `report.json` E3 |
| E4 | R2 **alone** is not durable: after one owner-checker run R15/R16 fail again | CONFIRMED | `report.json` E4 |
| E5 | with the writer redirected (`durability.patch`), two runs leave `675a99d0` in place, exit 0, checker still accept / 0 FAIL | PASS | `report.json` E5 |
| E6 | controls + instrument self-test 8/8; no canonical drift | PASS | `report.json` E6 |

## The patch (owner-applied, 2 lines)

```diff
-out = ROOT/"artifacts/formulation/evidence/taxonomy_consistency.json"
-out.write_text(json.dumps(rep, indent=2)+"\n")
+report = ROOT/"artifacts/formulation/evidence/taxonomy_consistency_report.json"
+report.write_text(json.dumps(rep, indent=2)+"\n")
```

`durability.patch` is the full unified diff; `patched_check_taxonomy_consistency.py` is the
patched file at the canonical tool's hash `de356d999ea3`.

## Required adoption order (owner: lead-formulation)

1. restore the 728 declared bytes from `raw/evidence_restored_675a99d0.json` to
   `artifacts/formulation/evidence/taxonomy_consistency.json`;
2. bump `artifacts/formulation/FROZEN.json` to rev29 with a wall-clock `frozen_at` and **only**
   the `artifacts/formulation/evidence/taxonomy_consistency.json` pin changed to `675a99d0...`;
3. apply `durability.patch` to `artifacts/formulation/tools/check_taxonomy_consistency.py`
   (re-emit its artifact event and re-pin it in the same FROZEN bump if the tool is pinned);
4. never run the unpatched checker after step 1 — it re-destroys the declaration (E2/E4).

Schema hashes do **not** change (`F1 cce9c60146d6`, `F2a 5476a3f2c6bc`, `F2b 55d0a1ea9bda`), so
every hash-pinned schema verdict keeps its binding and only the binding-axis verdicts need to be
re-issued.

## Falsifier

At the repaired pins: the repair fails if the canonical evidence hash moves off `675a99d0`, if
FROZEN moves any pin other than the evidence pin, if any schema byte changes, or if R15/R16 do not
both PASS on a fresh run of the independent checker.

## Non-claims

- No canonical file written; R2 is an owner-applied proposal.
- Not a gate verdict and not a review verdict on any class schema.
- Does not adjudicate worker-047 C06/C07 (taxonomy conclusion-text `pair_(s,delta)` vs schema
  `index_r` binder); that remains open for F0/formulation.
- R2 repairs the binding axis only; no content finding is re-opened or closed here.
- The sandbox FROZEN rev29 used a synthetic `frozen_at`; the owner must re-issue it at adoption
  time.

## Replay

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-043/w043d_r2_durability/reconstruct_declared_evidence.py
python3 artifacts/worker-043/w043d_r2_durability/durability_test.py
```

Sandbox trees used by the last run are kept beside the scripts
(`w043d_clobber_*`, `w043d_instr_*`, `w043d_r2_*`).
