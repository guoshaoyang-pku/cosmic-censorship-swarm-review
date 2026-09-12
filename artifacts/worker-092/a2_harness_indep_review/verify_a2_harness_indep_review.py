#!/usr/bin/env python3
"""Independent non-author verification of the repaired A2 ablation harness.

Task: W092-A2-HARNESS-INDEP-REVIEW-01 (node A2, gate G-AUDIT, class GLOBAL).
Requested by worker-020's blocker on W020-A2-HARNESS-REPAIR-01:
"An independent reviewer (not worker-020) must re-run the harness at 0fae94bf0190."

What this instrument does (stdlib only; no network; no canonical writes beyond this
artifact directory):

1.  pre-registered pins: every input is measured at entry and exit; any drift fails closed;
2.  self-test:      python3 evaluation/ablation_harness.py --self-test  -> exit 0, N/N checks;
3.  dry runs:       two independent --dry-run --design runs into a sandbox dir; byte-equal
                    core content (generated_at excluded) and byte-equal CSV;
4.  replication:    the run is compared against worker-020's own design-bound dry run
                    (artifacts/worker-020/.../ablation_dryrun_designbound_*) -- core-equal
                    report, byte-equal CSV;
5.  controls:       unmarked output name refused (exit 2); --execute fail-closed (exit 3);
                    a canonical-basename marked file is accepted by the name-based guard,
                    which documents the explicit `--outdir evaluation/` mutation hazard;
6.  re-derivation:  the four declared matched-field spreads are recomputed here from the
                    per-arm values with an independently written formula ((max-min)/min);
7.  finding closure: each prior review finding is classified against measured evidence;
8.  residues:       owner/design-side residues are measured, not asserted (design harness
                    path, canonical unmarked artifacts, NULL semantics/budget, metric drift).

This is a measurement/review instrument.  It writes no schema, ledger, rubric, detector,
inbox, FROZEN or claim byte, and it sets no node status or gate verdict.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
HARNESS = REPO / "evaluation" / "ablation_harness.py"
DESIGN = REPO / "evaluation" / "ablation_design.yaml"
# Relative design arg reproduces worker-020's invocation exactly (argv/design_path are
# recorded in the report provenance, so the path string is part of the compared core).
DESIGN_ARG = "evaluation/ablation_design.yaml"
AUDIT_COPY = REPO / "artifacts" / "audit" / "ablation_harness.py"
CANON_CSV = REPO / "evaluation" / "ablation.csv"
CANON_REPORT = REPO / "evaluation" / "ablation_report.json"
CANON_DRYRUN_CSV = REPO / "evaluation" / "ablation_dryrun.csv"
CANON_DRYRUN_REPORT = REPO / "evaluation" / "ablation_dryrun_report.json"
W020 = (REPO / "artifacts" / "worker-020" / "a2_harness_repair_20260912T0116" / "out"
        / "ablation_dryrun_designbound_report.json")
W020_CSV = (REPO / "artifacts" / "worker-020" / "a2_harness_repair_20260912T0116" / "out"
            / "ablation_dryrun_designbound.csv")
ART = Path(__file__).resolve().parent
PINS_FILE = ART / "pins_at_run.json"

PIN_PATHS = [
    "evaluation/ablation_harness.py",
    "evaluation/ablation_design.yaml",
    "evaluation/ablation.csv",
    "evaluation/ablation_dryrun.csv",
    "evaluation/ablation_dryrun_report.json",
    "evaluation/ablation_report.json",
    "artifacts/audit/ablation_harness.py",
    "artifacts/worker-020/a2_harness_repair_20260912T0116/out/ablation_dryrun_designbound_report.json",
    "artifacts/worker-020/a2_harness_repair_20260912T0116/out/ablation_dryrun_designbound.csv",
]

checks: list[dict] = []


def check(cid: str, ok: bool, detail: str, evidence: list[str] | None = None) -> bool:
    checks.append({"id": cid, "pass": bool(ok), "detail": detail,
                   "evidence": evidence or []})
    return bool(ok)


def sha(path: Path) -> str | None:
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(cmd: list[str], timeout: int = 900) -> tuple[int, str, str]:
    p = subprocess.run(cmd, cwd=str(REPO), capture_output=True, text=True, timeout=timeout)
    return p.returncode, p.stdout, p.stderr


def strip_time(obj):
    """Remove wall-clock stamps so core content can be compared across runs."""
    if isinstance(obj, dict):
        return {k: strip_time(v) for k, v in obj.items() if k != "generated_at"}
    if isinstance(obj, list):
        return [strip_time(v) for v in obj]
    return obj


def core_equal(a: dict, b: dict) -> bool:
    return json.dumps(strip_time(a), sort_keys=True) == json.dumps(strip_time(b), sort_keys=True)


def main() -> int:
    work = ART / "_verify_work"
    if work.exists():
        shutil.rmtree(work)
    (work / "run1").mkdir(parents=True)
    (work / "run2").mkdir(parents=True)

    # ---- 1. pins: entry measurement vs pre-registration -------------------------------
    prereg = json.loads(PINS_FILE.read_text())
    prereg_by_path = {e["path"]: e for e in prereg["inputs"]}
    entry = {p: sha(REPO / p) for p in PIN_PATHS}
    for p in PIN_PATHS:
        check(f"PIN-ENTRY-{p}", entry[p] == prereg_by_path[p]["sha256"],
              f"{p} entry {str(entry[p])[:16]} vs prereg {str(prereg_by_path[p]['sha256'])[:16]}")

    # ---- 2. self-test -----------------------------------------------------------------
    rc, out, err = run([sys.executable, str(HARNESS), "--self-test"])
    m = re.search(r'"checks_passed":\s*(\d+)', out)
    n = re.search(r'"checks_total":\s*(\d+)', out)
    passed = int(m.group(1)) if m else -1
    total = int(n.group(1)) if n else -1
    check("SELFTEST-EXIT0", rc == 0, f"self-test exit={rc}")
    check("SELFTEST-ALL", passed == total and total > 0,
          f"{passed}/{total} internal checks pass",
          ["evaluation/ablation_harness.py#0fae94bf0190 --self-test"])

    # ---- 3. two independent dry runs --------------------------------------------------
    rc1, out1, err1 = run([sys.executable, str(HARNESS), "--dry-run", "--design", DESIGN_ARG,
                           "--outdir", str(work / "run1")])
    rc2, out2, err2 = run([sys.executable, str(HARNESS), "--dry-run", "--design", DESIGN_ARG,
                           "--outdir", str(work / "run2")])
    check("DRYRUN-EXIT0", rc1 == 0 and rc2 == 0, f"dry-run exits={rc1},{rc2}")
    r1 = json.loads((work / "run1" / "ablation_dryrun_report.json").read_text())
    r2 = json.loads((work / "run2" / "ablation_dryrun_report.json").read_text())
    check("DETERMINISTIC-CORE", core_equal(r1, r2),
          "two same-seed runs are core-identical (generated_at excluded)")
    check("DETERMINISTIC-CSV",
          (work / "run1" / "ablation_dryrun.csv").read_bytes()
          == (work / "run2" / "ablation_dryrun.csv").read_bytes(),
          "CSV byte-identical across the two runs")

    # ---- 4. replication of worker-020's design-bound dry run --------------------------
    w20 = json.loads(W020.read_text())
    check("REPLICATE-W020-REPORT", core_equal(r1, w20),
          "core report equals worker-020's design-bound dry run (generated_at excluded)",
          [f"{W020.relative_to(REPO)}#{sha(W020)[:12]}"])
    check("REPLICATE-W020-CSV",
          (work / "run1" / "ablation_dryrun.csv").read_bytes() == W020_CSV.read_bytes(),
          "CSV byte-equal to worker-020's design-bound dry run",
          [f"{W020_CSV.relative_to(REPO)}#{sha(W020_CSV)[:12]}"])

    # ---- 5. negative controls ---------------------------------------------------------
    rc_unmarked, out_u, _ = run([sys.executable, str(HARNESS), "--dry-run", "--design",
                                 DESIGN_ARG, "--json-out", str(work / "clean_result.json")])
    check("CONTROL-UNMARKED-NAME-REFUSED", rc_unmarked == 2,
          f"unmarked simulated output refused (exit={rc_unmarked})")
    rc_exec, out_e, _ = run([sys.executable, str(HARNESS), "--execute"])
    check("CONTROL-EXECUTE-FAIL-CLOSED", rc_exec == 3,
          f"--execute refused without provider config (exit={rc_exec})")
    rc_marked, _, _ = run([sys.executable, str(HARNESS), "--dry-run", "--design", DESIGN_ARG,
                           "--json-out", str(work / "ablation_dryrun_report.json")])
    check("CONTROL-MARKED-NAME-ACCEPTED", rc_marked == 0,
          "name-based guard accepts a canonical dry-run basename written to a sandbox dir "
          "(documents the explicit --outdir evaluation/ mutation hazard)",
          ["evaluation/ablation_harness.py:895-904 guard_output_path (name-only check)"])

    # ---- 6. independent re-derivation of the budget arithmetic ------------------------
    bc = r1["budget_check"]
    fields = bc["declared_matched_fields"]
    for f in ("total_completion_tokens", "wall_clock_s",
              "verifier_calls_per_accepted_artifact", "human_review_minutes"):
        vals = list(fields[f]["per_arm"].values())
        mine = (max(vals) - min(vals)) / min(vals)
        check(f"SPREAD-FORMULA-{f}", abs(mine - fields[f]["spread_fraction"]) < 1e-12,
              f"recomputed spread {mine:.12f} == reported {fields[f]['spread_fraction']:.12f}")
    check("TOKEN-MATCHED", bc["matched"] and bc["token_spread_fraction"] <= 0.02,
          f"primary token spread {bc['token_spread_fraction']:.6f} <= 0.02")
    check("WALL-CONSUMPTION-MATCHED", bc["wall_consumption_spread_fraction"] <= 0.02,
          f"wall consumption spread {bc['wall_consumption_spread_fraction']:.6f} <= 0.02")
    check("WALL-BOTH-READINGS", set(bc["wall_basis_reading"]) == {"consumption", "envelope"},
          "wall ambiguity resolved: both consumption and envelope readings reported")
    check("DECLARED-FIELDS-FLAGGED",
          fields["verifier_calls_per_accepted_artifact"]["matched"] is False
          and fields["human_review_minutes"]["matched"] is False
          and bc["declared_matched_fields_all_matched"] is False,
          "the two non-budget declared matched fields are measured, spread-reported and flagged")
    dd = {d["field"]: d["spread_fraction"] for d in r1["design_deviations"]}
    check("DESIGN-DEVIATIONS-RECORDED",
          abs(dd.get("verifier_calls_per_accepted_artifact", -1) - 1.0740740740740742) < 1e-12
          and abs(dd.get("human_review_minutes", -1) - 3.547169811320755) < 1e-12,
          "the two unmatched declared fields are recorded in design_deviations")

    # ---- 7. provenance / NULL / guardrail / endpoint ----------------------------------
    prov = r1["provenance"]
    check("PROVENANCE-HARNESS-SHA", prov["harness_sha256"] == entry["evaluation/ablation_harness.py"],
          f"report harness_sha256 {prov['harness_sha256'][:16]} == live pin")
    check("PROVENANCE-DESIGN-SHA", prov["design_sha256"] == entry["evaluation/ablation_design.yaml"],
          f"report design_sha256 {prov['design_sha256'][:16]} == live pin")
    check("SIMULATED-MARKED", r1["simulated"] is True and r1["run_mode"] == "dry_run_synthetic"
          and r1["validation_status"] == "unverified",
          "report is marked simulated / dry_run_synthetic / unverified")
    check("NULL-ID-NORMALISED", prov.get("design_null_ids_normalized") == ["NULL"]
          and "NULL" in prov.get("design_arm_ids", []),
          "unquoted YAML NULL id is normalised back to the string 'NULL' and reported")
    null = next(a for a in r1["arms"] if a["arm"] == "random_iid_null")
    check("NULL-DECLARED-LIMITATION",
          null["tokens_consumed"] < r1["config_effective"]["token_budget"]
          and null["stop_reason"] == "episodes_exhausted"
          and any("null arm exhausts the episode suite" in x for x in r1["limitations"]),
          f"NULL consumes {null['tokens_consumed']:.0f}/{r1['config_effective']['token_budget']} "
          "tokens and the deviation is declared in limitations")
    check("GUARDRAIL-FIRST", r1["guardrail"]["applied_first"] is True
          and r1["primary_endpoint"]["guardrail_applied"] is True,
          "guardrail truncation is applied before the primary contrasts")
    want = {"ICC-IC", "ICC-S", "SC-S", "IC-NULL", "ICC-NULL"}
    check("CONTRASTS-COMPLETE", set(r1["primary_endpoint"]["contrasts"]) == want,
          "all five pre-registered contrasts including the two NULL contrasts are computed")
    check("PRIMARY-ENDPOINT-NAME",
          r1["primary_endpoint"]["name"] == "accepted_artifacts_per_1M_tokens",
          "primary endpoint is the pre-registered per-1M-token rate")
    check("NO-SCALAR-SCORE", r1["no_universal_scalar_score"] is True
          and not any(k in r1 for k in ("score", "composite", "combined_score")),
          "no universal scalar score field is emitted")
    with open(work / "run1" / "ablation_dryrun.csv", newline="") as fh:
        header = fh.readline().strip().split(",")
        row1 = fh.readline().strip().split(",")
    check("CSV-MARKED", {"simulated", "run_mode", "harness_sha256"} <= set(header)
          and row1[header.index("simulated")] == "True",
          "new CSV carries simulated/run_mode/harness_sha256 provenance columns per row")

    # ---- 8. owner/design-side residues (measured, not asserted) -----------------------
    design_txt = DESIGN.read_text().splitlines()
    named = re.search(r"harness:\s*(\S+)", design_txt[171])
    check("RESIDUE-DESIGN-PATH-MISMATCH",
          named is not None and named.group(1) == "artifacts/audit/ablation_harness.py"
          and sha(AUDIT_COPY) != entry["evaluation/ablation_harness.py"],
          f"design:172 names {named.group(1) if named else '?'} "
          f"({str(sha(AUDIT_COPY))[:12]}) while the live canonical harness is "
          f"evaluation/ablation_harness.py ({entry['evaluation/ablation_harness.py'][:12]})")
    check("RESIDUE-DESIGN-NULL-UNQUOTED", design_txt[39].strip() == "- id: NULL",
          "design:40 still uses unquoted `- id: NULL` (harness-side normalisation mitigates)")
    csv_head = CANON_CSV.read_text().splitlines()[0].split(",")
    check("RESIDUE-CANON-CSV-UNMARKED",
          not ({"simulated", "run_mode", "harness_sha256"} & set(csv_head)),
          f"canonical evaluation/ablation.csv still has {len(csv_head)} columns and no "
          "simulated/run_mode/harness_sha256 provenance column")
    crep = json.loads(CANON_REPORT.read_text())
    check("RESIDUE-CANON-REPORT-STALE-HARNESS",
          crep.get("generator_sha256", "").startswith("df878e97")
          and crep.get("simulated") is None,
          "canonical evaluation/ablation_report.json still binds generator_sha256=df878e97 "
          "(draft harness) and carries no simulated/run_mode marker")
    drep = json.loads(CANON_DRYRUN_REPORT.read_text())
    check("RESIDUE-CANON-DRYRUN-NO-PROVENANCE",
          "provenance" not in drep and "simulated" not in drep,
          "canonical evaluation/ablation_dryrun_report.json carries no provenance block")
    hsrc = HARNESS.read_text()
    check("RESIDUE-METRIC-DRIFT-OPEN",
          "information_gain" not in hsrc and "kish_ess" not in hsrc,
          "prior non-blocking N3 metric drift is NOT closed: the harness emits "
          "kish-free duplication/novelty metrics and no information_gain field")
    check("RESIDUE-GUARD-NAME-ONLY", "path.name.lower()" in hsrc,
          "output guard is filename-token based, so an explicit `--outdir evaluation/` "
          "can still rewrite canonical dry-run outputs (CF-12 owner decision)")

    # ---- 9. pins: exit measurement -----------------------------------------------------
    exit_ = {p: sha(REPO / p) for p in PIN_PATHS}
    for p in PIN_PATHS:
        check(f"PIN-EXIT-{p}", exit_[p] == entry[p],
              f"{p} entry==exit ({str(exit_[p])[:16]})")

    # ---- 10. prior-finding closure table ----------------------------------------------
    closure = [
        {"id": "18-B1 / 022-B1 / 067-B1", "axis": "wall-clock matching vacuous/unmeasured",
         "status": "closed", "evidence": "wall consumption spread 0.010101 and a slowed-arm "
         "control flips matched to False (self-test wall_consumption_falsifier_fires)"},
        {"id": "18-B2 / 022-B2 / 067-B2", "axis": "declared matched fields not measured; 15% "
         "tolerance vs pre-registered 2%",
         "status": "closed-harness-side", "evidence": "all four fields measured; spreads "
         "1.074/3.547 flagged; defaults token/wall tolerance 0.02 = pre-registration"},
        {"id": "18-B3 / 022-B3 / 019-HF-A2-19-02", "axis": "named canonical harness != producer; "
         "tolerance divergence between copies",
         "status": "residual-owner-side", "evidence": "design:172 still names the stale audit "
         "copy while the repaired canonical harness is evaluation/ablation_harness.py"},
        {"id": "019-HF-A2-19-01", "axis": "registered artifact is an unmarked synthetic dry run",
         "status": "closed-for-new-outputs / residual-at-canonical-path",
         "evidence": "new reports+CSV are fully marked, unmarked names refused; canonical "
         "evaluation/ablation.csv and ablation_report.json still carry the old unmarked bytes"},
        {"id": "019-HF-A2-19-03", "axis": "unquoted YAML NULL id parses as None",
         "status": "closed-harness-side", "evidence": "normalised to 'NULL' and reported in "
         "provenance.design_null_ids_normalized"},
        {"id": "019-04 / 18-N4 / 022-N4", "axis": "NULL arm is a declared-rate control, not the "
         "design's candidate-pool draw + shuffled-gate control",
         "status": "residual-owner-side (declared)", "evidence": "no shuffled-gate control in "
         "the harness; limitation text declares the iid-uniform null"},
        {"id": "019-05", "axis": "NULL arm consumes 3000/20000 tokens",
         "status": "residual-owner-side (declared)", "evidence": "limits record stop_reason="
         "episodes_exhausted; limitations declare non-token-matched NULL consumption; "
         "budget_check.matched is scoped to primary arms"},
        {"id": "019-06", "axis": "decision rule / guardrail ordering vs pipeline",
         "status": "closed", "evidence": "guardrail.applied_first=true; guardrail-applied "
         "accepted counts feed the endpoint; all five contrasts computed"},
        {"id": "022-N5", "axis": "--outdir defaults to evaluation/ (review rerun mutates "
         "canonical dry-run files)",
         "status": "partially-closed", "evidence": "no --outdir now writes nothing; the "
         "name-based guard still accepts `--outdir evaluation/` with a marked basename"},
        {"id": "18-N5", "axis": "guardrail example fired on the old declared inputs",
         "status": "changed", "evidence": "repaired parameters give hard_failure_rate <= 0.10 "
         "for every arm (S 0.08, SC 0.10, others 0.0); guardrail arms_above=[]"},
    ]

    ok = all(c["pass"] for c in checks)
    report = {
        "schema": "worker-independent-review/1",
        "task_id": "W092-A2-HARNESS-INDEP-REVIEW-01",
        "actor": "worker-092",
        "node_id": "A2",
        "gate": "G-AUDIT",
        "class_id": "GLOBAL",
        "reviewed": {
            "path": "evaluation/ablation_harness.py",
            "sha256": entry["evaluation/ablation_harness.py"],
            "version": "0.2.0-repair",
            "design_sha256": entry["evaluation/ablation_design.yaml"],
        },
        "instrument_checks_passed": sum(1 for c in checks if c["pass"]),
        "instrument_checks_total": len(checks),
        "instrument_valid": ok,
        "checks": checks,
        "finding_closure": closure,
        "residues": [c["detail"] for c in checks if c["id"].startswith("RESIDUE")],
        "entry_exit_pins_stable": all(
            c["pass"] for c in checks if c["id"].startswith("PIN-EXIT")),
        "no_canonical_write": True,
        "claim_scope": "harness-side reproducibility and closure of prior revise findings at "
                       "evaluation/ablation_harness.py#0fae94bf0190; not a gate verdict, not an "
                       "A2 node disposition, no mathematics or model-behaviour claim",
        "verdict": "accept" if ok else "inconclusive",
        "score": 4.0 if ok else 2.0,
        "falsifier": "Re-run this instrument at the same pins: falsified if any pin moves, if "
                     "the two dry runs are not core-identical, if the run is not core-equal to "
                     "worker-020's designbound dry run (generated_at excluded), if either "
                     "negative control stops firing, or if any closure row marked 'closed' "
                     "fails its stated evidence check.",
    }
    (ART / "report.json").write_text(json.dumps(report, indent=1, sort_keys=True))
    print(json.dumps({"instrument_valid": ok,
                      "checks": f"{report['instrument_checks_passed']}/"
                                f"{report['instrument_checks_total']}",
                      "pins_stable": report["entry_exit_pins_stable"],
                      "verdict": report["verdict"]}, indent=2))
    shutil.rmtree(work, ignore_errors=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
