#!/usr/bin/env python3
"""Assemble the W069 F2a independent-verdict report from the frozen snapshot.

Runs (all outputs captured under raw/, exit codes recorded):
  - check_f2a_independent.py --selftest          (independent criteria + 12 mutation controls)
  - artifacts/formulation/tools/check_class_schema.py --json   (canonical structural gate,
                                                                 snapshot and canonical path)
  - artifacts/formulation/tools/run_acceptance.py              (canonical two-stage acceptance)
  - artifacts/formulation/tools/verify_frozen.py               (FROZEN rev25 drift check)
  - runtime/bin/classsep_regression.py                         (class-separation regression)
  - research_map/audit_evidence.py                             (informational; known claim-prose
                                                                false positive expected non-zero)

Writes report.json next to this script.  Never edits a formulation artifact; the only
shared-state write is run_acceptance.py's own deterministic evidence file, whose bytes are
asserted unchanged against the FROZEN pin.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
CST = timezone(timedelta(hours=8))
SNAP = HERE / "snapshot"
RAW = HERE / "raw"

SCHEMA = SNAP / "af_scc_c2_vacuum.yaml"
F0 = SNAP / "formulation_taxonomy.yaml"
SUPPLEMENT = REPO / "artifacts/formulation/formulation_taxonomy.yaml"
REGISTRY = SNAP / "VARIANT_REGISTRY.json"
FROZEN = SNAP / "FROZEN.json"
CANON = {
    "schema": REPO / "schemas/af_scc_c2_vacuum.yaml",
    "f0": REPO / "research_map/formulation_taxonomy.yaml",
    "supplement": SUPPLEMENT,
    "registry": REPO / "artifacts/formulation/VARIANT_REGISTRY.json",
}
ACCEPTANCE_EVIDENCE = REPO / "artifacts/formulation/evidence/acceptance_pipeline_report.json"
ACCEPTANCE_PIN = "9b7d6c8208d3beae2510c5c9c0a4bdaf7ede8adb277cd2a4f6f9cd0fd430f0c6"


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def run(cmd: list[str], out_name: str, expect_zero: bool = True) -> dict:
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO, timeout=900)
    body = (p.stdout or "") + (("\n[stderr]\n" + p.stderr) if p.stderr else "")
    (RAW / out_name).write_text(body)
    rec = {"cmd": " ".join(cmd), "exit": p.returncode, "stdout_sha256": hashlib.sha256(body.encode()).hexdigest(),
           "raw": f"raw/{out_name}", "expected_exit_zero": expect_zero,
           "ok": (p.returncode == 0) if expect_zero else None}
    return rec


def main() -> int:
    pre = {k: sha(v) for k, v in {"schema": SCHEMA, "f0": F0, "supplement": SUPPLEMENT,
                                  "registry": REGISTRY, "frozen": FROZEN}.items()}
    pre_canon = {k: sha(v) for k, v in CANON.items()}

    tools = {}
    tools["independent_checker_selftest"] = run(
        [sys.executable, str(HERE / "check_f2a_independent.py"), "--selftest",
         "--schema", str(SCHEMA), "--f0", str(F0), "--supplement", str(SUPPLEMENT),
         "--registry", str(REGISTRY), "--json"],
        "checker_selftest.json", expect_zero=True)
    tools["structural_gate_snapshot"] = run(
        [sys.executable, str(REPO / "artifacts/formulation/tools/check_class_schema.py"),
         "--json", str(SCHEMA)], "structural_gate_f2a_snapshot.json", expect_zero=True)
    tools["structural_gate_canonical"] = run(
        [sys.executable, str(REPO / "artifacts/formulation/tools/check_class_schema.py"),
         "--json", str(CANON["schema"])], "structural_gate_f2a_canonical.json", expect_zero=True)
    tools["acceptance"] = run([sys.executable, str(REPO / "artifacts/formulation/tools/run_acceptance.py")],
                              "acceptance_pipeline.txt", expect_zero=True)
    tools["verify_frozen"] = run([sys.executable, str(REPO / "artifacts/formulation/tools/verify_frozen.py")],
                                 "verify_frozen.txt", expect_zero=True)
    tools["classsep_regression"] = run([sys.executable, str(REPO / "runtime/bin/classsep_regression.py")],
                                       "classsep_regression.txt", expect_zero=True)
    tools["audit_evidence_informational"] = run(
        [sys.executable, str(REPO / "research_map/audit_evidence.py")],
        "audit_evidence_stdout.txt", expect_zero=False)

    acceptance_bytes_pin_ok = sha(ACCEPTANCE_EVIDENCE) == ACCEPTANCE_PIN

    selftest = json.loads((RAW / "checker_selftest.json").read_text())
    structural_snap = json.loads((RAW / "structural_gate_f2a_snapshot.json").read_text())
    structural_canon = json.loads((RAW / "structural_gate_f2a_canonical.json").read_text())

    post = {k: sha(v) for k, v in {"schema": SCHEMA, "f0": F0, "supplement": SUPPLEMENT,
                                   "registry": REGISTRY, "frozen": FROZEN}.items()}
    post_canon = {k: sha(v) for k, v in CANON.items()}
    drift = {k: {"pre": pre_canon[k], "post": post_canon[k], "drifted": pre_canon[k] != post_canon[k]}
             for k in CANON}
    snapshot_equals_canonical = {k: pre[k] == pre_canon[k] for k in ("schema", "f0", "registry")}

    advisory = [c for c in selftest["checks"] if c["severity"] == "advisory" and not c["ok"]]
    hard_failures = selftest["hard_failures"]

    report = {
        "schema_version": "0.1",
        "artifact_type": "independent_schema_verdict",
        "task_id": "W069-F2A-REV11-VERDICT-01",
        "generated_at": now(),
        "actor": "worker-069",
        "reviewer": "worker-069",
        "node_id": "F2a",
        "class_id": "AF-SCC-C2-VAC-GEN",
        "class_ids": ["AF-SCC-C2-VAC-GEN"],
        "gate": "G-FORM",
        "target_artifact": "schemas/af_scc_c2_vacuum.yaml",
        "verdict": "accept" if (not hard_failures and selftest["verdict"] == "PASS"
                                and all(t["ok"] for k, t in tools.items() if k != "audit_evidence_informational")
                                and acceptance_bytes_pin_ok and not any(d["drifted"] for d in drift.values()))
                   else "revise",
        "score": 4.0,
        "hard_failures": hard_failures,
        "findings": [
            "ADVISORY G25: the C2 conclusion token is not identical across the three governing documents "
            "-- schema conclusion.conclusion_type='scc_c2_future_inextendibility', canonical F0 "
            "classes.AF-SCC-C2-VAC-GEN.axes.conclusion_type='strong_cosmic_censorship_C2', rubric A0 "
            "frozen_classes conclusion_primary='C2_inextendibility_of_maximal_development'. The axis check "
            "(SCC/C2/vacuum/future/one-ended AF) shows the three denote the same conclusion, but G-FORM's "
            "'conclusion_primary chosen from the class allowed set' is checkable only through a mapping, "
            "not by direct membership in one machine-readable vocabulary. Recommend one registry entry "
            "mapping the three spellings; no schema edit required for this review.",
            "ADVISORY G23: class_contract_pointer resolves to the FROZEN-pinned authoring supplement "
            "artifacts/formulation/formulation_taxonomy.yaml (sha256 c8e979a1eb48), not to the canonical F0 "
            "(276009f4f63d). Both were read; the C2 axes agree (G24). The controller's audit_evidence.py at "
            "this instant still reports a soft dual-tree divergence between the two paths, and CF-13 "
            "'one frozen revision per artifact' therefore remains open at F0 level; it does not falsify the "
            "F2a checks bound to the canonical F0 hash.",
            "INFO: canonical F0 status is draft_unverified and the schema keeps four unresolved items "
            "(diffeomorphism-quotient genericity, meagreness of excluded families, non-vacuity witness "
            "membership in G, nonlinear extension regularity across a Cauchy horizon). Unresolved items are "
            "recorded rather than dropped (G27) and are limits on what the schema can support, not G-FORM "
            "failures.",
            "INFO: audit_evidence.py exits 1 on the known claims[36] prose false positive (CF-16) plus the "
            "F0 dual-tree soft flag; neither is a finding against the F2a bytes.",
        ],
        "independence": {
            "author_of_target": "astra-lead-formulation",
            "reviewer_is_author": False,
            "authored_by_any_of_this_verdict": False,
            "checks_written_from": "evaluation_rubric.yaml G-FORM criteria + rubric frozen_classes contract",
            "author_self_tests_used_as_evidence": False,
            "mutation_controls": f"{selftest['controls_passed']}/{selftest['controls_total']} (positive + 12 field mutations)",
            "disclosure": "worker-069 read the schema blocks before finalising the checks (unavoidable: the "
                          "fields are the data); the 12 mutation controls bound the risk that the checks are "
                          "satisfied trivially.",
        },
        "inputs": {
            "snapshot": {k: {"path": str(v.relative_to(REPO)), "sha256": pre[k]} for k, v in
                         {"schema": SCHEMA, "f0": F0, "supplement": SUPPLEMENT, "registry": REGISTRY,
                          "frozen": FROZEN}.items()},
            "snapshot_equals_canonical_at_read": snapshot_equals_canonical,
            "canonical_pre": pre_canon,
            "canonical_post": post_canon,
            "drift_during_run": drift,
            "acceptance_evidence_pin": {"path": str(ACCEPTANCE_EVIDENCE.relative_to(REPO)),
                                        "expected_sha256": ACCEPTANCE_PIN,
                                        "measured_sha256": sha(ACCEPTANCE_EVIDENCE),
                                        "unchanged": acceptance_bytes_pin_ok},
        },
        "checks": selftest["checks"],
        "checks_passed": selftest["checks_passed"],
        "checks_total": selftest["checks_total"],
        "controls": selftest["controls"],
        "repo_tools": tools,
        "repo_tool_verdicts": {
            "structural_gate_snapshot": structural_snap.get("verdict"),
            "structural_gate_canonical": structural_canon.get("verdict"),
            "structural_report_identical_except_path": (
                {k: v for k, v in structural_snap.items() if k != "schema"}
                == {k: v for k, v in structural_canon.items() if k != "schema"}),
            "acceptance": "PASS" if "ACCEPTANCE: PASS" in (RAW / "acceptance_pipeline.txt").read_text() else "not PASS",
            "verify_frozen": (RAW / "verify_frozen.txt").read_text().strip().splitlines()[-1][:120],
            "classsep_regression": "PASS" if "VERDICT: PASS" in (RAW / "classsep_regression.txt").read_text() else "not PASS",
        },
        "falsifier": (
            "Re-run artifacts/worker-069/f2a_rev11_independent_verdict/run_verdict.py on a byte-identical copy "
            "of schemas/af_scc_c2_vacuum.yaml (sha256 b6123750b37d8bee1e92eeb025979a6afdf3b29a33331a9d8499e21398d13fb2). "
            "This verdict is falsified if: (a) any check recorded ok=true returns ok=false on those bytes; "
            "(b) any of the 12 mutation controls escapes its expected failing check; (c) the canonical schema "
            "or declared-F0 sha256 differs from the pinned values at re-measurement (drift voids the binding, "
            "not the checks); or (d) check_class_schema.py / run_acceptance.py / verify_frozen.py exits "
            "non-zero or reports non-pass on the pinned bytes. A reviewer showing that the three G25 "
            "conclusion-type tokens denote different conclusions (not one conclusion in three vocabularies) "
            "falsifies the advisory disposition and forces a revise verdict."
        ),
        "non_claims": [
            "Not a gate verdict: G-FORM is owned by the controller and group leads; worker events cannot set "
            "it. This is one independent reviewer verdict at one measured hash.",
            "Not a node transition: F2a status is unchanged.",
            "No claim about the truth of strong cosmic censorship, about L1 citation support, or about the "
            "physical well-posedness of the class.",
            "Binds only the pinned bytes; a later canonical revision voids it.",
        ],
        "evidence_refs": [
            "schemas/af_scc_c2_vacuum.yaml#b6123750b37d",
            "research_map/formulation_taxonomy.yaml#276009f4f63d",
            "artifacts/formulation/FROZEN.json#af24e9c39606",
            "artifacts/formulation/VARIANT_REGISTRY.json#5eb42f9a384a",
            "evaluation_rubric.yaml#d748a9e3574e",
        ],
    }
    out = HERE / "report.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"report": str(out.relative_to(REPO)), "sha256": sha(out),
                      "verdict": report["verdict"], "checks": f"{report['checks_passed']}/{report['checks_total']}",
                      "controls": f"{selftest['controls_passed']}/{selftest['controls_total']}",
                      "hard_failures": len(hard_failures), "advisories": len(advisory),
                      "drift": any(d["drifted"] for d in drift.values())}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
