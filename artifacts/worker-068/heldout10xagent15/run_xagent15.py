#!/usr/bin/env python3
"""W068-FORM-HELDOUT10-XAGENT-15 runner (worker-068, bounded class-bound task).

Cross-agent (worker-068, non-author) replication of FORM-HELDOUT-10 (worker-084) at a fully
pinned rev13 / FROZEN-rev29 shadow. Runs the two canonical class-binding stages exactly once
per fixture, compares every verdict against the pinned worker-084 raw verdicts, recomputes the
aggregates, and audits each mutant's structural distance from its own arm base.

Measurement only: never sets a gate verdict, node status or validation_status=passed. Writes
only under artifacts/worker-068/heldout10xagent15/.

Usage: python3 run_xagent15.py
Exit 0 run completed; 2 precondition failure.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SNAP = HERE / "snapshot"
RAW = HERE / "raw"
CST = timezone(timedelta(hours=8))
PY = sys.executable
HELDOUT = "artifacts/heldout/heldout-10"

STAGE_A = SNAP / "artifacts/formulation/tools/check_class_schema.py"
STAGE_B = SNAP / "artifacts/worker-06/spec_conformance_audit.py"
SPEC = SNAP / "artifacts/formulation/rule_spec.json"
MANIFEST = HERE / "manifest.json"
PREREG = HERE / "PREREGISTRATION.json"

A_ACCEPT = {"pass"}
B_ACCEPT = {"accept"}
LIVE_PINS = [
    "schemas/af_wcc_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml",
    "research_map/formulation_taxonomy.yaml",
    "artifacts/formulation/FROZEN.json",
    "artifacts/formulation/tools/check_class_schema.py",
    "artifacts/formulation/KEY_MANIFEST.json",
    "artifacts/formulation/rule_spec.json",
    "artifacts/worker-06/spec_conformance_audit.py",
]


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def flatten(doc, prefix: str = "") -> dict:
    out: dict = {}
    if isinstance(doc, dict):
        if not doc:
            out[prefix or "$"] = "<empty-map>"
        for k, v in doc.items():
            out.update(flatten(v, f"{prefix}.{k}" if prefix else str(k)))
    elif isinstance(doc, list):
        if not doc:
            out[prefix or "$"] = "<empty-list>"
        for i, v in enumerate(doc):
            out.update(flatten(v, f"{prefix}[{i}]"))
    else:
        out[prefix or "$"] = doc
    return out


def preview(v, limit: int = 140) -> str:
    try:
        s = json.dumps(v, default=str, ensure_ascii=True)
    except Exception:  # noqa: BLE001
        s = repr(v)
    return s if len(s) <= limit else s[: limit - 3] + "..."


def leaf_diff(base_doc, fx_doc) -> dict:
    a, b = flatten(base_doc), flatten(fx_doc)
    changed = []
    for k in sorted(set(a) | set(b)):
        if k not in a:
            changed.append({"path": k, "change": "added", "base_preview": None,
                            "fixture_preview": preview(b[k])})
        elif k not in b:
            changed.append({"path": k, "change": "removed", "base_preview": preview(a[k]),
                            "fixture_preview": None})
        elif a[k] != b[k]:
            changed.append({"path": k, "change": "modified", "base_preview": preview(a[k]),
                            "fixture_preview": preview(b[k])})
    return {"base_leaves": len(a), "fixture_leaves": len(b), "changed_count": len(changed),
            "changed": changed}


def run_stage(cmd: list, timeout: int = 300) -> dict:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           cwd=str(SNAP))
    except subprocess.TimeoutExpired:
        return {"exit": None, "verdict": "timeout", "failed_rules": [],
                "anomaly": "timeout", "stderr_tail": "timeout", "json": None}
    out = r.stdout.strip()
    j = None
    try:
        j = json.loads(out[out.find("{"):]) if "{" in out else None
        verdict = j.get("verdict") if isinstance(j, dict) else None
        anomaly = None if verdict else "no-verdict-field"
    except Exception as exc:  # noqa: BLE001
        verdict, anomaly = "unparseable", f"json parse error: {exc}"
    return {"exit": r.returncode, "verdict": verdict,
            "failed_rules": (j or {}).get("failed_rules", []) if isinstance(j, dict) else [],
            "anomaly": anomaly, "stderr_tail": r.stderr.strip()[-300:], "json": j}


def main() -> int:
    problems: list[str] = []
    pre = json.loads(PREREG.read_text())
    man = json.loads(MANIFEST.read_text())

    # ---- manifest hash BEFORE any stage process ------------------------------
    manifest_sha = sha256_file(MANIFEST)
    manifest_mtime = datetime.fromtimestamp(MANIFEST.stat().st_mtime, CST).isoformat(
        timespec="seconds")
    run_started = now()
    if manifest_mtime > run_started:
        problems.append(f"manifest mtime {manifest_mtime} is after run start {run_started}")

    # ---- snapshot integrity ---------------------------------------------------
    snap_bad = []
    for rel, rec in man["entries"].items():
        p = SNAP / rel
        got = sha256_file(p) if p.exists() else None
        if got != rec["sha256"]:
            snap_bad.append({"path": rel, "manifest": rec["sha256"], "measured": got})
    if snap_bad:
        problems.append(f"{len(snap_bad)} snapshot bytes do not match manifest.json")
    live_before = {rel: sha256_file(ROOT / rel) for rel in LIVE_PINS}
    if problems:
        print(json.dumps({"verdict": "PRECONDITION_FAILED", "problems": problems,
                          "snapshot_mismatches": snap_bad}, indent=1))
        return 2

    # ---- corpus rows ----------------------------------------------------------
    cm = json.loads((SNAP / HELDOUT / "manifest.json").read_text())
    target = json.loads((SNAP / HELDOUT / "raw/raw_verdicts.json").read_text())
    cmap = cm["class_ids"]
    base_by_arm = {arm: b for arm, b in cm["bases"].items()}

    # worker-084 target verdicts, keyed by relative path
    target_rows = {}
    mutant_path_by_name = {m["fixture"]: m["path"] for m in cm["mutants"]}
    for r in target["results"]:
        rel = mutant_path_by_name.get(r["fixture"])
        if rel is not None:
            target_rows[rel] = r
    for c in target["controls"]:
        target_rows[c["path"]] = c

    fixtures: list[dict] = []
    for rel in cm["frozen_canonical_controls"]:
        fixtures.append({"role": "frozen_canonical_control", "path": rel,
                         "fixture": Path(rel).name, "class_id": None, "family": None,
                         "base": None, "arm": None, "mutation_id": None})
    for c in cm["controls"]:
        fixtures.append({"role": "authored_control", "path": c["path"], "fixture": c["fixture"],
                         "class_id": c["class_id"], "family": c["kind"], "base": None,
                         "arm": None, "mutation_id": c["control_id"]})
    for m in cm["mutants"]:
        fixtures.append({"role": "mutant", "path": m["path"], "fixture": m["fixture"],
                         "class_id": m["class_id"], "family": m["family"], "base": m["base"],
                         "arm": m["arm"], "mutation_id": m["mutation_id"],
                         "declared_base_sha256": m["base_sha256"]})

    if RAW.exists():
        for p in RAW.glob("*.json"):
            p.unlink()
    RAW.mkdir(exist_ok=True)

    rows = []
    for fx in fixtures:
        path = SNAP / fx["path"]
        a = run_stage([PY, str(STAGE_A), "--json", str(path)])
        b = run_stage([PY, str(STAGE_B), str(path), "--spec", str(SPEC)])
        (RAW / f"{fx['fixture']}.stageA.json").write_text(
            json.dumps(a["json"] if a["json"] is not None else a, indent=1) + "\n")
        (RAW / f"{fx['fixture']}.stageB.json").write_text(
            json.dumps(b["json"] if b["json"] is not None else b, indent=1) + "\n")
        a_ok, b_ok = a["verdict"] in A_ACCEPT, b["verdict"] in B_ACCEPT
        row = {
            "fixture": fx["fixture"], "path": fx["path"], "role": fx["role"],
            "class_id": fx["class_id"], "family": fx["family"], "arm": fx["arm"],
            "mutation_id": fx["mutation_id"],
            "sha256": sha256_file(path),
            "stageA": {"verdict": a["verdict"], "exit": a["exit"],
                       "failed_rules": sorted(a["failed_rules"]), "anomaly": a["anomaly"]},
            "stageB": {"verdict": b["verdict"], "exit": b["exit"],
                       "failed_rules": sorted(b["failed_rules"]), "anomaly": b["anomaly"]},
            "structural_escape": a_ok, "semantic_escape": b_ok,
            "union_escape": bool(a_ok and b_ok),
            "caught_by": ([] if a_ok else ["structural"]) + ([] if b_ok else ["semantic"]),
        }
        # ---- replication comparison against worker-084 ------------------------
        t = target_rows.get(fx["path"])
        if t is None:
            row["replication"] = {"target_found": False}
        else:
            agree = (t["stage_a"]["verdict"] == a["verdict"]
                     and sorted(t["stage_a"]["failed_rules"]) == sorted(a["failed_rules"])
                     and t["stage_b"]["verdict"] == b["verdict"]
                     and sorted(t["stage_b"]["failed_rules"]) == sorted(b["failed_rules"]))
            row["replication"] = {
                "target_found": True, "agree": bool(agree),
                "target_stage_a": {"verdict": t["stage_a"]["verdict"],
                                   "failed_rules": sorted(t["stage_a"]["failed_rules"])},
                "target_stage_b": {"verdict": t["stage_b"]["verdict"],
                                   "failed_rules": sorted(t["stage_b"]["failed_rules"])},
            }
        # ---- mutation isolation audit (mutants only) --------------------------
        if fx["role"] == "mutant":
            base_path = SNAP / fx["base"]
            base_doc = yaml.safe_load(base_path.read_bytes())
            fx_doc = yaml.safe_load(path.read_bytes())
            d = leaf_diff(base_doc, fx_doc)
            d["declared_base_sha_matches"] = (
                sha256_file(base_path) == fx["declared_base_sha256"])
            d["flags"] = []
            if d["changed_count"] == 0:
                d["flags"].append("ZERO_CHANGED_LEAVES")
            if not d["declared_base_sha_matches"]:
                d["flags"].append("BASE_HASH_MISMATCH")
            if not isinstance(fx_doc, dict):
                d["flags"].append("FIXTURE_NOT_MAPPING")
            row["isolation"] = d
        rows.append(row)

    # ---- informative arms (frozen canonical control acceptance) --------------
    canonical_by_class: dict = {}
    for r in rows:
        if r["role"] == "frozen_canonical_control":
            doc = yaml.safe_load((SNAP / r["path"]).read_bytes())
            canonical_by_class[doc.get("class_id")] = r["union_escape"]
    informative_arms = {c: ok for c, ok in canonical_by_class.items() if ok}
    for r in rows:
        r["arm_informative"] = bool(canonical_by_class.get(r["class_id"], False))

    mutants = [r for r in rows if r["role"] == "mutant"]
    controls = [r for r in rows if r["role"] != "mutant"]
    inf = [r for r in mutants if r["arm_informative"]]
    uninf = [r for r in mutants if not r["arm_informative"]]

    def agg(rs: list) -> dict | None:
        m = len(rs)
        if not m:
            return None
        esc = [r for r in rs if r["union_escape"]]
        by_family: dict = {}
        for r in esc:
            by_family.setdefault(r["family"], []).append(r)
        return {
            "mutants": m,
            "structural_escape": round(sum(r["structural_escape"] for r in rs) / m, 4),
            "semantic_escape": round(sum(r["semantic_escape"] for r in rs) / m, 4),
            "union_escape": round(len(esc) / m, 4),
            "union_caught": m - len(esc),
            "escape_families": [{"family": f, "count": len(v),
                                 "fixtures": [r["fixture"] for r in v]}
                                for f, v in sorted(by_family.items())],
            "caught_families": sorted({r["family"] for r in rs} - set(by_family)),
        }

    aggregates = agg(mutants)
    inf_agg = agg(inf)
    uninf_agg = agg(uninf)

    # ---- snapshot integrity after the run + live context ----------------------
    snap_bad_after = []
    for rel, rec in man["entries"].items():
        p = SNAP / rel
        got = sha256_file(p) if p.exists() else None
        if got != rec["sha256"]:
            snap_bad_after.append({"path": rel, "manifest": rec["sha256"], "measured": got})
    live_after = {rel: sha256_file(ROOT / rel) for rel in LIVE_PINS}
    live_drift = {rel: {"before": live_before[rel], "after": live_after[rel]}
                  for rel in LIVE_PINS if live_before[rel] != live_after[rel]}

    # ---- replication summary ---------------------------------------------------
    rep_rows = [r for r in rows if r.get("replication", {}).get("target_found")]
    rep_agree = [r for r in rep_rows if r["replication"]["agree"]]
    disagreements = [
        {"fixture": r["fixture"], "path": r["path"],
         "replication": {"stageA": r["stageA"], "stageB": r["stageB"]},
         "target": r["replication"]}
        for r in rep_rows if not r["replication"]["agree"]
    ]
    isolation_flags = [{"fixture": r["fixture"], "flags": r["isolation"]["flags"],
                        "changed_count": r["isolation"]["changed_count"]}
                       for r in mutants if r["isolation"]["flags"]]
    changed_counts = sorted({r["isolation"]["changed_count"] for r in mutants})

    # ---- validity ---------------------------------------------------------------
    invalid_reasons = []
    if snap_bad or snap_bad_after:
        invalid_reasons.append("snapshot bytes do not match manifest.json")
    rejected_controls = [r["fixture"] for r in controls if not r["union_escape"]]
    for r in controls:
        if not r["union_escape"]:
            why = []
            if r["stageA"]["verdict"] not in A_ACCEPT:
                why.append(f"stage A {r['stageA']['verdict']} {r['stageA']['failed_rules']}")
            if r["stageB"]["verdict"] not in B_ACCEPT:
                why.append(f"stage B {r['stageB']['verdict']} {r['stageB']['failed_rules']}")
            invalid_reasons.append(f"control {r['fixture']} rejected: " + "; ".join(why))
    if live_drift:
        invalid_reasons.append("live pinned input drifted during the run (context only): "
                               + ", ".join(live_drift))
    crashes = [r["fixture"] for r in rows
               if r["stageA"]["anomaly"] or r["stageB"]["anomaly"]]
    if crashes:
        invalid_reasons.append("stage anomaly: " + ", ".join(crashes))
    valid = not invalid_reasons

    # ---- pre-registered predictions check ---------------------------------------
    pred = pre["pre_registered_predictions"]
    pred_checks = {
        "fixture_verdict_agreement_all_40": bool(
            len(rep_rows) == 40 and len(rep_agree) == 40),
        "all_mutants_union_escape": bool(
            aggregates and aggregates["union_escape"] == pred["all_mutants_union_escape"]),
        "informative_arms_union_escape": bool(
            inf_agg and inf_agg["union_escape"] == pred["informative_arms_union_escape"]),
        "informative_arms_mutants": len(inf) == pred["informative_arms_mutants"],
        "informative_arms_union_caught": bool(
            inf_agg and inf_agg["union_caught"] == pred["informative_arms_union_caught"]),
        "w_arm_non_informative": bool(not canonical_by_class.get("AF-WCC-VAC-GEN", False)),
        "w_arm_stage_b_reject_rule": any(
            r["role"] == "frozen_canonical_control"
            and r["class_id"] is None and not r["union_escape"]
            and r["stageB"]["failed_rules"] == [pred["w_arm_stage_b_reject_rule"]]
            for r in rows),
        "strict_h5_controls_all_accepted": bool(
            not rejected_controls) == pred["strict_h5_controls_all_accepted"],
        "strict_valid": valid == pred["strict_valid"],
        "invalid_reason_contains": any(
            pred["invalid_reason_contains"] in x for x in invalid_reasons),
    }
    predictions_all_match = all(pred_checks.values())

    report = {
        "schema": "worker-068/heldout10xagent15/report/v1",
        "task_id": "W068-FORM-HELDOUT10-XAGENT-15",
        "actor": "worker-068",
        "created_at": now(),
        "node_id": pre["node_id"],
        "gate": pre["gate"],
        "class_ids": pre["class_ids"],
        "authority_note": pre["authority_note"],
        "question": pre["question"],
        "independence": pre["independence_statement"],
        "replication_target": pre["replication_target"],
        "binding": {
            "shadow_manifest": "artifacts/worker-068/heldout10xagent15/manifest.json",
            "shadow_manifest_sha256": manifest_sha,
            "shadow_manifest_mtime": manifest_mtime,
            "manifest_hashed_before_any_stage_run": manifest_mtime <= run_started,
            "preregistration_sha256": sha256_file(PREREG),
            "snapshot_entries": len(man["entries"]),
            "stages": {
                "stage_a": {"path": str(STAGE_A.relative_to(ROOT)),
                            "sha256": man["pinned_sources"][
                                "artifacts/formulation/tools/check_class_schema.py"]},
                "stage_a_key_manifest": {
                    "path": str((SNAP / "artifacts/formulation/KEY_MANIFEST.json").relative_to(ROOT)),
                    "sha256": man["pinned_sources"]["artifacts/formulation/KEY_MANIFEST.json"],
                    "note": "PINNED in this shadow; the acknowledged unpinned live dependency of "
                            "stage A is bound to its snapshot bytes here"},
                "stage_b": {"path": str(STAGE_B.relative_to(ROOT)),
                            "sha256": man["pinned_sources"][
                                "artifacts/worker-06/spec_conformance_audit.py"]},
                "rule_spec": {"path": str(SPEC.relative_to(ROOT)),
                              "sha256": man["pinned_sources"]["artifacts/formulation/rule_spec.json"]},
            },
        },
        "run": {
            "run_started_at": run_started,
            "run_finished_at": now(),
            "fixtures_total": len(rows),
            "mutants": len(mutants),
            "controls": len(controls),
            "stage_processes": 2 * len(rows),
        },
        "validity": {
            "snapshot_stable": not snap_bad and not snap_bad_after,
            "snapshot_mismatches_before": snap_bad,
            "snapshot_mismatches_after": snap_bad_after,
            "controls_all_accepted": not rejected_controls,
            "rejected_controls": rejected_controls,
            "stage_anomalies": crashes,
            "live_pin_drift_during_run": live_drift,
            "live_pins_before": live_before,
            "live_pins_after": live_after,
            "valid": valid,
            "invalid_reasons": invalid_reasons,
        },
        "informative_arms": informative_arms,
        "aggregates": aggregates,
        "aggregates_informative_arms_only": inf_agg,
        "aggregates_uninformative_arms_only": uninf_agg,
        "replication": {
            "rows_compared": len(rep_rows),
            "rows_agreeing": len(rep_agree),
            "agreement_rate": round(len(rep_agree) / len(rep_rows), 4) if rep_rows else None,
            "full_agreement": len(rep_rows) == len(rows) and len(rep_agree) == len(rows),
            "disagreements": disagreements,
            "target_raw_verdicts_sha256": man["replication_target"][
                f"{HELDOUT}/raw/raw_verdicts.json"],
        },
        "mutation_isolation_audit": {
            "mutants": len(mutants),
            "changed_leaf_count_distribution": {str(c): sum(
                1 for r in mutants if r["isolation"]["changed_count"] == c)
                for c in changed_counts},
            "flagged": isolation_flags,
            "all_single_or_reported": not isolation_flags,
        },
        "pre_registered_predictions": pred,
        "prediction_checks": pred_checks,
        "predictions_all_match": predictions_all_match,
        "fixture_table": rows,
        "falsifier": pre["falsifier"],
        "next_falsifier": pre["next_falsifier"],
        "non_claims": pre["non_claims"],
        "stop_rule": pre["acceptance_criteria"]["A7_stop_rule"],
    }
    (HERE / "report.json").write_text(json.dumps(report, indent=2) + "\n")

    raw_out = {
        "schema": "worker-068/heldout10xagent15/raw-verdicts/v1",
        "task_id": report["task_id"], "actor": "worker-068",
        "shadow_manifest_sha256": manifest_sha,
        "run_started_at": run_started, "run_finished_at": now(),
        "stages": report["binding"]["stages"],
        "target_raw_verdicts_sha256": report["replication"]["target_raw_verdicts_sha256"],
        "rows": rows,
        "validity": report["validity"],
        "replication": report["replication"],
        "aggregates": aggregates,
    }
    (HERE / "raw_verdicts.json").write_text(json.dumps(raw_out, indent=2) + "\n")

    checkpoint = {
        "checkpoint_id": "ckpt-w068-heldout10xagent15",
        "created_at": now(),
        "worker": "worker-068", "task_id": report["task_id"],
        "node_id": report["node_id"], "gate": report["gate"],
        "class_ids": report["class_ids"],
        "status": "replication_complete" if valid else "replication_complete_controls_invalid",
        "valid": valid, "invalid_reasons": invalid_reasons,
        "shadow_manifest_sha256": manifest_sha,
        "report_sha256": sha256_file(HERE / "report.json"),
        "raw_verdicts_sha256": sha256_file(HERE / "raw_verdicts.json"),
        "replication_rows_compared": len(rep_rows),
        "replication_rows_agreeing": len(rep_agree),
        "replication_full_agreement": report["replication"]["full_agreement"],
        "aggregates": aggregates,
        "aggregates_informative_arms_only": inf_agg,
        "predictions_all_match": predictions_all_match,
        "falsifier": pre["falsifier"],
        "stop_rule": report["stop_rule"],
    }
    (HERE / "checkpoint.json").write_text(json.dumps(checkpoint, indent=2) + "\n")

    print(f"valid={valid} | fixtures={len(rows)} | replication agree "
          f"{len(rep_agree)}/{len(rep_rows)} | all-mutant union escape "
          f"{aggregates['union_escape']} ({aggregates['union_caught']} caught) | informative "
          f"C2+C0 union escape {inf_agg['union_escape']} ({inf_agg['union_caught']} caught)")
    print("invalid_reasons:", invalid_reasons)
    print("predictions_all_match:", predictions_all_match,
          "| failed checks:", [k for k, v in pred_checks.items() if not v])
    print("isolation flags:", isolation_flags)
    print("report sha256:", checkpoint["report_sha256"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
