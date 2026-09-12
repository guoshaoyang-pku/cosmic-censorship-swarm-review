#!/usr/bin/env python3
"""Regression runner: score class_separation against worker-07's 27-fixture corpus.

  python3 runtime/bin/classsep_regression.py [--verbose]

Ground truth (`is_class_merge`) comes from
artifacts/worker-07/class_separation_falsification/results.json, which was recorded
independently of the checker's regexes. Exit 0 only when every genuine merge is
detected and no legitimate document is flagged.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "research_map"))
import class_separation as cs  # noqa: E402

CORPUS = ROOT / "artifacts/worker-07/class_separation_falsification"
TMP = ROOT / "runtime/state/classsep_regression"


def main(verbose: bool):
    results = json.loads((CORPUS / "results.json").read_text())
    TMP.mkdir(parents=True, exist_ok=True)
    tp = fp = tn = fn = 0
    rows = []
    for fx in results["fixtures"]:
        path = ROOT / fx["fixture_path"]
        if not path.exists():
            rows.append((fx["id"], "MISSING", "?", "?")); continue
        m = json.loads(path.read_text())
        detected = cs.findings_for_map(m)
        # artifact-content fixtures: class_separation scans them via the node artifact path
        # (replicate audit_evidence behaviour here)
        for g in m.get("groups", []):
            for n in g.get("nodes", []):
                art = n.get("artifact")
                if art and (ROOT / art).is_file():
                    detected += cs.findings_for_text((ROOT / art).read_text(errors="replace"), f"artifact {art}")
        got = bool(detected)
        truth = bool(fx["is_class_merge"])
        if truth and got: tp += 1; cls = "TP"
        elif truth and not got: fn += 1; cls = "FN-MISSED"
        elif not truth and got: fp += 1; cls = "FP-SPURIOUS"
        else: tn += 1; cls = "TN"
        rows.append((fx["id"], cls, fx.get("surface"), (detected[0][:110] if detected else "")))
    for r in rows:
        if verbose or not r[1] in ("TP", "TN"):
            print(f"{r[0]:<40} {r[1]:<12} {str(r[2]):<16} {r[3]}")
    n_leaks = tp + fn
    n_ctrl = tn + fp
    print(f"\nleaks detected {tp}/{n_leaks}   controls clean {tn}/{n_ctrl}   (FP {fp}, FN {fn})")
    ok = (fn == 0 and fp == 0)
    print("VERDICT:", "PASS" if ok else "DEFECTIVE")
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--verbose", action="store_true")
    a = ap.parse_args()
    sys.exit(main(a.verbose))
