# W076-GATE-EVIDENCE-PINMAP-01 — acceptance-pipeline dependency / pin map

Worker: `worker-076` (bounded execution worker, self-assigned; no inbox card exists for this slot).
Node: `F1,F2a,F2b` · Classes: `AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN` · Gate: `G-FORM`.
Motivating blocker: `lead-form-20260912T011509-123` (astra-lead-formulation) — *"the acceptance
pipeline is only half hash-bound … `run_acceptance.py` IS pinned … but stage 2
`artifacts/worker-06/spec_conformance_audit.py` … is unpinned."*

**Authority: worker measurement only.** This task sets no gate verdict, no
`validation_status=passed`, no adoption, and writes no canonical file. Only the controller and
group leads move gates.

## What was measured

1. **Transitive dependency census** from the pinned seed
   `artifacts/formulation/tools/run_acceptance.py` (`depmap.py`, AST closure, no imports executed).
   44 files resolve; 9 are FROZEN rev29 pins that match their declared sha256 and **35 are
   unpinned**, including:
   - `artifacts/worker-06/spec_conformance_audit.py` (the stage-2 semantic rule engine, `c79d8ab8440a`),
   - `artifacts/worker-06/semantic_fixtures/manifest.json` (`c102445df397`),
   - all 33 `artifacts/formulation/evidence/rebased_fixtures/*.yaml` (31 mutants + 2 controls) that
     `run_acceptance.py` reads to compute `union_caught`.
2. **The declared stage-2 hash is documentary, not enforced.** The FROZEN-pinned corpus record
   `artifacts/formulation/evidence/semantic_escape_rebased.json` declares `w06_sha256` equal to the
   live engine hash, but only `measure_semantic_escape.py` *writes* that field; the acceptance
   runner invokes the stage-2 path with no hash check, and `verify_frozen.py` covers only the 50
   pinned paths.
3. **The engine's verdicts are editable without moving a pin.** A one-line edit of a sandbox copy
   (`verdict = "reject" …` → `verdict = "accept"`) flips 11/33 fresh-corpus stage-2 verdicts
   (reject → accept). No canonical byte is touched.
4. **The pinned acceptance report does not reproduce at the live base.** Pinned
   `acceptance_pipeline_report.json` (`9b7d6c8208d3`, verdict PASS) claims mutant union 31/31 at
   declared base `1bb78ce9b357`; re-running the FROZEN-pinned generator with only its `OUT`/`TMP`
   paths redirected to `sandbox/` against the live C0 `b2ab6acb2bbe` yields **30/31** with union
   escape `struct12_i_plus_completeness_lexical.yaml`. Stage-2 currently supplies **0** marginal
   union catches at the live base, while the pinned report claims one — the engine's marginal
   decisiveness is base-dependent and cannot be read off the pinned report.
5. **Corroboration of L-FORM-04:** the pinned corpus record declares the two controls `pass`; live
   stage-1 fails both on R22 `revised_at_unused`, and the pinned runner still exits 3 at preflight
   (`raw/run_acceptance_preflight.txt`). 3 pinned-record verdicts do not reproduce on live bytes.
6. Observation (not attributed to this task): FROZEN-pinned
   `artifacts/formulation/tools/check_variant_registry.py` drifted during the probe window
   (`c471da4b7be9` → `8c7ef46f11db`), i.e. FROZEN verification races live writers.

## Verdict / falsifier

`unpinned_stage2_verdicts_editable = true`; `pinned_report_reproduces = false`.

Falsified if the sabotaged copy reproduces every live stage-2 verdict on the fresh corpus, or the
pinned acceptance report reproduces at the live base, or a probe-written file appears in FROZEN, or
the live stage-2 hash differs from the declared `w06_sha256`.

## Recommendation (owner action; not performed here)

1. In the same authorized revision that adopts any stage-2 (R03) change, add
   `artifacts/worker-06/spec_conformance_audit.py` (and the manifest, if selftest is gate evidence)
   to `FROZEN.files` with measured sha256.
2. Make the acceptance runner fail closed on `sha256(stage2) != declared w06_sha256`.
3. Disposition the 33 corpus fixture bytes (pin by hash or bind to generator+base and require
   regeneration; preflight already fails at the live base).
4. Re-pin `acceptance_pipeline_report.json` only after regeneration at the rev14/rev30 base.

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-076/gate_evidence_pinmap/depmap.py artifacts/worker-076/gate_evidence_pinmap/raw
python3 artifacts/worker-076/gate_evidence_pinmap/materiality_probe.py
python3 artifacts/worker-076/gate_evidence_pinmap/make_report.py
python3 artifacts/formulation/tools/verify_frozen.py   # external traffic may drift; cf. finding 6
```

All probe writes are confined to `artifacts/worker-076/gate_evidence_pinmap/`; the sandbox copies
of the pinned generator and the stage-2 engine are named as such.
