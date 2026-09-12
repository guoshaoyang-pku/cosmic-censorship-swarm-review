"""Class-separation detector for the four frozen cosmic-censorship classes.

Designed against the worker-07 falsification corpus
(`artifacts/worker-07/class_separation_falsification/`), which demonstrated that a
naive regex detected only 3 of 17 genuine class-merge fixtures and produced one
spurious flag. This module implements:
  R1 composite-regularity merge (or/and/slash/comma/adjacency, caret and Unicode forms)
  R2 single class token containing both C0 and C2, or an unknown class token
  R3 WCC/SCC family unification in one declaration surface, or label/class_id family mismatch
  R4 conclusion inflation (SCC conclusion on a WCC class, WCC conclusion on an SCC class)
with prohibition/split contexts handled locally so legitimate documents
("C2/C0 split", "never write 'C0 or C2'", "C0-vs-C2 distinction") are not flagged,
and merge assertions ("...are one class", "merged", "share one schema") are flagged
even when a negation word appears elsewhere in the sentence.

`findings(obj, where)` returns human-readable violation strings; the regression
runner `runtime/bin/classsep_regression.py` scores them against domain ground truth.
"""
from __future__ import annotations

import json
import re

KNOWN_CLASSES = {
    "AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH",
}
WCC_MARK = re.compile(r"AF-WCC|(?<![A-Za-z])WCC(?![A-Za-z])")
SCC_MARK = re.compile(r"AF-SCC|(?<![A-Za-z])SCC(?![A-Za-z])")
SCC_CONCLUSION = re.compile(r"inextendib|cauchy[\s_-]*horizon|strong[\s_-]*cosmic|(?<![A-Za-z])scc(?![A-Za-z])|"
                            r"extension[\s_]+across|extendib", re.I)
WCC_CONCLUSION = re.compile(r"weak[\s_-]*cosmic|(?<![A-Za-z])wcc(?![A-Za-z])|visible|visibility|"
                            r"naked[\s_-]*singularit", re.I)

# surfaces whose contents are assertions about classes (scanned)
DECLARATION_KEYS = {
    "label", "title", "class_id", "class_ids", "conclusion", "conclusion_type",
    "notes", "purpose", "scope", "scope_statement", "direction", "event",
    "statement", "declared_selector", "regularity", "regularity_token", "family",
}

SUP = {"⁰": "0", "¹": "1", "²": "2", "³": "3"}


def norm(s: str) -> str:
    for k, v in SUP.items():
        s = s.replace(k, v)
    s = s.replace("^", "").replace("{", "").replace("}", "")
    return s


_MERGE_PAT = re.compile(
    r"c\s*0\s*(?:or|and|/|,|\+|\s)\s*c\s*2"
    r"|c\s*2\s*(?:or|and|/|,|\+|\s)\s*c\s*0"
    r"|c0c2|c2c0", re.I)

_PROHIBIT = re.compile(r"never|forbidden|forbid|must\s+not|do\s+not|don't|prohibit|ban(ned)?|illegal|"
                       r"conflate|avoid|no\s+\w+\s+may", re.I)
_SPLIT = re.compile(r"split|separate|separat|distinct|distinction|vs\b|leakage|hygiene|two\s+(?:separate\s+)?classes", re.I)
_MERGE_ASSERT = re.compile(r"as\s+one|are\s+one|is\s+one|one\s+class|single\s+class|one\s+schema|single\s+schema|"
                           r"unified|unif(y|ication)|merged|merge\b|share[sd]?\s+one|combined|same\s+class|"
                           r"treated?\s+as\s+one|into\s+a\s+single", re.I)
# tokens that make a slash/and legitimate even without an explicit split word
_BENIGN = re.compile(r"c0\s*-?\s*vs\.?\s*-?\s*c2|c2\s*-?\s*vs\.?\s*-?\s*c0", re.I)


def _class_tokens(text: str):
    return re.findall(r"AF-[A-Z0-9]+-[A-Z0-9]+-[A-Z0-9]+-[A-Z0-9]+", text.upper())


_NEG_BEFORE_ASSERT = re.compile(r"(?:no|not|never|without|zero|absent|nor)\s+(?:\w+\s+){0,2}$", re.I)

# --- CF-16 prose-mode calibration (worker-049, W049-CLASSSEP-PROSEFIX-01) ------
# In prose mode the canonical +-60-char window treats any merge word near a
# composite as an assertion.  It therefore misfires on (a) case labels
# ("TC-F0-N14 C0/C2 merge"), (b) negations its guard cannot span because \w+
# excludes '/', e.g. "no C0/C2 merge exists" and the "non-merge" compound,
# (c) quoted / metalinguistic mentions ("'C0 or C2 are one class' is flagged"),
# and (d) merge words belonging to another clause ("the retired merged file; and
# ... the live C2/C0 components moved").  The rules below classify each merge
# word in the window; a prose composite is flagged only if at least one merge
# word is an assertion *about that composite*.  Rule set ported from the
# independently controlled classifier in
# artifacts/worker-035/classsep_hardfail_adjudication/adjudicate_hardfailures.py
# (9/9 positive and 14/14 negative controls pass there).  Applied to
# mode="prose" only: declaration-mode behaviour is unchanged, so every
# worker-07 declaration/artifact fixture keeps its existing verdict.
_CASE_ID = re.compile(r"\b(?:TC|FX|CASE|ROW|FIXTURE)-[A-Za-z0-9-]+\b", re.I)
_LABEL_NOUN = re.compile(
    r"\b(?:merge|merger|merged|regularities|regularity|families|family|case|cases|"
    r"row|rows|fixture|fixtures|label|labels|disposition|request|composite|composites|"
    r"split)\b", re.I)
_NEG_CUE = re.compile(r"\b(?:no|not|never|without|zero|absent|nor|neither|none|non|0)\b", re.I)
_NEG_PHRASE = re.compile(r"rather\s+than|instead\s+of|as\s+opposed\s+to|not\s+a\b|no\s+longer", re.I)
_REJECT_CUE = re.compile(
    r"\b(?:rejects?|rejected|denies|denied|disputes?|disputed|refutes?|refuted|"
    r"contradicts?|contradicted|opposes?|opposed|dismiss(?:es|ed)?)\b", re.I)
_META_CUE = re.compile(
    r"\b(?:pattern|regex|regexp|detector|checker|scanner|scan|scans|matches?|matched|"
    r"flags?|flagged|flagging|reproduces?|vocabulary|asserted|assertion|adjudicat\w*|"
    r"false\s+positive|names?|describes?|quoted?|cites?|cited)\b", re.I)
_RIGHT_META_CUE = re.compile(r"\b(?:pattern|regex|regexp|vocabulary|matches?|flagged|flag)\b", re.I)
_QUOTED_SPAN = re.compile(
    r"\"[^\"]{1,400}\""
    r"|\u201c[^\u201d]{1,400}\u201d"
    r"|(?<![A-Za-z0-9])'[^']{1,400}'(?![A-Za-z0-9])"
    r"|(?<![A-Za-z0-9])\u2018[^\u2019]{1,400}\u2019(?![A-Za-z0-9])")
_CLAUSE_BOUNDARY = re.compile(r"[;.!?\n]|\u2014|\u2013")
_TOKEN = re.compile(r"[A-Za-z0-9/_.^+-]+")


def _quoted_spans(s: str):
    return [(m.start(), m.end()) for m in _QUOTED_SPAN.finditer(s)]


def _in_span(spans, pos: int) -> bool:
    return any(a <= pos < b for a, b in spans)


def _tokens_before(s: str, pos: int, n: int = 4):
    return _TOKEN.findall(s[:pos])[-n:]


def _merge_word_is_assertion(t: str, comp_start: int, comp_end: int,
                             w_start: int, w_end: int, qspans) -> bool:
    """True iff this merge word asserts that the composite is one class."""
    if _in_span(qspans, comp_start) or _in_span(qspans, w_start):
        return False  # QUOTED: mention of a composite/merge word, not a use
    between = t[min(comp_end, w_end):max(comp_start, w_start)]
    if _CLAUSE_BOUNDARY.search(between):
        return False  # CROSS_CLAUSE: the merge word governs another clause
    if re.search(r"\bnon[-\s]?$", t[max(0, w_start - 6):w_start], re.I):
        return False  # NEGATED: "non-merge" compound
    if [x for x in _tokens_before(t, comp_start, 4) if _NEG_CUE.fullmatch(x)]:
        return False  # NEGATED: cue before the composite ("no C0/C2 merge")
    if [x for x in _tokens_before(t, w_start, 3) if _NEG_CUE.fullmatch(x)]:
        return False  # NEGATED: cue before the merge word
    if _NEG_PHRASE.search(t[max(0, min(comp_start, w_start) - 55):max(comp_start, w_start)]):
        return False  # NEGATED: "rather than a C2/C0 merge"
    for anchor in (comp_start, w_start):
        rc = _REJECT_CUE.search(t[max(0, anchor - 80):anchor])
        if rc and not _CLAUSE_BOUNDARY.search(t[max(0, anchor - 80) + rc.end():anchor]):
            return False  # REJECTED/DENIED in the same clause
    word = t[w_start:w_end]
    cid = _CASE_ID.search(t[max(0, w_start - 50):w_start])
    if cid and (_LABEL_NOUN.search(word) or _LABEL_NOUN.search(t[w_end:w_end + 40])):
        return False  # CASE_LABEL: a taxonomy case names the merge, not a class
    if _META_CUE.search(t[max(0, w_start - 55):w_start]):
        return False  # METALINGUISTIC: describes a check/flag, not a class
    if _RIGHT_META_CUE.search(t[w_end:w_end + 60]):
        return False  # METALINGUISTIC: "merge pattern", "matches", "flagged"
    return True


def _scan_composite(text: str, where: str, out: list, mode: str = "declaration"):
    """mode=declaration: a bare composite is a violation (fixture L01/L02/...).
    mode=prose: only explicit merge assertions violate; quoted or discussed
    composites do not (a claim *about* a leak is not a leak)."""
    t = norm(text)
    for m in _MERGE_PAT.finditer(t):
        lo, hi = max(0, m.start() - 60), min(len(t), m.end() + 60)
        ctx = t[lo:hi]
        if _BENIGN.search(t[max(0, m.start() - 8):m.end() + 8]):
            continue
        assert_match = _MERGE_ASSERT.search(ctx)
        if assert_match:
            before = ctx[:assert_match.start()]
            if _NEG_BEFORE_ASSERT.search(before):
                continue  # "no merged 'C0 or C2'", "not unified"
            if mode == "prose":
                qspans = _quoted_spans(t)
                words = list(_MERGE_ASSERT.finditer(ctx))
                if not any(_merge_word_is_assertion(
                        t, m.start(), m.end(), lo + w.start(), lo + w.end(), qspans)
                        for w in words):
                    continue  # CF-16: all merge words are mentions/negations/labels
            out.append(f"CLASSSEP: composite C0/C2 asserted as one class in {where}: ...{ctx.strip()!r}")
        elif _PROHIBIT.search(ctx):
            continue
        elif _SPLIT.search(ctx):
            continue
        elif mode == "declaration":
            out.append(f"CLASSSEP: bare composite C0/C2 expression in {where}: ...{ctx.strip()!r}")


def _scan_class_ids(value, where: str, out: list):
    if isinstance(value, str):
        toks = [t for t in re.split(r"[;,]", value) if t.strip()]
    elif isinstance(value, list):
        toks = [str(x) for x in value]
    else:
        return
    for tok in toks:
        u = tok.strip().upper()
        if not u:
            continue
        n = norm(u)
        has0 = bool(re.search(r"C\s*0", n)) or "C0" in n
        has2 = bool(re.search(r"C\s*2", n)) or "C2" in n
        if has0 and has2:
            out.append(f"CLASSSEP: single class token merges C0 and C2 in {where}: {tok!r}")
        elif u not in KNOWN_CLASSES and u.startswith("AF-"):
            out.append(f"CLASSSEP: unknown class token in {where}: {tok!r}")


def _scan_family(text: str, where: str, class_id: str, out: list):
    t = norm(text)
    has_wcc = bool(WCC_MARK.search(t))
    has_scc = bool(SCC_MARK.search(t))
    if has_wcc and has_scc and _MERGE_ASSERT.search(t):
        out.append(f"CLASSSEP: WCC and SCC unified in one declaration surface in {where}: {text[:120]!r}")
    cid = (class_id or "").upper()
    if cid:
        fam_wcc = cid.startswith("AF-WCC")
        if has_wcc and not has_scc and not fam_wcc:
            out.append(f"CLASSSEP: label family (WCC) disagrees with class_id {cid} in {where}: {text[:120]!r}")
        if has_scc and not has_wcc and cid.startswith("AF-WCC"):
            out.append(f"CLASSSEP: label family (SCC) disagrees with class_id {cid} in {where}: {text[:120]!r}")


def _scan_conclusion(text: str, class_id: str, where: str, out: list):
    if not text or not class_id:
        return
    t = norm(str(text))
    cid = class_id.upper()
    if cid.startswith("AF-WCC") and SCC_CONCLUSION.search(t) and not WCC_CONCLUSION.search(t):
        out.append(f"CLASSSEP: SCC conclusion on a WCC class in {where}: {str(text)[:120]!r}")
    if cid.startswith("AF-SCC") and WCC_CONCLUSION.search(t) and not SCC_CONCLUSION.search(t):
        out.append(f"CLASSSEP: WCC conclusion on an SCC class in {where}: {str(text)[:120]!r}")


def _walk_strings(o, path=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from _walk_strings(v, f"{path}.{k}" if path else str(k))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from _walk_strings(v, f"{path}[{i}]")
    elif isinstance(o, str):
        yield path, o


def findings(obj, where: str, mode: str = "declaration") -> list:
    """Scan one declaration object (node, group header, portfolio event, claim)."""
    out: list = []
    if not isinstance(obj, dict):
        return out
    class_id = str(obj.get("class_id") or "")
    for key, val in obj.items():
        if key in ("class_id", "class_ids"):
            _scan_class_ids(val, f"{where}.{key}", out)
            continue
        if key not in DECLARATION_KEYS:
            continue
        if isinstance(val, str):
            _scan_composite(val, f"{where}.{key}", out, mode)
            if mode == "declaration":
                _scan_family(val, f"{where}.{key}", class_id, out)
            if key in ("conclusion", "conclusion_type", "scope", "scope_statement"):
                _scan_conclusion(val, class_id, f"{where}.{key}", out)
        elif isinstance(val, list):
            for i, v in enumerate(val):
                if isinstance(v, str):
                    _scan_composite(v, f"{where}.{key}[{i}]", out, mode)
                    if mode == "declaration":
                        _scan_family(v, f"{where}.{key}[{i}]", class_id, out)
    return out


def findings_for_map(m: dict) -> list:
    out = []
    for gi, g in enumerate(m.get("groups", [])):
        if isinstance(g.get("direction"), str):
            _scan_composite(g["direction"], f"groups[{g.get('id', gi)}].direction", out)
            _scan_family(g["direction"], f"groups[{g.get('id', gi)}].direction", "", out)
        for n in g.get("nodes", []):
            out += findings(n, f"node {n.get('id', '?')}")
    for i, ev in enumerate(m.get("portfolio_events", [])):
        if isinstance(ev, dict):
            out += findings(ev, f"portfolio_events[{i}]")
    for i, c in enumerate(m.get("claims", [])):
        if isinstance(c, dict):
            out += findings(c, f"claims[{i}]", mode="prose")
    return out


ASSERTED_LINE_KEYS = ("class_id", "class_ids", "conclusion_type", "regularity",
                      "regularity_token", "family", "declared_selector")


def findings_for_text(text: str, where: str) -> list:
    """Artifact content scan. Prose mode: only merge assertions and semantic
    key:value lines violate; unknown class tokens are reported as soft."""
    out: list = []
    _scan_composite(text, where, out, mode="prose")
    for i, line in enumerate(text.splitlines(), 1):
        m = re.match(r"\s*[\"']?([A-Za-z_]+)[\"']?\s*[:=]\s*(.+)$", line)
        if m and m.group(1) in ASSERTED_LINE_KEYS:
            _scan_composite(m.group(2), f"{where}:{i} ({m.group(1)})", out, mode="declaration")
    for tok in _class_tokens(text):
        if tok not in KNOWN_CLASSES:
            out.append(f"CLASSSEP-SOFT: unknown class token in {where}: {tok!r}")
    return out


def regression(corpus_dir=None) -> dict:
    """Score this detector against worker-07's falsification corpus.

    Returns {"tp","fn","tn","fp","verdict"}; ground truth is the corpus's
    independently recorded `is_class_merge` field.
    """
    import json as _json
    from pathlib import Path as _P
    root = _P(__file__).resolve().parent.parent
    corpus = _P(corpus_dir) if corpus_dir else root / "artifacts/worker-07/class_separation_falsification"
    res = _json.loads((corpus / "results.json").read_text())
    tp = fn = tn = fp = 0
    for fx in res["fixtures"]:
        fpth = root / fx["fixture_path"]
        if not fpth.exists():
            continue
        m = _json.loads(fpth.read_text())
        det = findings_for_map(m)
        for g in m.get("groups", []):
            for n in g.get("nodes", []):
                art = n.get("artifact")
                if art and (root / art).is_file():
                    det += findings_for_text((root / art).read_text(errors="replace"), f"artifact {art}")
        got, truth = bool(det), bool(fx["is_class_merge"])
        if truth and got:
            tp += 1
        elif truth and not got:
            fn += 1
        elif not truth and got:
            fp += 1
        else:
            tn += 1
    return {"tp": tp, "fn": fn, "tn": tn, "fp": fp,
            "verdict": "PASS" if fn == 0 and fp == 0 else "DEFECTIVE",
            "corpus_size": tp + fn + tn + fp}
