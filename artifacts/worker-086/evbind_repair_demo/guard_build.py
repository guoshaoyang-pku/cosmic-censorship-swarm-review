#!/usr/bin/env python3
"""Build the minimal non-writing guard for the frozen evidence producer.

W086-GFORM-R2-DURABILITY-01, worker-086.  Bounded, deterministic, fail-closed.

Input : artifacts/formulation/tools/check_taxonomy_consistency.py
        sha256 de356d999ea3b6aeb9cfe7d35d6604328ccc4945ead3bc3ec566a929363f31cd
Output: check_taxonomy_consistency.guarded.py  (candidate only; never canonical)
        guard.patch                           (unified diff for the owner to audit)

The guard changes exactly one behaviour: the checker no longer writes the
canonical evidence document artifacts/formulation/evidence/taxonomy_consistency.json
unless the operator passes --write explicitly.  Consistency checking and the
exit code are untouched, so the candidate is a checker, not a producer.
"""
import difflib
import hashlib
import sys
from pathlib import Path

PINNED_SHA = "de356d999ea3b6aeb9cfe7d35d6604328ccc4945ead3bc3ec566a929363f31cd"
ART = Path(__file__).resolve().parent
REPO = ART.parents[2]
PINNED = REPO / "artifacts/formulation/tools/check_taxonomy_consistency.py"

OLD_IMPORT = "import json, sys, yaml\n"
NEW_IMPORT = "import hashlib, json, sys, yaml\n"

OLD_WRITE = (
    'out = ROOT/"artifacts/formulation/evidence/taxonomy_consistency.json"\n'
    'out.write_text(json.dumps(rep, indent=2)+"\\n")\n'
)
NEW_WRITE = (
    'out = ROOT/"artifacts/formulation/evidence/taxonomy_consistency.json"\n'
    '_doc = json.dumps(rep, indent=2)+"\\n"\n'
    'if "--write" in sys.argv:\n'
    '    out.write_text(_doc)\n'
    'else:\n'
    '    _cur = out.read_text() if out.exists() else None\n'
    '    _cur_sha = hashlib.sha256(_cur.encode()).hexdigest() if _cur is not None else None\n'
    '    print("NOTE frozen-evidence guard: canonical evidence document not written"\n'
    '          f" (computed_sha256={hashlib.sha256(_doc.encode()).hexdigest()}, on_disk_sha256={_cur_sha})")\n'
)


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def build(pinned: Path = PINNED) -> dict:
    """Apply the two exact literal replacements; fail closed on any drift."""
    raw = pinned.read_bytes()
    got = sha256_bytes(raw)
    if got != PINNED_SHA:
        raise SystemExit(f"MOVING TARGET: pinned checker is {got}, expected {PINNED_SHA}")
    text = raw.decode()
    if text.count(OLD_IMPORT) != 1:
        raise SystemExit("MOVING TARGET: import line not found exactly once")
    if text.count(OLD_WRITE) != 1:
        raise SystemExit("MOVING TARGET: unconditional write block not found exactly once")
    guarded = text.replace(OLD_IMPORT, NEW_IMPORT).replace(OLD_WRITE, NEW_WRITE)
    if guarded == text:
        raise SystemExit("guard build was a no-op")
    gpath = ART / "check_taxonomy_consistency.guarded.py"
    gpath.write_text(guarded)
    diff = "".join(
        difflib.unified_diff(
            text.splitlines(keepends=True),
            guarded.splitlines(keepends=True),
            fromfile="a/artifacts/formulation/tools/check_taxonomy_consistency.py",
            tofile="b/artifacts/worker-086/evbind_repair_demo/check_taxonomy_consistency.guarded.py",
        )
    )
    (ART / "guard.patch").write_text(diff)
    return {
        "pinned_path": str(PINNED.relative_to(REPO)),
        "pinned_sha256": got,
        "guarded_path": str(gpath.relative_to(REPO)),
        "guarded_sha256": sha256_file(gpath),
        "patch_path": "artifacts/worker-086/evbind_repair_demo/guard.patch",
        "patch_sha256": sha256_file(ART / "guard.patch"),
        "replacements": [
            {"old": OLD_IMPORT.rstrip("\n"), "new": NEW_IMPORT.rstrip("\n")},
            {"old": OLD_WRITE.rstrip("\n"), "new": NEW_WRITE.rstrip("\n")},
        ],
    }


if __name__ == "__main__":
    info = build()
    print("GUARD BUILT")
    for k, v in info.items():
        if k != "replacements":
            print(f"  {k}: {v}")
    sys.exit(0)
