#!/usr/bin/env python3
"""W098-CLASSSEP-MENTION-SCOPE-01 candidate v3 builder (two measured v2 rule fixes).

v1 -> v2 fixed D1-D6 (idiom boundary, contrast span, mention/quoted spans, sentence-scoped
assertion, zero-count negation, re-assert vs the live skip). v2 measured two remaining
rule-implementation defects:
  D7 _W098_IDIOM still lacked the leading \\s* so 'no question that ...' (AX5) was over-suppressed
  D8 the ctx assertion word must lie in the composite's CLAUSE, not merely its sentence; a
     semicolon-separated earlier clause carrying 'merged file' (claim 144) or a leftmost
     'merge' before the clause (claim 276) still forced a finding.

Derives from the same live canonical by insertion only. Writes candidate_class_separation.v3.py.
"""
from __future__ import annotations

import difflib
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
LIVE = ROOT / "research_map/class_separation.py"
OUT = HERE / "candidate_class_separation.v3.py"

HELPERS = '''
# ---- W098-CLASSSEP-MENTION-SCOPE-01 candidate v3: prose-only, clause-scoped guards ----
# Inserted block. Prose mode only; declaration mode is unchanged from the live detector.
_W098_TERM = ".!?;"
_W098_SENT = ".!?"
_W098_NEG = re.compile(r"(?<![A-Za-z])(?:no|not|never|without|zero|absent|nor|none)(?![A-Za-z])", re.I)
_W098_ZERO = re.compile(r"\\b0\\s+(?:of|out\\s+of)\\b|"
                        r"\\b0\\s+(?:\\w+\\s+){0,2}(?:assertions?|claims?|declarations?|statements?|findings?)\\b", re.I)
_W098_CANCEL = re.compile(r"\\b(?:but|however|yet|although|though|nevertheless|instead|rather|"
                          r"on\\s+the\\s+contrary|in\\s+fact)\\b", re.I)
_W098_IDIOM = re.compile(r"\\s*(?:,\\s*\\S|only\\b|just\\b|merely\\b|doubt\\b|question\\b|surprise\\b|"
                         r"accident\\b|wonder\\b|longer\\b)", re.I)
_W098_CONTRAST_TAIL = re.compile(r"(?:rather\\s+than|instead\\s+of|as\\s+opposed\\s+to|"
                                 r"not\\s+(?:only|just|merely))\\s+(?:\\S+\\s+){0,5}$", re.I)
_W098_SPLIT_FIX = re.compile(r"split|separat|distinction|leakage|hygiene|two\\s+(?:separate\\s+)?classes", re.I)
_W098_REJECT = re.compile(r"rejected\\s+hypothesis|as\\s+a\\s+hypothesis|not\\s+proposed|"
                          r"never\\s+proposed|hypothetical", re.I)
_W098_MENTION_OBJ = re.compile(
    r"(?:(?:bare|literal|quoted|token|pattern|regex|regexp|phrase|expression|string|label)\\s+(?:\\S+\\s+){0,1}"
    r"|(?:mention|discussion|occurrence|instance|use)s?\\s+of\\s+(?:the\\s+)?)$", re.I)
_W098_MENTION_FRAME = re.compile(
    r"(?:pattern|regex|regexp|scanner|detector|matcher|token|string|phrase|expression|label)\\b"
    r"[^.;!?]{0,48}?\\b(?:match(?:es|ed|ing)?|flag(?:s|ged|ging)?|scan(?:s|ned|ning)?|"
    r"detect(?:s|ed|ing)?|covers?|covered|recogni[sz]e[sd]?|spell(?:s|ed|ing)?|"
    r"looks?\\s+for|searches?\\s+for|appears?|occurs?|shows?\\s+up)\\b", re.I)
_W098_ASSERT_TAIL = re.compile(
    r"\\b(?:are|is|as)\\s+one\\b|one\\s+class|single\\s+class|same\\s+class|merged\\s+into|"
    r"unified\\s+into|treat(?:s|ed)?\\s+as\\s+one|chosen\\s+unit|right\\s+unit|unit\\s+of\\s+analysis", re.I)
_W098_QUOTE = "\\"'\\u2018\\u2019\\u201c\\u201d`"


def _w098_span(t, a, b, terms):
    lo = 0
    for c in terms:
        i = t.rfind(c, 0, a)
        if i + 1 > lo:
            lo = i + 1
    hi = len(t)
    for c in terms:
        i = t.find(c, b)
        if i != -1 and i < hi:
            hi = i
    return lo, hi


def _w098_clause_of(t, a, b):
    return _w098_span(t, a, b, _W098_TERM)


def _w098_sentence_of(t, a, b):
    return _w098_span(t, a, b, _W098_SENT)


def _w098_quoted(pre, post):
    if not re.search(r"[" + _W098_QUOTE + r"]\\s*(?:\\S+\\s+){0,3}$", pre):
        return False
    return bool(re.match(r"(?:\\s+\\S+){0,4}\\s*[" + _W098_QUOTE + r"]", post))


def _w098_prose_skip(t, m, assert_abs):
    """True => suppress this composite match (prose mode only)."""
    clo, chi = _w098_clause_of(t, m.start(), m.end())
    slo, shi = _w098_sentence_of(t, m.start(), m.end())
    in_clause = assert_abs is not None and clo <= assert_abs < chi
    ap = assert_abs if in_clause else m.start()
    if not in_clause:
        return True  # the only assertion word found lies outside this clause: a mention
    clause = t[clo:chi]
    pre, pre_comp = t[clo:ap], t[clo:m.start()]
    if _w098_quoted(t[slo:m.start()], t[m.end():shi]):
        return True
    if _W098_CONTRAST_TAIL.search(pre):
        return True
    if _W098_ZERO.search(pre):
        return True
    for nm in _W098_NEG.finditer(pre):
        tail = pre[nm.end():]
        if _W098_IDIOM.match(tail) or _W098_CANCEL.search(tail):
            continue
        return True
    sm = _W098_SPLIT_FIX.search(clause)
    if sm and not _W098_CANCEL.search(clause[sm.end():]):
        return True
    rm = _W098_REJECT.search(clause)
    if rm and not _W098_CANCEL.search(clause[rm.end():]):
        return True
    if _W098_MENTION_OBJ.search(pre_comp):
        return True
    fm = _W098_MENTION_FRAME.search(clause)
    if fm and not _W098_ASSERT_TAIL.search(clause[fm.end():]):
        return True
    return False


def _w098_force_assert(t, m, assert_abs):
    """True => the live meta-quotation skip must not swallow a first-order assertion."""
    if _w098_prose_skip(t, m, assert_abs):
        return False
    slo, shi = _w098_sentence_of(t, m.start(), m.end())
    ap = assert_abs if (assert_abs is not None and slo <= assert_abs < shi) else m.start()
    return bool(_W098_ASSERT_TAIL.search(t[ap:shi]))
# ---- end W098 inserted block ----


'''

FORCE = ('            if mode == "prose" and _w098_force_assert(t, m, lo + assert_match.start()):\n'
         '                out.append(f"CLASSSEP: composite C0/C2 asserted as one class in {where}: ...{ctx.strip()!r}")\n'
         '                continue\n')

GUARD = ('            if mode == "prose" and _w098_prose_skip(t, m, lo + assert_match.start()):\n'
         '                continue\n')

ANCHOR_HELPERS = "def _scan_composite(text: str, where: str, out: list, mode: str = \"declaration\"):"
ANCHOR_GUARD = ('            if re.search(r"false[- ]positive|non[- ]merge|not\\s+(?:a\\s+)?merge|'
                'no\\s+genuine\\s+(?:c0/c2|c2/c0)\\s+merge|detector\\s+(?:finding|flag)|'
                'quote(?:d|s)?\\s+(?:the\\s+)?detector", ctx, re.I):\n                continue\n')


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main() -> int:
    live_text = LIVE.read_text()
    assert live_text.count(ANCHOR_HELPERS) == 1, "helper anchor not unique"
    assert live_text.count(ANCHOR_GUARD) == 1, "guard anchor not unique"

    cand = live_text.replace(ANCHOR_HELPERS, HELPERS + ANCHOR_HELPERS, 1)
    cand = cand.replace(ANCHOR_GUARD, FORCE + ANCHOR_GUARD + GUARD, 1)
    OUT.write_text(cand)

    diff = list(difflib.unified_diff(live_text.splitlines(keepends=True),
                                     cand.splitlines(keepends=True), n=2))
    removed = [l for l in diff if l.startswith("-") and not l.startswith("---")]
    added = [l for l in diff if l.startswith("+") and not l.startswith("+++")]

    spec = importlib.util.spec_from_file_location("w098_candidate_v3_build", OUT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["w098_candidate_v3_build"] = mod
    spec.loader.exec_module(mod)

    manifest = {
        "task_id": "W098-CLASSSEP-MENTION-SCOPE-01",
        "version": "v3",
        "built_at": "2026-09-12T00:59:00+08:00",
        "base_live": "research_map/class_separation.py",
        "base_live_sha256": sha(LIVE),
        "candidate_path": "artifacts/worker-098/classsep_mention_scope/candidate_class_separation.v3.py",
        "candidate_sha256": sha(OUT),
        "diff": {"added_lines": len(added), "removed_lines": len(removed),
                 "insertion_only": len(removed) == 0},
        "import_ok": True,
        "post_hoc_fixes": ["D1 idiom boundary", "D2 contrast tail span", "D3 mention-object/quoted spans",
                           "D4 assert-must-be-in-clause", "D5 zero-count negation", "D6 re-assert vs live skip",
                           "D7 idiom leading-whitespace", "D8 ctx-assert clause scope"],
        "declaration_mode_touched": False,
    }
    (HERE / "build_manifest_v3.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0 if removed == [] else 1


if __name__ == "__main__":
    raise SystemExit(main())
