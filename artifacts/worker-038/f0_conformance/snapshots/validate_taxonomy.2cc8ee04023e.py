#!/usr/bin/env python3
"""Acceptance checker for research_map/formulation_taxonomy.yaml (node F0, gate G-F0).

This is the machine-checkable part of the F0 acceptance criteria; it does NOT decide
scientific correctness. Reviewer verdicts (A1: workers 17/19) remain the human-facing gate.

Checks
  A. file parses; exactly the four frozen class ids
  B. per class: axes, hypotheses, exclusions, conclusion, positive+negative test case, provenance
  C. G2: SCC classes carry exactly one regularity token; WCC classes carry none
  D. disjointness: all 6 pairs present, and the named decisive axes actually differ in value
  E. transfer rules: only C0->C2 allowed with guards; the five forbidden leakage patterns present
  F. G3: no merged regularity string anywhere in the raw file
  G. no theorem-status claim in a draft-unverified file
  H. optional: schemas/taxonomy_cases.jsonl (worker-02 corpus) cases name a frozen class and a real hypothesis id

Usage
  python3 artifacts/worker-01/validate_taxonomy.py
  python3 artifacts/worker-01/validate_taxonomy.py --json artifacts/worker-01/taxonomy_validation.json
  python3 artifacts/worker-01/validate_taxonomy.py --self-test
Exit 0 = all checks pass, 1 = at least one failure.
"""
from __future__ import annotations

import argparse
import itertools
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FROZEN = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]
MERGED_RE = re.compile(r"C0\s*(?:or|and|/|\+)\s*C2|C2\s*(?:or|and|/|\+)\s*C0", re.I)


def normalize_regularity(text: str) -> str:
    """Strip the decoration that hides a merged regularity token (review finding 6):
    ^ { } _ and whitespace, so 'C^{0} or C^{2}' normalizes to 'C0orC2'."""
    return re.sub(r"[\^_{}\s]", "", text)


def merged_match(text: str) -> bool:
    return bool(MERGED_RE.search(text)) or bool(MERGED_RE.search(normalize_regularity(text)))
REQUIRED_CLASS_KEYS = ["axes", "hypotheses", "exclusions", "conclusion", "test_cases", "provenance"]
ALLOWED_FAMILY_AXES = {"family", "matter_model", "symmetry", "asymptotics", "regularity_token",
                       "genericity_kind", "conclusion_type"}


def semantic_subset(tax: dict) -> str:
    """Content that may state a class binding. Guard/prohibition sections are excluded by
    construction: they must be allowed to name the forbidden pattern they prohibit."""
    content = {
        "scope_statement": tax.get("scope_statement"),
        "classes": {
            cid: {
                "label": c.get("label"),
                "axes": c.get("axes"),
                "hypotheses": c.get("hypotheses"),
                "exclusions": c.get("exclusions"),
                "conclusion": c.get("conclusion"),
                "candidate_consequences": c.get("candidate_consequences"),
                "test_cases": c.get("test_cases"),
            }
            for cid, c in tax.get("classes", {}).items()
        },
        "disjointness": [{k: d.get(k) for k in ("pair", "separation")}
                         for d in tax.get("disjointness", [])],
        "disjointness_scope": tax.get("disjointness_scope"),
        "disjointness_overlap_note": tax.get("disjointness_overlap_note"),
        "open_questions": tax.get("open_questions"),
    }
    return json.dumps(content, sort_keys=True, default=str)


def check(tax: dict, raw: str, cases: list | None = None):
    ok, fail = [], []

    def req(cond, msg):
        (ok if cond else fail).append(msg)

    # A. identity
    ids = tax.get("class_ids")
    req(ids == FROZEN, "A: class_ids are exactly the four frozen classes")
    classes = tax.get("classes", {})
    req(set(classes) == set(FROZEN), "A: classes keys are exactly the four frozen classes")

    # B + C
    for cid in FROZEN:
        c = classes.get(cid, {})
        for key in REQUIRED_CLASS_KEYS:
            req(key in c and c[key], f"B[{cid}]: {key} present and non-empty")
        ax = c.get("axes", {})
        concl = c.get("conclusion", {})
        req(concl.get("type") == ax.get("conclusion_type"),
            f"B[{cid}]: conclusion.type matches axes.conclusion_type")
        req(bool(c.get("test_cases", {}).get("positive")) and bool(c.get("test_cases", {}).get("negative")),
            f"B[{cid}]: has one positive and one negative test case")
        fam, tok = ax.get("family"), ax.get("regularity_token")
        if fam == "SCC":
            req(tok in {"C0", "C2"}, f"C[{cid}]: SCC carries exactly one token in {{C0,C2}}")
            name_tok = re.match(r"AF-SCC-(C0|C2)-", cid)
            if name_tok:
                want = name_tok.group(1)
                req(tok == want, f"C[{cid}]: regularity_token matches the token in the class id")
                req(ax.get("conclusion_type") == f"strong_cosmic_censorship_{want}",
                    f"C[{cid}]: conclusion_type matches the class id token")
        elif fam == "WCC":
            req(tok is None, f"C[{cid}]: WCC carries no regularity token")
        else:
            req(False, f"C[{cid}]: family is WCC or SCC")
        for hyp in c.get("hypotheses", []):
            req("id" in hyp and "text" in hyp, f"B[{cid}]: hypothesis has id/text")

    # D. disjointness
    pairs = {tuple(sorted(d.get("pair", []))) for d in tax.get("disjointness", [])}
    expected = {tuple(sorted(p)) for p in itertools.combinations(FROZEN, 2)}
    req(pairs == expected, "D: disjointness covers all 6 pairs")
    for d in tax.get("disjointness", []):
        a, b = d.get("pair", [None, None])
        axes = d.get("decisive_axes", [])
        req(bool(axes) and all(x in ALLOWED_FAMILY_AXES for x in axes),
            f"D[{a},{b}]: decisive_axes are non-empty known axis names")
        va, vb = classes.get(a, {}).get("axes", {}), classes.get(b, {}).get("axes", {})
        differs = [x for x in axes if va.get(x) != vb.get(x)]
        req(bool(differs), f"D[{a},{b}]: named decisive axes actually differ")

    # E. transfer rules
    tr = tax.get("transfer_rules", {})
    allowed = tr.get("allowed", [])
    req(bool(allowed) and all(x.get("from") == "AF-SCC-C0-VAC-GEN" and x.get("to") == "AF-SCC-C2-VAC-GEN"
                              for x in allowed),
        "E: only C0->C2 strengthening is allowed")
    for x in allowed:
        req(bool(x.get("guards")), f"E: allowed transfer {x.get('id')} declares guards")
    kinds = {x.get("kind") for x in tr.get("forbidden", [])}
    for k in ["conclusion_inflation", "matter_leakage", "symmetry_release",
              "conclusion_family_leakage", "class_merge"]:
        req(k in kinds, f"E: forbidden transfer covers {k}")

    # J. disjointness scope is machine-visible, not only a comment (lead-audit HF-04)
    req("descriptor" in str(tax.get("disjointness_scope", "")).lower(),
        "J: disjointness_scope states the table is descriptor-level")
    req(bool(tax.get("disjointness_overlap_note")),
        "J: disjointness_overlap_note documents that data sets may overlap")

    # F. merged regularity in semantic content (guards may name the pattern)
    req(not merged_match(semantic_subset(tax)),
        "F: no merged regularity string in class content (G3, plain or braced/superscript)")

    # G. no theorem-status claim in a draft
    req(tax.get("claims_theorem_status") is False, "G: claims_theorem_status is false")
    req(all(c.get("conclusion", {}).get("type") != "theorem" for c in classes.values()),
        "G: no class carries conclusion_type 'theorem' in an unverified draft")

    # I. inline test cases classify under exactly one class (the assigned F0 falsifier)
    for cid in FROZEN:
        c = classes.get(cid, {})
        hyp_ids = {h.get("id") for h in c.get("hypotheses", [])}
        for key in ("positive", "negative", "negative_2"):
            case = c.get("test_cases", {}).get(key)
            if not case:
                continue
            hyp = case.get("decisive_hypotheses", [])
            req(bool(hyp) and all(h in hyp_ids for h in hyp),
                f"I[{case.get('id')}]: decisive hypotheses exist in {cid}")
            exp = str(case.get("expected_classification", ""))
            head = exp.split()[0] if exp else ""
            if key == "positive":
                req(head == cid, f"I[{case.get('id')}]: positive case classifies in {cid}")
            else:
                req(head in FROZEN or head.startswith(("excluded_by:", "rejected_by:")),
                    f"I[{case.get('id')}]: negative case names a frozen class or an explicit reason")
                if head in FROZEN:
                    req(head != cid, f"I[{case.get('id')}]: negative case does not classify in its source class")

    # H. optional worker-02 corpus
    if cases is not None:
        case_rows = [c for c in cases if c.get("record_type") in (None, "case")]
        metas = [c for c in cases if c.get("record_type") == "meta"]
        req(len(case_rows) > 0, "H: cases file has case rows")
        if metas:
            counts = metas[0].get("counts", {})
            npos = sum(1 for c in case_rows if c.get("polarity") == "positive")
            nneg = sum(1 for c in case_rows if c.get("polarity") == "negative")
            req(counts.get("positive") == npos and counts.get("negative") == nneg,
                "H: meta counts match actual polarity counts")
        guard_ids = ({g.get("id") for g in tax.get("guards", [])}
                     | {x.get("id") for x in tax.get("transfer_rules", {}).get("forbidden", [])}
                     | {x.get("id") for x in tax.get("coverage_gaps", [])}
                     | {q.get("id") for q in tax.get("open_questions", [])})
        for case in case_rows:
            cid = case.get("case_id", "?")
            pol = case.get("polarity")
            filed = case.get("class_id") or case.get("as_filed_class_id")
            if filed in FROZEN:
                req(True, f"H[{cid}]: filed class id is in the frozen set")
            else:
                # A non-frozen filed id is legitimate exactly when it is the planted defect
                # of a negative case (merged C0/C2, merged WCC/SCC, out-of-vocabulary axis).
                req(pol == "negative" and bool(case.get("violated_vocabulary") or case.get("expected_leak_rule")),
                    f"H[{cid}]: non-frozen filed class id is a planted negative defect")
            exp = str(case.get("expected_classification", ""))
            head = exp.split()[0] if exp else ""
            if pol == "positive":
                req(head in FROZEN, f"H[{cid}]: positive expected_classification is a frozen class")
            elif pol == "negative":
                req(case.get("expected_verdict") == "reject", f"H[{cid}]: negative case expects reject")
                req(head in FROZEN or head in {"NO_CLASS_IN_TAXONOMY", "AMBIGUOUS_SPLIT_REQUIRED"},
                    f"H[{cid}]: negative expected_classification is a class or explicit sentinel")
            else:
                req(False, f"H[{cid}]: polarity is positive or negative")
            for m in re.finditer(r"\b(AF-[A-Z0-9-]+):(H\d+)", str(case.get("decisive_hypothesis", ""))):
                cls, hid = m.group(1), m.group(2)
                hyp_ids = {h.get("id") for h in classes.get(cls, {}).get("hypotheses", [])}
                req(cls in FROZEN and hid in hyp_ids,
                    f"H[{cid}]: hypothesis ref {cls}:{hid} resolves in the taxonomy")
            rule = str(case.get("expected_leak_rule") or "")
            if pol == "negative" and rule:
                prefix = rule.split("-")[0]
                if prefix in guard_ids:
                    req(True, f"H[{cid}]: leak rule {rule} resolves to a taxonomy id")
                elif re.fullmatch(r"(?:G|X|CG|Q)\d+", prefix):
                    req(False, f"H[{cid}]: leak rule {rule} uses a taxonomy namespace prefix that does not resolve")
                else:
                    req(True, f"H[{cid}]: leak rule {rule} is an external catalog rule (not taxonomy-namespaced)")

    return ok, fail


def self_test():
    import yaml
    raw = (ROOT / "research_map" / "formulation_taxonomy.yaml").read_text()
    tax = yaml.safe_load(raw)
    base_ok, base_fail = check(tax, raw)
    mutations = []
    m1 = yaml.safe_load(raw)
    m1["classes"]["AF-SCC-C2-VAC-GEN"]["axes"]["regularity_token"] = "C0"
    mutations.append(("duplicate token", m1, raw))
    m2 = yaml.safe_load(raw)
    m2["disjointness"][2]["decisive_axes"] = ["asymptotics"]
    mutations.append(("same-value disjointness axis", m2, raw))
    m3 = yaml.safe_load(raw)
    m3["classes"]["AF-WCC-VAC-GEN"]["conclusion"]["text"] += " This also yields a C0 or C2 conclusion."
    mutations.append(("merged regularity string", m3, raw))
    m4 = yaml.safe_load(raw)
    m4["classes"]["AF-SCC-C0-VAC-GEN"]["test_cases"]["negative"]["expected_classification"] = "AF-SCC-C0-VAC-GEN"
    mutations.append(("self-classified negative case", m4, raw))
    m5 = yaml.safe_load(raw)
    m5["classes"]["AF-SCC-C2-VAC-GEN"]["conclusion"]["text"] += " The result holds for C^{0} or C^{2} extensions."
    mutations.append(("braced merged regularity string", m5, raw))
    m6 = yaml.safe_load(raw)
    m6.pop("disjointness_scope", None)
    mutations.append(("missing descriptor-level disjointness scope", m6, raw))
    results = {"baseline_passes": not base_fail, "baseline_failures": base_fail}
    for name, mtax, mraw in mutations:
        _, mfail = check(mtax, mraw)
        results[name] = bool(mfail)
    results["all_mutations_caught"] = all(v for k, v in results.items() if k not in
                                          ("baseline_passes", "baseline_failures", "all_mutations_caught"))
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=str(ROOT / "research_map" / "formulation_taxonomy.yaml"))
    ap.add_argument("--cases", default=str(ROOT / "schemas" / "taxonomy_cases.jsonl"))
    ap.add_argument("--json", default=None)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        res = self_test()
        print(json.dumps(res, indent=2))
        return 0 if res["baseline_passes"] and res["all_mutations_caught"] else 1

    import yaml
    path = Path(args.file)
    raw = path.read_text()
    tax = yaml.safe_load(raw)
    cases = None
    cpath = Path(args.cases)
    if cpath.exists():
        cases = [json.loads(l) for l in cpath.read_text().splitlines() if l.strip()]

    ok, fail = check(tax, raw, cases)
    by_group = {}
    for m in ok:
        by_group[m.split(":")[0]] = by_group.get(m.split(":")[0], 0) + 1
    report = {"file": str(path), "checks_passed": len(ok), "checks_failed": len(fail),
              "checks_passed_by_group": by_group,
              "failures": fail, "cases_checked": len(cases) if cases is not None else None,
              "verdict": "pass" if not fail else "fail",
              "note": "machine acceptance only; reviewer verdicts still required for G-F0"}
    for m in ok:
        print(f"  PASS  {m}")
    for m in fail:
        print(f"  FAIL  {m}")
    print(json.dumps({k: report[k] for k in ("checks_passed", "checks_failed", "cases_checked", "verdict")}))
    if args.json:
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json).write_text(json.dumps(report, indent=2) + "\n")
        print(f"wrote {args.json}")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
