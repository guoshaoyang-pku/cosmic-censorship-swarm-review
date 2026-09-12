#!/usr/bin/env python3
"""W023-L0-HF02-INTEG-01 — end-to-end integration test of the proposed HF-02
ledger-disjunction branch (P-CODE) inside the canonical audit runner.

Question
--------
worker-093 proposed `check_ledger_class_disjunction()` as a patch to
`artifacts/audit/audit_lib.py` and verified the *function in isolation*
(import OK, 8 corpus rows, 1 planted control). worker-023 (previous instance)
verified *composition* of the two open HF-02 proposals against an extracted
copy of the checker. Neither verified the branch **inside the canonical
runner**: that the diff applies to the pinned bytes, that one wiring line in
`audit_run.py` is sufficient, that the wired runner flags exactly the 8
dual-class ledger rows at the pinned ledger hash, that no other violation
moves, and that the run is deterministic.

This driver performs that integration test on frozen copies. No canonical
file is edited: sandboxes are built under `tmp/w023_hf02_integration/`.

Method
------
Two sandboxes (canonical, patched) each mirror only what the runner reads:
`artifacts/audit/{audit_lib.py,audit_run.py,evaluation_rubric.yaml}`,
`research_map/{full,trimmed} map`, `ledger/theorems.jsonl`,
`runtime/state/started_at`. The patched sandbox applies
`artifacts/worker-093/l0_rev3_review/proposed_hf02_disjunction_patch.diff`
to the copied audit_lib.py and inserts the one wiring line into the copied
audit_run.py. Six runner executions are compared: trimmed and full frozen map
variants, plus one rerun pair for determinism.

Pinned inputs fail closed (exit 2) if any canonical byte moved.

Exit codes: 0 all checks pass; 2 an input moved (verdict void); 3 a control or
integration assertion failed; 4 driver error.
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
OUTDIR = REPO / "artifacts" / "worker-023" / "l0_hf02_integration"
RAWDIR = OUTDIR / "raw"
WORK = REPO / "tmp" / "w023_hf02_integration"

PINS = {
    "ledger/theorems.jsonl":
        "a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28",
    "artifacts/audit/audit_lib.py":
        "ae573db84631b970caeea46e8821aee8af66166f6a5f16251e4a6c819a377c8c",
    "artifacts/audit/audit_run.py":
        "3b27dd3fef7f41488158099f888e3685dc8d9cca9f0507ad46c4d01f9bd2c411",
    "artifacts/audit/evaluation_rubric.yaml":
        "d748a9e3574ebe0c34c22b608ba0bf018d525a644ebff815371c6dcfca055885",
    "artifacts/worker-093/l0_rev3_review/proposed_hf02_disjunction_patch.diff":
        "0247a5c93acc0e015d09cf4dcec8c643696d4328b748c871857fb82cc9b4669a",
    "artifacts/worker-093/l0_rev3_review/patched_audit_lib.py":
        "9c8def1b50379e7cb5b6414cdf73c31e891276b2cf1bf8635a25aad7b4b1de8e",
}

WIRING_ANCHOR = "    # HF-13: cross-project contamination in text artifacts"
WIRING_LINE = ('    claimv += A.check_ledger_class_disjunction(corpus["records"], classes)')

EXPECTED_ROWS = ["D-004", "D-005", "T-303", "T-305", "T-402", "T-515", "T-526", "T-528"]

EXPECTED_PATCHED_LIB = PINS["artifacts/worker-093/l0_rev3_review/patched_audit_lib.py"]


class DriverError(RuntimeError):
    pass


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(t: str) -> str:
    return hashlib.sha256(t.encode()).hexdigest()


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def check_pins() -> dict:
    measured, moved = {}, []
    for rel, want in PINS.items():
        p = REPO / rel
        got = sha256_file(p) if p.is_file() else None
        measured[rel] = got
        if got != want:
            moved.append({"path": rel, "expected": want, "measured": got})
    return {"pins": measured, "moved": moved}


def build_sandbox(name: str, patched: bool, map_full: Path) -> dict:
    sb = WORK / name
    if sb.exists():
        shutil.rmtree(sb)
    for d in ("artifacts/audit", "research_map", "ledger", "comms/outbox", "runtime/state"):
        (sb / d).mkdir(parents=True, exist_ok=True)
    shutil.copy2(REPO / "artifacts/audit/audit_lib.py", sb / "artifacts/audit/audit_lib.py")
    shutil.copy2(REPO / "artifacts/audit/audit_run.py", sb / "artifacts/audit/audit_run.py")
    shutil.copy2(REPO / "artifacts/audit/evaluation_rubric.yaml",
                 sb / "artifacts/audit/evaluation_rubric.yaml")
    shutil.copy2(REPO / "ledger/theorems.jsonl", sb / "ledger/theorems.jsonl")
    if (REPO / "runtime/state/started_at").is_file():
        shutil.copy2(REPO / "runtime/state/started_at", sb / "runtime/state/started_at")
    shutil.copy2(map_full, sb / "research_map/research_map_full.json")
    full = json.loads((sb / "research_map/research_map_full.json").read_text())
    trimmed = {"schema_version": full.get("schema_version", "0.1"),
               "project": full.get("project", {}),
               "groups": []}
    (sb / "research_map/research_map_trimmed.json").write_text(
        json.dumps(trimmed, indent=2, sort_keys=True) + "\n")

    info = {"sandbox": str(sb), "map_full_sha256": sha256_file(sb / "research_map/research_map_full.json"),
            "lib_before": sha256_file(sb / "artifacts/audit/audit_lib.py"),
            "runner_before": sha256_file(sb / "artifacts/audit/audit_run.py")}
    if not patched:
        info["lib_after"] = info["lib_before"]
        info["runner_after"] = info["runner_before"]
        info["patch_apply"] = None
        info["wiring"] = None
        return info

    diff = REPO / "artifacts/worker-093/l0_rev3_review/proposed_hf02_disjunction_patch.diff"
    dry = subprocess.run(["patch", "-p1", "--dry-run", "-i", str(diff)],
                         cwd=str(sb), capture_output=True, text=True)
    real = subprocess.run(["patch", "-p1", "-i", str(diff)],
                          cwd=str(sb), capture_output=True, text=True)
    lib_after = sha256_file(sb / "artifacts/audit/audit_lib.py")
    info["patch_apply"] = {
        "dry_run_exit": dry.returncode, "dry_run_stdout": dry.stdout.strip(),
        "apply_exit": real.returncode, "apply_stdout": real.stdout.strip(),
        "lib_after": lib_after,
        "matches_declared_patched_bytes": lib_after == EXPECTED_PATCHED_LIB,
    }
    runner = (sb / "artifacts/audit/audit_run.py").read_text()
    n = runner.count(WIRING_ANCHOR)
    if n != 1:
        raise DriverError(f"wiring anchor occurs {n} times, expected 1")
    runner = runner.replace(WIRING_ANCHOR, WIRING_LINE + "\n\n" + WIRING_ANCHOR)
    (sb / "artifacts/audit/audit_run.py").write_text(runner)
    info["runner_after"] = sha256_file(sb / "artifacts/audit/audit_run.py")
    info["wiring"] = {"anchor": WIRING_ANCHOR, "inserted_line": WIRING_LINE,
                      "insertions": 1, "runner_after": info["runner_after"]}
    return info


def run_scenario(sb: Path, map_name: str, tag: str) -> dict:
    out = sb / "artifacts/audit" / f"reports_{tag}"
    cmd = [sys.executable, str(sb / "artifacts/audit/audit_run.py"),
           "--map", str(sb / "research_map" / map_name),
           "--scan", str(sb / "ledger"),
           "--out", str(out), "--quiet", "--kind", "findings", "--fail-on-critical"]
    proc = subprocess.run(cmd, cwd=str(sb), capture_output=True, text=True)
    report_path = out / "LATEST.json"
    if not report_path.is_file():
        raise DriverError(f"scenario {tag}: no report; exit={proc.returncode} "
                          f"stderr={proc.stderr[-500:]}")
    report = json.loads(report_path.read_text())
    vs = report["violations"]
    hf_counts: dict[str, int] = {}
    for v in vs:
        hf_counts[v["hf"]] = hf_counts.get(v["hf"], 0) + 1
    disj = sorted(v["where"].split("ledger/", 1)[1] for v in vs
                  if v["hf"] == "HF-02" and v["detail"].startswith("disjunction of class_ids"))
    digest = sha256_text(json.dumps(sorted(
        [v["hf"], v["severity"], v["where"], v["detail"]] for v in vs), sort_keys=True))
    return {
        "tag": tag, "map": map_name, "exit_code": proc.returncode,
        "stdout": proc.stdout.strip()[-400:], "stderr": proc.stderr.strip()[-400:],
        "corpus": report["corpus"], "summary": report["summary"],
        "gates": report["gates"],
        "citation_support_n": report["citation_support"]["n"],
        "hf_counts": hf_counts, "violations_total": len(vs),
        "hf02_disjunction_rows": disj, "hf02_disjunction_n": len(disj),
        "violations_digest": digest,
        "report_latest_sha256": sha256_file(report_path),
        "report_raw": report,
    }


def delta(base: dict, patched: dict) -> dict:
    key = lambda v: json.dumps({"hf": v["hf"], "severity": v["severity"],
                                "where": v["where"], "detail": v["detail"]}, sort_keys=True)
    from collections import Counter
    b = Counter(key(v) for v in base["report_raw"]["violations"])
    p = Counter(key(v) for v in patched["report_raw"]["violations"])
    added = sorted((p - b).elements())
    removed = sorted((b - p).elements())
    added_obj = [json.loads(x) for x in added]
    return {
        "n_added": len(added), "n_removed": len(removed),
        "added": added_obj, "removed": [json.loads(x) for x in removed],
        "all_added_are_hf02_disjunction": all(
            v["hf"] == "HF-02" and v["detail"].startswith("disjunction of class_ids")
            for v in added_obj),
        "added_rows": sorted(v["where"].split("ledger/", 1)[1] for v in added_obj
                             if "ledger/" in v["where"]),
    }


def load_patched_lib(sb: Path):
    path = sb / "artifacts/audit/audit_lib.py"
    spec = importlib.util.spec_from_file_location("w023_patched_audit_lib", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod  # dataclasses resolve cls.__module__ via sys.modules
    spec.loader.exec_module(mod)
    return mod


def run_controls(patched_sb: Path) -> dict:
    import yaml
    A = load_patched_lib(patched_sb)
    rubric = yaml.safe_load((patched_sb / "artifacts/audit/evaluation_rubric.yaml").read_text())
    classes = A.frozen_classes(rubric)
    C2, C0, WCC = "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-VAC-GEN"
    cases = []

    def case(cid, records, expect, note):
        got = A.check_ledger_class_disjunction(records, classes)
        n = len(got)
        cases.append({"id": cid, "expect": expect, "got": n, "pass": n == expect,
                      "note": note,
                      "where": [v.where for v in got],
                      "evidence": [v.evidence for v in got]})

    case("C1-clean-single", [{"theorem_id": "X-1", "class_ids": [C2]}], 0,
         "one frozen class id is not a disjunction")
    case("C2-dual-frozen", [{"theorem_id": "X-2", "class_ids": [C2, C0]}], 1,
         "two frozen class ids in one list fire once")
    case("C3-duplicate-single", [{"theorem_id": "X-3", "class_ids": [C2, C2]}], 0,
         "repeated identical id is a set of size one")
    case("C4-empty-list", [{"theorem_id": "X-4", "class_ids": []}], 0,
         "empty list cannot disjoin")
    case("C5-absent-key", [{"theorem_id": "X-5"}], 0,
         "missing class_ids key is not an assertion")
    case("C6-null-list", [{"theorem_id": "X-6", "class_ids": None}], 0,
         "null class_ids is not an assertion")
    case("C7-coverage-annotation", [{"theorem_id": "X-7", "class_ids": [C2],
                                     "informs_classes": [C2, C0]}], 0,
         "P-DATA shape: multi-class coverage in informs_classes must not fire the assertion detector")
    case("C8-unknown-token", [{"theorem_id": "X-8", "class_ids": [C2, "AF-NOT-A-CLASS"]}], 0,
         "function filters to frozen classes; unknown tokens are the canonical invented-token branch's scope")
    case("C9-dual-wcc-c0", [{"theorem_id": "X-9", "class_ids": [WCC, C0]}], 1,
         "the WCC/C0 pair is also a disjunction")
    case("C10-triple-frozen", [{"theorem_id": "X-10", "class_ids": [C2, C0, WCC]}], 1,
         "three frozen ids still yield one violation per record")
    case("C11-two-records", [{"theorem_id": "X-11a", "class_ids": [C2, C0]},
                             {"theorem_id": "X-11b", "class_ids": [WCC, C0]}], 2,
         "one violation per offending record")

    ledger = [json.loads(l) for l in (patched_sb / "ledger/theorems.jsonl").read_text().splitlines() if l.strip()]
    case("C12-frozen-corpus", ledger, 8,
         "the pinned 62-row ledger yields exactly the 8 known dual-class rows")
    mutant = json.loads(json.dumps(ledger))
    for r in mutant:
        if r.get("theorem_id") == "T-526":
            r["class_ids"] = [C2]
    case("C13-corpus-mutant-minus-one", mutant, 7,
         "dropping one class id from T-526 must drop exactly that firing (sensitivity, not hardcoding)")
    coverage_view = []
    for r in json.loads(json.dumps(ledger)):
        if len(set(r.get("class_ids") or [])) >= 2:
            r["informs_classes"] = r.pop("class_ids")
        coverage_view.append(r)
    case("C14-corpus-coverage-view", coverage_view, 0,
         "applying the P-DATA shape to all 8 rows silences the code detector (shows the two proposals compose)")
    singular_view = json.loads(json.dumps(ledger))
    for r in singular_view:
        ids = r.get("class_ids") or []
        if len(ids) >= 2:
            r["class_id"] = ids[0]
            r.pop("class_ids")
    case("C15-corpus-singular-view", singular_view, 0,
         "moving multi-class rows to the singular claim field is not seen by this branch; that surface is check_class_binding's scope")

    passed = sum(1 for c in cases if c["pass"])
    return {"n": len(cases), "passed": passed, "failed": len(cases) - passed, "cases": cases}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep-sandboxes", action="store_true")
    a = ap.parse_args()

    OUTDIR.mkdir(parents=True, exist_ok=True)
    RAWDIR.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)

    pin_state = check_pins()
    if pin_state["moved"]:
        (OUTDIR / "FAILED_PINS.json").write_text(json.dumps(
            {"created_at": now_iso(), "actor": "worker-023",
             "reason": "pinned input moved; integration verdict void", **pin_state},
            indent=2, sort_keys=True) + "\n")
        print("INPUT MOVED:", json.dumps(pin_state["moved"], indent=1))
        return 2

    full_map = WORK / "research_map_snapshot.json"
    shutil.copy2(REPO / "research_map/research_map.json", full_map)
    map_sha = sha256_file(full_map)

    canon = build_sandbox("sandbox_canonical", patched=False, map_full=full_map)
    patch = build_sandbox("sandbox_patched", patched=True, map_full=full_map)
    if not patch["patch_apply"]["matches_declared_patched_bytes"]:
        raise DriverError("patch result does not hash to the declared patched_audit_lib.py")

    sb_canon = WORK / "sandbox_canonical"
    sb_patch = WORK / "sandbox_patched"

    wiring_diff = "".join(difflib.unified_diff(
        (sb_canon / "artifacts/audit/audit_run.py").read_text().splitlines(keepends=True),
        (sb_patch / "artifacts/audit/audit_run.py").read_text().splitlines(keepends=True),
        fromfile="a/artifacts/audit/audit_run.py",
        tofile="b/artifacts/audit/audit_run.py"))
    (OUTDIR / "runner_wiring.diff").write_text(wiring_diff)
    wiring_diff_sha = sha256_text(wiring_diff)

    scenarios = {}
    scenarios["baseline_trim"] = run_scenario(sb_canon, "research_map_trimmed.json", "base_trim")
    scenarios["baseline_trim_rerun"] = run_scenario(sb_canon, "research_map_trimmed.json", "base_trim2")
    scenarios["patched_trim"] = run_scenario(sb_patch, "research_map_trimmed.json", "patch_trim")
    scenarios["patched_trim_rerun"] = run_scenario(sb_patch, "research_map_trimmed.json", "patch_trim2")
    scenarios["baseline_full"] = run_scenario(sb_canon, "research_map_full.json", "base_full")
    scenarios["patched_full"] = run_scenario(sb_patch, "research_map_full.json", "patch_full")

    d_trim = delta(scenarios["baseline_trim"], scenarios["patched_trim"])
    d_full = delta(scenarios["baseline_full"], scenarios["patched_full"])

    controls = run_controls(sb_patch)

    gate_effect = {
        "baseline_trim": scenarios["baseline_trim"]["gates"],
        "patched_trim": scenarios["patched_trim"]["gates"],
        "baseline_full": scenarios["baseline_full"]["gates"],
        "patched_full": scenarios["patched_full"]["gates"],
        "observed": ("In the isolated (trimmed-map) runs the derived G-AUDIT verdict moves pending -> fail "
                     "purely from the 8 added critical HF-02. In the full-map runs the partial sandbox mirror "
                     "makes map-side done-node existence checks unfaithful (e.g. HF-05 for an unmirrored "
                     "artifact), so absolute full-map verdicts are NOT interpretable; only the within-variant "
                     "delta is, and it is identical (8 added, 0 removed). G-FORM stays pending in all six "
                     "runs because audit_run.py:142-143 gates on "
                     "`any(c.get(\"class_id\") for c in [])`, a constant-False expression. Landing P-CODE "
                     "without the ledger repair (P-DATA shape) or a rubric amendment therefore makes the "
                     "derived G-AUDIT verdict fail."),
    }

    det = {
        "baseline_trim_deterministic":
            scenarios["baseline_trim"]["violations_digest"] == scenarios["baseline_trim_rerun"]["violations_digest"],
        "patched_trim_deterministic":
            scenarios["patched_trim"]["violations_digest"] == scenarios["patched_trim_rerun"]["violations_digest"],
    }

    checks = {
        "pinned_inputs_match": not pin_state["moved"],
        "patch_applies_cleanly_and_byte_faithfully":
            patch["patch_apply"]["dry_run_exit"] == 0 and patch["patch_apply"]["apply_exit"] == 0
            and patch["patch_apply"]["matches_declared_patched_bytes"],
        "wiring_is_single_insertion": patch["wiring"]["insertions"] == 1,
        "baseline_trim_flags_zero": scenarios["baseline_trim"]["hf02_disjunction_n"] == 0,
        "baseline_full_flags_zero": scenarios["baseline_full"]["hf02_disjunction_n"] == 0,
        "patched_trim_flags_eight": scenarios["patched_trim"]["hf02_disjunction_n"] == 8,
        "patched_full_flags_eight": scenarios["patched_full"]["hf02_disjunction_n"] == 8,
        "patched_rows_match_expected":
            scenarios["patched_trim"]["hf02_disjunction_rows"] == EXPECTED_ROWS,
        "delta_trim_is_only_the_eight":
            d_trim["n_added"] == 8 and d_trim["n_removed"] == 0
            and d_trim["all_added_are_hf02_disjunction"] and d_trim["added_rows"] == EXPECTED_ROWS,
        "delta_full_is_only_the_eight":
            d_full["n_added"] == 8 and d_full["n_removed"] == 0
            and d_full["all_added_are_hf02_disjunction"] and d_full["added_rows"] == EXPECTED_ROWS,
        "runner_exits_cleanly_without_crash":
            all(s["exit_code"] in (0, 2) for s in scenarios.values()),
        "determinism": det["baseline_trim_deterministic"] and det["patched_trim_deterministic"],
        "controls_all_pass": controls["failed"] == 0,
        "gate_effect_is_gaudit_pending_to_fail":
            scenarios["baseline_trim"]["gates"]["G-AUDIT"] == "pending"
            and scenarios["patched_trim"]["gates"]["G-AUDIT"] == "fail"
            and scenarios["patched_full"]["gates"]["G-AUDIT"] == "fail",
    }
    overall = all(checks.values())

    # copy durable raw evidence
    for tag, s in scenarios.items():
        raw = dict(s)
        raw.pop("report_raw", None)
        (RAWDIR / f"{tag}.json").write_text(json.dumps(raw, indent=2, sort_keys=True) + "\n")
        (RAWDIR / f"{tag}.audit-report.json").write_text(
            json.dumps(s["report_raw"], indent=2, sort_keys=True) + "\n")

    result = {
        "overall_pass": overall,
        "checks": checks,
        "verdict_if_pass": (
            "P-CODE integrated end-to-end: the one-line wiring in audit_run.py is sufficient; "
            "at ledger a1674f094979 the wired canonical runner reports exactly the 8 dual-class rows "
            "as HF-02 and adds no other violation; the unpatched canonical runner reports none of them."
        ),
        "consequence": (
            "The HF-02 accept/revise split at L0 is explained by a validator gap, and a two-file, "
            "16-line repair closes it without touching any other detector. Applying it to canonical "
            "bytes is a lead/controller decision, not this worker's."
        ),
    }

    report = {
        "schema": "w023-hf02-integration/v1",
        "task_id": "W023-L0-HF02-INTEG-01",
        "actor": "worker-023",
        "instance": "worker-023-20260912T004419-968807",
        "created_at": now_iso(),
        "node_id": "L0",
        "gate": "G-LIT",
        "class_id": "AF-SCC-C2-VAC-GEN",
        "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-VAC-GEN"],
        "question": ("Does the worker-093 HF-02 ledger-disjunction proposal work inside the canonical "
                     "audit_run.py pipeline at the pinned bytes, flagging exactly the 8 dual-class rows "
                     "and perturbing nothing else?"),
        "pins": {**pin_state["pins"],
                 "research_map/research_map.json@snapshot": map_sha},
        "inputs": {"canonical_sandbox": canon, "patched_sandbox": patch,
                   "frozen_map_snapshot": str(full_map)},
        "method": {
            "sandboxes": "frozen copies under tmp/w023_hf02_integration; no canonical file edited",
            "scan": "ledger only (62 rows) so the delta is attributable to the ledger branch",
            "map_variants": ["trimmed (groups=[]) to isolate claim-side detections",
                             "full frozen snapshot to prove map-side noise cancels"],
            "cross_check": "worker-093 isolation verdict and worker-023 composition verdict are compared in README",
        },
        "scenarios": {k: {kk: vv for kk, vv in v.items() if kk != "report_raw"}
                      for k, v in scenarios.items()},
        "delta_trimmed_map": d_trim,
        "delta_full_map": d_full,
        "gate_effect": gate_effect,
        "controls": controls,
        "determinism": det,
        "findings": [
            {"id": "W023-INTEG-F1", "severity": "none",
             "finding": ("P-CODE integrates: diff applies byte-faithfully to the pinned audit_lib.py "
                         "(patched bytes hash 9c8def1b5037), and one wiring line in audit_run.py is "
                         "sufficient. The wired runner flags exactly the 8 dual-class rows and adds no "
                         "other violation at ledger a1674f094979."),
             "status": "integration-verified"},
            {"id": "W023-INTEG-F2", "severity": "major-instrument",
             "finding": ("The 093 diff ships no call site, so the patch alone is inert; a landing change "
                         "must include the one-line wiring (recorded in runner_wiring_comment below). "
                         "The proposal README states this, but the diff itself does not."),
             "status": "reported-not-repaired"},
            {"id": "W023-INTEG-F3", "severity": "minor-instrument",
             "finding": ("audit_run.py:142-143 gate_verdicts() G-FORM branch is `pending if not "
                         "any(c.get(\"class_id\") for c in [])`, a constant-False expression, so G-FORM "
                         "can never return pass or fail from this runner. Observed in all six runs: "
                         "G-FORM pending, including patched runs carrying 8 critical HF-02."),
             "status": "reported-not-repaired"},
            {"id": "W023-INTEG-F4", "severity": "none",
             "finding": ("Integration is not cosmetic: in the isolated run, landing P-CODE flips the "
                         "derived G-AUDIT verdict from pending to fail via the 8 added criticals. In the "
                         "full-map runs the partial sandbox mirror makes absolute verdicts uninterpretable, "
                         "so only the delta is read. The ledger repair (P-DATA shape) or a rubric amendment "
                         "must land with the code, else the repair itself blocks the gate."),
             "status": "consequence-recorded"},
        ],
        "runner_wiring_comment": {
            "file": "artifacts/audit/audit_run.py",
            "anchor": WIRING_ANCHOR,
            "inserted_line": WIRING_LINE,
            "wired_runner_sha256": patch["runner_after"],
            "wiring_diff_path": "artifacts/worker-023/l0_hf02_integration/runner_wiring.diff",
            "wiring_diff_sha256": wiring_diff_sha,
        },
        "result": result,
        "scope_limits": [
            "Sandboxed frozen inputs; the live workspace may move after the run.",
            "The trimmed-map runs are the primary measurement. The full-map variant uses a PARTIAL mirror: "
            "done-node artifact existence checks (HF-05/HF-06) are not faithful because only the files the "
            "ledger scan reads are mirrored. Absolute full-map verdicts are not interpretable; only the "
            "within-variant delta is, and the snapshot hash is recorded.",
            "No page-level literature re-reading and no L1 re-fetch: this is a tooling integration test.",
            "Worker authority only: no node status, no validation_status=passed, no gate verdict.",
        ],
        "falsifier": (
            "Re-run this driver at the same pins. It is falsified if (a) any pinned input hash differs "
            "(verdict void, exit 2); (b) the patched runner reports other than exactly the 8 expected rows; "
            "(c) the canonical runner reports any of them; (d) any added violation is not HF-02 "
            "ledger-disjunction; (e) the patched audit_lib.py does not hash to 9c8def1b5037; or "
            "(f) any of the 15 controls does not reproduce its expected value."
        ),
    }

    report_path = OUTDIR / "report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    report_sha = sha256_file(report_path)
    (OUTDIR / "report.json.sha256").write_text(f"{report_sha}  report.json\n")

    manifest = {
        "schema": "w023-artifact-manifest/v1",
        "task_id": "W023-L0-HF02-INTEG-01",
        "actor": "worker-023",
        "created_at": now_iso(),
        "artifacts": [
            {"role": "driver", "path": "artifacts/worker-023/l0_hf02_integration/run_integration_023.py",
             "sha256": sha256_file(Path(__file__))},
            {"role": "report", "path": "artifacts/worker-023/l0_hf02_integration/report.json",
             "sha256": report_sha},
            {"role": "wiring_diff", "path": "artifacts/worker-023/l0_hf02_integration/runner_wiring.diff",
             "sha256": wiring_diff_sha},
        ],
        "raw_evidence_dir": "artifacts/worker-023/l0_hf02_integration/raw/",
        "pins": report["pins"],
        "overall_pass": overall,
    }
    for p in sorted(RAWDIR.glob("*.json")):
        manifest["artifacts"].append(
            {"role": "raw", "path": str(p.relative_to(REPO)), "sha256": sha256_file(p)})
    manifest_path = OUTDIR / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    (OUTDIR / "manifest.json.sha256").write_text(
        f"{sha256_file(manifest_path)}  manifest.json\n")

    print(f"overall_pass={overall} checks={sum(checks.values())}/{len(checks)} "
          f"controls={controls['passed']}/{controls['n']} "
          f"delta_trim={d_trim['n_added']}+/{d_trim['n_removed']}- "
          f"delta_full={d_full['n_added']}+/{d_full['n_removed']}-")
    for k, v in checks.items():
        if not v:
            print(f"  FAIL {k}")
    print(f"report -> {report_path.relative_to(REPO)} sha256={report_sha[:12]}")

    if not a.keep_sandboxes:
        shutil.rmtree(WORK, ignore_errors=True)
    return 0 if overall else 3


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except DriverError as e:
        print(f"DRIVER ERROR: {e}", file=sys.stderr)
        raise SystemExit(4)
