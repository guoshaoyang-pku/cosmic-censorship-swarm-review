#!/usr/bin/env python3
"""FORM-PROBE-11 surface inventory + R32 candidate-rule calibration (worker-06).

Two deliverables, both mechanical, neither edits the canonical gate:

1. surface_inventory.json -- every leaf path of the three canonical schemas classified by
   what the canonical pipeline actually scans:
     A_LEXICAL       : path is one of ASSERTIVE_PATHS -> family-token R12 scan
     R13_COMPOSITE   : reachable by scan_composite (no key in path matches EXEMPT_KEY)
                       -> composite-regularity R13 only, no family-token scan
     EXEMPT_KEY      : some key in the path matches EXEMPT_KEY -> neither scan
   (R13 reaches non-exempt subtrees only; the leaf-level split A vs R13_COMPOSITE is what
   the R32 proposal below needs.)

2. r32_calibration.json -- a PROPOSED rule family (not adopted, not merged):
     R32-fam   : apply FOREIGN[fam] family-token patterns over every non-exempt leaf
                 (the exact recursion R13 already uses, with family tokens).
     R32-fam-pol: same, but inside EXEMPT_KEY subtrees only flag a string that also carries
                 a positive-assertion cue and no negation cue (polarity filter).
   Calibrated on: 3 canonical schemas (must stay accepted -> any hit is a false positive),
   3 legitimate-negative controls, and the 22 EXEMPT-SURFACE-11 mutants (hits = catches).
   Adoption is the formulation lead's decision; this file is calibration evidence only.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
GATE_A = ROOT / "artifacts" / "formulation" / "tools" / "check_class_schema.py"
MANIFEST = json.loads((HERE / "manifest.json").read_text(encoding="utf-8"))

spec = importlib.util.spec_from_file_location("canon_gate", GATE_A)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)

import yaml  # noqa: E402


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


ASSERTIVE = {tuple(p) for p in gate.ASSERTIVE_PATHS}
EXEMPT = gate.EXEMPT_KEY


def classify(path_parts):
    if tuple(path_parts) in ASSERTIVE:
        return "A_LEXICAL"
    if any(EXEMPT.match(str(k)) for k in path_parts):
        return "EXEMPT_KEY"
    return "R13_COMPOSITE"


def leaves(node, parts=()):
    if isinstance(node, dict):
        for k, v in node.items():
            yield from leaves(v, parts + (str(k),))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from leaves(v, parts + (f"[{i}]",))
    else:
        yield parts, node


NEG = re.compile(r"\b(not|never|no|cannot|must not|may not|forbidden|excluded|"
                 r"does not|do not|neither|nor)\b", re.I)
POS_CUE = re.compile(r"\b(is|are|asserts?|requires?|proves?|proved|established|holds?|"
                     r"transfers?|substitut\w+|equivalen\w+|implies|entails|settles?)\b", re.I)

# R32-narrow: declared load-bearing, non-exempt prose fields.  This list is exactly the
# S2 target set of EXEMPT-SURFACE-11 (declared before the run) with list indices removed.
R32_NARROW_ALLOWLIST = [
    "conclusion.wellformedness_conditions",
    "conclusion.known_obstruction",
    "quantifiers.order_note",
    "genericity.ambient_space",
    "non_vacuity.c2_specific_note",
    "non_vacuity.c0_specific_note",
    "conventions.proof_status",
    "c0_specifics.conclusion_relation_to_sibling",
]


def norm_path(parts):
    return ".".join(p for p in parts if not p.startswith("["))


def fam_hits(text, fam):
    out = []
    for pat in gate.FOREIGN[fam]:
        if pat == "INEXTENDIB_NON_GEODESIC":
            if gate.INEXTENDIB.search(text) and not gate.GEODESIC.search(text):
                out.append(pat)
            continue
        if re.search(pat, text, re.I):
            out.append(pat)
    return out


def scan(doc, fam, mode):
    hits = []
    for parts, val in leaves(doc):
        if not isinstance(val, str) or not val.strip():
            continue
        foreign = fam_hits(val, fam)
        if not foreign:
            continue
        cls = classify(parts)
        if mode == "R32-narrow":
            if norm_path(parts) not in R32_NARROW_ALLOWLIST:
                continue
            hits.append({"path": ".".join(parts), "class": cls, "patterns": foreign})
            continue
        if cls == "A_LEXICAL":
            continue  # already R12 territory; not an R32 finding
        if cls == "EXEMPT_KEY":
            if mode == "R32-fam":
                hits.append({"path": ".".join(parts), "class": cls, "patterns": foreign})
            else:  # polarity-filtered
                if NEG.search(val) or not POS_CUE.search(val):
                    continue
                hits.append({"path": ".".join(parts), "class": cls, "patterns": foreign})
        else:  # R13_COMPOSITE, non-exempt
            hits.append({"path": ".".join(parts), "class": cls, "patterns": foreign})
    return hits


def main():
    # ---- 1. surface inventory ----
    inv = {"artifact": "FORM-PROBE-11-SURFACE-INVENTORY",
           "gate_sha256": sha(GATE_A),
           "assertive_paths": [".".join(p) for p in gate.ASSERTIVE_PATHS],
           "exempt_key_regex": gate.EXEMPT_KEY.pattern,
           "schemas": {}}
    for cid, rel in (("AF-WCC-VAC-GEN", "schemas/af_wcc_vacuum.yaml"),
                     ("AF-SCC-C2-VAC-GEN", "schemas/af_scc_c2_vacuum.yaml"),
                     ("AF-SCC-C0-VAC-GEN", "schemas/af_scc_c0_vacuum.yaml")):
        doc = yaml.safe_load((ROOT / rel).read_text(encoding="utf-8"))
        classes = {}
        rows = []
        for parts, val in leaves(doc):
            if not isinstance(val, str) or not val.strip():
                continue
            cls = classify(parts)
            classes.setdefault(cls, []).append(".".join(parts))
            rows.append(".".join(parts))
        inv["schemas"][cid] = {"path": rel, "sha256": sha(ROOT / rel),
                               "leaf_string_count": len(rows),
                               "by_class_counts": {k: len(v) for k, v in classes.items()},
                               "paths_by_class": classes}
    (HERE / "surface_inventory.json").write_text(json.dumps(inv, indent=1, ensure_ascii=False) + "\n",
                                                 encoding="utf-8")

    # ---- 2. R32 calibration ----
    canon = [f for f in MANIFEST["fixtures"] if f["kind"] == "canonical_pass_control"]
    neg = [f for f in MANIFEST["fixtures"] if f.get("expect") == "pass" and f["kind"] != "canonical_pass_control"]
    mut = [f for f in MANIFEST["fixtures"] if f["kind"] == "mutant"]
    cal = {"artifact": "FORM-PROBE-11-R32-CANDIDATE-CALIBRATION",
           "status": "PROPOSAL ONLY - not merged, not adopted; adoption is lead-formulation's",
           "gate_sha256": sha(GATE_A), "manifest_sha256": sha(HERE / "manifest.json"),
           "modes": {}}
    for mode in ("R32-fam", "R32-fam-pol", "R32-narrow"):
        fp, tp, fn = [], [], []
        for f in canon + neg:
            doc = yaml.safe_load((ROOT / f["file"]).read_text(encoding="utf-8"))
            fam = "WCC" if f["base"] == "AF-WCC-VAC-GEN" else "SCC"
            h = scan(doc, fam, mode)
            if h:
                fp.append({"fixture": f["id"], "role": f["kind"], "hits": h})
        for f in mut:
            doc = yaml.safe_load((ROOT / f["file"]).read_text(encoding="utf-8"))
            fam = "WCC" if f["base"] == "AF-WCC-VAC-GEN" else "SCC"
            h = [x for x in scan(doc, fam, mode) if x["path"] == f["path"]]
            (tp if h else fn).append({"fixture": f["id"], "family": f["family"],
                                      "surface": f["surface"], "path": f["path"],
                                      "hits": h})
        cal["modes"][mode] = {
            "false_positives_on_canonical_and_negative_controls": fp,
            "fp_count": len(fp),
            "catches_on_mutants": len(tp),
            "misses_on_mutants": len(fn),
            "catch_ids": [x["fixture"] for x in tp],
            "miss_detail": fn,
            "self_falsifier": ("A canonical schema or legitimate-negative control flagged here "
                               "falsifies this mode's calibration on that field; report the field "
                               "as FP before proposing adoption."),
        }
    (HERE / "r32_calibration.json").write_text(json.dumps(cal, indent=1, ensure_ascii=False) + "\n",
                                               encoding="utf-8")
    print(json.dumps({k: {"fp": v["fp_count"], "catches": v["catches_on_mutants"],
                          "misses": v["misses_on_mutants"]} for k, v in cal["modes"].items()}, indent=1))
    print("inventory:", json.dumps({c: d["by_class_counts"] for c, d in inv["schemas"].items()}, indent=1))


if __name__ == "__main__":
    main()
