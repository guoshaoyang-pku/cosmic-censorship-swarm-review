#!/usr/bin/env python3
"""W062-GFORM-R03V2-SCOPE-REPLICATION-01 -- independent black-box replication harness.

Written by worker-062, NOT derived from artifacts/worker-06/r03scope/run_scope.py. Each
candidate tool is invoked as a subprocess with the pinned rule spec and its own --json
output file; only the tool's machine-readable JSON is parsed (verdict, failed_rules,
returncode). Every cell is run twice and must be identical.

Part A  reproduce W006-R03-SCOPE-01 cell-for-cell on worker-006's pinned corpus (read-only)
Part B  run this worker's fresh held-out corpus (14 fixtures) against all four candidates
Part C  read out the cand_r03v2 span boundary from the unscored edge probes

Writes: raw_verdicts.json, report.json. Never writes outside this directory.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).isoformat(timespec="seconds")

SPEC = ROOT / "artifacts/formulation/rule_spec.json"
TOOLS = {
    "frozen": ROOT / "artifacts/worker-06/spec_conformance_audit.py",
    "cand_r03v2": ROOT / "artifacts/worker-06/r03v2/audit_r03v2.py",
    "cand_004": ROOT / "artifacts/worker-004/f1_r03_repair/patched/spec_conformance_audit.py",
    "cand_E3": ROOT / "artifacts/worker-064/r03_cause/work/cand_E3/artifacts/worker-06/spec_conformance_audit.py",
}
# Pins measured before and after; also the binding inputs of the work under replication.
PINS = [
    "schemas/af_wcc_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml",
    "artifacts/formulation/FROZEN.json",
    "artifacts/formulation/rule_spec.json",
    "artifacts/worker-06/spec_conformance_audit.py",
    "artifacts/worker-004/f1_r03_repair/patched/spec_conformance_audit.py",
    "artifacts/worker-064/r03_cause/work/cand_E3/artifacts/worker-06/spec_conformance_audit.py",
    "artifacts/worker-06/r03v2/audit_r03v2.py",
    "artifacts/worker-06/r03v2/r03v2_rule.py",
    "artifacts/worker-06/r03scope/fixture_manifest.json",
    "artifacts/worker-06/r03scope/raw_verdicts.json",
]
W006_FIX = ROOT / "artifacts/worker-06/r03scope/fixtures"
W006_RAW = ROOT / "artifacts/worker-06/r03scope/raw_verdicts.json"


def sha256_path(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def measure_pins() -> dict:
    return {rel: sha256_path(ROOT / rel) for rel in PINS}


def run_cell(tool: str, fixture: Path, run_idx: int) -> dict:
    out = RAW / f"{tool}__{fixture.name}__run{run_idx}.json"
    cmd = [sys.executable, str(TOOLS[tool]), str(fixture),
           "--spec", str(SPEC), "--json", str(out)]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    rec = {
        "cmd": " ".join(cmd),
        "returncode": proc.returncode,
        "stdout_tail": proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else "",
        "stderr_tail": proc.stderr.strip().splitlines()[-1] if proc.stderr.strip() else "",
        "json_path": str(out.relative_to(ROOT)),
    }
    if out.is_file():
        d = json.loads(out.read_text())
        rec["verdict"] = d.get("verdict")
        rec["failed_rules"] = d.get("failed_rules", [])
        rec["doc_sha256"] = d.get("doc_sha256")
    else:
        rec["verdict"] = "error"
        rec["failed_rules"] = []
    return rec


def run_matrix(fixtures: list[Path]) -> dict:
    matrix = {t: {} for t in TOOLS}
    for tool in TOOLS:
        for fx in fixtures:
            runs = [run_cell(tool, fx, i) for i in (1, 2)]
            r1, r2 = runs
            key = (r1["verdict"], tuple(r1["failed_rules"]), r1["returncode"])
            key2 = (r2["verdict"], tuple(r2["failed_rules"]), r2["returncode"])
            matrix[tool][fx.name] = {
                "run1": r1,
                "run2": r2,
                "deterministic": key == key2,
                "verdict": r1["verdict"],
                "failed_rules": r1["failed_rules"],
                "returncode": r1["returncode"],
            }
    return matrix


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    pins_pre = measure_pins()
    prereg = json.loads((HERE / "PREREGISTRATION.json").read_text())
    pred = prereg["predicted_cells"]

    # ---- Part A: reproduce worker-006's corpus --------------------------------
    w006_fixtures = sorted(W006_FIX.glob("*.yaml"))
    w006_ref = json.loads(W006_RAW.read_text())
    part_a = {"cells": {}, "matches": 0, "mismatches": [], "total": 0}
    matrix_a = run_matrix(w006_fixtures)
    for tool in TOOLS:
        for fx in w006_fixtures:
            mine = matrix_a[tool][fx.name]
            ref = w006_ref[tool][fx.name]
            same = (mine["verdict"] == ref["verdict"]
                    and sorted(mine["failed_rules"]) == sorted(ref["failed_rules"])
                    and mine["returncode"] == ref["returncode"])
            part_a["total"] += 1
            if same:
                part_a["matches"] += 1
            else:
                part_a["mismatches"].append({
                    "tool": tool, "fixture": fx.name,
                    "mine": {k: mine[k] for k in ("verdict", "failed_rules", "returncode")},
                    "reference": {k: ref[k] for k in ("verdict", "failed_rules", "returncode")},
                })
            part_a["cells"][f"{tool}::{fx.name}"] = {
                "verdict": mine["verdict"], "failed_rules": mine["failed_rules"],
                "returncode": mine["returncode"], "deterministic": mine["deterministic"],
                "matches_reference": same,
            }

    # ---- Part B: fresh held-out corpus ---------------------------------------
    my_fixtures = sorted((HERE / "fixtures").glob("*.yaml"))
    manifest = json.loads((HERE / "fixture_manifest.json").read_text())
    meta = {f["fixture"]: f for f in manifest["fixtures"]}
    matrix_b = run_matrix(my_fixtures)

    part_b = {"cells": {}, "per_tool": {}, "prediction_deviations": [], "errors": []}
    for tool in TOOLS:
        fp = fn = tp = tn = 0
        for fx in my_fixtures:
            m = matrix_b[tool][fx.name]
            info = meta[fx.name]
            p = pred[fx.name][tool]
            hit = (m["verdict"] == p)
            scored = info["scored"]
            measured_is_error = m["verdict"] == "error"
            if measured_is_error:
                part_b["errors"].append({"tool": tool, "fixture": fx.name})
            if scored and not measured_is_error:
                if info["category"] == "neg":       # must reject
                    if m["verdict"] == "accept":
                        fp += 1
                    else:
                        tn += 1
                elif info["category"] == "pos":     # must accept
                    if m["verdict"] == "reject":
                        fn += 1
                    else:
                        tp += 1
            if not hit:
                part_b["prediction_deviations"].append({
                    "tool": tool, "fixture": fx.name, "predicted": p,
                    "measured": m["verdict"], "failed_rules": m["failed_rules"],
                    "scored": scored, "category": info["category"],
                })
            part_b["cells"][f"{tool}::{fx.name}"] = {
                "category": info["category"], "scored": scored, "predicted": p,
                "measured": m["verdict"], "failed_rules": m["failed_rules"],
                "returncode": m["returncode"], "deterministic": m["deterministic"],
                "prediction_hit": hit, "q_to_t0": info["q_to_t0_distance_in_head"],
            }
        part_b["per_tool"][tool] = {
            "FP_must_reject_but_accepted": fp, "FN_must_accept_but_rejected": fn,
            "TP": tp, "TN": tn,
            "scored_cells": fp + fn + tp + tn,
            "deterministic_cells": sum(1 for fx in my_fixtures if matrix_b[tool][fx.name]["deterministic"]),
        }

    # ---- Part C: cand_r03v2 span boundary ------------------------------------
    part_c = {"probes": []}
    for fx in my_fixtures:
        name = fx.name
        if not name.startswith("edge_span"):
            continue
        m = matrix_b["cand_r03v2"][name]
        part_c["probes"].append({
            "fixture": name, "target_distance": int(name.split("_")[-1].split(".")[0]),
            "measured_q_to_t0": meta[name]["q_to_t0_distance_in_head"],
            "cand_r03v2": m["verdict"],
            "predicted": pred[name]["cand_r03v2"],
        })
    part_c["probes"].sort(key=lambda x: x["measured_q_to_t0"])

    # ---- pins post ------------------------------------------------------------
    pins_post = measure_pins()
    pin_drift = {k: {"pre": pins_pre[k], "post": pins_post[k]}
                 for k in PINS if pins_pre[k] != pins_post[k]}

    a_ok = part_a["matches"] == part_a["total"]
    v2_fp = part_b["per_tool"]["cand_r03v2"]["FP_must_reject_but_accepted"]
    v2_fn = part_b["per_tool"]["cand_r03v2"]["FN_must_accept_but_rejected"]
    deviations = len(part_b["prediction_deviations"])
    n_cells_b = len(TOOLS) * len(my_fixtures)
    if pin_drift or part_b["errors"]:
        outcome = "inconclusive-stop-rule"
    elif a_ok and v2_fp == 0 and v2_fn == 0 and deviations <= int(0.05 * n_cells_b):
        outcome = "replicate-confirmed"
    elif a_ok and (v2_fp > 0 or v2_fn > 0):
        outcome = "generalisation-falsified"
    else:
        outcome = "inconclusive"

    report = {
        "task_id": "W062-R03V2-SCOPE-REPLICATION-01",
        "worker": "worker-062",
        "created_at": NOW,
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "node_id": "A1",
        "gate": "G-FORM/G-CLASSBIND",
        "preregistration_sha256": sha256_path(HERE / "PREREGISTRATION.json"),
        "harness_sha256": sha256_path(HERE / "run_replication.py"),
        "fixture_manifest_sha256": sha256_path(HERE / "fixture_manifest.json"),
        "pins_pre": pins_pre,
        "pins_post": pins_post,
        "pin_drift": pin_drift,
        "part_a_reproduce_w006": {
            "corpus_manifest_sha256": pins_pre["artifacts/worker-06/r03scope/fixture_manifest.json"],
            "reference_raw_sha256": pins_pre["artifacts/worker-06/r03scope/raw_verdicts.json"],
            "total_cells": part_a["total"], "matches": part_a["matches"],
            "mismatches": part_a["mismatches"],
        },
        "part_b_heldout": {
            "fixtures": len(my_fixtures),
            "cells": n_cells_b,
            "per_tool_scored": part_b["per_tool"],
            "prediction_deviations": part_b["prediction_deviations"],
            "error_cells": part_b["errors"],
        },
        "part_c_span_boundary": part_c,
        "outcome_under_preregistered_rule": outcome,
        "cand_r03v2_FP": v2_fp,
        "cand_r03v2_FN": v2_fn,
        "cells": part_b["cells"],
        "part_a_cells": part_a["cells"],
        "raw_verdicts_sha256_written": None,  # filled after raw dump below
        "not_claimed": ["no gate verdict", "no node completion", "no adoption recommendation",
                        "no canonical or frozen write"],
    }
    (HERE / "raw_verdicts.json").write_text(json.dumps(
        {"part_a": part_a["cells"], "part_b": part_b["cells"],
         "pins_pre": pins_pre, "pins_post": pins_post}, indent=1) + "\n")
    report["raw_verdicts_sha256_written"] = sha256_path(HERE / "raw_verdicts.json")
    (HERE / "report.json").write_text(json.dumps(report, indent=1) + "\n")

    print(json.dumps({
        "part_a_matches": f"{part_a['matches']}/{part_a['total']}",
        "part_b_per_tool": part_b["per_tool"],
        "prediction_deviations": deviations,
        "pin_drift": pin_drift,
        "span_boundary": part_c["probes"],
        "outcome": outcome,
    }, indent=1))


if __name__ == "__main__":
    main()
