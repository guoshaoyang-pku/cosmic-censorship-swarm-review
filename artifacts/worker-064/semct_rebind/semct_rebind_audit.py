#!/usr/bin/env python3
"""W064-SEMCT-REBIND-01 - independent rebind audit of schemas/semantic_contract_tests.

Read-only against every canonical artifact.  The shared suite directory is never
written to: the fixture tree is copied byte-for-byte into this worker directory
(`suite_copy/`), the runner module is loaded from the canonical path, and only the
module-level MANIFEST / OBSERVED / HERE / REPO bindings are redirected for each run.

Runs:
  A. ORIGINAL - canonical manifest, unmodified.  Expected: exit 2 (integrity
     failure) because the three `conforming_canonical_controls` pins predate the
     2026-09-12T00:19:14+08:00 canonical republish.
  B. REBOUND - worker-local copy of the manifest with only those three sha256 pins
     replaced by the measured rev25 hashes, then the full 38-target suite is run.

Outputs (all in this directory): original_run.json, rebound_run.json,
manifest_rebound.json, rebind_patch.json, report.json, README.md, manifest.sha256.

Falsifiers are emitted per finding in report.json.  Re-running this script must
reproduce every number; any fixture/control integrity mismatch, a non-2 exit from
run A, different run-B counts, accepted frozen controls, or rejected canonical
controls falsifies the corresponding finding.
"""
from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

WORK = Path(__file__).resolve().parent
REPO = WORK.parents[2]
SUITE = REPO / "schemas" / "semantic_contract_tests"
COPY = WORK / "suite_copy"
CST = timezone(timedelta(hours=8))
TASK_ID = "W064-SEMCT-REBIND-01"

CANONICAL = {
    "AF-WCC-VAC-GEN": REPO / "schemas" / "af_wcc_vacuum.yaml",
    "AF-SCC-C2-VAC-GEN": REPO / "schemas" / "af_scc_c2_vacuum.yaml",
    "AF-SCC-C0-VAC-GEN": REPO / "schemas" / "af_scc_c0_vacuum.yaml",
}
TOOLS = {
    "structural_gate": REPO / "artifacts" / "formulation" / "tools" / "check_class_schema.py",
    "semantic_auditor": REPO / "artifacts" / "worker-06" / "spec_conformance_audit.py",
    "suite_runner": SUITE / "run_contract_tests.py",
}


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load_runner():
    spec = importlib.util.spec_from_file_location("semct_runner_w064", SUITE / "run_contract_tests.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_suite(manifest_path: Path, observed_path: Path, label: str) -> dict:
    """Run the canonical runner with paths redirected; never writes to SUITE."""
    mod = load_runner()
    mod.HERE = COPY                      # fixtures + .tmp outputs land in the copy
    mod.REPO = REPO                      # canonical entries + stage tools stay real
    mod.MANIFEST = manifest_path
    mod.OBSERVED = observed_path
    buf = io.StringIO()
    saved_argv = sys.argv
    sys.argv = ["run_contract_tests.py"]
    rc = None
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            rc = mod.main()
    except SystemExit as exc:  # defensive: runner returns, but keep the contract
        rc = exc.code
    finally:
        sys.argv = saved_argv
    observed = json.loads(observed_path.read_text()) if observed_path.exists() else None
    return {
        "label": label,
        "manifest": str(manifest_path),
        "manifest_sha256": sha(manifest_path),
        "exit": rc,
        "stdout": buf.getvalue(),
        "observed_written": observed_path.exists(),
        "observed": observed,
    }


def main() -> int:
    WORK.mkdir(parents=True, exist_ok=True)
    (COPY / "fixtures").mkdir(parents=True, exist_ok=True)
    shutil.copytree(SUITE / "fixtures", COPY / "fixtures", dirs_exist_ok=True)

    observed_at = now()
    measured = {
        "canonical": {k: sha(v) for k, v in CANONICAL.items()},
        "tools": {k: sha(v) for k, v in TOOLS.items()},
        "suite_manifest": sha(SUITE / "manifest.json"),
        "suite_observed_verdicts": sha(SUITE / "observed_verdicts.json"),
    }

    original_manifest = json.loads((SUITE / "manifest.json").read_text())

    # ---- integrity census (read-only, against the canonical pins) -------------
    integrity: dict = {"fixtures": [], "frozen_controls": [], "conforming_canonical": []}
    for group in integrity:
        key = {"fixtures": "fixtures", "frozen_controls": "controls",
               "conforming_canonical": "conforming_canonical_controls"}[group]
        for e in original_manifest[key]:
            f = e["fixture"]
            target = (COPY / f) if f.startswith("fixtures/") else (REPO / f)
            cur = sha(target) if target.exists() else None
            integrity[group].append({
                "test_id": e["test_id"],
                "fixture": f,
                "pinned_sha256": e["sha256"],
                "measured_sha256": cur,
                "match": cur == e["sha256"],
                "expected_verdict": e["expected_verdict"],
            })
    integrity_errors = [r for g in integrity.values() for r in g if not r["match"]]

    # ---- run A: canonical manifest, unmodified --------------------------------
    run_a = run_suite(SUITE / "manifest.json", WORK / "original_observed.json", "original")

    # ---- rebind: only the 3 stale canonical pins ------------------------------
    rebound = json.loads(json.dumps(original_manifest))
    changes = []
    for e in rebound["conforming_canonical_controls"]:
        new = measured["canonical"]  # keyed by class, not path; resolve by fixture
        new_hash = sha(REPO / e["fixture"])
        if new_hash != e["sha256"]:
            changes.append({
                "test_id": e["test_id"],
                "path": e["fixture"],
                "old_sha256": e["sha256"],
                "new_sha256": new_hash,
            })
            e["sha256"] = new_hash
    rebound["worker_rebind"] = {
        "task_id": TASK_ID,
        "rebound_by": "worker-064",
        "rebound_at": observed_at,
        "scope": "conforming_canonical_controls[].sha256 only; fixtures, controls, expected verdicts and rules untouched",
        "changes": changes,
        "note": "worker-local copy; the canonical schemas/semantic_contract_tests/manifest.json is not modified",
    }
    rebound_path = WORK / "manifest_rebound.json"
    rebound_path.write_text(json.dumps(rebound, indent=1) + "\n")

    patch = {
        "task_id": TASK_ID,
        "target": "schemas/semantic_contract_tests/manifest.json",
        "operation": "replace sha256 pins of conforming_canonical_controls to the measured rev25 bytes",
        "authored_at": observed_at,
        "canonical_manifest_sha256_at_audit": measured["suite_manifest"],
        "changes": changes,
        "not_changed": ["fixtures[]", "controls[]", "adjudication_items[]", "run_record", "expected_verdict of every entry"],
    }
    (WORK / "rebind_patch.json").write_text(json.dumps(patch, indent=1) + "\n")

    # ---- run B: rebound manifest ---------------------------------------------
    run_b = run_suite(rebound_path, WORK / "rebound_observed.json", "rebound")

    # ---- analysis -------------------------------------------------------------
    b = run_b["observed"]
    per_stage, escapes, hardened_only, stage_failures = {}, [], [], {}
    if b:
        for r in b["results"]:
            for s in ("structural", "semantic_baseline", "semantic_hardened"):
                per_stage.setdefault(s, {"rejected": 0, "accepted": 0})
                per_stage[s]["rejected" if s in r["observed"]["rejected_by"] else "accepted"] += 1
            if r["observed"]["escapes_adopted_stages"]:
                escapes.append(r["test_id"])
            if r["observed"]["hardened_only_catch"]:
                hardened_only.append(r["test_id"])
        for e in original_manifest["fixtures"] + original_manifest["controls"] + \
                original_manifest["conforming_canonical_controls"]:
            stage_failures[e["test_id"]] = e["fixture"]

    control_rows = []
    canonical_rows = []
    if b:
        by_id = {r["test_id"]: r for r in b["results"]}
        for e in original_manifest["controls"]:
            r = by_id[e["test_id"]]
            control_rows.append({
                "test_id": e["test_id"], "fixture": e["fixture"],
                "expected": e["expected_verdict"], "observed": r["observed"]["verdict"],
                "rejected_by": r["observed"]["rejected_by"],
                "structural_failed_rules": r["observed"]["stages"]["structural"]["failed_rules"],
                "agrees_with_expected": r["observed"]["agrees_with_expected"],
            })
        for e in original_manifest["conforming_canonical_controls"]:
            r = by_id[e["test_id"]]
            canonical_rows.append({
                "test_id": e["test_id"], "fixture": e["fixture"],
                "class_hash_at_run": sha(REPO / e["fixture"]),
                "expected": e["expected_verdict"], "observed": r["observed"]["verdict"],
                "accepted_by": r["observed"]["accepted_by"],
                "rejected_by": r["observed"]["rejected_by"],
                "agrees_with_expected": r["observed"]["agrees_with_expected"],
            })

    readme_summary = original_manifest.get("run_record", {}).get("summary", {})
    reproduced = {}
    if b:
        for k in ("mutants", "structural_caught", "semantic_baseline_caught",
                  "semantic_hardened_caught", "escaped_adopted_stages", "hardened_only_catches"):
            reproduced[k] = {"readme": readme_summary.get(k), "measured": b["summary"].get(k),
                             "agree": readme_summary.get(k) == b["summary"].get(k)}
    stage_tools_unchanged = (
        measured["tools"]["structural_gate"] ==
        original_manifest.get("run_record", {}).get("stage_hashes", {}).get("structural")
        and measured["tools"]["semantic_auditor"] ==
        original_manifest.get("run_record", {}).get("stage_hashes", {}).get("semantic")
    )

    original_errors = []
    if run_a["exit"] == 2 and run_a["stdout"]:
        original_errors = [ln.strip(" -\n") for ln in run_a["stdout"].splitlines()
                           if ln.strip().startswith("-")]

    report = {
        "task_id": TASK_ID,
        "worker": "worker-064",
        "created_at": observed_at,
        "repo": str(REPO),
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "node_id": "A1",
        "scope": "independent rebind audit + full re-run of the semantic contract suite at FROZEN rev25; no canonical file modified",
        "measured": measured,
        "fixture_integrity": {
            "counts": {g: len(rows) for g, rows in integrity.items()},
            "mismatch_count": len(integrity_errors),
            "mismatches": integrity_errors,
            "canonical_pins_stale": [r for r in integrity["conforming_canonical"] if not r["match"]],
        },
        "run_original": {
            "exit": run_a["exit"], "observed_written": run_a["observed_written"],
            "stdout": run_a["stdout"],
            "integrity_errors": original_errors,
            "error_count": len(original_errors),
        },
        "rebind_patch": patch,
        "run_rebound": {
            "exit": run_b["exit"], "observed_written": run_b["observed_written"],
            "stdout": run_b["stdout"],
            "stage_hashes": (b or {}).get("stage_hashes"),
            "summary": (b or {}).get("summary"),
            "validity": (b or {}).get("validity"),
            "adjudication_required_ids": [a.get("item_id") for a in (b or {}).get("adjudication_required", [])],
        },
        "stage_totals_rebound": per_stage,
        "frozen_controls_rebound": control_rows,
        "canonical_controls_rebound": canonical_rows,
        "escaped_adopted_stages": escapes,
        "hardened_only_catches": hardened_only,
        "reproduction_vs_readme_00_14_40": reproduced,
        "stage_tools_unchanged_since_00_14_40": stage_tools_unchanged,
        "findings": [
            {
                "id": "F-SEMCT-1",
                "statement": ("The canonical suite manifest pins all three conforming_canonical_controls to "
                              "pre-00:19:14 bytes (SCT-K01 a8d899d2941f, SCT-K02 8dae50da1ab5, SCT-K03 b65fcc0f0118); "
                              "the 32 leak mutants and 3 frozen controls are byte-intact. Running the suite "
                              "unmodified therefore exits 2 with exactly 3 integrity errors and writes no "
                              "observed_verdicts.json."),
                "evidence": ["original_run.json", "report.json#fixture_integrity"],
                "falsifier": "Re-run semct_rebind_audit.py: exit != 2 for run A, any fixture/control sha mismatch, or an error count != 3 falsifies this finding.",
            },
            {
                "id": "F-SEMCT-2",
                "statement": ("Replacing only the three conforming_canonical_controls sha256 pins with the measured "
                              "rev25 hashes (C0 1bb78ce9b357, C2 b6123750b37d, F1 9a8bd4c96800) makes the suite run to "
                              "completion at unchanged stage tools; no mutant, control, rule or expected verdict is touched."),
                "evidence": ["rebind_patch.json", "manifest_rebound.json"],
                "falsifier": "Any additional field differing between manifest_rebound.json and the canonical manifest beyond conforming_canonical_controls[].sha256 and worker_rebind falsifies the minimality claim.",
            },
            {
                "id": "F-SEMCT-3",
                "statement": ("At rev25 the rebound suite reproduces the 00:14:40 measurements: 32/32 mutants caught "
                              "by the structural gate, 32/32 by the proposed hardened auditor, 11/32 by the semantic "
                              "baseline; 0 escapes of the adopted stages and 0 hardened-only catches (unless run B "
                              "disagrees, in which case the measured numbers here supersede the README)."),
                "evidence": ["rebound_observed.json", "report.json#reproduction_vs_readme_00_14_40"],
                "falsifier": "Any stage count in run B differing from the recorded run_record.summary, or an escape/hardened-only id appearing, falsifies the reproduction claim.",
            },
            {
                "id": "F-SEMCT-4",
                "statement": ("The ADJ-CONTROL-STALENESS blocker persists at rev25: the three frozen controls are "
                              "rejected by the structural stage (R28) while all three current canonical schemas are "
                              "accepted by all three stages, so validity.valid_for_calibration is false and the suite "
                              "still cannot be used as current-revision calibration evidence."),
                "evidence": ["rebound_observed.json", "report.json#frozen_controls_rebound", "report.json#canonical_controls_rebound"],
                "falsifier": "A run in which every frozen control is accepted by both adopted stages, or in which any current canonical schema is rejected by a stage, falsifies this finding.",
            },
        ],
        "not_claimed": [
            "no gate verdict", "no node completion", "no mathematical verdict on any schema",
            "no modification of any canonical artifact", "no claim about bytes outside the measured rev25 snapshot",
        ],
    }
    (WORK / "report.json").write_text(json.dumps(report, indent=1) + "\n")
    (WORK / "original_run.json").write_text(json.dumps(run_a, indent=1) + "\n")
    (WORK / "rebound_run.json").write_text(json.dumps(run_b, indent=1) + "\n")

    print(json.dumps({
        "task_id": TASK_ID, "at": observed_at,
        "run_original_exit": run_a["exit"], "run_original_errors": original_errors,
        "run_rebound_exit": run_b["exit"],
        "rebound_summary": (b or {}).get("summary"),
        "validity": (b or {}).get("validity"),
        "reproduced": reproduced,
    }, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
