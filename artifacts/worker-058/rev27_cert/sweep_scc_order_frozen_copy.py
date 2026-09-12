#!/usr/bin/env python3
"""W058-REPAIR-CERT-02 -- independent full-text order/strength sweep of the SCC canonical pair.

Purpose
-------
1. Re-measure, with a fresh independent implementation, the recorded hard failure
   C0 implication_ledger.forbidden_transfers[0].reason ("C2 is a strictly larger
   extension class") at the live canonical hash.
2. Sweep the WHOLE document -- not only implication_ledger -- for class-size /
   statement-strength claims, including the regions W058-CONTAIN-01 explicitly did
   not sweep (must_not_conflate, conclusion.forbidden_weakenings/strengthenings,
   anti_scope, class_identity_variants). FORM-SEP-04's X2 scanner excludes
   anti_scope/variants by construction; this checker does not.
3. Pre-register a mechanical acceptance test for the pending repair.

Reference relations (parsed from the documents, then frozen here as the audit axiom;
see `reference` in the output JSON):
    E_C2  subset of  E_{C^1,1}  subset of  E_H2loc  subset of  E_C0
    E_DV (distributional-vacuum) subset of E_C0
    E_{two-sided} superset of E_future
Rule: larger extension set  <=>  stronger "no proper future extension" statement.
      entailment runs stronger -> weaker; forbidden transfer runs weaker -> stronger.

Read-only on the repository. Exit code: 0 = PASS (0 hard findings), 1 = FAIL,
2 = checker error. `--root` supports mutant trees (sensitivity self-test).
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
except Exception as exc:  # pragma: no cover
    print("checker error: pyyaml unavailable: %s" % exc, file=sys.stderr)
    sys.exit(2)

C0_PATH = "schemas/af_scc_c0_vacuum.yaml"
C2_PATH = "schemas/af_scc_c2_vacuum.yaml"
FROZEN_PATH = "artifacts/formulation/FROZEN.json"

# extension-class rank: larger rank = larger extension set = stronger inexistence statement
RANK = {
    "C2": 0.0,
    "C1": 0.5,
    "C^0,1": 0.7,
    "C^1,1": 1.0,
    "H2_loc": 2.0,
    "CH": 2.5,        # horizon-localized variant: subset of extensions -> weaker than C0
    "DV": 2.5,        # distributional-vacuum variant: subset of E_C0
    "C0": 3.0,
    "TWOSIDED": 4.0,  # two-sided: superset of future extensions -> strictly stronger
}
# pairs that neither document orders; comparisons across them are reported UNCHECKED
INCOMPARABLE = {
    frozenset(("DV", "H2_loc")),
    frozenset(("DV", "C^1,1")),
    frozenset(("DV", "C1")),
    frozenset(("DV", "C^0,1")),
    frozenset(("DV", "C2")),
    frozenset(("DV", "CH")),
    frozenset(("CH", "H2_loc")),
    frozenset(("CH", "C^1,1")),
    frozenset(("CH", "C2")),
    frozenset(("TWOSIDED", "H2_loc")),
    frozenset(("TWOSIDED", "C^1,1")),
    frozenset(("TWOSIDED", "C1")),
    frozenset(("TWOSIDED", "C0")),
    frozenset(("TWOSIDED", "DV")),
    frozenset(("TWOSIDED", "CH")),
}
CLS = (r"(?<![A-Za-z0-9])(?:distributional(?:-|\s+)vacuum(?:\s+C0)?|two-sided|"
       r"TWOSIDED|DV|CH|C\^?\{?1,1\}?|C\^?\{?0,1\}?|H2_?loc|H2LOC|C0|C1|C2)(?![A-Za-z0-9])")
VARIANT_TOKENS = ("H2_loc", "H2LOC", "two-sided", "distributional")

HARD_CODES = {
    "class_size_predicate_inverted",
    "strength_predicate_inverted",
    "containment_edge_inverted",
    "entailment_direction_inverted",
    "forbidden_transfer_direction_inverted",
    "chain_parse_failure",
    "chain_concordance_failure",
    "strength_bucket_mismatch",
}


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def canon(tok: str) -> str:
    t = (tok or "").strip().lower()
    t = t.replace("{", "").replace("}", "").replace("^", "").replace("_", " ").replace("-", " ")
    t = re.sub(r"\s+", " ", t)
    if t == "c0":
        return "C0"
    if t == "c1":
        return "C1"
    if t == "c2":
        return "C2"
    if t in ("c1,1", "c11"):
        return "C^1,1"
    if t in ("c0,1", "c01"):
        return "C^0,1"
    if t.startswith("h2"):
        return "H2_loc"
    if "distributional" in t:
        return "DV"
    if "two" in t:
        return "TWOSIDED"
    return tok


def norm_text(s: str) -> str:
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"distributional(?:-|\s+)vacuum\s+C0\s+(metric\s+)?extension", r"DV \1extension", s, flags=re.I)
    s = re.sub(r"C0\s+distributional(?:-|\s+)vacuum\s+(metric\s+)?extension", r"DV \1extension", s, flags=re.I)
    s = re.sub(r"distributional(?:-|\s+)vacuum\s+C0", "DV", s, flags=re.I)
    return s


def ordered(x, y):
    return None if frozenset((x, y)) in INCOMPARABLE else (RANK[x], RANK[y])


class DupLoader(yaml.SafeLoader):
    pass


DUPLICATES = []


def _construct_mapping(loader, node, deep=False):
    seen = {}
    for key_node, _ in node.value:
        try:
            key = loader.construct_object(key_node, deep=True)
        except Exception:
            continue
        if isinstance(key, (str, int, float, bool)) and key in seen:
            DUPLICATES.append({"key": str(key), "first_line": seen[key],
                               "again_line": key_node.start_mark.line + 1})
        elif isinstance(key, (str, int, float, bool)):
            seen[key] = key_node.start_mark.line + 1
    return yaml.SafeLoader.construct_mapping(loader, node, deep=deep)


DupLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping)


def walk_scalars(node, path=()):
    if isinstance(node, dict):
        for k, v in node.items():
            yield from walk_scalars(v, path + (str(k),))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from walk_scalars(v, path + ("[%d]" % i,))
    elif isinstance(node, str):
        yield (".".join(path), node)


def line_hint(raw_lines, text, start=1):
    frag = re.sub(r"\s+", " ", text.strip())[:48]
    frag2 = re.sub(r"\s+", " ", text.strip())[:24]
    for needle in (frag, frag2):
        if not needle:
            continue
        for i in range(start - 1, len(raw_lines)):
            if needle in re.sub(r"\s+", " ", raw_lines[i]):
                return i + 1
    return None


def clauses(text):
    t = norm_text(text)
    parts = re.split(r"(?<=[.;])\s+|\s+(?:but|so|hence|therefore)\s+", t)
    return [p for p in parts if p.strip()]


def compare(x, y, want_greater, *, code, path, ypath, line, quote, repair, observed):
    pair = ordered(x, y)
    f = {"rule": code, "class_id": x, "vs": y, "file": path, "yaml_path": ypath,
         "line": line, "quote": quote, "observed": observed, "repair": repair}
    if pair is None:
        f.update({"severity": "unchecked", "code": "unchecked_incomparable_pair"})
        return f
    rx, ry = pair
    ok = (rx > ry) if want_greater else (rx < ry)
    if ok:
        f.update({"severity": "ok", "code": "order_claim_consistent"})
    else:
        f.update({"severity": "hard", "code": code})
    return f


def check_scalar(ypath, text, file_key, default, raw_lines, findings):
    quote = norm_text(text)[:240]
    line = line_hint(raw_lines, text)
    for cl in clauses(text):
        # R1 -- class-size predicate: "X is a [strictly] larger/smaller extension class"
        for m in re.finditer(
                rf"(?P<x>{CLS})\s+(?:is|are)\s+(?:a\s+)?(?:strictly\s+)?"
                rf"(?P<c>larger|bigger|wider|smaller)\s+extension\s+class"
                rf"(?:\s+than\s+(?P<y>{CLS}))?", cl, re.I):
            x = canon(m.group("x"))
            y = canon(m.group("y")) if m.group("y") else default
            want_gt = m.group("c").lower() in ("larger", "bigger", "wider")
            findings.append(compare(
                x, y, want_gt, code="class_size_predicate_inverted", path=file_key,
                ypath=ypath, line=line, quote=quote,
                observed=m.group(0), repair="rewrite the antecedent to match the declared chain"))
        # R2 -- strength predicates
        pats = [
            (rf"(?P<x>{CLS})-inextendibility\s+is\s+(?:strictly\s+)?(?P<c>stronger|weaker)"
             rf"(?:\s+than\s+(?:the\s+)?(?P<y>{CLS}|this\s+(?:frozen\s+)?class))?", "inextendibility"),
            (rf"(?P<x>{CLS})\s+(?:result|statement)\s+is\s+(?:strictly\s+)?(?P<c>stronger|weaker)",
             "result"),
            (rf"(?P<x>{CLS})(?:\s+extension)?\s+is\s+a\s+(?:strictly\s+)?(?P<c>stronger|weaker)\s+statement",
             "statement"),
        ]
        for pat, kind in pats:
            for m in re.finditer(pat, cl, re.I):
                x = canon(m.group("x"))
                ym = m.groupdict().get("y")
                if ym and re.match(r"this\s", ym, re.I):
                    y = default
                elif ym:
                    y = canon(ym)
                else:
                    # no 'than Y': use the nearest other class token in the clause
                    others = [canon(t) for t in re.findall(CLS, cl, re.I)]
                    others = [t for t in others if t in RANK and t != x]
                    y = others[0] if others else default
                want_gt = m.group("c").lower() == "stronger"
                findings.append(compare(
                    x, y, want_gt, code="strength_predicate_inverted", path=file_key,
                    ypath=ypath, line=line, quote=quote, observed=m.group(0),
                    repair="flip the strength word or re-point the subject to the correct class"))
        # "(those are WEAKER statements)" -- pronoun subject only; an explicit
        # "<class>-inextendibility is the stronger statement" is handled by R2a/R2b above
        for m in re.finditer(r"(?P<c>stronger|weaker)\s+statements?\b", cl, re.I):
            head = cl[:m.start()]
            if not re.search(r"\b(those|these|they)\s+are\s+$", head, re.I):
                continue
            toks = {canon(t) for t in re.findall(CLS, cl, re.I)}
            toks = {t for t in toks if t in RANK}
            if len(toks) < 1:
                continue
            want_gt = m.group("c").lower() == "stronger"
            for x in sorted(toks):
                findings.append(compare(
                    x, default, want_gt, code="strength_predicate_inverted", path=file_key,
                    ypath=ypath, line=line, quote=quote, observed=m.group(0),
                    repair="move the item to the correctly-labelled strength bucket"))
        # R2d -- variant vs parent class in class_identity_variants
        for m in re.finditer(r"strictly\s+(?P<c>stronger|weaker)\s+than\s+this\s+(?:frozen\s+)?class",
                             cl, re.I):
            subject = None
            for tok in re.findall(CLS, cl[:m.start()], re.I):
                subject = canon(tok)
            if subject is None:
                mm = re.search(r"variant\s+(?P<v>[A-Za-z0-9_]+)", cl)
                subject = {"CH": "CH"}.get(mm.group("v"), None) if mm else None
            if subject is None and "variant" in ypath:
                subject = "CH"
            if subject is None:
                continue
            want_gt = m.group("c").lower() == "stronger"
            findings.append(compare(
                subject, default, want_gt, code="strength_predicate_inverted", path=file_key,
                ypath=ypath, line=line, quote=quote, observed=m.group(0),
                repair="state the variant strength relative to its parent class correctly"))
        # R3 -- containment edges, overlapping lookahead covers 'A contains B contains C'
        for m in re.finditer(
                rf"(?=(E_?\(?(?P<x>{CLS})\)?\s*"
                rf"(?P<op>⊂|⊆|⊃|⊇|subset\s+of|is\s+a\s+subset\s+of|superset\s+of|contains|contained\s+in)\s*"
                rf"E_?\(?(?P<y>{CLS})\)?))", cl, re.I):
            x, y = canon(m.group("x")), canon(m.group("y"))
            op = m.group("op").lower()
            subset = ("subset" in op) or ("contained" in op) or op in ("⊂", "⊆")
            if not subset and op in ("⊃", "⊇"):
                findings.append(compare(
                    y, x, True, code="containment_edge_inverted", path=file_key,
                    ypath=ypath, line=line, quote=quote, observed=m.group(0),
                    repair="write the edge in the declared direction"))
                continue
            findings.append(compare(
                x, y, not subset, code="containment_edge_inverted", path=file_key,
                ypath=ypath, line=line, quote=quote, observed=m.group(0),
                repair="write the edge in the declared direction"))
        # "every X extension is a Y extension" == subset
        for m in re.finditer(
                rf"every\s+(?P<x>{CLS})\s+extension\s+is\s+an?\s+(?P<y>{CLS})\s+extension",
                cl, re.I):
            x, y = canon(m.group("x")), canon(m.group("y"))
            findings.append(compare(
                x, y, False, code="containment_edge_inverted", path=file_key,
                ypath=ypath, line=line, quote=quote, observed=m.group(0),
                repair="write the edge in the declared direction"))
        # R7 (advisory) -- negation of a containment the ledger asserts
        if re.search(r"\bno\s+(?:proper\s+)?containment\b|\bnot\s+contained\b", cl, re.I):
            toks = sorted({canon(t) for t in re.findall(CLS, cl, re.I)} & set(RANK))
            if len(toks) >= 2 and any(ordered(a, b) is not None
                                      for i, a in enumerate(toks) for b in toks[i + 1:]):
                findings.append({
                    "rule": "denial_of_asserted_containment", "severity": "advisory",
                    "code": "denial_tension_with_ledger", "file": file_key, "yaml_path": ypath,
                    "line": line, "quote": quote, "observed": cl[:200], "class_id": ",".join(toks),
                    "repair": "scope the denial to the definition block or align it with implication_ledger"})


def check_structured(doc, file_key, default, findings):
    ledger = (doc or {}).get("implication_ledger") or {}
    for i, row in enumerate(ledger.get("one_way_entailments") or []):
        if not isinstance(row, dict):
            continue
        frm, to = parse_no_ext(row.get("from")), parse_no_ext(row.get("to"))
        if not frm or not to:
            continue
        f = compare(frm, to, True, code="entailment_direction_inverted", path=file_key,
                    ypath="implication_ledger.one_way_entailments[%d]" % i, line=None,
                    quote=norm_text(json.dumps(row))[:240],
                    observed="%s entails %s" % (row.get("from"), row.get("to")),
                    repair="entailment must run from the larger extension set to the smaller")
        findings.append(f)
    for i, row in enumerate(ledger.get("forbidden_transfers") or []):
        if not isinstance(row, dict):
            continue
        frm = parse_no_ext(row.get("from")) or parse_classid(row.get("from"))
        to = parse_no_ext(row.get("to")) or parse_classid(row.get("to")) or (
            default if "this class" in str(row.get("to")) else None)
        if not frm or not to:
            continue
        f = compare(frm, to, False, code="forbidden_transfer_direction_inverted", path=file_key,
                    ypath="implication_ledger.forbidden_transfers[%d]" % i, line=None,
                    quote=norm_text(json.dumps(row))[:240],
                    observed="%s =/=> %s" % (row.get("from"), row.get("to")),
                    repair="forbidden transfer must run from the smaller extension set to the larger")
        findings.append(f)
    # R6 -- chain parse + monotonicity
    chain = parse_chain(ledger.get("extension_class_containment") or "")
    if not chain:
        findings.append({"rule": "chain_parse", "severity": "hard", "code": "chain_parse_failure",
                         "file": file_key, "class_id": default,
                         "yaml_path": "implication_ledger.extension_class_containment",
                         "line": None, "quote": str(ledger.get("extension_class_containment"))[:200],
                         "observed": "no ordered class chain parsed",
                         "repair": "restore an explicit E_X subset/contains E_Y chain"})
    else:
        for a, b in zip(chain, chain[1:]):
            f = compare(a, b, False, code="containment_edge_inverted", path=file_key,
                        ypath="implication_ledger.extension_class_containment", line=None,
                        quote="chain: " + " -> ".join(chain),
                        observed="%s precedes %s" % (a, b),
                        repair="chain must be monotone in extension-set size")
            if f["severity"] == "hard":
                findings.append(f)
        findings.append({"rule": "chain_parse", "severity": "ok",
                         "code": "chain_parsed", "file": file_key,
                         "yaml_path": "implication_ledger.extension_class_containment",
                         "line": None, "quote": "chain: " + " -> ".join(chain),
                         "observed": "smallest-to-largest order parsed", "class_id": ",".join(chain)})
    return chain


def parse_no_ext(s):
    if not isinstance(s, str):
        return None
    m = re.search(rf"no\s+proper\s+future\s+({CLS}(?:\s+metric)?)\s+extension", norm_text(s), re.I)
    if not m:
        return None
    return canon(m.group(1).replace("metric", "").strip())


def parse_classid(s):
    if not isinstance(s, str):
        return None
    m = re.search(r"(AF-[A-Z0-9-]+)", s)
    if m:
        return None if "WCC" in m.group(1) else None
    return None


def parse_chain(s):
    s = norm_text(s)
    s = re.split(r"[;(:]", s)[0]
    toks = [canon(t) for t in re.findall(CLS, s, re.I)]
    toks = [t for t in toks if t in RANK]
    ops = re.findall(r"⊂|⊆|⊃|⊇|subset\s+of|superset\s+of|contains|contained\s+in", s, re.I)
    if len(toks) < 2:
        return []
    # orient: if first operator is a 'contains' family, the written order is largest-first
    largest_first = bool(ops) and bool(re.match(r"⊃|⊇|superset|contains", ops[0], re.I))
    chain = list(reversed(toks)) if largest_first else list(toks)
    # canonical orientation: smallest extension set first
    ranks = [RANK[t] for t in chain]
    if ranks != sorted(ranks):
        return []
    return chain


def check_direction_buckets(doc, file_key, default, findings, raw_lines=None):
    concl = (doc or {}).get("conclusion") or {}
    for bucket, expect_stronger in (("forbidden_weakenings", False),
                                    ("forbidden_strengthenings", True)):
        items = concl.get(bucket) or []
        for i, item in enumerate(items):
            if not isinstance(item, str):
                continue
            if "two-sided" not in item.lower():
                continue
            if re.search(r"stronger|weaker|mislabell?ed|repaired|not\s+strengthenings", item, re.I):
                continue  # item states its own strength or is meta-commentary
            bad = (not expect_stronger)  # two-sided is strictly stronger than the future class
            f = {"rule": "direction_bucket", "file": file_key,
                 "yaml_path": "conclusion.%s[%d]" % (bucket, i),
                 "line": line_hint(raw_lines or [], item),
                 "quote": norm_text(item), "class_id": "TWOSIDED",
                 "reported_severity": "minor labelling (R2-10)",
                 "observed": "'two-sided' item in %s" % bucket,
                 "repair": ("move the item to forbidden_strengthenings (two-sided is strictly "
                            "stronger than the future-only class)")}
            if bad:
                f.update({"severity": "hard", "code": "strength_bucket_mismatch"})
            else:
                f.update({"severity": "ok", "code": "strength_bucket_consistent"})
            findings.append(f)


def check_identity(doc, file_key, findings):
    variant_claims, different_claims = set(), set()
    for ypath, text in walk_scalars(doc):
        t = norm_text(text)
        toks = {canon(x) for x in re.findall(CLS, t, re.I)}
        low = t.lower()
        if "variant" in low and re.search(r"not\s+a\s+separate\s+class\s+id|variant\s+of\s+(?:this|the)\s+", low):
            for tok in toks:
                if tok in ("H2_loc", "DV", "TWOSIDED", "CH"):
                    variant_claims.add(tok)
        if re.search(r"different\s+class|separate\s+tokens\s+and\s+nodes", low):
            for tok in toks:
                if tok in ("H2_loc", "DV", "TWOSIDED", "CH"):
                    different_claims.add(tok)
    for tok in sorted(variant_claims & different_claims):
        findings.append({
            "rule": "identity_tension", "severity": "advisory",
            "code": "variant_class_identity_tension", "file": file_key,
            "yaml_path": "(whole file)", "line": None, "class_id": tok,
            "quote": "%s both 'DIFFERENT class' and 'VARIANT ... not a separate class id'" % tok,
            "observed": "VARIANT_REGISTRY 2.0 registers variants by parent_class+variant_id and has no node field",
            "repair": "say 'distinct extension predicate / registered variant', not 'separate nodes'"})


def run(root: str, mutant: bool):
    sys.modules[__name__].DUPLICATES = []
    files = {"C0": os.path.join(root, C0_PATH), "C2": os.path.join(root, C2_PATH)}
    raw, docs, hashes = {}, {}, {}
    for key, p in files.items():
        with open(p, "r", encoding="utf-8") as fh:
            raw[key] = fh.read().splitlines()
        hashes[key] = sha256_file(p)
        docs[key] = yaml.load("\n".join(raw[key]), Loader=DupLoader)
    frozen = {}
    fpath = os.path.join(root, FROZEN_PATH)
    if os.path.exists(fpath):
        frozen = (json.load(open(fpath)) or {}).get("files") or {}
    default = {"C0": "C0", "C2": "C2"}
    findings = []
    chains = {}
    for key in ("C0", "C2"):
        for ypath, text in walk_scalars(docs[key]):
            check_scalar(ypath, text, key, default[key], raw[key], findings)
        chains[key] = check_structured(docs[key], key, default[key], findings)
        check_direction_buckets(docs[key], key, default[key], findings, raw[key])
        check_identity(docs[key], key, findings)
    if chains["C0"] and chains["C2"] and chains["C0"] != chains["C2"]:
        findings.append({"rule": "chain_concordance", "severity": "hard",
                         "code": "chain_concordance_failure", "file": "C0+C2",
                         "class_id": "AF-SCC-C0-VAC-GEN;AF-SCC-C2-VAC-GEN",
                         "yaml_path": "implication_ledger.extension_class_containment",
                         "line": None,
                         "quote": "C0 %s vs C2 %s" % (" -> ".join(chains["C0"]), " -> ".join(chains["C2"])),
                         "observed": "the two SCC files declare different orders",
                         "repair": "reconcile the two containment declarations"})
    hard = [f for f in findings if f["severity"] == "hard"]
    advisory = [f for f in findings if f["severity"] == "advisory"]
    checked = [f for f in findings if f["severity"] == "ok"]
    binding = {}
    for key, p in files.items():
        pin = (frozen.get(C0_PATH if key == "C0" else C2_PATH) or {}).get("sha256")
        binding[key] = {"path": C0_PATH if key == "C0" else C2_PATH,
                        "measured_sha256": hashes[key], "frozen_sha256": pin,
                        "frozen_match": pin == hashes[key]}
    result = {
        "artifact": "W058-REPAIR-CERT-02 full-text SCC order/strength sweep",
        "worker": "worker-058",
        "actor": "deepseek-flash-058",
        "generated_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "task_id": "W058-REPAIR-CERT-02",
        "node_id": "F2b",
        "class_ids": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"],
        "gate": "G-FORM",
        "mode": "MUTANT" if mutant else "CANONICAL",
        "scope": {
            "sweeps": ["whole YAML scalar content of both SCC schemas",
                       "implication_ledger structured rows",
                       "conclusion.forbidden_weakenings/forbidden_strengthenings",
                       "anti_scope, class_identity_variants, must_not_conflate"],
            "does_not_audit": ["physical truth", "citation scope", "mathematical correctness of definitions",
                               "genericity transfer matrix", "C0/C2 class-merge regex (FORM-SEP-04 owns it)"],
            "read_only": True, "claims_no_completion": True,
            "interpretation_owner": "astra-lead-formulation",
        },
        "inputs": {"files": binding, "frozen_manifest": FROZEN_PATH},
        "reference": {
            "source": "implication_ledger.extension_class_containment (both SCC files)",
            "rank_smallest_extension_set_first": RANK,
            "rule": "larger extension set <=> stronger inexistence statement; entailment runs stronger -> weaker",
            "chain_C0": chains.get("C0"), "chain_C2": chains.get("C2"),
        },
        "yaml_duplicate_keys": DUPLICATES,
        "counts": {"hard": len(hard), "advisory": len(advisory), "consistent": len(checked),
                   "total_claims_evaluated": len(findings)},
        "verdict": "FAIL" if hard else "PASS",
        "hard_findings": hard,
        "advisories": advisory,
        "consistent_claims": checked,
        "repair_acceptance_test": {
            "status": "PRE_REGISTERED",
            "procedure": ("re-run this checker after the lead re-freezes C0; PASS iff hard == 0 "
                          "at the new hash and the two advisories are either unchanged or repaired"),
            "required_repairs": [
                {"id": "HF-1", "yaml_path": "implication_ledger.forbidden_transfers[0].reason",
                 "op": "'strictly larger extension class' -> 'strictly smaller extension class'",
                 "class_id": "AF-SCC-C0-VAC-GEN"},
                {"id": "MINOR-1 (R2-10 status refresh)",
                 "yaml_path": "conclusion.forbidden_weakenings (two-sided item)",
                 "op": "move the two-sided item to conclusion.forbidden_strengthenings",
                 "class_id": "AF-SCC-C0-VAC-GEN"},
            ],
            "evidence": "sensitivity self-test mutants M1 (both repairs) / M2-M4, M6 (planted defects)",
        },
        "falsifier": ("A reader exhibits an order/strength claim this sweep accepts that contradicts the "
                      "declared chain, or shows that a reported hard finding is not present in the bound "
                      "bytes, or shows the chain axiom itself is mis-derived from the definitions."),
        "next_falsifier": ("Re-run at the next canonical C0 hash. Falsified if PASS at 1bb78ce9 (the "
                           "defect must still be visible), or FAIL after both repairs at the new hash "
                           "(repair insufficiency or a new defect)."),
        "authority_note": ("Worker claims no node completion and no gate verdict; lead-formulation owns "
                           "the repair and any gate consequence."),
    }
    return result, (0 if not hard else 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out")
    ap.add_argument("--mutant", action="store_true")
    args = ap.parse_args()
    try:
        result, rc = run(args.root, args.mutant)
    except FileNotFoundError as exc:
        print("checker error: %s" % exc, file=sys.stderr)
        return 2
    payload = json.dumps(result, indent=1, sort_keys=False)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(payload + "\n")
    print("%s hard=%d advisory=%d consistent=%d" % (
        result["verdict"], result["counts"]["hard"], result["counts"]["advisory"],
        result["counts"]["consistent"]))
    for f in result["hard_findings"]:
        print("  HARD %-34s %s %s:%s" % (f["code"], f.get("class_id", "-"), f["file"], f.get("line")))
    for f in result["advisories"]:
        print("  ADVS %-34s %s %s" % (f["code"], f.get("class_id", "-"), f["file"]))
    return rc


if __name__ == "__main__":
    sys.exit(main())
