#!/usr/bin/env python3
"""Fail-closed quote-grounding check for ledger theorem rows.

The literature lead's builder checks that a verified source carries an evidence
quote of >=30 characters.  It does NOT check that the theorem row citing that
source actually quotes it.  A row can therefore paraphrase, mis-attribute, or
invent its support while the build stays green.

This checker closes that gap for rows that declare a `grounding` list:

    "grounding": [{"source_id": "SRC-004", "quote": "<verbatim text>"}, ...]

Every declared quote must be a whitespace-normalised substring of the cited
source record's `verification.evidence`.  Missing source, empty evidence, or a
non-matching quote is a HARD failure.

Scope: read-only.  It reads the same batch-*.jsonl inputs as the builder and
writes one report; it never edits another agent's files.

Exit codes: 0 = all declared quotes grounded; 1 = grounding failures;
            2 = input/parse error.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LIT = ROOT / "artifacts" / "literature"
HERE = Path(__file__).resolve().parent
REPORT = HERE / "grounding_report.json"
# Worker-07's durable batches live outside the literature lead's tree after the
# 23:27 restructure deleted the injected copies; include them explicitly.
W07_SOURCES = HERE / "batches" / "batch-w07-sources.jsonl"
W07_THEOREMS = HERE / "batches" / "batch-w07-theorems.jsonl"
CST = timezone(timedelta(hours=8))
WS = re.compile(r"\s+")


def norm(s: str) -> str:
    return WS.sub(" ", (s or "")).strip()


def read_jsonl(path: Path) -> list[dict]:
    out = []
    if not path.exists():
        return out
    for i, line in enumerate(path.read_text().splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError as e:
            print(f"PARSE ERROR {path}:{i}: {e}")
            sys.exit(2)
    return out


def read_batches(dirpath: Path) -> list[dict]:
    out = []
    for p in sorted(dirpath.glob("batch-*.jsonl")):
        out.extend(read_jsonl(p))
    return out


def main() -> int:
    sources = {s["source_id"]: s for s in
               (read_batches(LIT / "sources") + read_jsonl(W07_SOURCES)) if "source_id" in s}
    theorems = read_batches(LIT / "theorems") + read_jsonl(W07_THEOREMS)

    failures, per_row, ungrounded_accepted = [], [], []
    for t in theorems:
        tid = t.get("theorem_id", "?")
        rows = t.get("grounding", [])
        ok = 0
        for g in rows:
            sid, quote = g.get("source_id"), g.get("quote", "")
            s = sources.get(sid)
            if s is None:
                failures.append({"theorem_id": tid, "source_id": sid,
                                 "reason": "source_id not found in source batches"})
                continue
            ev = norm((s.get("verification") or {}).get("evidence", ""))
            if not ev:
                failures.append({"theorem_id": tid, "source_id": sid,
                                 "reason": "source has no evidence quote"})
                continue
            if norm(quote) and norm(quote) in ev:
                ok += 1
            else:
                failures.append({"theorem_id": tid, "source_id": sid,
                                 "reason": "declared quote is not a verbatim substring of source evidence",
                                 "quote": norm(quote)[:220]})
        per_row.append({"theorem_id": tid, "status": t.get("status"),
                        "declared": len(rows), "grounded": ok,
                        "source_ids": t.get("source_ids", [])})
        if t.get("status") == "accepted" and ok == 0:
            ungrounded_accepted.append(tid)

    counts = Counter(r["status"] for r in per_row)
    report = {
        "checker": "worker-07 ledger quote-grounding check v1",
        "generated_at": datetime.now(CST).isoformat(timespec="seconds"),
        "inputs": {"sources": len(sources), "theorems": len(theorems)},
        "hard_failures": failures,
        "ungrounded_accepted_rows": ungrounded_accepted,
        "rows": per_row,
        "status_counts": dict(counts),
        "verdict": ("ALL DECLARED QUOTES GROUNDED"
                    if not failures else f"{len(failures)} GROUNDING FAILURE(S)"),
    }
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")

    print(f"sources {len(sources)}  theorems {len(theorems)}  statuses {dict(counts)}")
    print(f"rows with >=1 grounded quote: {sum(1 for r in per_row if r['grounded'] > 0)}/{len(per_row)}")
    print(f"accepted rows with ZERO grounding: {len(ungrounded_accepted)} {ungrounded_accepted}")
    for f in failures:
        print(f"  FAIL {f['theorem_id']} <- {f['source_id']}: {f['reason']}")
    print(f"verdict: {report['verdict']}")
    print(f"wrote {REPORT.relative_to(ROOT)}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
