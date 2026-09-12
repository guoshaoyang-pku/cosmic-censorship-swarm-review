#!/usr/bin/env python3
"""Black-box differential: this gate (FORM-GATE-01) vs the lead's frozen gate.

The lead's tool is invoked as a separate process and read from its JSON stdout only; it is never
imported and its source is not consulted (independence of the primary implementation is
preserved). Reports per-target verdict agreement over the 3 conforming fixtures, 24 mutants,
6 rephrased mutants and the 3 frozen canonical schemas. Writes differential_report.json.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
GATE = HERE / "check_class_schema.py"
FIX = HERE / "fixtures"
LEAD = REPO / "artifacts" / "formulation" / "tools" / "check_class_schema.py"

spec = importlib.util.spec_from_file_location("check_class_schema", GATE)
ccs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ccs)


def mine(path: Path, cid=None):
    res = ccs.evaluate(path, cid)
    return res["verdict"], res.get("failed_rules", [])


def theirs(path: Path):
    proc = subprocess.run([sys.executable, str(LEAD), str(path), "--json"],
                          capture_output=True, text=True, timeout=300)
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return "error", [f"exit={proc.returncode} stderr={proc.stderr.strip()[:120]}"], proc.returncode
    return payload.get("verdict", "error"), payload.get("failed_rules", []), proc.returncode


def sha(p: Path):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    manifest = json.loads((FIX / "manifest.json").read_text())
    targets = []
    for name, meta in manifest["positives"].items():
        targets.append(("positive", name, Path(meta["path"]), meta["class_id"], "pass"))
    for name, meta in manifest["mutants"].items():
        targets.append(("mutant", name, Path(meta["path"]), meta["class_id"], "fail"))
    for name, meta in manifest["rephrased"].items():
        targets.append(("rephrased", name, Path(meta["path"]), meta["class_id"], None))
    frozen = json.loads((REPO / ccs.FROZEN_MANIFEST).read_text()).get("files", {})
    for cid, rel in ccs.CANONICAL.items():
        p = REPO / rel
        if p.exists():
            targets.append(("canonical", Path(rel).name, p, cid, "pass"))

    rows, agree, disagree = [], 0, []
    for kind, name, path, cid, expected in targets:
        mv, mf = mine(path, cid)
        tv, tf, trc = theirs(path)
        same = mv == tv
        agree += int(same)
        row = {"kind": kind, "name": name, "class_id": cid, "my_verdict": mv,
               "my_failed_rules": mf, "lead_verdict": tv, "lead_failed_rules": tf,
               "agree": same, "expected": expected,
               "my_sha256": sha(path)}
        if not same:
            disagree.append(row)
        rows.append(row)

    summary = {
        "targets": len(rows),
        "agreement": agree,
        "agreement_rate": round(agree / len(rows), 4) if rows else 0.0,
        "positives_both_pass": all(r["my_verdict"] == "pass" and r["lead_verdict"] == "pass"
                                   for r in rows if r["kind"] == "positive"),
        "canonical_both_pass": all(r["my_verdict"] == "pass" and r["lead_verdict"] == "pass"
                                   for r in rows if r["kind"] == "canonical"),
        "my_mutants_all_rejected": all(r["my_verdict"] == "fail" for r in rows
                                       if r["kind"] == "mutant"),
        "lead_mutants_rejected": sum(1 for r in rows
                                     if r["kind"] == "mutant" and r["lead_verdict"] == "fail"),
        "mutants_total": sum(1 for r in rows if r["kind"] == "mutant"),
        "disagreements": [{"kind": r["kind"], "name": r["name"], "mine": r["my_verdict"],
                           "lead": r["lead_verdict"], "my_rules": r["my_failed_rules"],
                           "lead_rules": r["lead_failed_rules"]} for r in disagree],
    }
    report = {
        "differential": "form_gate_01_vs_lead_frozen_tool",
        "generated_at": __import__("time").strftime("%Y-%m-%dT%H:%M:%S%z"),
        "my_gate_sha256": sha(GATE),
        "lead_gate_sha256": sha(LEAD),
        "method": "black-box: lead tool executed as a subprocess, JSON stdout parsed; no import",
        "summary": summary,
        "rows": rows,
    }
    (HERE / "differential_report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["positives_both_pass"] and summary["canonical_both_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
