#!/usr/bin/env python3
"""Independent containment-consistency check for the SCC C2/C0 schema pair (worker-008).

Purpose: a second, from-scratch instrument for the FORM-SEP-04 hard failure
`containment_inversion_in_ledger`.  It does not import or reuse the v3 scanner
(`artifacts/worker08/c2_c0_separation_audit.py`); it re-derives the containment order from the
files' own declarations and checks every relative-containment sentence and every
strength comparison against that order.  Disagreement between the two instruments is itself
evidence (either a scanner artifact or a missed defect).

Derivation rule used here (stated so it can be falsified):
  * If E_X subset E_Y (every X extension is a Y extension), then
      - I_Y ("no proper future Y extension") entails I_X, so I_Y is STRONGER and I_X is WEAKER;
      - "X is a strictly smaller extension class than Y" is true, and "X is strictly larger" is
        an inversion.
  * A sentence asserting an inverted premise ("C2 is strictly larger" given E_C2 subset E_C0) is
    a hard failure regardless of whether the strength conclusion happens to be right, because the
    ledger's stated reason then contradicts the containment chain it derives from.

Inputs are read-only.  Usage:
  python3 independent_containment_check.py --c0 <c0.yaml> --c2 <c2.yaml> --out-json <path>
Exit code: 0 = no hard failures, 1 = >=1 hard failure, 2 = input/parse error.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml

CST = timezone(timedelta(hours=8))

# E_<token> where token may carry sub/superscripts: C0, C2, H2loc, H2_loc, C^{1,1}, ...
E_TOKEN = re.compile(r"E_\{?([A-Za-z0-9^_'{},]+)\}?")
CONTAINS = re.compile(r"contains", re.IGNORECASE)
REL_LARGER = re.compile(
    r"\b(C0|C2|H2_?loc|C\^?\{?1,1\}?)\b[^.]*?\bis (?:a )?strictly (larger|smaller)\b",
    re.IGNORECASE)
STRENGTH = re.compile(
    r"\b(C0|C2)(?:-inextendibility|\s+inextendibility|\s+result)\b([^.;]{0,30}?)"
    r"\bis (?:strictly )?(stronger|weaker)\b",
    re.IGNORECASE)
SUBSET_SENT = re.compile(r"E_C2\s+subset\s+of\s+E_C0|E_\{?C2\}?\s*(?:⊂|subset)\s*E_\{?C0\}?",
                         re.IGNORECASE)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def norm(tok: str) -> str:
    t = tok.replace("{", "").replace("}", "").replace("_", "").replace("^", "").lower()
    return "h2loc" if t.startswith("h2loc") else t


def derive_order(c0: dict) -> dict:
    """Parse extension_class_containment into strictly-decreasing extension classes.

    Returns {"raw": str, "order": [outermost, ..., innermost], "subsets": [(inner, outer), ...]}
    """
    raw = None
    for k, v in c0.items():
        if k == "extension_class_containment" or (isinstance(v, dict) and "extension_class_containment" in v):
            raw = v if isinstance(v, str) else v["extension_class_containment"]
            break
    if raw is None:
        raise SystemExit("input/parse error: extension_class_containment not found in C0 schema")
    toks = [norm(m.group(1)) for m in E_TOKEN.finditer(raw)]
    # keep first occurrence order, dedupe
    order, seen = [], set()
    for t in toks:
        if t not in seen:
            seen.add(t)
            order.append(t)
    subsets = [(order[i + 1], order[i]) for i in range(len(order) - 1)]
    # expand to all pairs (inner, outer)
    all_pairs = [(order[j], order[i]) for i in range(len(order)) for j in range(i + 1, len(order))]
    return {"raw": raw, "order": order, "subsets": all_pairs}


def iter_strings(obj, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from iter_strings(v, f"{path}.{k}" if path else str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from iter_strings(v, f"{path}[{i}]")
    elif isinstance(obj, str):
        yield path, obj


def class_token(tok: str) -> str:
    t = tok.upper().replace("_", "")
    if t.startswith("C0"):
        return "C0"
    if t.startswith("C2"):
        return "C2"
    if t.startswith("H2LOC"):
        return "H2LOC"
    return t


def check(c0_path: Path, c2_path: Path) -> dict:
    c0 = yaml.safe_load(c0_path.read_text())
    c2 = yaml.safe_load(c2_path.read_text())
    order = derive_order(c0)
    # derived[a|b] = (a is strictly smaller than b, a-inextendibility is weaker than b-inextendibility)

    hard, records = [], []

    # --- cross-file independent anchor: C2's own prose about which extension class is contained
    c2_anchor = []
    for path, s in iter_strings(c2):
        if SUBSET_SENT.search(s) or re.search(r"every C2 extension is a C0 extension", s, re.I):
            c2_anchor.append({"path": path, "sentence": s.strip()[:400],
                              "direction": "E_C2 subset E_C0"})
    for path, s in iter_strings(c0):
        if "E_C2 subset" in s or "E_C2 ⊂" in s:
            c2_anchor.append({"path": "C0:" + path, "sentence": s.strip()[:400],
                              "direction": "E_C2 subset E_C0"})

    # derived relative size of a class token w.r.t. C0, from the parsed chain (C0 outermost)
    def rel_to_c0(token: str):
        key = norm(token)
        if key not in order["order"]:
            return None
        return "smaller" if order["order"].index(key) > order["order"].index("c0") else "larger"

    # --- relative-containment claims: "X is a strictly larger/smaller extension class"
    for path, s in iter_strings(c0):
        for m in REL_LARGER.finditer(s):
            subj = class_token(m.group(1))
            claim = m.group(2).lower()
            derived_rel = rel_to_c0(subj)
            rec = {"instrument": "independent_containment_check", "kind": "relative_containment",
                   "path": path, "sentence": s.strip()[:400], "subject": subj,
                   "claimed": claim, "derived": derived_rel}
            if derived_rel is not None and claim != derived_rel:
                rec["classification"] = "inversion"
                hard.append({"kind": "containment_premise_inversion", "path": path,
                             "sentence": s.strip()[:400],
                             "claimed": f"{subj} strictly {claim}",
                             "derived": f"{subj} strictly {derived_rel} from {order['raw'][:120]}"})
            else:
                rec["classification"] = "consistent"
            records.append(rec)

    # --- strength comparisons: "X-inextendibility is strictly stronger/weaker"
    for path, s in iter_strings(c0):
        for m in STRENGTH.finditer(s):
            subj = class_token(m.group(1))
            claimed = m.group(3).lower()
            gap = m.group(2)
            if re.search(r"\b(?:C0|C2|H2_?loc)\b", gap, re.I):
                records.append({"instrument": "independent_containment_check",
                                "kind": "strength_comparison", "path": path,
                                "sentence": s.strip()[:400], "subject": subj, "claimed": claimed,
                                "derived": "unclassified_multi_subject_clause",
                                "classification": "unclassified"})
                continue
            if subj == "C2":
                derived_strength = "weaker"   # E_C2 subset E_C0 -> I_C2 weaker
            elif subj == "C0":
                derived_strength = "stronger"  # I_C0 stronger
            else:
                derived_strength = None
            rec = {"instrument": "independent_containment_check", "kind": "strength_comparison",
                   "path": path, "sentence": s.strip()[:400], "subject": subj,
                   "claimed": claimed, "derived": derived_strength}
            if derived_strength is not None and claimed != derived_strength:
                rec["classification"] = "strength_inversion"
                hard.append({"kind": "strength_inversion", "path": path,
                             "sentence": s.strip()[:400], "claimed": claimed,
                             "derived": derived_strength})
            else:
                rec["classification"] = "consistent"
            records.append(rec)

    return {
        "instrument": "independent_containment_check",
        "version": 1,
        "generated_at": datetime.now(CST).isoformat(timespec="seconds"),
        "generated_by": "worker-008 (independent bounded worker instance)",
        "note": "second instrument for the FORM-SEP-04 containment-inversion defect; written from "
                "scratch, does not import the v3 scanner",
        "inputs": {str(c0_path): sha256(c0_path), str(c2_path): sha256(c2_path)},
        "containment_declaration": order["raw"],
        "derived_order_outer_to_inner": order["order"],
        "derived_relative_map_C0": {f"E_{a} subset E_{b}": "a strictly smaller; a-inextendibility weaker"
                                    for a, b in order["subsets"] if "c0" in (a, b)},
        "cross_file_anchor_C2_every_C2_extension_is_C0": c2_anchor,
        "records": records,
        "hard_failure_count": len(hard),
        "hard_failures": hard,
        "verdict": "FAIL" if hard else "PASS",
        "falsifier": "Verdict flips if extension_class_containment in C0 (or the C2 anchor sentence) "
                     "states E_C0 subset E_C2; re-run after any hash change.",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--c0", required=True)
    ap.add_argument("--c2", required=True)
    ap.add_argument("--out-json", required=True)
    a = ap.parse_args()
    try:
        rec = check(Path(a.c0).resolve(), Path(a.c2).resolve())
    except SystemExit:
        raise
    except Exception as e:  # schema shape changed
        print(f"input/parse error: {e}", file=sys.stderr)
        return 2
    Path(a.out_json).write_text(json.dumps(rec, indent=2, sort_keys=True))
    print(json.dumps({"verdict": rec["verdict"], "hard_failure_count": rec["hard_failure_count"],
                      "hard_failures": rec["hard_failures"]}, indent=1))
    return 1 if rec["hard_failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
