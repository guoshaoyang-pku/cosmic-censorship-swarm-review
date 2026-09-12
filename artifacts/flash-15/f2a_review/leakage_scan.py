#!/usr/bin/env python3
"""Reproducible block-scoped leakage scan for the C2/C0 separation (review F-1 evidence).

Reads the two schemas, extracts the subtrees that carry the class's own conclusion, and greps
them for foreign-family tokens. Printed findings back review F-1; this script makes that claim
re-runnable instead of resting on manual attribution.

Usage: python3 leakage_scan.py [--json]
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
SCHEMAS = (Path(sys.argv[sys.argv.index("--dir") + 1]).resolve() if "--dir" in sys.argv
           else ROOT / "schemas")
C2 = SCHEMAS / "af_scc_c2_vacuum.yaml"
C0 = SCHEMAS / "af_scc_c0_vacuum.yaml"

# subtrees that must contain only this class's own tokens (canonical names with fallbacks)
OWN_SUBTREES = ["quantifiers", "topology", "i_plus", "conclusion"]
FALLBACKS = {"quantifiers": ["exact_quantifiers"], "i_plus": ["future_null_infinity"]}
# falsifier sub-parts that must be class-bound; scope_guard/schema_falsifiers may name foreign
# classes by design, and topology.forbidden legitimately names the sibling class as excluded.
FALSIFIER_PARTS = ["tier_1", "tier_2"]
EXEMPT_FIELDS = {"forbidden", "forbidden_strengthenings", "scope_guard", "anti_scope",
                 "neighbouring_class_facts", "class_boundary", "variants"}

FOREIGN = {
    "C2": [r"C\^?0\b", r"\bC0\b", r"continuity[- ]class", r"continuous metric", r"weak cosmic censorship", r"visible"],
    "C0": [r"C\^?2\b", r"\bC2\b", r"twice[- ]continuously differentiable", r"weak cosmic censorship"],
}


def flatten(x) -> str:
    if isinstance(x, dict):
        return " ".join(f"{k}: {flatten(v)}" for k, v in x.items())
    if isinstance(x, list):
        return " ".join(flatten(v) for v in x)
    return str(x)


def strip_exempt(node):
    """Remove fields where foreign-class tokens are required or explicitly tagged."""
    if isinstance(node, dict):
        return {k: strip_exempt(v) for k, v in node.items() if k not in EXEMPT_FIELDS}
    if isinstance(node, list):
        return [strip_exempt(v) for v in node]
    return node


def scan(path: Path, foreign: list, subtrees: list, falsifier_parts: list) -> dict:
    doc = yaml.safe_load(path.read_text())
    hits, notes = [], []
    for key in subtrees:
        real = key if key in doc else next((f for f in FALLBACKS.get(key, []) if f in doc), None)
        if real is None:
            hits.append({"block": key, "status": "absent"})
            continue
        if real != key:
            notes.append(f"{key} resolved via fallback key {real}")
        node = strip_exempt(doc[real])
        blob = flatten(node)
        for pat in foreign:
            for m in re.finditer(pat, blob, flags=re.IGNORECASE):
                s = max(0, m.start() - 60)
                hits.append({"block": real, "pattern": pat, "context": blob[s:m.end() + 60]})
    f = doc.get("falsifier", {})
    for part in falsifier_parts:
        if part not in f:
            hits.append({"block": f"falsifier.{part}", "status": "absent"})
            continue
        blob = flatten(strip_exempt(f[part]))
        for pat in foreign:
            for m in re.finditer(pat, blob, flags=re.IGNORECASE):
                s = max(0, m.start() - 60)
                hits.append({"block": f"falsifier.{part}", "pattern": pat, "context": blob[s:m.end() + 60]})
    return {"path": str(path.relative_to(ROOT)), "foreign_hits": hits, "exemptions": notes,
            "verdict": "CLEAN" if not hits else "REVIEW"}


def main() -> int:
    out = {"artifact_kind": "block_scoped_leakage_scan",
           "method": "extract own-conclusion subtrees, regex foreign-family tokens; scope_guard excluded by design",
           "C2": scan(C2, FOREIGN["C2"], OWN_SUBTREES, FALSIFIER_PARTS),
           "C0": scan(C0, FOREIGN["C0"], OWN_SUBTREES, FALSIFIER_PARTS)}
    if "--json" in sys.argv:
        print(json.dumps(out, indent=2))
    else:
        for cls in ("C2", "C0"):
            r = out[cls]
            print(f"{cls} {r['path']}: {r['verdict']}")
            for h in r["foreign_hits"]:
                print("   ", h.get("block"), "|", h.get("pattern", h.get("status")), "|", h.get("context", ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
