#!/usr/bin/env python3
"""Candidate SEMANTIC conclusion-axis invariance checker (worker-060) -- PROPOSAL ONLY.

Scope: the conclusion-statement axis of the AF-SCC-C2-VAC-GEN / AF-SCC-C0-VAC-GEN
class schemas -- conclusion.statement_formal, conclusion.statement_natural_language
and conclusion.conclusion_type -- measured as unchecked by both canonical stages
(stage A check_class_schema.py, stage B spec_conformance_audit.py) on FORM-HELDOUT-10
(informative C2/C0 union escape 1.0).

Why a semantic rule and not a content freeze: the in-flight worker-068 candidate
(artifacts/worker-068/polarity12/conclusion_freeze_check.py, variants
freeze_statements/freeze_full) catches m01-m06 but also flags the CONFORMING control
c02_conforming_c0_polished.yaml, whose conclusion sentence is a faithful rephrase
("cannot be extended to the future as a continuous Lorentzian manifold" ==
"future-inextendible as a continuous Lorentzian manifold").  A byte/content freeze
cannot separate a faithful negation-scoped rephrase from a polarity inversion.  The
rules here parse the negation scope instead:

  CS-F-EXT-ATOM   formal conclusion extension-predicate atom still present
  CS-F-EXT-POL    formal extension-predicate polarity preserved
  CS-NL-EXT-ATOM  natural-language conclusion predicate still asserted
                  (either the "inextendib*" lexeme or a negated extension lexeme)
  CS-NL-EXT-POL   natural-language does not assert a positive extension
  CS-NL-SCOPE     the frozen conclusion predicate is not itself negated
  CS-NL-REG       arm class/regularity phrase preserved (C2 / continuous Lorentzian)
  CS-TOKEN        conclusion_type token equals the arm base token

Every rule is relative to the PINNED canonical base of the fixture's own arm, is
base-gated (an axis absent from the base makes the rule skip), and is structural:
it never decides mathematics, class truth, or a gate verdict.  Flags are instrument
findings, not verdicts.  Independent of stage A/B code: stdlib + PyYAML only.
Read-only: the script never writes to a canonical path.

Usage:
  python3 check_conclusion_semantics.py --corpus artifacts/heldout/heldout-10 --json OUT
  python3 check_conclusion_semantics.py --selftest --json OUT
  python3 check_conclusion_semantics.py --corpus ... --json OUT \
      --compose-tenrules artifacts/worker-060/classmix_content_invariance/check_class_content_invariance.py \
      --compose-w068 artifacts/worker-068/polarity12/conclusion_freeze_check.py
Exit: 0 checked; 2 usage/IO/hash error or a flagged control (instrument invalid).
"""
from __future__ import annotations

import argparse
import copy
import datetime as _dt
import hashlib
import json
import os
import re
import subprocess
import sys
import unicodedata

try:
    import yaml
except ImportError:  # pragma: no cover
    print("PyYAML required", file=sys.stderr)
    sys.exit(2)

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

RULE_IDS = ["CS-F-EXT-ATOM", "CS-F-EXT-POL", "CS-NL-EXT-ATOM", "CS-NL-EXT-POL",
            "CS-NL-SCOPE", "CS-NL-REG", "CS-TOKEN"]
AXIS_OF_RULE = {
    "CS-F-EXT-ATOM": "formal conclusion predicate present",
    "CS-F-EXT-POL": "formal extension-predicate polarity",
    "CS-NL-EXT-ATOM": "natural-language conclusion predicate present",
    "CS-NL-EXT-POL": "natural-language extension polarity",
    "CS-NL-SCOPE": "natural-language negation scope over the conclusion predicate",
    "CS-NL-REG": "arm class/regularity phrase",
    "CS-TOKEN": "conclusion_type token vs arm base",
}
ARM_OF_CLASS = {
    "AF-SCC-C2-VAC-GEN": "C2",
    "AF-SCC-C0-VAC-GEN": "C0",
    "AF-WCC-VAC-GEN": "W",
}
# Arm regularity vocabulary (declared; the base must match at least one pattern of its
# own arm for the rule to be base-gated on, and the fixture must match at least one).
REG_VOCAB = {
    "C2": [r"\bc2\b", r"\bc\^2\b", r"twice continuously differentiable"],
    "C0": [r"\bc0\b", r"\bc\^0\b", r"continuous lorentzian"],
    "W": [r"\bc0\b", r"continuous lorentzian"],
}
# Extension lexemes.  (?<!in) excludes "inextendible"/"inextendibility"; "continuous"
# is excluded because continu(es|ed|ation|ing) does not match it.  The lookarounds use
# [a-z] rather than \b so that schema-internal identifiers such as
# "proper_future_extension_in_class" are matched (underscores are not word boundaries
# for \b, but they are not letters either).
EXT_RE = re.compile(
    r"(?<![a-z])(?<!in)extend(?:ed|s|ible|ibility|ing)?(?![a-z])"
    r"|(?<![a-z])extension(?:s)?(?![a-z])"
    r"|(?<![a-z])prolong(?:ed|s|ation)?(?![a-z])"
    r"|(?<![a-z])continu(?:ed|es|ation|ing)(?![a-z])",
    re.IGNORECASE,
)
INEXT_RE = re.compile(r"(?<![a-z])inextendib\w*|(?<![a-z])inextend\w*", re.IGNORECASE)
NEG_RE = re.compile(
    r"(?<![\w-])(?:not|no|never|without|absent|none|cannot|can't|can not|fails?|"
    r"impossible|neither|nor|nothing|lacks?|devoid|¬)(?![\w-])",
    re.IGNORECASE,
)
# A negation that scopes directly over the frozen conclusion predicate.
SCOPE_FLIP_RE = re.compile(
    r"(?:\b(?:is|are|was|were|be)\s+not|\bnot|\bnever|\bno longer)\s+"
    r"(?:\w+\s+){0,3}?inextendib\w*"
    r"|\b(?:does|do|did)(?:n't|\s+not)\s+(?:admit|have|possess|yield|imply)\b[^.;]{0,60}?inextendib\w*",
    re.IGNORECASE,
)


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def norm(s) -> str:
    if s is None:
        return ""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", str(s))).strip().lower()


def get(obj, dotted, default=None):
    cur = obj
    for key in dotted.split("."):
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


def split_clauses(text: str):
    return [c.strip() for c in re.split(r"[.;]\s*|,\s*", text) if c.strip()]


# ------------------------------------------------------------------ rule helpers

def extension_atoms(text: str):
    """[(lexeme, negated_in_clause)] over one clause."""
    t = norm(text)
    return [(m.group(0), bool(NEG_RE.search(t))) for m in EXT_RE.finditer(t)]


def has_inext(text: str) -> bool:
    return bool(INEXT_RE.search(norm(text)))


def has_scope_flip(text: str) -> bool:
    return bool(SCOPE_FLIP_RE.search(norm(text)))


def reg_matches(text: str, arm: str):
    t = norm(text)
    return [p for p in REG_VOCAB.get(arm, []) if re.search(p, t)]


# ------------------------------------------------------------- profile + rules

def profile(fixture_doc: dict, base_doc: dict):
    """Base-relative semantic profile of the conclusion statements."""
    out = {}
    for field, is_formal in (("conclusion.statement_formal", True),
                             ("conclusion.statement_natural_language", False)):
        b = norm(get(base_doc, field))
        f = norm(get(fixture_doc, field))
        if is_formal:
            b_atoms = extension_atoms(b)
            f_atoms = extension_atoms(f)
            out[field] = {
                "base_extension_atoms": [a for a, _ in b_atoms],
                "base_polarity": "negative" if (b_atoms and all(n for _, n in b_atoms)) else
                                 ("positive" if b_atoms else None),
                "base_has_inext": has_inext(b),
                "fixture_extension_atoms": [a for a, _ in f_atoms],
                "fixture_polarity": "negative" if (f_atoms and all(n for _, n in f_atoms)) else
                                    ("positive" if f_atoms else None),
                "fixture_has_inext": has_inext(f),
            }
        else:
            b_clauses = split_clauses(b)
            f_clauses = split_clauses(f)
            b_neg = sum(1 for c in b_clauses for _, n in extension_atoms(c) if n)
            f_neg = sum(1 for c in f_clauses for _, n in extension_atoms(c) if n)
            f_pos = sum(1 for c in f_clauses for _, n in extension_atoms(c) if not n)
            out[field] = {
                "base_has_inext": has_inext(b),
                "base_negated_extension_lexemes": b_neg,
                "fixture_has_inext": has_inext(f),
                "fixture_negated_extension_lexemes": f_neg,
                "fixture_positive_extension_lexemes": f_pos,
                "fixture_scope_flip": has_scope_flip(f),
                "base_reg_patterns": reg_matches(b, ARM_OF_CLASS.get(get(base_doc, "class_id"), "")),
                "fixture_reg_patterns": reg_matches(f, ARM_OF_CLASS.get(get(base_doc, "class_id"), "")),
            }
    return out


def check_fixture(fixture_doc: dict, base_doc: dict):
    prof = profile(fixture_doc, base_doc)
    flags = {}
    fp = prof["conclusion.statement_formal"]
    np_ = prof["conclusion.statement_natural_language"]

    # CS-F-EXT-ATOM
    if fp["base_extension_atoms"] and not fp["fixture_extension_atoms"]:
        flags["CS-F-EXT-ATOM"] = [
            f"formal extension-predicate atom(s) {fp['base_extension_atoms']} absent from the fixture formal statement"
        ]
    # CS-F-EXT-POL
    if fp["base_polarity"] and fp["fixture_polarity"] and fp["base_polarity"] != fp["fixture_polarity"]:
        flags["CS-F-EXT-POL"] = [
            f"formal extension polarity {fp['base_polarity']} -> {fp['fixture_polarity']}"
        ]
    # CS-NL-EXT-ATOM
    base_asserts = np_["base_has_inext"] or np_["base_negated_extension_lexemes"] > 0
    fx_asserts = np_["fixture_has_inext"] or np_["fixture_negated_extension_lexemes"] > 0
    if base_asserts and not fx_asserts:
        flags["CS-NL-EXT-ATOM"] = [
            "natural-language conclusion predicate erased: no inextendibility lexeme and no negated extension lexeme"
        ]
    # CS-NL-EXT-POL
    if np_["fixture_positive_extension_lexemes"] > 0:
        flags["CS-NL-EXT-POL"] = [
            f"natural-language asserts {np_['fixture_positive_extension_lexemes']} positive extension lexeme(s)"
        ]
    # CS-NL-SCOPE
    if base_asserts and np_["fixture_scope_flip"]:
        flags["CS-NL-SCOPE"] = [
            "negation scopes directly over the frozen conclusion predicate (inextendibility denied)"
        ]
    # CS-NL-REG
    if np_["base_reg_patterns"] and not np_["fixture_reg_patterns"]:
        flags["CS-NL-REG"] = [
            f"arm regularity phrase {np_['base_reg_patterns']} absent from the natural-language statement"
        ]
    # CS-TOKEN
    b_tok = norm(get(base_doc, "conclusion.conclusion_type"))
    f_tok = norm(get(fixture_doc, "conclusion.conclusion_type"))
    if b_tok != f_tok:
        flags["CS-TOKEN"] = [f"conclusion_type {b_tok!r} -> {f_tok!r}"]

    return {"flags": flags, "verdict": "FLAG" if flags else "PASS", "profile": prof}


# ------------------------------------------------------------------ corpus run

def load_bases(man):
    bases, hashes = {}, {}
    for arm in ("W", "C2", "C0"):
        spec = man.get("bases", {}).get(arm)
        if not spec:
            continue
        p = spec["path"] if isinstance(spec, dict) else spec
        bs = spec.get("sha256") if isinstance(spec, dict) else None
        cand = p if os.path.isabs(p) and os.path.exists(p) else os.path.join(ROOT, p)
        if not os.path.exists(cand):
            raise SystemExit(f"[exit2] base not found: {p}")
        measured = sha256_file(cand)
        if bs and measured != bs:
            raise SystemExit(f"[exit2] base {p} hash drift {measured[:16]} != manifest {bs[:16]}")
        bases[arm] = yaml.safe_load(open(cand))
        hashes[arm] = {"path": p, "manifest_sha256": bs, "measured_sha256": measured,
                       "match": (bs is None or measured == bs)}
    return bases, hashes


def run_corpus(corpus_dir):
    man_path = os.path.join(corpus_dir, "manifest.json")
    man = json.load(open(man_path))
    man_sha = sha256_file(man_path)
    bases, base_hashes = load_bases(man)
    rows = []
    for group, items in (("mutant", man.get("mutants", [])), ("control", man.get("controls", []))):
        for x in items:
            p = x["path"]
            cp = p if os.path.isabs(p) and os.path.exists(p) else os.path.join(ROOT, p)
            measured = sha256_file(cp)
            if measured != x.get("sha256"):
                raise SystemExit(f"[exit2] fixture hash drift {p}: {measured[:16]} != {x['sha256'][:16]}")
            arm = x.get("arm")
            base_doc = bases.get(arm) or bases.get("C2")
            base_path = base_hashes.get(arm, {}).get("path")
            fx = yaml.safe_load(open(cp))
            res = check_fixture(fx, base_doc)
            rows.append({
                "name": x.get("fixture") or os.path.basename(p),
                "group": group, "arm": arm,
                "family": x.get("family") or x.get("kind"),
                "class_id": x.get("class_id") or fx.get("class_id"),
                "path": p, "sha256": measured,
                "base_path": base_path,
                "flags": res["flags"], "verdict": res["verdict"], "profile": res["profile"],
            })
    canon = []
    for arm, obj in bases.items():
        res = check_fixture(obj, obj)
        canon.append({"name": f"frozen_canonical_{arm}", "group": "frozen_canonical", "arm": arm,
                      "family": "frozen_canonical",
                      "path": base_hashes[arm]["path"], "sha256": base_hashes[arm]["measured_sha256"],
                      "base_path": base_hashes[arm]["path"],
                      "flags": res["flags"], "verdict": res["verdict"], "profile": res["profile"]})
    return man, man_sha, base_hashes, rows + canon


def block(sel):
    n = len(sel)
    flagged = [r for r in sel if r["verdict"] == "FLAG"]
    return {"n": n, "flagged": len(flagged), "escaped": n - len(flagged),
            "escape_rate": round((n - len(flagged)) / n, 4) if n else None,
            "flagged_names": [r["name"] for r in flagged]}


def summarise(rows):
    muts = [r for r in rows if r["group"] == "mutant"]
    informative = [r for r in muts if r["arm"] in ("C2", "C0")]
    per_rule = {rid: sum(1 for r in rows if rid in r["flags"]) for rid in RULE_IDS}
    per_family = {}
    for r in muts:
        fam = r["family"] or "?"
        d = per_family.setdefault(fam, {"n": 0, "flagged": 0, "mutants": []})
        d["n"] += 1
        d["mutants"].append(r["name"])
        if r["verdict"] == "FLAG":
            d["flagged"] += 1
    controls = [r for r in rows if r["group"] in ("control", "frozen_canonical")]
    return {
        "all_mutants": block(muts),
        "informative_c2c0": block(informative),
        "wcc_arm": block([r for r in muts if r["arm"] == "W"]),
        "controls": block(controls),
        "per_rule_flag_counts_all_rows": per_rule,
        "per_family": per_family,
        "misses_informative": [r["name"] for r in informative if r["verdict"] == "PASS"],
        "false_positives_controls": [r["name"] for r in controls if r["verdict"] == "FLAG"],
    }


# ------------------------------------------------------------- fresh self-test

def fresh_corpus(c2_base, c0_base):
    """Independently worded mutants + conforming rephrases for the conclusion axis.
    Returns rows: (name, arm, obj, expect, family, operator)."""
    out = []

    def mk(base, arm, name, expect, family, operator, **fields):
        obj = copy.deepcopy(base)
        c = obj.setdefault("conclusion", {})
        for k, v in fields.items():
            c[k] = v
        out.append((name, arm, obj, expect, family, operator))

    # ---- C2 mutants (expect FLAG)
    mk(c2_base, "C2", "f01_formal_polarity_positive", "FLAG", "conclusion-polarity-inversion",
       "formal: negated existence -> positive existence",
       statement_formal="forall r in D0 exists G_r comeager forall D in G_r: "
                        "exists proper_future_extension_in_class(MGHD(D))")
    mk(c2_base, "C2", "f02_nl_polarity_positive", "FLAG", "conclusion-polarity-inversion",
       "nl: 'possesses a proper future C2 vacuum extension'",
       statement_natural_language="Generic asymptotically flat vacuum initial data have a maximal "
                                  "development that possesses a proper future C2 vacuum extension.")
    mk(c2_base, "C2", "f03_nl_predicate_erased", "FLAG", "conclusion-content-erasure",
       "nl: conclusion replaced by an existence statement (no inextendibility, no extension)",
       statement_natural_language="Generic asymptotically flat vacuum initial data have a maximal "
                                  "globally hyperbolic development.")
    mk(c2_base, "C2", "f04_nl_positive_continuation", "FLAG", "conclusion-polarity-inversion",
       "nl: 'can be continued beyond the future boundary'",
       statement_natural_language="Generic asymptotically flat vacuum initial data have a maximal "
                                  "development that can be continued beyond the future boundary as a "
                                  "C2 vacuum solution.")
    mk(c2_base, "C2", "f05_formal_predicate_replaced", "FLAG", "conclusion-content-erasure",
       "formal: extension predicate replaced by an unrelated property",
       statement_formal="forall r in D0 exists G_r comeager forall D in G_r: "
                        "MGHD(D) admits a future Cauchy horizon")
    mk(c2_base, "C2", "f06_nl_class_erased", "FLAG", "conclusion-class-phrase-erasure",
       "nl: C2 regularity phrase dropped",
       statement_natural_language="Generic asymptotically flat vacuum initial data have a maximal "
                                  "development that is future-inextendible as a Lorentzian manifold.")

    # ---- C0 mutants (expect FLAG)
    mk(c0_base, "C0", "f07_nl_polarity_positive", "FLAG", "conclusion-polarity-inversion",
       "nl: 'there exists a proper future C0 metric extension'",
       statement_natural_language="Generic asymptotically flat vacuum initial data have a maximal "
                                  "development to which there exists a proper future C0 metric extension.")
    mk(c0_base, "C0", "f08_nl_scope_flip", "FLAG", "natural-language-inversion",
       "nl: whole conclusion denied ('do not have ... future-inextendible')",
       statement_natural_language="Generic asymptotically flat vacuum initial data do not have a maximal "
                                  "development that is future-inextendible as a continuous Lorentzian manifold.")
    mk(c0_base, "C0", "f09_formal_polarity_positive", "FLAG", "conclusion-polarity-inversion",
       "formal: 'exists' -> '... exists' positive form",
       statement_formal="forall r in D0 exists G_r comeager forall D in G_r: "
                        "proper_future_extension_in_class(MGHD(D)) exists")
    mk(c0_base, "C0", "f10_nl_positive_extend", "FLAG", "conclusion-polarity-inversion",
       "nl: 'extends past its future boundary'",
       statement_natural_language="Generic asymptotically flat vacuum initial data have a maximal "
                                  "development that extends past its future boundary as a continuous "
                                  "Lorentzian manifold.")

    # ---- C2 conforming rephrases (expect PASS)
    mk(c2_base, "C2", "g01_nl_admitting_no_extension", "PASS", "conforming-rephrase",
       "nl: 'admitting no proper future extension in the C2 class'",
       statement_natural_language="Generic asymptotically flat vacuum initial data have a maximal "
                                  "development admitting no proper future extension in the C2 class.")
    mk(c2_base, "C2", "g02_nl_cannot_be_extended_synonym_reg", "PASS", "conforming-rephrase",
       "nl: 'cannot be extended ... twice continuously differentiable' (reg synonym)",
       statement_natural_language="Generic asymptotically flat vacuum initial data have a maximal "
                                  "development that cannot be extended to the future as a twice "
                                  "continuously differentiable vacuum solution.")
    mk(c2_base, "C2", "g03_nl_has_no_future_extension", "PASS", "conforming-rephrase",
       "nl: 'has no future extension within the C2 class'",
       statement_natural_language="For generic asymptotically flat vacuum initial data, the maximal "
                                  "development has no future extension within the C2 class of vacuum solutions.")
    mk(c2_base, "C2", "g04_formal_no_extension_exists", "PASS", "conforming-rephrase",
       "formal: 'no proper_future_extension_in_class(...) exists'",
       statement_formal="forall r in D0 exists G_r comeager forall D in G_r: "
                        "no proper_future_extension_in_class(MGHD(D)) exists")
    mk(c2_base, "C2", "g05_nl_no_development_admits_extension", "PASS", "conforming-rephrase",
       "nl: 'no maximal development admits a proper future C2 vacuum extension'",
       statement_natural_language="Generic asymptotically flat vacuum initial data are such that no "
                                  "maximal development admits a proper future C2 vacuum extension.")

    # ---- C0 conforming rephrases (expect PASS)
    mk(c0_base, "C0", "g06_nl_not_extendible", "PASS", "conforming-rephrase",
       "nl: 'is not extendible to the future'",
       statement_natural_language="Generic asymptotically flat vacuum initial data have a maximal "
                                  "development that is not extendible to the future as a continuous "
                                  "Lorentzian manifold.")
    mk(c0_base, "C0", "g07_nl_no_extension_c0", "PASS", "conforming-rephrase",
       "nl: 'there is no proper future extension ... within the C0 class' (reg synonym)",
       statement_natural_language="There is no proper future extension of the maximal development of "
                                  "generic asymptotically flat vacuum initial data within the C0 class.")
    mk(c0_base, "C0", "g08_nl_inextendible_plus_negated_extension", "PASS", "conforming-rephrase",
       "nl: inextendibility asserted, later clause denies a C0 extension",
       statement_natural_language="Generic asymptotically flat vacuum initial data have a "
                                  "future-inextendible maximal development as a continuous Lorentzian "
                                  "manifold; it does not admit a future C0 extension.")
    mk(c0_base, "C0", "g09_formal_does_not_exist", "PASS", "conforming-rephrase",
       "formal: '... does not exist'",
       statement_formal="forall r in D0, for a comeager G_r and every D in G_r, "
                        "proper_future_extension_in_class(MGHD(D)) does not exist")
    mk(c0_base, "C0", "g10_nl_cannot_be_continued", "PASS", "conforming-rephrase",
       "nl: 'cannot be continued to the future'",
       statement_natural_language="The maximal development of generic asymptotically flat vacuum "
                                  "initial data cannot be continued to the future as a continuous "
                                  "Lorentzian manifold.")
    return out


def run_fresh(c2_base, c0_base):
    rows = []
    for name, arm, obj, expect, family, operator in fresh_corpus(c2_base, c0_base):
        base = c2_base if arm == "C2" else c0_base
        res = check_fixture(obj, base)
        ok = (res["verdict"] == expect)
        rows.append({"name": name, "arm": arm, "family": family, "operator": operator,
                     "expect": expect, "verdict": res["verdict"], "agree": ok,
                     "flags": res["flags"], "profile": res["profile"]})
    n = len(rows)
    n_flag = sum(1 for r in rows if r["verdict"] == "FLAG")
    n_pass = n - n_flag
    expected_flag = sum(1 for r in rows if r["expect"] == "FLAG")
    expected_pass = n - expected_flag
    return {
        "n": n, "flagged": n_flag, "passed": n_pass,
        "mutants_expected_flag": expected_flag,
        "mutants_caught": sum(1 for r in rows if r["expect"] == "FLAG" and r["verdict"] == "FLAG"),
        "rephrases_expected_pass": expected_pass,
        "rephrases_false_positive": [r["name"] for r in rows
                                     if r["expect"] == "PASS" and r["verdict"] == "FLAG"],
        "mutant_misses": [r["name"] for r in rows
                          if r["expect"] == "FLAG" and r["verdict"] == "PASS"],
        "all_agree": all(r["agree"] for r in rows),
        "rows": rows,
    }


# --------------------------------------------------------------- compositions

def compose_tenrules(rows, tool, out_json):
    """Union with worker-060's ten non-conclusion rules (independent instrument)."""
    if not os.path.exists(tool):
        return {"error": f"tool not found: {tool}"}
    tool_sha = sha256_file(tool)
    cp = subprocess.run([sys.executable, tool, "--corpus", "artifacts/heldout/heldout-10",
                         "--json", out_json, "--live"], capture_output=True, text=True, timeout=900)
    if not os.path.exists(out_json):
        return {"error": f"no json written (exit {cp.returncode})", "stderr": cp.stderr[-800:]}
    ten = json.load(open(out_json))
    ten_by_name = {r["name"]: r for r in ten.get("rows", [])}
    union_rows = []
    for r in rows:
        t = ten_by_name.get(r["name"], {})
        mine = r["verdict"] == "FLAG"
        theirs = t.get("verdict") == "FLAG"
        union_rows.append({"name": r["name"], "group": r["group"], "arm": r.get("arm"),
                           "family": r.get("family"), "semantic": r["verdict"],
                           "ten_rules": t.get("verdict", "MISSING"),
                           "union": "FLAG" if (mine or theirs) else "PASS"})
    def ublock(sel):
        n = len(sel)
        caught = sum(1 for x in sel if x["union"] == "FLAG")
        return {"n": n, "union_caught": caught, "union_escape": n - caught,
                "union_escape_rate": round((n - caught) / n, 4) if n else None,
                "union_flagged_names": [x["name"] for x in sel if x["union"] == "FLAG"]}
    muts = [x for x in union_rows if x["group"] == "mutant"]
    informative = [x for x in muts if x["arm"] in ("C2", "C0")]
    controls = [x for x in union_rows if x["group"] in ("control", "frozen_canonical")]
    return {"tool": tool, "tool_sha256": tool_sha, "compose_json": out_json,
            "compose_json_sha256": sha256_file(out_json),
            "ten_rules_sha256": tool_sha,
            "authority": "worker-level composition of two PROPOSAL rule sets; not an adopted gate rule",
            "rows": union_rows,
            "informative_c2c0": ublock(informative),
            "all_mutants": ublock(muts),
            "controls": ublock(controls),
            "control_false_positives": [x["name"] for x in controls if x["union"] == "FLAG"],
            "ten_rules_own_measurement": ten.get("measurement"),
            "ten_rules_sha256_evidence": ten.get("generated_by_sha256")}


def compose_w068(rows, tool, base_of):
    """Union with the in-flight worker-068 content-freeze candidate (read-only)."""
    if not os.path.exists(tool):
        return {"error": f"tool not found: {tool}"}
    tool_sha = sha256_file(tool)
    out_rows = []
    for r in rows:
        arm = r.get("arm") or "C2"
        bp = base_of.get(arm) or base_of["C2"]
        cp = subprocess.run([sys.executable, tool, "--fixture", r["path"], "--base", bp,
                             "--variant", "freeze_statements", "--json"],
                            capture_output=True, text=True, timeout=180)
        try:
            verdict = json.loads(cp.stdout).get("verdict")
        except Exception:
            verdict = f"ERR(exit {cp.returncode})"
        mine = r["verdict"] == "FLAG"
        theirs = verdict == "FLAG"
        out_rows.append({"name": r["name"], "group": r["group"], "arm": arm,
                         "semantic": r["verdict"], "w068_freeze_statements": verdict,
                         "union": "FLAG" if (mine or theirs) else "PASS"})
    def ublock(sel):
        n = len(sel)
        caught = sum(1 for x in sel if x["union"] == "FLAG")
        return {"n": n, "union_caught": caught,
                "union_flagged_names": [x["name"] for x in sel if x["union"] == "FLAG"]}
    muts = [x for x in out_rows if x["group"] == "mutant"]
    informative = [x for x in muts if x["arm"] in ("C2", "C0")]
    controls = [x for x in out_rows if x["group"] in ("control", "frozen_canonical")]
    return {"tool": tool, "tool_sha256": tool_sha,
            "authority": "worker-level composition; the freeze variant is a PROPOSAL candidate",
            "rows": out_rows, "informative_c2c0": ublock(informative), "all_mutants": ublock(muts),
            "controls": ublock(controls),
            "control_false_positives": [x["name"] for x in controls if x["union"] == "FLAG"]}


def live_pin_check(base_hashes):
    """Compare the live canonical schemas to the corpus base bytes (non-fatal)."""
    live = {
        "C2": "schemas/af_scc_c2_vacuum.yaml",
        "C0": "schemas/af_scc_c0_vacuum.yaml",
        "W": "schemas/af_wcc_vacuum.yaml",
        "F0": "research_map/formulation_taxonomy.yaml",
        "FROZEN": "artifacts/formulation/FROZEN.json",
    }
    out = {}
    for k, p in live.items():
        fp = os.path.join(ROOT, p)
        out[k] = {"path": p, "exists": os.path.exists(fp),
                  "measured_sha256": sha256_file(fp) if os.path.exists(fp) else None}
    for arm in ("C2", "C0", "W"):
        if arm in base_hashes:
            out[arm]["corpus_base_sha256"] = base_hashes[arm]["measured_sha256"]
            out[arm]["matches_corpus_base"] = out[arm]["measured_sha256"] == base_hashes[arm]["measured_sha256"]
    out["drift"] = [k for k in ("C2", "C0", "W") if out.get(k, {}).get("matches_corpus_base") is False]
    out["scope_note"] = ("corpus bytes are authoritative for this measurement; live-pin drift is "
                         "reported, not repaired")
    return out


# ----------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default="artifacts/heldout/heldout-10")
    ap.add_argument("--json", default=None)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--compose-tenrules", default=None)
    ap.add_argument("--compose-w068", default=None)
    ap.add_argument("--stamp", default=None, help="fixed run timestamp for reproducibility")
    args = ap.parse_args()

    result = {
        "artifact": "worker-060 SEMANTIC conclusion-axis invariance candidate rule set (PROPOSAL)",
        "worker": "worker-060",
        "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "control_class_ids": ["AF-WCC-VAC-GEN"],
        "authority": "worker measurement evidence only; no gate verdict, no theorem, no canonical write",
        "counts_as_full_schema_verdict": False,
        "verdict_authority": "advisory_worker_evidence_only",
        "run_at": args.stamp or _dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "axes": {rid: AXIS_OF_RULE[rid] for rid in RULE_IDS},
        "generated_by": os.path.abspath(__file__),
        "generated_by_sha256": sha256_file(os.path.abspath(__file__)),
    }
    c2_base = yaml.safe_load(open(os.path.join(ROOT, "artifacts/heldout/heldout-10/bases/af_scc_c2_vacuum.yaml")))
    c0_base = yaml.safe_load(open(os.path.join(ROOT, "artifacts/heldout/heldout-10/bases/af_scc_c0_vacuum.yaml")))
    exit_code = 0

    if args.selftest:
        result["fresh_corpus"] = run_fresh(c2_base, c0_base)
        result["selftest_only"] = True
    else:
        cdir = args.corpus if os.path.isabs(args.corpus) else os.path.join(ROOT, args.corpus)
        man, man_sha, base_hashes, rows = run_corpus(cdir)
        result["corpus"] = {"id": man.get("corpus_id"), "dir": os.path.relpath(cdir, ROOT),
                            "manifest_sha256": man_sha, "frozen_revision": man.get("frozen_revision"),
                            "pins": man.get("pins"), "bases": base_hashes,
                            "authoritative": "corpus bytes; the manifest is an index, not evidence"}
        result["measurement"] = summarise(rows)
        result["rows"] = rows
        result["fresh_corpus"] = run_fresh(c2_base, c0_base)
        result["live_pin_check"] = live_pin_check(base_hashes)
        if args.compose_tenrules:
            tool = args.compose_tenrules if os.path.isabs(args.compose_tenrules) \
                else os.path.join(ROOT, args.compose_tenrules)
            cj = os.path.join(ROOT, "artifacts/worker-060/conclusion_semantic_invariance",
                              "compose_tenrules_evidence.json")
            result["union_with_ten_rules"] = compose_tenrules(rows, tool, cj)
        if args.compose_w068:
            tool = args.compose_w068 if os.path.isabs(args.compose_w068) \
                else os.path.join(ROOT, args.compose_w068)
            base_of = {arm: base_hashes[arm]["path"] for arm in base_hashes}
            result["union_with_worker068"] = compose_w068(rows, tool, base_of)
        iv = result["measurement"]["controls"]
        result["instrument_validity"] = {
            "frozen_canonicals_and_controls_all_pass": iv["flagged"] == 0,
            "control_flagged": iv["flagged_names"],
        }
        if iv["flagged"]:
            exit_code = 2
            result["invalid_reasons"] = [f"control flagged: {n}" for n in iv["flagged_names"]]

    text = json.dumps(result, indent=1, sort_keys=True, default=str)
    if args.json:
        outp = args.json if os.path.isabs(args.json) else os.path.join(ROOT, args.json)
        os.makedirs(os.path.dirname(outp), exist_ok=True)
        with open(outp, "w") as f:
            f.write(text + "\n")
    print(json.dumps({
        "wrote": args.json,
        "measurement": result.get("measurement"),
        "fresh": {k: v for k, v in result.get("fresh_corpus", {}).items() if k != "rows"},
        "union_with_ten_rules": {k: v for k, v in result.get("union_with_ten_rules", {}).items()
                                 if k not in ("rows", "ten_rules_own_measurement")},
        "union_with_worker068": {k: v for k, v in result.get("union_with_worker068", {}).items()
                                 if k != "rows"},
        "live_pin_drift": result.get("live_pin_check", {}).get("drift"),
        "instrument_validity": result.get("instrument_validity"),
    }, indent=1, default=str))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
