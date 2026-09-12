#!/usr/bin/env python3
"""W066-REV25-VERDICT-01 step 2: independent acceptance replication at FROZEN rev25.

Re-implements the two-stage acceptance measurement (structural gate + semantic auditor)
from the tool interfaces, rather than calling artifacts/formulation/tools/run_acceptance.py
(which rewrites a frozen evidence file). All inputs come from pinned/ and every pinned byte
is re-verified before use. Outputs:
  evidence/replica_verdicts.json       raw per-fixture stage results
  evidence/acceptance_comparison.json  replica vs frozen acceptance_pipeline_report.json
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
PINNED = HERE / "pinned"
EVID = HERE / "evidence"
CST = timezone(timedelta(hours=8))
GATE_A = PINNED / "tools/check_class_schema.py"
GATE_B = PINNED / "tools/spec_conformance_audit.py"
SPEC = PINNED / "tools/rule_spec.json"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def verify_pins(manifest: dict) -> list:
    bad = []
    for e in manifest["targets"] + manifest.get("gate_relative_copies", []):
        p = HERE / e["pinned"]
        if sha(p) != e["sha256_pinned"]:
            bad.append(e["pinned"])
    for c in manifest["corpus"]["fixtures"]:
        p = PINNED / "rebased_fixtures" / c["fixture"]
        if sha(p) != c["sha256_pinned"]:
            bad.append(f"pinned/rebased_fixtures/{c['fixture']}")
    return bad


def run_tool(args: list) -> dict:
    proc = subprocess.run(args, capture_output=True, text=True, timeout=300)
    try:
        rep = json.loads(proc.stdout)
    except json.JSONDecodeError:
        rep = {}
    return {"exit": proc.returncode, "verdict": rep.get("verdict"),
            "failed_rules": rep.get("failed_rules", []), "stdout_json": bool(rep),
            "stderr": proc.stderr.strip()[:300]}


def stage_a(target: Path) -> dict:
    r = run_tool([sys.executable, str(GATE_A), "--json", str(target)])
    r["escaped"] = r["exit"] == 0 and r["verdict"] == "pass"
    return r


def stage_b(target: Path) -> dict:
    r = run_tool([sys.executable, str(GATE_B), "--spec", str(SPEC), str(target)])
    r["escaped"] = (r["verdict"] == "accept") if r["verdict"] else r["exit"] == 0
    return r


def rows_for(paths: list, class_id_of=None) -> list:
    rows = []
    for p in paths:
        a, b = stage_a(p), stage_b(p)
        rows.append({
            "fixture": p.name,
            "class_id": (class_id_of or {}).get(p.name),
            "stage_a": {k: v for k, v in a.items() if k != "stdout_json"},
            "stage_b": {k: v for k, v in b.items() if k != "stdout_json"},
            "structural_pass": a["escaped"], "semantic_accept": b["escaped"],
            "union_escaped": a["escaped"] and b["escaped"],
        })
    return rows


def norm_sem(v) -> str:
    """run_acceptance.py prints the semantic stage as pass/fail; the auditor emits
    accept/reject. Normalise to a single token before comparing, or every row 'disagrees'
    for a purely lexical reason."""
    return "accept" if str(v).lower() in ("accept", "pass", "ok", "true") else "reject"


def main() -> int:
    manifest = json.loads((HERE / "pinned_manifest.json").read_text())
    bad = verify_pins(manifest)
    if bad:
        print("PIN VERIFICATION FAILED:", bad)
        return 2

    canon = [PINNED / "schemas/af_wcc_vacuum.yaml",
             PINNED / "schemas/af_scc_c2_vacuum.yaml",
             PINNED / "schemas/af_scc_c0_vacuum.yaml"]
    class_of = {
        "af_wcc_vacuum.yaml": "AF-WCC-VAC-GEN",
        "af_scc_c2_vacuum.yaml": "AF-SCC-C2-VAC-GEN",
        "af_scc_c0_vacuum.yaml": "AF-SCC-C0-VAC-GEN",
    }
    canonical_rows = rows_for(canon)
    for r in canonical_rows:
        r["class_id"] = class_of[r["fixture"]]

    controls = [PINNED / "rebased_fixtures" / f for f in manifest["corpus"]["controls"]]
    mutants = [PINNED / "rebased_fixtures" / f for f in manifest["corpus"]["mutants"]]
    control_rows = rows_for(controls)
    mutant_rows = rows_for(mutants)

    n = len(mutant_rows)
    structural_caught = sum(1 for r in mutant_rows if not r["structural_pass"])
    semantic_caught = sum(1 for r in mutant_rows if not r["semantic_accept"])
    union_caught = sum(1 for r in mutant_rows if not r["union_escaped"])
    replica = {
        "task_id": "W066-REV25-VERDICT-01",
        "generated_at": datetime.now(CST).isoformat(timespec="seconds"),
        "gate_a": {"path": "pinned/tools/check_class_schema.py", "sha256": sha(GATE_A)},
        "gate_b": {"path": "pinned/tools/spec_conformance_audit.py", "sha256": sha(GATE_B)},
        "spec": {"path": "pinned/tools/rule_spec.json", "sha256": sha(SPEC)},
        "canonical": canonical_rows,
        "controls": control_rows,
        "mutants": mutant_rows,
        "aggregates": {
            "total": n,
            "structural_caught": structural_caught,
            "semantic_caught": semantic_caught,
            "union_caught": union_caught,
            "union_escapes": [r["fixture"] for r in mutant_rows if r["union_escaped"]],
        },
        "verdict": "PASS" if (all(r["structural_pass"] and r["semantic_accept"] for r in canonical_rows)
                              and all(r["structural_pass"] and r["semantic_accept"] for r in control_rows)
                              and union_caught == n) else "FAIL",
    }
    (EVID / "replica_verdicts.json").write_text(json.dumps(replica, indent=2) + "\n")

    frozen = json.loads((PINNED / "evidence/acceptance_pipeline_report.json").read_text())
    frozen_controls = {r["control"]: r for r in frozen.get("controls", [])}
    comp = {
        "task_id": "W066-REV25-VERDICT-01",
        "generated_at": replica["generated_at"],
        "frozen_report": "pinned/evidence/acceptance_pipeline_report.json",
        "frozen_report_sha256": sha(PINNED / "evidence/acceptance_pipeline_report.json"),
        "canonical_agreement": [
            {"schema": r["fixture"],
             "frozen_structural": next((c["structural"] for c in frozen["canonical"] if c["schema"] == r["fixture"]), None),
             "replica_structural": "pass" if r["structural_pass"] else "fail",
             "frozen_semantic": next((c["semantic"] for c in frozen["canonical"] if c["schema"] == r["fixture"]), None),
             "replica_semantic": "accept" if r["semantic_accept"] else "reject",
             "agree": (next((c["structural"] for c in frozen["canonical"] if c["schema"] == r["fixture"]), None) == ("pass" if r["structural_pass"] else "fail")
                       and norm_sem(next((c["semantic"] for c in frozen["canonical"] if c["schema"] == r["fixture"]), None)) == ("accept" if r["semantic_accept"] else "reject"))}
            for r in canonical_rows],
        "controls_agreement": [
            {"control": r["fixture"],
             "frozen_structural": frozen_controls.get(r["fixture"], {}).get("structural"),
             "replica_structural": "pass" if r["structural_pass"] else "fail",
             "frozen_semantic": frozen_controls.get(r["fixture"], {}).get("semantic"),
             "replica_semantic": "accept" if r["semantic_accept"] else "reject",
             "agree": frozen_controls.get(r["fixture"], {}).get("structural") == ("pass" if r["structural_pass"] else "fail")
                      and norm_sem(frozen_controls.get(r["fixture"], {}).get("semantic")) == ("accept" if r["semantic_accept"] else "reject")}
            for r in control_rows],
        "mutant_aggregates": {
            "frozen": frozen["mutants"],
            "replica": {"total": n, "structural_caught": structural_caught, "semantic_caught": semantic_caught,
                        "union_caught": union_caught},
            "agree": (frozen["mutants"]["total"] == n
                      and frozen["mutants"]["structural_caught"] == structural_caught
                      and frozen["mutants"]["semantic_caught"] == semantic_caught
                      and frozen["mutants"].get("union_caught") == union_caught),
        },
        "verdict_agreement": frozen["verdict"] == replica["verdict"],
    }
    comp["overall_agree"] = (all(c["agree"] for c in comp["canonical_agreement"])
                             and all(c["agree"] for c in comp["controls_agreement"])
                             and comp["mutant_aggregates"]["agree"] and comp["verdict_agreement"])
    (EVID / "acceptance_comparison.json").write_text(json.dumps(comp, indent=2) + "\n")

    print(f"replica verdict={replica['verdict']} | canonical "
          f"{sum(1 for r in canonical_rows if r['structural_pass'] and r['semantic_accept'])}/3 | "
          f"controls {sum(1 for r in control_rows if r['structural_pass'] and r['semantic_accept'])}/{len(control_rows)} | "
          f"union caught {union_caught}/{n}")
    print(f"agreement with frozen report: {comp['overall_agree']}")
    return 0 if comp["overall_agree"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
