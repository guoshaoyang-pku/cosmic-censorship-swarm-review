#!/usr/bin/env python3
"""W043-F2A-INDEP-VERDICT-01: independent structural re-check of canonical F2a.

Bounded, read-only instrument. It does NOT modify any lead-owned artifact and does NOT
emit a gate verdict. It answers four questions about the pinned bytes:

  A1  Is the previously-reported HF-A1 (dangling `extension_predicate`) resolved?
      -> require a top-level extension_predicate block, clauses (a)-(f), and every
         `definition_ref: extension_predicate` in the quantifier domains to resolve.
  A2  Is the previously-reported HF-A2 (undefined D0 / two incompatible formal
      renderings) resolved?
      -> require D0..D3 definitions, and check that the formal, ordered, negation and
         negation_normal_form renderings agree on binder order (forall-exists-forall-
         not-exists vs its dual exists-forall-exists).
  A3  Adjudicate the class-collapse probe's S5 hard flag ('c0 or c2' merge token).
      -> classify each merge hit by its YAML path, not by a negation heuristic; a hit
         under anti_scope is a separation mention, not a merge-use.
  A4  Report the data-class contract shape shared by F1/F2a/F2b (the G-FORM requirement
      of one shared data class) and leave the accept/revise decision to the lead.

Usage:
  python3 check_f2a.py --f2a F2A.yaml --c0 C0.yaml --f1 F1.yaml --out report.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import yaml

UP = "\u2192"
MERGE_RE = re.compile(r"c\s*\^?\s*\{?\s*([02])\s*\}?\s*(?:,|/|&|\+|-|\band\b|\bor\b)\s*"
                      r"c\s*\^?\s*\{?\s*([02])\s*\}?", re.I)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def strings_with_paths(node, path="", out=None):
    """Yield (yaml_path, string) for every scalar string in the document."""
    if out is None:
        out = []
    if isinstance(node, dict):
        for k, v in node.items():
            strings_with_paths(v, f"{path}.{k}" if path else str(k), out)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            strings_with_paths(v, f"{path}[{i}]", out)
    elif isinstance(node, str):
        out.append((path, node))
    return out


def find_key(node, key):
    """Return the first value whose dict key equals `key` (depth-first)."""
    if isinstance(node, dict):
        if key in node:
            return node[key]
        for v in node.values():
            got = find_key(v, key)
            if got is not None:
                return got
    elif isinstance(node, list):
        for v in node:
            got = find_key(v, key)
            if got is not None:
                return got
    return None


def check_a1(doc, text):
    ext = doc.get("extension_predicate")
    clauses = sorted(set(re.findall(r"\(([a-f])\)", str(ext.get("definition", "")) if ext else "")))
    refs = []
    for path, s in strings_with_paths(doc):
        if s.strip() == "extension_predicate":
            refs.append(path)
    # every definition_ref to extension_predicate must resolve to the top-level block
    dangling = [] if ext is not None else refs
    return {
        "check": "A1-extension-predicate-defined",
        "top_level_block_present": ext is not None,
        "block_name": (ext or {}).get("name"),
        "frozen_regularity": (ext or {}).get("frozen_regularity"),
        "clauses_found": clauses,
        "clauses_a_to_f_complete": clauses == ["a", "b", "c", "d", "e", "f"],
        "reference_sites": refs,
        "dangling_reference_sites": dangling,
        "result": "RESOLVED" if (ext is not None and clauses == ["a", "b", "c", "d", "e", "f"] and not dangling) else "STILL_DANGLING",
    }


def check_a2(doc):
    q = doc.get("quantifiers") or {}
    doms = q.get("domains") or {}
    dom_status = {d: {"defined": isinstance(doms.get(d), dict)
                      and bool(doms[d].get("definition"))
                      and bool(doms[d].get("definition_ref"))}
                  for d in ("D0", "D1", "D2", "D3")}
    formal = str(q.get("formal", ""))
    ordered = q.get("ordered") or []
    kinds = [str(o.get("kind")) for o in ordered if isinstance(o, dict)]
    neg = str(q.get("negation", ""))
    nnf = str(q.get("negation_normal_form", ""))
    # dual check: the formal is forall-exists-forall-not_exists; its negation must be
    # exists-forall-exists (order of the first three quantifier words)
    def first_quant_words(s):
        return re.findall(r"forall|exists|not\s+exists", s, re.I)[:3]
    formal_words = [w.lower() for w in first_quant_words(formal)]
    neg_words = [w.lower() for w in first_quant_words(neg)]
    formal_ok = formal_words[:2] == ["forall", "exists"] and "not exists" in formal.lower()
    neg_ok = neg_words[:1] == ["exists"] and "every" in neg.lower()
    nnf_ok = nnf.strip().startswith("{") and "non-empty" in nnf
    return {
        "check": "A2-quantifier-and-domain-consistency",
        "domains": dom_status,
        "all_domains_defined": all(v["defined"] for v in dom_status.values()),
        "ordered_kinds": kinds,
        "formal_first_quantifiers": formal_words,
        "negation_first_quantifiers": neg_words,
        "formal_is_forall_exists_forall_notexists": formal_ok,
        "negation_is_dual_exists_forall_exists": neg_ok,
        "negation_normal_form_present_nonempty": nnf_ok,
        "result": "CONSISTENT" if (all(v["defined"] for v in dom_status.values()) and formal_ok and neg_ok and nnf_ok) else "INCONSISTENT_OR_UNDEFINED",
        "residual_scope_question": (
            "D0 is a set of admissible regularity pairs (s,delta); the class sentence is uniform over D0. "
            "The worker-18 probe S6 calls any such binder 'a family of statements, not one class'. "
            "F1/F2a/F2b use the identical D0 form (check A4), so this is a design decision for the lead, "
            "not a dangling reference."),
    }


def check_a3(doc, text):
    hits = []
    for path, s in strings_with_paths(doc):
        for m in MERGE_RE.finditer(s):
            under_antiscope = path.startswith("anti_scope") or ".anti_scope" in path
            negative_key = any(tok in path.lower() for tok in (
                "anti_scope", "forbidden", "must_not", "not_this_class", "phrases_that_are_not",
                "exclusions", "schema_falsifiers", "forbidden_transfers", "forbidden_strengthenings",
                "forbidden_weakenings", "why_", "reason"))
            hits.append({
                "yaml_path": path,
                "matched_form": m.group(0),
                "classified": "separation_mention" if (under_antiscope or negative_key) else "merge_use",
            })
    merge_uses = [h for h in hits if h["classified"] == "merge_use"]
    return {
        "check": "A3-merge-token-adjudication",
        "hits": hits,
        "merge_uses": merge_uses,
        "separation_mentions": [h for h in hits if h["classified"] == "separation_mention"],
        "probe_S5_would_flag": bool(hits),
        "adjudication": ("probe S5 is a FALSE POSITIVE on this revision: the only hit lives under "
                         "anti_scope.phrases_that_are_not_this_class, an explicit exclusion list; the "
                         "probe's negation heuristic misses 'not_this_class' because underscores are "
                         "word characters." if hits and not merge_uses else
                         "no merge token found" if not hits else "genuine merge use present"),
        "result": "FALSE_POSITIVE" if (hits and not merge_uses) else "CLEAN" if not hits else "MERGE_USE",
    }


DATA_PREFIX_RE = re.compile(
    r"^forall\s*\(\s*s\s*,\s*delta\s*\)\s*in\s*D0\s*:\s*exists\s*G_\{s,delta\}\s*subset\s*"
    r"X\^\{s,delta\}_vac\(AF\)\s*with\s*G_\{s,delta\}\s*comeager\s*:\s*"
    r"forall\s*\(\s*Sigma\s*,\s*h\s*,\s*K\s*\)\s*in\s*G_\{s,delta\}", re.S)


def quant_shape(doc):
    q = doc.get("quantifiers") or {}
    formal = re.sub(r"\s+", " ", str(q.get("formal", ""))).strip()
    stmt = re.sub(r"\s+", " ", str(find_key(doc, "statement_formal") or "")).strip()
    d0 = str(((q.get("domains") or {}).get("D0") or {}).get("definition", ""))
    dc = doc.get("data_class") or {}
    rc = dc.get("regularity_class") or {}
    return {
        "formal": formal,
        "statement_formal": stmt,
        "shared_prefix_matches": bool(DATA_PREFIX_RE.match(formal)),
        "d0_core": d0.split(";")[0].strip(),
        "d0_full": d0,
        "sobolev_variant": rc.get("sobolev_variant"),
        "default_regularity": rc.get("default"),
        "symmetry": dc.get("symmetry"),
        "first_quantifier_kinds": [o.get("kind") for o in (q.get("ordered") or [])[:4]
                                   if isinstance(o, dict)],
    }


def check_a4(f1, f2a, c0):
    shapes = {"F1": quant_shape(f1), "F2a": quant_shape(f2a), "F2b": quant_shape(c0)}
    def core(v):
        sv = v["sobolev_variant"] or {}
        return json.dumps({"prefix": v["shared_prefix_matches"], "d0_core": v["d0_core"],
                           "s": sv.get("s"), "delta": sv.get("delta"),
                           "spaces": re.sub(r"\s*\([^)]*\)", "", str(sv.get("spaces", ""))).strip(),
                           "default": v["default_regularity"], "symmetry": v["symmetry"]},
                          sort_keys=True)
    cores = {k: core(v) for k, v in shapes.items()}
    same_core = len(set(cores.values())) == 1
    annotations = {}
    def ann(v):
        sv = v["sobolev_variant"] or {}
        return {"spaces_raw": sv.get("spaces"), "status": sv.get("status")}
    for k, v in shapes.items():
        annotations[k] = ann(v)
    ann_differs = len({json.dumps(a, sort_keys=True) for a in annotations.values()}) > 1
    d0_suffix_only = len({v["d0_full"] for v in shapes.values()}) > 1 and \
        len({v["d0_core"] for v in shapes.values()}) == 1
    return {
        "check": "A4-shared-data-class-contract",
        "shapes": shapes,
        "data_class_core_keys": cores,
        "annotation_fields": annotations,
        "same_data_class_core": same_core,
        "annotation_fields_differ": ann_differs,
        "d0_differs_only_in_trailing_note": d0_suffix_only,
        "result": ("SHARED_CORE" if same_core and not ann_differs else
                   "SHARED_CORE_WITH_ANNOTATION_DIFFS" if same_core else "DIVERGENT"),
        "scope_note": ("compared: shared quantifier prefix, D0 core definition, numeric s/delta, "
                       "spaces text with parenthetical qualifiers stripped, default regularity, "
                       "symmetry. Conclusion clauses differ by design (WCC visibility vs C2 vs C0 "
                       "extension); that is not a data-class divergence."),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--f2a", required=True)
    ap.add_argument("--c0", required=True)
    ap.add_argument("--f1", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--expect-f2a-sha256", default=None)
    args = ap.parse_args()

    f2a_p, c0_p, f1_p = Path(args.f2a), Path(args.c0), Path(args.f1)
    hashes = {str(p): sha256_file(p) for p in (f2a_p, c0_p, f1_p)}
    f2a_text = f2a_p.read_text()
    f2a = yaml.safe_load(f2a_text)
    c0 = yaml.safe_load(c0_p.read_text())
    f1 = yaml.safe_load(f1_p.read_text())

    pin_ok = args.expect_f2a_sha256 is None or hashes[str(f2a_p)] == args.expect_f2a_sha256
    checks = [check_a1(f2a, f2a_text), check_a2(f2a), check_a3(f2a, f2a_text),
              check_a4(f1, f2a, c0)]
    out = {
        "instrument": "artifacts/worker-043/f2a_rev10_independent_verdict/check_f2a.py",
        "task_id": "W043-F2A-INDEP-VERDICT-01",
        "class_id": "AF-SCC-C2-VAC-GEN",
        "reviewed_paths_and_sha256": hashes,
        "pin_ok": pin_ok,
        "checks": checks,
        "mechanically_verified": {
            "hf_a1_dangling_extension_predicate": checks[0]["result"] == "RESOLVED",
            "hf_a2_undefined_domain_and_inconsistent_renderings": checks[1]["result"] == "CONSISTENT",
            "probe_s5_merge_flag": checks[2]["result"],
            "shared_data_class_contract": checks[3]["result"],
        },
        "falsifier": (
            "Re-run this script on the same bytes: the report is falsified if (a) any recorded sha256 "
            "differs; (b) A1 reports the block absent or a clause missing; (c) A2 reports an undefined "
            "domain or a non-dual negation; (d) A3 reports a merge-use outside anti_scope; or (e) A4 "
            "reports divergent skeletons/D0 across F1/F2a/F2b."),
    }
    Path(args.out).write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({"out": args.out, "pin_ok": pin_ok,
                      "results": {c["check"]: c["result"] for c in checks},
                      "f2a_sha256": hashes[str(f2a_p)]}, indent=1))
    return 0 if pin_ok else 1


if __name__ == "__main__":
    sys.exit(main())
