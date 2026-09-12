#!/usr/bin/env python3
"""Closure checker for the A2 harness repair (author self-check, NOT a review verdict).

Reads the repaired dry-run report/CSV and the live canonical harness bytes, then asserts each
blocking review finding is closed at the new pin, or records the residue that belongs to the
design owner (astra-lead-audit).  Also re-runs the harness with no output arguments and proves
the pinned canonical dry-run files are not mutated.

Findings mapped:
  R18/R22/R67-B1  wall-clock matching was vacuous
  R18/R22/R67-B2  two declared matched fields never measured
  R18/R22/R67-B3  tolerance divergence (0.15 vs pre-registered 0.02)
  R67-N3          envelope vs consumption reading undecided
  R19-HF-01/08    dry run mistakable for a real result (no markers)
  R19-HF-02       two byte-different harness copies / not single-sourced
  R19-HF-03       unquoted `- id: NULL` lost by yaml.safe_load
  R19-06          guardrail not applied before contrasts
  R22-N5          default/outdir runs can mutate canonical dry-run files
  R19-07          unreliable exit status
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

CST = timezone(timedelta(hours=8))
CANONICAL_DRYRUN_FILES = (
    "evaluation/ablation.csv",
    "evaluation/ablation_report.json",
    "evaluation/ablation_dryrun.csv",
    "evaluation/ablation_dryrun_report.json",
    "evaluation/ablation_design.yaml",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--report", required=True)
    ap.add_argument("--csv", required=True)
    ap.add_argument("--old-harness", required=True)
    ap.add_argument("--log", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    repo = Path(a.repo).resolve()
    report = json.loads(Path(a.report).read_text())
    csv_text = Path(a.csv).read_text()
    log = Path(a.log).read_text()
    harness = repo / "evaluation" / "ablation_harness.py"
    old = Path(a.old_harness)
    checks = []

    def rec(cid, finding, ok, detail):
        checks.append({"check_id": cid, "finding": finding, "pass": bool(ok), "detail": detail})

    bc = report["budget_check"]
    dmf = bc["declared_matched_fields"]

    # B1 -- wall-clock matching is non-vacuous
    wall_vals = bc["wall_basis_reading"]["consumption"]["per_arm"]
    rec("C-B1", "R18/R22/R67-B1 wall-clock matching vacuous",
        bc["wall_consumption_spread_fraction"] is not None
        and len(set(wall_vals.values())) > 1
        and bc["wall_consumption_spread_fraction"] <= report["config"]["wall_tolerance"]
        and bc["wall_match_basis"] == "consumption",
        f"per-arm wall s={wall_vals}, spread={bc['wall_consumption_spread_fraction']:.4f}, "
        f"basis={bc['wall_match_basis']}")

    # B2 -- both extra declared fields measured and emitted
    per_arm = report["arms"]
    rec("C-B2", "R18/R22/R67-B2 declared matched fields never measured",
        all(f in dmf and dmf[f]["measured"] for f in
            ("total_completion_tokens", "wall_clock_s",
             "verifier_calls_per_accepted_artifact", "human_review_minutes"))
        and all(x["verifier_calls_per_accepted_artifact"] is not None
                and x["human_review_minutes"] is not None for x in per_arm),
        f"declared={ {k: (round(v['spread_fraction'], 4), v['matched']) for k, v in dmf.items()} }, "
        f"unmatched={bc['unmatched_declared_fields']} (flagged, design owner)")

    # B3 -- tolerances equal the pre-registered 2%
    rec("C-B3", "R18/R22/R67-B3 tolerance divergence",
        report["config"]["token_tolerance"] == 0.02 and report["config"]["wall_tolerance"] == 0.02
        and dmf["total_completion_tokens"]["tolerance"] == 0.02,
        f"token={report['config']['token_tolerance']} wall={report['config']['wall_tolerance']}")

    # N3 -- both readings computed, chosen basis explicit
    reading = bc["wall_basis_reading"]
    rec("C-N3", "R67-N3 envelope vs consumption reading undecided",
        set(reading) == {"envelope", "consumption"} and bc["wall_match_basis"] == "consumption"
        and "envelope" in reading and "consumption" in reading,
        f"basis={bc['wall_match_basis']}, envelope matched={reading['envelope']['matched']}, "
        f"consumption matched={reading['consumption']['matched']}")

    # HF-01/08 -- dry-run cannot be mistaken for a real result
    lines = csv_text.splitlines()
    header = lines[0].split(",")
    data_ok = all(line.split(",")[0] in ("True", "true") and line.split(",")[1] == "dry_run_synthetic"
                  for line in lines[1:])
    rec("C-HF01", "R19-HF-01/08 dry run mistakable for a real result",
        report.get("simulated") is True and report.get("run_mode") == "dry_run_synthetic"
        and bool(report.get("simulation_disclaimer"))
        and all(c in header for c in ("simulated", "run_mode", "harness_sha256")) and data_ok,
        f"report simulated={report.get('simulated')} mode={report.get('run_mode')}; "
        f"csv header has markers={all(c in header for c in ('simulated','run_mode','harness_sha256'))}, "
        f"rows marked={data_ok}")

    # HF-02 -- the generator hash binds the canonical harness bytes
    harness_sha = sha256(harness)
    audit_copy = repo / "artifacts" / "audit" / "ablation_harness.py"
    audit_sha = sha256(audit_copy) if audit_copy.exists() else None
    rec("C-HF02", "R19-HF-02 two byte-different harness copies / not single-sourced",
        report["generator_sha256"] == harness_sha
        and report["provenance"]["harness_sha256"] == harness_sha
        and old.exists() and sha256(old) == "df878e97bf6ede6c41e540dcf20664e51c9963cf44d74c2f5f9a9005bc8af432",
        f"report generator == live canonical == {harness_sha[:12]}; "
        f"audit copy {str(audit_sha)[:12] if audit_sha else None} still differs "
        f"(design line 172 names the audit copy: lead-audit owner item)")

    # HF-03 -- NULL id survives the loader
    rec("C-HF03", "R19-HF-03 unquoted `- id: NULL` lost by yaml.safe_load",
        report["provenance"]["design_null_ids_normalized"] == ["NULL"]
        and "NULL" in report["provenance"]["design_arm_ids"],
        f"normalized={report['provenance']['design_null_ids_normalized']} "
        f"ids={report['provenance']['design_arm_ids']}")

    # 19-06 -- guardrail first
    rec("C-1906", "R19-06 guardrail not applied before contrasts",
        report["guardrail"]["applied_first"] is True
        and report["primary_endpoint"]["guardrail_applied"] is True
        and report["decision_rule"]["order"][0].startswith("(1) guardrail"),
        f"order={report['decision_rule']['order']}, "
        f"arms_above={report['guardrail']['arms_above']}")

    # 19-07 -- exit codes: dry run 0, guard refusal 2, execute refusal 3
    codes = {m.group(1): int(m.group(2)) for m in re.finditer(r"(\w+)_exit=(\d+)", log)}
    rec("C-1907", "R19-07 unreliable exit status",
        codes.get("selftest") == 0 and codes.get("dryrun") == 0
        and codes.get("guard") == 2 and codes.get("execute") == 3,
        f"exit codes observed: {codes}")

    # 19-04/05 -- NULL is a marked control, not a primary arm; semantics residue recorded
    null = report["null_baseline"]
    rec("C-1904", "R19-04/05 NULL semantics / episode exhaustion",
        null is not None and all(not (x["is_null"] and x["is_primary"]) for x in per_arm)
        and any("null" in lim.lower() for lim in report["limitations"]),
        f"null arm={null['arm']}, control-only, exhaustion disclosed in limitations")

    # R22-N5 -- a run with no output arguments must not mutate the pinned canonical files
    before = {p: sha256(repo / p) for p in CANONICAL_DRYRUN_FILES if (repo / p).exists()}
    proc = subprocess.run([sys.executable, str(harness), "--dry-run"], cwd=str(repo),
                          capture_output=True, text=True, timeout=300)
    after = {p: sha256(repo / p) for p in before}
    rec("C-N5", "R22-N5 outdir/default run can mutate canonical dry-run files",
        proc.returncode == 0 and before == after,
        f"no-output run exit={proc.returncode}; canonical files unchanged={before == after}")

    # determinism: two fresh dry runs must agree modulo timestamps
    tmp = Path(a.out).parent / "out"
    tmp.mkdir(parents=True, exist_ok=True)
    outs = []
    for i in (1, 2):
        out = tmp / f"ablation_dryrun_recheck{i}.json"
        subprocess.run([sys.executable, str(harness), "--dry-run", "--json-out", str(out)],
                       cwd=str(repo), capture_output=True, text=True, timeout=300, check=True)
        doc = json.loads(out.read_text())
        doc.pop("generated_at", None)
        doc.get("provenance", {}).pop("generated_at", None)
        outs.append(doc)
    rec("C-DET", "determinism of repaired harness",
        outs[0] == outs[1], "two fresh dry runs identical modulo generated_at")

    result = {
        "checker": "a2_harness_repair_closure_check",
        "authority": "worker self-check, NOT an independent review verdict; no gate status set",
        "checked_at": datetime.now(CST).isoformat(timespec="seconds"),
        "canonical_harness": {"path": "evaluation/ablation_harness.py", "sha256": harness_sha,
                              "version": report["harness_version"]},
        "prev_harness_sha256": sha256(old) if old.exists() else None,
        "report_sha256": sha256(Path(a.report)),
        "csv_sha256": sha256(Path(a.csv)),
        "checks_total": len(checks),
        "checks_passed": sum(1 for c in checks if c["pass"]),
        "all_pass": all(c["pass"] for c in checks),
        "checks": checks,
        "residue_for_design_owner": [
            {"item": "design line 172 names artifacts/audit/ablation_harness.py as the harness; the "
                     "canonical path registered by the card/map is evaluation/ablation_harness.py",
             "owner": "astra-lead-audit"},
            {"item": "verifier_calls_per_accepted_artifact and human_review_minutes are declared "
                     "matched but cannot be equalised under token matching across arms of different "
                     "accuracy; design amendment or explicit scope note needed",
             "owner": "astra-lead-audit"},
            {"item": "NULL arm is an iid-uniform declared-rate control, not the design's iid "
                     "candidate-pool draw; harness discloses this",
             "owner": "astra-lead-audit"},
        ],
    }
    Path(a.out).write_text(json.dumps(result, indent=2, sort_keys=True))
    print(json.dumps({k: result[k] for k in ("checks_total", "checks_passed", "all_pass")}, indent=2))
    for c in checks:
        print(f"  [{'ok' if c['pass'] else 'FAIL'}] {c['check_id']} {c['finding']}: {c['detail']}")
    return 0 if result["all_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
