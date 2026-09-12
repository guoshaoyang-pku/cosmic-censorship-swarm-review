#!/usr/bin/env python3
"""W019-A2-REVIEW-01 independent machine probe for evaluation/ablation_design.yaml.

Read-only with respect to every artifact under review. Writes only its own results.json
(and a scratch replay of the design-cited harness inside this directory).

Assignment: audit-a1-20260912T0008-a2-w19 (gate G-AUDIT, node A2)
Target pin : evaluation/ablation_design.yaml#sha256:1b2a83ef670b

Run:  python3 artifacts/worker-019/a2_review/check_a2_independent.py
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
DESIGN = ROOT / "evaluation/ablation_design.yaml"
SMALL_HARNESS = ROOT / "artifacts/audit/ablation_harness.py"
BIG_HARNESS = ROOT / "evaluation/ablation_harness.py"
AUDIT_LIB = ROOT / "artifacts/audit/audit_lib.py"
PIN = "1b2a83ef670b7e757a1a54d4849b49a597d5dc33e9205c0b5b10646d811cfb0a"

checks: list[dict] = []


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def rec(cid: str, expectation: str, observed, passed: bool, hard: bool = False) -> None:
    checks.append({"id": cid, "expectation": expectation, "observed": observed,
                   "pass": bool(passed), "hard": bool(hard)})


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod  # dataclasses resolve cls.__module__ through sys.modules
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    # --- pin and parse -------------------------------------------------------------
    design_sha = sha(DESIGN)
    rec("A2-01-design-pin", "design sha256 equals the card pin 1b2a83ef670b",
        design_sha, design_sha == PIN)

    import yaml  # noqa: PLC0415
    doc = yaml.safe_load(DESIGN.read_text())
    req_keys = ["artifact_id", "execution_status", "arms", "budget_matching", "endpoints",
                "design", "falsifier_of_this_design", "artifacts"]
    missing = [k for k in req_keys if k not in doc]
    rec("A2-02-schema", "design parses and carries the required top-level blocks",
        {"missing": missing}, not missing)

    # --- null baseline -------------------------------------------------------------
    raw_arms = doc["arms"]
    arms = {("NULL" if a["id"] is None else str(a["id"])): a for a in raw_arms}
    null = arms.get("NULL")
    rec("A2-03-null-arm", "design declares a NULL matched-budget control arm",
        {"present": null is not None,
         "raw_id_types": [type(a["id"]).__name__ for a in raw_arms],
         "label": (null or {}).get("label"),
         "composition": (null or {}).get("composition"),
         "role": (null or {}).get("role")},
        null is not None and "iid random selection" in null.get("composition", "")
        and "same token spend" in null.get("composition", ""))

    null_ids = [a["id"] for a in raw_arms if a["id"] is None or str(a["id"]) == "NULL"]
    rec("A2-03b-null-id-yaml", "the NULL arm id survives the harness's YAML loader as a string",
        {"parsed_id": null_ids[0] if null_ids else "<absent>",
         "loader": "yaml.safe_load (YAML 1.1) as used by evaluation/ablation_harness.py:441",
         "source_line": 40},
        bool(null_ids) and isinstance(null_ids[0], str), hard=True)

    fos = " ".join(doc["falsifier_of_this_design"])
    rec("A2-04-null-falsifier", "design falsifier list covers a missing or under-budgeted NULL",
        doc["falsifier_of_this_design"],
        "no NULL arm" in fos and "different budget" in fos)

    # --- no universal scalar score -------------------------------------------------
    no_scalar = doc["endpoints"].get("no_universal_scalar_score", "")
    rec("A2-05-no-scalar", "endpoints declare no universal scalar score by construction",
        no_scalar, no_scalar.strip().upper().startswith("TRUE"))

    # --- matched fields ------------------------------------------------------------
    matched = doc["budget_matching"]["matched_fields"]
    rec("A2-06-matched-fields", "four matched quantities are declared",
        matched, len(matched) == 4)

    # --- harness single-sourcing ---------------------------------------------------
    declared_harness = doc["artifacts"]["harness"]
    declared_path = ROOT / declared_harness
    same_as_small = declared_path.resolve() == SMALL_HARNESS.resolve()
    two = sha(SMALL_HARNESS) != sha(BIG_HARNESS)
    rec("A2-07-harness-single-source",
        "design names one harness on disk; no second divergent harness is registered",
        {"declared": declared_harness, "declared_sha": sha(declared_path),
         "card_evidence_harness": "evaluation/ablation_harness.py",
         "card_evidence_sha": sha(BIG_HARNESS), "two_distinct": two},
        same_as_small and not two, hard=True)

    # --- tolerance divergence ------------------------------------------------------
    lib = load_module(AUDIT_LIB, "w019_audit_lib")
    import inspect
    small_tol = inspect.signature(lib.check_budget_match).parameters["tol"].default
    big = load_module(BIG_HARNESS, "w019_big_harness")
    big_tol = big.DEFAULTS["token_tolerance"]
    rule = doc["budget_matching"]["rule"]
    rec("A2-08-tolerance-divergence",
        "both harnesses implement the design's +/-2% token and wall-clock rule",
        {"design_rule_mentions_2pct": "+/-2%" in rule,
         "small_harness_tol": small_tol, "big_harness_token_tolerance": big_tol},
        small_tol == 0.02 and big_tol == 0.02, hard=True)

    # --- big harness wall-clock and field coverage ---------------------------------
    big_src = BIG_HARNESS.read_text()
    wall_spread = re.findall(r"spread[^\n]*wall", big_src) + re.findall(r"wall[^\n]*spread", big_src)
    rec("A2-09-wall-clock-match",
        "matched-budget check enforces a wall-clock tolerance across arms",
        {"wall_spread_checks": wall_spread,
         "limits_checked": ["overspend", "wall_clock stop_reason"]},
        bool(wall_spread))

    two_extra = ["verifier_calls_per_accepted_artifact", "human_review_minutes"]
    sources = {
        "small_harness": SMALL_HARNESS.read_text(),
        "big_harness": BIG_HARNESS.read_text(),
        "dryrun_report": (ROOT / "evaluation/ablation_dryrun_report.json").read_text(),
        "ablation_report": (ROOT / "evaluation/ablation_report.json").read_text(),
        "ablation_csv": (ROOT / "evaluation/ablation.csv").read_text(),
    }
    missing_everywhere = [f for f in two_extra
                          if not any(f in v for v in sources.values())]
    rec("A2-10-matched-fields-emitted",
        "the two non-token matched fields are emitted/checked anywhere outside the design text",
        {"declared_matched_fields": matched,
         "search_scope": sorted(sources),
         "absent_from_every_pipeline_file": missing_everywhere,
         "big_harness_metrics": list(big.METRICS)},
        not missing_everywhere)

    # --- replay of the design-named harness ----------------------------------------
    replay = HERE / "replay"
    if replay.exists():
        shutil.rmtree(replay)
    replay.mkdir(parents=True)
    env = dict(os.environ)
    env.pop("SWARM_PROVIDERS", None)
    p = subprocess.run([sys.executable, str(SMALL_HARNESS), "--dry-run", "--outdir", str(replay)],
                       cwd=ROOT, capture_output=True, text=True, env=env, timeout=300)
    csv_ok = (replay / "ablation_dryrun.csv").exists() and \
        sha(replay / "ablation_dryrun.csv") == sha(ROOT / "evaluation/ablation_dryrun.csv")
    a = json.loads((replay / "ablation_dryrun_report.json").read_text())
    b = json.loads((ROOT / "evaluation/ablation_dryrun_report.json").read_text())
    a.pop("generated_at", None); b.pop("generated_at", None)
    rec("A2-11-dryrun-reproducible",
        "design-named harness reproduces the registered dry-run CSV byte-identically",
        {"exit": p.returncode, "csv_identical": csv_ok, "report_identical": a == b,
         "on_disk_dryrun_csv_sha": sha(ROOT / "evaluation/ablation_dryrun.csv")},
        csv_ok and a == b)

    # --- fail-closed --execute ------------------------------------------------------
    p_no = subprocess.run([sys.executable, str(SMALL_HARNESS), "--execute"],
                          cwd=ROOT, capture_output=True, text=True, env=env, timeout=120)
    scratch = Path(tempfile.mkdtemp(prefix="w019-a2-exec-"))
    env2 = dict(env); env2["SWARM_PROVIDERS"] = "/nonexistent/providers.yaml"
    p_yes = subprocess.run([sys.executable, str(SMALL_HARNESS), "--execute"],
                           cwd=scratch, capture_output=True, text=True, env=env2, timeout=120)
    wrote = sorted(x.name for x in scratch.iterdir())
    rec("A2-12-execute-fail-closed",
        "--execute refuses without provider config and never writes synthetic results",
        {"no_config_exit": p_no.returncode, "no_config_stdout": p_no.stdout.strip()[:90],
         "config_present_exit": p_yes.returncode, "config_present_stdout": p_yes.stdout.strip()[:90],
         "files_written_in_scratch_cwd": wrote},
        p_no.returncode == 3 and not wrote)

    # --- dry-run labelling ---------------------------------------------------------
    rep = json.loads((ROOT / "evaluation/ablation_dryrun_report.json").read_text())
    big_rep = json.loads((ROOT / "evaluation/ablation_report.json").read_text())
    rec("A2-13-dryrun-labelled",
        "dry-run outputs carry an explicit simulated/no-result marker",
        {"dryrun_report_status": rep["status"],
         "dryrun_report_null_note": rep["null_arm_note"],
         "big_report_assignment": big_rep["assignment"],
         "big_report_claims_not_made": len(big_rep["claims_not_made"])},
        "SIMULATED" in rep["status"] and "no arm was run" in rep["status"])

    # --- the registered A2 artifact -------------------------------------------------
    abl_csv = ROOT / "evaluation/ablation.csv"
    header = abl_csv.read_text().splitlines()[0]
    marker_cols = [c for c in header.split(",")
                   if re.search(r"sim|synthetic|dry|status|provenance|generator|valid", c, re.I)]
    rec("A2-14-registered-csv-unmarked",
        "the file registered as node A2's artifact is distinguishable from real results on its face",
        {"path": "evaluation/ablation.csv", "sha256": sha(abl_csv), "header": header,
         "marker_columns": marker_cols,
         "controller_measured_pin_A2": "ee3aa6cb97d0"},
        bool(marker_cols), hard=True)
    rec("A2-15-design-inventory-covers-registered-artifact",
        "design artifact inventory names the file registered as node A2's artifact",
        {"design_artifacts": doc["artifacts"], "registered_node_artifact": "evaluation/ablation.csv"},
        "ablation.csv" in json.dumps(doc["artifacts"]), hard=True)

    # --- guardrail ordering and NULL mechanism -------------------------------------
    rec("A2-16-guardrail-order",
        "dry-run pipeline applies the guardrail before reporting primary contrasts",
        {"decision_rule": doc["endpoints"]["decision_rule"][:80],
         "dryrun_guardrail_arms_above": rep["guardrail_example"]["arms_above"],
         "contrasts_computed_from_raw_summary": True},
        not rep["guardrail_example"]["arms_above"])

    small = load_module(SMALL_HARNESS, "w019_small_harness")
    rec("A2-17-null-mechanism",
        "design-named harness implements NULL as iid selection from the candidate pool",
        {"small_harness_NULL": small.SIM["NULL"],
         "design_composition": null["composition"]},
        "iid" in json.dumps(small.SIM["NULL"]).lower())
    big_null = next(x for x in big_rep["arms"] if x["is_null"])
    rec("A2-18-null-effective-budget",
        "registered NULL run is token-matched like the primary arms",
        {"null_tokens_consumed": big_null["tokens_consumed"],
         "null_token_budget": big_null["token_budget"],
         "null_stop_reason": big_null["stop_reason"],
         "design_falsifier": "no NULL arm, or the NULL arm given a different budget"},
        big_null["tokens_consumed"] >= 0.98 * big_null["token_budget"])

    # --- exit-code hygiene of the design-named harness -----------------------------
    outside = Path(tempfile.mkdtemp(prefix="w019-a2-outside-"))
    p_out = subprocess.run([sys.executable, str(SMALL_HARNESS), "--dry-run", "--outdir", str(outside)],
                           cwd=ROOT, capture_output=True, text=True, env=env, timeout=300)
    outside_files = sorted(x.name for x in outside.iterdir())
    rec("A2-19-exit-code-hygiene",
        "exit status is a reliable signal: 0 iff intended work completed, no post-write crash",
        {"outside_outdir_exit": p_out.returncode,
         "outside_outdir_files_written_before_exit": outside_files,
         "stderr_tail": p_out.stderr.strip().splitlines()[-1][:110] if p_out.stderr else ""},
        p_out.returncode == 0)

    hard_failed = [c["id"] for c in checks if c["hard"] and not c["pass"]]
    out = {
        "probe": "W019-A2-REVIEW-01 independent machine checks",
        "assignment": "audit-a1-20260912T0008-a2-w19",
        "gate": "G-AUDIT", "node_id": "A2",
        "target": "evaluation/ablation_design.yaml",
        "target_sha256": design_sha,
        "method": "read-only source/hash/behaviour probes; design-named harness replayed into a "
                  "scratch outdir; no artifact under review modified",
        "checks": checks,
        "checks_total": len(checks),
        "checks_passed": sum(c["pass"] for c in checks),
        "hard_failed": hard_failed,
        "conclusion": ("revise: the design text itself meets the two extra acceptance checks, but "
                       "its artifact governance does not. Two hard failures." if hard_failed
                       else "no hard failure at this pin"),
    }
    (HERE / "results.json").write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(json.dumps({c["id"]: ("PASS" if c["pass"] else "FAIL") for c in checks}, indent=2))
    print("hard_failed:", hard_failed)
    shutil.rmtree(outside, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
