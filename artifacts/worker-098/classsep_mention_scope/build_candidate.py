#!/usr/bin/env python3
"""W098-CLASSSEP-MENTION-SCOPE-01 candidate builder.

Derives a shadow detector from the LIVE canonical research_map/class_separation.py by
insertion only: one helper block before `_scan_composite`, one guard call inside the
assertion branch. Asserts (a) every anchor occurs exactly once, (b) the unified diff has
zero removed lines, (c) the result imports. Writes candidate_class_separation.py plus
build_manifest.json (hashes + diff stats + anchor offsets). Read-only on canonical files.
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
OUT = HERE / "candidate_class_separation.py"

HELPERS = '''
# ---- W098-CLASSSEP-MENTION-SCOPE-01 candidate: prose-only, clause-scoped guards ----
# Inserted block. Prose mode only; declaration mode is unchanged from the live detector.
_W098_TERM = ".!?;"
_W098_NEG = re.compile(r"(?<![A-Za-z])(?:no|not|never|without|zero|absent|nor|none)(?![A-Za-z])", re.I)
_W098_CANCEL = re.compile(r"\\b(?:but|however|yet|although|though|nevertheless|instead|rather|"
                          r"on\\s+the\\s+contrary|in\\s+fact)\\b", re.I)
_W098_IDIOM = re.compile(r"\\s*(?:,\\s*\\S|only|just|merely|doubt|question|surprise|accident|wonder|longer)\\b", re.I)
_W098_CONTRAST_TAIL = re.compile(r"(?:rather\\s+than|instead\\s+of|as\\s+opposed\\s+to|"
                                 r"not\\s+(?:only|just|merely))\\s+(?:\\w+\\s+){0,4}$", re.I)
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


def _w098_clause_of(t, a, b):
    lo = 0
    for c in _W098_TERM:
        i = t.rfind(c, 0, a)
        if i + 1 > lo:
            lo = i + 1
    hi = len(t)
    for c in _W098_TERM:
        i = t.find(c, b)
        if i != -1 and i < hi:
            hi = i
    return lo, hi


def _w098_quoted(pre, post):
    if not re.search(r"[" + _W098_QUOTE + r"]\\s*(?:\\S+\\s+){0,3}$", pre):
        return False
    return bool(re.match(r"(?:\\s+\\S+){0,4}\\s*[" + _W098_QUOTE + r"]", post))


def _w098_prose_skip(t, m, assert_abs):
    """True => suppress this composite match (prose mode only)."""
    lo, hi = _w098_clause_of(t, m.start(), m.end())
    clause = t[lo:hi]
    ap = assert_abs if (assert_abs is not None and lo <= assert_abs < hi) else m.start()
    pre, post = t[lo:ap], t[m.end():hi]
    if _w098_quoted(t[lo:m.start()], post):
        return True
    if _W098_CONTRAST_TAIL.search(pre):
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
    if _W098_MENTION_OBJ.search(pre):
        return True
    fm = _W098_MENTION_FRAME.search(clause)
    if fm and not _W098_ASSERT_TAIL.search(clause[fm.end():]):
        return True
    return False
# ---- end W098 inserted block ----


'''

GUARD = ('            if mode == "prose" and _w098_prose_skip(t, m, lo + assert_match.start()):\n'
         '                continue\n')

ANCHOR_HELPERS = "def _scan_composite(text: str, where: str, out: list, mode: str = \"declaration\"):"
ANCHOR_GUARD = ('            if re.search(r"false[- ]positive|non[- ]merge|not\\s+(?:a\\s+)?merge|'
                'no\\s+genuine\\s+(?:c0/c2|c2/c0)\\s+merge|detector\\s+(?:finding|flag)|'
                'quote(?:d|s)?\\s+(?:the\\s+)?detector", ctx, re.I):\n                continue\n')


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    live_text = LIVE.read_text()
    assert live_text.count(ANCHOR_HELPERS) == 1, "helper anchor not unique"
    assert live_text.count(ANCHOR_GUARD) == 1, "guard anchor not unique"

    cand = live_text.replace(ANCHOR_HELPERS, HELPERS + ANCHOR_HELPERS, 1)
    cand = cand.replace(ANCHOR_GUARD, ANCHOR_GUARD + GUARD, 1)
    OUT.write_text(cand)

    diff = list(difflib.unified_diff(live_text.splitlines(keepends=True),
                                     cand.splitlines(keepends=True), n=2))
    removed = [l for l in diff if l.startswith("-") and not l.startswith("---")]
    added = [l for l in diff if l.startswith("+") and not l.startswith("+++")]

    spec = importlib.util.spec_from_file_location("w098_candidate_build", OUT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["w098_candidate_build"] = mod
    spec.loader.exec_module(mod)

    manifest = {
        "task_id": "W098-CLASSSEP-MENTION-SCOPE-01",
        "built_at": "2026-09-12T00:56:00+08:00",
        "base_live": "research_map/class_separation.py",
        "base_live_sha256": sha(LIVE),
        "candidate_path": "artifacts/worker-098/classsep_mention_scope/candidate_class_separation.py",
        "candidate_sha256": sha(OUT),
        "diff": {"added_lines": len(added), "removed_lines": len(removed),
                 "insertion_only": len(removed) == 0},
        "import_ok": True,
        "declaration_mode_touched": False,
        "notes": "Guard is behind mode == 'prose'; the helper block is inert for declaration mode.",
    }
    (HERE / "build_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0 if removed == [] else 1


if __name__ == "__main__":
    raise SystemExit(main())
