#!/usr/bin/env python3
"""Class-relative containment/entailment-direction lint for F1/F2a/F2b schemas.

STATUS: proposal by worker-023 (task W023-F2B-DIR-GUARD-01). Non-canonical. It does not
modify any frozen instrument, schema, taxonomy, FROZEN.json or map file; it only reads a
schema document and reports whether the direction claims written in it agree with the
document's own declared entailment graph and declared extension-set nesting.

WHY: the canonical structural gate (`artifacts/formulation/tools/check_class_schema.py`,
FROZEN rev29 pin `000e09e46b2f`) certifies that `regularity.must_not_conflate` is present
and non-empty (R06), but not that its sentences agree with the same file's
`implication_ledger`. Measured (worker-023 W023-F2B-DIR-REVIEW-01, corroborated by
worker-080 W080-F2B-REPAIR-H2E-01): a repair candidate can assert the reverse entailment
inside the C0 file and still pass the canonical gate. This module is the missing
class-relative predicate.

SEMANTICS (document-internal only, no physics):
  * an edge  X -> Y  in `implication_ledger.one_way_entailments` (relation `entails`)
    means "no proper future X extension" entails "no proper future Y extension", i.e.
    E_Y subset of E_X;
  * `extension_class_containment` declares the nesting of the extension sets directly
    ("E_C0 contains E_H2loc contains ..." / "E_C2 subset of E_H2loc subset of ...");
  * a sentence of the form "<X>-inextendibility ENTAILS this class's conclusion" requires
    the edge X -> own; the reverse wording requires own -> X; "<X> => <Y>" requires X -> Y;
  * a required edge whose reverse is declared is a direction INVERSION (hard);
  * a required edge absent in both directions is UNSUPPORTED (warning; the label may not
    be in this document's graph);
  * a sentence under an explicit negation ("it is NOT the case that ...") is a MENTION,
    not a claim, and is reported as NEUTRAL;
  * text that matches no form is UNCLASSIFIED: the lint does not pretend to certify it.

LIMITS (stated, not hidden): regex/lexical recognition, English forms only; it cannot
decide whether the mathematics is right, whether an unclassified sentence is a
conflation, or whether a citation supports a claim. Adding this predicate to the
canonical gate changes the instrument hash and voids the current FROZEN rev29 pin, so
adoption is lead-formulation + controller business, not this worker's.

CLI: see check_containment_direction.py.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

# forms recognised in prose.  The token capture is deliberately broad and normalised below.
_TOK = r"(?P<x>[A-Za-z0-9^{},_]+?)-inextendibility"
_TOK_Y = r"(?P<y>C0|C2|H2_?loc|H2loc|C\^?\{?1,1\}?)"
_FORM_A = re.compile(_TOK + r"\s+(?P<v>ENTAILS|ENTAIL|entails|entail)\s+this class'?s conclusion")
_FORM_B = re.compile(
    r"this class'?s conclusion(?:\s*\((?P<own>[^)]*)\))?(?P<bridge>[^.\n]{0,60}?)"
    r"(?P<v>ENTAILS|ENTAIL|entails|entail)\s+" + _TOK)
_FORM_C = re.compile(_TOK + r"\s+(?P<v>ENTAILS|ENTAIL|entails|entail)\s+"
                     r"(?:the\s+)?" + _TOK_Y + r"(?:'s)?\s+(?:sibling'?s\s+)?conclusion")
_FORM_D = re.compile(r"(?P<x>C0|C2|H2_?loc|H2loc|C\^?\{?1,1\}?)\s*(?:=>|->)\s*"
                     r"(?P<y>C0|C2|H2_?loc|H2loc|C\^?\{?1,1\}?)")
# an arrow is only a *containment* claim when its chain is introduced as one; this keeps
# regularity chains such as "(C2 => C^1,1 => Riemann in L^inf)" out of the lint.
_ARROW_CTX = re.compile(r"(implication|direction|entail|runs|no\s+proper\s+future|inextendib)",
                        re.I)
_NEG_BEFORE = re.compile(r"\b(not|never|cannot|can't|does\s+not|doesn't|fails?\s+to|"
                         r"no\s+longer|nor|rather\s+than)\b", re.I)
_NEG_AFTER = re.compile(r"\b(not\s+this\s+class|does\s+not\s+hold|is\s+not\s+entailed|"
                        r"is\s+false|fails?)\b", re.I)
_ENT_LABEL = re.compile(r"no\s+proper\s+future\s+(.+?)(?:\s+metric)?\s+extension")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p) -> str:
    return sha256_bytes(Path(p).read_bytes())


def norm_token(s: str) -> str:
    """E_{C^1,1} / H2loc / C0 -> C^1,1 / H2_loc / C0 (comparison key)."""
    t = str(s).strip().strip("{}").replace("E_", "").strip()
    t = t.replace("H2loc", "H2_loc").replace("H2_loc", "H2_loc")
    t = re.sub(r"\s+", "", t)
    return t


def load_document(path):
    """Return (doc, sha256hex); raises ValueError with a machine-readable reason."""
    p = Path(path)
    b = p.read_bytes()
    if yaml is None:
        raise ValueError("PyYAML required")
    try:
        d = yaml.safe_load(b.decode("utf-8"))
    except Exception as e:  # noqa: BLE001
        raise ValueError(f"yaml_parse_error: {e}") from e
    if not isinstance(d, dict):
        raise ValueError("not_a_mapping")
    return d, sha256_bytes(b)


def graph_labels(doc) -> dict:
    """token -> full label, harvested from the document's own one_way_entailments."""
    labels = {}
    il = doc.get("implication_ledger") or {}
    for row in il.get("one_way_entailments") or []:
        for side in ("from", "to"):
            lab = str(row.get(side, ""))
            m = _ENT_LABEL.search(lab)
            if m:
                lab = lab.strip()
                labels.setdefault(norm_token(m.group(1)), lab)
    return labels


def own_token(doc) -> str | None:
    reg = doc.get("regularity") or {}
    tok = reg.get("extension_regularity")
    if tok:
        return norm_token(tok)
    cid = str(doc.get("class_id", ""))
    m = re.match(r"AF-(?:WCC|SCC)-([A-Za-z0-9^{},_]+)-", cid)
    return norm_token(m.group(1)) if m else None


def edges(doc) -> set:
    il = doc.get("implication_ledger") or {}
    out = set()
    for row in il.get("one_way_entailments") or []:
        rel = row.get("relation", "entails")
        if rel not in (None, "entails"):
            continue
        out.add((str(row.get("from", "")).strip(), str(row.get("to", "")).strip()))
    return out


def closure(edgeset) -> set:
    cl = set(edgeset)
    changed = True
    while changed:
        changed = False
        for a, b in list(cl):
            for c, d in list(cl):
                if b == c and (a, d) not in cl:
                    cl.add((a, d))
                    changed = True
    return cl


def subset_pairs(doc) -> set:
    """Declared extension-set nesting as (smaller, larger) token pairs, transitively closed."""
    s = str((doc.get("implication_ledger") or {}).get("extension_class_containment") or "")
    pairs = set()
    # tokenise: E_<name> and the relation words between them, so chains work.
    toks = [(m.start(), m.group(1)) for m in re.finditer(r"E_(\{[^}]+\}|[A-Za-z0-9^,]+)", s)]
    rels = [(m.start(), m.group(1)) for m in re.finditer(r"(contains|subset\s+of)", s, re.I)]
    for rpos, word in rels:
        before = [t for t in toks if t[0] < rpos]
        after = [t for t in toks if t[0] > rpos]
        if not before or not after:
            continue
        a = norm_token(before[-1][1])
        b = norm_token(after[0][1])
        if word.lower().startswith("contains"):
            pairs.add((b, a))  # E_b subset of E_a
        else:
            pairs.add((a, b))
    # transitive closure of a subset relation
    changed = True
    while changed:
        changed = False
        for a, b in list(pairs):
            for c, d in list(pairs):
                if b == c and (a, d) not in pairs:
                    pairs.add((a, d))
                    changed = True
    return pairs


def _slot_strings(doc):
    """(slot_path, text) pairs that carry direction-bearing prose in a class schema."""
    out = []
    reg = doc.get("regularity") or {}
    for i, s in enumerate(reg.get("must_not_conflate") or []):
        out.append((f"regularity.must_not_conflate[{i}]", str(s)))
    il = doc.get("implication_ledger") or {}
    for i, row in enumerate(il.get("forbidden_transfers") or []):
        if isinstance(row, dict) and row.get("reason"):
            out.append((f"implication_ledger.forbidden_transfers[{i}].reason", str(row["reason"])))
    for i, row in enumerate(il.get("forbidden_weakenings") or []):
        if isinstance(row, dict) and row.get("reason"):
            out.append((f"implication_ledger.forbidden_weakenings[{i}].reason", str(row["reason"])))
    if il.get("subsumption_note"):
        out.append(("implication_ledger.subsumption_note", str(il["subsumption_note"])))
    return out


def scan_document(doc) -> dict:
    """Return the direction report for one parsed schema document."""
    own = own_token(doc)
    labels = graph_labels(doc)
    own_label = labels.get(own)
    cl = closure(edges(doc))
    subs = subset_pairs(doc)
    applicable = own is not None and own_label is not None and ("SCC" in str(doc.get("class_id", "")))
    report = {
        "class_id": doc.get("class_id"),
        "own_token": own,
        "own_label": own_label,
        "applicable": applicable,
        "declared_edges": sorted(f"{a} => {b}" for a, b in cl if a != b),
        "declared_subset_pairs": sorted(f"{a} subset of {b}" for a, b in subs if a != b),
        "claims": [],
        "unclassified_strings": [],
        "inverted_count": 0,
        "unsupported_count": 0,
    }
    if not applicable:
        return report

    default_label = lambda t: labels.get(t) or f"no proper future {t} extension"  # noqa: E731

    def judge(slot, text, form, x, y, excerpt):
        xl, yl = default_label(x), default_label(y)
        rec = {"slot": slot, "form": form, "required_edge": f"{xl} => {yl}",
               "excerpt": excerpt, "verdict": None, "basis": []}
        if norm_token(x) == norm_token(y):
            rec["verdict"], rec["basis"] = "neutral", ["same token on both sides"]
        elif (xl, yl) in cl:
            rec["verdict"], rec["basis"] = "consistent", ["required edge declared"]
        elif (yl, xl) in cl:
            rec["verdict"], rec["basis"] = "inverted", ["reverse edge declared"]
        elif (norm_token(y), norm_token(x)) in subs:
            rec["verdict"], rec["basis"] = "inverted", ["containment nesting declares the reverse"]
        elif (norm_token(x), norm_token(y)) in subs:
            rec["verdict"], rec["basis"] = "consistent", ["containment nesting supports the edge"]
        else:
            rec["verdict"] = "unsupported"
            rec["basis"] = ["required edge not found in either direction"]
        return rec

    for slot, text in _slot_strings(doc):
        hits = []
        for m in _FORM_A.finditer(text):
            if _NEG_BEFORE.search(text[max(0, m.start() - 60):m.start()]) or \
               _NEG_AFTER.search(text[m.end():m.end() + 40]):
                hits.append(("A", m, "neutral"))
            else:
                hits.append(("A", m, None))
        for m in _FORM_B.finditer(text):
            if _NEG_BEFORE.search(text[max(0, m.start() - 60):m.start()]):
                hits.append(("B", m, "neutral"))
            else:
                hits.append(("B", m, None))
        for m in _FORM_C.finditer(text):
            if _NEG_AFTER.search(text[m.end():m.end() + 40]):
                hits.append(("C", m, "neutral"))
            else:
                hits.append(("C", m, None))
        dms = list(_FORM_D.finditer(text))
        i = 0
        while i < len(dms):
            chain = [dms[i]]
            while i + 1 < len(dms):
                gap = text[dms[i].end():dms[i + 1].start()]
                if gap.strip() == "" and norm_token(dms[i].group("y")) == norm_token(dms[i + 1].group("x")):
                    chain.append(dms[i + 1])
                    i += 1
                else:
                    break
            if _ARROW_CTX.search(text[max(0, chain[0].start() - 45):chain[0].start()]):
                for m in chain:
                    hits.append(("D", m, None))
            i += 1
        if not hits:
            if re.search(r"inextendib", text, re.I):
                report["unclassified_strings"].append(
                    {"slot": slot, "excerpt": text[:160], "text": text})
            continue
        seen = set()
        for form, m, forced in hits:
            key = (form, m.start(), m.end())
            if key in seen:
                continue
            seen.add(key)
            if form == "B":
                x2, y2 = own, norm_token(m.group("x"))
            elif form in ("C", "D"):
                x2, y2 = norm_token(m.group("x")), norm_token(m.group("y"))
            else:  # form A
                x2, y2 = norm_token(m.group("x")), own
            excerpt = text[max(0, m.start() - 20):m.end() + 20].replace("\n", " ")
            if forced == "neutral":
                rec = {"slot": slot, "form": form, "required_edge": None, "excerpt": excerpt,
                       "verdict": "neutral", "basis": ["explicit negation/mention guard"]}
            else:
                rec = judge(slot, text, form, x2, y2, excerpt)
            if rec["verdict"] == "inverted":
                report["inverted_count"] += 1
            elif rec["verdict"] == "unsupported":
                report["unsupported_count"] += 1
            report["claims"].append(rec)
    return report


def scan_path(path, expect_sha256: str | None = None) -> dict:
    doc, sha = load_document(path)
    rep = scan_document(doc)
    rep["path"] = str(path)
    rep["sha256"] = sha
    rep["expect_sha256"] = expect_sha256
    rep["pin_ok"] = (expect_sha256 is None or expect_sha256 == sha)
    return rep


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="containment/entailment-direction lint (proposal)")
    ap.add_argument("schema")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--expect-sha256", default=None)
    a = ap.parse_args(argv)
    try:
        rep = scan_path(a.schema, a.expect_sha256)
    except ValueError as e:
        print(json.dumps({"error": str(e), "path": a.schema}))
        return 2
    if not rep["pin_ok"]:
        print(json.dumps({"error": "pin_mismatch", **rep}))
        return 2
    if a.json:
        print(json.dumps(rep, indent=2, sort_keys=True))
    else:
        print(f"{rep['path']} sha256={rep['sha256'][:12]} applicable={rep['applicable']} "
              f"inverted={rep['inverted_count']} unsupported={rep['unsupported_count']}")
    return 1 if rep["inverted_count"] else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
