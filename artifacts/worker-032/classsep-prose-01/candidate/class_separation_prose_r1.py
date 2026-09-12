"""Class-separation detector for the four frozen cosmic-censorship classes.

STAGED CANDIDATE r1 (worker-032, task W032-CLASSSEP-PROSE-01). NOT APPLIED.
Base: research_map/class_separation.py @ sha256 a8c04fc31e4afa1b691cd6bfb6bf8b4f953a0adc925939a8351bab9cf453c5bd
(canonical, live at pin 2026-09-12T00:59+08:00).

Change scope: COMPOSITE PROSE MODE ONLY (`_scan_composite(..., mode="prose")`).
The declaration-mode decision procedure is the canonical one, verbatim, but the
module-level and `_scan_composite`-local patterns are shared: the assertion
vocabulary is extended and the clause helpers are new. Any declaration-surface
effect is therefore measured, not assumed, by the harness's declaration-mode
differential (0 diffs on the design pin at the time of writing).

What this candidate fixes, per the CLASSSEP calibration adjudication
(reviews/CLASSSEP-calibration-adjudication.json, astra-life05 r2 + life06 r3):

  R-a  negation binding must span the composite token ("no C0/C2 merge"),
       not just \\w+ words.
  R-b  the skip/assert decision must bind inside the local clause, not a
       character window that crosses ';', ',' or ', but'.
  R-c  metalinguistic cues (quoting/describing the detector, pattern/regex
       vocabulary, "genuine assertions"/"pre-registered adversarial ... twin"
       control prose) exempt the mention.
  A6   "Do not split: C0 or C2" is an assertion of unity and must fire, but
       only when the directive is not itself quoted.
  B1/B3/B4/B5  assertion vocabulary gap: "constitutes/forms/is a single +
       family|regularity class" (measured in W032-CF16-DELTA-02).

Precedence, per composite mention in prose mode:
  quoted > case-label-bound > non-merge compound > negated/bound-away merge >
  post-mention negation > rejection frame > embedded question/interrogative >
  metalinguistic > unquoted negated-split or negated-separation (fires) >
  prohibition of merge (silent) > merge assertion (fires) > prohibit/split
  (silent) > appositive enumeration (fires) > bare composite (silent in prose).

Measured by artifacts/worker-032/classsep-prose-01/run_calibration.py:
27-fixture PASS 17/0/10/0; lead corpus (c) sensitivity 5/6 specificity 10/10;
worker-049 cue-FN corpus 0 HIGH cue-FN / 0 mention FP / 12-12 twins;
worker-035 battery 23/23; live hard findings 17 -> 0 at map 262da697 (320
claims) and 23 -> 0 at map 5ab4bed1 (414 claims); converse scan 0 genuine
unflagged; declaration differential 0.

This module is evidence, not a gate verdict; it writes nothing.
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

# ---- candidate r1: assertion vocabulary extended to close B1/B3/B4/B5 ----
_MERGE_ASSERT = re.compile(r"as\s+one|are\s+one|is\s+one|one\s+class|single\s+class|one\s+schema|single\s+schema|"
                           r"unified|unif(y|ication)|merged|merge\b|share[sd]?\s+one|combined|same\s+class|"
                           r"treated?\s+as\s+one|into\s+a\s+single|"
                           r"(?:constitutes?|forms?|is|are|becomes?)\s+(?:a\s+|the\s+)?(?:single|one)\s+"
                           r"(?:family|regularity(?:\s+class)?|class|schema)\b", re.I)
# tokens that make a slash/and legitimate even without an explicit split word
_BENIGN = re.compile(r"c0\s*-?\s*vs\.?\s*-?\s*c2|c2\s*-?\s*vs\.?\s*-?\s*c0", re.I)


def _class_tokens(text: str):
    return re.findall(r"AF-[A-Z0-9]+-[A-Z0-9]+-[A-Z0-9]+-[A-Z0-9]+", text.upper())


_NEG_BEFORE_ASSERT = re.compile(r"(?:no|not|never|without|zero|absent|nor)\s+(?:\w+\s+){0,2}$", re.I)

# ---- candidate r1 helpers (prose mode only) ------------------------------------------------
_CLAUSE_STOP = re.compile(
    r"[.;:!?,\u2014\u2013]|,\s*(?:but|yet|however|nevertheless|whereas|while|although|though|instead)\b",
    re.I)
_QUOTED_SPAN = re.compile(
    r"(?<![A-Za-z0-9])'(?!s(?=[\s,.;:)\]\u2019]|$))[^'\n]{2,300}'"
    r"|\"[^\"\n]{2,300}\""
    r"|\u2018[^\u2019\n]{2,300}\u2019"
    r"|\u201c[^\u201d\n]{2,300}\u201d")
# a taxonomy case label exempts only when it BINDS the mention (adjacent, e.g.
# "TC-F0-N14 merged C0/C2"), never when it is incidental ("Following TC-F0-N14, the C0/C2 merge...").
_CASE_LABEL_BIND = re.compile(
    r"(?:TC-[A-Z0-9]+(?:-[A-Z0-9]+)*|SPLIT_REQUIRED|NEW_CLASS_REQUIRED|DEFERRED)"
    r"\s*\(?\s*(?:merged\s+|unified\s+)?$", re.I)
_NONMERGE = re.compile(r"non[\s-]?merge", re.I)
_DENY_BEFORE = re.compile(
    r"(?:\b(?:no|not|never|without|zero|absent|nor|none|0)\b|\brather\s+than\b|"
    r"\binstead\s+of\b|\bas\s+opposed\s+to\b)(?:\s+[\w'\-]+){0,3}\s*$", re.I)
_MERGE_AFTER = re.compile(
    r"^[\s\w'\-]{0,12}?\b(?:merge|merging|merged|unif\w*|fusion|combined|conflat\w*)\b", re.I)
_META_CUE = re.compile(
    r"\b(?:detector|scanner|class_separation|CLASSSEP|false[\s-]?positive|pattern|regex|vocabulary|"
    r"fixture|corpus|probe|pre-registered|adversarial|cue-stripped|twin|quote(?:d|s)?|quoting|"
    r"describ\w*|mention(?:s|ed)?|match(?:es|ed)?\s+only|genuine\s+assertions?|"
    r"first-order\s+assertions?|assertion-cued)\b", re.I)
_NEG_SPLIT = re.compile(
    r"\b(?:do\s+not|don'?t|never|must\s+not|should\s+not|not\s+to|refuse\s+to)\s+split\b", re.I)
# "C0/C2 are not separate; one class." -- negated separation applied to the composite
# is an assertion of unity, exactly like the negated-split directive.
_NEG_SEPARATE = re.compile(r"\b(?:not|never|no\s+longer)\s+(?:separate[ds]?|distinct|split)\b", re.I)
# "Do not merge C0 and C2 into one class." -- prohibition of the merge is a mention.
_PROHIBIT_MERGE = re.compile(
    r"\b(?:do\s+not|don'?t|never|must\s+not|should\s+not|avoid|no\s+\w+\s+may)\s+"
    r"(?:\w+\s+){0,2}(?:merge|merging|merged|combine|combined|unify|unified|conflate)\b", re.I)
# "a required separation, not a merged class" -- post-mention negation of the merge word.
_NEG_MERGE_POST = re.compile(r"\bnot\s+(?:a\s+|the\s+)?(?:merged|unified|single|combined|one)\b", re.I)
# "We reject the proposal that C0/C2 are one class." -- attribution/rejection frame.
_REJECT_FRAME = re.compile(
    r"\b(?:rejects?|rejected|denies|denied|refuses?|refused|refutes?|refuted)\s+"
    r"(?:(?:\w+\s+){0,2}(?:claim|assertion|reading|proposal|statement)s?\s+)?that\b", re.I)
_WHETHER = re.compile(r"\bwhether\b", re.I)
# "Both classes are one: C0 and C2." -- appositive enumeration bound to the previous clause.
_APPOSITIVE_BIND = re.compile(r"\b(?:are|is|were|was)\s+(?:one|the\s+same|a\s+single)\s*[:;,]\s*$", re.I)


def _spans(rx, t):
    return [(m.start(), m.end()) for m in rx.finditer(t)]


def _inside(spans, s, e):
    return any(a < e and s < b for a, b in spans)


def _sentence(t: str, start: int, end: int) -> str:
    left = max(t.rfind(".", 0, start), t.rfind("!", 0, start), t.rfind("?", 0, start)) + 1
    rights = [x for x in (t.find(".", end), t.find("!", end), t.find("?", end)) if x != -1]
    right = min(rights) + 1 if rights else len(t)
    return t[left:right]


def _local_scope(t: str, start: int, end: int):
    """Clause containing t[start:end]; returns (scope_text, scope_offset)."""
    left = 0
    for m in _CLAUSE_STOP.finditer(t, 0, start):
        left = m.end()
    right = len(t)
    for m in _CLAUSE_STOP.finditer(t, end):
        right = m.start()
        break
    return t[left:right], left


def _scan_composite(text: str, where: str, out: list, mode: str = "declaration"):
    """mode=declaration: canonical algorithm, unchanged.
    mode=prose: clause-local binding (candidate r1); quoted or discussed
    composites do not violate (a claim *about* a leak is not a leak)."""
    t = norm(text)
    qspans = _spans(_QUOTED_SPAN, t)
    for m in _MERGE_PAT.finditer(t):
        if _BENIGN.search(t[max(0, m.start() - 8):m.end() + 8]):
            continue

        if mode == "prose":
            if _inside(qspans, m.start(), m.end()):
                continue  # quoted mention
            scope, off = _local_scope(t, m.start(), m.end())
            before, after = scope[:m.start() - off], scope[m.end() - off:]
            sent = _sentence(t, m.start(), m.end())
            if _CASE_LABEL_BIND.search(before):
                continue  # taxonomy case entry binds the composite ("TC-F0-N14 merged C0/C2")
            if _NONMERGE.search(scope):
                continue  # "non-merge" compound
            if _DENY_BEFORE.search(before) and _MERGE_AFTER.search(after):
                continue  # "no C0/C2 merge", "rather than a C2/C0 merge"
            if _NEG_MERGE_POST.search(scope):
                continue  # "not a merged class"
            if _REJECT_FRAME.search(scope):
                continue  # "rejects the proposal that C0/C2 are one class"
            if _WHETHER.search(scope):
                continue  # embedded question
            if sent.rstrip().endswith("?"):
                continue  # interrogative mention
            if _META_CUE.search(scope):
                continue  # detector self-description / quoting prose
            nm = _NEG_SPLIT.search(sent)
            if nm and not _inside(qspans, nm.start(), nm.end()):
                out.append(f"CLASSSEP: composite C0/C2 asserted as one class in {where}: "
                           f"...{(scope.strip() or sent.strip())!r}")
                continue  # A6: unquoted "do not split: C0 or C2" asserts unity
            nsep = _NEG_SEPARATE.search(scope)
            if nsep and not _inside(qspans, nsep.start() + off, nsep.end() + off):
                out.append(f"CLASSSEP: composite C0/C2 asserted as one class in {where}: "
                           f"...{scope.strip()!r}")
                continue  # "C0/C2 are not separate" asserts unity (quote-guarded)
            if _PROHIBIT_MERGE.search(scope):
                continue  # "do not merge C0 and C2"
            am = _MERGE_ASSERT.search(scope)
            if am:
                if _NEG_BEFORE_ASSERT.search(scope[:am.start()]):
                    continue
                out.append(f"CLASSSEP: composite C0/C2 asserted as one class in {where}: "
                           f"...{scope.strip()!r}")
                continue
            if _PROHIBIT.search(scope) or _SPLIT.search(scope):
                continue
            # appositive enumeration: "Both classes are one: C0 and C2."
            if _APPOSITIVE_BIND.search(t[max(0, off - 60):off]):
                out.append(f"CLASSSEP: composite C0/C2 asserted as one class in {where}: "
                           f"...{(t[max(0, off - 60):m.end()]).strip()!r}")
                continue
            # bare composite in prose mode is not a violation
            continue

        # ---- declaration mode: canonical a8c04fc31e4a algorithm, verbatim ----
        lo, hi = max(0, m.start() - 60), min(len(t), m.end() + 60)
        ctx = t[lo:hi]
        assert_match = _MERGE_ASSERT.search(ctx)
        if assert_match:
            # Do not treat explicit detector/meta-audit quotations as declarations.
            if re.search(r"false[- ]positive|non[- ]merge|not\s+(?:a\s+)?merge|no\s+genuine\s+(?:c0/c2|c2/c0)\s+merge|detector\s+(?:finding|flag)|quote(?:d|s)?\s+(?:the\s+)?detector", ctx, re.I):
                continue
            before = ctx[:assert_match.start()]
            if _NEG_BEFORE_ASSERT.search(before):
                continue  # "no merged 'C0 or C2'", "not unified"
            out.append(f"CLASSSEP: composite C0/C2 asserted as one class in {where}: ...{ctx.strip()!r}")
        elif _PROHIBIT.search(ctx):
            continue
        elif _SPLIT.search(ctx):
            continue
        else:
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
