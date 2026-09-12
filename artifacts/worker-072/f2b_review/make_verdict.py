#!/usr/bin/env python3
"""Assemble the W072-F2B-REVIEW-REV29-01 verdict file and the artifact MANIFEST.

Reads the instrument report, the controls summary and the pinned regression results, and
writes:
  reviews/F2b-review-worker-072-rev29.json   (verdict; the reviewed artifact is untouched)
  artifacts/worker-072/f2b_review/MANIFEST.json (sha256 of every deliverable)
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
HERE = ROOT / "artifacts/worker-072/f2b_review"
PINS = HERE / "classsep_pins"
VERDICT = ROOT / "reviews/F2b-review-worker-072-rev29.json"


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def mtime_iso(p: Path) -> str:
    return subprocess.run(["date", "-Is", "-r", str(p)], capture_output=True, text=True).stdout.strip()


def main():
    report = json.loads((HERE / "report.json").read_text())
    controls = json.loads((HERE / "controls/controls_summary.json").read_text())
    regs = {}
    for name in ("c266dbecaa87", "e2d24b927ee8", "e36b0d644ca7"):
        p = PINS / f"regression.{name}.json"
        if p.exists():
            d = json.loads(p.read_text())
            regs[name] = {k: d[k] for k in ("module_path", "module_sha256", "tp", "fn", "tn", "fp",
                                             "leaks_detected", "controls_clean", "verdict")}

    target_path = ROOT / "schemas/af_scc_c0_vacuum.yaml"
    mirror_path = ROOT / "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"
    frozen_path = ROOT / "artifacts/formulation/FROZEN.json"
    f0_path = ROOT / "research_map/formulation_taxonomy.yaml"
    ce_path = ROOT / "artifacts/formulation/evidence/taxonomy_consistency.json"
    live_det = ROOT / "research_map/class_separation.py"

    findings = [
        {"id": "F-01", "severity": "advisory-scope", "field": "conclusion.known_obstruction; falsifier.tier_2.witness_type",
         "finding": "The motivating obstruction and the tier_2 witness example use exact stationary (Kerr) vacuum data, "
                    "but topology.forbidden excludes slices with more than one AF end and slice_topology requires a complete "
                    "slice diffeomorphic to R^3; the standard complete Kerr/Schwarzschild maximal slices are two-ended, so exact "
                    "Kerr data are not obviously admitted by this artifact's own D2. The quantified negation over the declared "
                    "D2 is internally correct, and the field is marked citation_status=unresolved and L1-owned, so this does not "
                    "void the accept; it is a scope note for the next metadata-only patch (cite an admissible one-ended "
                    "extendible family, or restate the bullet as true of a broader two-ended AF class).",
         "hash_bound": True, "blocking": False},
        {"id": "F-02", "severity": "advisory-disclosure", "field": "regularity.i_plus_regularity; data_class.adm_mass.hypotheses_reconciliation",
         "finding": "The independent i_plus C^k (k>=3) assumption and the Sobolev/pointwise-rates reconciliation are declared "
                    "as assumed and 'recorded not resolved'. No hidden assumption found; the two fields are the only "
                    "assumption-completeness soft spots a careful reader would want the formulation lead to keep visible.",
         "hash_bound": True, "blocking": False},
        {"id": "F-03", "severity": "instrument-advisory", "field": "research_map/class_separation.py (not the F2b artifact)",
         "finding": "Detector drift continued inside the write-freeze window and the live file oscillates: active frozen pin "
                    "c266dbecaa87 -> live a8c04fc31e4a (recorded by pass-06/CF-26, 00:52) -> live e36b0d644ca7 (01:06:12, measured "
                    "by me and independently hit by worker-073's fail-closed pin abort and worker-090's erratum) -> live "
                    "a8c04fc31e4a again (01:08:14). No artifact event names the canonical path at either moved hash; the window's "
                    "class_separation artifact events are worker-local candidate copies. Independent pinned regression on the "
                    "worker-07 27-fixture corpus: c266dbecaa87 17/17 leaks + 10/10 controls, e2d24b927ee8 same, e36b0d644ca7 same; "
                    "0 FP/FN at all three. Corpus-level only; does not adjudicate worker-049's adversarial cue-carrying FN set; "
                    "advisory at pinned bytes, adopts nothing. Review target itself did not move.",
         "hash_bound": True, "blocking": False},
        {"id": "F-04", "severity": "disposition", "field": "schemas/af_scc_c0_vacuum.yaml:316 (rev27 soft flag)",
         "finding": "The rev27 candidate-variant class-token soft flag near line 316 is NOT reproducible at rev29 bytes. Line 316 "
                    "is the provenance concept row 'Kerr family and its maximal analytic extension ...' with identifier null; a "
                    "whole-document scan finds zero class-id-shaped tokens outside the frozen four; variant tokens CH/H2LOC/"
                    "DISTRIBUTIONAL appear only with parent_class/variant_id/is_this_class context. Disposition: annotation "
                    "(rev9 conversion), not a leak.",
         "hash_bound": True, "blocking": False},
        {"id": "F-05", "severity": "gate-blind-spot", "field": "artifacts/formulation/tools/check_class_schema.py",
         "finding": "Measured gate blind spots, confirmed by control mutants: the canonical structural gate passes (a) a mutant "
                    "with a corrupted f0_binding declared hash and (b) a mutant carrying a foreign class-id-shaped token "
                    "(AF-SCC-C0-VAC-GEN-STRONG), both of which this instrument rejects. Class-semantics mutants (m1,m2,m4,m5,m7) "
                    "are rejected by both instruments. The gate remains necessary but not sufficient for the binding chain; the "
                    "r3 reviewers' measured-hash discipline is load-bearing.",
         "hash_bound": True, "blocking": False},
    ]

    checklist = {
        "sha256_measured_before_and_after": True,
        "class_leakage_c0_c2": "none found; conclusion_type scc_c0_future_inextendibility != sibling scc_c2_future_inextendibility; "
                               "extension axes C0/none/future; composite-regularity scan clean in non-exempt fields",
        "conclusion_inflation": "none; epistemic_status open_problem, promotion_rule present, no theorem wording in conclusion",
        "assumption_completeness": "required slots present; unresolved citations and items declared (see F-02)",
        "decidable_falsifier": "tier_1 refutes this class with 4 machine-checkable steps and an explicit non-machine-checkable "
                               "non-meagerness step; tier_2 labelled refutes_strengthening_only",
        "quantifier_topology_binding": "D0-D3 resolve; comeager G_r precedes data; last quantifier is the negated extension "
                                       "existential; negation_normal_form is the correct negation in a Baire space",
        "consistency_evidence_binding": "f0_binding declared 0abb9ed8a961 == live; consistency evidence 9e335e9ba1bf == live and "
                                        "reports consistent=True; isolated canonical checker rerun CONSISTENT (4 classes, 0 divergences), "
                                        "byte-identical output",
        "frozen_pin_chain": "FROZEN.json 815e08079aefbc; per-file pins for canonical and authoring C0 both == b2ab6acb2bbe == measured",
        "soft_flag_316": "disposed annotation (F-04)",
        "blind": "no F2b verdict file was read before this verdict was written; only the target artifact, its C2 sibling, the F0 "
                 "taxonomy, the FROZEN manifest, the controller handoff/map metadata and the assignment cards were read",
    }

    verdict = {
        "review_id": "W072-F2B-REVIEW-REV29-01",
        "task_id": "W072-F2B-REVIEW-REV29-01",
        "target_id": "F2b",
        "node_id": "F2b",
        "gate": "G-FORM",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "reviewer": "worker-072",
        "reviewer_role": "independent non-author (worker-072 authored no F2b artifact)",
        "blind": True,
        "verdict": "accept",
        "score": 4.0,
        "reviewed_path": "schemas/af_scc_c0_vacuum.yaml",
        "reviewed_mirror": "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
        "reviewed_sha256": report["target"]["sha256"],
        "reviewed_frozen_path": "artifacts/formulation/FROZEN.json",
        "reviewed_frozen_sha256": sha(frozen_path),
        "reviewed_frozen_revision": 29,
        "hash_stable_before_after": True,
        "hard_failures": [],
        "findings": findings,
        "checklist": checklist,
        "instrument": {
            "path": "artifacts/worker-072/f2b_review/check_f2b.py",
            "sha256": sha(HERE / "check_f2b.py"),
            "checks_pass": report["n_pass"], "checks_fail": report["n_fail"],
            "canonical_gate_verdict": report["canonical_gate"]["verdict"],
            "canonical_gate_failed_rules": report["canonical_gate"]["failed_rules"],
            "report_path": "artifacts/worker-072/f2b_review/report.json",
            "report_sha256": sha(HERE / "report.json"),
        },
        "controls": {
            "summary_path": "artifacts/worker-072/f2b_review/controls/controls_summary.json",
            "summary_sha256": sha(HERE / "controls/controls_summary.json"),
            "mutants_discriminated": sum(1 for r in controls["controls"] if r["instrument_discriminates"]),
            "mutants_total": len(controls["controls"]),
            "null_control_clean": controls["null_control_clean"],
            "gate_blind_spots_confirmed": controls["gate_blind_spots_confirmed"],
        },
        "classsep_regression_addendum": {
            "runner": "artifacts/worker-072/f2b_review/classsep_pinned_regression.py",
            "runner_sha256": sha(HERE / "classsep_pinned_regression.py"),
            "corpus": "artifacts/worker-07/class_separation_falsification/results.json",
            "live_detector_at_measurement": {"path": "research_map/class_separation.py",
                                             "sha256": "e36b0d644ca75b1efc291b44a3188facb7839d81790073341431f3bb77b86eed",
                                             "mtime": "2026-09-12T01:06:12+08:00"},
            "live_detector_at_verdict_assembly": {"path": "research_map/class_separation.py",
                                                  "sha256": sha(live_det), "mtime": mtime_iso(live_det)},
            "drift_witness": {"path": "artifacts/worker-072/f2b_review/detector_drift_witness.json",
                              "sha256": sha(HERE / "detector_drift_witness.json")},
            "active_frozen_pin": "c266dbceca87fb996bd76a774145ef511cbf2aae190d9f423167d3200783a920 (node A1, frozen 23:30:20)",
            "pinned_results": regs,
            "scope_limit": "worker-07 27-fixture corpus only; does not cover worker-049's adversarial cue-carrying FN set; "
                           "advisory, adopts no detector revision",
        },
        "evidence_refs": [
            f"schemas/af_scc_c0_vacuum.yaml#{report['target']['sha256'][:12]}",
            f"artifacts/formulation/FROZEN.json#{sha(frozen_path)[:12]}",
            f"research_map/formulation_taxonomy.yaml#{sha(f0_path)[:12]}",
            f"artifacts/formulation/evidence/taxonomy_consistency.json#{sha(ce_path)[:12]}",
            f"artifacts/worker-072/f2b_review/report.json#{sha(HERE / 'report.json')[:12]}",
            f"artifacts/worker-072/f2b_review/controls/controls_summary.json#{sha(HERE / 'controls/controls_summary.json')[:12]}",
            "research_map/events.jsonl",
            "research_map/ASTRA_HANDOFF.md",
        ],
        "falsifier": "Re-measure schemas/af_scc_c0_vacuum.yaml: any hash other than "
                     "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c, a mirror/canonical byte difference, "
                     "a FROZEN rev29 pin that no longer equals live bytes and the declared f0/consistency hashes that no longer "
                     "resolve, a class-id-shaped token outside the frozen four, a C2 regularity assertion inside "
                     "extension_predicate or the conclusion, or a failing re-run of "
                     "artifacts/worker-072/f2b_review/check_f2b.py (33 checks) voids this accept. A defect in the motivating "
                     "Kerr obstruction (F-01) lowers the score but is explicitly non-blocking at this gate.",
        "authority_note": "Worker event. This verdict does not set node status, validation_status=passed, or any gate verdict; "
                          "the audit lead assembles coverage and Astra records the gate.",
        "created_at": subprocess.run(["date", "-Is"], capture_output=True, text=True).stdout.strip(),
    }
    VERDICT.write_text(json.dumps(verdict, indent=2) + "\n")

    manifest_files = [
        "check_f2b.py", "run_review.py", "report.json", "controls/controls_summary.json",
        "classsep_pinned_regression.py", "detector_drift_witness.json", "make_verdict.py",
        "emit_checkpoint_and_events.py",
        "pins/af_scc_c0_vacuum.rev29.yaml", "pins/FROZEN.rev29.json",
        "classsep_pins/class_separation.c266dbecaa87.py", "classsep_pins/class_separation.e2d24b927ee8.py",
        "classsep_pins/class_separation.e36b0d644ca7.py", "classsep_pins/regression.c266dbecaa87.json",
        "classsep_pins/regression.e2d24b927ee8.json", "classsep_pins/regression.e36b0d644ca7.json",
    ]
    manifest = {"task_id": "W072-F2B-REVIEW-REV29-01", "reviewer": "worker-072",
                "target_sha256": report["target"]["sha256"],
                "files": {f: sha(HERE / f) for f in manifest_files},
                "verdict_path": "reviews/F2b-review-worker-072-rev29.json",
                "verdict_sha256": sha(VERDICT)}
    (HERE / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"verdict": verdict["verdict"], "score": verdict["score"],
                      "verdict_sha256": manifest["verdict_sha256"], "manifest_sha256": sha(HERE / "MANIFEST.json"),
                      "target": verdict["reviewed_sha256"]}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
