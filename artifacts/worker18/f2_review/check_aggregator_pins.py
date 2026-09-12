#!/usr/bin/env python3
"""Aggregator pin check for schemas/af_scc_regularities.yaml (worker 18, node A1).

The F2 aggregator (deepseek-flash-05) declares itself an index that pins the two component
schema hashes and forbids a shared conclusion. This checker verifies exactly that, so the
reviewer's accept/revise verdicts can be bound to a stable pair of files.

Checks:
  P1 aggregator parses and names both component class ids exactly once each
  P2 each component path exists on disk
  P3 each pinned sha256 equals the file's current sha256 (SEP-6)
  P4 aggregator carries no top-level conclusion/conclusion_type object (SEP-4)
  P5 no merged class token in the aggregator outside a negation context
Exit 0 if all checks pass, 1 otherwise; writes a JSON report.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from f2_class_probe import CLASS_C0, CLASS_C2, merge_scan, parse_doc  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
CST = timezone(timedelta(hours=8))


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--aggregator", default="schemas/af_scc_regularities.yaml")
    ap.add_argument("--out", default="artifacts/worker18/f2_review/aggregator_pin_check.json")
    a = ap.parse_args()
    agg_path = ROOT / a.aggregator
    checks, findings = [], []
    if not agg_path.exists():
        report = {"aggregator": a.aggregator, "exists": False, "verdict": "not_applicable",
                  "generated_at": datetime.now(CST).isoformat(timespec="seconds")}
        Path(ROOT / a.out).write_text(json.dumps(report, indent=2))
        print(json.dumps(report, indent=2))
        return 0
    doc = parse_doc(agg_path)
    comps = doc.get("components", []) if isinstance(doc, dict) else []
    ids = [c.get("class_id") for c in comps if isinstance(c, dict)]
    checks.append({"id": "P1", "pass": sorted(ids) == sorted([CLASS_C0, CLASS_C2]),
                   "observed": ids})
    for comp in comps:
        cid = comp.get("class_id")
        p = ROOT / str(comp.get("path", ""))
        exists = p.exists()
        actual = sha256_file(p) if exists else None
        pinned = str(comp.get("sha256", "")).lower()
        checks.append({"id": f"P2-{cid}", "pass": exists, "observed": str(comp.get("path"))})
        checks.append({"id": f"P3-{cid}", "pass": bool(actual and pinned == actual),
                       "observed": {"pinned": pinned[:16], "actual": (actual or "")[:16]}})
        if exists and pinned != actual:
            findings.append(f"PIN MISMATCH {cid}: pinned {pinned[:16]}... vs disk {actual[:16]}...")
    has_conclusion = isinstance(doc, dict) and any(
        k in doc for k in ("conclusion", "conclusion_type", "conclusion_object"))
    checks.append({"id": "P4", "pass": not has_conclusion,
                   "observed": [k for k in ("conclusion", "conclusion_type", "conclusion_object")
                                if isinstance(doc, dict) and k in doc]})
    ms = merge_scan(json.dumps(doc))
    checks.append({"id": "P5", "pass": not ms["merge_uses"],
                   "observed": [h["form"] for h in ms["merge_uses"]]})
    ok = all(c["pass"] for c in checks)
    report = {
        "aggregator": a.aggregator,
        "aggregator_sha256": sha256_file(agg_path),
        "exists": True,
        "generated_at": datetime.now(CST).isoformat(timespec="seconds"),
        "generated_by": "deepseek-flash-18 (A1 reviewer)",
        "checks": checks,
        "findings": findings,
        "verdict": "pass" if ok else "fail",
    }
    Path(ROOT / a.out).write_text(json.dumps(report, indent=2))
    print(json.dumps({"aggregator": a.aggregator, "verdict": report["verdict"],
                      "failures": [c["id"] for c in checks if not c["pass"]],
                      "findings": findings}, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
