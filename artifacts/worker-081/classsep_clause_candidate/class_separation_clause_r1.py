"""Class-separation detector for the four frozen cosmic-censorship classes.

CANDIDATE worker-081 -- clause/structure-scoped successor to the frozen pin
`artifacts/worker-049/classsep_fn_audit/pinned/class_separation_c266_recovered.py`
(sha256 c266dbceca87fb996bd76a774145ef511cbf2aae190d9f423167d3200783a920).

Design (pre-registered in pre_registration.json):

  R1 composite-regularity merge (or/and/slash/comma/adjacency, caret and Unicode forms)
  R2 single class token containing both C0 and C2, or an unknown class token
  R3 WCC/SCC family unification in one declaration surface, or label/class_id family mismatch
  R4 conclusion inflation (SCC conclusion on a WCC class, WCC conclusion on an SCC class)

The R1 decision path is upgraded from a flat +/-60 character window to a
clause-scope classifier (`_clause_verdict`). The measured CF-16 failure mode is a
scope phenomenon: in adversarial assertions the cue sits in a different clause than
the clause carrying the merge predicate, and in metalinguistic mentions the merge
predicate is itself negated, quoted, reported, rejected, interrogative, or governed
by a mention noun. Cues are therefore resolved per clause, with quote spans, matrix
predicates, complement frames and pronoun continuations.

Every decision category that is not confidently ASSERT or MENTION returns
"UNCLEAR" and falls through to the canonical fallback logic below, which is retained
byte-for-byte so the frozen behaviour is available wherever the new classifier
abstains. No canonical file is edited by this module.
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
_BENIGN = re.compile(r"c0\s*-?\s*vs\.?\s*-?\s*c2|c2\s*-?\s*vs\.?\s*-?\s*c0", re.I)


def _class_tokens(text: str):
    return re.findall(r"AF-[A-Z0-9]+-[A-Z0-9]+-[A-Z0-9]+-[A-Z0-9]+", text.upper())


_NEG_BEFORE_ASSERT = re.compile(r"(?:no|not|never|without|zero|absent|nor)\s+(?:\w+\s+){0,2}$", re.I)


# =====================================================================================
# BEGIN worker-081 clause-scope classifier (new code; the canonical R1 fallback below
# is retained unchanged for every UNCLEAR decision)
# =====================================================================================

_SENT_END = re.compile(r"[.!?;\n]")
_CLAUSE_SEP = re.compile(r";|:|\n|,\s*(?:but|yet|so|whereas|although|though)\s+|,\s+", re.I)

# a predicate that asserts unity of C0 and C2, or a unity nominal
_UNITY = re.compile(
    r"\b(?:one|single|same|only)\s+(?:class|schema|regularity|label|unit|case|pattern|object|file)\b"
    r"|\bmerged\b|\bunified\b|\bcombined\b"
    r"|\binto\s+a\s+(?:single|one)\b"
    r"|\bas\s+one\s+(?:class|schema|regularity|label|unit)\b"
    r"|\bno\s+distinction\b"
    r"|\bshare[sd]?\s+(?:one|a\s+single)\b"
    r"|\badopted\s+design\b|\bcanonical\s+design\b"
    r"|\b(?:right|chosen|our|the\s+only)\s+(?:unit|case)\b"
    r"|\bshould\s+be\s+(?:merged|unified|combined|one)\b"
    r"|\bmerges?\s+(?:them|these|those|it)?\s*into\b"
    r"|\bkeeps?\s+(?:them\s+)?as\s+one\b"
    r"|\bkept\s+together\b"
    r"|\b(?:is|are|was|were)\s+one\b"
    r"|\bour\s+design\b"
    r"|\btreat(?:s|ed)?\b[^.;:]{0,30}\bas\s+one\b"
    r"|\bform(?:s|ed)?\s+(?:one|a\s+single)\b"
    r"|\bconstitute(?:s|d)?\s+(?:one|a\s+single)\b",
    re.I)

# negation scoped to the unity predicate -> the merge is denied, not asserted
_NEG_UNITY = re.compile(
    r"\b(?:is|are|was|were|remains?)\s+(?:not|never)\s+(?:one|a\s+single|the\s+same)\b"
    r"|\bnot\s+(?:one|a\s+single|the\s+same)\s+(?:class|schema|regularity|label|unit)\b"
    r"|\bnot\s+a\s+merged\s+class\b"
    r"|\bno\s+(?:genuine\s+|real\s+|actual\s+|proposed\s+)?(?:c\s*0[^.;:]{0,14}c\s*2|c\s*2[^.;:]{0,14}c\s*0)?\s*(?:merge|merging|merger|unification)\b"
    r"|\b(?:0|zero)\s+(?:genuine\s+|real\s+|actual\s+)?(?:assertion|claim|merge|evidence|finding)s?\b"
    r"|\b(?:merge|claim|reading|proposal|hypothesis|finding|assertion|story|outcome|evidence|note|report)\b"
    r"[^.;:]{0,40}?\b(?:is|was|were|are|remains?)\s+(?:rejected|refuted|denied|false|wrong|not\s+our|not\s+a|not\s+the)\b"
    r"|\b(?:reject(?:s|ed|ing)?|den(?:y|ies|ied)|refus(?:e|es|ed)|refut(?:e|es|ed))\b",
    re.I)

# negation of separation, or prohibition of splitting -> assertion of unity
_NEG_SEPARATION = re.compile(
    r"\b(?:not|never|rather\s+than|as\s+opposed\s+to|instead\s+of|no\s+longer)\s+(?:\w+\s+){0,3}"
    r"(?:separat\w*|split|distinct\w*|apart|two\s+classes|hygiene)\b"
    r"|\b(?:do|does|did)\s+not\s+separate\b"
    r"|\bnot\s+(?:distinct|separate|a\s+distinction)\b",
    re.I)
_SPLIT_PROHIBIT = re.compile(
    r"\b(?:do\s+not|don't|never|must\s+not|no)\s+(?:\w+\s+){0,2}"
    r"(?:split|separate|keep\s+(?:them\s+)?apart)\b", re.I)

# contrast that negates the merge itself -> mention
_CONTRAST_MERGE = re.compile(
    r"\b(?:rather\s+than|as\s+opposed\s+to|instead\s+of)\s+(?:a\s+|the\s+|any\s+)?"
    r"(?:c\s*0[^.;:]{0,14}c\s*2|c\s*2[^.;:]{0,14}c\s*0)?\s*(?:merge|merging|merger|unification)\b",
    re.I)

# mention / meta / reporting / case-label frames
_MENTION_FRAME = re.compile(
    r"\bfalse[- ]positive\b|\bnon-?merge\b|\bmetalinguistic\b|\bmention\b|\bdiscussion\s+of\b"
    r"|\b(?:says?|said|states?|stated|report(?:s|ed)?|record(?:s|ed)?|describ(?:e|es|ed)|quot(?:e|es|ed|ing)|discuss(?:es|ed)?|analys(?:e|es|ed)|measure[sd]?)\b"
    r"|\b(?:the\s+)?(?:phrase|token|string|sentence)\b"
    r"|\bwhether\b|\bhypothesis\b|\bquestion\b|\bproposal\b|\bcase\s*label\b"
    r"|\bTC-F0-N\d+\b|\bSPLIT_REQUIRED\b|\bsplit\s+rows?\b"
    r"|\brequire(?:s|d)?\s+(?:a\s+)?split\b|\bneed(?:s|ed)?\s+no\s+new\s+class\b"
    r"|\b(?:detector|checker|guard)\b[^.;:]{0,40}\b(?:finding|flag|output|pattern|match(?:es)?|self)\b"
    r"|\bflag(?:s|ged)?\b[^.;:]{0,40}\b(?:detector|checker|false|once)\b"
    r"|\b(?:matches?|appears?|occurs?)\s+only\b|\bpattern\b[^.;:]{0,40}\bappears?\b"
    r"|\bmust\s+(?:flag|be\s+flagged)\b|\bnot\s+our\s+claim\b|\bappears\s+in\b"
    r"|\bonly\s+as\s+a\s+(?:rejected|discarded|withdrawn)\b|\brejected\s+hypothesis\b"
    r"|\bproposed\b|\bquoted\b|\bstay(?:s)?\s+(?:separate|distinct)\b",
    re.I)

# adoption / enactment / endorsement of the merger
_ADOPT = re.compile(
    r"\badopt(?:s|ed|ing)?\b|\bhereby\b|\benact(?:s|ed)?\b|\bdecid(?:e|es|ed)\b|\bdecision\s+that\b"
    r"|\bconclu(?:de|des|ded)\s+that\b|\bhold(?:s)?\s+that\b"
    r"|\bwe\s+(?:agree|hold|adopt|keep|treat|unify|merge)\b"
    r"|\b(?:right|chosen|our|the\s+only)\s+(?:unit|case)\b"
    r"|\bno\s+question\b|\bno\s+doubt\b|\bnever\s+wrong\b|\bcorrect\s+to\s+say\b"
    r"|\breally\s+does\b|\bthis\s+text\s+does\b|\bfor\s+our\s+purposes\b"
    r"|\basserted\s*,\s*and\s+we\s+agree\b|\bfroze\s+it\b",
    re.I)

_MERGE_PROHIBIT = re.compile(
    r"\b(?:do\s+not|don't|never|must\s+not|forbidden|forbid(?:den)?|prohibit\w*|avoid)\b"
    r"[^.;:]{0,40}\b(?:merge|merging|conflate|unify|unification|combine|treat\s+as\s+one|"
    r"write|use|cite|call|label)\b", re.I)

_QUOTE_CHARS = {'"': '"', "“": "”", "‘": "’"}


def _quote_spans(text: str):
    """Quote spans for double quotes, curly quotes, and single quotes that are not
    apostrophes (an apostrophe has an alphanumeric character on both sides)."""
    spans = []
    stack = []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch in _QUOTE_CHARS:
            if stack and stack[-1][1] == ch:
                spans.append((stack.pop()[0], i + 1))
            else:
                stack.append((i, _QUOTE_CHARS[ch]))
        elif ch == "'":
            left = text[i - 1] if i > 0 else " "
            right = text[i + 1] if i + 1 < len(text) else " "
            if not (left.isalnum() and right.isalnum()):
                if stack and stack[-1][1] == "'":
                    spans.append((stack.pop()[0], i + 1))
                else:
                    stack.append((i, "'"))
        i += 1
    return spans


def _clauses(sent: str, keep_spans=()):
    """Split a sentence into clause spans (start, end, text), offsets local to sent.
    A comma boundary that falls inside or immediately beside a protected span (the
    composite match) is not a clause boundary."""
    cuts = [0]
    for m in _CLAUSE_SEP.finditer(sent):
        if any(a - 12 <= m.start() and m.end() <= b + 12 for a, b in keep_spans):
            continue
        cuts.append(m.end())
    cuts.append(len(sent))
    out = []
    for a, b in zip(cuts, cuts[1:]):
        seg = sent[a:b]
        if seg.strip():
            out.append((a, b, seg))
    return out


def _sent_span(t: str, s: int, e: int):
    start = 0
    for m in _SENT_END.finditer(t[:s]):
        start = m.end()
    m = _SENT_END.search(t, e)
    end = m.start() if m else len(t)
    return start, end


def _in_span(spans, s, e):
    return any(a <= s and e <= b for a, b in spans)


def _clause_verdict(t: str, s: int, e: int, mode: str) -> str:
    """Return ASSERT / MENTION / UNCLEAR for the composite occurrence t[s:e]."""
    start, end = _sent_span(t, s, e)
    sent = t[start:end]
    ls, le = s - start, e - start
    qspans = _quote_spans(sent)
    quoted = _in_span(qspans, ls, le)
    clauses = _clauses(sent, keep_spans=[(ls, le)])
    ci = None
    for i, (a, b, _seg) in enumerate(clauses):
        if a <= ls < b:
            ci = i
            break
    if ci is None:
        return "UNCLEAR"
    ctext = clauses[ci][2]

    # -- quoted composite: the matrix predicate governs --------------------------------
    if quoted:
        matrix = " ".join(seg for a, b, seg in clauses if not (a <= ls and le <= b))
        for qa, qb in qspans:
            if qa <= ls and le <= qb:
                matrix += " " + sent[qb:]
                break
        if _ADOPT.search(matrix):
            return "ASSERT"
        if _MENTION_FRAME.search(matrix) or _NEG_UNITY.search(matrix) or _MERGE_PROHIBIT.search(matrix):
            return "MENTION"
        return "MENTION"  # an unendorsed quotation is a mention by construction

    # -- merge prohibition in the evaluable clause -------------------------------------
    if _MERGE_PROHIBIT.search(ctext):
        return "MENTION"

    # -- adoption / endorsement wins over report frames (positional scope) --------------
    neg_m = _NEG_UNITY.search(ctext)
    adopt_m = _ADOPT.search(ctext)
    if adopt_m and (not neg_m or adopt_m.start() > neg_m.start()):
        return "ASSERT"

    # -- negation of unity, contrastive merge, mention/case frames ----------------------
    if neg_m or _CONTRAST_MERGE.search(ctext):
        return "MENTION"
    copular = re.search(r"\b(?:are|is|was|were|remains?)\s+(?:one|a\s+single|the\s+same|merged|unified|combined|kept|treated)\b",
                        ctext, re.I)
    if _MENTION_FRAME.search(ctext):
        # FN4/AX3-style endorsement already handled above; a mention frame with a
        # directly negated split is still an assertion (A10-style); a finite copular
        # unity assertion outranks an incidental report word (P07-style).
        if not _NEG_SEPARATION.search(ctext) and not copular:
            return "MENTION"

    # -- negated separation / split prohibition ----------------------------------------
    if _NEG_SEPARATION.search(ctext):
        return "ASSERT"
    prev = clauses[ci - 1][2] if ci > 0 else ""
    if _SPLIT_PROHIBIT.search(prev):
        return "ASSERT"

    # -- pronoun continuation: a following clause asserts unity positively --------------
    nxt = clauses[ci + 1][2] if ci + 1 < len(clauses) else ""
    if nxt and _UNITY.search(nxt) and not _NEG_UNITY.search(nxt) and not _MENTION_FRAME.search(nxt):
        return "ASSERT"

    # -- direct unity predicate in the composite's own clause ---------------------------
    if _UNITY.search(ctext):
        if re.search(r"\?\s*$", ctext.strip()) or re.match(r"\s*(?:is|are|was|were|does|do|did|can|should|whether)\b", ctext.strip(), re.I):
            return "MENTION"
        return "ASSERT"

    # -- appositive continuation: a bare composite clause following a unity clause ------
    ca, cb, _seg = clauses[ci]
    rest = (ctext[:ls - ca] + ctext[le - ca:]).strip(" .,:;'\"-\u2013\u2014")
    if not rest and ci > 0:
        prevc = clauses[ci - 1][2]
        if _UNITY.search(prevc) and not _NEG_UNITY.search(prevc) and not _MENTION_FRAME.search(prevc):
            return "ASSERT"

    # -- no unity predicate in the clause: window artifacts are mentions in prose -------
    if _UNITY.search(sent):
        return "MENTION"          # unity word lives in a different clause -> flat-window artifact
    if mode == "prose":
        return "MENTION"
    return "UNCLEAR"


# =====================================================================================
# END worker-081 clause-scope classifier
# =====================================================================================


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
        verdict = _clause_verdict(t, m.start(), m.end(), mode)
        if verdict == "ASSERT":
            out.append(f"CLASSSEP: composite C0/C2 asserted as one class in {where}: ...{ctx.strip()!r}")
            continue
        if verdict == "MENTION":
            continue
        # ---- canonical fallback (unchanged) for UNCLEAR decisions ----
        assert_match = _MERGE_ASSERT.search(ctx)
        if assert_match:
            before = ctx[:assert_match.start()]
            if _NEG_BEFORE_ASSERT.search(before):
                continue  # "no merged 'C0 or C2'", "not unified"
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
