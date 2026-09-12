#!/usr/bin/env python3
"""W052-A1-CLASSSEP-VACUITY-REPL-01.

Independent adversarial replication of worker-024's finding that the standing
class-separation regression instrument fails open on an incomplete corpus.

Canonical pins (re-measured at start AND end of this run; mismatch aborts):
  runtime/bin/classsep_regression.py                    9f1cf9c336be...
  research_map/class_separation.py                      c266dbceca87...
  artifacts/worker-07/.../results.json                  d69ad58468be...
  artifacts/worker-024/.../proposed_patch.diff          1a9a2f214a81...

Method is deliberately NOT worker-024's driver: one template sandbox is copied
per case, mutated in place, and the pinned runner is executed as a subprocess.
A canonical in-situ run (S0) anchors the sandbox reproduction to the real repo.
Each case is then re-run with worker-024's proposed patch applied to the sandbox
copy, so the claimed fix is validated independently of its author's harness.

Expectations are pre-registered in EXPECT; the harness exits 0 only if every
case matches. No canonical repo file is written: all mutations happen inside
artifacts/worker-052/classsep_vacuity_replication/sandbox/.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

CST = timezone(timedelta(hours=8))
HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent
SANDBOX = HERE / "sandbox"
LOGS = HERE / "logs"
TEMPLATE = SANDBOX / "template"
CASES = SANDBOX / "cases"
PATCHED = SANDBOX / "patched"
PATCH_FILE = REPO / "artifacts/worker-024/classsep_runner_vacuity/proposed_patch.diff"

RUNNER_REL = "runtime/bin/classsep_regression.py"
DETECTOR_REL = "research_map/class_separation.py"
CORPUS_REL = "artifacts/worker-07/class_separation_falsification"
TRUTH_REL = CORPUS_REL + "/results.json"

PINNED = {
    RUNNER_REL: "9f1cf9c336be874182e8882e00f7fdf8e4f6c4ea1881f11a6b3e762e038a7091",
    DETECTOR_REL: "c266dbceca87fb996bd76a774145ef511cbf2aae190d9f423167d3200783a920",
    TRUTH_REL: "d69ad58468be16655921dcf0eab9570fa6e7ccaf828558a45d4b306cce3de452",
    "artifacts/worker-024/classsep_runner_vacuity/proposed_patch.diff":
        "1a9a2f214a81503d27b798e96c3dc879480ce0fa8c11cc5039acd23ab4d740f9",
}

# case -> (expect_exit_zero, expected stdout substrings, expected VERDICT token)
EXPECT = {
    "S0_in_situ":              (True,  ["leaks detected 17/17", "controls clean 10/10"], "PASS"),
    "R0_real":                 (True,  ["leaks detected 17/17", "controls clean 10/10"], "PASS"),
    "R1_empty":                (True,  ["leaks detected 0/0", "controls clean 0/0"], "PASS"),
    "R2_missing_all":          (True,  ["leaks detected 0/0", "controls clean 0/0"], "PASS"),
    "R3_leaks_removed":        (True,  ["leaks detected 0/0", "controls clean 10/10"], "PASS"),
    "R4_summary_zeroed":       (True,  ["leaks detected 17/17", "controls clean 10/10"], "PASS"),
    "R5_controls_removed":     (True,  ["leaks detected 17/17", "controls clean 0/0"], "PASS"),
    "R6_results_absent":       (False, [], None),
    "R7_replaced_corpus":      (True,  ["leaks detected 0/0", "controls clean 1/1"], "PASS"),
    "P0_patched_real":         (True,  ["leaks detected 17/17", "controls clean 10/10"], "PASS"),
    "P1_patched_empty":        (False, ["REASON:"], "DEFECTIVE"),
    "P2_patched_missing_all":  (False, ["REASON:"], "DEFECTIVE"),
    "P3_patched_leaks_removed": (False, ["REASON:"], "DEFECTIVE"),
    "P4_patched_summary_zeroed": (False, ["REASON:"], "DEFECTIVE"),
    "P5_patched_controls_removed": (False, ["REASON:"], "DEFECTIVE"),
    "P7_patched_replaced_corpus": (True, ["leaks detected 0/0", "controls clean 1/1"], "PASS"),
}

LEAKS_RE = re.compile(r"leaks detected (\d+)/(\d+)")
CTRL_RE = re.compile(r"controls clean (\d+)/(\d+)")
VERDICT_RE = re.compile(r"VERDICT:\s*(\S+)")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def measure_pins() -> dict:
    return {rel: sha256(REPO / rel) for rel in PINNED}


def build_template() -> None:
    if TEMPLATE.exists():
        shutil.rmtree(TEMPLATE)
    (TEMPLATE / "runtime/bin").mkdir(parents=True)
    (TEMPLATE / "research_map").mkdir(parents=True)
    shutil.copy2(REPO / RUNNER_REL, TEMPLATE / RUNNER_REL)
    shutil.copy2(REPO / DETECTOR_REL, TEMPLATE / DETECTOR_REL)
    shutil.copytree(REPO / CORPUS_REL, TEMPLATE / CORPUS_REL)


def load_truth(root: Path) -> dict:
    return json.loads((root / TRUTH_REL).read_text())


def write_truth(root: Path, truth: dict) -> None:
    (root / TRUTH_REL).write_text(json.dumps(truth, indent=1, sort_keys=True) + "\n")


def mutate(root: Path, case: str) -> None:
    truth = load_truth(root)
    if case in ("R0_real", "P0_patched_real"):
        pass
    elif case in ("R1_empty", "P1_patched_empty"):
        truth["fixtures"] = []
    elif case in ("R2_missing_all", "P2_patched_missing_all"):
        for fx in truth["fixtures"]:
            fx["fixture_path"] = "artifacts/worker-07/class_separation_falsification/fixtures/__absent__" + fx["id"] + ".json"
    elif case in ("R3_leaks_removed", "P3_patched_leaks_removed"):
        truth["fixtures"] = [fx for fx in truth["fixtures"] if not fx["is_class_merge"]]
    elif case in ("R4_summary_zeroed", "P4_patched_summary_zeroed"):
        for k in ("fixtures_total", "leaks_total", "controls_total",
                  "accepted_controls", "violations_detected"):
            truth["summary"][k] = 0
    elif case in ("R5_controls_removed", "P5_patched_controls_removed"):
        truth["fixtures"] = [fx for fx in truth["fixtures"] if fx["is_class_merge"]]
    elif case == "R6_results_absent":
        (root / TRUTH_REL).unlink()
    elif case in ("R7_replaced_corpus", "P7_patched_replaced_corpus"):
        ctrl = next(fx for fx in truth["fixtures"]
                    if not fx["is_class_merge"] and fx["id"].startswith("C01"))
        truth["fixtures"] = [ctrl]
        truth["summary"] = {
            "accepted_controls": 1, "controls_total": 1, "fixtures_total": 1,
            "leaks_total": 0, "missed_by_surface": {}, "missed_violation_ids": [],
            "missed_violations": 0, "spurious_flag_ids": [], "spurious_flags": 0,
            "violations_detected": 0,
        }
        truth["verdict"] = "PASS"
    else:
        raise ValueError(case)
    if case != "R6_results_absent":
        write_truth(root, truth)


def run_runner(root: Path, tag: str) -> dict:
    proc = subprocess.run(
        [sys.executable, str(root / RUNNER_REL)],
        cwd=str(root), capture_output=True, text=True, timeout=120,
    )
    (LOGS / f"{tag}.stdout.txt").write_text(proc.stdout)
    (LOGS / f"{tag}.stderr.txt").write_text(proc.stderr)
    (LOGS / f"{tag}.exit").write_text(str(proc.returncode) + "\n")
    m, c, v = LEAKS_RE.search(proc.stdout), CTRL_RE.search(proc.stdout), VERDICT_RE.search(proc.stdout)
    return {
        "exit_code": proc.returncode,
        "leaks": f"{m.group(1)}/{m.group(2)}" if m else None,
        "controls": f"{c.group(1)}/{c.group(2)}" if c else None,
        "verdict": v.group(1) if v else None,
        "reasons": [ln for ln in proc.stdout.splitlines() if ln.startswith("REASON:")],
        "missing_rows": proc.stdout.count(" MISSING "),
        "stdout": proc.stdout[-3000:],
        "last_stderr_line": (proc.stderr.strip().splitlines() or [""])[-1][:200],
    }


def run_detector_regression(root: Path, tag: str) -> dict:
    probe = (
        "import json,sys;"
        f"sys.path.insert(0,{str(root / 'research_map')!r});"
        "import class_separation as cs;"
        "print(json.dumps(cs.regression()))"
    )
    proc = subprocess.run([sys.executable, "-c", probe], cwd=str(root),
                          capture_output=True, text=True, timeout=120)
    (LOGS / f"{tag}.stdout.txt").write_text(proc.stdout)
    (LOGS / f"{tag}.stderr.txt").write_text(proc.stderr)
    (LOGS / f"{tag}.exit").write_text(str(proc.returncode) + "\n")
    try:
        out = json.loads(proc.stdout.strip().splitlines()[-1])
    except Exception:
        out = {"parse_error": proc.stdout[-300:], "exit_code": proc.returncode}
    out["exit_code"] = proc.returncode
    return out


def apply_patch(root: Path) -> dict:
    proc = subprocess.run(["patch", "-p0", "--batch", "--forward", "-i", str(PATCH_FILE)],
                          cwd=str(root), capture_output=True, text=True, timeout=60)
    (LOGS / f"{root.name}.patch.stdout.txt").write_text(proc.stdout)
    (LOGS / f"{root.name}.patch.stderr.txt").write_text(proc.stderr)
    return {"exit_code": proc.returncode, "stdout": proc.stdout.strip()[-400:]}


def expect_ok(case: str, res: dict) -> tuple[bool, list[str]]:
    zero, subs, verdict = EXPECT[case]
    problems = []
    if zero and res["exit_code"] != 0:
        problems.append(f"exit {res['exit_code']} != 0")
    if not zero and res["exit_code"] == 0:
        problems.append("exit 0 but nonzero expected")
    for s in subs:
        hay = json.dumps(res) if s.startswith("REASON") else json.dumps(res)
        if s not in hay:
            problems.append(f"missing {s!r}")
    if verdict is not None and res.get("verdict") != verdict:
        problems.append(f"verdict {res.get('verdict')!r} != {verdict!r}")
    return (not problems), problems


def main() -> int:
    LOGS.mkdir(parents=True, exist_ok=True)
    start_pins = measure_pins()
    bad = {k: (v, start_pins[k]) for k, v in PINNED.items() if start_pins[k] != v}
    if bad:
        print("PIN MISMATCH AT START", json.dumps(bad, indent=1))
        return 2

    build_template()
    results = {}
    problems_all = []

    # S0: canonical in-situ positive control (the runner writes only an empty
    # runtime/state/classsep_regression dir; no canonical file content changes).
    results["S0_in_situ"] = run_runner(REPO, "S0_in_situ")
    ok, probs = expect_ok("S0_in_situ", results["S0_in_situ"])
    if not ok:
        problems_all.append(("S0_in_situ", probs))

    # unpatched sandbox cases
    if CASES.exists():
        shutil.rmtree(CASES)
    for case in [c for c in EXPECT if c.startswith("R")]:
        root = CASES / case
        root.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(TEMPLATE, root)
        mutate(root, case)
        res = run_runner(root, case)
        results[case] = res
        ok, probs = expect_ok(case, res)
        if not ok:
            problems_all.append((case, probs))

    # detector module entry point on the empty corpus
    root = CASES / "R1_empty"
    det = run_detector_regression(root, "R1_empty.detector_regression")
    results["R1_empty.detector_regression"] = det
    if not (det.get("verdict") == "PASS" and det.get("corpus_size") == 0):
        problems_all.append(("R1_empty.detector_regression",
                             [f"expected PASS corpus_size 0, got {det}"]))
    det = run_detector_regression(CASES / "R0_real", "R0_real.detector_regression")
    results["R0_real.detector_regression"] = det
    if not (det.get("verdict") == "PASS" and det.get("corpus_size") == 27):
        problems_all.append(("R0_real.detector_regression",
                             [f"expected PASS corpus_size 27, got {det}"]))

    # patched sandbox cases (worker-024's proposed diff applied to sandbox copies)
    if PATCHED.exists():
        shutil.rmtree(PATCHED)
    for case in [c for c in EXPECT if c.startswith("P")]:
        root = PATCHED / case
        root.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(TEMPLATE, root)
        patch_res = apply_patch(root)
        results[f"{case}.patch_apply"] = patch_res
        if patch_res["exit_code"] != 0:
            problems_all.append((f"{case}.patch_apply", [patch_res["stdout"]]))
        mutate(root, case)
        res = run_runner(root, case)
        results[case] = res
        ok, probs = expect_ok(case, res)
        if not ok:
            problems_all.append((case, probs))

    root = PATCHED / "P1_patched_empty"
    det = run_detector_regression(root, "P1_patched_empty.detector_regression")
    results["P1_patched_empty.detector_regression"] = det
    if not (det.get("verdict") == "DEFECTIVE" and det.get("problems")):
        problems_all.append(("P1_patched_empty.detector_regression",
                             [f"expected DEFECTIVE with problems, got {det}"]))
    det = run_detector_regression(PATCHED / "P0_patched_real", "P0_patched_real.detector_regression")
    results["P0_patched_real.detector_regression"] = det
    if not (det.get("verdict") == "PASS" and det.get("corpus_size") == 27):
        problems_all.append(("P0_patched_real.detector_regression",
                             [f"expected PASS corpus_size 27, got {det}"]))

    end_pins = measure_pins()
    pins_stable = end_pins == start_pins
    if not pins_stable:
        problems_all.append(("pin_stability", [json.dumps(end_pins)]))

    report = {
        "task_id": "W052-A1-CLASSSEP-VACUITY-REPL-01",
        "worker": "worker-052",
        "node_id": "A1",
        "gate": "G-AUDIT",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN",
                      "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
        "created_at": datetime.now(CST).isoformat(timespec="seconds"),
        "target_finding": {
            "author": "worker-024",
            "claim": "runtime/bin/classsep_regression.py fails open (PASS/exit 0) on an empty, unreachable, or truncated corpus; same shape in class_separation.regression()",
            "artifact": "artifacts/worker-024/classsep_runner_vacuity/report.json",
            "artifact_sha256": sha256(REPO / "artifacts/worker-024/classsep_runner_vacuity/report.json"),
            "proposed_patch": "artifacts/worker-024/classsep_runner_vacuity/proposed_patch.diff",
            "proposed_patch_sha256": PINNED["artifacts/worker-024/classsep_runner_vacuity/proposed_patch.diff"],
        },
        "pins": {"start": start_pins, "end": end_pins, "stable": pins_stable, "declared": PINNED},
        "expectations": {k: {"exit_zero": v[0], "substrings": v[1], "verdict": v[2]}
                         for k, v in EXPECT.items()},
        "results": results,
        "fail_open_confirmed": all(
            results.get(c, {}).get("exit_code") == 0 and results.get(c, {}).get("verdict") == "PASS"
            for c in ("R1_empty", "R2_missing_all", "R3_leaks_removed",
                      "R4_summary_zeroed", "R5_controls_removed")
        ),
        "patch_closes_fail_open": all(
            results.get(c, {}).get("exit_code") not in (0, None)
            and results.get(c, {}).get("verdict") == "DEFECTIVE"
            for c in ("P1_patched_empty", "P2_patched_missing_all", "P3_patched_leaks_removed",
                      "P4_patched_summary_zeroed", "P5_patched_controls_removed")
        ),
        "patch_scope_limit_confirmed": (
            results.get("R7_replaced_corpus", {}).get("verdict") == "PASS"
            and results.get("P7_patched_replaced_corpus", {}).get("verdict") == "PASS"
        ),
        "patch_scope_limit_note": (
            "R7/P7 replace results.json with a single genuine control fixture and a summary that "
            "declares exactly those totals. The patched runner still certifies it PASS: the fix makes "
            "accidental truncation loud but does not bind the corpus to the pinned 27/17/10 ground "
            "truth (truth file sha256 is still unchecked)."
        ),
        "problems": [{"case": c, "detail": d} for c, d in problems_all],
        "all_expectations_met": not problems_all,
        "verdict": "REPLICATED" if not problems_all else "REPLICATION_FAILED",
        "next_falsifier": (
            "Re-run this harness at the same pins. Falsified if any of R1..R5 exits nonzero or prints "
            "DEFECTIVE under the unpatched runner, if R0_real does not reproduce 17/17 + 10/10 PASS, if any "
            "patched case passes an incomplete corpus, or if the proposed patch fails to apply cleanly to "
            "byte-identical copies."
        ),
    }
    (HERE / "report.json").write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: results[k] for k in sorted(results)}, indent=1)[:4000])
    print("fail_open_confirmed:", report["fail_open_confirmed"])
    print("patch_closes_fail_open:", report["patch_closes_fail_open"])
    print("all_expectations_met:", report["all_expectations_met"])
    if problems_all:
        print("PROBLEMS:", json.dumps(problems_all, indent=1))
    return 0 if not problems_all else 1


if __name__ == "__main__":
    sys.exit(main())
