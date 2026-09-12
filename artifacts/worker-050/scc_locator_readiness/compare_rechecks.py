#!/usr/bin/env python3
"""W050-SCC-LOCATOR-READINESS-02: compare two live-fetch passes.

The CONFIRMED verdict of the readiness map rests on HTTP observations that are not
reproducible from bytes, so this script compares two independent fetch passes and
reports any instability instead of assuming it away.

A row is STABLE only if both passes returned HTTP 200 and a normalised title
match for the same proposed locator.  Any difference is emitted as a MISMATCH
record; a MISMATCH voids the corresponding CONFIRMED verdict until re-fetched.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import unicodedata
import re
from datetime import datetime, timedelta, timezone

TZ = timezone(timedelta(hours=8))
PINNED_LEDGER_SHA256 = "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9"


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def norm_title(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").lower()
    s = re.sub(r"\\[a-z]+", " ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--first", required=True)
    ap.add_argument("--second", required=True)
    ap.add_argument("--ledger", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    a = json.load(open(args.first))
    b = json.load(open(args.second))
    ledger_sha = sha256_file(args.ledger)
    ia = {(f["citation_id"], f.get("fetched_locator")): f for f in a["fetches"]}
    ib = {(f["citation_id"], f.get("fetched_locator")): f for f in b["fetches"]}

    rows, mismatches = [], []
    for key, fa in sorted(ia.items()):
        fb = ib.get(key)
        rec = {"citation_id": key[0], "fetched_locator": key[1],
               "first": {"http_status": fa.get("http_status"), "title_match": fa.get("title_match"),
                         "title_returned_norm": norm_title(fa.get("title_returned"))},
               "second": None, "stable": False}
        if fb is None:
            rec["reason"] = "MISSING_IN_SECOND_PASS"
            mismatches.append(rec)
            rows.append(rec)
            continue
        rec["second"] = {"http_status": fb.get("http_status"), "title_match": fb.get("title_match"),
                         "title_returned_norm": norm_title(fb.get("title_returned"))}
        stable = (fa.get("http_status") == 200 and fb.get("http_status") == 200
                  and bool(fa.get("title_match")) and bool(fb.get("title_match"))
                  and rec["first"]["title_returned_norm"] == rec["second"]["title_returned_norm"])
        rec["stable"] = stable
        if not stable:
            rec["reason"] = "OBSERVATION_DIFFERS"
            mismatches.append(rec)
        rows.append(rec)

    out = {
        "artifact_id": "W050-SCC-LOCATOR-READINESS-02-recheck",
        "artifact_type": "fetch_stability_comparison",
        "actor": "worker-050",
        "created_at": datetime.now(TZ).replace(microsecond=0).isoformat(),
        "inputs": {
            "first": {"path": args.first, "sha256_measured": sha256_file(args.first),
                      "sha256_pinned": a.get("ledger_sha256_pinned"),
                      "ledger_matches_pin": a.get("ledger_sha256_measured") == PINNED_LEDGER_SHA256},
            "second": {"path": args.second, "sha256_measured": sha256_file(args.second),
                       "sha256_pinned": b.get("ledger_sha256_pinned"),
                       "ledger_matches_pin": b.get("ledger_sha256_measured") == PINNED_LEDGER_SHA256},
            "ledger/citation_audit.csv": {"sha256_measured": ledger_sha,
                                          "sha256_pinned": PINNED_LEDGER_SHA256,
                                          "matches_pin": ledger_sha == PINNED_LEDGER_SHA256},
        },
        "counts": {"compared": len(rows), "stable": sum(1 for r in rows if r["stable"]),
                   "mismatches": len(mismatches)},
        "falsifier": "Any MISMATCH record voids the corresponding CONFIRMED verdict in readiness.json until the locator is re-fetched a third time with a stable observation.",
        "mismatches": mismatches,
        "rows": rows,
    }
    with open(args.out, "w") as fh:
        json.dump(out, fh, indent=1, sort_keys=True, ensure_ascii=False)
        fh.write("\n")
    print("compared=%d stable=%d mismatches=%d ledger_pin_ok=%s"
          % (len(rows), out["counts"]["stable"], len(mismatches), ledger_sha == PINNED_LEDGER_SHA256))
    return 0 if (ledger_sha == PINNED_LEDGER_SHA256 and not mismatches) else (3 if ledger_sha != PINNED_LEDGER_SHA256 else 1)


if __name__ == "__main__":
    sys.exit(main())
