#!/usr/bin/env python3
"""Independent verifier for artifacts/worker-075/l1_spotcheck/spotcheck-l1-075.json.

Reads ONLY the recorded artifact plus the stored raw registry bodies under
fetched/, and re-derives every identity/excerpt verdict with the comparison
functions from run_spotcheck_075.py.  It does not touch the ledger, so a ledger
edit after the check cannot make the artifact verify.

Exit 0 = VERIFIED; exit 1 = a stored body, a recomputed verdict, or the negative
control disagrees with the artifact.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, HERE)
import run_spotcheck_075 as R  # noqa: E402

ART = os.path.join(HERE, "spotcheck-l1-075.json")


def main() -> int:
    doc = json.load(open(ART, encoding="utf-8"))
    problems = []

    # 1. raw bodies: re-hash from disk
    for r in doc["results"]:
        for f in r["fetches"]:
            p = os.path.join(ROOT, f["cache_file"])
            if not os.path.exists(p):
                problems.append(f"missing cached body {f['cache_file']}")
                continue
            h = hashlib.sha256(open(p, "rb").read()).hexdigest()
            if h != f["sha256"]:
                problems.append(f"{f['cache_file']} sha256 {h} != recorded {f['sha256']}")

    # 2. recompute verdicts from the raw bodies + the ledger fields embedded in the
    #    artifact (the CSV itself is not re-read, so a later ledger edit cannot make
    #    this verification pass or fail)
    for r in doc["results"]:
        cid = r["citation_id"]
        for f in r["fetches"]:
            p = os.path.join(ROOT, f["cache_file"])
            body = open(p, "rb").read()
            parsed = (R.parse_crossref(body) if f["kind"] == "crossref"
                      else R.parse_inspire(body))
            fresh = R.compare_against(r["ledger"], parsed)
            if fresh != f["checks"]:
                problems.append(f"{cid} {f['kind']}: recomputed checks differ from "
                                f"recorded: {fresh} vs {f['checks']}")

    # 3. adjudication classification must follow from the recorded states
    clean = {"exact", "match", "supported", "close"}
    bad = {"mismatch", "not-supported", "off-by-one", "conflicting"}
    for a in doc["adjudication_of_worker_086"]:
        classes = []
        for fc in a["fields_compared"]:
            mine = fc["our_state"]
            classes.append("clean" if mine in clean else "bad" if mine in bad
                           else "inconclusive")
            expect = ("clean" if mine in clean else "bad" if mine in bad
                      else "inconclusive")
            if fc["classification"] != expect:
                problems.append(f"{a['row']} field {fc['field']}: classification "
                                f"{fc['classification']} != derived {expect}")
        overall = ("replicates" if all(c == "bad" for c in classes)
                   else "does-not-replicate" if all(c == "clean" for c in classes)
                   else "partially-replicates")
        if a["our_verdict"] != overall:
            problems.append(f"{a['row']}: verdict {a['our_verdict']} != derived {overall}")

    # 4. negative control: a mutated fetched year must flip the check
    r0 = doc["results"][0]
    p0 = os.path.join(ROOT, r0["fetches"][0]["cache_file"])
    parsed0 = R.parse_crossref(open(p0, "rb").read())
    mutated = dict(parsed0)
    mutated["issued_year"] = 1900
    m = R.compare_against(r0["ledger"], mutated)
    control_ok = m["year"] == "mismatch" and r0["fetches"][0]["checks"]["year"] == "exact"
    if not control_ok:
        problems.append(f"negative control failed: mutated year -> {m['year']}")

    print(f"artifact: {ART}")
    print(f"rows={len(doc['results'])} fetches="
          f"{sum(len(r['fetches']) for r in doc['results'])}")
    print(f"negative control (SRC-004 fetched_year 1900 -> mismatch): "
          f"{'PASS' if control_ok else 'FAIL'}")
    if problems:
        print("VERIFY FAILED:")
        for p in problems:
            print("  -", p)
        return 1
    print("VERIFIED: all stored bodies re-hash, all verdicts recompute, "
          "adjudication classifications follow from the recorded states.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
