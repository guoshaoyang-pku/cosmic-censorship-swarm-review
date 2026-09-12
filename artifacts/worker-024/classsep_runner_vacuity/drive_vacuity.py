#!/usr/bin/env python3
"""W024-CLASSSEP-RUNNER-VACUITY-01 — fail-open audit of the frozen class-separation
gate runner (node A1 / gate G-AUDIT).

Question
--------
`runtime/bin/classsep_regression.py` is the standing regression that CF-3 cites as
frozen gate evidence for four-class separation. The runner derives a PASS/FAIL verdict
from counts of detected violations, not from the integrity of the corpus it reads.
Can it return PASS (exit 0) when the corpus is empty, unreachable, partial, or when the
ground-truth file has been re-labelled?

Method
------
1. Pin the runner, the detector and the corpus truth file by sha256; copy the two
   Python files byte-identically into per-case sandboxes (hash-verified after copy).
2. Materialise six corpus cases under `sandbox/cases/<case>/` with exactly the layout
   the runner expects (`artifacts/worker-07/class_separation_falsification/`):
     T0_real              the untouched corpus                     (positive control)
     T1_empty_list        summary intact, fixtures list empty
     T2_missing_paths     27 listed, every fixture_path unreachable
     T3_leaks_dropped     17 leak fixtures removed from the list
     T4_truth_flipped     all 27 fixtures re-labelled is_class_merge=False
     T5_partial_missing   3 control files deleted, list untouched
3. Run the pinned runner copy in each sandbox and record exit code + stdout.
4. Run the detector's module-level `regression(corpus_dir=...)` entry point on the
   same sandboxes through an isolated import.
5. Apply `proposed_patch.diff` to copies of both files under `sandbox/patched/` and
   re-run every case. The patch asserts corpus size, missing files and declared
   leak/control totals before it is allowed to print PASS.

This is an instrument-level audit. It makes no claim about class semantics, no gate
verdict, and writes no shared state outside this artifact directory.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]          # .../ai4math-swarm
ART = Path(__file__).resolve().parent               # artifacts/worker-024/classsep_runner_vacuity
SANDBOX = ART / "sandbox"
CASES = SANDBOX / "cases"
PATCHED = SANDBOX / "patched"
LOGS = ART / "logs"
PATCHED_FILES = ART / "patched"

RUNNER_SRC = ROOT / "runtime/bin/classsep_regression.py"
DETECTOR_SRC = ROOT / "research_map/class_separation.py"
CORPUS_SRC = ROOT / "artifacts/worker-07/class_separation_falsification"
TRUTH_SRC = CORPUS_SRC / "results.json"

CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_case_results(case: str, mutator) -> tuple[Path, dict]:
    """Create sandbox/cases/<case>/artifacts/worker-07/class_separation_falsification/."""
    corpus = CASES / case / "artifacts/worker-07/class_separation_falsification"
    if corpus.exists():
        shutil.rmtree(corpus)
    (corpus / "fixtures").mkdir(parents=True, exist_ok=True)
    results = json.loads(TRUTH_SRC.read_text())
    mutator(results, corpus)
    (corpus / "results.json").write_text(json.dumps(results, indent=2, sort_keys=True))
    return corpus, results


def copy_layout(case: str) -> Path:
    """Byte-identical copies of the pinned runner and detector in a case sandbox."""
    base = CASES / case
    (base / "runtime/bin").mkdir(parents=True, exist_ok=True)
    (base / "research_map").mkdir(parents=True, exist_ok=True)
    shutil.copy2(RUNNER_SRC, base / "runtime/bin/classsep_regression.py")
    shutil.copy2(DETECTOR_SRC, base / "research_map/class_separation.py")
    assert sha256(base / "runtime/bin/classsep_regression.py") == sha256(RUNNER_SRC)
    assert sha256(base / "research_map/class_separation.py") == sha256(DETECTOR_SRC)
    return base


def run_runner(case: str) -> dict:
    base = CASES / case
    proc = subprocess.run(
        [sys.executable, str(base / "runtime/bin/classsep_regression.py"), "--verbose"],
        cwd=str(base), capture_output=True, text=True, timeout=300,
    )
    (LOGS / f"{case}.runner.stdout.txt").write_text(proc.stdout)
    (LOGS / f"{case}.runner.stderr.txt").write_text(proc.stderr)
    return {"exit_code": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}


def run_module_regression(case: str, detector_path: Path | None = None):
    path = detector_path or (CASES / case / "research_map/class_separation.py")
    spec = importlib.util.spec_from_file_location(f"cs_{case}_{path.stat().st_mtime_ns}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod.regression(corpus_dir=str(CASES / case / "artifacts/worker-07/class_separation_falsification"))


def build_cases() -> dict:
    cases: dict[str, dict] = {}

    def real(results, corpus):
        shutil.copytree(CORPUS_SRC / "fixtures", corpus / "fixtures", dirs_exist_ok=True)

    def empty(results, corpus):
        results["fixtures"] = []

    def missing_paths(results, corpus):
        for fx in results["fixtures"]:
            fx["fixture_path"] = "artifacts/worker-07/class_separation_falsification/fixtures/MISSING__" + Path(fx["fixture_path"]).name

    def leaks_dropped(results, corpus):
        kept = [fx for fx in results["fixtures"] if not fx["is_class_merge"]]
        results["fixtures"] = kept
        for fx in kept:
            dst = corpus / "fixtures" / Path(fx["fixture_path"]).name
            shutil.copy2(ROOT / fx["fixture_path"], dst)

    def truth_flipped(results, corpus):
        for fx in results["fixtures"]:
            fx["is_class_merge"] = False
        shutil.copytree(CORPUS_SRC / "fixtures", corpus / "fixtures", dirs_exist_ok=True)

    def partial_missing(results, corpus):
        drop = {"C08_prohibition_after_phrase_label", "C09_prohibition_artifact", "C10_conclusion_type_ok"}
        for fx in results["fixtures"]:
            src = ROOT / fx["fixture_path"]
            if src.stem in drop:
                continue
            shutil.copy2(src, corpus / "fixtures" / src.name)

    for case, mut in [
        ("T0_real", real),
        ("T1_empty_list", empty),
        ("T2_missing_paths", missing_paths),
        ("T3_leaks_dropped", leaks_dropped),
        ("T4_truth_flipped", truth_flipped),
        ("T5_partial_missing", partial_missing),
    ]:
        copy_layout(case)
        corpus, _ = write_case_results(case, mut)
        cases[case] = {
            "corpus_dir": str(corpus.relative_to(ART)),
            "results_sha256": sha256(corpus / "results.json"),
            "fixtures_on_disk": len(list((corpus / "fixtures").glob("*.json"))),
            "runner": run_runner(case),
        }
        cases[case]["module_regression"] = run_module_regression(case)
    return cases


def build_patched() -> dict:
    """Apply the recorded patch to copies; run the same six cases against them."""
    PATCHED_FILES.mkdir(parents=True, exist_ok=True)
    shutil.copy2(RUNNER_SRC, PATCHED_FILES / "classsep_regression.unpatched.py")
    shutil.copy2(DETECTOR_SRC, PATCHED_FILES / "class_separation.unpatched.py")

    runner = (PATCHED_FILES / "classsep_regression.unpatched.py").read_text()
    runner = runner.replace(
        '''    results = json.loads((CORPUS / "results.json").read_text())
    TMP.mkdir(parents=True, exist_ok=True)
    tp = fp = tn = fn = 0
    rows = []
    for fx in results["fixtures"]:
        path = ROOT / fx["fixture_path"]
        if not path.exists():
            rows.append((fx["id"], "MISSING", "?", "?")); continue
''',
        '''    results = json.loads((CORPUS / "results.json").read_text())
    summary = results.get("summary", {})
    problems = []
    if summary.get("fixtures_total") != len(results["fixtures"]):
        problems.append(
            f"corpus list size {len(results['fixtures'])} != declared fixtures_total "
            f"{summary.get('fixtures_total')}")
    TMP.mkdir(parents=True, exist_ok=True)
    tp = fp = tn = fn = 0
    rows = []
    missing = []
    for fx in results["fixtures"]:
        path = ROOT / fx["fixture_path"]
        if not path.exists():
            rows.append((fx["id"], "MISSING", "?", "?")); missing.append(fx["id"]); continue
''')
    runner = runner.replace(
        '''    n_leaks = tp + fn
    n_ctrl = tn + fp
    print(f"\\nleaks detected {tp}/{n_leaks}   controls clean {tn}/{n_ctrl}   (FP {fp}, FN {fn})")
    ok = (fn == 0 and fp == 0)
    print("VERDICT:", "PASS" if ok else "DEFECTIVE")
    return 0 if ok else 1''',
        '''    n_leaks = tp + fn
    n_ctrl = tn + fp
    if missing:
        problems.append(f"{len(missing)} fixture file(s) unreadable: {sorted(missing)}")
    if summary.get("leaks_total") != n_leaks:
        problems.append(f"scored leaks {n_leaks} != declared leaks_total {summary.get('leaks_total')}")
    if summary.get("controls_total") != n_ctrl:
        problems.append(f"scored controls {n_ctrl} != declared controls_total {summary.get('controls_total')}")
    print(f"\\nleaks detected {tp}/{n_leaks}   controls clean {tn}/{n_ctrl}   (FP {fp}, FN {fn})")
    ok = (fn == 0 and fp == 0 and not problems)
    for p in problems:
        print("REASON:", p)
    print("VERDICT:", "PASS" if ok else "DEFECTIVE")
    return 0 if ok else 1''')
    assert runner != (PATCHED_FILES / "classsep_regression.unpatched.py").read_text(), "runner patch did not apply"

    detector = (PATCHED_FILES / "class_separation.unpatched.py").read_text()
    detector = detector.replace(
        '''    tp = fn = tn = fp = 0
    for fx in res["fixtures"]:
        fpth = root / fx["fixture_path"]
        if not fpth.exists():
            continue
''',
        '''    tp = fn = tn = fp = 0
    missing = []
    summary = res.get("summary", {})
    for fx in res["fixtures"]:
        fpth = root / fx["fixture_path"]
        if not fpth.exists():
            missing.append(fx["id"])
            continue
''')
    detector = detector.replace(
        '''    return {"tp": tp, "fn": fn, "tn": tn, "fp": fp,
            "verdict": "PASS" if fn == 0 and fp == 0 else "DEFECTIVE",
            "corpus_size": tp + fn + tn + fp}''',
        '''    size = tp + fn + tn + fp
    problems = []
    if missing:
        problems.append(f"{len(missing)} fixture file(s) unreadable: {sorted(missing)}")
    if summary.get("fixtures_total") != len(res["fixtures"]):
        problems.append(f"corpus list size {len(res['fixtures'])} != declared fixtures_total {summary.get('fixtures_total')}")
    if summary.get("leaks_total") != tp + fn:
        problems.append(f"scored leaks {tp + fn} != declared leaks_total {summary.get('leaks_total')}")
    if summary.get("controls_total") != tn + fp:
        problems.append(f"scored controls {tn + fp} != declared controls_total {summary.get('controls_total')}")
    return {"tp": tp, "fn": fn, "tn": tn, "fp": fp,
            "verdict": "PASS" if fn == 0 and fp == 0 and not problems else "DEFECTIVE",
            "corpus_size": size, "missing": missing, "problems": problems}''')
    assert detector != (PATCHED_FILES / "class_separation.unpatched.py").read_text(), "detector patch did not apply"

    (PATCHED_FILES / "classsep_regression.py").write_text(runner)
    (PATCHED_FILES / "class_separation.py").write_text(detector)

    out: dict[str, dict] = {}
    for case in [f"T{i}_" for i in range(6)]:
        case = next(c for c in sorted(p.name for p in CASES.iterdir() if p.is_dir()) if c.startswith(case))
        base = PATCHED / case
        (base / "runtime/bin").mkdir(parents=True, exist_ok=True)
        (base / "research_map").mkdir(parents=True, exist_ok=True)
        shutil.copy2(PATCHED_FILES / "classsep_regression.py", base / "runtime/bin/classsep_regression.py")
        shutil.copy2(PATCHED_FILES / "class_separation.py", base / "research_map/class_separation.py")
        src = CASES / case / "artifacts/worker-07/class_separation_falsification"
        dst = base / "artifacts/worker-07/class_separation_falsification"
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        proc = subprocess.run(
            [sys.executable, str(base / "runtime/bin/classsep_regression.py"), "--verbose"],
            cwd=str(base), capture_output=True, text=True, timeout=300,
        )
        (LOGS / f"{case}.patched.runner.stdout.txt").write_text(proc.stdout)
        module = run_module_regression(case, detector_path=base / "research_map/class_separation.py")
        out[case] = {"exit_code": proc.returncode, "stdout": proc.stdout,
                     "stderr": proc.stderr, "module_regression": module}
    return out


def main():
    for d in (SANDBOX, LOGS):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True, exist_ok=True)

    pins = {
        "runtime/bin/classsep_regression.py": sha256(RUNNER_SRC),
        "research_map/class_separation.py": sha256(DETECTOR_SRC),
        "artifacts/worker-07/class_separation_falsification/results.json": sha256(TRUTH_SRC),
        "artifacts/worker-07/class_separation_falsification/baseline_hashes.txt": sha256(CORPUS_SRC / "baseline_hashes.txt"),
    }
    cases = build_cases()
    patched = build_patched()

    findings = []
    for case, rec in cases.items():
        runner_pass = rec["runner"]["exit_code"] == 0 and "VERDICT: PASS" in rec["runner"]["stdout"]
        mod_pass = rec["module_regression"]["verdict"] == "PASS"
        patched_pass = patched[case]["exit_code"] == 0 and "VERDICT: PASS" in patched[case]["stdout"]
        findings.append({
            "case": case,
            "unpatched_runner_exit": rec["runner"]["exit_code"],
            "unpatched_runner_verdict": "PASS" if runner_pass else "DEFECTIVE",
            "unpatched_module_verdict": rec["module_regression"]["verdict"],
            "unpatched_module_corpus_size": rec["module_regression"]["corpus_size"],
            "patched_runner_exit": patched[case]["exit_code"],
            "patched_runner_verdict": "PASS" if patched_pass else "DEFECTIVE",
            "patched_module_verdict": patched[case]["module_regression"]["verdict"],
        })

    regressions = [f for f in findings if f["case"] != "T0_real"]
    # Vacuous = incomplete corpus still certified PASS by the unpatched instrument.
    vacuous = [f["case"] for f in regressions
               if f["unpatched_runner_verdict"] == "PASS" and f["unpatched_module_verdict"] == "PASS"]
    # Incidental = unpatched instrument said DEFECTIVE, but only because detector output
    # disagreed with the damaged corpus (FP/FN side effect), not because corpus integrity
    # was asserted. The runner cannot distinguish these from a genuine detector defect.
    incidental = [f["case"] for f in regressions if f["case"] not in vacuous]
    closed = [f["case"] for f in regressions if f["patched_runner_verdict"] == "DEFECTIVE"]
    control_ok = (findings[0]["case"] == "T0_real" and findings[0]["unpatched_runner_verdict"] == "PASS"
                  and findings[0]["patched_runner_verdict"] == "PASS")

    report = {
        "task_id": "W024-CLASSSEP-RUNNER-VACUITY-01",
        "node_id": "A1",
        "gate_scope": ["G-AUDIT"],
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
        "actor": "worker-024",
        "created_at": NOW.isoformat(timespec="seconds"),
        "pins": pins,
        "frozen_evidence_under_audit": {
            "controller_finding": "CF-3: class_separation.py rebuilt; standing regression 17/17 leaks + 10/10 controls, 0 FP/FN; frozen as gate evidence",
            "runner": "runtime/bin/classsep_regression.py",
            "detector": "research_map/class_separation.py",
            "ground_truth": "artifacts/worker-07/class_separation_falsification/results.json",
        },
        "method": "byte-identical copies of the pinned runner/detector in per-case sandboxes; six corpus-integrity cases; the same cases re-run after proposed_patch.diff",
        "cases": cases,
        "patched": patched,
        "findings": findings,
        "result": {
            "verdict": "FAIL_OPEN_ON_EMPTY_OR_TRUNCATED_CORPUS",
            "positive_control_ok": control_ok,
            "vacuous_pass_cases": vacuous,
            "incidentally_detected_cases": incidental,
            "patched_closes_cases": closed,
            "mechanism": (
                "The runner scores PASS iff fn==0 and fp==0 over the fixtures it could read. "
                "It never compares the scored counts with results.json.summary "
                "(fixtures_total=27, leaks_total=17, controls_total=10), never fails on a missing "
                "fixture file (it records MISSING and continues), and never pins the ground-truth "
                "file hash. The module-level class_separation.regression() has the same shape: "
                "missing fixtures are skipped with `continue`."
            ),
            "impact": (
                "Corpus loss or a truncated fixtures list yields VERDICT: PASS / exit 0 with "
                "corpus_size 0-10 (T1/T2/T3). The regression is therefore necessary but not "
                "sufficient gate evidence: it certifies detector behaviour only for the corpus it "
                "actually read, and it cannot distinguish 'detector clean' from 'corpus empty' or "
                "'leak fixtures removed'."
            ),
            "incidental_detection_note": (
                "T4 (all truth labels flipped to False) and T5 (3 control files deleted) did exit 1, "
                "but only as a side effect of detector/truth disagreement: T4 because 17 genuine "
                "leaks were re-labelled non-merges (FP=17), T5 because the deleted C09 artifact "
                "file made L16 unreadable (FN=1). Neither run reports that the corpus is damaged; a "
                "targeted relabel that preserves detector agreement, or deletion of fixtures whose "
                "artifacts are not referenced by another fixture, is not caught."
            ),
            "residual_risk": (
                "The truth file itself is not hash-pinned; a semantically consistent relabel that "
                "keeps TP/FP/FN at their declared values would still PASS without the count "
                "assertions. The proposed patch closes the count/missing-file gaps; pinning "
                "results.json by hash remains an owner decision."
            ),
            "scope": "instrument-level; no claim about class semantics and no gate verdict",
            "shared_state_written": False,
        },
        "proposed_patch": {
            "path": "artifacts/worker-024/classsep_runner_vacuity/proposed_patch.diff",
            "applied_files": {
                "runtime/bin/classsep_regression.py": sha256(PATCHED_FILES / "classsep_regression.py"),
                "research_map/class_separation.py": sha256(PATCHED_FILES / "class_separation.py"),
            },
            "rule": "assert declared corpus totals and fail on any MISSING fixture path before PASS is reachable",
        },
        "falsifier": (
            "Re-run drive_vacuity.py against the pinned runner sha256 "
            "9f1cf9c336be874182e8882e00f7fdf8e4f6c4ea1881f11a6b3e762e038a7091. "
            "FALSIFIED if any of T1_empty_list, T2_missing_paths or T3_leaks_dropped returns "
            "exit != 0 or prints VERDICT: DEFECTIVE under the unpatched runner, or if T0_real "
            "fails to reproduce 17/17 leaks + 10/10 controls, or if any patched sandbox passes "
            "an incomplete corpus. T4/T5 are explicitly not part of the fail-open claim: they "
            "exit 1 incidentally, and the report records why."
        ),
        "next_falsifier": (
            "Apply proposed_patch.diff at the canonical path and re-run the six cases plus a "
            "deliberately emptied corpus in the standing A1 evidence; the defect is closed only "
            "if every incomplete corpus exits 1 with a printed REASON while T0_real still exits 0 "
            "at 17/17 and 10/10. If the canonical runner is later replaced, re-run this audit at "
            "the new hash and expect all six cases to be non-vacuous."
        ),
    }
    (ART / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True))

    # Recorded unified diff (unpatched copy -> patched copy) for owner review.
    import difflib
    diff_lines = []
    for name in ("classsep_regression", "class_separation"):
        a = (PATCHED_FILES / f"{name}.unpatched.py").read_text().splitlines(keepends=True)
        b = (PATCHED_FILES / f"{name}.py").read_text().splitlines(keepends=True)
        diff_lines += list(difflib.unified_diff(
            a, b, fromfile=f"runtime/bin/{name}.py" if name == "classsep_regression" else f"research_map/{name}.py",
            tofile=f"runtime/bin/{name}.py" if name == "classsep_regression" else f"research_map/{name}.py",
            n=3))
    (ART / "proposed_patch.diff").write_text("".join(diff_lines))

    entry = {
        "task_id": report["task_id"],
        "created_at": report["created_at"],
        "inputs": pins,
    }
    (ART / "entry_hashes.json").write_text(json.dumps(entry, indent=2, sort_keys=True))
    outputs = {p.name: sha256(p) for p in sorted(ART.iterdir())
               if p.is_file() and p.name in {"report.json", "proposed_patch.diff",
                                             "entry_hashes.json", "drive_vacuity.py"}}
    exit_rec = {
        "task_id": report["task_id"],
        "measured_at": datetime.now(CST).isoformat(timespec="seconds"),
        "canonical_inputs_remeasured": {
            "runtime/bin/classsep_regression.py": sha256(RUNNER_SRC),
            "research_map/class_separation.py": sha256(DETECTOR_SRC),
            "artifacts/worker-07/class_separation_falsification/results.json": sha256(TRUTH_SRC),
        },
        "no_canonical_input_changed_during_run": (
            sha256(RUNNER_SRC) == pins["runtime/bin/classsep_regression.py"]
            and sha256(DETECTOR_SRC) == pins["research_map/class_separation.py"]
            and sha256(TRUTH_SRC) == pins["artifacts/worker-07/class_separation_falsification/results.json"]
        ),
        "artifact_outputs": outputs,
    }
    (ART / "exit_hashes.json").write_text(json.dumps(exit_rec, indent=2, sort_keys=True))

    print(json.dumps({
        "pins": pins,
        "findings": findings,
        "vacuous_pass_cases": vacuous,
        "incidentally_detected_cases": incidental,
        "patched_closes_cases": closed,
        "positive_control_ok": control_ok,
    }, indent=1))
    return 0 if control_ok and len(vacuous) == 3 and len(closed) == 5 else 1


if __name__ == "__main__":
    sys.exit(main())
