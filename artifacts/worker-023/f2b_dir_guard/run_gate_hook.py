#!/usr/bin/env python3
"""Execute the proposed R31 gate hook (sandbox copy) against the frozen fixture set.

Pre-registered expectations:
  * canonical checker (FROZEN rev29 pin) rc 0 on every fixture - the blindness control;
  * sandbox patched checker rc 0 on live C0/C2/WCC and both corrected candidates;
  * sandbox patched checker rc 1 (R31) on f03/f04 (the two circulating inverted repair
    candidates) and on the m09/m10 reversal mutants;
  * m11 (unknown label) stays rc 0: unsupported is a warning, not a block.

    python3 run_gate_hook.py      # writes evidence/gate_hook.json
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
FIX = HERE / "fixtures"
SB_CHECKER = HERE / "sandbox/formulation/tools/check_class_schema.py"
CANON = ROOT / "artifacts/formulation/tools/check_class_schema.py"
TZ = timezone(timedelta(hours=8))
NOW = lambda: datetime.now(TZ).isoformat(timespec="seconds")  # noqa: E731

EXPECT_PATCHED = {
    "f00_live_c0": 0, "f01_live_c2": 0, "f02_live_wcc": 0,
    "f03_repair_066": 1, "f04_composed_044": 1,
    "f05_corrected_023": 0, "f06_corrected_080": 0,
    "m07_nonsense": 0, "m08_negated": 0, "m09_reversed_corrected": 1,
    "m10_arrow_inverted": 1, "m11_unsupported_label": 0,
}


def run(checker, path):
    r = subprocess.run([sys.executable, str(checker), "--json", str(path)],
                       capture_output=True, text=True)
    failed = []
    try:
        rep = json.loads(r.stdout)
        failed = sorted({f.get("rule") for f in rep.get("failures", []) if isinstance(f, dict)})
    except Exception:  # noqa: BLE001
        pass
    return {"rc": r.returncode, "failed_rules": failed,
            "stdout_tail": r.stdout[-300:], "stderr_tail": r.stderr[-200:]}


def main() -> int:
    names = ["f00_live_c0", "f01_live_c2", "f02_live_wcc", "f03_repair_066",
             "f04_composed_044", "f05_corrected_023", "f06_corrected_080",
             "m07_nonsense", "m08_negated", "m09_reversed_corrected",
             "m10_arrow_inverted", "m11_unsupported_label"]
    checks, rows = [], {}
    for name in names:
        p = FIX / f"{name}.yaml"
        c, s = run(CANON, p), run(SB_CHECKER, p)
        rows[name] = {"canonical": c, "patched": s}
        checks.append({"fixture": name, "key": "canonical_rc", "expected": 0,
                       "observed": c["rc"], "pass": c["rc"] == 0})
        want = EXPECT_PATCHED[name]
        checks.append({"fixture": name, "key": "patched_rc", "expected": want,
                       "observed": s["rc"], "pass": s["rc"] == want})
        if want == 1:
            checks.append({"fixture": name, "key": "failed_rule_R31", "expected": ["R31"],
                           "observed": s["failed_rules"], "pass": s["failed_rules"] == ["R31"]})
    passed = sum(1 for c in checks if c["pass"])
    out = {
        "task_id": "W023-F2B-DIR-GUARD-01",
        "actor": "worker-023",
        "created_at": NOW(),
        "verdict": "PASS" if passed == len(checks) else "FAIL",
        "checks_passed": passed,
        "checks_total": len(checks),
        "checks": checks,
        "rows": rows,
        "canonical_checker_sha256": __import__("hashlib").sha256(CANON.read_bytes()).hexdigest(),
        "sandbox_checker_sha256": __import__("hashlib").sha256(SB_CHECKER.read_bytes()).hexdigest(),
        "authority": ("proposal only: the canonical checker was not modified; adopting the "
                      "diff changes the frozen instrument hash and requires lead-formulation "
                      "plus controller re-freeze"),
        "falsifier": ("Falsified if the patched sandbox checker stops failing f03/f04 or starts "
                      "failing live/corrected fixtures at the pinned hashes, or if the diff no "
                      "longer applies to the FROZEN rev29 checker bytes."),
    }
    (HERE / "evidence").mkdir(exist_ok=True)
    (HERE / "evidence/gate_hook.json").write_text(json.dumps(out, indent=2, sort_keys=True))
    print(f"gate hook: {passed}/{len(checks)} {'PASS' if passed == len(checks) else 'FAIL'}")
    for c in checks:
        if not c["pass"]:
            print("  FAIL", c)
    return 0 if passed == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
