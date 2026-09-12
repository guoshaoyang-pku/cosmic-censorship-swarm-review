#!/usr/bin/env python3
"""Hash-bound snapshot review of F0/F1 for A1 (reviewer deepseek-flash-17).

Motivation: during the 23:15-23:30 window the F0 and F1 artifacts were rewritten
several times (F1: eb0d69fa -> f15ea523 -> 337f21cf -> 6a371abe -> a7ef0398 ...).
A review that re-reads a moving file cannot bind a verdict. This script reads each
file ONCE, hashes the exact bytes it parsed, and reports the filename it wrote, so a
verdict is always traceable to one sha256.

It also checks whether the two F0 candidates cross-reference each other and which F0
hash F1 cites, which is the canonicalization question raised in the blocker.

Run: python3 review_snapshot.py
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
F0_PATH = ROOT / "research_map" / "formulation_taxonomy.yaml"
F0R_PATH = ROOT / "artifacts" / "formulation" / "formulation_taxonomy.yaml"
F1_PATH = ROOT / "schemas" / "af_wcc_vacuum.yaml"
MAP_PATH = ROOT / "research_map" / "research_map.json"
FROZEN = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]


def snapshot(path):
    p = Path(path)
    raw = p.read_bytes()
    stat = p.stat()
    try:
        doc = yaml.safe_load(raw)
        parse_error = None
    except yaml.YAMLError as exc:
        doc, parse_error = None, f"{type(exc).__name__}: {str(exc)[:300]}"
    return {"path": str(p.relative_to(ROOT)), "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw), "doc": doc, "parse_error": parse_error,
            "mtime": stat.st_mtime, "text": raw.decode("utf-8", "replace")}


def leaves(obj, path=()):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from leaves(v, path + (str(k),))
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            yield from leaves(v, path + (str(i),))
    else:
        yield path, obj


def walk_container(obj, path=()):
    """Yield (path, value) for every node including containers (leaves() yields leaves only)."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = path + (str(k),)
            yield p, v
            yield from walk_container(v, p)
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            p = path + (str(i),)
            yield p, v
            yield from walk_container(v, p)


def find_sections(doc, key_re):
    out = []
    for path, value in walk_container(doc):
        if path and re.search(key_re, path[-1], re.I) and isinstance(value, (dict, list, str)):
            out.append(("/".join(path), value))
    return out


def texts(obj):
    return [v for _, v in leaves(obj) if isinstance(v, str)]


def contains(doc, pattern):
    return any(re.search(pattern, t, re.I) for t in texts(doc))


def main():
    f0 = snapshot(F0_PATH)
    f0r = snapshot(F0R_PATH) if F0R_PATH.exists() else None
    f1 = snapshot(F1_PATH)
    mapping = json.loads(MAP_PATH.read_text())
    map_nodes = {n["id"]: n for g in mapping.get("groups", []) for n in g.get("nodes", [])}

    findings, checks = [], []

    def add(sev, text, evidence=None):
        findings.append({"severity": sev, "finding": text, "evidence": evidence or []})

    def chk(cid, ok, detail, evidence=None):
        checks.append({"check": cid, "status": "pass" if ok else "fail", "detail": detail,
                       "evidence": evidence or []})

    # ---- canonicalization ----
    for snap in (f0, f1):
        if snap["parse_error"]:
            add("critical", f"{snap['path']} does not parse at snapshot sha256 {snap['sha256'][:12]}: "
                            f"{snap['parse_error']}", [snap["path"]])
    if f0r and f0r["parse_error"]:
        add("major", f"competing F0 candidate {f0r['path']} does not parse at snapshot sha256 "
                     f"{f0r['sha256'][:12]} (possible torn write under artifact churn): {f0r['parse_error']}",
            [f0r["path"]])
    f0_cites_f0r = bool(f0r) and (f0r["sha256"][:12] in f0["text"] or "artifacts/formulation/formulation_taxonomy.yaml" in f0["text"])
    f0r_cites_f0 = bool(f0r) and (f0["sha256"][:12] in f0r["text"] or "research_map/formulation_taxonomy.yaml" in f0r["text"])
    f1_cites = sorted({s for s in (f0["sha256"][:12], f0r["sha256"][:12] if f0r else "") if s and s in f1["text"]})
    chk("canonical.f0_candidates_cross_referenced", f0_cites_f0r or f0r_cites_f0,
        f"F0->F0R citation: {f0_cites_f0r}; F0R->F0 citation: {f0r_cites_f0}",
        [f0["path"], f0r["path"] if f0r else "absent"])
    chk("canonical.f1_cites_one_f0", len(f1_cites) == 1,
        f"F1 cites F0 sha prefixes: {f1_cites}", [f1["path"]])
    chk("canonical.map_hash_lag",
        map_nodes.get("F0", {}).get("artifact_sha256") == f0["sha256"]
        and map_nodes.get("F1", {}).get("artifact_sha256") == f1["sha256"],
        "map recorded hash equals the snapshot hash for both targets",
        [f"map F0={str(map_nodes.get('F0', {}).get('artifact_sha256'))[:12]} snapshot={f0['sha256'][:12]}",
         f"map F1={str(map_nodes.get('F1', {}).get('artifact_sha256'))[:12]} snapshot={f1['sha256'][:12]}"])
    if f0_cites_f0r or f0r_cites_f0:
        # cross-reference exists: duplication downgraded to adjudicated-two-candidates
        pass
    else:
        add("critical", "Two F0 candidates still unreferenced to each other (HF-07 duplication): "
                        f"{f0['path']}#{f0['sha256'][:12]} vs {f0r['path']}#{f0r['sha256'][:12]}",
            [f0["path"], f0r["path"] if f0r else "absent"])

    # ---- F0 snapshot acceptance ----
    f0_doc = f0["doc"] or {}
    chk("f0.accept.class_ids", sorted(f0_doc.get("class_ids", [])) == sorted(FROZEN),
        f"class_ids={f0_doc.get('class_ids')}")
    per_class_ok = True
    for cid in FROZEN:
        c = f0_doc.get("classes", {}).get(cid, {})
        tc = c.get("test_cases", {})
        per_class_ok &= bool(c.get("hypotheses")) and bool(c.get("exclusions")) \
            and bool(c.get("conclusion", {}).get("type")) and bool(tc.get("positive")) \
            and any(k.startswith("negative") for k in tc)
    chk("f0.accept.per_class", per_class_ok, "hypotheses+exclusions+conclusion+positive+negative for all four classes")
    chk("f0.accept.provenance", "reconstruct" in str(f0_doc.get("provenance", {}).get("status", "")),
        f"provenance.status={f0_doc.get('provenance', {}).get('status')!r}")

    # ---- F1 snapshot content, adaptive ----
    f1_doc = f1["doc"] or {}
    q_sections = find_sections(f1_doc, r"^quantifiers?$")
    q_ok = any(isinstance(v, dict) and (v.get("forall") or v.get("for_all"))
               and (v.get("logical_form") or v.get("order")) for _, v in q_sections)
    chk("f1.content.quantifiers", q_ok, f"quantifier sections found: {[p for p, _ in q_sections]}")
    i_minus = contains(f1_doc, r"I_minus|past null infinity|scri\s*-")
    i0 = contains(f1_doc, r"\bi0\b|spatial infinity")
    chk("f1.accept.I_minus_i0", i_minus and i0, f"I-={i_minus} i0={i0}")
    gen_sections = find_sections(f1_doc, r"^genericity$")
    gen_ok = any(isinstance(v, dict) and v.get("kind")
                 and (v.get("topology_or_measure") or v.get("topology_name") or v.get("ambient_space"))
                 for _, v in gen_sections)
    chk("f1.accept.genericity_named", gen_ok, f"genericity sections: {[p for p, _ in gen_sections]}")
    concl_sections = find_sections(f1_doc, r"^conclusion$")
    cdict = next((v for _, v in concl_sections if isinstance(v, dict)), {})
    ctype_ok = cdict.get("conclusion_type") == "weak_cosmic_censorship" or cdict.get("family") == "weak_cosmic_censorship"
    chk("f1.accept.conclusion_wcc", ctype_ok,
        f"conclusion_type={cdict.get('conclusion_type')!r} family={cdict.get('family')!r}")
    statement = str(cdict.get("statement", ""))
    curve_geodesic = "geodesic" in statement.lower()
    vis_sections = find_sections(f1_doc, r"^visibility$")
    vis_text = " ".join(texts(vis_sections)) if vis_sections else ""
    variant_geodesic = "geodesic" in f1["text"].lower()
    chk("f1.consistency.statement_and_visibility_curve_class",
        not ("causal curve" in statement.lower() and variant_geodesic and "geodesic" not in statement.lower()),
        f"statement uses causal curve={ 'causal curve' in statement.lower() }; geodesic wording present in doc={variant_geodesic}",
        ["conclusion.statement", "visibility/variants"])
    if "causal curve" in statement.lower() and variant_geodesic and "geodesic" not in statement.lower():
        add("major", "conclusion.statement still quantifies over causal curves while the document elsewhere "
                     "proposes geodesic completeness; the frozen predicate remains ambiguous", ["conclusion.statement"])
    equiv = cdict.get("equivalence_claim", {})
    if "equivalently" in statement.lower() and isinstance(equiv, dict) and equiv.get("status") == "unverified":
        add("major", "'equivalently' in conclusion.statement pairs with equivalence_claim.status=unverified; "
                     "the equivalence must be proved, cited, or removed", ["conclusion.statement", "conclusion.equivalence_claim"])
    if re.search(r"linter", f1["text"], re.I):
        add("major", "the document still records that a class-binding linter's token matching forced the F0 "
                     "canonical wording into `variants`; a tool false positive continues to shape the statement",
            ["search: linter"])
    fals = find_sections(f1_doc, r"^falsifier$")
    chk("f1.accept.falsifier", bool(fals), f"falsifier sections: {[p for p, _ in fals]}")
    sep = find_sections(f1_doc, r"^class_separation$")
    chk("f1.accept.class_separation", bool(sep), f"class_separation sections: {[p for p, _ in sep]}")
    ev = find_sections(f1_doc, r"^(evidence_refs|source_refs)$")
    chk("f1.accept.evidence_refs", bool(ev), f"evidence sections: {[p for p, _ in ev]}")

    # verdict rules
    major = [f for f in findings if f["severity"] == "major"]
    critical = [f for f in findings if f["severity"] == "critical"]
    f1_major = [f for f in major if "conclusion.statement" in " ".join(f["evidence"]) or "linter" in f["finding"]]
    if critical:
        f1_verdict, f1_score = "revise", 3.0
    elif len(f1_major) >= 2:
        f1_verdict, f1_score = "revise", 3.5
    elif len(f1_major) == 1:
        f1_verdict, f1_score = "revise", 4.0
    else:
        f1_verdict, f1_score = "accept", 4.5
    f0_verdict, f0_score = ("revise", 3.0) if critical else ("accept", 4.0)

    report = {
        "review_id": f"snapshot-review-17-{f1['sha256'][:12]}",
        "reviewer": "deepseek-flash-17",
        "gate": "G-AUDIT", "node_id": "A1",
        "snapshots": {"F0": {k: f0[k] for k in ("path", "sha256", "bytes")},
                      "F0_competing": ({k: f0r[k] for k in ("path", "sha256", "bytes")} if f0r else None),
                      "F1": {k: f1[k] for k in ("path", "sha256", "bytes")}},
        "map_binding": {"map_updated_at": mapping.get("updated_at"),
                        "map_F0_sha256": map_nodes.get("F0", {}).get("artifact_sha256"),
                        "map_F1_sha256": map_nodes.get("F1", {}).get("artifact_sha256")},
        "checks": checks,
        "findings": findings,
        "verdicts": {
            "F0": {"sha256": f0["sha256"], "verdict": f0_verdict, "score": f0_score,
                   "hard_failures": ["HF-07"] if critical else []},
            "F1": {"sha256": f1["sha256"], "verdict": f1_verdict, "score": f1_score,
                   "hard_failures": []},
        },
        "method_note": "Each artifact was read once; the sha256 is of the exact bytes parsed. "
                       "Content checks locate sections by name pattern, not fixed paths, because the "
                       "artifact structure changed between revisions.",
        "no_completion_claim": True,
    }
    out = HERE / f"review_snapshot_{f1['sha256'][:12]}_f0-{f0['sha256'][:12]}.json"
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"F0 {f0['sha256'][:12]}  F0R {f0r['sha256'][:12] if f0r else '-'}  F1 {f1['sha256'][:12]}")
    for c in checks:
        print(f"  [{c['status']:4}] {c['check']}: {c['detail'][:110]}")
    for f in findings:
        print(f"  [{f['severity']}] {f['finding'][:130]}")
    print(f"verdicts: F0 {f0_verdict} {f0_score} | F1 {f1_verdict} {f1_score}")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
