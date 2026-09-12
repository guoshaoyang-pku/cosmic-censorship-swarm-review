# W069 F2b rev12 independent G-FORM verdict

**Task** `W069-F2B-REV12-INDEPENDENT-VERDICT-01` (worker-069, class `AF-SCC-C0-VAC-GEN`, node F2b, gate G-FORM).
**Target** `schemas/af_scc_c0_vacuum.yaml` at the FROZEN rev28 pin `55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6` (schema revision 12).
**Verdict** `revise` score 3.5: 41/44 independent
checks pass, 17/17 mutation controls fire, 3 blocking-for-clean-accept
findings, 3 advisory/info findings.

## Hard failures (blocking for a clean accept)

- **HF-069F2B-I08** (declared consistency_evidence_sha256 resolves at the canonical evidence path): declared consistency_evidence_sha256 675a99d0d25b2b37 does not resolve: canonical artifacts/formulation/evidence/taxonomy_consistency.json measures 9e335e9ba1bfcf77 (FROZEN rev28 pin)
  - falsifier: restore/regenerate the canonical evidence generation so that the canonical path artifacts/formulation/evidence/taxonomy_consistency.json hashes to the declared 675a99d0... (or update the declaration to the measured value), re-pin it in FROZEN, and re-run: declared == measured voids the finding
- **HF-069F2B-I09** (consistency evidence binds the compared trees by hash (input pins present)): canonical consistency evidence contains no sha256 of either compared tree (keys=['alias_policy', 'classes_compared', 'consistent', 'contract_divergences', 'errors', 'lead_contract', 'map_taxonomy', 'notes']); the consistency claim is not bound to the inputs it checks
  - falsifier: an evidence generation whose bytes carry map_taxonomy_sha256=0abb9ed8... and lead_contract_sha256=d7419b4e... (as the declared 675a99d0 generation already does) closes this finding; the current canonical bytes dropped both keys
- **HF-069F2B-F07** (two-stage acceptance pipeline status recorded (PASS required for clean accept)): two-stage acceptance not PASS (exit=3):   re-run: python3 artifacts/formulation/tools/measure_semantic_escape.py
  - falsifier: rebase the fixtures (artifacts/formulation/tools/measure_semantic_escape.py) and re-run run_acceptance.py on the same frozen bytes; an ACCEPTANCE: PASS voids the finding

## What passed

- Stage 1 canonical structural gate `check_class_schema.py` (`000e09e46b2f`): verdict pass,
  failed_rules=[] on the snapshot.
- Stage 2 semantic auditor `spec_conformance_audit.py` (`c79d8ab8440a`): verdict pass.
- `class_separation.findings` on the snapshot: 0; `classsep_regression.py`: PASS.
- `verify_frozen.py`: FROZEN revision 28, 0 problems; the manifest pins subject/F0/supplement/evidence exactly.
- Worker-098's B1/B2/B3 closure claims independently reproduced: strict parse has no duplicate keys (S02),
  D0 is a typed disjoint union with no pair-index residue (Q04), the canonical pointer resolves (I02).
- No pinned input drifted during the run: {"subject": false, "f0": false, "supplement": false, "evidence": false, "frozen": false, "aliases": false, "rubric": false, "stage1": false, "stage2": false, "classsep_module": false}.
- Determinism: a second run is byte-identical except `run_at`.

## Reading the two binding failures together

The schema declares `f0_binding.consistency_evidence_sha256 = 675a99d0d25b...`. The canonical evidence path
currently holds `9e335e9ba1bf...` (FROZEN rev28 pin), which additionally **dropped** the two input pins
(`map_taxonomy_sha256`, `lead_contract_sha256`) that the declared `675a99d0` generation carries. So the
consistency claim is unbound in both directions: the declaration does not resolve, and the live evidence does
not bind the trees it claims to have compared. The minimal closure is to make the canonical path hold a
generation that carries both input pins (the preserved `675a99d0` bytes already satisfy this) and re-pin it in
FROZEN, or to regenerate and update the declarations and FROZEN in one step. The F2a verdict
`reviews/F2a-rev12-069.json` found the same defect; it is family-wide.

## Reproduction

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-069/f2b_rev12_independent_verdict/check_f2b_rev12_independent.py --controls
```

Raw outputs: `raw/checker_result.json`, `raw/stage1_stdout.json`, `raw/stage2_stdout.txt`,
`raw/verify_frozen.txt`, `raw/classsep_regression.txt`, `raw/run_acceptance.txt`,
`raw/classsep_module.json`, `raw/snapshot.sha256`, `raw/controls_dir/`.

## Non-claims

Worker events cannot set a node `done`, a `validation_status=passed`, or a gate verdict. This is one bounded
class-bound task: artifact evidence only. No canonical file was modified.
