#!/usr/bin/env python3
"""Machine-check the verbatim quotes used by positive case TC-F0-P15 (Christodoulou 1999).

Normalizes the extracted primary-source text (NFKC, ligatures, whitespace) and checks each
declared quote is present. Writes artifacts/flash-02/sources/quote_checks.json.

This verifies quote presence and scope, NOT mathematical truth or theorem status.
"""
import hashlib
import json
import re
import unicodedata
from pathlib import Path

SRC = Path("artifacts/flash-02/sources/christodoulou1999.txt")
OUT = Path("artifacts/flash-02/sources/quote_checks.json")

QUOTES = [
    {"locator": "p.184, Introduction",
     "role": "codimension/genericity headline",
     "quote": "the subset of initial conditions leading to the formation of naked singularities has, in a certain sense, positive codimension"},
    {"locator": "p.184, Introduction",
     "role": "instability headline (original spelling 'occurence')",
     "quote": "the occurence of naked singularities is an unstable phenomenon"},
    {"locator": "p.191, Section 2",
     "role": "apparent horizon definition, decisive for visibility",
     "quote": "The apparent horizon A is the set of points of Q at which"},
    {"locator": "p.192, Section 2",
     "role": "naked-singularity characterization used by the class",
     "quote": "Then O is a naked singularity."},
    {"locator": "p.192, Section 2",
     "role": "the 1994 construction referenced as the non-generic witness",
     "quote": "In [4] we constructed examples where A is empty and the solutions have a regular extension to B0"},
    {"locator": "p.214, Section 4 opening",
     "role": "definition of the exceptional set E",
     "quote": "Consider the exceptional set E in the space of initial data"},
    {"locator": "p.216, Theorem 4.1",
     "role": "the positive-codimension conclusion",
     "quote": "We may therefore say that E has positive codimension in the space of initial data."},
]


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    s = s.replace("\u00ad", "").replace("\ufb01", "fi").replace("\ufb02", "fl")
    return re.sub(r"\s+", " ", s).strip()


def main():
    raw = SRC.read_text()
    text = norm(raw)
    checks, ok = [], 0
    for q in QUOTES:
        found = norm(q["quote"]) in text
        ok += found
        checks.append({**q, "found": bool(found)})
    doc = {
        "artifact_id": str(OUT),
        "source": "artifacts/flash-02/sources/christodoulou1999.txt",
        "source_sha256": hashlib.sha256(SRC.read_bytes()).hexdigest(),
        "bibliographic": "Christodoulou, D. The instability of naked singularities in the gravitational collapse of a scalar field. Ann. of Math. (2) 149 (1999), no. 1, 183-217. DOI 10.2307/121023",
        "normalization": "NFKC; soft hyphen removed; fi/fl ligatures expanded; whitespace collapsed",
        "quotes_checked": len(checks),
        "quotes_found": ok,
        "all_found": ok == len(checks),
        "checks": checks,
        "scope_caveat": "Presence of a quote verifies provenance, not interpretation. The paper's genericity result is codimension-positive within BV cap L1 cone data; it is not a theorem for all asymptotically flat Cauchy data.",
        "claims_theorem_status": False,
    }
    OUT.write_text(json.dumps(doc, indent=2) + "\n")
    print(f"quotes found {ok}/{len(checks)}; source sha {doc['source_sha256'][:12]}")
    for c in checks:
        print(("OK  " if c["found"] else "MISS"), c["locator"], "|", c["role"])
    return 0 if doc["all_found"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
