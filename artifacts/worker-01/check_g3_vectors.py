#!/usr/bin/env python3
"""G3 merge-guard test vectors (evidence packet for the single surviving class-binding gate).

Context: reviews/G-FORM-tooling-review-lead-audit.json HF-12 reports four incompatible gates, one of
which documents a `probe_rephrased_leak` escape. This packet separates two questions a lexical gate
must not conflate:

  1. BINDING fields (class_id, conclusion_type, expected_classification): a merged regularity
     spelling is a HARD flag, including braced/superscript/underscored/spaced spellings.
  2. PROSE fields (note, guard_rule, prohibition, revision_note): the same spelling is usually a
     prohibition or a discussion; it is at most a SOFT mention, never a class-binding failure.

Reference verdicts are produced here; a surviving gate should match them, or state why it deviates.
Exit 0 iff every vector matches.  Usage: python3 artifacts/worker-01/check_g3_vectors.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
VECTORS = HERE / "G3_normalization_vectors.jsonl"
BINDING_FIELDS = {"class_id", "class_ids", "conclusion_type", "expected_classification", "expected_class"}
MERGED_RE = re.compile(r"C0\s*(?:or|and|/|\+)\s*C2|C2\s*(?:or|and|/|\+)\s*C0", re.I)


def normalize(text: str) -> str:
    return re.sub(r"[\^_{}\s]", "", text)


def merged_match(text: str) -> bool:
    return bool(MERGED_RE.search(text)) or bool(MERGED_RE.search(normalize(text)))


def verdict(field: str, value) -> str:
    values = value if isinstance(value, list) else [value]
    hit = any(merged_match(str(v)) for v in values)
    if field in BINDING_FIELDS:
        return "flag" if hit else "no_flag"
    return "soft" if hit else "no_flag"


def main():
    rows = [json.loads(l) for l in VECTORS.read_text().splitlines() if l.strip()]
    bad = []
    for r in rows:
        got = verdict(r["field"], r["value"])
        if got != r["expect"]:
            bad.append((r["id"], r["field"], r["value"], r["expect"], got))
    print(f"{len(rows) - len(bad)}/{len(rows)} vectors match the reference verdict")
    for b in bad:
        print(f"  MISMATCH {b[0]} field={b[1]} value={b[2]!r} expect={b[3]} got={b[4]}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
