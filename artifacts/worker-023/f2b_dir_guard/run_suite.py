#!/usr/bin/env python3
"""Run the frozen W023-F2B-DIR-GUARD-01 suite and write evidence/results.json.

Controls (all expectations pre-registered in fixtures/MANIFEST.json):
  * direction lint on the live C0 / C2 / WCC schemas: no inversion, WCC not applicable;
  * direction lint catches the two circulating inverted repair candidates (f03/f04);
  * direction lint clears both staged corrected candidates (f05/f06);
  * mutants m07..m11 calibrate nonsense / negation / reversal / arrow / unknown-label;
  * the canonical gate is executed on every fixture as a blindness control: it passes the
    inverted candidates, which is why this predicate is proposed.

    python3 run_suite.py       # exit 0 iff every pre-registered expectation holds
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
EV = HERE / "evidence"
TZ = timezone(timedelta(hours=8))
NOW = lambda: datetime.now(TZ).isoformat(timespec="seconds")  # noqa: E731

sys.path.insert(0, str(HERE))
from containment_direction_lint import scan_path  # noqa: E402


def gate(path):
    r = subprocess.run([sys.executable, str(ROOT / "artifacts/formulation/tools/check_class_schema.py"),
                        "--json", str(path)], capture_output=True, text=True)
    return {"rc": r.returncode, "stdout": r.stdout[-400:], "stderr": r.stderr[-200:]}


def main() -> int:
    man = json.loads((FIX / "MANIFEST.json").read_text())
    expect = {
        "f00_live_c0": {"inverted": 0},
        "f01_live_c2": {"inverted": 0},
        "f02_live_wcc": {"applicable": False, "inverted": 0},
        "f03_repair_066": {"inverted": 1},
        "f04_composed_044": {"inverted": 1},
        "f05_corrected_023": {"inverted": 0},
        "f06_corrected_080": {"inverted": 0},
    }
    for name, spec in man["mutants"].items():
        expect[name] = dict(spec["expect"])
    expect["m07_nonsense"] = {"inverted": 0, "unclassified_contains": "banana"}
    expect["m08_negated"] = {"inverted": 0, "neutral_present": True}
    expect["m09_reversed_corrected"] = {"inverted": 1}
    expect["m10_arrow_inverted"] = {"inverted": 1}
    expect["m11_unsupported_label"] = {"inverted": 0, "unsupported": 1}

    checks, reports = [], {}
    for name in list(man["fixtures"]) + list(man["mutants"]):
        rep = scan_path(FIX / f"{name}.yaml")
        reports[name] = rep
        got = {
            "inverted": rep["inverted_count"],
            "unsupported": rep["unsupported_count"],
            "applicable": rep["applicable"],
            "neutral_present": any(c["verdict"] == "neutral" for c in rep["claims"]),
            "unclassified_contains": " ".join(
                u.get("text") or u["excerpt"] for u in rep["unclassified_strings"]),
        }
        for key, want in expect.get(name, {}).items():
            if key == "unclassified_contains":
                ok = str(want) in got[key]
            else:
                ok = got.get(key) == want
            checks.append({"fixture": name, "key": key, "expected": want,
                           "observed": got.get(key), "pass": ok})
        g = gate(FIX / f"{name}.yaml")
        reports[name]["canonical_gate"] = g
        reports[name]["canonical_gate_passed"] = (g["rc"] == 0)

    # explicit blindness control: the canonical gate passes both inverted candidates
    for name in ("f03_repair_066", "f04_composed_044"):
        checks.append({"fixture": name, "key": "canonical_gate_blind_rc0",
                       "expected": True, "observed": reports[name]["canonical_gate_passed"],
                       "pass": reports[name]["canonical_gate_passed"]})
    # lint exit codes are the CLI contract
    for name in ("f03_repair_066", "f05_corrected_023", "m09_reversed_corrected"):
        r = subprocess.run([sys.executable, str(HERE / "check_containment_direction.py"),
                            "--json", str(FIX / f"{name}.yaml")], capture_output=True)
        want = 1 if reports[name]["inverted_count"] else 0
        checks.append({"fixture": name, "key": "cli_exit", "expected": want,
                       "observed": r.returncode, "pass": r.returncode == want})

    passed = sum(1 for c in checks if c["pass"])
    out = {
        "task_id": "W023-F2B-DIR-GUARD-01",
        "actor": "worker-023",
        "created_at": NOW(),
        "verdict": "PASS" if passed == len(checks) else "FAIL",
        "checks_passed": passed,
        "checks_total": len(checks),
        "checks": checks,
        "reports": reports,
        "summary": {n: {"inverted": r["inverted_count"], "unsupported": r["unsupported_count"],
                        "applicable": r["applicable"],
                        "canonical_gate_rc": r["canonical_gate"]["rc"]}
                    for n, r in reports.items()},
        "falsifier": ("Any pre-registered expectation flipping on the pinned fixture hashes, or "
                      "the lint failing to flag f03/f04 while flagging f05/f06, voids the packet; "
                      "a hash move on any pinned input voids it."),
    }
    EV.mkdir(exist_ok=True)
    (EV / "results.json").write_text(json.dumps(out, indent=2, sort_keys=True))
    print(f"suite: {passed}/{len(checks)} {'PASS' if passed == len(checks) else 'FAIL'}")
    for c in checks:
        if not c["pass"]:
            print("  FAIL", c)
    return 0 if passed == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
