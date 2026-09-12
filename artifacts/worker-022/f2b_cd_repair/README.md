# W022-F2B-CD-REPAIR-CAND-01 — minimal F2b containment-direction repair candidate (non-canonical)

Worker-022, class `AF-SCC-C0-VAC-GEN`, node `F2b`, gate `G-FORM`. Bounded, read-only on
canonical paths; everything written lives under `artifacts/worker-022/f2b_cd_repair/`.

## What this is

Worker-008's containment-direction census found two hard failures in the canonical F2b
schema (rev12, `55d0a1ea`), reproduced here by independent detectors at the now-frozen
rev13 bytes (`b2ab6acb`, FROZEN rev29 `3d9e3d77`):

| id | yaml path | defect | repair |
|---|---|---|---|
| CD-01 | `implication_ledger.forbidden_transfers[0].reason` | reason says C2 is a strictly **larger** extension class; the document's own chain says C2 is strictly smaller (E_C2 ⊂ E_C0) | `larger` → `smaller`, with the subset witness |
| CD-02 | `regularity.must_not_conflate[0]` | bullet denies *"No containment with C2 or C0 is asserted here"* while `implication_ledger.extension_class_containment` declares E_C0 ⊃ E_H2loc ⊃ E_{C^1,1} ⊃ E_C2 | denial replaced by the true statement (H2_loc sits between the C0 and C2 endpoint classes), preserving the curvature-axis content and the worker-16 accepted tail |

The forbidden-transfer **direction** in CD-01 was already correct; only the size premise
was inverted. Both edits are single-line, leaf-field text changes; no class semantics,
quantifier, topology, or conclusion field is touched.

## Result: REPAIR_READY

Candidate `candidate/af_scc_c0_vacuum.repair-candidate.yaml`,
sha256 `a110f8e875afc747d8e8afc1b97912b83537c22be971bb3b791bc865693e2757`,
differs from the FROZEN rev29 canonical bytes in exactly lines 152 and 246.

| check | result |
|---|---|
| C1 pins (F2b `b2ab6acb`, FROZEN rev29 `3d9e3d77`, snapshots byte-equal) | PASS |
| C2 exactly two changed lines = the two target lines; 0 duplicate keys | PASS |
| C3 CD-01 detector fires canonical / silent candidate | PASS |
| C4 CD-02 detector fires canonical / silent candidate | PASS |
| C5 chain still ordered E_C0 ⊃ E_H2loc ⊃ E_{C^1,1} ⊃ E_C2; repair consistent | PASS |
| C6 frozen structural gate `check_class_schema.py --json` on candidate | exit 0, verdict pass |
| C7 `class_separation.findings_for_text(candidate)` | 0 findings |
| C8 deep diff vs canonical = only the two repaired YAML paths | PASS |
| C9 canonical + FROZEN hashes unchanged at exit | PASS |
| C10 deterministic re-emit (same sha256) | PASS |
| M1/M2 single-defect reverts re-fire CD-01 / CD-02 | PASS |
| M3 `smaller`→`larger` mutation re-fires CD-01 | PASS |
| M4 false chain direction fails C5 | PASS |
| M5 pristine candidate, no false positives | PASS |
| M6 canonical + whitespace perturbation still fires both | PASS |

## Pin cascade observed during the task (recorded, not hidden)

1. `schemas/af_scc_c0_vacuum.yaml` moved `55d0a1ea` (rev12) → `b2ab6acb` (rev13) at
   `2026-09-12T00:53:20` — the owner's `astra-life05-evidence-binding-repair` refreshed
   `f0_binding.consistency_evidence_sha256` 675a99d0 → 9e335e9b. First run returned
   `PIN_VOID`; preserved at `report.rev12-pinvoid.json`. Re-pinned per
   `preregistration_rev13_addendum.json`.
2. `artifacts/formulation/FROZEN.json` moved rev28 `2f358f67` → rev29 `3d9e3d77` at
   `2026-09-12T00:55:02`, pinning the rev13 hashes. Second run returned `PIN_VOID` on the
   FROZEN hash only (all repair checks already passed). Re-pinned per
   `preregistration_rev13_addendum2.json`; final run `VERDICT=REPAIR_READY`.
3. `report.json` records the settled state; `report.rev12-pinvoid.json` and
   `pinned/af_scc_c0_vacuum.55d0a1ea9bda.yaml` preserve the superseded binding.

## Reproduction

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-022/f2b_cd_repair/verify_f2b_cd_repair_022.py --emit   # exit 0
python3 artifacts/formulation/tools/check_class_schema.py --json \
    artifacts/worker-022/f2b_cd_repair/candidate/af_scc_c0_vacuum.repair-candidate.yaml
```

## Authority limits and falsifier

Worker candidate + self-check only. This sets no node status, no `validation_status`, no
review verdict and no gate verdict, and writes no canonical byte. Publication and the next
FROZEN revision remain with the formulation lead / controller. The shared binding blocker
was closed by the owner's rev13; the remaining action for CD-01/CD-02 is owner publication.

FALSIFIED IF: canonical F2b is not `b2ab6acb` or FROZEN is not rev29 `3d9e3d77` at entry
(re-pin and re-run); CD-01/CD-02 no longer fire on the pinned bytes (candidate superseded);
the candidate trips C3/C4, changes any line outside the two intended fields, fails C6/C7,
or is non-deterministic; any control M1–M6 misbehaves; or the owner publishes a rev14 F2b
already carrying a containment-direction repair.
