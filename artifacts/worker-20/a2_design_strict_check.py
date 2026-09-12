#!/usr/bin/env python3
"""A2 / G-AUDIT: independent, design-strict audit of the canonical ablation harness.

Worker: deepseek-flash-20 (bounded execution worker, assignment
asg-2026-09-11-A2-deepseek-flash-20-29).

What this does (dry-run evidence only; no model calls, no network):
  1. Binds the ratified design hash and reads its matched-budget tolerance from the
     design text itself (budget_matching.rule: "B (+/-2%)" and "T (+/-2%)").
  2. Binds the canonical harness hash and checks the run report's generator_sha256.
  3. Re-audits the raw per-arm records of a fresh design-driven dry run under the
     DESIGN tolerance, not the harness default, and runs mutation negative controls.

The point of the strict pass is the assignment falsifier "harness compares arms at
unequal token budget": a run whose token spread is inside the harness default (0.15)
but outside the ratified design bound (0.02) must not be reported as matched.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HARNESS = ROOT / "evaluation" / "ablation_harness.py"
DESIGN = ROOT / "evaluation" / "ablation_design.yaml"
AUDIT_LIB = ROOT / "artifacts" / "audit" / "audit_lib.py"
METRICS = (
    "accepted_claim_rate", "hard_failure_rate", "citation_support", "duplication",
    "reviewer_agreement", "novel_accepted_coverage", "cost_per_accepted_claim",
    "per_class_coverage",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def design_tolerance(text: str) -> float:
    """Read the matched-budget bound out of the ratified design rule text."""
    m = re.search(r"\+/-(\d+(?:\.\d+)?)%", text)
    if not m:
        raise SystemExit("design tolerance not found in budget_matching.rule")
    return float(m.group(1)) / 100.0


def strict_audit(report: dict, tol: float) -> dict:
    """Design-strict audit of one harness report. Returns checks + violations."""
    checks: list[dict] = []
    violations: list[str] = []

    def rec(name: str, ok: bool, detail: str) -> None:
        checks.append({"name": name, "pass": bool(ok), "detail": detail})
        if not ok:
            violations.append(f"{name}: {detail}")

    primary = [a for a in report["arms"] if a.get("is_primary")]
    nulls = [a for a in report["arms"] if a.get("is_null")]
    caps = {(a["token_budget"], a["wall_budget"]) for a in primary}

    rec("generator_hash_matches_disk",
        report.get("generator_sha256") == sha256(HARNESS),
        f"report={str(report.get('generator_sha256'))[:12]} disk={sha256(HARNESS)[:12]}")
    rec("four_primary_arms", len(primary) == 4, f"n_primary={len(primary)}")
    rec("identical_enforced_caps", len(caps) == 1, f"caps={sorted(caps)}")
    rec("null_arm_present_and_control_only",
        len(nulls) == 1 and not nulls[0].get("is_primary"),
        f"nulls={[a['arm'] for a in nulls]}")
    rec("null_arm_same_enforced_caps",
        bool(nulls) and all((a["token_budget"], a["wall_budget"]) in caps for a in nulls),
        "null arm must not receive a different budget (design falsifier 3)")

    consumed = [a["tokens_consumed"] for a in primary]
    spread = (max(consumed) - min(consumed)) / max(1.0, primary[0]["token_budget"]) if primary else None
    rec("token_spread_within_design_bound",
        spread is not None and spread <= tol,
        f"spread={spread:.4f} design_tol={tol:.4f} consumed={consumed}")

    overspends = [f"{a['arm']}" for a in report["arms"]
                  if a["tokens_consumed"] > a["token_budget"] + 1e-9
                  or a["wall_consumed"] > a["wall_budget"] + 1e-9]
    rec("no_cap_overspend", not overspends, f"overspends={overspends}")

    not_token_limited = [a["arm"] for a in primary if a.get("stop_reason") != "token_budget"]
    rec("all_primary_token_limited", not not_token_limited, f"other={not_token_limited}")

    missing = {a["arm"]: [m for m in METRICS if m not in a] for a in primary}
    missing = {k: v for k, v in missing.items() if v}
    rec("all_pre_registered_metrics_present", not missing, f"missing={missing}")

    scalar_keys = [k for k in report if k.lower() in ("score", "scalar", "composite", "total_score")]
    rec("no_universal_scalar_score",
        bool(report.get("no_universal_scalar_score")) and not scalar_keys,
        f"flag={report.get('no_universal_scalar_score')} scalar_keys={scalar_keys}")

    cfg_tol = report.get("config", {}).get("token_tolerance")
    rec("enforced_tolerance_recorded", cfg_tol is not None, f"config.token_tolerance={cfg_tol}")

    return {
        "checks": checks,
        "checks_passed": sum(c["pass"] for c in checks),
        "checks_total": len(checks),
        "violations": violations,
        "run_token_spread": spread,
        "design_tolerance": tol,
        "harness_enforced_tolerance": cfg_tol,
        "design_conformance_tolerance_ok": cfg_tol is not None and cfg_tol <= tol,
        "primary_arms": [a["arm"] for a in primary],
        "null_arm": nulls[0]["arm"] if nulls else None,
    }


def mutate(report: dict, fn) -> dict:
    r = copy.deepcopy(report)
    fn(r)
    return r


def _spread_5pct(r: dict) -> None:
    """Token spread 0.05: inside the harness default 0.15, outside the design 0.02."""
    for a in r["arms"]:
        if a["is_primary"] and a["arm"] == "independent_cheap":
            a["tokens_consumed"] = a["token_budget"] * 0.95


def negative_controls(report: dict, tol: float) -> list[dict]:
    """Every mutation must be REJECTED by strict_audit; otherwise the check is blind."""
    def unequal_caps(r):
        for a in r["arms"]:
            if a["arm"] == "cheap_coordinator":
                a["token_budget"] = a["token_budget"] / 2
    def overspend(r):
        for a in r["arms"]:
            if a["arm"] == "strong_single":
                a["tokens_consumed"] = a["token_budget"] + 1
    def wall_limited(r):
        for a in r["arms"]:
            if a["arm"] == "self_consistency":
                a["stop_reason"] = "wall_clock"
    def missing_metric(r):
        for a in r["arms"]:
            if a["arm"] == "strong_single":
                a.pop("per_class_coverage", None)
    def scalar_score(r):
        r["total_score"] = 1.23
    controls = [
        ("spread_5pct_rejected", _spread_5pct),
        ("unequal_caps_rejected", unequal_caps),
        ("overspend_rejected", overspend),
        ("wall_limited_rejected", wall_limited),
        ("missing_metric_rejected", missing_metric),
        ("scalar_score_rejected", scalar_score),
    ]
    out = []
    for name, fn in controls:
        aud = strict_audit(mutate(report, fn), tol)
        out.append({"control": name, "rejected": bool(aud["violations"]),
                    "violations": aud["violations"]})
    return out


def main(argv: list[str]) -> int:
    report_path = Path(argv[1]) if len(argv) > 1 else None
    out_path = Path(argv[2]) if len(argv) > 2 else None
    if report_path is None:
        raise SystemExit("usage: a2_design_strict_check.py <report.json> [out.json]")
    report_path = report_path.resolve()
    report = json.loads(report_path.read_text())
    design_text = DESIGN.read_text()
    tol = design_tolerance(design_text)
    audit = strict_audit(report, tol)
    controls = negative_controls(report, tol)

    # Cross-artifact binding: which harness does the design point at, and which one does
    # the map assignment name as canonical?
    declared = re.search(r"^\s*harness:\s*(\S+)", design_text, re.M)
    declared_path = declared.group(1) if declared else None
    declared_sha = None
    declared_exists = False
    if declared_path:
        p = ROOT / declared_path
        declared_exists = p.exists()
        if declared_exists:
            declared_sha = sha256(p)
    audit_lib_tol = None
    if AUDIT_LIB.exists():
        m = re.search(r"def check_budget_match\(arms: list\[dict\], tol: float = ([\d.]+)\)",
                      AUDIT_LIB.read_text())
        audit_lib_tol = float(m.group(1)) if m else None

    findings = []
    harness_matched = bool(report.get("budget_check", {}).get("matched"))
    if not audit["design_conformance_tolerance_ok"]:
        findings.append({
            "id": "F1-tolerance-loose",
            "severity": "gate-relevant",
            "triggered_on_audited_run": bool(audit["violations"]) and harness_matched,
            "statement": (
                "The canonical harness records token_tolerance="
                f"{audit['harness_enforced_tolerance']} (harness DEFAULTS), while the ratified "
                f"design binds matched budgets at {tol:.2f} and the design-declared harness "
                f"(audit_lib.check_budget_match) defaults to tol={audit_lib_tol}. A run whose "
                f"primary token spread lies in ({tol:.2f}, {audit['harness_enforced_tolerance']}] "
                "is reported budget_matched=true / primary_comparison_valid=true by the canonical "
                "harness, while the design's H-design falsifier (any arm pair outside tolerance "
                "-> the comparison is void, HF-11) declares it void. The harness's per-episode "
                "residual rule tightens the effective bound at the default 20,000-token budget "
                "((20000-19800)/20000=1%) but not at non-default budgets: episode costs are "
                "fixed token counts, so shortfalls scale with the budget."),
            "observed_on_audited_run": {
                "report_token_spread": audit["run_token_spread"],
                "design_tolerance": tol,
                "harness_token_tolerance": audit["harness_enforced_tolerance"],
                "harness_budget_matched": harness_matched,
                "harness_primary_comparison_valid": bool(report.get("primary_comparison_valid")),
                "design_strict_violations": audit["violations"],
            },
            "evidence_refs": [
                f"evaluation/ablation_harness.py#{sha256(HARNESS)[:16]}:70-77 (DEFAULTS token_tolerance 0.15)",
                f"evaluation/ablation_harness.py#{sha256(HARNESS)[:16]}:399-412 (spread + residual checks)",
                f"evaluation/ablation_design.yaml#{sha256(DESIGN)[:16]}:45-49,130-132 (+/-2%, H-design)",
                f"artifacts/audit/audit_lib.py#{sha256(AUDIT_LIB)[:16] if AUDIT_LIB.exists() else 'missing'}:404 (tol=0.02)",
            ],
            "falsifier": (
                "The finding is falsified if no CLI-reachable configuration can produce a "
                "primary token spread in (0.02, 0.15] that the harness reports as "
                "budget_matched=true, or if the harness is shown to take a tolerance <= 0.02 "
                "from the design file or a CLI flag. It is *demonstrated* on this run when "
                "observed_on_audited_run.harness_budget_matched is true while "
                "design_strict_violations is non-empty (small-budget probe: --token-budget 2000, "
                "spread 0.10)."
            ),
        })
    if declared_path and declared_exists and declared_sha != sha256(HARNESS):
        findings.append({
            "id": "F2-harness-path-binding",
            "severity": "binding-ambiguity",
            "statement": (
                f"The design's artifacts.harness points at {declared_path}#{declared_sha[:12]}, "
                f"while the map assignment asg-2026-09-11-A2-deepseek-flash-20-29 names "
                f"evaluation/ablation_harness.py#{sha256(HARNESS)[:12]} as the canonical A2 "
                "artifact. Two distinct implementations both answer to 'A2 harness'; G-AUDIT "
                "must bind exactly one path before any real arm runs."),
            "evidence_refs": [
                f"evaluation/ablation_design.yaml#{sha256(DESIGN)[:16]}:170-175 (artifacts.harness)",
                f"evaluation/ablation_harness.py#{sha256(HARNESS)[:16]} (699 lines)",
                f"{declared_path}#{declared_sha[:16]} (210 lines)" if declared_sha else declared_path,
            ],
            "falsifier": (
                "A gate verdict or controller event names one harness path and both hashes are "
                "reconciled to it; or the design pointer is repointed to the canonical path."
            ),
        })
    wall_consumed = [a["wall_consumed"] for a in report["arms"] if a.get("is_primary")]
    if wall_consumed:
        lo = min(wall_consumed)
        findings.append({
            "id": "F3-wall-clock-semantics",
            "severity": "documentation",
            "statement": (
                "The canonical harness matches wall clock as an equal envelope (identical "
                "wall_budget caps; wall-limited primaries rejected), not as equal consumed wall "
                f"time: observed primary wall_consumed={wall_consumed} "
                f"(envelope {report.get('config', {}).get('wall_budget')}s). The "
                "design's audit_lib.check_budget_match applies its 2% test to a field named "
                "wall_clock_s, which in the lead's dry-run is the envelope. The two checkers "
                "agree on the envelope reading; a reviewer must not feed consumed wall time "
                "into check_budget_match as if it were the envelope."),
            "evidence_refs": [
                f"evaluation/ablation_harness.py#{sha256(HARNESS)[:16]}:389-398 (caps + wall-limited rejection)",
                f"artifacts/audit/audit_lib.py#{sha256(AUDIT_LIB)[:16] if AUDIT_LIB.exists() else 'missing'}:404-419",
            ],
            "falsifier": ("A design amendment states that consumed wall time, not the envelope, "
                          "is the matched field; then the canonical harness is non-conformant."),
        })

    controls_passed = sum(c["rejected"] for c in controls)
    harness_matched = bool(report.get("budget_check", {}).get("matched"))
    result = {
        "checker": "a2_design_strict_check",
        "node_id": "A2",
        "class_id": "GLOBAL",
        "gate": "G-AUDIT",
        "actor": "deepseek-flash-20",
        "created_at": datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds"),
        "report_audited": str(report_path.relative_to(ROOT)),
        "report_sha256": sha256(report_path),
        "harness": {"path": "evaluation/ablation_harness.py", "sha256": sha256(HARNESS)},
        "design": {"path": "evaluation/ablation_design.yaml", "sha256": sha256(DESIGN),
                   "tolerance": tol},
        "design_declared_harness": {"path": declared_path, "sha256": declared_sha,
                                    "exists": declared_exists},
        "assignment_canonical_harness": {"path": "evaluation/ablation_harness.py",
                                         "sha256": sha256(HARNESS)},
        "harness_self_verdict": {
            "budget_matched": harness_matched,
            "primary_comparison_valid": bool(report.get("primary_comparison_valid")),
            "enforced_token_tolerance": audit["harness_enforced_tolerance"],
            "run_token_spread": audit["run_token_spread"],
        },
        "design_conformance_violation_accepted_by_harness": bool(audit["violations"]) and harness_matched,
        "run_audit": audit,
        "negative_controls": controls,
        "negative_controls_passed": controls_passed,
        "negative_controls_total": len(controls),
        "findings": findings,
        "falsifier": ("assignment falsifier on this run: any primary arm whose token consumption "
                      "differs from another by more than the DESIGN bound, unequal enforced caps, "
                      "an overspend, a wall-clock-limited primary, a missing metric, or a report "
                      "whose generator_sha256 differs from the on-disk canonical harness."),
        "falsifier_triggered": bool(audit["violations"]),
        "claims_not_made": [
            "no model call and no network access: the audited run is the synthetic dry run only",
            "no swarm-advantage claim; no arm result is a measurement of a real proposer",
            "no A2 completion claim; worker events cannot move the map or set validation_status",
            "F1/F2/F3 are findings for the design reviewers and G-AUDIT, not gate verdicts",
        ],
        "validation_status": "unverified",
    }
    text = json.dumps(result, indent=2, sort_keys=True)
    if out_path:
        out_path.write_text(text)
        print(f"wrote {out_path}")
    print(json.dumps({
        "checks_passed": f"{audit['checks_passed']}/{audit['checks_total']}",
        "violations": audit["violations"],
        "negative_controls": f"{controls_passed}/{len(controls)}",
        "design_conformance_tolerance_ok": audit["design_conformance_tolerance_ok"],
        "harness_self_verdict": result["harness_self_verdict"],
        "design_conformance_violation_accepted_by_harness":
            result["design_conformance_violation_accepted_by_harness"],
        "findings": [f["id"] for f in findings],
        "falsifier_triggered": bool(audit["violations"]),
    }, indent=2))
    return 0 if (audit["checks_passed"] == audit["checks_total"]
                 and controls_passed == len(controls)) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
