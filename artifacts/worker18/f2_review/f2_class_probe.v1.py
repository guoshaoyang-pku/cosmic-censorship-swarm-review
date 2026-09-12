#!/usr/bin/env python3
"""F2 class-collapse probe suite (worker deepseek-flash-18, node A1).

Assignment: asg-2026-09-11-A1-deepseek-flash-18-27
  "Try to prove the C0 and C2 schemas are the same class. If you cannot, say so."
  Stop rule: two separate verdicts, one per regularity.

This tool is an ADVERSARIAL REVIEW INSTRUMENT, not a schema generator. It loads F2 schema
documents for classes AF-SCC-C2-VAC-GEN and AF-SCC-C0-VAC-GEN, locates each class section,
and runs probes that would support a class-collapse (C0 == C2) conclusion. Each probe reports
pass (separation holds), fail (collapse supported), warn, na, or error.

Exit codes: 0 = report written; 2 = usage/input error. --selftest exits 0 only when the
planted merged fixture is caught by all required probes AND the separated fixture is clean.

Primary-source anchor for probe K5 (fetched 2026-09-11):
  M. Dafermos, J. Luk, arXiv:1710.01722: maximal Cauchy evolution extends across a non-trivial
  piece of Kerr Cauchy horizon with continuous metric; conditional on Kerr exterior stability,
  the C^0-inextendibility formulation of SCC is false, and the surviving statement concerns
  weak null singularities. A C0 schema that claims generic C^0-inextendibility without this
  obstruction is class-inflated.

Usage:
  python3 f2_class_probe.py --report OUT.json --c2 PATH --c0 PATH
  python3 f2_class_probe.py --selftest
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

CLASS_C2 = "AF-SCC-C2-VAC-GEN"
CLASS_C0 = "AF-SCC-C0-VAC-GEN"
SUPERSCRIPT = {"⁰": "0", "²": "2"}


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", str(text)).strip().lower()


def flat(text: str) -> str:
    return re.sub(r"[\s^\[\]\{\}\(\)\.\u200b]", "", text.translate(str.maketrans(SUPERSCRIPT))).lower()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------- merge-string lint

_C = r"c\s*\^?\s*\{?\s*([02])\s*\}?"
MERGE_RE = re.compile(rf"{_C}\s*(?:,|/|&|\+|-|\band\b|\bor\b)\s*{_C}", re.I)
MERGE_BRACE_RE = re.compile(r"c\s*\^?\s*\{\s*0\s*,\s*2\s*\}", re.I)
STRONG_SEP = re.compile(
    r"\b(not|never|no|distinct|separate|separated|differ|different|rather than|excluded|"
    r"forbidden|anti[-_ ]?scope|non[-_ ]?goals?|keep apart|two)\b", re.I)


def merge_scan(text: str) -> dict:
    """Classify merged-class token occurrences as merge-use or separation-mention.

    A hit is a separation mention only when a strong separation/negation marker appears in
    the 40 characters immediately before it. Bare occurrences in class-defining fields are
    always merge-uses (F2 acceptance: 'prove no merged class string')."""
    t = str(text).translate(str.maketrans(SUPERSCRIPT))
    hits = []
    for rx in (MERGE_RE, MERGE_BRACE_RE):
        for m in rx.finditer(t):
            before = norm(t[max(0, m.start() - 40):m.start()])
            negated = bool(STRONG_SEP.search(before))
            hits.append({"form": norm(m.group(0)), "before": before[-40:],
                         "separation_context": negated})
    return {"hits": hits,
            "merge_uses": [h for h in hits if not h["separation_context"]],
            "separation_mentions": [h for h in hits if h["separation_context"]]}


# ---------------------------------------------------------------- loading / extraction

def parse_doc(path: Path):
    text = path.read_text(errors="replace")
    if path.suffix.lower() in (".yaml", ".yml"):
        if yaml is None:
            raise RuntimeError("PyYAML not available for .yaml input")
        return yaml.safe_load(text)
    try:
        return json.loads(text)
    except ValueError:
        if yaml is not None:
            return yaml.safe_load(text)
        raise


def _walk(node, pointer, out):
    if isinstance(node, dict):
        cid = node.get("class_id") or node.get("class") or node.get("id")
        if isinstance(cid, str) and cid.strip() in (CLASS_C2, CLASS_C0):
            out.append((pointer, cid.strip(), node))
        for k, v in node.items():
            if not isinstance(v, (dict, list)):
                continue
            child = f"{pointer}/{k}" if pointer else str(k)
            if str(k).strip() in (CLASS_C2, CLASS_C0) and isinstance(v, dict):
                out.append((child, str(k).strip(), v))
            _walk(v, child, out)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            _walk(v, f"{pointer}[{i}]", out)


def find_sections(doc) -> dict:
    raw = []
    _walk(doc, "", raw)
    found = {CLASS_C2: [], CLASS_C0: []}
    for pointer, cid, sec in raw:
        found[cid].append((pointer, sec))
    return found


FIELD_ALIASES = {
    "regularity": ["regularity", "metric_regularity", "extension_regularity", "regularity_class",
                   "differentiability", "extension_class"],
    "hypotheses": ["hypotheses", "assumptions", "data_class", "initial_data", "setup", "premises"],
    "genericity": ["genericity", "generic", "generic_data", "generic_set"],
    "topology": ["topology", "asymptotics", "asymptotic_structure", "spacetime_topology",
                 "boundary", "i_plus", "iplus"],
    "conclusion": ["conclusion", "conclusion_type", "statement", "claim"],
    "conclusion_type": ["conclusion_type", "conclusiontype", "type_of_conclusion", "conclusion_kind"],
    "obstruction": ["known_obstruction", "obstruction", "known_obstruction_result", "what_fails",
                    "failure_mode", "counterevidence", "known_results", "status"],
    "antiscope": ["anti_scope", "non_goals", "non-goals", "exclusions", "out_of_scope",
                  "scope_exclusions", "not_claimed", "non_claims"],
    "tests": ["test_cases", "tests", "witnesses", "positive_test", "negative_test",
              "discriminating_witness"],
    "class_id": ["class_id", "class", "id"],
}


def get_field(section, field):
    """Resolve a field by alias with breadth-first search to depth 3.

    Alias order matters: 'conclusion' must win over 'conclusion_type', otherwise a schema
    that stores both would hand back the type string where the predicate is expected. The
    BFS allows schemas that nest regularity/conclusion under `premise`/`conclusion` blocks
    (the layout used by schemas/af_wcc_vacuum.yaml) to resolve without changing the probes.
    """
    wanted = [a.replace("_", " ").replace("-", " ") for a in FIELD_ALIASES[field]]
    queue, best = [(section, 0)], None
    while queue:
        node, depth = queue.pop(0)
        if depth > 3:
            continue
        if isinstance(node, dict):
            lower = {}
            for k, v in node.items():
                lower.setdefault(norm(k).replace("_", " ").replace("-", " "), (k, v))
            for i, a in enumerate(wanted):
                if a in lower:
                    cand = (depth, i, lower[a])
                    if best is None or (cand[0], cand[1]) < (best[0], best[1]):
                        best = cand
            for v in node.values():
                if isinstance(v, (dict, list)):
                    queue.append((v, depth + 1))
        elif isinstance(node, list):
            for v in node:
                if isinstance(v, (dict, list)):
                    queue.append((v, depth + 1))
    return (best[2] if best else (None, None))


def subtree_text(node) -> str:
    parts = []
    if isinstance(node, dict):
        for k, v in node.items():
            parts.append(str(k))
            parts.append(subtree_text(v))
    elif isinstance(node, list):
        for v in node:
            parts.append(subtree_text(v))
    elif node is not None:
        parts.append(str(node))
    return " ".join(p for p in parts if p)


def tok_jaccard(a: str, b: str) -> float:
    ta = set(re.findall(r"[a-z0-9^]+", norm(a)))
    tb = set(re.findall(r"[a-z0-9^]+", norm(b)))
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


# ---------------------------------------------------------------- probes

def _result(pid, cid, kind, severity, verdict, detail, evidence=None):
    return {"probe_id": pid, "class_id": cid, "kind": kind, "severity": severity,
            "verdict": verdict, "detail": detail, "evidence": evidence or []}


def section_ref(path: Path, pointer: str) -> str:
    return f"{path}:{pointer}" if pointer else str(path)


C2_HYP_LEAK = [
    re.compile(rf"{_C}\s*(metric|regularity|extension|differentiab|solution|manifold|class)\b", re.I),
    re.compile(r"\b(extension|metric|solution|manifold)\s*(is|be|being|required to be|assumed)?\s*"
               r"c\s*\^?\s*\{?\s*2\s*\}?", re.I),
    re.compile(r"\b(twice|second)\s+(continuously\s+)?differentiab", re.I),
    re.compile(r"\bsecond\s+derivatives?\b", re.I),
]


def run_probes(c2_path: Path, c0_path: Path, c2_doc, c0_doc) -> dict:
    res = []
    sections = {}
    for cid, path, doc in ((CLASS_C2, c2_path, c2_doc), (CLASS_C0, c0_path, c0_doc)):
        tag = cid.split("-")[2]  # C2 / C0
        found = find_sections(doc)
        if not found[cid]:
            res.append(_result(f"S2-{tag}", cid, "structural", "hard", "fail",
                               f"no section declaring class_id {cid} found in {path}", [str(path)]))
            sections[cid] = None
            continue
        if len(found[cid]) > 1:
            res.append(_result(f"S2b-{tag}", cid, "structural", "warn", "warn",
                               f"class {cid} declared {len(found[cid])} times: "
                               f"{[p for p, _ in found[cid]]}", [str(path)]))
        pointer, sec = found[cid][0]
        sections[cid] = (pointer, sec)
        # S3 required fields
        missing = [f for f in ("regularity", "hypotheses", "genericity", "topology",
                               "conclusion", "obstruction", "antiscope")
                   if get_field(sec, f)[0] is None]
        res.append(_result(f"S3-{tag}", cid, "structural", "hard",
                           "fail" if missing else "pass",
                           f"required fields missing: {missing}" if missing else "required fields present",
                           [section_ref(path, pointer)]))
        # S4 regularity value (accept standard synonyms for the declared class)
        regt = norm(subtree_text(get_field(sec, "regularity")[1]))
        want = "c2" if cid == CLASS_C2 else "c0"
        syn = (["c2", "twicedifferentiab", "twicecontinuouslydifferentiab", "seconddifferentiab",
                "secondderivatives"] if cid == CLASS_C2 else
               ["c0", "continuous", "nodifferentiab", "merelycontinuous"])
        matched = [s for s in syn if s in flat(regt)]
        res.append(_result(f"S4-{tag}", cid, "structural", "hard",
                           "fail" if not matched else "pass",
                           f"regularity declares {want.upper()} (matched {matched}): {regt[:140]!r}",
                           [section_ref(path, pointer)]))
        # S5 merged-class token
        ms = merge_scan(subtree_text(sec))
        res.append(_result(f"S5-{tag}", cid, "structural", "hard",
                           "fail" if ms["merge_uses"] else "pass",
                           (f"{len(ms['merge_uses'])} merged-class token(s) outside a negation "
                            f"context: {[h['form'] for h in ms['merge_uses'][:3]]}")
                           if ms["merge_uses"] else
                           f"no merged token ({len(ms['separation_mentions'])} separation mention(s))",
                           [section_ref(path, pointer)]))
        # K9 anti-scope explicitly excludes the other regularity
        other = CLASS_C0 if cid == CLASS_C2 else CLASS_C2
        other_tok = "c0" if cid == CLASS_C2 else "c2"
        antit_raw = subtree_text(get_field(sec, "antiscope")[1])
        antit = flat(antit_raw)
        explicit = other.lower() in antit
        negated = bool(re.search(r"\b(not|never|no|exclude|excludes|excluding|out of scope|"
                                 r"non[-_ ]?goal|forbid)", antit_raw, re.I))
        res.append(_result(f"K9-{tag}", cid, "collapse", "hard",
                           "pass" if (other_tok in antit and (explicit or negated)) else "fail",
                           f"anti_scope excludes {other}: explicit_id={explicit} negation={negated}; "
                           f"text={norm(antit_raw)[:120]!r}",
                           [section_ref(path, pointer)]))
    if not all(sections.values()):
        return {"probes": res, "sections": {k: (v[0] if v else None) for k, v in sections.items()},
                "class_collapse": "undetermined",
                "collapse_evidence": ["one or both class sections could not be located"]}

    (c2_ptr, c2_sec), (c0_ptr, c0_sec) = sections[CLASS_C2], sections[CLASS_C0]
    ref_c2, ref_c0 = section_ref(c2_path, c2_ptr), section_ref(c0_path, c0_ptr)

    # K1 distinct extension regularity
    r2 = norm(subtree_text(get_field(c2_sec, "regularity")[1]))
    r0 = norm(subtree_text(get_field(c0_sec, "regularity")[1]))
    res.append(_result("K1", "BOTH", "collapse", "hard",
                       "fail" if (flat(r2) == flat(r0) or not r2 or not r0) else "pass",
                       f"regularity C2={r2[:70]!r} C0={r0[:70]!r}", [ref_c2, ref_c0]))
    # K2 distinct conclusion type + predicate
    _, cv2 = get_field(c2_sec, "conclusion")
    _, cv0 = get_field(c0_sec, "conclusion")
    concl2, concl0 = norm(subtree_text(cv2)), norm(subtree_text(cv0))

    def conclusion_type_of(sec, cv):
        _, tv = get_field(sec, "conclusion_type")
        if tv is None and isinstance(cv, dict):
            tv = cv.get("conclusion_type") or cv.get("type")
        return norm(subtree_text(tv)) if tv is not None else ""

    type2, type0 = conclusion_type_of(c2_sec, cv2), conclusion_type_of(c0_sec, cv0)
    same = bool(type2 and type0 and type2 == type0 and tok_jaccard(concl2, concl0) >= 0.85)
    res.append(_result("K2", "BOTH", "collapse", "hard", "fail" if same else "pass",
                       f"conclusion_type C2={type2!r} C0={type0!r}, text jaccard="
                       f"{tok_jaccard(concl2, concl0):.2f}", [ref_c2, ref_c0]))
    # K3 C0 conclusion is not a copy of the C2 conclusion
    strip_reg = lambda t: re.sub(r"c\s*\^?\s*\{?\s*[02]\s*\}?", "", norm(t))
    j3 = tok_jaccard(strip_reg(concl2), strip_reg(concl0))
    res.append(_result("K3", CLASS_C0, "collapse", "hard",
                       "fail" if (concl0 and j3 >= 0.85) else "pass",
                       f"C0-vs-C2 conclusion jaccard after regularity stripping = {j3:.2f}; "
                       f"C2_pred={strip_reg(concl2)[:120]!r}; C0_pred={strip_reg(concl0)[:120]!r}",
                       [ref_c2, ref_c0]))
    # K10 conclusion-level regularity leakage
    c0_concl = subtree_text(cv0)
    c2_concl = subtree_text(cv2)
    near = lambda text, tok: bool(re.search(rf"{tok}[^.]{{0,60}}inextendib|inextendib[^.]{{0,60}}{tok}",
                                            flat(text), re.I))
    leak_c0 = near(c0_concl, "c2")
    leak_c2 = near(c2_concl, "c0")
    res.append(_result("K10a", CLASS_C0, "collapse", "hard",
                       "fail" if leak_c0 else "pass",
                       ("C0 conclusion asserts C2-inextendibility (inherited C2 conclusion)"
                        if leak_c0 else "C0 conclusion does not assert C2-inextendibility"),
                       [ref_c0, ref_c2]))
    res.append(_result("K10b", CLASS_C2, "collapse", "warn",
                       "warn" if leak_c2 else "pass",
                       ("C2 conclusion asserts C0-inextendibility (stronger than the C2 class; "
                        "D-L arXiv:1710.01722 makes this suspicious)" if leak_c2
                        else "C2 conclusion does not assert C0-inextendibility"),
                       [ref_c2, ref_c0]))
    # K4 distinct known obstruction
    o2 = norm(subtree_text(get_field(c2_sec, "obstruction")[1]))
    o0 = norm(subtree_text(get_field(c0_sec, "obstruction")[1]))
    j4 = tok_jaccard(o2, o0)
    if not o2 or not o0:
        v4, d4 = "fail", f"known obstruction missing (C2 missing={not o2}, C0 missing={not o0})"
    elif j4 >= 0.85:
        v4, d4 = "fail", f"known obstructions near-identical (jaccard={j4:.2f})"
    else:
        v4, d4 = "pass", f"obstructions differ (jaccard={j4:.2f})"
    res.append(_result("K4", "BOTH", "collapse", "hard", v4, d4, [ref_c2, ref_c0]))
    # K5 C0 records the continuous-extendibility obstruction (primary-source anchored)
    c0_all = flat(subtree_text(c0_sec))
    anchor = ("arxiv" in c0_all or "doi" in c0_all or "dafermos" in c0_all or "luk" in c0_all)
    extend = ("extendib" in c0_all)
    continuous = ("continuous" in c0_all or "weaknull" in c0_all or "weak null" in c0_all)
    res.append(_result("K5", CLASS_C0, "collapse", "hard",
                       "pass" if (anchor and extend and continuous) else "fail",
                       f"C0 obstruction anchor={anchor} extendibility={extend} "
                       f"continuous-metric={continuous}; primary source arXiv:1710.01722",
                       [ref_c0]))
    # K6 C0 hypotheses do not assume C2 regularity
    h0 = norm(subtree_text(get_field(c0_sec, "hypotheses")[1]))
    leaks = [rx.pattern for rx in C2_HYP_LEAK if rx.search(h0)]
    res.append(_result("K6", CLASS_C0, "collapse", "hard",
                       "fail" if leaks else "pass",
                       f"C0 hypotheses C2-regularity leak patterns: {leaks}" if leaks
                       else "no C2-regularity assumption in C0 hypotheses", [ref_c0]))
    # K6b hypotheses near-identical
    h2 = norm(subtree_text(get_field(c2_sec, "hypotheses")[1]))
    j6 = tok_jaccard(h2, h0)
    res.append(_result("K6b", "BOTH", "collapse", "warn", "warn" if j6 >= 0.9 else "pass",
                       f"hypotheses jaccard={j6:.2f}", [ref_c2, ref_c0]))
    # K7 discriminating test case
    t2 = flat(subtree_text(get_field(c2_sec, "tests")[1]))
    t0 = flat(subtree_text(get_field(c0_sec, "tests")[1]))
    if not t2 or not t0:
        res.append(_result("K7", "BOTH", "collapse", "warn", "na",
                           f"test-case fields absent (C2={bool(t2)}, C0={bool(t0)})", [ref_c2, ref_c0]))
    else:
        j7 = tok_jaccard(t2, t0)
        res.append(_result("K7", "BOTH", "collapse", "warn",
                           "fail" if j7 >= 0.9 else "pass",
                           f"test-case blocks jaccard={j7:.2f}", [ref_c2, ref_c0]))
    # K8 whole-section near-duplicate detector
    j8 = tok_jaccard(subtree_text(c2_sec), subtree_text(c0_sec))
    res.append(_result("K8", "BOTH", "collapse", "warn",
                       "fail" if j8 >= 0.9 else "warn" if j8 >= 0.75 else "pass",
                       f"whole-section token jaccard={j8:.2f}", [ref_c2, ref_c0]))

    hard_fails = [p for p in res if p["severity"] == "hard" and p["verdict"] == "fail"]
    if not hard_fails:
        collapse = "not_supported"
    elif any(p["probe_id"] in ("K1", "K2", "K3") for p in hard_fails):
        collapse = "supported"
    else:
        collapse = "partially_supported"
    return {"probes": res,
            "sections": {CLASS_C2: c2_ptr, CLASS_C0: c0_ptr},
            "class_collapse": collapse,
            "collapse_evidence": [f"{p['probe_id']}: {p['detail']}" for p in hard_fails]}


# ---------------------------------------------------------------- fixtures / self-test

FIXTURE_SEPARATED_C2 = {
    "class_id": CLASS_C2,
    "regularity": "C^2 (the extension is required to be a C^2 Lorentzian manifold solving the vacuum Einstein equations)",
    "topology": "globally hyperbolic asymptotically flat 3+1 spacetime, future null infinity I+ complete",
    "hypotheses": {"data": "asymptotically flat vacuum initial data with weighted Sobolev decay",
                   "genericity": "open dense subset of the constraint manifold"},
    "genericity": "open dense subset of asymptotically flat vacuum data in H^s_{-delta}",
    "conclusion_type": "open_problem",
    "conclusion": "For generic asymptotically flat vacuum data the maximal Cauchy development admits no C^2 extension across a Cauchy horizon.",
    "known_obstruction": "Blue-shift instability suggests extensions are at most C0; no proof of C2-inextendibility exists for generic vacuum data.",
    "anti_scope": ["not the C0-inextendibility statement", "excludes " + CLASS_C0,
                   "matter models other than vacuum are out of scope"],
}
FIXTURE_SEPARATED_C0 = {
    "class_id": CLASS_C0,
    "regularity": "C^0 (continuous metric; no differentiability of the extension is required)",
    "topology": "globally hyperbolic asymptotically flat 3+1 spacetime, future null infinity I+ as in the companion schema",
    "hypotheses": {"data": "asymptotically flat vacuum initial data, same weighted class as the companion regularity schema",
                   "genericity": "open dense subset of asymptotically flat vacuum data"},
    "genericity": "open dense subset of asymptotically flat vacuum data in H^s_{-delta}",
    "conclusion_type": "counterexample",
    "conclusion": "The C^0-inextendibility formulation of strong cosmic censorship is false for perturbations of sub-extremal Kerr: the evolution extends across the Cauchy horizon with continuous metric.",
    "known_obstruction": "Dafermos-Luk prove C^0 extendibility of the Kerr Cauchy horizon (arXiv:1710.01722); conditionally on Kerr exterior stability the C^0-inextendibility statement fails; the surviving statement concerns weak null singularities.",
    "anti_scope": ["not the C2-inextendibility statement", "excludes " + CLASS_C2,
                   "does not assert that no continuous extension exists"],
}
FIXTURE_MERGED_C2 = {
    "class_id": CLASS_C2,
    "regularity": "C0 or C2 (regularity not fixed)",
    "topology": "asymptotically flat",
    "hypotheses": {"data": "generic AF vacuum data", "genericity": "generic"},
    "genericity": "generic AF vacuum data",
    "conclusion_type": "open_problem",
    "conclusion": "Generic AF vacuum maximal developments are inextendible across the Cauchy horizon.",
    "known_obstruction": "Cauchy horizon instability.",
    "anti_scope": [],
}
FIXTURE_MERGED_C0 = dict(FIXTURE_MERGED_C2)
FIXTURE_MERGED_C0["class_id"] = CLASS_C0
FIXTURE_MERGED_C0["anti_scope"] = ["C0 or C2 treated together"]

REQUIRED_CAUGHT = {"S5-C2", "S5-C0", "K1", "K2", "K3", "K4", "K5", "K9-C2", "K9-C0"}


def _write(path: Path, doc):
    path.write_text(yaml.safe_dump(doc, sort_keys=False) if yaml else json.dumps(doc, indent=2))


def selftest(tmp: Path) -> int:
    tmp.mkdir(parents=True, exist_ok=True)
    paths = {}
    for name, doc in (("sep_c2", FIXTURE_SEPARATED_C2), ("sep_c0", FIXTURE_SEPARATED_C0),
                      ("mrg_c2", FIXTURE_MERGED_C2), ("mrg_c0", FIXTURE_MERGED_C0)):
        paths[name] = tmp / f"{name}.yaml"
        _write(paths[name], doc)
    sep = run_probes(paths["sep_c2"], paths["sep_c0"], parse_doc(paths["sep_c2"]), parse_doc(paths["sep_c0"]))
    mrg = run_probes(paths["mrg_c2"], paths["mrg_c0"], parse_doc(paths["mrg_c2"]), parse_doc(paths["mrg_c0"]))
    hard = lambda r: {p["probe_id"] for p in r["probes"] if p["severity"] == "hard" and p["verdict"] == "fail"}
    sep_f, mrg_f = hard(sep), hard(mrg)
    checks = [
        {"check": "separated fixture has no hard failures", "pass": not sep_f, "observed": sorted(sep_f)},
        {"check": "merged fixture collapse supported",
         "pass": mrg["class_collapse"] == "supported", "observed": mrg["class_collapse"]},
        {"check": "merged fixture caught by >=7 hard probes",
         "pass": len(mrg_f) >= 7, "observed": sorted(mrg_f)},
        {"check": "all required probes fire on merged fixture",
         "pass": REQUIRED_CAUGHT.issubset(mrg_f), "observed": sorted(REQUIRED_CAUGHT - mrg_f)},
    ]
    ok = all(c["pass"] for c in checks)
    report = {"selftest": "f2_class_probe", "ok": ok, "checks": checks,
              "separated_hard_failures": sorted(sep_f), "merged_hard_failures": sorted(mrg_f),
              "fixture_sha256": {k: sha256_file(v) for k, v in paths.items()}}
    out = tmp / "selftest_report.json"
    out.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--report")
    ap.add_argument("--c2")
    ap.add_argument("--c0")
    ap.add_argument("--tmp", default="artifacts/worker18/f2_review/fixtures")
    a = ap.parse_args()
    if a.selftest:
        return selftest(Path(a.tmp))
    if not (a.report and a.c2 and a.c0):
        ap.error("--report/--c2/--c0 required unless --selftest")
    c2_path, c0_path = Path(a.c2), Path(a.c0)
    missing = [str(p) for p in (c2_path, c0_path) if not p.exists()]
    if missing:
        print(f"INPUT ERROR: missing {missing}", file=sys.stderr)
        return 2
    report = run_probes(c2_path, c0_path, parse_doc(c2_path), parse_doc(c0_path))
    report.update({"instrument": "artifacts/worker18/f2_review/f2_class_probe.py",
                   "assignment": "asg-2026-09-11-A1-deepseek-flash-18-27",
                   "generated_at": __import__("datetime").datetime.now(
                       __import__("datetime").timezone(__import__("datetime").timedelta(hours=8))
                   ).isoformat(timespec="seconds"),
                   "inputs": {CLASS_C2: {"path": str(c2_path), "sha256": sha256_file(c2_path)},
                              CLASS_C0: {"path": str(c0_path), "sha256": sha256_file(c0_path)}}})
    Path(a.report).write_text(json.dumps(report, indent=2))
    print(json.dumps({"report": a.report, "class_collapse": report["class_collapse"],
                      "hard_failures": [p["probe_id"] for p in report["probes"]
                                        if p["severity"] == "hard" and p["verdict"] == "fail"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
