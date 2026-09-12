"""W040-A1-CLASSSEP-STRUCTURAL-01 prototype: a clause-scope structural cue.

Pre-registered rule `STRUCTURAL_R1` (artifacts/worker-040/classsep_structural/
PRE_REGISTRATION.json). Read-only prototype; it edits no canonical path and is not an
adoption candidate by itself.

Design difference from the four lexical arms: there is no character-window proximity
test. The unit of decision is the clause. A composite C0/C2 occurrence is judged by
(1) whether it sits inside a quotation span, (2) whether the clause's unity predicate is
under the scope of a merge-negation, (3) which matrix predicate / meta-noun governs the
embedded unity clause, and (4) intra-sentential antecedent for pronominal continuations.
"""
from __future__ import annotations

import ast
import json
import re
from pathlib import Path

KNOWN_CLASSES = {
    "AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH",
}

SUP = {"\u2070": "0", "\u00b9": "1", "\u00b2": "2", "\u00b3": "3"}


def norm(s: str) -> str:
    for k, v in SUP.items():
        s = s.replace(k, v)
    s = s.replace("^", "")
    return s


# ---------------------------------------------------------------- composites
_JOIN = r"(?:or|and|/|,|\+|&|vs\.?)"
COMPOSITE = re.compile(
    rf"c\s*0\s*{_JOIN}\s*c\s*2|c\s*2\s*{_JOIN}\s*c\s*0|c0c2|c2c0", re.I)
COMPOSITE_STR = COMPOSITE.pattern

_UNITY_HEAD = (
    rf"(?:the\s+|a\s+|our\s+|this\s+|these\s+)?(?:live\s+|independent\s+|composite\s+)?"
    rf"(?:{COMPOSITE_STR})\s+(?:merged|unified|combined|single|one)\s+"
    rf"(?:class|classes|schema|schemas|unit|label|labels|table|pattern|composite|composites|"
    rf"regularit(?:y|ies)|family|families)"
)

# compounds where the merge adjective precedes the composite, e.g. "merged C0/C2 regularities"
_UNITY_HEAD_PRE = (
    rf"(?:merged|unified|combined)\s+(?:{COMPOSITE_STR})\s+"
    rf"(?:class|classes|schema|schemas|unit|label|table|pattern|composite|composites|"
    rf"regularit(?:y|ies)|family|families)"
)

_UNITY_PRED = re.compile(
    # copula / predication
    r"\b(?:are|is|were|was|be|becomes?|remain[s]?|stay[s]?)\s+(?:the\s+|a\s+|our\s+)?"
    r"(?:one|single|same|a\s+single)\s+(?:class|schema|unit|family|label)"
    r"|\b(?:constitutes?|forms?|shares?|share[sd]?|creates?|defines?|drops?|dropped)\b[^.;]{0,30}?"
    r"\b(?:one|single|same|a\s+single)\s+(?:class|schema|unit|family|label)"
    r"|\b(?:merged|unified|combined|consolidated)\s+(?:in)?to\s+(?:a\s+|one\s+|the\s+|our\s+)?"
    r"(?:single\s+|one\s+|same\s+)?(?:class|schema|unit|label|table|regularit(?:y|ies))"
    r"|\bunified\s+under\s+(?:one|a\s+single|the\s+same)\s+(?:label|class|schema)"
    # "treat/use/keep/regard/cover/take X as one class"
    r"|\b(?:treat|treats|treated|regard|regards|regarded|use[sd]?|keeps?|kept|take[s]?|taken|"
    r"cover[s]?|adopt(?:s|ed)?|hold|holds|held|call(?:s|ed)?)\b[^.;]{0,50}?"
    r"\bas\s+(?:one|a\s+single|the\s+same)\b"
    # possessive/design/unit predication
    rf"|{_UNITY_HEAD}\s+(?:is|are|was|were|becomes?|should\s+be)\s+"
    r"(?:the\s+|our\s+|a\s+)?(?:right|chosen|adopted|canonical|only|correct|single|one)\b"
    rf"|{_UNITY_HEAD}\s+(?:is|are)\s+our\s+(?:unit|design)\b"
    rf"|(?:is|are)\s+our\s+(?:adopted|canonical)\s+design\b"
    r"|\bmatches?\s+our\s+(?:adopted|canonical)\s+design\b"
    r"|\bonly\s+case\s+we\s+consider\b"
    r"|\bchosen\s+unit\b"
    r"|\b(?:our|the)\s+adopted\s+design\b"
    # verbs that take the unity head as direct object
    rf"|\b(?:covers?|uses?|adopts?|keeps?|treats?|regards?|merges?|unifies|combines?|"
    rf"constitutes?|forms?|defines?|creates?|drops?)\s+(?:the\s+|a\s+|our\s+|this\s+)?"
    rf"(?:{_UNITY_HEAD}|{_UNITY_HEAD_PRE})"
    rf"|^(?:the\s+|a\s+|our\s+)?(?:{_UNITY_HEAD}|{_UNITY_HEAD_PRE})\s*$",
    re.I)

# negation whose scope is separation -> unity (structural double-negation)
_NEG_SPLIT_ASSERT = re.compile(
    r"\b(?:do\s+not|don't|does\s+not|never|must\s+not|should\s+not|shall\s+not|refuse[sd]?\s+to)\s+"
    r"(?:split|separate|distinguish)\b"
    r"|\b(?:are|is|were|was)\s+not\s+(?:separate|distinct)\b"
    r"|\bnot\s+a\s+distinction\s+(?:we|that\s+we)\s+keep\b"
    r"|\brather\s+than\s+separat"
    r"|\bas\s+opposed\s+to\s+a\s+split\b"
    r"|\bnot\s+the\s+case\s+that\b[^.;]{0,60}?\b(?:separate|distinct)\b"
    r"|\b(?:never|not)\s+(?:wrong|incorrect|false|untrue|a\s+mistake)\s+to\s+(?:say|claim|assert|hold|state)\b"
    r"|\bno\s+(?:false\s+positive|objection|caveat)\b[^.;:!?]{0,30}?[:;,]"
    r"|\bthere\s+is\s+no\s+(?:remaining\s+)?doubt\b"
    r"|\bno\s+remaining\s+doubt\b", re.I)

# negation of the merge itself -> mention
_NEG_MERGE = re.compile(
    r"\bno\s+(?:genuine\s+|new\s+|remaining\s+|actual\s+|real\s+|possible\s+)?"
    r"(?:c0/c2|c2/c0|composite\s+)?\s*merge\b"
    r"|\bnon[- ]merge\b"
    r"|\bnot\s+(?:a\s+|the\s+)?merge\b"
    r"|\b(?:are|is|were|was)\s+not\s+(?:one|a\s+single|the\s+same)\s+(?:class|schema|label|unit)\b"
    r"|\bmerge\b[^.;]{0,40}?\b(?:rejected|denied|refuted|dismissed|false)\b"
    r"|\bno\s+(?:new\s+)?class\s+is\s+created\b"
    r"|\bnew\s+class\s+is\s+not\s+created\b", re.I)

# meta/reporting/rejecting frames -> the embedded unity clause is a mention
_META_FRAME = re.compile(
    r"\bquestion\s+whether\b|\bwhether\b[^.;]{0,60}?\b(?:answered|resolved|decided)\b"
    r"|\banswered\s+in\s+the\s+negative\b|\banswers?\s+no\b"
    r"|\b(?:rejects?|rejected|den(?:y|ies|ied)|refut(?:e|es|ed)|dismiss(?:es|ed)?|"
    r"question(?:s|ed)?|audit(?:s|ed)?|discuss(?:es|ed)?|mention(?:s|ed)?|"
    r"describe(?:s|d)?|report(?:s|ed)?|quote(?:s|d)?|quoting|flag(?:s|ged)?|label(?:s|led)?|"
    r"mislabels?|count(?:s|ed)?|match(?:es|ed)?|reads?|reading)\b"
    r"[^.;]{0,45}?\b(?:claim|assertion|statement|finding|reading|pattern|question|proposal|"
    r"merge|class|schema|test|string|phrase|token|text|region|output|record|file|note|"
    r"disposition|design)\b"
    r"|\b(?:claim|assertion|statement|finding|question|reading|pattern|proposal|disposition|"
    r"false\s+positive|false\s+composite)\s+that\b"
    r"|\b(?:finding|claim|assertion|question|reading|pattern|proposal|disposition)\b"
    r"[^.;]{0,35}?\b(?:is|are|was|were)\s+(?:rejected|denied|refuted|dismissed|false)\b"
    r"|\b(?:detector|checker|gate|scan|probe|census|corpus|fixture|regex|rule|pattern|label|"
    r"flag|finding)\b[^.;:!?]{0,40}?\b(?:matches?|flags?|fires?|catches|suppresses|"
    r"reports?|quotes?|labels?|describes?)\b"
    r"|\bTC-[A-Z0-9-]+\b"
    r"|\b(?:retired|stale|irrelevant|so-called|moved|components)\b"
    r"|\b(?:split|separate|distinct|separation|leakage|hygiene)\b(?!\s+(?:is|are)\s+(?:not|never))"
    r"|\b0\s+(?:genuine\s+)?(?:assertions?|claims?|findings?|instances?)\b"
    r"|\b(?:no|zero)\s+(?:genuine\s+)?(?:assertions?|claims?|findings?|instances?)\b", re.I)

_QUOTE_OPEN = {'"': '"', "'": "'", "\u201c": "\u201d", "\u2018": "\u2019", "\u00ab": "\u00bb"}


def quoted_spans(t: str):
    spans = []
    for a, b in (('"', '"'), ("'", "'"), ("\u201c", "\u201d"), ("\u2018", "\u2019"), ("\u00ab", "\u00bb")):
        for m in re.finditer(re.escape(a) + r".*?" + re.escape(b), t, re.S):
            if a == "'":
                prev = t[m.start() - 1] if m.start() > 0 else " "
                if prev.isalnum():
                    continue  # apostrophe, not an opening quote
            spans.append((m.start(), m.end()))
    return spans


def _in_spans(pos: int, spans) -> bool:
    return any(a <= pos < b for a, b in spans)


def split_clauses(sent: str):
    parts, buf, depth, quote, i = [], [], 0, None, 0
    while i < len(sent):
        ch = sent[i]
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = None
            i += 1
            continue
        if ch in _QUOTE_OPEN:
            quote = _QUOTE_OPEN[ch]
            buf.append(ch)
            i += 1
            continue
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth = max(0, depth - 1)
        if depth == 0 and ch in ";:!?":
            parts.append("".join(buf)); buf = []; i += 1; continue
        if depth == 0 and ch == ".":
            if i + 1 >= len(sent) or (sent[i + 1] == " " and i + 2 < len(sent) and sent[i + 2].isupper()):
                parts.append("".join(buf)); buf = []; i += 1; continue
        if depth == 0 and ch == ",":
            rest = sent[i + 1:].lstrip()
            if re.match(r"(?:but|yet|so|whereas|while|although|though|then|and\s+(?:then|now|we|the|c0|c2|adopted|one))\b",
                        rest, re.I):
                parts.append("".join(buf)); buf = []; i += 1; continue
        buf.append(ch); i += 1
    parts.append("".join(buf))
    return [p.strip() for p in parts if p.strip()]


def split_sentences(text: str):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]


# ---------------------------------------------------------------- decision
def classify_text(text: str, mode: str = "prose"):
    """Return a list of (decision, reason, clause) where decision in {'fire','silent'}."""
    t = norm(text)
    out = []
    spans = quoted_spans(t)
    for sent in split_sentences(t):
        if not sent:
            continue
        sent_composite = bool(COMPOSITE.search(sent))
        sent_has_quoted_composite = any(_in_spans(m.start(), spans) for m in COMPOSITE.finditer(sent))
        if not sent_composite and not sent_has_quoted_composite:
            continue
        if _NEG_SPLIT_ASSERT.search(sent):
            out.append(("fire", "negated-separation asserts unity", sent)); continue
        clauses = split_clauses(sent)
        for ci, cl in enumerate(clauses):
            hits = list(COMPOSITE.finditer(cl))
            antecedent = False
            if not hits and sent_composite and re.search(
                    r"\b(?:they|these|those|the\s+two|both)\b", cl, re.I):
                antecedent = True  # intra-sentential anaphora to a composite earlier in the sentence
            if not hits and not antecedent:
                continue
            if hits and all(_in_spans(m.start(), spans) for m in hits):
                if re.search(r"\b(?:we|i)\s+(?:agree|adopt|hold|keep)\b|\bdecision\s+that\b", cl, re.I):
                    out.append(("fire", "quoted content with explicit endorsement", cl))
                else:
                    out.append(("silent", "composite inside a quotation span", cl))
                continue
            if re.search(r"^\s*(?:is|are|does|do|can|should|what|why|how|whether)\b", cl, re.I) or cl.endswith("?"):
                out.append(("silent", "interrogative clause", cl)); continue
            if _NEG_MERGE.search(cl):
                out.append(("silent", "negation scoped to the merge predicate", cl)); continue
            if _META_FRAME.search(cl):
                out.append(("silent", "matrix/meta frame places the unity clause in mention scope", cl)); continue
            if _UNITY_PRED.search(cl):
                out.append(("fire", "unity predicate in the clause", cl)); continue
            # declaration mode: a bare composite in an asserted field is a leak
            if mode == "declaration" and hits:
                out.append(("fire", "bare composite in a declaration surface", cl)); continue
            out.append(("silent", "no unity predicate in the clause", cl))
    return out


def findings_for_text(text: str, where: str, mode: str = "prose") -> list:
    out = []
    if not text:
        return out
    for dec, reason, cl in classify_text(str(text), mode=mode):
        if dec == "fire":
            out.append(f"CLASSSEP-STRUCT: {reason} in {where}: ...{cl.strip()[:150]!r}")
    # unknown class tokens stay soft, as in the canonical detector
    for tok in re.findall(r"AF-[A-Z0-9]+-[A-Z0-9]+-[A-Z0-9]+-[A-Z0-9]+", norm(text).upper()):
        if tok not in KNOWN_CLASSES:
            out.append(f"CLASSSEP-SOFT: unknown class token in {where}: {tok!r}")
    return out


DECLARATION_KEYS = {
    "label", "title", "class_id", "class_ids", "conclusion", "conclusion_type",
    "notes", "purpose", "scope", "scope_statement", "direction", "event",
    "statement", "declared_selector", "regularity", "regularity_token", "family",
}


def findings(obj, where: str, mode: str = "declaration") -> list:
    out = []
    if not isinstance(obj, dict):
        return out
    for key, val in obj.items():
        if key not in DECLARATION_KEYS:
            continue
        if isinstance(val, str):
            out += findings_for_text(val, f"{where}.{key}", mode=mode)
        elif isinstance(val, list):
            for i, v in enumerate(val):
                if isinstance(v, str):
                    out += findings_for_text(v, f"{where}.{key}[{i}]", mode=mode)
    return out


def findings_for_map(m: dict) -> list:
    out = []
    for gi, g in enumerate(m.get("groups", [])):
        if isinstance(g.get("direction"), str):
            out += findings_for_text(g["direction"], f"groups[{g.get('id', gi)}].direction", mode="prose")
        for n in g.get("nodes", []):
            out += findings(n, f"node {n.get('id', '?')}", mode="declaration")
    for i, ev in enumerate(m.get("portfolio_events", [])):
        if isinstance(ev, dict):
            out += findings(ev, f"portfolio_events[{i}]", mode="declaration")
    for i, c in enumerate(m.get("claims", [])):
        if isinstance(c, dict):
            out += findings(c, f"claims[{i}]", mode="prose")
    return out


def regression(corpus_dir=None) -> dict:
    root = Path(__file__).resolve().parents[3]
    corpus = Path(corpus_dir) if corpus_dir else root / "artifacts/worker-07/class_separation_falsification"
    res = json.loads((corpus / "results.json").read_text())
    tp = fn = tn = fp = 0
    rows = []
    for fx in res["fixtures"]:
        fpth = root / fx["fixture_path"]
        if not fpth.exists():
            rows.append({"id": fx["id"], "class": "MISSING"}); continue
        m = json.loads(fpth.read_text())
        det = findings_for_map(m)
        for g in m.get("groups", []):
            for n in g.get("nodes", []):
                art = n.get("artifact")
                if art and (root / art).is_file():
                    det += findings_for_text((root / art).read_text(errors="replace"), f"artifact {art}")
        got, truth = bool(det), bool(fx["is_class_merge"])
        if truth and got:
            tp += 1; cls = "TP"
        elif truth and not got:
            fn += 1; cls = "FN"
        elif not truth and got:
            fp += 1; cls = "FP"
        else:
            tn += 1; cls = "TN"
        rows.append({"id": fx["id"], "class": cls, "first": det[0][:120] if det else ""})
    return {"tp": tp, "fn": fn, "tn": tn, "fp": fp,
            "verdict": "PASS" if fn == 0 and fp == 0 else "DEFECTIVE",
            "corpus_size": tp + fn + tn + fp, "rows": rows}


def extract_assertion_mention_fixtures(path: Path):
    """Side-effect-free extraction of the audit-authored corpus C tuple list."""
    tree = ast.parse(Path(path).read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "ASSERTION_MENTION_FIXTURES" for t in node.targets):
            return ast.literal_eval(node.value)
    raise RuntimeError("ASSERTION_MENTION_FIXTURES not found")
