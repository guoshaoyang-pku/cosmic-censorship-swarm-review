#!/usr/bin/env python3
"""Candidate conclusion-freeze rule R-CAND -- reference implementation (worker-068).

This is a PROPOSAL artifact, not an adopted gate rule. It implements two deterministic
checks of a class-bound candidate schema against the frozen class base:

  freeze_statements  FLAG iff conclusion.statement_formal or
                     conclusion.statement_natural_language differs from the frozen class
                     base after canonicalisation (whitespace + Unicode NFKC; YAML parsing
                     already removes comments, anchors and key order). This is the
                     conclusion-content axis that FORM-POLARITY-10/11 measured as unchecked.
  freeze_full        freeze_statements plus conclusion.conclusion_type, conclusion.family
                     and conclusion.epistemic_status token equality (overlaps R11).
  negation_only      FLAG iff the negation-marker count of either statement differs from
                     the base. A deliberately narrow comparison baseline: it sees lexical
                     negation flips but no other content substitution.

The check is structural and vocabulary-free: it never decides mathematics, class truth,
or a gate verdict. Independent of worker-06 / formulation stage code: PyYAML + stdlib only.

Usage:
  python3 conclusion_freeze_check.py --fixture F.yaml --base B.yaml --variant freeze_statements [--json]
Exit: 0 checked (FLAG or PASS); 2 usage/IO error.
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
import unicodedata

try:
    import yaml
except ImportError:  # pragma: no cover
    print("PyYAML required", file=sys.stderr)
    sys.exit(2)

VARIANTS = ("freeze_statements", "freeze_full", "negation_only")
CONTENT_FIELDS = ("conclusion.statement_formal", "conclusion.statement_natural_language")
TOKEN_FIELDS = ("conclusion.conclusion_type", "conclusion.family", "conclusion.epistemic_status")
# Conservative, declared negation-marker vocabulary for the negation_only baseline.
NEGATION_MARKERS = (
    "not", "no", "never", "without", "absent", "none", "cannot", "non", "fails",
    "impossible", "neither", "nor", "nothing", "incomplete", "¬",
)
NEG_RE = re.compile(r"(?<![\w-])(" + "|".join(re.escape(m) for m in NEGATION_MARKERS) + r")(?![\w-])",
                    re.IGNORECASE)


def canon(text) -> str:
    if text is None:
        return ""
    if not isinstance(text, str):
        text = json.dumps(text, sort_keys=True)
    text = unicodedata.normalize("NFKC", text)
    return re.sub(r"\s+", " ", text).strip()


def get_path(doc: dict, dotted: str):
    cur = doc
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def neg_count(text) -> int:
    return len(NEG_RE.findall(canon(text)))


def diff_summary(base: str, fixture: str, limit: int = 400) -> str:
    d = list(difflib.unified_diff(base.split(), fixture.split(), lineterm="", n=0))
    out = " ".join(d[3:]) if len(d) > 3 else " ".join(d)
    return out[:limit]


def check(fixture_doc: dict, base_doc: dict, variant: str) -> dict:
    if variant not in VARIANTS:
        raise ValueError(f"unknown variant {variant}")
    flags = []
    fields = {}
    for field in CONTENT_FIELDS:
        b = canon(get_path(base_doc, field))
        f = canon(get_path(fixture_doc, field))
        same = (b == f)
        entry = {
            "field": field,
            "base_sha256_12": __import__("hashlib").sha256(b.encode()).hexdigest()[:12],
            "fixture_sha256_12": __import__("hashlib").sha256(f.encode()).hexdigest()[:12],
            "identical": same,
            "base_negation_markers": neg_count(b),
            "fixture_negation_markers": neg_count(f),
            "content_diff": None if same else diff_summary(b, f),
        }
        fields[field] = entry
        if variant in ("freeze_statements", "freeze_full") and not same:
            flags.append({"rule": variant, "field": field, "reason": "content_changed"})
        if variant == "negation_only" and entry["base_negation_markers"] != entry["fixture_negation_markers"]:
            flags.append({"rule": variant, "field": field,
                          "reason": f"negation_marker_count {entry['base_negation_markers']} -> "
                                    f"{entry['fixture_negation_markers']}"})
    if variant == "freeze_full":
        for field in TOKEN_FIELDS:
            b = canon(get_path(base_doc, field))
            f = canon(get_path(fixture_doc, field))
            entry = {"field": field, "base": b, "fixture": f, "identical": b == f}
            fields[field] = entry
            if b != f:
                flags.append({"rule": variant, "field": field, "reason": "token_changed"})
    # union-level negation delta, for reporting only
    fields["$negation_union"] = {
        "base": sum(v["base_negation_markers"] for k, v in fields.items()
                    if isinstance(v, dict) and k in CONTENT_FIELDS),
        "fixture": sum(v["fixture_negation_markers"] for k, v in fields.items()
                       if isinstance(v, dict) and k in CONTENT_FIELDS),
    }
    return {
        "variant": variant,
        "verdict": "FLAG" if flags else "PASS",
        "flag_count": len(flags),
        "flags": flags,
        "fields": fields,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixture", required=True)
    ap.add_argument("--base", required=True)
    ap.add_argument("--variant", required=True, choices=VARIANTS)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    try:
        fixture_doc = yaml.safe_load(open(a.fixture, "rb").read())
        base_doc = yaml.safe_load(open(a.base, "rb").read())
    except Exception as e:
        print(f"IO/YAML error: {e}", file=sys.stderr)
        return 2
    out = check(fixture_doc, base_doc, a.variant)
    out["fixture"] = a.fixture
    out["base"] = a.base
    print(json.dumps(out, indent=2, sort_keys=True) if a.json else out["verdict"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
