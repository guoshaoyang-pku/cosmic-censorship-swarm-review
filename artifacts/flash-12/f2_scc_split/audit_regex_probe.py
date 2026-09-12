#!/usr/bin/env python3
"""Probe: the evidence audit's C0/C2 merge regex false-positives on the map's own F2 label.

Context: runtime/state/current_checkpoint.json records the hard finding
  "F2: text merges C0/C2 regularities"
produced by research_map/audit_evidence.py, whose rule is
  re.search(r"C0\\s*(or|/|,)\\s*C2|C2\\s*(or|/|,)\\s*C0", json.dumps(node))
The F2 node's label is "AF-SCC C2/C0 split" — a label that *announces the separation*, not a
merged conclusion. The rule therefore fires on the separation task itself.

This probe (a) reproduces the false positive, (b) demonstrates a narrow discriminator that keeps
the true positive, and (c) prints a drop-in replacement rule for review. It is evidence only; it
does NOT modify research_map/audit_evidence.py (shared, audit-owned).

Usage: python3 audit_regex_probe.py [--map ../../research_map/research_map.json]
Exit 0 if the false positive reproduces and the proposed discriminator behaves as claimed.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OLD_RE = re.compile(r"C0\s*(or|/|,)\s*C2|C2\s*(or|/|,)\s*C0")
# Proposal: same merge tokens, but only when they occur in a conclusion-bearing field and are
# not immediately qualified as a separation ("split"/"separate"/"distinct").
CONCLUSION_KEYS = {"conclusion", "statement", "regularity", "claim", "verdict_text"}
SEPARATION_MARKERS = re.compile(r"\b(split|separate|distinct|disjoint|never\s+merge|not\s+one\s+class)\b", re.I)


def walk(obj, key=None):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk(v, k)
    elif isinstance(obj, list):
        for v in obj:
            yield from walk(v, key)
    elif isinstance(obj, str):
        yield key, obj


def composite_in_conclusion_fields(node: dict) -> list[str]:
    hits = []
    for key, val in walk(node):
        if key not in CONCLUSION_KEYS:
            continue
        if not OLD_RE.search(val):
            continue
        # keep separation language out: "C2/C0 split" describes the split, it is not a merge
        for frag in re.split(r"[.;]\s*", val):
            if OLD_RE.search(frag) and not SEPARATION_MARKERS.search(frag):
                hits.append(frag.strip()[:160])
    return hits


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--map", default=str(ROOT / "research_map" / "research_map.json"))
    a = ap.parse_args()
    m = json.loads(Path(a.map).read_text())
    nodes = [n for g in m.get("groups", []) for n in g.get("nodes", [])]
    f2 = next(n for n in nodes if n["id"] == "F2")

    old_hit = bool(OLD_RE.search(json.dumps(f2)))
    proposed_hit = composite_in_conclusion_fields(f2)

    # true-positive control: a genuinely merged conclusion must still be caught
    merged = {"conclusion": {"statement": "the maximal development is inextendible in the C0 or C2 sense"}}
    control_caught = bool(composite_in_conclusion_fields(merged))

    # true-negative control: the separation label must not be caught
    label_ok = OLD_RE.search(json.dumps(f2)) and not proposed_hit

    out = {
        "map": str(a.map),
        "node": "F2",
        "node_label": f2.get("label"),
        "old_rule_hits_f2": old_hit,
        "proposed_rule_hits_f2": proposed_hit,
        "merged_conclusion_control_caught": control_caught,
        "proposal": ("scan conclusion-bearing fields only (conclusion/statement/regularity/claim), "
                     "and ignore fragments explicitly marked as a split/separation; if a broader "
                     "sweep is wanted, exclude {'label','display_name','description'} keys"),
        "verdict": "OK" if (old_hit and not proposed_hit and control_caught) else "UNEXPECTED",
    }
    print(json.dumps(out, indent=2))
    return 0 if out["verdict"] == "OK" else 1


if __name__ == "__main__":
    sys.exit(main())
