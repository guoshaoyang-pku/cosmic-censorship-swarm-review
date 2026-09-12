#!/usr/bin/env python3
"""Derive the calibrated stage-B auditor for FORM-PROBE-11 (single documented delta).

Reuses the FORM-PROBE-10 calibration verbatim:
  * R03 binder check: literal substring -> identifier-token test (the frozen auditor
    falsely rejects the CANONICAL WCC schema at rev28 otherwise);
  * a path rebase so the copy can live in this directory.
The frozen source is left untouched; source and calibrated hashes are both recorded.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / "spec_conformance_audit.py"
DST = HERE / "audit_calibrated_exempt11.py"

OLD = """                for b in binders:
                    if b not in formal:
                        bad.append(f"binder {b!r} absent from formal sentence")
"""
NEW = """                # [FORM-PROBE-10/11 calibration] canonical `quantifiers.formal` writes
                # multi-binder tuples in mathematical notation ("q in I+ and t0 in
                # [0,T)") rather than as the literal tuple "(q,t0)".  Require every
                # identifier of the binder entry to occur in the formal sentence.
                _ident = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
                for b in binders:
                    _missing = [t for t in _ident.findall(str(b)) if t not in formal]
                    if _missing:
                        bad.append(f"binder {b!r} tokens {_missing} absent from formal sentence")
"""
OLD_PATHS = 'DEFAULT_SPEC = ROOT / "artifacts" / "formulation" / "rule_spec.json"\n'
NEW_PATHS = ('DEFAULT_SPEC = ROOT / "artifacts" / "formulation" / "rule_spec.json"\n'
             '# [FORM-PROBE-11 calibration] path rebase: this copy lives one directory deeper.\n'
             'ROOT = HERE.parent.parent.parent\n'
             'SEMANTIC = HERE.parent / "semantic_fixtures"\n'
             'DEFAULT_SPEC = ROOT / "artifacts" / "formulation" / "rule_spec.json"\n')


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    text = SRC.read_text()
    assert text.count(OLD) == 1, "R03 block not found exactly once"
    assert text.count(OLD_PATHS) == 1, "DEFAULT_SPEC line not found exactly once"
    patched = text.replace(OLD, NEW).replace(OLD_PATHS, NEW_PATHS)
    header = ('"""CALIBRATED COPY of spec_conformance_audit.py for FORM-PROBE-11.\n\n'
              f"source: artifacts/worker-06/spec_conformance_audit.py @ {sha(SRC)}\n"
              "delta : FORM-PROBE-10 R03 binder check verbatim + path rebase. No other rule text differs.\n"
              '"""\n')
    idx = patched.index('"""', patched.index('"""') + 3) + 3
    patched = header + patched[idx:].lstrip("\n")
    orig_body = text.split('"""', 2)[2]
    new_body = patched.split('"""', 2)[2]
    assert orig_body.replace(OLD, NEW).replace(OLD_PATHS, NEW_PATHS) == new_body
    DST.write_text(patched)
    print(f"source     {sha(SRC)}")
    print(f"calibrated {sha(DST)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
