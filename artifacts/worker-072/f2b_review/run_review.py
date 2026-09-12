#!/usr/bin/env python3
"""Runner for W072-F2B-REVIEW-REV29-01.

Executes the independent instrument (check_f2b.py) on the canonical F2b schema and on a
battery of control mutants, executes the canonical formulation gate on the same inputs for
agreement/disagreement, and writes:
  report.json              - canonical instrument report + gate + bindings
  controls/controls_summary.json - mutant generation + expected/actual discrimination
"""
from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
from check_f2b import (  # noqa: E402
    DEFAULT_SCHEMA, DEFAULT_MIRROR, DEFAULT_FROZEN, GATE, EXPECTED_SHA, EXPECTED_FROZEN_SHA,
    FROZEN_CLASSES, Review, sha256_file,
)

CONTROLS = HERE / "controls"
MUTANTS = CONTROLS / "mutants"


def run_instrument(schema: Path, controls: bool):
    rv = Review(schema, DEFAULT_MIRROR, DEFAULT_FROZEN, EXPECTED_SHA, EXPECTED_FROZEN_SHA, controls=controls)
    res = rv.run()
    return {"schema": str(schema), "sha256_before": rv.sha_before, "checks": res,
            "n_fail": sum(1 for r in res if r["status"] == "FAIL"),
            "failing_ids": [r["id"] for r in res if r["status"] == "FAIL"],
            "verdict": "PASS" if not any(r["status"] == "FAIL" for r in res) else "FAIL"}


def run_gate(schema: Path):
    r = subprocess.run([sys.executable, str(GATE), "--json", str(schema)], capture_output=True, text=True)
    try:
        rep = json.loads(r.stdout)
        return {"verdict": rep.get("verdict"), "failed_rules": rep.get("failed_rules"),
                "failures": rep.get("failures")}
    except ValueError:
        return {"verdict": "error", "stdout": r.stdout[-300:], "stderr": r.stderr[-300:]}


def mutate(doc, kind):
    d = copy.deepcopy(doc)
    if kind == "m1_conclusion_type_c2":
        d["conclusion"]["conclusion_type"] = "scc_c2_future_inextendibility"
    elif kind == "m2_extension_regularity_c2":
        d["extension_predicate"]["frozen_regularity"] = "C2"
    elif kind == "m3_f0_hash_wrong":
        d["f0_binding"]["declared_f0_sha256"] = "0" * 64
    elif kind == "m4_composite_scope":
        d["scope_statement"] = str(d.get("scope_statement", "")) + " The class covers C0 or C2 extensions."
    elif kind == "m5_iplus_conclusion":
        d["i_plus"]["role"] = "conclusion"
        d["i_plus"]["in_conclusion"] = True
    elif kind == "m6_foreign_class_token":
        d["provenance"]["sources"].append(
            {"concept": "candidate stronger class", "identifier": "AF-SCC-C0-VAC-GEN-STRONG",
             "status": "unresolved", "needed_for": "provenance"})
    elif kind == "m7_c2_implies_c0_owed":
        d["implication_ledger"]["one_way_entailments"].append(
            {"from": "no proper future C2 extension", "to": "no proper future C0 metric extension",
             "relation": "entails", "reason": "control mutant: forbidden converse"})
    elif kind == "m8_clean_perturbation":
        d["revision_history"][-1]["notes"] = list(d["revision_history"][-1].get("notes") or []) + ["control: comment-only perturbation"]
    else:
        raise ValueError(kind)
    return d


MUTANT_EXPECT = {
    "m1_conclusion_type_c2": ["c2_conclusion_type_distinct"],
    "m2_extension_regularity_c2": ["c3_extension_axes"],
    "m3_f0_hash_wrong": ["b7_declared_f0_resolves", "b11_refresh_rule_satisfied"],
    "m4_composite_scope": ["c5_composite_ban"],
    "m5_iplus_conclusion": ["c7_axis_roles"],
    "m6_foreign_class_token": ["e1_no_foreign_class_ids"],
    "m7_c2_implies_c0_owed": ["c6_implication_direction"],
    "m8_clean_perturbation": [],
}
GATE_EXPECT = {
    "m1_conclusion_type_c2": ["R11"],
    "m2_extension_regularity_c2": ["R18"],
    "m3_f0_hash_wrong": [],
    "m4_composite_scope": ["R13"],
    "m5_iplus_conclusion": ["R09"],
    "m6_foreign_class_token": [],
    "m7_c2_implies_c0_owed": ["R16"],
    "m8_clean_perturbation": [],
}


def main():
    CONTROLS.mkdir(parents=True, exist_ok=True)
    MUTANTS.mkdir(parents=True, exist_ok=True)
    canon_doc = yaml.safe_load(DEFAULT_SCHEMA.read_text())

    canonical = run_instrument(DEFAULT_SCHEMA, controls=False)
    canonical_gate = run_gate(DEFAULT_SCHEMA)

    rows = []
    for kind, expect in MUTANT_EXPECT.items():
        doc = mutate(canon_doc, kind)
        p = MUTANTS / f"{kind}.yaml"
        p.write_text(yaml.safe_dump(doc, sort_keys=False, width=110))
        control_mode = kind != "m3_f0_hash_wrong"   # hash-chain mutant must actually fire the binding checks
        inst = run_instrument(p, controls=control_mode)
        gate = run_gate(p)
        missing = [e for e in expect if e not in inst["failing_ids"]]
        unexpected = [f for f in inst["failing_ids"] if f not in expect]
        gate_missing = [r for r in GATE_EXPECT[kind] if r not in (gate.get("failed_rules") or [])]
        rows.append({
            "mutant": kind, "path": str(p.relative_to(ROOT)), "sha256": sha256_file(p),
            "expected_fail_ids": expect, "actual_fail_ids": inst["failing_ids"],
            "instrument_discriminates": not missing,
            "unexpected_fail_ids": unexpected,
            "expected_gate_rules": GATE_EXPECT[kind], "gate_failed_rules": gate.get("failed_rules"),
            "gate_discriminates": not gate_missing,
            "gate_missing_rules": gate_missing,
        })

    blind_spots = [r["mutant"] for r in rows
                   if r["actual_fail_ids"] and not (r["gate_failed_rules"] or [])]
    summary = {
        "instrument": "artifacts/worker-072/f2b_review/check_f2b.py",
        "instrument_sha256": sha256_file(HERE / "check_f2b.py"),
        "canonical": {k: canonical[k] for k in ("schema", "sha256_before", "verdict", "n_fail", "failing_ids")},
        "canonical_gate": canonical_gate,
        "controls": rows,
        "null_control_clean": canonical["verdict"] == "PASS" and canonical_gate.get("verdict") == "pass",
        "all_mutants_discriminated": all(r["instrument_discriminates"] for r in rows),
        "gate_blind_spots_confirmed": blind_spots,
        "frozen_classes": FROZEN_CLASSES,
    }
    (CONTROLS / "controls_summary.json").write_text(json.dumps(summary, indent=2) + "\n")

    report = {
        "task_id": "W072-F2B-REVIEW-REV29-01",
        "reviewer": "worker-072",
        "target": {"path": "schemas/af_scc_c0_vacuum.yaml",
                   "mirror": "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
                   "class_id": "AF-SCC-C0-VAC-GEN", "node_id": "F2b", "gate": "G-FORM",
                   "sha256": canonical["sha256_before"],
                   "frozen_rev": 29,
                   "frozen_sha256": EXPECTED_FROZEN_SHA},
        "instrument": summary["instrument"],
        "instrument_sha256": summary["instrument_sha256"],
        "checks": canonical["checks"],
        "n_pass": sum(1 for c in canonical["checks"] if c["status"] == "PASS"),
        "n_fail": canonical["n_fail"],
        "canonical_gate": canonical_gate,
        "controls_summary": "artifacts/worker-072/f2b_review/controls/controls_summary.json",
        "controls": summary["controls"],
        "verdict": canonical["verdict"],
    }
    (HERE / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"canonical": report["verdict"], "n_pass": report["n_pass"], "n_fail": report["n_fail"],
                      "canonical_gate": canonical_gate.get("verdict"),
                      "all_mutants_discriminated": summary["all_mutants_discriminated"],
                      "gate_blind_spots_confirmed": summary["gate_blind_spots_confirmed"]}, indent=2))
    return 0 if report["verdict"] == "PASS" and summary["all_mutants_discriminated"] else 1


if __name__ == "__main__":
    sys.exit(main())
