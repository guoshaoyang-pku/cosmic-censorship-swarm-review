#!/usr/bin/env python3
"""Generate the byte-minimal repair candidate for numerics/tests/selfgravity_lock_guard.py.

W012-LOCKGUARD-FAILCLOSED-01 (class AF-WCC-SCALAR-SPH, node N1-BLOCK, gate G-NUM).

This script does not touch the canonical guard. It reads the canonical bytes, asserts the
exact substrings to be replaced occur once, applies the patch, asserts the verdict expression
at canonical line 98 is unchanged, and writes guard_candidate.py next to this file.

Run: python3 make_candidate.py
Exit 0 iff the candidate was generated from the pinned canonical hash.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
CANONICAL = REPO / "numerics" / "tests" / "selfgravity_lock_guard.py"
CANDIDATE = HERE / "guard_candidate.py"

PINNED_CANONICAL_SHA256 = (
    "7535ec84ac9ceb0b5451e4ed93ae6b03083966db47aa218eb4fba3da6627b9f5"
)

OLD_STATE = '''    lock = m.get("numerics_lock") or {}
    state = lock.get("state", "unknown")
'''

NEW_STATE = '''    lock = m.get("numerics_lock") or {}
    # Fail-closed state derivation: only the exact string ``released`` (set by the release
    # authority, astra) permits N1+ artifacts to exist.  An absent, null, miscased or
    # otherwise unrecognised state is treated as ``locked``, mirroring numerics/gates.py.
    state_key_present = "state" in lock
    raw_state = lock.get("state")
    state_recognised = raw_state in ("locked", "released")
    state = raw_state if state_recognised else "locked"
'''

OLD_DOC = '''* Exit codes: 0 = lock intact, 1 = VIOLATION, 2 = cannot evaluate (map unreadable) -- a guard
  that silently passes when it cannot read its evidence would itself be a lock bypass.
'''

NEW_DOC = '''* Exit codes: 0 = lock intact, 1 = VIOLATION, 2 = cannot evaluate (map unreadable) -- a guard
  that silently passes when it cannot read its evidence would itself be a lock bypass.
* Fail-closed state semantics: PASS requires that the lock is not closed.  The only state that
  permits a blocked-node artifact to exist is the exact string ``released``; an absent, null,
  miscased or otherwise unrecognised state is treated as ``locked``.  ``numerics_lock_state_raw``,
  ``state_key_present`` and ``state_recognised`` report the original value so a malformed map is
  visible.
'''

OLD_REPORT = '''        "numerics_lock_state": state,
'''

NEW_REPORT = '''        "numerics_lock_state": state,
        "numerics_lock_state_raw": raw_state,
        "state_key_present": state_key_present,
        "state_recognised": state_recognised,
'''

UNCHANGED_VERDICT_LINE = '        "verdict": "FAIL" if (state == "locked" and violations) else "PASS",\n'


def main() -> int:
    src_bytes = CANONICAL.read_bytes()
    measured = hashlib.sha256(src_bytes).hexdigest()
    if measured != PINNED_CANONICAL_SHA256:
        print(f"REFUSE: canonical sha256 {measured} != pinned {PINNED_CANONICAL_SHA256}")
        return 2
    src = src_bytes.decode("utf-8")

    for name, old in (("state", OLD_STATE), ("doc", OLD_DOC), ("report", OLD_REPORT)):
        n = src.count(old)
        if n != 1:
            print(f"REFUSE: anchor '{name}' occurs {n} times (need exactly 1)")
            return 2

    out = src.replace(OLD_STATE, NEW_STATE).replace(OLD_DOC, NEW_DOC).replace(OLD_REPORT, NEW_REPORT)

    if out.count(UNCHANGED_VERDICT_LINE) != 1:
        print("REFUSE: verdict expression changed or duplicated")
        return 2

    CANDIDATE.write_text(out, encoding="utf-8")
    print(f"canonical_sha256={measured}")
    print(f"candidate_path={CANDIDATE.relative_to(REPO)}")
    print(f"candidate_sha256={hashlib.sha256(out.encode('utf-8')).hexdigest()}")
    print(f"candidate_bytes={len(out.encode('utf-8'))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
