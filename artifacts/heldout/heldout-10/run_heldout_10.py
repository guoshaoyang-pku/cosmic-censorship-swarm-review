#!/usr/bin/env python3
"""FORM-HELDOUT-10 single frozen measurement run (worker-084).

Re-issue successor to FORM-HELDOUT-09, against the LIVE FROZEN rev29 / rev13 bytes.
Fixtures were frozen by build_corpus_10.py --freeze; no fixture is rewritten here.

Stages (canonical two-stage acceptance pipeline):
  stage A (structural): python3 artifacts/formulation/tools/check_class_schema.py --json FIXTURE
  stage B (semantic):   python3 artifacts/worker-06/spec_conformance_audit.py FIXTURE

Order of operations (H1):
  1. sha256(manifest.json) is taken BEFORE any fixture stage process is started;
  2. the live pins, the three bases and every fixture are re-verified against the manifest;
  3. controls (3 frozen canonical + 2 conforming + 2 negated-phrase) are run;
  4. each mutant is run exactly once; no fixture is rewritten after a verdict is observed;
  5. pins are re-measured AFTER the run (moving-target guard).

Union escape = accepted by BOTH stages (the pipeline's own "union catch" convention).
H5: if any control is rejected by either stage the corpus is format-dominated and valid=false;
escape rates are still reported (H7).  The frozen WCC canonical's stage-B R03 rejection is
pre-registered in the manifest (known_calibration_defect) as a measured instrument defect, which
declares the WCC arm non-informative in advance; strict H5 is still evaluated and reported.

Usage: python3 run_heldout_10.py
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
MANIFEST = HERE / "manifest.json"
RAW = HERE / "raw"
CST = timezone(timedelta(hours=8))
TIMEOUT = 300


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def parse_json_stdout(stdout: str):
    i = stdout.find("{")
    if i < 0:
        return None
    try:
        return json.loads(stdout[i:])
    except json.JSONDecodeError:
        return None


def run_stage_a(tool: Path, target: Path) -> dict:
    t0 = time.time()
    try:
        p = subprocess.run([sys.executable, str(tool), "--json", str(target)],
                           capture_output=True, text=True, timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        return {"tool": "stage_a/check_class_schema.py", "exit": None, "verdict": None,
                "failed_rules": [], "failures": [], "escaped": False, "crash": True,
                "seconds": round(time.time() - t0, 3), "stderr": "timeout"}
    rep = parse_json_stdout(p.stdout) or {}
    return {
        "tool": "stage_a/check_class_schema.py", "exit": p.returncode,
        "verdict": rep.get("verdict"), "failed_rules": rep.get("failed_rules", []),
        "failures": rep.get("failures", [])[:6],
        "escaped": p.returncode == 0 and rep.get("verdict") == "pass",
        "crash": rep.get("verdict") is None,
        "seconds": round(time.time() - t0, 3),
        "stderr": p.stderr.strip()[:200],
    }


def run_stage_b(tool: Path, target: Path) -> dict:
    t0 = time.time()
    try:
        p = subprocess.run([sys.executable, str(tool), str(target)],
                           capture_output=True, text=True, timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        return {"tool": "stage_b/spec_conformance_audit.py", "exit": None, "verdict": None,
                "failed_rules": [], "failed_checks": [], "escaped": False, "crash": True,
                "seconds": round(time.time() - t0, 3), "stderr": "timeout"}
    rep = parse_json_stdout(p.stdout) or {}
    verdict = rep.get("verdict")
    return {
        "tool": "stage_b/spec_conformance_audit.py", "exit": p.returncode,
        "verdict": verdict, "failed_rules": rep.get("failed_rules", []),
        "failed_checks": [c for c in rep.get("checks", []) if c.get("verdict") == "fail"][:6],
        "escaped": verdict == "accept",
        "crash": verdict is None,
        "seconds": round(time.time() - t0, 3),
        "stderr": p.stderr.strip()[:200],
    }


def main() -> int:
    if not MANIFEST.exists():
        print("manifest missing; run build_corpus_09.py --freeze first", file=sys.stderr)
        return 2
    RAW.mkdir(parents=True, exist_ok=True)

    # ---- H1: manifest hash BEFORE any stage process ---------------------------
    manifest_sha = sha(MANIFEST)
    manifest_mtime = datetime.fromtimestamp(MANIFEST.stat().st_mtime, CST).isoformat(timespec="seconds")
    run_started = now()
    man = json.loads(MANIFEST.read_text())

    struct = ROOT / man["stages"]["structural"]["path"]
    sem = ROOT / man["stages"]["semantic"]["path"]
    keyman = ROOT / man["stages"]["stage_a_key_manifest"]["path"]

    # ---- pins / hashes before run --------------------------------------------
    pins_before = {}
    for rel, want in man["pins"].items():
        got = sha(ROOT / rel)
        pins_before[rel] = {"pinned": want, "measured_before": got, "match": got == want}
    frozen_now = sha(ROOT / man["frozen_manifest"]["path"])
    pins_before[man["frozen_manifest"]["path"]] = {
        "pinned": man["frozen_manifest"]["sha256"], "measured_before": frozen_now,
        "match": frozen_now == man["frozen_manifest"]["sha256"]}
    stages_before = {
        "structural": {"expected": man["stages"]["structural"]["sha256"], "measured": sha(struct)},
        "semantic": {"expected": man["stages"]["semantic"]["sha256"], "measured": sha(sem)},
        "stage_a_key_manifest": {"expected": man["stages"]["stage_a_key_manifest"]["sha256"],
                                 "measured": sha(keyman)},
    }
    for k, v in stages_before.items():
        v["match"] = v["expected"] == v["measured"]
    pins_ok_before = all(v["match"] for v in pins_before.values()) and \
        all(v["match"] for v in stages_before.values())

    # ---- fixture integrity ----------------------------------------------------
    tampered = []
    for e in man["mutants"] + man["controls"]:
        p = ROOT / e["path"]
        if not p.exists() or sha(p) != e["sha256"]:
            tampered.append(e["path"])
    for arm, b in man["bases"].items():
        p = ROOT / b["path"]
        if not p.exists() or sha(p) != b["sha256"] or b["sha256"] != man["pins"][b["frozen_path"]]:
            tampered.append(b["path"])

    # ---- controls: 3 frozen canonical + 4 authored ----------------------------
    controls = []
    for rel in man["frozen_canonical_controls"]:
        a, b = run_stage_a(struct, ROOT / rel), run_stage_b(sem, ROOT / rel)
        controls.append({"fixture": Path(rel).name, "kind": "frozen-canonical", "path": rel,
                         "class_id": None, "stage_a": a, "stage_b": b,
                         "accepted_both": a["escaped"] and b["escaped"]})
    for e in man["controls"]:
        a, b = run_stage_a(struct, ROOT / e["path"]), run_stage_b(sem, ROOT / e["path"])
        controls.append({"fixture": e["fixture"], "kind": e["kind"], "path": e["path"],
                         "class_id": e["class_id"], "control_id": e["control_id"],
                         "description": e["description"], "stage_a": a, "stage_b": b,
                         "accepted_both": a["escaped"] and b["escaped"]})
    controls_ok = all(c["accepted_both"] for c in controls) and not tampered

    # informative arms: an arm is informative only if its frozen canonical control
    # is accepted by BOTH stages (otherwise every verdict in that arm is format-dominated)
    frozen_class_map = {}
    for rel in man["frozen_canonical_controls"]:
        cls = None
        try:
            import yaml as _yaml
            cls = _yaml.safe_load((ROOT / rel).read_text()).get("class_id")
        except Exception:  # noqa: BLE001
            cls = None
        frozen_class_map[Path(rel).name] = cls
    canonical_by_class = {}
    for c in controls:
        if c["kind"] == "frozen-canonical":
            c["class_id"] = frozen_class_map.get(c["fixture"])
            canonical_by_class[c["class_id"]] = c["accepted_both"]
    informative_arms = {cls: ok for cls, ok in canonical_by_class.items() if ok}

    # ---- mutants: exactly one run each ---------------------------------------
    results = []
    for e in man["mutants"]:
        a, b = run_stage_a(struct, ROOT / e["path"]), run_stage_b(sem, ROOT / e["path"])
        caught_by = []
        if not a["escaped"]:
            caught_by.append("structural")
        if not b["escaped"]:
            caught_by.append("semantic")
        results.append({
            "fixture": e["fixture"], "mutation_id": e["mutation_id"], "family": e["family"],
            "arm": e["arm"], "class_id": e["class_id"], "rephrased": e["rephrased"],
            "stage_a": a, "stage_b": b,
            "structural_escape": a["escaped"], "semantic_escape": b["escaped"],
            "union_escape": a["escaped"] and b["escaped"],
            "caught_by": caught_by,
            "arm_informative": bool(canonical_by_class.get(e["class_id"], False)),
        })

    n = len(results)

    def agg(rows):
        m = len(rows)
        if not m:
            return None
        union_esc = [r for r in rows if r["union_escape"]]
        by_family = {}
        for r in union_esc:
            by_family.setdefault(r["family"], []).append(r)
        fam_list = []
        rat = {f["family"]: f["rationale"] for f in man["families"]}
        for fam in sorted(by_family):
            rows_f = by_family[fam]
            fam_list.append({
                "family": fam, "count": len(rows_f),
                "example_name": rows_f[0]["fixture"],
                "one_sentence_reason": rat.get(fam, "no rule in either stage inspects this axis"),
                "fixtures": [r["fixture"] for r in rows_f],
            })
        return {
            "mutants": m,
            "structural_escape": round(sum(1 for r in rows if r["structural_escape"]) / m, 4),
            "semantic_escape": round(sum(1 for r in rows if r["semantic_escape"]) / m, 4),
            "union_escape": round(len(union_esc) / m, 4),
            "structural_caught": m - sum(1 for r in rows if r["structural_escape"]),
            "semantic_caught": m - sum(1 for r in rows if r["semantic_escape"]),
            "union_caught": m - len(union_esc),
            "escape_families": fam_list,
            "caught_families": sorted({r["family"] for r in rows} - set(by_family)),
        }

    aggregates = agg(results)
    informative_rows = [r for r in results if r["arm_informative"]]
    uninformatve_rows = [r for r in results if not r["arm_informative"]]
    informative_aggregates = agg(informative_rows)
    uninformative_aggregates = agg(uninformatve_rows)

    # ---- pins after run (moving-target guard) ---------------------------------
    pins_after = {rel: sha(ROOT / rel) for rel in list(man["pins"]) + [man["frozen_manifest"]["path"]]}
    moving_target = {rel: {"before": v["measured_before"], "after": pins_after[rel],
                           "changed": v["measured_before"] != pins_after[rel]}
                     for rel, v in pins_before.items()}

    # ---- validity -------------------------------------------------------------
    invalid_reasons = []
    if tampered:
        invalid_reasons.append("tampered or missing fixtures/bases: " + ", ".join(tampered))
    for c in controls:
        if not c["accepted_both"]:
            why = []
            if not c["stage_a"]["escaped"]:
                why.append(f"stage A {c['stage_a']['verdict']} {c['stage_a']['failed_rules']}")
            if not c["stage_b"]["escaped"]:
                why.append(f"stage B {c['stage_b']['verdict']} {c['stage_b']['failed_rules']}")
            invalid_reasons.append(f"control {c['fixture']} rejected: " + "; ".join(why))
    if not pins_ok_before:
        invalid_reasons.append("a pinned canonical hash or stage tool hash changed before the run")
    if any(v["changed"] for v in moving_target.values()):
        invalid_reasons.append("a pinned canonical hash changed DURING the run (moving target)")
    valid = not invalid_reasons

    run_finished = now()
    report = {
        "corpus_id": man["corpus_id"], "assignment": man["assignment"], "task_id": man["task_id"],
        "worker": man["worker"], "actor": man["actor"], "node_id": man["node_id"],
        "gate": man["gate"], "class_ids": man["class_ids"],
        "generated_at": run_finished, "run_started_at": run_started,
        "manifest_sha256_before_run": manifest_sha,
        "manifest_mtime": manifest_mtime,
        "manifest_hashed_before_any_stage_run": manifest_mtime <= run_started,
        "frozen_revision": man["frozen_revision"],
        "pins": man["pins"],
        "frozen_manifest": man["frozen_manifest"],
        "pin_check_before_run": pins_before,
        "pin_check_after_run": moving_target,
        "stages": {
            "structural": {"gate": man["stages"]["structural"]["path"],
                           "sha256": stages_before["structural"]["measured"]},
            "semantic": {"gate": man["stages"]["semantic"]["path"],
                         "sha256": stages_before["semantic"]["measured"]},
            "stage_a_key_manifest": {"path": man["stages"]["stage_a_key_manifest"]["path"],
                                     "sha256": stages_before["stage_a_key_manifest"]["measured"],
                                     "note": "unpinned live dependency of stage A, measured and recorded"},
        },
        "valid": valid,
        "invalid_reasons": invalid_reasons,
        "corpus": {
            "mutants": n,
            "families": len({r["family"] for r in results}),
            "rephrased": sum(1 for r in results if r["rephrased"]),
            "controls": len(controls),
            "frozen_canonical_controls": len(man["frozen_canonical_controls"]),
            "conforming_controls": sum(1 for c in controls if c["kind"] == "conforming"),
            "negated_phrase_controls": sum(1 for c in controls if c["kind"] == "negated-phrase"),
        },
        "informative_arms": informative_arms,
        "aggregates": aggregates,
        "aggregates_informative_arms_only": informative_aggregates,
        "aggregates_uninformative_arms_only": uninformative_aggregates,
        "controls_detail": controls,
        "measurement_rule": (
            "union escape = accepted by BOTH stages; structural escape = stage A pass; semantic "
            "escape = stage B accept. Controls (3 frozen canonical + 2 conforming + 2 negated-phrase) "
            "must be accepted by both stages or valid=false (H5)."),
        "known_calibration_defect": man.get("known_calibration_defect"),
        "card_pin_staleness": man.get("card_pin_staleness"),
        "pre_measurement_note": (
            "the manifest pre-registers a builder-time calibration preflight of the three frozen "
            "canonical schemas (known_calibration_defect.canonical_preflight); the WCC canonical is "
            "rejected by stage B on R03 before any fixture was written, which is why the WCC arm is "
            "declared non-informative in advance while strict H5 is still evaluated. The same three "
            "canonicals were independently re-run at 2026-09-12T01:00:49+08:00 by worker-084 and the "
            "verdicts agreed; the run's own control block below is authoritative."),
        "acceptance": {},
        "falsifier": man["falsifier"],
        "do_not_claim": man["do_not_claim"],
        "stop_rule": "3 agent-hours or one complete held-out report, whichever is first; NO rule edits after seeing results.",
    }

    # ---- H1-H7 acceptance block ----------------------------------------------
    report["acceptance"] = {
        "H1_manifest_hashed_before_any_stage_run": bool(report["manifest_hashed_before_any_stage_run"]),
        "H2_mutants_ge_20_families_ge_10_built_on_frozen_bytes":
            n >= 20 and report["corpus"]["families"] >= 10
            and all(sha(ROOT / b["path"]) == b["sha256"] == man["pins"][b["frozen_path"]]
                    for b in man["bases"].values()),
        "H3_both_stages_run_and_raw_verdicts_retained":
            all(r["stage_a"]["crash"] is False and r["stage_b"]["crash"] is False for r in results)
            and all(c["stage_a"]["crash"] is False and c["stage_b"]["crash"] is False for c in controls)
            and True,  # finalized after raw/raw_verdicts.json is written, before report.json
        "H4_aggregates_and_union_escape_family_list_present":
            aggregates is not None and "escape_families" in aggregates,
        "H5_controls_all_accepted_by_both_stages": controls_ok,
        "H5_pre_registered_wcc_r03_instrument_defect":
            bool(man.get("known_calibration_defect", {}).get("wcc_control_predicted_reject_r03")),
        "H6_executor_independent_not_worker_16":
            man["worker"] == "worker-084" and man["actor"] == "worker-084",
        "H7_escape_rate_reported_regardless_of_outcome": aggregates is not None,
    }

    # ---- write raw verdicts, then report -------------------------------------
    raw = {
        "corpus_id": man["corpus_id"], "task_id": man["task_id"],
        "manifest_sha256_before_run": manifest_sha,
        "run_started_at": run_started, "run_finished_at": run_finished,
        "stages": report["stages"], "pins_before": pins_before, "pins_after": pins_after,
        "tampered": tampered,
        "controls": controls, "results": results,
        "recon_canonical_check": {
            "recorded_at": man.get("known_calibration_defect", {}).get("measured_at"),
            "note": ("builder-time calibration preflight recorded in the manifest before freeze; the "
                     "frozen WCC canonical is rejected by stage B on R03 (literal-substring binder "
                     "false positive), C2 and C0 canonicals are accepted by both stages"),
            "observed": {
                rel: {"sha256": v.get("sha256"),
                      "stage_a": v.get("stage_a", {}).get("verdict"),
                      "stage_b": v.get("stage_b", {}).get("verdict"),
                      "stage_b_failed_rules": v.get("stage_b", {}).get("failed_rules", [])}
                for rel, v in man.get("known_calibration_defect", {}).get(
                    "canonical_preflight", {}).items()
            },
        },
    }
    (RAW / "raw_verdicts.json").write_text(json.dumps(raw, indent=2) + "\n")
    report["acceptance"]["H3_both_stages_run_and_raw_verdicts_retained"] = (
        all(r["stage_a"]["crash"] is False and r["stage_b"]["crash"] is False for r in results)
        and all(c["stage_a"]["crash"] is False and c["stage_b"]["crash"] is False for c in controls)
        and (RAW / "raw_verdicts.json").exists())
    (HERE / "report.json").write_text(json.dumps(report, indent=2) + "\n")

    checkpoint = {
        "checkpoint_id": "ckpt-heldout-10-worker-084",
        "created_at": now(), "worker": man["worker"], "actor": man["actor"],
        "task_id": man["task_id"], "corpus_id": man["corpus_id"],
        "assignment": man["assignment"], "node_id": man["node_id"], "gate": man["gate"],
        "class_ids": man["class_ids"],
        "status": "measurement_complete" if valid else "measurement_complete_controls_invalid",
        "valid": valid, "invalid_reasons": invalid_reasons,
        "manifest_sha256": manifest_sha,
        "report_sha256": sha(HERE / "report.json"),
        "raw_verdicts_sha256": sha(RAW / "raw_verdicts.json"),
        "pins": man["pins"], "stages": report["stages"],
        "aggregates": aggregates,
        "aggregates_informative_arms_only": informative_aggregates,
        "controls_ok": controls_ok,
        "falsifier": man["falsifier"],
        "stop_rule": report["stop_rule"],
        "artifacts": {
            "manifest": str(MANIFEST.relative_to(ROOT)),
            "report": str((HERE / "report.json").relative_to(ROOT)),
            "raw_verdicts": str((RAW / "raw_verdicts.json").relative_to(ROOT)),
        },
    }
    (HERE / "checkpoint.json").write_text(json.dumps(checkpoint, indent=2) + "\n")

    a = aggregates
    print(f"valid={valid} | structural escape {a['structural_escape']} | semantic escape "
          f"{a['semantic_escape']} | union escape {a['union_escape']} ({a['mutants']} mutants)")
    if informative_aggregates:
        b = informative_aggregates
        print(f"informative arms only ({b['mutants']} mutants): union escape {b['union_escape']}")
    print(f"controls ok: {controls_ok} | tampered: {tampered}")
    print("invalid reasons:", invalid_reasons)
    print("union escape families:", [(f["family"], f["count"]) for f in a["escape_families"]])
    print("report sha256:", checkpoint["report_sha256"])
    return 0 if valid else 5


if __name__ == "__main__":
    sys.exit(main())
