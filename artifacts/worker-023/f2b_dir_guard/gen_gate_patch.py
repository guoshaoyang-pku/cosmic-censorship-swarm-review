#!/usr/bin/env python3
"""Build the proposed R31 gate hook, its diff, and an isolated sandbox copy.

PROPOSAL ONLY: the canonical checker at
`artifacts/formulation/tools/check_class_schema.py` (FROZEN rev29 pin
`000e09e46b2fb4abc047c21e99165cbc55692f3132744fb27e84645609263aff`) is read, never
written. Its patched copy lives under ./sandbox/formulation/tools/ so the hook can be
executed and calibrated. Adopting the hook changes the frozen instrument hash and voids
the rev29 pin until lead-formulation + controller re-freeze; that call is not this
worker's.

    python3 gen_gate_patch.py     # writes sandbox/, proposed_gate_hook_R31.diff
"""
from __future__ import annotations

import difflib
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
SB = HERE / "sandbox" / "formulation"
PIN = "000e09e46b2fb4abc047c21e99165cbc55692f3132744fb27e84645609263aff"
ANCHOR = "        # R07 genericity\n"

HOOK = '''        # R31 containment/entailment direction (PROPOSED, W023-F2B-DIR-GUARD-01).
        # R06 certifies that regularity.must_not_conflate is present and non-empty; it does
        # not certify that its sentences agree with this file's own implication_ledger.
        # Measured: an inverted H1/H2 repair clause passes R06 (worker-023 review, worker-080
        # audit).  Fail closed if the predicate module cannot run.
        try:
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            import containment_direction_lint as _cdl
            _dirrep = _cdl.scan_document(d)
            for _c in _dirrep.get("claims", []):
                if _c.get("verdict") == "inverted":
                    self.fail("R31", "direction-reversed slot content at %s: required %r, "
                                     "sentence %r [W023F-DIR]" % (_c.get("slot"),
                                                                 _c.get("required_edge"),
                                                                 _c.get("excerpt", "")[:110]))
        except Exception as _e:  # noqa: BLE001 - a broken direction lint must not pass
            self.fail("R31", "containment_direction_lint error: %s" % _e)
'''


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def main() -> int:
    live = ROOT / "artifacts/formulation/tools/check_class_schema.py"
    orig = live.read_bytes()
    if sha(orig) != PIN:
        print(f"PIN DRIFT: live checker {sha(orig)[:12]} != FROZEN rev29 pin {PIN[:12]}")
        return 2
    frozen = json.loads((ROOT / "artifacts/formulation/FROZEN.json").read_text())
    fpin = frozen["files"]["artifacts/formulation/tools/check_class_schema.py"]["sha256"]
    if fpin != PIN:
        print(f"FROZEN.json disagrees: {fpin[:12]} != {PIN[:12]}")
        return 2
    text = orig.decode()
    if text.count(ANCHOR) != 1:
        print(f"ANCHOR MISS: {text.count(ANCHOR)} occurrences of {ANCHOR!r}")
        return 2
    patched = text.replace(ANCHOR, HOOK + ANCHOR, 1)

    if SB.exists():
        shutil.rmtree(SB)
    (SB / "tools").mkdir(parents=True)
    shutil.copyfile(ROOT / "artifacts/formulation/rule_spec.json", SB / "rule_spec.json")
    shutil.copyfile(ROOT / "artifacts/formulation/KEY_MANIFEST.json", SB / "KEY_MANIFEST.json")
    (SB / "tools/check_class_schema.py").write_text(patched)
    for name in ("containment_direction_lint.py", "check_containment_direction.py"):
        shutil.copyfile(HERE / name, SB / "tools" / name)

    diff = "".join(difflib.unified_diff(
        orig.decode().splitlines(keepends=True), patched.splitlines(keepends=True),
        fromfile="a/artifacts/formulation/tools/check_class_schema.py",
        tofile="b/artifacts/formulation/tools/check_class_schema.py", n=3))
    (HERE / "proposed_gate_hook_R31.diff").write_text(diff)

    # prove the proposal applies to the live bytes without writing them
    dry = subprocess.run(["patch", "-p1", "--dry-run", "-i", str(HERE / "proposed_gate_hook_R31.diff")],
                         cwd=ROOT, capture_output=True, text=True)
    print(f"patch --dry-run rc={dry.returncode}: {dry.stdout.strip().splitlines()[:2]}")
    if dry.returncode != 0:
        return 2
    print(f"patched sandbox checker: {sha(patched.encode())[:12]} ({len(patched)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
