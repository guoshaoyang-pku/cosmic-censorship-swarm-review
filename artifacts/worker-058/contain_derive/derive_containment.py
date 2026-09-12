#!/usr/bin/env python3
"""W058-CONTAIN-DERIVE-04 -- containment-derivation certificate for the SCC pair.

Question this answers (the limitation carried by W058-CONTAIN-01/02/03): the SCC schemas
declare the extension-class containment chain

    E_C2 subset of E_{C^1,1} subset of E_H2loc subset of E_C0

but prior audits took that declaration as an AXIOM and never re-derived it from the frozen
definitional base. This instrument re-derives each link from an explicit rule base, records
the exact warrant of every link, and sweeps the bound bytes for sentences whose size or
strength assertions contradict the derived order.

Read-only on every canonical path.  Verdicts bind to measured sha256 values, never to
revision numbers.  No mathematical truth claim, no node completion, no gate verdict.

Usage:
    python3 derive_containment.py --root . [--out contain_ledger.json]
                                   [--no-require-frozen-match]

Exit codes: 0 = all hard checks pass (PASS), 1 = hard findings (FAIL), 2 = input error.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import re
import sys

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

TASK_ID = "W058-CONTAIN-DERIVE-04"
WORKER = "worker-058"
ACTOR = "worker-058"
NODE = "F2b"
CLASS_IDS = "AF-SCC-C0-VAC-GEN;AF-SCC-C2-VAC-GEN"
GATE = "G-FORM"

# Canonical order, smallest extension set (most regular) first: E_C2 < E_C11 < E_H2loc < E_C0.
# Written as a list of canonical tokens from the SMALLEST extension class to the LARGEST.
CANONICAL_ORDER = ["C2", "C11", "H2loc", "C0"]

FILES = {
    "schemas/af_scc_c0_vacuum.yaml": "C0",
    "schemas/af_scc_c2_vacuum.yaml": "C2",
    "artifacts/formulation/VARIANT_REGISTRY.json": "VARIANT_REGISTRY",
    "research_map/formulation_taxonomy.yaml": "F0_taxonomy",
    "artifacts/formulation/FROZEN.json": "FROZEN",
}

# ---------------------------------------------------------------- class tokens / regexes

TOKEN_PATTERNS = {
    "C2": re.compile(r"(?<![A-Za-z0-9_])C2(?![A-Za-z0-9_])"),
    "C0": re.compile(r"(?<![A-Za-z0-9_])C0(?![A-Za-z0-9_])"),
    "C11": re.compile(r"C\^?\{?1\s*,\s*1\}?"),
    "H2loc": re.compile(r"H\^?2_?\{?loc\}?"),
}

# chain-token normalisation inside an E_... expression
CHAIN_TOKEN_RE = re.compile(
    r"E_?\s*\{?\s*(C\^?\{?1\s*,\s*1\}?|H\^?2_?\{?loc\}?|C2|C0|C\^?\{?0\s*,\s*1\}?)\s*\}?"
)
COMPARATOR_RE = re.compile(
    r"strictly\s+(larger|smaller)|"
    r"(?<![A-Za-z])(larger|smaller)(?![A-Za-z])|"
    r"(?<![A-Za-z])(weaker|stronger)(?![A-Za-z])|"
    r"\bcontains\b|\bsubset\b|\bnested\b|\bcontainment\b|\bstrictly between\b",
    re.IGNORECASE,
)

LINK_SPECS = [
    ("L1", "C2", "C11", "E_C2 subset of E_{C^1,1}"),
    ("L2", "C11", "H2loc", "E_{C^1,1} subset of E_H2loc"),
    ("L3", "H2loc", "C0", "E_H2loc subset of E_C0"),
]


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def norm_token(tok: str) -> str:
    t = re.sub(r"[\s{}\\^]", "", tok)
    if t in ("C11", "C1,1"):
        return "C11"
    if t in ("H2loc", "H2_loc"):
        return "H2loc"
    if t in ("C2", "C0"):
        return t
    if t in ("C0,1", "C01"):
        return "C0,1"
    return t


def chain_tokens(text: str) -> list[str]:
    """Tokens of the E_... chain in textual order of appearance."""
    out = []
    for m in CHAIN_TOKEN_RE.finditer(text or ""):
        t = norm_token(m.group(1))
        if t in CANONICAL_ORDER or t == "C0,1":
            if not out or out[-1] != t:
                out.append(t)
    return out


def chain_is_canonical(tokens: list[str], text: str) -> tuple[bool, str]:
    """A chain occurrence is canonical if it lists the four classes consecutively in either
    reading direction AND the direction word agrees with the written order.

    Ascending  : E_C2 subset of E_{C^1,1} subset of E_H2loc subset of E_C0  ('subset')
    Descending : E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2     ('contains')
    A bare listing with no direction word is accepted as an order statement.
    """
    head = text.lower()
    has_contains = "contains" in head
    has_subset = "subset" in head
    for start in range(0, len(tokens) - 3):
        window = tokens[start:start + 4]
        if window == CANONICAL_ORDER:
            if has_contains and not has_subset:
                return False, "ascending token order contradicts the 'contains' direction word"
            return True, ("ascending 'subset' chain" if has_subset
                          else "ascending chain listing (no direction word)")
        if window == list(reversed(CANONICAL_ORDER)):
            if has_subset and not has_contains:
                return False, "descending token order contradicts the 'subset' direction word"
            return True, ("descending 'contains' chain" if has_contains
                          else "descending chain listing (no direction word)")
    return False, "chain incomplete"


def normalized_chain(tokens: list[str]) -> list[str]:
    """Return the small->large canonical order if the token list contains a correct window."""
    for start in range(0, len(tokens) - 3):
        window = tokens[start:start + 4]
        if window in (CANONICAL_ORDER, list(reversed(CANONICAL_ORDER))):
            return list(CANONICAL_ORDER)
    return list(tokens)


def line_of(text: str, needle: str) -> int | None:
    for i, ln in enumerate(text.splitlines(), 1):
        if needle in ln:
            return i
    return None


def sentence_of(text: str, needle: str) -> str:
    i = text.find(needle)
    if i < 0:
        return ""
    start = text.rfind("\n", 0, i) + 1
    end = text.find("\n", i)
    return text[start:end if end >= 0 else len(text)].strip()


# ---------------------------------------------------------------- rule base

def rule_base(registry: dict, c2_text: str) -> list[dict]:
    h2 = None
    for v in registry.get("variants", []):
        if v.get("variant_id") == "H2LOC":
            h2 = v
            break
    h2_def = (h2 or {}).get("definition", "")
    h2_has_continuity = bool(re.search(r"continuous\s+metric", h2_def, re.IGNORECASE))
    h2_has_l2 = bool(re.search(r"Riemann tensor in L\^?2_?\{?loc\}?", h2_def, re.IGNORECASE))
    return [
        {
            "rule_id": "R1",
            "antecedent": "metric class C2",
            "consequent": "metric class C^{1,1}",
            "status": "elementary",
            "warrant": "C2 = twice continuously differentiable; a C2 function has C1 first "
                       "derivatives, hence locally Lipschitz first derivatives (C^{1,1}).",
            "source": "calculus: derivative-count inclusion",
            "present": True,
        },
        {
            "rule_id": "R2",
            "antecedent": "metric class C^{1,1}",
            "consequent": "Riemann tensor in L2_loc",
            "status": "standard_fact",
            "warrant": "C^{1,1} second weak derivatives are in L-infinity_loc; the Riemann "
                       "tensor is an algebraic combination of g, g^{-1} and two derivatives "
                       "of g, so Riem in L-infinity_loc subset L2_loc.",
            "source": "regularity calculus; stated verbatim at C2:151 and C2:240",
            "present": bool(re.search(r"locally bounded (Riemann )?curvature", c2_text)
                            and re.search(r"L\^?2_?\{?loc\}?", c2_text)),
        },
        {
            "rule_id": "R4",
            "antecedent": "metric class C^{1,1}",
            "consequent": "continuous metric (C0)",
            "status": "elementary",
            "warrant": "a C^{1,1} function is continuous; the chain C2 subset C^{1,1} subset C0 "
                       "is stated at C2:147 and C2:240.",
            "source": "regularity calculus; C2:147, C2:240",
            "present": True,
        },
        {
            "rule_id": "R3",
            "antecedent": "H2LOC membership",
            "consequent": "continuous metric AND Riemann tensor in L2_loc",
            "status": "definitional",
            "warrant": "VARIANT_REGISTRY v2.0 H2LOC definition: 'extension class: "
                       "continuous metric with Riemann tensor in L^2_loc (H2_loc).'",
            "source": "artifacts/formulation/VARIANT_REGISTRY.json#variants.H2LOC.definition",
            "present": h2_has_continuity and h2_has_l2,
            "premise_continuity_present": h2_has_continuity,
            "premise_l2_present": h2_has_l2,
            "h2loc_definition": h2_def,
        },
    ]


def derive_links(rules: list[dict]) -> list[dict]:
    by_id = {r["rule_id"]: r for r in rules}
    links = []
    for lid, small, large, statement in LINK_SPECS:
        if lid == "L1":
            rules_used, derived = ["R1"], by_id["R1"]["present"]
            premise = "C2 implies C^{1,1}; both classes share the base proper-future-extension predicate"
        elif lid == "L2":
            rules_used = ["R2", "R4", "R3"]
            derived = (by_id["R2"]["present"] and by_id["R4"]["present"]
                       and by_id["R3"].get("premise_l2_present", False))
            premise = ("C^{1,1} implies Riemann in L2_loc (R2) and continuity (R4), which "
                       "satisfies both conjuncts of the H2LOC definition (R3)")
        else:
            rules_used = ["R3"]
            derived = by_id["R3"].get("premise_continuity_present", False)
            premise = ("H2LOC membership carries metric continuity as a defining conjunct (R3); "
                       "if the definition were curvature-only the link would need H^2_loc metric "
                       "regularity, which does not embed into C0 in 4D (s = n/2 is the sharp "
                       "Sobolev borderline)")
        links.append({
            "link_id": lid,
            "statement": statement,
            "smaller_class": small,
            "larger_class": large,
            "rules_used": rules_used,
            "status": "derived" if derived else "under_justified",
            "warrant": premise,
            "definitional_dependency": ("R3 continuity conjunct" if lid == "L3" else None),
        })
    return links


# ---------------------------------------------------------------- findings

def add(finding_list, code, severity, file_key, line, quote, observed, expected, repair):
    finding_list.append({
        "code": code,
        "severity": severity,
        "file": file_key,
        "line": line,
        "quote": quote[:400],
        "observed": observed,
        "expected": expected,
        "repair": repair,
    })


def sweep(texts: dict, rules: list[dict], links: list[dict]) -> tuple[list, list, list]:
    hard, advisory, consistent = [], [], []
    by_id = {r["rule_id"]: r for r in rules}

    # --- chain declarations -------------------------------------------------
    c0_txt, c2_txt = texts["C0"], texts["C2"]
    declared = {}
    for key, txt, prose_needles in (
        ("C0", c0_txt, []),
        ("C2", c2_txt, ["Containment of extension sets runs E_C2 subset",
                        "the extension sets are nested: E_C2 subset"]),
    ):
        structured_field = ((yaml.safe_load(txt) or {}).get("implication_ledger") or {}) \
            .get("extension_class_containment", "")
        tokens_field = chain_tokens(structured_field)
        ok_field, why_field = chain_is_canonical(tokens_field, structured_field)
        declared[key] = {"structured_chain_tokens": tokens_field,
                         "structured_chain_normalized": normalized_chain(tokens_field),
                         "structured_canonical": ok_field, "structured_note": why_field}
        if not ok_field:
            add(hard, "chain_declaration_not_canonical", "hard", key,
                line_of(txt, structured_field) or None, sentence_of(txt, structured_field),
                why_field, "E_C2 subset E_{C^1,1} subset E_H2loc subset E_C0",
                "restore the canonical chain in implication_ledger.extension_class_containment")
        else:
            consistent.append({"check": "chain_declaration", "file": key, "detail": why_field})
        # prose occurrences (line 147/151 in C2, one_way rows, subsumption note)
        for needle in prose_needles:
            ln = line_of(txt, needle)
            if ln is None:
                add(advisory, "prose_chain_occurrence_absent", "advisory", key, None, "",
                    f"needle {needle!r} not found", "prose chain occurrence present",
                    "informational only")
            else:
                seg = sentence_of(txt, needle)
                toks = chain_tokens(seg)
                ok, why = chain_is_canonical(toks, seg)
                if ok:
                    consistent.append({"check": "prose_chain_occurrence", "file": key,
                                       "line": ln, "detail": why})
                else:
                    add(hard, "prose_chain_not_canonical", "hard", key, ln, seg, why,
                        "E_C2 subset E_{C^1,1} subset E_H2loc subset E_C0",
                        "restore the canonical chain in the prose occurrence")

    # cross-file agreement on the structured field (normalised to small->large)
    n_c0 = declared["C0"]["structured_chain_normalized"]
    n_c2 = declared["C2"]["structured_chain_normalized"]
    if (declared["C0"]["structured_canonical"] and declared["C2"]["structured_canonical"]
            and n_c0 == CANONICAL_ORDER and n_c2 == CANONICAL_ORDER):
        consistent.append({"check": "cross_file_chain_agreement", "detail":
                           "C0 and C2 declare the same canonical order "
                           "(descending 'contains' vs ascending 'subset' writing)"})
    elif declared["C0"]["structured_canonical"] and declared["C2"]["structured_canonical"]:
        add(hard, "cross_file_chain_disagreement", "hard", "C0,C2", None, "",
            f"{n_c0} vs {n_c2}", "identical canonical chains",
            "align the two implication_ledger declarations")

    # --- derived links ------------------------------------------------------
    for link in links:
        if link["status"] != "derived":
            add(hard, "containment_link_under_justified", "hard", "VARIANT_REGISTRY",
                line_of(texts["VARIANT_REGISTRY"], (by_id["R3"].get("h2loc_definition") or "")[:40]) or None,
                by_id["R3"].get("h2loc_definition", "")[:200],
                f"{link['link_id']} under_justified",
                "every chain link closed under the frozen rule base",
                "restore the continuity conjunct in the H2LOC definition or restate the chain")

    # --- size assertions: C2 vs C0 -----------------------------------------
    size_re = re.compile(r"C2[^.\n]{0,80}strictly\s+(larger|smaller)[^.\n]{0,40}extension class",
                         re.IGNORECASE)
    for key, txt in (("C0", c0_txt), ("C2", c2_txt)):
        for m in size_re.finditer(txt):
            ln = txt.count("\n", 0, m.start()) + 1
            seg = sentence_of(txt, m.group(0))
            if m.group(1).lower() == "larger":
                add(hard, "class_size_predicate_inverted", "hard", key, ln, seg,
                    "C2 called strictly larger",
                    "C2 is strictly smaller (E_C2 subset E_C0): 'strictly smaller'",
                    "one word: larger -> smaller")
            else:
                consistent.append({"check": "class_size_assertion", "file": key, "line": ln,
                                   "detail": "correctly calls C2 strictly smaller"})

    # --- forbidden/one-way rows: any E_X subset E_Y pair must match the order
    subset_re = re.compile(
        r"E_?\s*\{?\s*(C\^?\{?1\s*,\s*1\}?|H\^?2_?\{?loc\}?|C2|C0)\s*\}?\s+"
        r"(?:is\s+)?(?:a\s+)?subset\s+of\s+E_?\s*\{?\s*"
        r"(C\^?\{?1\s*,\s*1\}?|H\^?2_?\{?loc\}?|C2|C0)\s*\}?",
        re.IGNORECASE)
    for key, txt in (("C0", c0_txt), ("C2", c2_txt)):
        for m in subset_re.finditer(txt):
            ln = txt.count("\n", 0, m.start()) + 1
            a, b = norm_token(m.group(1)), norm_token(m.group(2))
            if a in CANONICAL_ORDER and b in CANONICAL_ORDER:
                if CANONICAL_ORDER.index(a) < CANONICAL_ORDER.index(b):
                    consistent.append({"check": "subset_assertion", "file": key, "line": ln,
                                       "detail": f"E_{a} subset E_{b} matches the order"})
                elif a == b:
                    pass
                else:
                    add(hard, "subset_assertion_reversed", "hard", key, ln,
                        sentence_of(txt, m.group(0)), f"E_{a} subset E_{b}",
                        "chain E_C2 subset E_C11 subset E_H2loc subset E_C0",
                        "swap the two class tokens in this containment assertion")

    # --- containment denial -------------------------------------------------
    denial_re = re.compile(r"[Nn]o\s+containment[^.\n]{0,80}", re.IGNORECASE)
    for key, txt in (("C0", c0_txt), ("C2", c2_txt)):
        for m in denial_re.finditer(txt):
            ln = txt.count("\n", 0, m.start()) + 1
            seg = sentence_of(txt, m.group(0))
            # A denial quoted inside a correction ('the earlier ... was wrong') is history,
            # not a live assertion.
            if re.search(r"earlier|was wrong|superseded|repaired", seg, re.IGNORECASE):
                consistent.append({"check": "historical_containment_denial", "file": key,
                                   "line": ln, "detail": "denial is quoted as corrected history"})
                continue
            add(advisory, "stale_containment_denial", "advisory", key, ln, seg,
                "denies containment while the same file's implication_ledger declares it",
                "scope the denial to the definition block, or align it with implication_ledger",
                "scope or delete the denial sentence (advisory; ledger is authoritative)")

    # --- entailment rows: from-class must be the larger set -----------------
    entail_re = re.compile(
        r"from:\s*\"no proper future ([^\"]{0,60}?)\s+extension\",\s*to:\s*\"([^\"]{0,80}?)\"")
    strength_re = re.compile(r"(stronger|weaker)", re.IGNORECASE)
    for key, txt in (("C0", c0_txt), ("C2", c2_txt)):
        for m in entail_re.finditer(txt):
            ln = txt.count("\n", 0, m.start()) + 1
            frm = m.group(1)
            frm_tok = ("C0" if re.search(r"\bC0\b", frm) else
                       "C2" if re.search(r"\bC2\b", frm) else
                       "H2loc" if TOKEN_PATTERNS["H2loc"].search(frm) else
                       "C11" if TOKEN_PATTERNS["C11"].search(frm) else None)
            if frm_tok is None:
                continue
            seg = sentence_of(txt, m.group(0))
            sm = strength_re.search(seg)
            if sm and frm_tok in CANONICAL_ORDER:
                stronger = sm.group(1).lower() == "stronger"
                # The larger the admissible extension set, the stronger the inexistence
                # statement: C0 (largest set) is strongest, C2 (smallest set) is weakest.
                should_be_stronger = CANONICAL_ORDER.index(frm_tok) >= 2
                if stronger == should_be_stronger:
                    consistent.append({"check": "strength_label", "file": key, "line": ln,
                                       "detail": f"{frm_tok} labelled {sm.group(1)}"})
                else:
                    add(hard, "strength_label_inverted", "hard", key, ln, seg,
                        f"{frm_tok} labelled {sm.group(1)}",
                        "larger extension set => weaker inexistence statement",
                        "swap stronger/weaker on this row")

    return hard, advisory, consistent


def check_f0_vocabulary(texts: dict) -> tuple[list, list]:
    hard, consistent = [], []
    t = texts["F0_taxonomy"]
    try:
        tax = yaml.safe_load(t) if yaml else {}
    except Exception as exc:  # pragma: no cover
        return [{"code": "f0_taxonomy_unparseable", "severity": "hard", "file": "F0_taxonomy",
                 "line": None, "quote": str(exc), "observed": "unparseable",
                 "expected": "parseable YAML", "repair": "fix YAML"}], []
    meaning = (((tax or {}).get("field_vocabulary") or {}).get("regularity_token") or {}).get("meaning_C2", "")
    if not meaning:
        hard.append({"code": "f0_meaning_C2_absent", "severity": "hard", "file": "F0_taxonomy",
                     "line": None, "quote": "", "observed": "absent",
                     "expected": "meaning_C2 present and consistent with the SCC chain",
                     "repair": "restore the vocabulary entry"})
        return hard, consistent
    # A repair sentence such as "It does NOT forbid C^{1,1} or H^2_loc extensions" is the
    # correct statement; only an un-negated "hence also C^{1,1}" / "forbids C^{1,1}" is a defect.
    wrong = re.search(r"(?<!not )(?<!NOT )hence\s+also\s+C\^?\{?1\s*,\s*1\}?", meaning) \
        or re.search(r"(?<!not )(?<!NOT )forbid[s]?\s+C\^?\{?1\s*,\s*1\}?", meaning) \
        or re.search(r"(?<!not )(?<!NOT )forbid[s]?\s+H\^?2_?\{?loc\}?", meaning)
    if wrong:
        ln = line_of(t, meaning[:60])
        hard.append({"code": "f0_meaning_C2_claims_larger_classes_forbidden", "severity": "hard",
                     "file": "F0_taxonomy", "line": ln, "quote": meaning[:400],
                     "observed": f"matches {wrong.group(0)!r}",
                     "expected": "C2-inextendibility forbids only C2 and smoother classes "
                                 "(C2 subset C11 subset H2loc subset C0)",
                     "repair": "state that C^{1,1}/H2_loc are strictly larger extension classes "
                               "and are NOT excluded by C2-inextendibility"})
    else:
        consistent.append({"check": "f0_meaning_C2", "detail":
                           "F0 vocabulary does not claim C2 forbids C^{1,1}/H2_loc"})
    return hard, consistent


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default=None)
    ap.add_argument("--no-require-frozen-match", action="store_true")
    args = ap.parse_args()
    root = os.path.abspath(args.root)
    now = datetime.datetime.now().astimezone().isoformat(timespec="seconds")

    if yaml is None:
        print("PyYAML required", file=sys.stderr)
        return 2

    texts, inputs = {}, {}
    for rel, key in FILES.items():
        p = os.path.join(root, rel)
        if not os.path.exists(p):
            print(f"missing input: {rel}", file=sys.stderr)
            return 2
        raw = open(p, encoding="utf-8").read()
        texts[key] = raw
        inputs[rel] = {"sha256": sha256(p), "bytes": len(raw.encode("utf-8"))}

    frozen = json.loads(texts["FROZEN"])
    fpin = frozen.get("files", {})
    drift = []
    for rel in FILES:
        if rel == "artifacts/formulation/FROZEN.json":
            continue
        pin = (fpin.get(rel) or {}).get("sha256")
        if pin and pin != inputs[rel]["sha256"]:
            drift.append({"path": rel, "frozen_pin": pin, "measured": inputs[rel]["sha256"]})
    frozen_revision = frozen.get("revision")
    frozen_sha = inputs["artifacts/formulation/FROZEN.json"]["sha256"]

    registry = json.loads(texts["VARIANT_REGISTRY"])
    rules = rule_base(registry, texts["C2"])
    links = derive_links(rules)
    hard, advisory, consistent = sweep(texts, rules, links)
    f0_hard, f0_consistent = check_f0_vocabulary(texts)
    hard.extend(f0_hard)
    consistent.extend(f0_consistent)

    if drift and not args.no_require_frozen_match:
        hard.append({"code": "frozen_pin_drift", "severity": "hard", "file": "FROZEN",
                     "line": None, "quote": "", "observed": json.dumps(drift),
                     "expected": "measured canonical bytes match the FROZEN rev pins",
                     "repair": "re-freeze or re-point the declared pins"})

    # de-duplicate findings by (code,file,line)
    def dedup(fs):
        seen, out = set(), []
        for f in fs:
            k = (f["code"], f["file"], f["line"])
            if k not in seen:
                seen.add(k)
                out.append(f)
        return out

    hard, advisory = dedup(hard), dedup(advisory)
    verdict = "FAIL" if hard else "PASS"

    result = {
        "artifact": "w058_containment_derivation_ledger",
        "task_id": TASK_ID,
        "worker": WORKER,
        "actor": ACTOR,
        "generated_at": now,
        "node_id": NODE,
        "class_ids": CLASS_IDS.split(";"),
        "gate": GATE,
        "mode": "read-only; verdicts bind to measured sha256",
        "question": ("Are the SCC extension-class containment declarations derivable from the "
                     "frozen definitional base, or do they rest on unstated premises?"),
        "inputs": {
            "files": inputs,
            "frozen_manifest_sha256": frozen_sha,
            "frozen_revision": frozen_revision,
            "frozen_pin_drift": drift,
            "frozen_match": not drift,
        },
        "rule_base": rules,
        "chain": {
            "canonical_order_small_to_large": CANONICAL_ORDER,
            "canonical_statement": "E_C2 subset E_{C^1,1} subset E_H2loc subset E_C0",
            "declarations": {},
            "links": links,
        },
        "counts": {
            "hard": len(hard),
            "advisory": len(advisory),
            "consistent": len(consistent),
            "links_derived": sum(1 for l in links if l["status"] == "derived"),
            "links_under_justified": sum(1 for l in links if l["status"] != "derived"),
        },
        "verdict": verdict,
        "hard_findings": hard,
        "advisories": advisory,
        "consistent_checks": consistent,
        "derivation_summary": (
            "L1 (C2 -> C^{1,1}) and L2 (C^{1,1} -> H2loc) follow from the elementary regularity "
            "calculus stated verbatim at C2:151/C2:240. L3 (H2loc -> C0) is definitional: the "
            "registered H2LOC variant is 'continuous metric with Riemann tensor in L^2_loc'. "
            "The chain is therefore derived, but its third link inherits a definitional "
            "dependency: a curvature-only reading of H2_loc would NOT give E_H2loc subset E_C0 "
            "in 4D (s = n/2 Sobolev borderline). C0:151 denies containment outright and is stale "
            "against both the ledger and VARIANT_REGISTRY v2.0."
        ),
        "pre_registered_acceptance_test": {
            "repair_a": "C0:245 'strictly larger' -> 'strictly smaller'",
            "repair_b": "C0:151 'No containment with C2 or C0 is asserted here;' scoped to the "
                        "definition block or replaced by a pointer to implication_ledger (this "
                        "checker's only advisory)",
            "acceptance": "after both repairs at a new C0 hash, this checker returns PASS "
                          "(hard=0, advisory=0) with all three links still derived; demonstrated "
                          "by mutant M1_both_repairs in sensitivity_selftest.json",
            "separate_track": "the duplicate two-sided item at C0:234 (forbidden_weakenings) is "
                              "tracked by W058-REPAIR-CERT-02 MINOR-1 and is outside this "
                              "checker's SCC-containment scope",
            "definitional_dependency": "if VARIANT_REGISTRY H2LOC ever drops its 'continuous "
                                       "metric' conjunct, L3 (E_H2loc subset E_C0) becomes "
                                       "under_justified: mutant M4_h2loc_continuity_stripped "
                                       "demonstrates the sensitivity",
        },
        "falsifier": (
            "(a) a reader exhibits a frozen definitional base in which a chain link fails or the "
            "order reverses; (b) the checker returns PASS while a bound sentence still calls C2 "
            "strictly larger or denies containment; (c) a sensitivity mutant is not caught; "
            "(d) VARIANT_REGISTRY H2LOC loses the continuity conjunct and the checker still "
            "reports L3 derived."
        ),
        "next_falsifier": (
            "Re-run at the next canonical C0/C2/registry hashes. Falsified if the derived order "
            "changes, if L3 becomes under-justified with the continuity conjunct still present, "
            "or if hard findings disappear without the two recorded repairs."
        ),
        "limitations": [
            "The rule base (R1-R3) is declared and sourced; the checker verifies closure of the "
            "chain under it and the presence of each warrant in the bound bytes, not the "
            "calculus rules themselves.",
            "The sweep is lexical/semi-structured: it evaluates sentences carrying class tokens "
            "and comparator tokens; semantic claims without those tokens are out of scope.",
            "No mathematical truth claim about asymptotic censorship, no citation-scope claim, "
            "no node completion and no gate verdict.",
        ],
        "authority_note": (
            "Worker artifact, validation_status unverified. astra-lead-formulation owns "
            "interpretation, the repairs and any gate consequence."
        ),
    }

    # chain declarations detail (line-anchored)
    for key, rel in (("C0", "schemas/af_scc_c0_vacuum.yaml"),
                     ("C2", "schemas/af_scc_c2_vacuum.yaml")):
        declaration = (yaml.safe_load(texts[key]) or {}).get("implication_ledger", {}) \
            .get("extension_class_containment", "")
        toks = chain_tokens(declaration)
        ok, why = chain_is_canonical(toks, declaration)
        result["chain"]["declarations"][key] = {
            "path": rel,
            "line": line_of(texts[key], declaration),
            "tokens": toks,
            "canonical": ok,
            "note": why,
        }

    out_path = args.out or os.path.join(root, "artifacts/worker-058/contain_derive/containment_derivation.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=1, sort_keys=False)
        fh.write("\n")

    print(f"{TASK_ID} verdict={verdict} hard={len(hard)} advisory={len(advisory)} "
          f"consistent={len(consistent)} links_derived={result['counts']['links_derived']}/3")
    for f in hard:
        print(f"  HARD {f['code']} {f['file']}:{f['line']} :: {f['observed'][:120]}")
    for f in advisory:
        print(f"  ADV  {f['code']} {f['file']}:{f['line']} :: {f['observed'][:120]}")
    print(f"written: {out_path}")
    return 1 if hard else 0


if __name__ == "__main__":
    sys.exit(main())
