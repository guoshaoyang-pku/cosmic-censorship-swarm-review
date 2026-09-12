#!/usr/bin/env python3
"""Calibration harness for research_map/audit_evidence.py  (worker-16, proposal support).

Why this exists
---------------
audit_evidence.py is the A1 gate that is supposed to (a) require on-disk artifacts for
done nodes, (b) enforce explicit gates + the numerics lock, and (c) prevent the four
frozen WCC/SCC classes from being merged. A detector is only useful if it is calibrated:
false positives burn lead attention, false negatives give false assurance. This harness
feeds labeled synthetic maps to audit_evidence.audit() and scores the observed hard/soft
signals against expected.json.

It does NOT modify audit_evidence.py and it does not claim any node complete. It is a
proposal-support artifact: the fix list it produces is for lead-audit to accept/reject.
The report pins the detector sha256, so a later revision invalidates the result rather
than silently changing it.

Run:
    python3 artifacts/worker-16/audit_calibration/run_calibration.py
    python3 artifacts/worker-16/audit_calibration/run_calibration.py --out /tmp/rep.json

Exit code 0 = every fixture's observed signals equal the expected signals.
Exit code 1 = calibration mismatches (currently 3 real gaps; see RESULTS.md).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
import importlib  # noqa: E402

CST = timezone(timedelta(hours=8))
FIXTURES = HERE / "fixtures"
EXPECTED = json.loads((HERE / "expected.json").read_text())

# Signal signatures. A detector message is classified by the first matching pattern.
# Order matters: more specific patterns first. Old and new message wordings are both
# covered so the corpus pins the contract, not one revision's phrasing.
SIGNATURES = {
    "frozen-artifact-missing": r"frozen artifact missing",
    "frozen-artifact-drift": r"frozen artifact drifted",
    "artifact-text-merge": r"asserted as one class in .*artifact",
    "class-id-merge": r"(class_id merges C0 and C2|single class token merges C0 and C2)",
    "class-id-unknown": r"unknown class token",
    "family-mismatch": r"label family .* disagrees with class_id",
    "text-merge": r"(merges C0/C2|bare composite C0/C2 expression|asserted as one class)",
    "done-artifact-missing": r"artifact missing on disk",
    "done-no-evidence": r"done without evidence_refs",
    # Proposed signals: not implemented by the pinned detector revision.
    "gate-not-passed-signal": r"required gate .+ verdict=(fail|pending|None)",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def classify(messages: list[str]) -> tuple[set[str], list[str]]:
    """Return (matched signature names, unmatched raw messages)."""
    names, unmatched = set(), []
    for msg in messages:
        for name, pat in SIGNATURES.items():
            if re.search(pat, msg):
                names.add(name)
                break
        else:
            unmatched.append(msg)
    return names, unmatched


def live_map_coverage(map_path: Path) -> dict:
    m = json.loads(map_path.read_text())
    nodes = [n for g in m.get("groups", []) for n in g.get("nodes", [])]
    done = [n for n in nodes if n.get("status") == "done"]
    return {
        "nodes": len(nodes),
        "done_nodes": len(done),
        "nodes_with_class_id": sum(1 for n in nodes if n.get("class_id")),
        "gates_present": bool(m.get("gates")),
        "numerics_lock_present": bool(m.get("numerics_lock")),
        "sections_with_inputs": {
            "done_artifact": len(done) > 0,
            "gates": bool(m.get("gates")),
            "numerics_lock": bool(m.get("numerics_lock")),
            "class_separation": any(n.get("class_id") for n in nodes),
        },
    }


def run(out_path: Path | None, detector_dir: Path | None = None) -> int:
    det_dir = Path(detector_dir) if detector_dir else ROOT / "research_map"
    sys.path.insert(0, str(det_dir.resolve()))
    audit_evidence = importlib.import_module("audit_evidence")
    detector = det_dir / "audit_evidence.py"
    report = {
        "harness": "artifacts/worker-16/audit_calibration/run_calibration.py",
        "detector": str(detector.relative_to(ROOT)) if str(detector).startswith(str(ROOT)) else str(detector),
        "detector_dir": str(det_dir),
        "detector_sha256": sha256(detector),
        "checked_at": datetime.now(CST).isoformat(timespec="seconds"),
        "fixtures": [],
        "totals": {"tp": 0, "tn": 0, "fp": 0, "fn": 0},
        "coverage": {},
    }

    for fixture_name, spec in EXPECTED.items():
        if fixture_name == "research_map.json":
            fixture = ROOT / "research_map" / "research_map.json"
            report["coverage"]["live_map"] = live_map_coverage(fixture)
        else:
            fixture = FIXTURES / fixture_name
        res = audit_evidence.audit(fixture)
        obs_hard, unclass_hard = classify(res["hard"])
        obs_soft, unclass_soft = classify(res["soft"])
        exp_hard, exp_soft = set(spec["hard"]), set(spec["soft"])

        missing_hard = sorted(exp_hard - obs_hard)          # false negative
        missing_soft = sorted(exp_soft - obs_soft)          # missing warning
        unexpected_hard = sorted(obs_hard - exp_hard)       # false positive
        unexpected_soft = sorted(obs_soft - exp_soft)

        record = {
            "fixture": fixture_name,
            "informational": bool(spec.get("informational")),
            "expectation": spec["rationale"],
            "expected_hard": sorted(exp_hard),
            "expected_soft": sorted(exp_soft),
            "observed_hard": sorted(obs_hard),
            "observed_soft": sorted(obs_soft),
            "observed_hard_raw": res["hard"],
            "observed_soft_raw": res["soft"],
            "unclassified_hard": unclass_hard,
            "unclassified_soft": unclass_soft,
            "missing_hard": missing_hard,
            "missing_soft": missing_soft,
            "unexpected_hard": unexpected_hard,
            "unexpected_soft": unexpected_soft,
            "verdict": "INFO" if spec.get("informational") else
                       ("MATCH" if not (missing_hard or missing_soft or unexpected_hard
                                        or unexpected_soft or unclass_hard or unclass_soft)
                        else "MISMATCH"),
        }
        if spec.get("informational"):
            report["fixtures"].append(record)
            continue
        clean_expected = not exp_hard and not exp_soft
        observed_any = bool(obs_hard or obs_soft or unclass_hard or unclass_soft)
        if clean_expected and not observed_any:
            report["totals"]["tn"] += 1
        elif clean_expected and observed_any:
            report["totals"]["fp"] += 1
        elif not clean_expected and observed_any:
            report["totals"]["tp"] += 1
        else:
            report["totals"]["fn"] += 1
        report["fixtures"].append(record)

    payload = json.dumps(report, indent=2, sort_keys=True)
    if out_path:
        out_path.write_text(payload)
    print(payload)
    mismatches = [f["fixture"] for f in report["fixtures"] if f["verdict"] == "MISMATCH"]
    print(f"\ncalibration: {len(mismatches)}/{len(report['fixtures'])} fixtures MISMATCH "
          f"| totals {report['totals']}", file=sys.stderr)
    return 1 if mismatches else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=HERE / "calibration_report.json")
    ap.add_argument("--detector-dir", type=Path, default=None,
                    help="directory containing audit_evidence.py (default: research_map)")
    a = ap.parse_args()
    sys.exit(run(a.out, a.detector_dir))
