#!/usr/bin/env python3
"""F2 separation checker — machine acceptance test for the AF-SCC C^2 / C^0 split.

DRAFT / UNVERIFIED breadth artifact by execution worker deepseek-flash-12.
Not a gate. Owner of record for F2: lead-formulation; independent review: lead-audit (A1).

WHAT IT CHECKS (lexical + structural, deterministic)
  AT1 class binding   : exactly the two in-scope class ids, each exactly once
  AT2 conclusion split: extension_regularity C^2 for the C^2 class, C^0 for the C^0 class;
                        conclusion_type is not inflated above open_problem;
                        the two conclusion statements are distinct and each mentions only
                        its own regularity token
  AT3 no composite    : no 'C0 or C2' / 'C2/C0' / 'C0 and C2' / 'either C0 or C2' token in any
                        conclusion or extension-conditions field
  AT4 implication     : the only admissible cross-class edge is C0 -> C2, one way; a reverse
                        edge is allowed only if explicitly marked direction=forbidden
  AT5 genericity      : every document quantifies genericity (quantified_over, exception_set,
                        smallness_notion, topology, status); an unresolved genericity blocks
                        conclusion_type=theorem (no conclusion inflation)
  AT6 visibility      : SCC documents declare visibility.role=not_used_in_conclusion and their
                        conclusion contains no visible-from-I+/complete-I+ claim
  AT7 no memory cites : while primary_sources.status=unresolved, no source slot may contain a
                        year, arXiv id or DOI (the base HANDOFF.md records a fabricated-citation
                        incident; unresolved means unresolved)

MUTATION TESTS (AT6 of the proposal): the checker is itself falsified by injecting each leak into
a clean fixture and requiring the matching diagnostic to fire.

SCOPE LIMITS: it cannot judge physical or mathematical correctness, cannot prove a schema
well-posed, and accepts anything that does not match a known leak/omission pattern. Escape rate
is NOT established; a domain reviewer is required.

Usage:
  python3 check_f2_separation.py [--artifact af_scc_c2_c0.draft.yaml] [--report checker_report.json]
Exit code 0 iff every check passes and every injected mutation is caught.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml

CST = timezone(timedelta(hours=8))
HERE = Path(__file__).resolve().parent
IN_SCOPE = ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
OUT_SCOPE = ["AF-WCC-VAC-GEN", "AF-WCC-SCALAR-SPH"]
EXPECTED_REG = {"AF-SCC-C2-VAC-GEN": "C^2", "AF-SCC-C0-VAC-GEN": "C^0"}

C0 = r"C\s*\^?\s*\{?\s*0\s*\}?"
C2 = r"C\s*\^?\s*\{?\s*2\s*\}?"
JOIN = r"(?:or|and|/|,|\\cup|∪)"
COMPOSITE_RE = re.compile(rf"(?:{C0}\s*{JOIN}\s*{C2})|(?:{C2}\s*{JOIN}\s*{C0})", re.I)
C0_RE = re.compile(C0, re.I)
C2_RE = re.compile(C2, re.I)
VISIBILITY_LEAK_RE = re.compile(r"visible\s+from\s+I\+|complete\s+(future\s+)?(null\s+)?infinity|I\+\s+is\s+complete", re.I)
YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")
ID_RE = re.compile(r"arxiv|doi\.org|10\.\d{4}/", re.I)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def collect_strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from collect_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from collect_strings(v)


def doc_by_class(artifact: dict, class_id: str):
    for d in artifact.get("documents", []):
        if d.get("class_id") == class_id:
            return d
    return None


def check(artifact: dict) -> list[dict]:
    """Return a list of {id, status: pass|fail, detail}."""
    out = []

    def rec(cid, ok, detail=""):
        out.append({"id": cid, "status": "pass" if ok else "fail", "detail": detail})

    docs = artifact.get("documents", [])
    ids = [d.get("class_id") for d in docs]
    rec("AT1.class_ids", sorted(ids) == sorted(IN_SCOPE) and len(ids) == 2,
        f"class ids found: {ids}")

    if not (artifact.get("node_id") == "F2"):
        rec("AT0.node_id", False, f"node_id={artifact.get('node_id')!r}, expected 'F2'")
    else:
        rec("AT0.node_id", True)
    rec("AT0.no_completion_claim",
        artifact.get("claims_completion") is False and artifact.get("validation_status") == "unverified",
        f"claims_completion={artifact.get('claims_completion')!r} validation_status={artifact.get('validation_status')!r}")

    if sorted(ids) != sorted(IN_SCOPE):
        return out  # structure too broken to continue

    c2doc, c0doc = doc_by_class(artifact, IN_SCOPE[0]), doc_by_class(artifact, IN_SCOPE[1])

    # AT2 conclusion split
    det = []
    ok2 = True
    for d in (c2doc, c0doc):
        want = EXPECTED_REG[d["class_id"]]
        got = (d.get("conclusion") or {}).get("extension_regularity")
        ct = (d.get("conclusion") or {}).get("conclusion_type")
        if got != want:
            ok2 = False
            det.append(f"{d['class_id']}: extension_regularity={got!r} expected {want!r}")
        if ct != "open_problem":
            ok2 = False
            det.append(f"{d['class_id']}: conclusion_type={ct!r} expected 'open_problem' (no inflation)")
    s2 = (c2doc.get("conclusion") or {}).get("statement", "") or ""
    s0 = (c0doc.get("conclusion") or {}).get("statement", "") or ""
    if s2 == s0 or not s2 or not s0:
        ok2 = False
        det.append("the two conclusion statements are empty or identical")
    if not (C2_RE.search(s2) and not C0_RE.search(s2)):
        ok2 = False
        det.append("C^2 conclusion statement must mention C^2 and not C^0")
    if not (C0_RE.search(s0) and not C2_RE.search(s0)):
        ok2 = False
        det.append("C^0 conclusion statement must mention C^0 and not C^2")
    rec("AT2.conclusion_split", ok2, "; ".join(det))

    # AT3 composite tokens in conclusion / extension fields
    bad = []
    for d in (c2doc, c0doc):
        subtree = {"conclusion": d.get("conclusion"),
                   "extension_conditions": (d.get("quantifier_form") or {}).get("extension_conditions")}
        for s in collect_strings(subtree):
            if COMPOSITE_RE.search(s):
                bad.append(f"{d['class_id']}: {s[:120]!r}")
    rec("AT3.no_composite_regularity", not bad, "; ".join(bad))

    # AT4 implication direction
    imps = artifact.get("implications", []) or []
    fwd = [i for i in imps if i.get("from") == IN_SCOPE[1] and i.get("to") == IN_SCOPE[0]]
    rev = [i for i in imps if i.get("from") == IN_SCOPE[0] and i.get("to") == IN_SCOPE[1]]
    ok4 = len(fwd) == 1 and all(i.get("direction") == "one_way" for i in fwd)
    if rev and not all(i.get("direction") == "forbidden" for i in rev):
        ok4 = False
    rec("AT4.implication_direction", ok4,
        f"forward_edges={len(fwd)} reverse_edges={len(rev)}")

    # AT5 genericity completeness + no inflation
    det5, ok5 = [], True
    for d in (c2doc, c0doc):
        g = d.get("genericity") or {}
        for k in ("quantified_over", "exception_set", "smallness_notion", "topology", "status"):
            if k not in g:
                ok5 = False
                det5.append(f"{d['class_id']}: genericity missing {k}")
        if g.get("status") == "unresolved" and (d.get("conclusion") or {}).get("conclusion_type") == "theorem":
            ok5 = False
            det5.append(f"{d['class_id']}: theorem conclusion with unresolved genericity (inflation)")
        if g.get("status") is None:
            ok5 = False
            det5.append(f"{d['class_id']}: genericity.status is unset")
    rec("AT5.genericity_quantified", ok5, "; ".join(det5))

    # AT6 visibility not exported into SCC conclusions
    det6, ok6 = [], True
    for d in (c2doc, c0doc):
        vis = d.get("visibility") or {}
        if vis.get("role") != "not_used_in_conclusion":
            ok6 = False
            det6.append(f"{d['class_id']}: visibility.role={vis.get('role')!r}")
        for s in collect_strings(d.get("conclusion")):
            if VISIBILITY_LEAK_RE.search(s):
                ok6 = False
                det6.append(f"{d['class_id']}: visibility leak in conclusion: {s[:100]!r}")
    rec("AT6.visibility_not_exported", ok6, "; ".join(det6))

    # AT7 no memory citations while unresolved
    det7, ok7 = [], True
    for d in (c2doc, c0doc):
        ps = d.get("primary_sources") or {}
        if ps.get("status") != "unresolved":
            ok7 = False
            det7.append(f"{d['class_id']}: primary_sources.status={ps.get('status')!r}, expected 'unresolved'")
            continue
        for s in collect_strings(ps.get("required_slots", [])):
            if YEAR_RE.search(s) or ID_RE.search(s):
                ok7 = False
                det7.append(f"{d['class_id']}: unresolved source slot carries a citation token: {s[:100]!r}")
    rec("AT7.no_memory_citations", ok7, "; ".join(det7))

    return out


def check_raw_text(text: str) -> list[dict]:
    problems = []
    if re.search(r"(^|\s)&\w", text):
        problems.append("YAML anchor found")
    if re.search(r"(^|\s)\*\w", text) or re.search(r"<<\s*:", text):
        problems.append("YAML alias/merge key found")
    return problems


# ---------------------------------------------------------------- clean fixture (minimal)
def clean_fixture() -> dict:
    def doc(cid, reg):
        return {
            "class_id": cid,
            "conclusion_type": "open_problem",
            "conclusion_family": "strong_cosmic_censorship",
            "quantifier_form": {"extension_conditions": {"embedding_regularity": reg}},
            "genericity": {"quantified_over": "admissible data", "exception_set": "extension-admitting data",
                           "smallness_notion": {"value": None, "status": "unresolved"},
                           "topology": {"value": None, "status": "unresolved"}, "status": "unresolved"},
            "visibility": {"role": "not_used_in_conclusion"},
            "conclusion": {"statement": f"no proper future extension in the {reg} class",
                           "extension_regularity": reg, "conclusion_type": "open_problem"},
            "primary_sources": {"status": "unresolved",
                                "required_slots": [f"{reg} formulation - primary source - UNRESOLVED"]},
        }
    return {
        "artifact_id": "clean-fixture", "node_id": "F2",
        "validation_status": "unverified", "claims_completion": False,
        "documents": [doc(IN_SCOPE[0], "C^2"), doc(IN_SCOPE[1], "C^0")],
        "implications": [{"from": IN_SCOPE[1], "to": IN_SCOPE[0], "direction": "one_way"}],
    }


def mutation_tests() -> list[dict]:
    """Inject each known leak; require the matching diagnostic to fail."""
    cases = []

    def run(name, expect, mutate):
        art = copy.deepcopy(clean_fixture())
        mutate(art)
        failed = {c["id"] for c in check(art) if c["status"] == "fail"}
        cases.append({"mutation": name, "expect_fail_code": expect,
                      "failed_codes": sorted(failed), "caught": expect in failed})

    def m_dup(a):
        a["documents"][1]["class_id"] = a["documents"][0]["class_id"]
        a["documents"][1]["conclusion"]["extension_regularity"] = "C^2"

    run("M1 duplicate class id", "AT1.class_ids", m_dup)

    def m_comp(a):
        a["documents"][0]["conclusion"]["statement"] = "no proper future extension in the C0 or C2 class"

    run("M2 composite 'C0 or C2' in C^2 conclusion", "AT3.no_composite_regularity", m_comp)

    def m_wrong_token(a):
        a["documents"][0]["conclusion"]["statement"] = "no proper future extension in the C^0 class"

    run("M2b wrong regularity token in C^2 conclusion", "AT2.conclusion_split", m_wrong_token)

    def m_rev(a):
        a["implications"] = [{"from": IN_SCOPE[0], "to": IN_SCOPE[1], "direction": "one_way"}]

    run("M3 reversed implication", "AT4.implication_direction", m_rev)

    def m_gen(a):
        del a["documents"][1]["genericity"]["topology"]

    run("M4 genericity missing topology", "AT5.genericity_quantified", m_gen)

    def m_vis(a):
        a["documents"][1]["conclusion"]["statement"] += "; no singularity is visible from I+"

    run("M5 visibility leak into C^0 conclusion", "AT6.visibility_not_exported", m_vis)

    def m_infl(a):
        a["documents"][1]["conclusion"]["conclusion_type"] = "theorem"

    run("M6 conclusion inflation with unresolved genericity", "AT5.genericity_quantified", m_infl)

    def m_cite(a):
        a["documents"][0]["primary_sources"]["required_slots"].append("see arXiv:2401.00001")

    run("M7 memory citation while unresolved", "AT7.no_memory_citations", m_cite)

    return cases


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifact", default=str(HERE / "af_scc_c2_c0.draft.yaml"))
    ap.add_argument("--report", default=str(HERE / "checker_report.json"))
    a = ap.parse_args()
    path = Path(a.artifact)
    text = path.read_text()
    artifact = yaml.safe_load(text)
    checks = check(artifact)
    raw_problems = check_raw_text(text)
    checks.append({"id": "SEP.no_yaml_anchors", "status": "pass" if not raw_problems else "fail",
                   "detail": "; ".join(raw_problems)})
    muts = mutation_tests()
    failed = [c for c in checks if c["status"] == "fail"]
    uncaught = [m for m in muts if not m["caught"]]
    verdict = "pass" if not failed and not uncaught else "fail"
    report = {
        "checker": "flash-12/f2_scc_split/check_f2_separation.py",
        "artifact": str(path),
        "artifact_sha256": sha256_file(path),
        "checked_at": datetime.now(CST).isoformat(timespec="seconds"),
        "verdict": verdict,
        "checks_failed": failed,
        "checks_passed": [c["id"] for c in checks if c["status"] == "pass"],
        "mutations": muts,
        "mutations_uncaught": [m["mutation"] for m in uncaught],
        "scope_limits": "lexical/structural only; not a domain review; escape rate not established",
    }
    Path(a.report).write_text(json.dumps(report, indent=2, sort_keys=True))
    print(json.dumps({k: report[k] for k in ("verdict", "artifact_sha256", "checks_failed",
                                             "mutations_uncaught")}, indent=2))
    return 0 if verdict == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
