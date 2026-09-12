#!/usr/bin/env python3
"""W070-L1-ANCHORS-01 post-frame addendum.

Clearly separated from the pre-registered run: three work-specific candidate locators that the
pre-registered keyword rules did not force (Schoen-Yau 1981 correct DOI, Carter 1968 Kerr
extension, Hawking-Ellis predictability definition), plus a ledger scan for H2_loc/L^s_loc
inextendibility rows. Writes addendum.json; does not modify report.json or frame.json.
"""
import csv
import hashlib
import json
import re
import sys
import time

sys.path.insert(0, "/data3/guoshaoyang/workdir/ai4math-swarm/artifacts/worker-070/l1_anchors01")
from run_anchors070 import (D, ROOT, log, norm, resolve_crossref_query, resolve_doi,
                            sha256_file, expectation_met, log_lines)

ADD = [
    {"tag": "sy1981_query", "kind": "crossref_query",
     "query": "Proof of the positive mass theorem II Schoen Yau",
     "note": "pre-registered DOI 10.1007/BF01942093 returned HTTP 404; this query finds the live DOI",
     "expect_title_tokens": ["positive", "mass"], "expect_author_any": ["schoen", "yau"]},
    {"tag": "carter1968", "kind": "doi", "id": "10.1103/PhysRev.174.1559",
     "note": "work-specific Kerr maximal-extension pointer; item matched the ledger only by the generic token 'kerr'",
     "expect_title_tokens": ["kerr"]},
    {"tag": "he1973", "kind": "doi", "id": "10.1017/CBO9780511524646",
     "note": "predictability/asymptotic-predictability definition source; item matched the ledger by on-topic rows only",
     "expect_title_tokens": ["large", "scale", "structure", "space"]},
]


def main():
    rep = json.load(open(f"{D}/report.json"))
    frame = json.load(open(f"{D}/frame.json"))
    pins_now = {k: sha256_file(f"{ROOT}/{k}") for k in frame["pins"]}
    stable = pins_now == frame["pins"]
    out = {"schema_version": "w070-anchors-addendum-1", "task_id": frame["task_id"],
           "actor": "worker-070", "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
           "label": "POST_FRAME_ADDENDUM (not pre-registered; candidates only)",
           "pins_unchanged_since_frame": stable, "pins": frame["pins"], "pins_now": pins_now,
           "pre_registered_report_sha256": sha256_file(f"{D}/report.json"),
           "resolutions": [], "ledger_scan": {}}

    for a in ADD:
        if a["kind"] == "doi":
            res = resolve_doi(a["id"], a["tag"])
        else:
            res = resolve_crossref_query(a["query"], a["tag"])
        met, why = expectation_met(res, a)
        res.update({"expectation_met": met, "expectation_detail": why, "note": a["note"]})
        out["resolutions"].append(res)
        log(f"addendum {a['tag']}: http={res['http_status']} met={met} ({why})")

    # ledger scan for H2_loc / L^s_loc inextendibility anchors
    with open(f"{ROOT}/ledger/citation_audit.csv", newline="") as f:
        rows = list(csv.DictReader(f))
    pats = {"h2_loc": r"h2\s*loc|h\^?2|h 2 loc", "ls_loc": r"l\^?s\s*loc|l s loc",
            "lipschitz": r"lipschitz", "inextendib": r"inextendib"}
    scan = {k: [] for k in pats}
    for r in rows:
        blob = norm(r.get("title") + " " + (r.get("evidence_excerpt") or "") + " " + (r.get("assessment") or ""))
        for k, p in pats.items():
            if re.search(p, blob):
                scan[k].append(r["citation_id"])
    out["ledger_scan"] = {k: {"n": len(v), "citation_ids": v[:12]} for k, v in scan.items()}
    log(f"addendum ledger scan: {json.dumps({k: v['n'] for k, v in out['ledger_scan'].items()})}")

    with open(f"{D}/addendum.json", "w") as f:
        json.dump(out, f, indent=1)
    log(f"addendum.json sha256 {sha256_file(D + '/addendum.json')}")
    with open(f"{D}/run.log", "a") as f:
        f.write("\n".join(log_lines) + "\n")


if __name__ == "__main__":
    main()
