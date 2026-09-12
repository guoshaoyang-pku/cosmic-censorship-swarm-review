#!/usr/bin/env python3
"""Semantic contract-test runner for `schemas/semantic_contract_tests/`.

Runs every fixture in `manifest.json` through the two repo stages:

  stage A / structural        artifacts/formulation/tools/check_class_schema.py --json <fixture>
  stage B / semantic baseline artifacts/worker-06/spec_conformance_audit.py <fixture> --json <out>
  stage B / semantic hardened same auditor with --hardened

and records the observed verdict next to the expected verdict. This runner is
calibration evidence routed to G-AUDIT; it is NOT a gate and defines no gate id.

Exit codes
  0  run valid: integrity ok, every control (frozen + conforming canonical)
     accepted by both stages
  2  integrity failure: missing/tampered fixture, or a stage produced no verdict
  3  integrity ok but validity failed: at least one control rejected by a stage
     (the suite must not be used as calibration evidence until the lead resolves
     the adjudication item named in the output)

Usage
  python3 schemas/semantic_contract_tests/run_contract_tests.py
  python3 schemas/semantic_contract_tests/run_contract_tests.py --update-manifest
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
MANIFEST = HERE / "manifest.json"
OBSERVED = HERE / "observed_verdicts.json"
STRUCT = REPO / "artifacts" / "formulation" / "tools" / "check_class_schema.py"
SEM = REPO / "artifacts" / "worker-06" / "spec_conformance_audit.py"
CST = timezone(timedelta(hours=8))


def now():
    return datetime.now(CST).isoformat(timespec="seconds")


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def run_structural(target: Path) -> dict:
    proc = subprocess.run([sys.executable, str(STRUCT), "--json", str(target)],
                          capture_output=True, text=True, timeout=180)
    try:
        rep = json.loads(proc.stdout[proc.stdout.index("{"):])
    except (ValueError, json.JSONDecodeError):
        rep = {}
    return {"tool": "structural", "exit": proc.returncode,
            "verdict": rep.get("verdict", "no_verdict"),
            "failed_rules": rep.get("failed_rules", []),
            "accepted": proc.returncode == 0 and rep.get("verdict") == "pass",
            "rejected": rep.get("verdict") == "fail",
            "stderr": proc.stderr.strip()[:300]}


def run_semantic(target: Path, hardened: bool) -> dict:
    out = HERE / f".tmp_audit_{'h' if hardened else 'b'}_{target.stem}.json"
    cmd = [sys.executable, str(SEM), str(target), "--json", str(out)]
    if hardened:
        cmd.insert(-2, "--hardened")
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    rep = {}
    if out.exists():
        try:
            rep = json.loads(out.read_text())
        finally:
            out.unlink()
    return {"tool": "semantic_hardened" if hardened else "semantic_baseline",
            "exit": proc.returncode,
            "verdict": rep.get("verdict", "no_verdict"),
            "failed_rules": rep.get("failed_rules", []),
            "undecided_rules": rep.get("undecided_rules", []),
            "accepted": rep.get("verdict") == "accept",
            "rejected": rep.get("verdict") == "reject",
            "stderr": proc.stderr.strip()[:300]}


def stage_triplet(target: Path) -> dict:
    return {"structural": run_structural(target),
            "semantic_baseline": run_semantic(target, hardened=False),
            "semantic_hardened": run_semantic(target, hardened=True)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--update-manifest", action="store_true",
                    help="write observed verdicts back into manifest.json")
    args = ap.parse_args()

    if not MANIFEST.exists():
        print("FATAL: manifest.json missing", file=sys.stderr)
        return 2
    manifest = json.loads(MANIFEST.read_text())
    integrity_errors = []

    def process(entry: dict, expect: str):
        f = entry["fixture"]
        target = (HERE / f) if f.startswith("fixtures/") else (REPO / f)
        if not target.exists():
            integrity_errors.append(f"missing fixture {entry['fixture']}")
            return None
        got = sha(target)
        if got != entry["sha256"]:
            integrity_errors.append(f"sha mismatch {entry['fixture']}: {got[:12]} != {entry['sha256'][:12]}")
            return None
        stages = stage_triplet(target)
        if any(s["verdict"] == "no_verdict" for s in stages.values()):
            integrity_errors.append(f"stage produced no verdict for {entry['fixture']}")
        accepted_by = [k for k, s in stages.items() if s["accepted"]]
        rejected_by = [k for k, s in stages.items() if s["rejected"]]
        observed = "accept" if accepted_by else ("reject" if rejected_by else "undecided")
        adopted_reject = bool({"structural", "semantic_baseline"} & set(rejected_by))
        record = dict(entry)
        record["observed"] = {
            "verdict": observed,
            "accepted_by": accepted_by,
            "rejected_by": rejected_by,
            "stages": stages,
            "agrees_with_expected": observed == expect,
            "escapes_adopted_stages": expect == "reject" and not adopted_reject,
            "hardened_only_catch": (expect == "reject" and rejected_by == ["semantic_hardened"]),
        }
        return record

    results = []
    for e in manifest["fixtures"]:
        r = process(e, e["expected_verdict"])
        if r:
            results.append(r)
    for e in manifest["controls"]:
        r = process(e, e["expected_verdict"])
        if r:
            results.append(r)
    for e in manifest["conforming_canonical_controls"]:
        r = process(e, e["expected_verdict"])
        if r:
            results.append(r)

    if integrity_errors:
        print("INTEGRITY FAILURE:")
        for x in integrity_errors:
            print("  -", x)
        return 2

    mutants = [r for r in results if r["kind"] == "leak_mutant"]
    controls = [r for r in results if r["kind"] == "frozen_control"]
    conforming = [r for r in results if r["kind"] == "conforming_canonical"]

    def caught(rs, stage):
        return sum(1 for r in rs if stage in r["observed"]["rejected_by"])

    n = len(mutants)
    structural_caught = caught(mutants, "structural")
    baseline_caught = caught(mutants, "semantic_baseline")
    hardened_caught = caught(mutants, "semantic_hardened")
    escaped_adopted = [r["test_id"] for r in mutants if r["observed"]["escapes_adopted_stages"]]
    hardened_only = [r["test_id"] for r in mutants if r["observed"]["hardened_only_catch"]]
    controls_ok = all(c["observed"]["accepted_by"] and not c["observed"]["rejected_by"] for c in controls)
    conforming_ok = all(c["observed"]["accepted_by"] and not c["observed"]["rejected_by"] for c in conforming)

    adjudication = list(manifest.get("adjudication_items", []))
    for r in mutants:
        if r["observed"]["escapes_adopted_stages"]:
            adjudication.append({
                "item_id": f"ADJ-{r['test_id']}",
                "status": "needs_rule_adjudication" if r["observed"]["hardened_only_catch"] else "needs_new_rule",
                "owner": "astra-lead-formulation",
                "finding": (f"{r['fixture']} ({r['leak_family']}) is rejected by no adopted stage"
                            + (" and only by the proposed hardened set" if r["observed"]["hardened_only_catch"] else "")),
                "rules_tested": r["rules_tested"],
                "hardened_failed_rules": r["observed"]["stages"]["semantic_hardened"]["failed_rules"],
                "falsifier": "a fixture shown to be a legitimate formulation, or a rule that catches it and rejects no conforming control",
            })

    summary = {
        "mutants": n,
        "rephrased": sum(1 for r in mutants if r.get("rephrased")),
        "leak_families": len({r.get("leak_family") for r in mutants}),
        "structural_caught": structural_caught,
        "semantic_baseline_caught": baseline_caught,
        "semantic_hardened_caught": hardened_caught,
        "structural_escape_rate": round(1 - structural_caught / n, 4),
        "semantic_baseline_escape_rate": round(1 - baseline_caught / n, 4),
        "semantic_hardened_escape_rate": round(1 - hardened_caught / n, 4),
        "escaped_adopted_stages": escaped_adopted,
        "hardened_only_catches": hardened_only,
        "controls_accepted_both_stages": controls_ok,
        "conforming_canonical_accepted_both_stages": conforming_ok,
    }
    validity = {
        "valid_for_calibration": bool(controls_ok and conforming_ok),
        "controls_basis": "3 frozen corpus controls + 3 current canonical schemas",
        "blocking_adjudication": ([] if controls_ok else ["ADJ-CONTROL-STALENESS"]),
        "note": ("controls are frozen at corpus base; if a control is rejected the suite may not be used "
                 "as current-revision calibration evidence until the lead resolves the blocker"),
    }
    out = {
        "suite_id": manifest["suite_id"],
        "assignment": manifest["assignment"],
        "run_at": now(),
        "stage_hashes": {"structural": sha(STRUCT), "semantic": sha(SEM)},
        "manifest_sha256_at_run": sha(MANIFEST),
        "summary": summary,
        "validity": validity,
        "adjudication_required": adjudication,
        "results": results,
    }
    OBSERVED.write_text(json.dumps(out, indent=1) + "\n")

    if args.update_manifest:
        by_id = {r["test_id"]: r["observed"] for r in results}
        for e in manifest["fixtures"] + manifest["controls"] + manifest["conforming_canonical_controls"]:
            e["observed"] = by_id.get(e["test_id"])
        manifest["run_record"] = {
            "run_at": out["run_at"],
            "observed_verdicts": "observed_verdicts.json",
            "observed_verdicts_sha256": sha(OBSERVED),
            "stage_hashes": out["stage_hashes"],
            "summary": summary,
            "validity": validity,
        }
        MANIFEST.write_text(json.dumps(manifest, indent=1) + "\n")
        print(f"updated {MANIFEST}")

    print(f"run {out['run_at']}  stages {out['stage_hashes']['structural'][:12]}"
          f"/{out['stage_hashes']['semantic'][:12]}")
    print(f"mutants {n}: structural {structural_caught}/{n}, baseline {baseline_caught}/{n}, "
          f"hardened {hardened_caught}/{n}")
    print(f"controls accepted (frozen/canonical): {controls_ok}/{conforming_ok}")
    if not validity["valid_for_calibration"]:
        print("VALIDITY: INVALID for current-revision calibration -> see adjudication_required")
    return 0 if validity["valid_for_calibration"] else 3


if __name__ == "__main__":
    sys.exit(main())
