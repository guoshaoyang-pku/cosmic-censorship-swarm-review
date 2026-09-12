#!/usr/bin/env python3
"""Independent fail-closed probe for the N0 lock guard (worker-012, slot 012).

Runs `flat_wave.lock_guard(root=...)` in fresh subprocesses under four roots:

  positive_control  : the real repo root              -> expect N1_BLOCKED, fail_closed False
  nonexistent_root  : a path that does not exist      -> expect N1_BLOCKED, production_allowed False
  malformed_map     : temp root, symlinked numerics/  -> expect N1_BLOCKED, production_allowed False
                      + corrupt research_map.json
  missing_module    : temp root with no numerics pkg  -> expect N1_BLOCKED, production_allowed False

The child process is started with cwd=/tmp and PYTHONPATH cleared so that
`import numerics` cannot silently resolve to the real tree.

Usage: python3 probe_failclosed.py --json-out <path>
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve()
REPO = HERE.parents[3]
TESTS = REPO / "numerics" / "tests"


def child(root: str) -> dict:
    sys.path.insert(0, str(TESTS))
    import flat_wave  # noqa: E402

    return flat_wave.lock_guard(root=root)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json-out", default=None)
    ap.add_argument("--child", default=None, help="internal: evaluate one root and print JSON")
    a = ap.parse_args()
    if a.child is not None:
        print(json.dumps(child(a.child), sort_keys=True))
        return 0

    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    results = {}

    def run_case(name: str, root: str) -> dict:
        proc = subprocess.run(
            [sys.executable, str(HERE), "--child", root],
            cwd="/tmp", env=env, capture_output=True, text=True, timeout=300,
        )
        rec = {"root": root, "exit_code": proc.returncode,
               "stdout": proc.stdout.strip(), "stderr_tail": proc.stderr.strip()[-400:]}
        try:
            rec["guard"] = json.loads(proc.stdout)
        except Exception as exc:  # pragma: no cover
            rec["guard"] = None
            rec["parse_error"] = f"{type(exc).__name__}: {exc}"
        results[name] = rec
        return rec

    run_case("positive_control", str(REPO))
    run_case("nonexistent_root", "/nonexistent-root-w012-2")
    with tempfile.TemporaryDirectory(prefix="w012-probe-") as td:
        t = Path(td)
        (t / "research_map").mkdir()
        (t / "research_map" / "research_map.json").write_text("{not json")
        os.symlink(REPO / "numerics", t / "numerics")
        run_case("malformed_map", str(t))
    with tempfile.TemporaryDirectory(prefix="w012-probe-nomod-") as td:
        t = Path(td)
        (t / "research_map").mkdir()
        (t / "research_map" / "research_map.json").write_text(
            json.dumps({"numerics_lock": {"state": "locked"}, "gates": []}))
        run_case("missing_module", str(t))

    checks = {}
    for name, rec in results.items():
        g = rec.get("guard") or {}
        checks[name] = {
            "verdict": g.get("verdict"),
            "production_allowed": g.get("production_allowed"),
            "fail_closed": g.get("fail_closed"),
            "blocked": g.get("verdict") == "N1_BLOCKED",
        }
    checks["positive_control"]["expected"] = "N1_BLOCKED with fail_closed False (proves harness works)"
    for name in ("nonexistent_root", "malformed_map", "missing_module"):
        checks[name]["expected"] = "N1_BLOCKED / production_allowed False (fail closed)"
    checks["all_fail_closed"] = all(
        checks[n]["blocked"] and checks[n].get("production_allowed") is False
        for n in ("nonexistent_root", "malformed_map", "missing_module"))
    checks["positive_control_valid"] = (
        checks["positive_control"]["blocked"]
        and checks["positive_control"].get("production_allowed") is False
        and checks["positive_control"].get("fail_closed") is False)

    out = {"artifact_kind": "failclosed_probe_results", "worker": "worker-012",
           "slot": "012", "canonical_artifact": "numerics/tests/flat_wave.py",
           "cases": results, "checks": checks}
    text = json.dumps(out, indent=2, sort_keys=True)
    if a.json_out:
        Path(a.json_out).write_text(text + "\n")
        print(f"wrote {a.json_out}")
    else:
        print(text)
    return 0 if checks["all_fail_closed"] and checks["positive_control_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
