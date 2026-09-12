#!/usr/bin/env python3
"""W080-SEMCT-REBASE-01 — executed candidate resolution of ADJ-CONTROL-STALENESS.

Task (one bounded, class-bound task; classes AF-WCC-VAC-GEN, AF-SCC-C2-VAC-GEN,
AF-SCC-C0-VAC-GEN):

  The G-AUDIT calibration suite `schemas/semantic_contract_tests/` is unusable at the
  current frozen revision because (a) its three `conforming_canonical_controls` pins
  predate the FROZEN rev27 republish, and (b) its three frozen controls embed the old
  corpus-base layout. The suite README and worker-064's blocker both route (b) to
  lead-formulation as `ADJ-CONTROL-STALENESS`: "rebase the control layouts to the
  current canonical (mutants stay frozen — that changes only controls)".

  This harness produces and *executes* that rebase as a candidate patch, read-only on
  every canonical path. It never writes outside its own artifact directory.

Method: copy a minimal repo subset into a sandbox, run the canonical runner there under
pre-registered expectations, apply the two minimal text edits to the three control
fixtures, re-pin, re-run, and run targeted negative controls proving each edit is
necessary and that the structural gate still fires on the drift it was written for.

Exit 0 iff every pre-registered expectation holds; 1 otherwise.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import time
from collections import OrderedDict
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]                      # artifacts/worker-080/semct_rebase -> repo root
STAGE_ROOT = HERE / "stage"
RUNS = HERE / "runs"
PATCHED = HERE / "patched_controls"

SUITE_REL = "schemas/semantic_contract_tests"
CANON_SCHEMAS = [
    "schemas/af_wcc_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml",
]
TOOLS = [
    "artifacts/formulation/tools/check_class_schema.py",
    "artifacts/formulation/rule_spec.json",
    "artifacts/formulation/KEY_MANIFEST.json",
    "artifacts/worker-06/spec_conformance_audit.py",
]
FROZEN_INPUTS = CANON_SCHEMAS + [
    "research_map/formulation_taxonomy.yaml",
    "artifacts/formulation/FROZEN.json",
    "artifacts/formulation/formulation_taxonomy.yaml",
]

CONTROL_NAMES = [
    "control_conforming_base.yaml",
    "control_comment_only_composite.yaml",
    "control_quoted_forbidden_phrase.yaml",
]
STALE_ROW = ["finite_codimension_complement", "residual_comeager"]
STALE_KEY = "revised_at_unused"

EXPECTATIONS = OrderedDict([
    ("R0_canonical_manifest", {"exit": 2, "integrity_errors": 3}),
    ("R1_pins_rebound_only", {"exit": 3, "controls_accepted_all_stages": 0,
                              "valid_for_calibration": False}),
    ("R2_pins_rebound_and_controls_rebased", {"exit": 0, "controls_accepted_all_stages": 3,
                                              "valid_for_calibration": True}),
    ("R3a_key_kept_row_removed", {"exit": 3, "structural_R22_on_controls": True}),
    ("R3b_row_kept_key_removed", {"exit": 3, "structural_R28_on_controls": True}),
    ("R4_stale_row_reinserted", {"exit": 3, "structural_R28_on_controls": True}),
    ("R5_determinism_rerun_of_R2", {"exit": 0, "identical_observed_to_R2": True}),
])


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def measure_inputs() -> dict:
    return {rel: ({"sha256": sha(REPO / rel), "bytes": (REPO / rel).stat().st_size}
                  if (REPO / rel).exists() else {"sha256": None, "bytes": None})
            for rel in FROZEN_INPUTS + TOOLS + [f"{SUITE_REL}/manifest.json",
                                                f"{SUITE_REL}/run_contract_tests.py"]
            + [f"{SUITE_REL}/fixtures/controls/{n}" for n in CONTROL_NAMES]}


# --------------------------------------------------------------------------- staging
def stage_sandbox(mutate) -> Path:
    """Fresh sandbox with the minimal repo subset; `mutate(stage)` may edit it."""
    if STAGE_ROOT.exists():
        shutil.rmtree(STAGE_ROOT)
    (STAGE_ROOT / SUITE_REL / "fixtures").mkdir(parents=True)
    for rel in TOOLS:
        dst = STAGE_ROOT / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO / rel, dst)
    for rel in CANON_SCHEMAS:
        dst = STAGE_ROOT / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO / rel, dst)
    for rel in [f"{SUITE_REL}/manifest.json", f"{SUITE_REL}/run_contract_tests.py"]:
        shutil.copy2(REPO / rel, STAGE_ROOT / rel)
    shutil.copytree(REPO / SUITE_REL / "fixtures", STAGE_ROOT / SUITE_REL / "fixtures",
                    dirs_exist_ok=True)
    mutate(STAGE_ROOT)
    return STAGE_ROOT


def rebind_canonical_pins(stage: Path) -> dict:
    """Point the three conforming_canonical_controls pins at the staged canonical bytes."""
    man = stage / SUITE_REL / "manifest.json"
    d = json.loads(man.read_text())
    changes = {}
    for e in d["conforming_canonical_controls"]:
        new = sha(stage / e["fixture"])
        if new != e["sha256"]:
            changes[e["test_id"]] = {"fixture": e["fixture"],
                                     "old": e["sha256"], "new": new}
            e["sha256"] = new
    man.write_text(json.dumps(d, indent=1) + "\n")
    return changes


# ------------------------------------------------------------------ control rebasing
def _toplevel(node, key):
    for k, v in node.value:
        if k.value == key:
            return v
    return None


def _row_pair(item):
    pair = _toplevel(item, "pair")
    if pair is None:
        return None
    return [x.value for x in pair.value]


def control_edits(text: str, drop_row: bool, drop_key: bool):
    """Return (new_text, edits). Text-level, comment-preserving; validated afterwards."""
    edits = []
    root = yaml.compose(text)
    drop_lines = []
    if drop_row:
        tf = _toplevel(_toplevel(root, "genericity"), "transfer_failures")
        for item in tf.value:
            if _row_pair(item) == STALE_ROW:
                drop_lines += list(range(item.start_mark.line, item.end_mark.line))
                edits.append({"edit": "remove_duplicate_transfer_failures_row",
                              "pair": STALE_ROW,
                              "lines_removed": [item.start_mark.line + 1, item.end_mark.line]})
                break
    if drop_key:
        kv = _toplevel(root, STALE_KEY)
        if kv is not None:
            drop_lines += list(range(kv.start_mark.line, kv.end_mark.line + 1))
            edits.append({"edit": "remove_unknown_top_level_key",
                          "key": STALE_KEY,
                          "lines_removed": [kv.start_mark.line + 1, kv.end_mark.line + 1]})
    lines = text.splitlines(keepends=True)
    out = [ln for i, ln in enumerate(lines) if i not in set(drop_lines)]
    return "".join(out), edits


def validate_edit(orig: str, new: str, drop_row: bool, drop_key: bool) -> dict:
    a, b = yaml.safe_load(orig), yaml.safe_load(new)
    ok = True
    if drop_row:
        tf_b = [r["pair"] for r in b["genericity"]["transfer_failures"]]
        ok &= STALE_ROW not in tf_b
        th_b = [r["pair"] for r in b["genericity"].get("transfer_holds", [])]
        ok &= STALE_ROW in th_b                     # kept in holds, only the duplicate goes
        if not ok:
            return {"valid": False, "reason": "row not removed as intended"}
    if drop_key:
        ok &= STALE_KEY not in b
    # everything else must be byte-equal after round-trip of the data model
    def strip(d):
        d = json.loads(json.dumps(d))
        d.get("genericity", {}).get("transfer_failures") and None
        return d
    a2, b2 = strip(a), strip(b)
    if drop_row:
        a2["genericity"]["transfer_failures"] = [
            r for r in a2["genericity"]["transfer_failures"]
            if not (isinstance(r, dict) and r.get("pair") == STALE_ROW)]
    if drop_key:
        a2.pop(STALE_KEY, None)
    equal = a2 == b2
    return {"valid": bool(ok and equal), "data_equal_except_intended": equal,
            "comments_preserved": orig.count("#") == new.count("#")}


def write_patched_controls(controls: dict, with_row: bool, with_key: bool) -> list:
    PATCHED.mkdir(parents=True, exist_ok=True)
    out = []
    for name, text in controls.items():
        new, edits = control_edits(text, drop_row=not with_row, drop_key=not with_key)
        v = validate_edit(text, new, drop_row=not with_row, drop_key=not with_key)
        out.append({"control": name, "edits": edits, "validation": v,
                    "patched_sha256": hashlib.sha256(new.encode()).hexdigest()})
        if not v["valid"]:
            raise SystemExit(f"FATAL: edit validation failed for {name}: {v}")
        (PATCHED / name).write_text(new)
    return out


def apply_controls(stage: Path, name_map: dict, with_row: bool, with_key: bool) -> list:
    """Write rebased controls into the sandbox and return the edit record."""
    recs = []
    for name, text in name_map.items():
        new, edits = control_edits(text, drop_row=not with_row, drop_key=not with_key)
        v = validate_edit(text, new, drop_row=not with_row, drop_key=not with_key)
        if not v["valid"]:
            raise SystemExit(f"FATAL: edit validation failed for {name}: {v}")
        dst = stage / SUITE_REL / "fixtures" / "controls" / name
        dst.write_text(new)
        recs.append({"control": name, "edits": edits, "validation": v,
                     "sha256": hashlib.sha256(new.encode()).hexdigest()})
    return recs


def repin_controls(stage: Path) -> list:
    man = stage / SUITE_REL / "manifest.json"
    d = json.loads(man.read_text())
    out = []
    for e in d["controls"]:
        p = stage / SUITE_REL / e["fixture"]
        new = sha(p)
        if new != e["sha256"]:
            out.append({"test_id": e["test_id"], "old": e["sha256"], "new": new})
            e["sha256"] = new
    man.write_text(json.dumps(d, indent=1) + "\n")
    return out


def reinsert_stale_row(stage: Path) -> dict:
    """Negative control R4: re-add the duplicate row to every rebased control."""
    man = stage / SUITE_REL / "manifest.json"
    d = json.loads(man.read_text())
    recs = []
    for e in d["controls"]:
        p = stage / SUITE_REL / e["fixture"]
        text = p.read_text()
        root = yaml.compose(text)
        tf = _toplevel(_toplevel(root, "genericity"), "transfer_failures")
        last = tf.value[-1]
        insert_at = last.end_mark.line
        template = ("  - pair:\n    - finite_codimension_complement\n    - residual_comeager\n"
                    "    direction: transfers\n    witness: a countable union of proper closed "
                    "finite-codimension submanifolds is meager\n    status: elementary\n"
                    "    citation_status: n/a\n")
        lines = text.splitlines(keepends=True)
        new = "".join(lines[:insert_at]) + template + "".join(lines[insert_at:])
        ok = STALE_ROW in [r["pair"] for r in yaml.safe_load(new)["genericity"]["transfer_failures"]]
        if not ok:
            raise SystemExit("FATAL: R4 re-insert did not take")
        p.write_text(new)
        e["sha256"] = sha(p)
        recs.append({"control": e["fixture"], "reinserted": True})
    man.write_text(json.dumps(d, indent=1) + "\n")
    return {"controls": recs}


# ------------------------------------------------------------------------ suite runs
def run_suite(tag: str) -> dict:
    runner = STAGE_ROOT / SUITE_REL / "run_contract_tests.py"
    t0 = time.time()
    proc = subprocess.run([sys.executable, str(runner)], capture_output=True, text=True,
                          timeout=3600)
    dt = time.time() - t0
    RUNS.mkdir(parents=True, exist_ok=True)
    (RUNS / f"{tag}_stdout.txt").write_text(proc.stdout + "\n--- stderr ---\n" + proc.stderr)
    obs_path = STAGE_ROOT / SUITE_REL / "observed_verdicts.json"
    obs = json.loads(obs_path.read_text()) if obs_path.exists() else None
    if obs is not None:
        shutil.copy2(obs_path, RUNS / f"{tag}_observed.json")
    return {"tag": tag, "exit": proc.returncode, "seconds": round(dt, 1),
            "stdout_tail": proc.stdout.strip().splitlines()[-3:],
            "integrity_errors": [l.strip() for l in proc.stdout.splitlines()
                                 if l.strip().startswith("- ")],
            "observed": obs}


def grade(run: dict) -> dict:
    """Pre-registered, machine-readable summary of one run."""
    obs = run["observed"]
    out = {"exit": run["exit"], "integrity_error_count": len(run["integrity_errors"]),
           "integrity_errors": run["integrity_errors"]}
    if not obs:
        out["ran"] = False
        return out
    s = obs["summary"]
    res = {r["test_id"]: r for r in obs["results"]}
    controls = [r for r in obs["results"] if r["kind"] == "frozen_control"]
    conforming = [r for r in obs["results"] if r["kind"] == "conforming_canonical"]
    mutants = [r for r in obs["results"] if r["kind"] == "leak_mutant"]
    out.update({
        "ran": True,
        "valid_for_calibration": obs["validity"]["valid_for_calibration"],
        "mutants": {"total": len(mutants),
                    "structural_caught": s["structural_caught"],
                    "semantic_baseline_caught": s["semantic_baseline_caught"],
                    "semantic_hardened_caught": s["semantic_hardened_caught"],
                    "escapes_adopted": s["escaped_adopted_stages"],
                    "hardened_only": s["hardened_only_catches"]},
        "controls_accepted_all_stages": sum(
            1 for r in controls if len(r["observed"]["accepted_by"]) == 3 and not r["observed"]["rejected_by"]),
        "controls_detail": {r["test_id"]: {"accepted_by": r["observed"]["accepted_by"],
                                           "rejected_by": r["observed"]["rejected_by"],
                                           "structural_failed_rules":
                                               r["observed"]["stages"]["structural"]["failed_rules"]}
                            for r in controls},
        "conforming_canonical_accepted": sum(
            1 for r in conforming if len(r["observed"]["accepted_by"]) == 3 and not r["observed"]["rejected_by"]),
        "stage_hashes": obs["stage_hashes"],
        "observed_verdicts_sha256": hashlib.sha256(
            (RUNS / f"{run['tag']}_observed.json").read_bytes()).hexdigest(),
        "per_test_observed": {tid: r["observed"]["verdict"] for tid, r in res.items()},
    })
    return out


def check(tag: str, got: dict, exp: dict) -> list:
    fails = []
    for k, v in exp.items():
        if k == "integrity_errors":
            if got.get("integrity_error_count") != v:
                fails.append(f"{tag}: integrity_errors {got.get('integrity_error_count')} != {v}")
        elif k == "controls_accepted_all_stages":
            if got.get(k) != v:
                fails.append(f"{tag}: {k} {got.get(k)} != {v}")
        elif k == "structural_R22_on_controls":
            hit = any("R22" in (d["structural_failed_rules"] or [])
                      for d in got.get("controls_detail", {}).values())
            if hit != v:
                fails.append(f"{tag}: structural R22 on controls {hit} != {v}")
        elif k == "structural_R28_on_controls":
            hit = any("R28" in (d["structural_failed_rules"] or [])
                      for d in got.get("controls_detail", {}).values())
            if hit != v:
                fails.append(f"{tag}: structural R28 on controls {hit} != {v}")
        elif got.get(k) != v:
            fails.append(f"{tag}: {k} {got.get(k)} != {v}")
    return fails


# ------------------------------------------------------------------------------ main
def main() -> int:
    pre = measure_inputs()
    results, runs, failures = OrderedDict(), OrderedDict(), []

    # R0 — canonical manifest at the current frozen revision.
    stage_sandbox(lambda s: None)
    runs["R0_canonical_manifest"] = run_suite("R0")
    results["R0_canonical_manifest"] = grade(runs["R0_canonical_manifest"])
    failures += check("R0", results["R0_canonical_manifest"], EXPECTATIONS["R0_canonical_manifest"])

    # R1 — pins rebound only (isolates the control-layout staleness).
    def m1(s):
        repin = rebind_canonical_pins(s)
        (HERE / "run_meta_R1_pin_rebind.json").write_text(json.dumps(repin, indent=1) + "\n")
    stage_sandbox(m1)
    runs["R1_pins_rebound_only"] = run_suite("R1")
    results["R1_pins_rebound_only"] = grade(runs["R1_pins_rebound_only"])
    failures += check("R1", results["R1_pins_rebound_only"], EXPECTATIONS["R1_pins_rebound_only"])

    # R2 — pins rebound + the two minimal control edits.
    controls_src = {n: (REPO / SUITE_REL / "fixtures" / "controls" / n).read_text()
                    for n in CONTROL_NAMES}
    edit_record = write_patched_controls(controls_src, with_row=False, with_key=False)
    (HERE / "control_edits.json").write_text(json.dumps(edit_record, indent=1) + "\n")

    def m2(s):
        apply_controls(s, controls_src, with_row=False, with_key=False)
        repin_controls(s)
        rebind_canonical_pins(s)
    stage_sandbox(m2)
    # persist the staged (rebased) manifest for review; rebased controls are in patched_controls/
    shutil.copy2(STAGE_ROOT / SUITE_REL / "manifest.json", HERE / "manifest_rebased.json")
    runs["R2_pins_rebound_and_controls_rebased"] = run_suite("R2")
    results["R2_pins_rebound_and_controls_rebased"] = grade(runs["R2_pins_rebound_and_controls_rebased"])
    failures += check("R2", results["R2_pins_rebound_and_controls_rebased"],
                      EXPECTATIONS["R2_pins_rebound_and_controls_rebased"])

    # R3a — row removed, unknown key kept -> R22 must still fire.
    stage_sandbox(lambda s: (apply_controls(s, controls_src, with_row=False, with_key=True),
                             repin_controls(s), rebind_canonical_pins(s)))
    runs["R3a_key_kept_row_removed"] = run_suite("R3a")
    results["R3a_key_kept_row_removed"] = grade(runs["R3a_key_kept_row_removed"])
    failures += check("R3a", results["R3a_key_kept_row_removed"], EXPECTATIONS["R3a_key_kept_row_removed"])

    # R3b — key removed, stale row kept -> R28 must still fire.
    stage_sandbox(lambda s: (apply_controls(s, controls_src, with_row=True, with_key=False),
                             repin_controls(s), rebind_canonical_pins(s)))
    runs["R3b_row_kept_key_removed"] = run_suite("R3b")
    results["R3b_row_kept_key_removed"] = grade(runs["R3b_row_kept_key_removed"])
    failures += check("R3b", results["R3b_row_kept_key_removed"], EXPECTATIONS["R3b_row_kept_key_removed"])

    # R4 — fully rebased controls, stale row re-inserted -> R28 must still fire.
    stage_sandbox(lambda s: (apply_controls(s, controls_src, with_row=False, with_key=False),
                             repin_controls(s), rebind_canonical_pins(s), reinsert_stale_row(s)))
    runs["R4_stale_row_reinserted"] = run_suite("R4")
    results["R4_stale_row_reinserted"] = grade(runs["R4_stale_row_reinserted"])
    failures += check("R4", results["R4_stale_row_reinserted"], EXPECTATIONS["R4_stale_row_reinserted"])

    # R5 — determinism: fresh sandbox, repeat R2, compare per-test observed verdicts.
    stage_sandbox(lambda s: (apply_controls(s, controls_src, with_row=False, with_key=False),
                             repin_controls(s), rebind_canonical_pins(s)))
    runs["R5_determinism_rerun_of_R2"] = run_suite("R5")
    results["R5_determinism_rerun_of_R2"] = grade(runs["R5_determinism_rerun_of_R2"])
    det = (results["R5_determinism_rerun_of_R2"].get("per_test_observed")
           == results["R2_pins_rebound_and_controls_rebased"].get("per_test_observed"))
    results["R5_determinism_rerun_of_R2"]["identical_observed_to_R2"] = det
    failures += check("R5", results["R5_determinism_rerun_of_R2"], EXPECTATIONS["R5_determinism_rerun_of_R2"])

    post = measure_inputs()
    drift = {k: [pre[k], post[k]] for k in pre if pre[k] != post[k]}

    report = {
        "task_id": "W080-SEMCT-REBASE-01",
        "worker": "worker-080",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "node_ids": ["A1"],
        "gate": "G-AUDIT",
        "statement_kind": "measured artifact/calibration evidence (no gate verdict, no node status)",
        "question": ("Can ADJ-CONTROL-STALENESS be resolved by rebasing the three frozen "
                     "controls to the FROZEN rev27 canonical layout (mutants untouched), and "
                     "does the suite then run and validate at the frozen revision?"),
        "pre_registered_expectations": EXPECTATIONS,
        "expectations_met": not failures,
        "expectation_failures": failures,
        "inputs_before": pre,
        "inputs_after": post,
        "input_drift_during_run": drift,
        "frozen_revision": json.loads((REPO / "artifacts/formulation/FROZEN.json").read_text()).get("revision"),
        "run_meta": {
            "sandbox": str(STAGE_ROOT.relative_to(REPO)),
            "runner": f"{SUITE_REL}/run_contract_tests.py",
            "structural_tool_sha256": sha(REPO / TOOLS[0]),
            "semantic_tool_sha256": sha(REPO / TOOLS[3]),
            "key_manifest_sha256": sha(REPO / TOOLS[2]),
            "rule_spec_sha256": sha(REPO / TOOLS[1]),
        },
        "control_edits": edit_record,
        "runs": {k: {kk: vv for kk, vv in v.items() if kk != "observed"} for k, v in runs.items()},
        "grades": results,
        "conclusion": (
            "See grades: each run's pre-registered expectation is checked mechanically. "
            "R2 is the candidate resolution; R3a/R3b/R4 are executed negative controls "
            "showing each edit is necessary and that the structural gate still fires on "
            "the stale row and the unknown key."
        ),
        "falsifier": (
            "Re-run this harness (`python3 artifacts/worker-080/semct_rebase/rebase_semct.py`) "
            "at the same input hashes: any run whose exit code, integrity-error count, control "
            "acceptance, mutant counts, or per-test observed verdicts differ from the recorded "
            "grades falsifies the corresponding clause; any input-hash drift listed in "
            "input_drift_during_run voids the report at those paths; a rebased control accepted "
            "by the structural stage while still carrying the duplicate transfer_failures row, or "
            "while still carrying revised_at_unused, falsifies the necessity claim of that edit."
        ),
        "limits": [
            "Worker-side candidate patch only: no canonical path was written; lead-formulation owns ADJ-CONTROL-STALENESS.",
            "The rebased controls are calibration controls, not mutants; the 32-mutant corpus is byte-untouched (see grades.*.mutants equal across runs).",
            "valid_for_calibration=true in R2 is a mechanical property of the suite's own runner; it is not a gate verdict and implies nothing about mathematical truth or non-vacuity.",
            "The staged sandbox pins copies; hashes of every input are recorded before and after.",
        ],
    }
    (HERE / "report.json").write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps({"expectations_met": report["expectations_met"],
                      "failures": failures,
                      "exits": {k: v["exit"] for k, v in results.items()},
                      "R2_valid": results["R2_pins_rebound_and_controls_rebased"].get("valid_for_calibration"),
                      "input_drift": drift}, indent=1))
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
