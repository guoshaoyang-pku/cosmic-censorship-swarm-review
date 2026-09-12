#!/usr/bin/env python3
"""A2 independent check — lead-audit lifecycle-10 (one lifecycle, read-only w.r.t. canonical).

Measures, at the pinned repaired harness `0fae94bf0190`:
  1. canonical bytes before/after every probe (drift check);
  2. author self-test and a fresh design-bound synthetic dry run into a private outdir;
  3. negative controls: --execute fail-closed, unmarked output name refused, no-output run;
  4. HF-A2-19-01: is the A2-registered artifact evaluation/ablation.csv an unmarked dry run?
  5. the A2 review binding table: which reviews bind which target hash.

Writes only under artifacts/audit/l10/. Emits a JSON summary on stdout path.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
L10 = ROOT / "artifacts" / "audit" / "l10"
OUT = L10 / "out"
HARNESS = ROOT / "evaluation" / "ablation_harness.py"
DESIGN = ROOT / "evaluation" / "ablation_design.yaml"

CANONICAL = [
    "evaluation/ablation_harness.py",
    "evaluation/ablation_design.yaml",
    "evaluation/ablation.csv",
    "evaluation/ablation_report.json",
    "evaluation/ablation_dryrun.csv",
    "evaluation/ablation_dryrun_report.json",
]
REVIEWS = [
    "reviews/A2-review-18.json",
    "reviews/A2-review-022.json",
    "reviews/A2-review-19.json",
    "reviews/A2-review-worker-067.json",
    "reviews/A2-hf19-adjudication-worker-067.json",
]


def sha(p: Path) -> str | None:
    if not p.is_file():
        return None
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run(args, timeout=300, name=None):
    r = subprocess.run([sys.executable, *args], cwd=ROOT, capture_output=True, text=True,
                       timeout=timeout)
    tail = "\n".join((r.stdout or "").strip().splitlines()[-4:])
    out = {"rc": r.returncode, "stdout_tail": tail[-800:], "stderr_tail": (r.stderr or "")[-500:]}
    if name:  # full logs, same run as the hashes recorded below
        logs = L10 / "logs"
        logs.mkdir(parents=True, exist_ok=True)
        (logs / f"{name}.stdout").write_text(r.stdout or "")
        (logs / f"{name}.stderr").write_text(r.stderr or "")
        out["stdout_sha256"] = sha(logs / f"{name}.stdout")
        out["stderr_sha256"] = sha(logs / f"{name}.stderr")
    return out


def main() -> int:
    L10.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    before = {p: sha(ROOT / p) for p in CANONICAL}
    harness_now = sha(HARNESS)
    result: dict = {
        "schema": "audit-l10-a2-independent-check/1",
        "harness_path": "evaluation/ablation_harness.py",
        "harness_sha256": harness_now,
        "harness_pin_expected": "0fae94bf01903ec7b8076a6b11706bc4444b19f98e6d0985e4ac2d1b2921f157",
        "harness_pin_matches": harness_now
        == "0fae94bf01903ec7b8076a6b11706bc4444b19f98e6d0985e4ac2d1b2921f157",
        "canonical_before": before,
        "probes": {},
    }

    result["probes"]["self_test"] = run([str(HARNESS), "--self-test"], name="self_test")
    result["probes"]["fresh_design_dry_run"] = run(
        [str(HARNESS), "--dry-run", "--design", str(DESIGN), "--outdir", str(OUT)],
        name="fresh_design_dry_run")
    result["probes"]["execute_refusal"] = run(
        [str(HARNESS), "--execute", "--outdir", str(L10 / "out_exec")], name="execute_refusal")
    unmarked = L10 / "unmarked_report.json"
    result["probes"]["unmarked_output_refusal"] = run(
        [str(HARNESS), "--dry-run", "--design", str(DESIGN),
         "--json-out", str(unmarked), "--csv-out", str(L10 / "unmarked.csv")],
        name="unmarked_output_refusal")
    result["probes"]["no_output_run"] = run(
        [str(HARNESS), "--dry-run", "--design", str(DESIGN)], name="no_output_run")

    after = {p: sha(ROOT / p) for p in CANONICAL}
    result["canonical_after"] = after
    result["canonical_drift"] = {p: [before[p], after[p]] for p in CANONICAL if before[p] != after[p]}

    report_path = OUT / "ablation_dryrun_report.json"
    csv_path = OUT / "ablation_dryrun.csv"
    if report_path.is_file():
        rep = json.loads(report_path.read_text())
        bc = rep.get("budget_check", {})
        arms = rep.get("arms", [])
        result["dry_run"] = {
            "report_sha256": sha(report_path),
            "csv_sha256": sha(csv_path),
            "run_mode": rep.get("run_mode"),
            "simulated": rep.get("simulated"),
            "budget_check_matched": bc.get("matched"),
            "budget_check_keys": sorted(bc.keys()),
            "primary_comparison_valid": rep.get("primary_comparison_valid"),
            "n_arms": len(arms),
            "arm_ids": [a.get("arm_id") for a in arms],
            "arm_wall_s": {a.get("arm_id"): a.get("wall_clock_s") for a in arms},
            "token_spread": bc.get("token_spread"),
            "wall_spread_consumption": bc.get("wall_spread_consumption"),
            "wall_spread_envelope": bc.get("wall_spread_envelope"),
            "wall_match_basis": bc.get("wall_match_basis"),
            "matched_fields": bc.get("matched_fields") or rep.get("matched_fields"),
            "design_deviations": rep.get("design_deviations"),
            "csv_header": csv_path.read_text().splitlines()[0].split(",") if csv_path.is_file() else None,
        }

    # HF-A2-19-01: the map-registered A2 artifact vs the design inventory.
    reg = ROOT / "evaluation" / "ablation.csv"
    dry = ROOT / "evaluation" / "ablation_dryrun.csv"
    old_report = ROOT / "evaluation" / "ablation_report.json"
    reg_head = reg.read_text().splitlines()[0].split(",") if reg.is_file() else []
    dry_head = dry.read_text().splitlines()[0].split(",") if dry.is_file() else []
    marker_cols = [c for c in reg_head
                   if any(t in c.lower() for t in ("sim", "synthetic", "dry", "status", "provenance", "mode", "harness"))]
    orj = json.loads(old_report.read_text()) if old_report.is_file() else {}
    result["hf_a2_19_01"] = {
        "registered_artifact": "evaluation/ablation.csv",
        "registered_sha256": sha(reg),
        "registered_n_columns": len(reg_head),
        "registered_marker_columns": marker_cols,
        "registered_header": reg_head,
        "marked_dryrun_sha256": sha(dry),
        "marked_dryrun_marker_columns": [c for c in dry_head
                                         if any(t in c.lower() for t in ("sim", "synthetic", "dry", "status", "provenance", "mode", "harness"))],
        "ablation_report_generator_sha256": orj.get("generator_sha256"),
        "ablation_report_assignment": orj.get("assignment") or orj.get("note") or orj.get("summary"),
        "design_artifact_inventory": None,
    }
    # design inventory lines (yaml text, no parser dependency)
    try:
        lines = DESIGN.read_text().splitlines()
        result["hf_a2_19_01"]["design_artifact_inventory"] = [
            f"{i+1}:{lines[i]}" for i in range(len(lines))
            if "ablation" in lines[i] and ("csv" in lines[i] or "report" in lines[i])
        ][:12]
    except Exception as e:  # pragma: no cover
        result["hf_a2_19_01"]["design_artifact_inventory"] = f"unreadable: {e}"

    # binding table for the existing A2 reviews
    table = []
    for rp in REVIEWS:
        p = ROOT / rp
        if not p.is_file():
            table.append({"path": rp, "exists": False})
            continue
        d = json.loads(p.read_text())
        table.append({
            "path": rp,
            "sha256": sha(p),
            "reviewer": d.get("reviewer"),
            "verdict": d.get("verdict"),
            "score": d.get("score"),
            "target_id": d.get("target_id"),
            "target_artifact": d.get("artifact"),
            "target_sha256": d.get("target_sha256") or d.get("reviewed_sha256")
            or d.get("artifact_sha256") or d.get("harness_sha256"),
            "created_at": d.get("created_at"),
            "full_schema": d.get("full_schema"),
            "hard_failures": d.get("hard_failures"),
            "binds_repaired_harness": (
                (d.get("target_sha256") or d.get("reviewed_sha256") or "")
                == result["harness_pin_expected"]
            ),
        })
    result["review_binding_table"] = table

    summary_path = L10 / "a2_independent_check.json"
    summary_path.write_text(json.dumps(result, indent=2, sort_keys=True))
    print(json.dumps({
        "summary_path": str(summary_path.relative_to(ROOT)),
        "summary_sha256": sha(summary_path),
        "harness_pin_matches": result["harness_pin_matches"],
        "probe_rcs": {k: v["rc"] for k, v in result["probes"].items()},
        "canonical_drift": result["canonical_drift"],
        "budget_check_matched": result.get("dry_run", {}).get("budget_check_matched"),
        "primary_comparison_valid": result.get("dry_run", {}).get("primary_comparison_valid"),
        "registered_marker_columns": result["hf_a2_19_01"]["registered_marker_columns"],
        "binding_at_repaired_pin": sum(1 for t in table if t.get("binds_repaired_harness")),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
