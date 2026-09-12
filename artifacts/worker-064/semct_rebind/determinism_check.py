#!/usr/bin/env python3
"""W064-SEMCT-REBIND-01 determinism control.

Re-runs the rebound manifest a second time through the same runner/redirect
mechanism and compares the per-fixture `observed` records and the summary against
`rebound_observed.json`.  `run_at` is the only field allowed to differ.

Falsifier: any difference in a per-fixture observed record or in the summary
invalidates the single-run numbers in report.json until the cause is explained.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

WORK = Path(__file__).resolve().parent


def load_audit():
    spec = importlib.util.spec_from_file_location("w064_audit", WORK / "semct_rebind_audit.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    audit = load_audit()
    if not (WORK / "suite_copy" / "fixtures").exists():
        print("suite_copy missing; run semct_rebind_audit.py first", file=sys.stderr)
        return 2
    second = audit.run_suite(WORK / "manifest_rebound.json", WORK / "rebound_observed_2.json", "rebound_rerun")
    first = json.loads((WORK / "rebound_observed.json").read_text())
    two = second["observed"]
    diffs = []
    if first["summary"] != two["summary"]:
        diffs.append("summary differs")
    if first["validity"] != two["validity"]:
        diffs.append("validity differs")
    if first["stage_hashes"] != two["stage_hashes"]:
        diffs.append("stage_hashes differ")
    a = {r["test_id"]: r["observed"] for r in first["results"]}
    b = {r["test_id"]: r["observed"] for r in two["results"]}
    if set(a) != set(b):
        diffs.append(f"test_id sets differ: {sorted(set(a) ^ set(b))}")
    for k in sorted(set(a) & set(b)):
        if a[k] != b[k]:
            diffs.append(f"observed differs for {k}")
    out = {
        "task_id": audit.TASK_ID,
        "checked_at": audit.now(),
        "second_run_exit": second["exit"],
        "first_run_at": first.get("run_at"),
        "second_run_at": two.get("run_at"),
        "compared_test_ids": len(a),
        "differences": diffs,
        "deterministic": not diffs,
        "falsifier": "any entry in differences invalidates the single-run numbers until explained",
    }
    (WORK / "determinism_check.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))
    return 0 if not diffs else 1


if __name__ == "__main__":
    sys.exit(main())
