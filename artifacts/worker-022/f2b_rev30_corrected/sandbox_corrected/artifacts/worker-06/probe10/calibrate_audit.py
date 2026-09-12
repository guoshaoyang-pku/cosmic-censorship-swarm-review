#!/usr/bin/env python3
"""Derive the calibrated semantic auditor used as stage B of FORM-PROBE-10.

WHY A DERIVED COPY (not an edit of the frozen auditor):
  The frozen worker-06 auditor (spec_conformance_audit.py) rejects the CANONICAL WCC
  schema at FROZEN rev28 with a single R03 failure:

      R03: binder '(q,t0)' absent from formal sentence

  That is a literal-substring binder check (line ~210) against a canonical
  `quantifiers.formal` that writes the same binders in mathematical notation
  ("not exists q in I+ and t0 in [0,T)"), not as the tuple "(q,t0)".  The canonical
  schema passes the canonical structural gate and its quantifier block contains both
  binders, so this is a stale-auditor false positive -- exactly the layout mismatch the
  formulation lead flagged ("re-derive your rules against the canonical key layout").

DELTA (single, generic, pre-registered before any mutant is run):
  Replace the literal `b not in formal` test with an identifier-token test: every
  identifier occurring in a binder entry must occur in the formal sentence.  No rule is
  added, removed, or re-scoped.  The original file is left untouched; its sha256 and the
  calibrated copy's sha256 are both recorded in the probe report.

Usage: python3 calibrate_audit.py   (writes audit_calibrated.py, prints both hashes)
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / "spec_conformance_audit.py"
DST = HERE / "audit_calibrated.py"

OLD = """                for b in binders:
                    if b not in formal:
                        bad.append(f"binder {b!r} absent from formal sentence")
"""

NEW = """                # [FORM-PROBE-10 calibration] canonical `quantifiers.formal` writes
                # multi-binder tuples in mathematical notation ("q in I+ and t0 in
                # [0,T)") rather than as the literal tuple "(q,t0)".  Require every
                # identifier of the binder entry to occur in the formal sentence.
                _ident = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
                for b in binders:
                    _missing = [t for t in _ident.findall(str(b)) if t not in formal]
                    if _missing:
                        bad.append(f"binder {b!r} tokens {_missing} absent from formal sentence")
"""


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


OLD_PATHS = 'DEFAULT_SPEC = ROOT / "artifacts" / "formulation" / "rule_spec.json"\n'
NEW_PATHS = ('DEFAULT_SPEC = ROOT / "artifacts" / "formulation" / "rule_spec.json"\n'
             '# [FORM-PROBE-10 calibration] path rebase: this copy lives one directory deeper.\n'
             'ROOT = HERE.parent.parent.parent\n'
             'SEMANTIC = HERE.parent / "semantic_fixtures"\n'
             'DEFAULT_SPEC = ROOT / "artifacts" / "formulation" / "rule_spec.json"\n')


def main() -> int:
    text = SRC.read_text()
    if text.count(OLD) != 1:
        print(f"FAIL: expected exactly one R03 block, found {text.count(OLD)}", file=sys.stderr)
        return 1
    if text.count(OLD_PATHS) != 1:
        print(f"FAIL: expected exactly one DEFAULT_SPEC line, found {text.count(OLD_PATHS)}", file=sys.stderr)
        return 1
    patched = text.replace(OLD, NEW).replace(OLD_PATHS, NEW_PATHS)
    header = (
        '"""CALIBRATED COPY of spec_conformance_audit.py for FORM-PROBE-10.\n\n'
        f"source: artifacts/worker-06/spec_conformance_audit.py @ {sha(SRC)}\n"
        "delta : single R03 binder check, literal substring -> identifier tokens,\n"
        "         plus a path rebase for the deeper directory (both in calibrate_audit.py).\n"
        "No other rule text differs. Regenerate with: python3 calibrate_audit.py\n"
        '"""\n'
    )
    # keep the module docstring position by replacing the original header docstring end
    idx = patched.index('"""', patched.index('"""') + 3) + 3
    patched = header + patched[idx:].lstrip("\n")
    DST.write_text(patched)
    print(f"source    {SRC.name} {sha(SRC)}")
    print(f"calibrated {DST.name} {sha(DST)}")

    # sanity: the only textual difference is the R03 block and the header
    orig_body = text.split('"""', 2)[2]
    new_body = patched.split('"""', 2)[2]
    assert orig_body.replace(OLD, NEW).replace(OLD_PATHS, NEW_PATHS) == new_body, "unexpected extra diff"
    return 0


if __name__ == "__main__":
    sys.exit(main())
