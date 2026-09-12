#!/usr/bin/env python3
"""Instrument self-test (falsification control) for the worker-100 L1 spot check.

A checker that reports MATCH for everything is not evidence.  This control takes the frozen
sample, recomputes the quote-fidelity result from the *raw fetched bodies only*, then mutates
each ledger excerpt by replacing one content word inside its first quoted span with a token
that cannot occur in the sources ("zzzq") and recomputes.  The instrument passes only if the
real excerpts match and every mutation is detected.  It writes selftest_report.json.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
import spotcheck as sc  # noqa: E402


def main() -> int:
    report = json.loads((HERE / "spotcheck-l1-100.json").read_text())
    rows = {r["citation_id"]: r for r in csv.DictReader((ROOT / "ledger" / "citation_audit.csv").open())}
    real_match, mutated_detected, details = 0, 0, []
    for entry in report["results"]:
        sid = entry["source_id"]
        relevant = entry["sources"]
        hay_parts = []
        for s in relevant:
            body = (ROOT / s["raw_path"]).read_bytes()
            meta = sc.parse_fetched(body)
            hay_parts.append(" ".join(str(meta.get(k, "")) for k in
                                      ("abstract", "title", "authors", "venue", "doi",
                                       "journal_ref", "comment", "version_years")))
        hay = sc.norm(" ".join(hay_parts))
        qsegs, _ = sc.excerpt_parts(rows[sid]["evidence_excerpt"])

        def matches(segs):
            return sum(1 for seg in segs if seg in hay or (len(seg[:80]) >= 25 and seg[:80] in hay))
        real = matches(qsegs) == len(qsegs) and len(qsegs) > 0
        real_match += int(real)
        # mutate: replace one >=5-char word inside the first evaluated quote segment; the
        # mutated segment must then fail the same predicate.
        mutated = None
        for seg in qsegs:
            wm = re.search(r"[a-z]{5,}", seg)
            if wm:
                mut_seg = seg[:wm.start()] + "zzzq" + seg[wm.end():]
                mutated = not matches([mut_seg])
                break
        mutated_detected += int(bool(mutated))
        details.append({"source_id": sid, "quote_segments": len(qsegs),
                        "real_excerpt_matches": real, "mutation_detected": bool(mutated)})
    out = {
        "control": "w100-l1-spotcheck-instrument-selftest",
        "method": "raw-fetched-body recomputation; then one content word inside the first evaluated quote segment replaced by zzzq",
        "rows": len(details),
        "real_excerpt_matches": real_match,
        "mutations_detected": mutated_detected,
        "pass": real_match == len(details) and mutated_detected == len(details),
        "details": details,
        "note": "a rule that never fires is not evidence; this shows the quote-fidelity check fires on a single-word alteration",
    }
    (HERE / "selftest_report.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k != "details"}, indent=1))
    return 0 if out["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
