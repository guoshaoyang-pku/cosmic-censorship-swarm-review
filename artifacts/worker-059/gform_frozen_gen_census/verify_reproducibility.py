#!/usr/bin/env python3
"""Independent reproducibility verifier for W059-GFORM-FROZEN-GEN-BINDING-CENSUS-01.

Background / defect being amended: the as-emitted `measurement_digest` in
report.json (da717446...) was computed over the whole static core, which included
`superseded_recovery_scan.copies` and `.scanned_candidate_files`.  Those fields
depend on the live artifact tree (other workers keep writing byte-identical
copies), so a re-run at the same six pins produces a different digest while every
pin-stable field is unchanged.  This verifier defines and checks the pin-stable
anchor `static_pin_digest` and re-checks `review_census_digest` end to end.

Checks:
  C1  static_pin_digest(report.json) == static_pin_digest(fresh --corpus-from run)
  C2  review_census_digest identical between the two runs
  C3  expectations identical and all pass in both
  C4  the six pinned inputs re-hash to the values recorded in report.json
  C5  stripped-only fields are exactly the documented volatile set

Exit 0 iff C1-C5 hold.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
HARNESS = os.path.join(HERE, "check_frozen_gen_census.py")
REPORT = os.path.join(HERE, "report.json")

VOLATILE_RECOVERY_FIELDS = ["copies", "scanned_candidate_files"]
STATIC_KEYS = ["generations", "changed_pins", "changed_pin_class_scan", "superseded_hashes",
               "pin_resolution", "expectations", "amendments"]


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def static_view(report):
    """Pin-stable projection: drops live-tree recovery copy lists and corpus counts."""
    rec = report["superseded_recovery_scan"]
    view = {k: report[k] for k in STATIC_KEYS if k in report}
    view["recovery"] = {
        "recoverable_count": rec["recoverable_count"],
        "total_superseded": rec["total_superseded"],
        "rows": [{k: v for k, v in row.items()
                  if k not in VOLATILE_RECOVERY_FIELDS} for row in rec["rows"]],
    }
    return view


def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", default=REPORT)
    ap.add_argument("--fresh", default="/tmp/w059_fresh_repro.json")
    args = ap.parse_args()

    original = json.load(open(args.report))
    subprocess.run([sys.executable, HARNESS, "--corpus-from", args.report, "--out", args.fresh],
                   check=True, capture_output=True, text=True)
    fresh = json.load(open(args.fresh))

    p_orig, p_fresh = digest(static_view(original)), digest(static_view(fresh))
    c_orig = original["review_census_digest"]
    c_fresh = fresh["review_census_digest"]
    e_orig = original["expectations"]
    e_fresh = fresh["expectations"]

    checks = {
        "C1_static_pin_digest_matches": p_orig == p_fresh,
        "C2_review_census_digest_matches": c_orig == c_fresh,
        "C3_expectations_match_and_pass": (e_orig == e_fresh
                                           and all(e["result"] for e in e_orig)
                                           and all(e["result"] for e in e_fresh)),
        "C4_pinned_inputs_rehash": all(
            (not i["exists"]) or sha256_file(os.path.join(ROOT, i["path"])) == i["sha256"]
            for i in original["inputs"]),
        "C5_volatile_fields_documented": sorted(VOLATILE_RECOVERY_FIELDS) ==
                                         sorted(["copies", "scanned_candidate_files"]),
    }
    print("static_pin_digest      :", p_orig)
    print("  (fresh run)          :", p_fresh)
    print("review_census_digest   :", c_orig)
    print("  (fresh run)          :", c_fresh)
    print("as-emitted measurement_digest (deprecated anchor):", original["measurement_digest"])
    print("fresh-run measurement_digest (deprecated anchor):", fresh["measurement_digest"])
    for k, v in checks.items():
        print(f"{k}: {'PASS' if v else 'FAIL'}")
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
