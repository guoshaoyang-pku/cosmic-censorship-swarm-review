#!/usr/bin/env python3
"""W061-PREDICATE-CONSISTENCY-V1 -- proposed gate rule for the visibility-predicate axis.

Motivation (worker-061 finding F-06 of W061-F1-INDEP-REV-02): the binding canonical
structural gate `artifacts/formulation/tools/check_class_schema.py` has no rule that resolves
the visibility predicate named by `conclusion.statement_formal` and checks that
`quantifiers.formal`, the not_exists domain (`D5`) and `quantifiers.negation` expand the SAME
predicate form (single-q TAIL vs whole-curve/set-based).  A class-identity substitution that
the schema itself forbids (`visibility.must_not_conflate`, `class_identity_variants`) therefore
passes the gate.  This file is a standalone, dependency-free rule that closes that axis.

Scope: structure of the assertive surface only.  It does not decide physical truth, does not
verify citations, does not check the top-level key whitelist (that is R22 of the binding gate),
and does not set a gate verdict by itself -- it emits a rule report for the controller/lead.

Usage:
    python3 check_predicate_consistency.py SCHEMA.yaml [--json OUT] [--class-id ID] [--label L]

Exit codes: 0 = pass or not_applicable, 1 = fail (including strict-parse failure), 2 = usage.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

CST = timezone(timedelta(hours=8))
RULE_SET = "W061-PREDICATE-CONSISTENCY-V1"

TAIL_MARKERS = ("gamma([t0,t))", "t0 in [0,t)", "tail")
WHOLE_CURVE_PATTERNS = [
    # assertive whole-curve single-q containment
    r"gamma\(\[0,t\)\)\s*(?:is contained in|lies in|subset of|\u2282)\s*(?:the causal past\s*)?j\^-\(q\)",
    # whole-curve shorthand without a t0 binder
    r"with\s+gamma\s+subset\s+(?:j\^-\(q\)|b)\b",
    # set-based / union reading (variant SET)
    r"union of j\^-\(q\)",
    r"j\^\(-\)?\(?i\+\)?\)?\s+as a set",
    r"set-based visibility",
]
REPUDIATION = ("not the predicate", "strictly stronger", "must not", "never", "not equivalent",
               "misclassify", "is not this class", "variant", "forbidden", "not equivalent to")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def duplicate_keys(node, path=""):
    out = []
    if isinstance(node, yaml.MappingNode):
        seen = set()
        for k_node, v_node in node.value:
            k = getattr(k_node, "value", str(k_node))
            if k in seen:
                out.append(f"{path}/{k}")
            seen.add(k)
            out.extend(duplicate_keys(v_node, f"{path}/{k}"))
    elif isinstance(node, yaml.SequenceNode):
        for i, v_node in enumerate(node.value):
            out.extend(duplicate_keys(v_node, f"{path}[{i}]"))
    return out


def get(d, dotted, default="<MISSING>"):
    cur = d
    for k in dotted.split("."):
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur


def norm(x) -> str:
    return " ".join(str(x).split()) if x is not None else ""


def line_numbers(text: str, needle: str):
    n = norm(needle).lower()
    if not n:
        return []
    return [i for i, line in enumerate(text.splitlines(), 1) if n in norm(line).lower()]


def sentences(text: str):
    return [s.strip() for s in re.split(r"(?<=[.;])\s+", norm(text)) if s.strip()]


def assertive_clause(text: str):
    """Return whole-curve/set-based sentences that are not explicitly repudiated."""
    hits = []
    for s in sentences(text):
        low = s.lower()
        for pat in WHOLE_CURVE_PATTERNS:
            if re.search(pat, low):
                if not any(r in low for r in REPUDIATION):
                    hits.append(s)
                break
    return hits


def iff_clause(definition: str) -> str:
    """Extract the clause after the defining 'iff' (or the whole string if none)."""
    m = re.search(r"\biff\b(.*)", norm(definition), re.I)
    return (m.group(1) if m else norm(definition)).strip()


def has_tail_markers(text: str) -> bool:
    low = norm(text).lower()
    return "gamma([t0,t))" in low and "t0 in [0,t)" in low


class RuleReport:
    def __init__(self, path: str, raw: bytes):
        self.path = path
        self.sha256 = sha256_bytes(raw)
        self.text = raw.decode("utf-8", "replace")
        self.rules = []
        self.data = None
        self.parse_error = None

    def add(self, rule_id, ok, detail, evidence=None, required=True):
        self.rules.append({
            "rule_id": rule_id,
            "status": "pass" if ok else "fail",
            "required": required,
            "detail": detail,
            "evidence_lines": evidence or [],
        })

    def failed(self):
        return [r["rule_id"] for r in self.rules if r["required"] and r["status"] != "pass"]


def evaluate(path: Path, expected_class=None, label=None) -> dict:
    raw = path.read_bytes()
    rep = RuleReport(str(path), raw)

    # R0 -- strict parse ------------------------------------------------
    try:
        node = yaml.compose(rep.text)
        dups = duplicate_keys(node) if node is not None else []
    except yaml.YAMLError as exc:
        dups = []
        rep.parse_error = f"{type(exc).__name__}: {exc}"
    if rep.parse_error:
        rep.add("R0-strict-yaml-parse", False, {"error": rep.parse_error})
        return finalize(rep, label, expected_class)
    rep.add("R0-strict-yaml-parse", not dups,
            {"duplicate_key_paths": dups,
             "note": "yaml.safe_load keeps last-wins on duplicates; the rule refuses to reason on such bytes"})

    try:
        data = yaml.safe_load(rep.text)
    except yaml.YAMLError as exc:
        rep.parse_error = f"{type(exc).__name__}: {exc}"
        rep.add("R0-strict-yaml-parse", False, {"error": rep.parse_error})
        return finalize(rep, label, expected_class)
    if not isinstance(data, dict):
        rep.add("R0-strict-yaml-parse", False, {"error": "top level is not a mapping"})
        return finalize(rep, label, expected_class)
    rep.data = data
    class_id = data.get("class_id") or get(data, "class_identity.class_id", "<MISSING>")

    vis = data.get("visibility") if isinstance(data.get("visibility"), dict) else None
    pred_name = norm(vis.get("predicate_name")) if vis else ""
    vis_def = norm(vis.get("definition")) if vis else ""
    stmt_formal = norm(get(data, "conclusion.statement_formal", ""))
    formal = norm(get(data, "quantifiers.formal", ""))
    negation = norm(get(data, "quantifiers.negation", ""))

    if not vis or not (vis_def or pred_name):
        rep.add("R1-applicability", True,
                {"applicable": False, "reason": "no visibility.definition / predicate_name in this schema "
                                                "(rule is bound to the WCC visibility class; SCC classes have none)",
                 "class_id": class_id})
        return finalize(rep, label, expected_class, applicable=False)

    rep.add("R1-applicability", True, {"applicable": True, "class_id": class_id,
                                       "predicate_name": pred_name})

    # R2 -- predicate resolution + canonical predicate is the single-q TAIL form ----
    called = bool(pred_name) and pred_name in stmt_formal
    rep.add("R2-predicate-resolves-and-is-called",
            bool(pred_name) and bool(vis_def) and called,
            {"predicate_name": pred_name, "definition_present": bool(vis_def),
             "called_in_conclusion_statement_formal": called,
             "evidence_lines": line_numbers(rep.text, pred_name)[:6]})

    defining = iff_clause(vis_def)
    defining_tail = has_tail_markers(defining)
    assert_hits = assertive_clause(defining)
    rep.add("R3-canonical-predicate-is-tail",
            defining_tail and not assert_hits,
            {"defining_iff_clause": defining[:320],
             "tail_markers_in_defining_clause": defining_tail,
             "assertive_whole_curve_or_set_based_clauses": assert_hits,
             "evidence_lines": line_numbers(rep.text, "predicate_name")})

    # R4 -- quantifiers.formal expands the same predicate ---------------------------
    formal_tail = has_tail_markers(formal) or ("gamma([t0,t))" in formal.lower())
    formal_pred = (pred_name in formal) if pred_name else False
    formal_assert = assertive_clause(formal)
    formal_ok = formal_tail and not formal_assert
    rep.add("R4-formal-matches-predicate", formal_ok,
            {"formal_tail_expansion": formal_tail,
             "calls_predicate_by_name": formal_pred,
             "assertive_whole_curve_clauses": formal_assert,
             "formal_tail_excerpt": formal.split("finite affine length")[-1].strip()[:260],
             "evidence_lines": line_numbers(rep.text, "not exists q in I+")[:4]})

    # R5 -- the not_exists domain definition expands the same predicate -------------
    ordered = get(data, "quantifiers.ordered", [])
    domain_id = None
    if isinstance(ordered, list):
        for e in ordered:
            if isinstance(e, dict) and str(e.get("kind", "")).startswith("not_exists"):
                if "q" in str(e.get("binder", "")):
                    domain_id = e.get("domain_id")
    if domain_id is None:
        domain_id = "D5"
    dom = get(data, f"quantifiers.domains.{domain_id}.definition", "")
    dom_tail = has_tail_markers(dom)
    dom_assert = assertive_clause(dom)
    rep.add("R5-not-exists-domain-matches-predicate",
            bool(dom) and dom_tail and not dom_assert,
            {"domain_id": domain_id,
             "domain_tail_expansion": dom_tail,
             "assertive_whole_curve_clauses": dom_assert,
             "domain_excerpt": norm(dom)[:300],
             "evidence_lines": line_numbers(rep.text, f"{domain_id}:")})

    # R6 -- negation is the exact negation of the TAIL predicate --------------------
    neg_tail = "visible from i+" in negation.lower() and "tail" in negation.lower()
    neg_assert = assertive_clause(negation)
    neg_ok = bool(negation) and neg_tail and not neg_assert
    neg_concl = norm(get(data, "visibility.negation_conclusion", ""))
    neg_concl_ok = (not neg_concl) or ("t0 in [0,t)" in neg_concl.lower()
                                       and "tail" in neg_concl.lower())
    rep.add("R6-negation-is-exact-negation-of-tail",
            neg_ok and neg_concl_ok,
            {"negation_tail_form": neg_tail,
             "negation_assertive_whole_curve_clauses": neg_assert,
             "negation_excerpt": negation[-260:],
             "negation_conclusion_tail_form": neg_concl_ok,
             "evidence_lines": line_numbers(rep.text, "negation:")[:4]})

    # R7 -- the registered variant reading is not on the assertive surface ----------
    surface = {"visibility.definition": vis_def, "quantifiers.formal": formal,
               "quantifiers.negation": negation, "conclusion.statement_formal": stmt_formal}
    variant_hits = {k: assertive_clause(v) for k, v in surface.items() if assertive_clause(v)}
    rep.add("R7-variant-reading-not-assertive", not variant_hits,
            {"assertive_surface_variant_hits": variant_hits,
             "note": "variant SET / union-of-J^-(q) wording is allowed only under "
                     "class_identity_variants, must_not_conflate and explanatory negation text"})

    # R8 -- optional expected class binding ----------------------------------------
    if expected_class:
        rep.add("R8-class-id-binding", class_id == expected_class,
                {"expected": expected_class, "found": class_id})

    return finalize(rep, label, expected_class)


def finalize(rep: RuleReport, label, expected_class, applicable=True) -> dict:
    failed = rep.failed()
    if not applicable:
        verdict = "not_applicable"
    else:
        verdict = "fail" if failed else "pass"
    return {
        "rule_set": RULE_SET,
        "label": label,
        "target": rep.path,
        "sha256": rep.sha256,
        "class_id": (rep.data or {}).get("class_id"),
        "applicable": applicable,
        "verdict": verdict,
        "failed_rules": failed,
        "rules": rep.rules,
        "generated_at": datetime.now(CST).isoformat(timespec="seconds"),
        "scope_limit": ("structural consistency of the visibility-predicate axis only; not a gate "
                        "verdict, not a truth claim, not a citation check, not an R22 key check"),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("schema")
    ap.add_argument("--json", dest="json_out")
    ap.add_argument("--class-id", dest="class_id")
    ap.add_argument("--label")
    args = ap.parse_args()
    path = Path(args.schema)
    if not path.exists():
        print(json.dumps({"error": f"no such file: {path}"}), file=sys.stderr)
        return 2
    report = evaluate(path, expected_class=args.class_id, label=args.label or path.stem)
    out = json.dumps(report, indent=2, sort_keys=False)
    if args.json_out:
        Path(args.json_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_out).write_text(out + "\n")
    print(out)
    return 0 if report["verdict"] in ("pass", "not_applicable") else 1


if __name__ == "__main__":
    sys.exit(main())
