#!/usr/bin/env python3
"""W48-F1-REV13-CLOSURE-RERUN-01 — reproduce the controller review-coverage scan.

Read-only. Calls the controller tool `research_map/astra_lifecycle.review_coverage`
with the F1/F2a/F2b hashes measured at run time and records exactly what the
controller's advisory scan would count at that instant. This is a measurement of
the review corpus, not a gate verdict: binding coverage is adjudicated by the
audit lead (per the tool's own note).

Usage:
  python3 review_coverage_probe.py --out review_coverage_probe.json
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research_map"))

PINS = {
    "F1": "schemas/af_wcc_vacuum.yaml",
    "F2a": "schemas/af_scc_c2_vacuum.yaml",
    "F2b": "schemas/af_scc_c0_vacuum.yaml",
}


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    import astra_lifecycle as al  # noqa: E402

    hashes = {t: {"sha256": sha256(ROOT / p)} for t, p in PINS.items()}
    cov = al.review_coverage(hashes)
    rec = {
        "probe": "controller review_coverage reproduction (astra_lifecycle.review_coverage)",
        "probed_at": datetime.datetime.now().astimezone().isoformat(),
        "pins": {t: hashes[t]["sha256"] for t in PINS},
        "coverage": cov,
        "caveat": (
            "advisory scan of reviews/*.json at the probe instant; the corpus is live, "
            "so later files are not covered; not a gate verdict"
        ),
    }
    out = Path(a.out) if a.out else Path(__file__).with_name("review_coverage_probe.json")
    out.write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n")
    f1 = cov.get("F1", {})
    print(json.dumps({
        "F1_distinct_accept_reviewers": f1.get("distinct_accept_reviewers"),
        "F1_two_distinct_accepts": f1.get("two_distinct_accepts"),
        "F1_verdicts": [(v["reviewer"], v["verdict"], v["counts_as_full_schema_verdict"])
                        for v in f1.get("verdicts", [])],
        "out": str(out.resolve().relative_to(ROOT)),
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
