#!/usr/bin/env python3
"""Build the staged R5 container-disjunction candidate from the pinned canonical module.

W036-CLASSSEP-DISJ-RULE-01, worker-036, 2026-09-12.

The candidate is generated mechanically, not hand-edited: it is the pinned canonical
bytes (`class_separation.canonical.c266dbceca87.py`) with exactly one insertion into
`_scan_class_ids`.  `probe_disj_rule.py` re-derives and enforces that property, so the
candidate cannot silently carry unrelated edits.

Writes: candidate_class_separation.py, candidate_build.json
Canonical `research_map/class_separation.py` is never written.
"""
from __future__ import annotations

import difflib
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CANONICAL = HERE / "snapshots" / "class_separation.canonical.c266dbceca87.py"
CANONICAL_SHA = "c266dbceca87fb996bd76a774145ef511cbf2aae190d9f423167d3200783a920"
CANDIDATE = HERE / "candidate_class_separation.py"

ANCHOR = '''        if has0 and has2:
            out.append(f"CLASSSEP: single class token merges C0 and C2 in {where}: {tok!r}")
        elif u not in KNOWN_CLASSES and u.startswith("AF-"):
            out.append(f"CLASSSEP: unknown class token in {where}: {tok!r}")
'''

INSERT = '''        if has0 and has2:
            out.append(f"CLASSSEP: single class token merges C0 and C2 in {where}: {tok!r}")
        elif u not in KNOWN_CLASSES and u.startswith("AF-"):
            out.append(f"CLASSSEP: unknown class token in {where}: {tok!r}")
    # R5 (STAGED CANDIDATE, worker-036): a class_ids container that binds two or more
    # distinct frozen classes is a disjunction.  A declaration surface binds exactly one
    # class; the frozen class a row/claim belongs to is singular even when a relation to
    # another class is the subject matter.  This is container-level only: statement/prose
    # text is untouched, so metalinguistic mentions ("never merge C0 or C2") cannot fire.
    known = sorted({t.strip().upper() for t in toks if t.strip().upper() in KNOWN_CLASSES})
    if len(known) >= 2:
        out.append(
            f"CLASSSEP: class_ids container disjoins {len(known)} frozen classes in {where}: {known!r}"
        )
'''


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def main() -> int:
    raw = CANONICAL.read_bytes()
    if sha256_bytes(raw) != CANONICAL_SHA:
        print(f"FAIL: canonical snapshot hash mismatch: {sha256_bytes(raw)}", file=sys.stderr)
        return 2
    text = raw.decode("utf-8")
    if text.count(ANCHOR) != 1:
        print(f"FAIL: anchor occurs {text.count(ANCHOR)} times, expected 1", file=sys.stderr)
        return 2
    cand_text = text.replace(ANCHOR, INSERT, 1)
    CANDIDATE.write_bytes(cand_text.encode("utf-8"))

    diff = list(
        difflib.unified_diff(
            text.splitlines(keepends=True),
            cand_text.splitlines(keepends=True),
            fromfile="a/research_map/class_separation.py",
            tofile="b/candidate_class_separation.py",
            n=2,
        )
    )
    added = [ln for ln in diff if ln.startswith("+") and not ln.startswith("+++")]
    removed = [ln for ln in diff if ln.startswith("-") and not ln.startswith("---")]
    rec = {
        "task_id": "W036-CLASSSEP-DISJ-RULE-01",
        "canonical_sha256": CANONICAL_SHA,
        "candidate_sha256": sha256_bytes(cand_text.encode("utf-8")),
        "diff_added_lines": len(added),
        "diff_removed_lines": len(removed),
        "diff": "".join(diff),
        "reverse_apply_equals_canonical": cand_text.replace(INSERT, ANCHOR, 1) == text,
    }
    (HERE / "candidate_build.json").write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps({k: v for k, v in rec.items() if k != "diff"}, indent=1))
    return 0 if rec["reverse_apply_equals_canonical"] and not removed else 2


if __name__ == "__main__":
    raise SystemExit(main())
