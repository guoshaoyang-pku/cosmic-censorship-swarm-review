#!/usr/bin/env python3
"""Independent audit of the A2 ablation harness dry-run report.

Reads only the *output* of evaluation/ablation_harness.py (the dry-run JSON and CSV) plus
the harness bytes for hash binding.  It does not import the harness and does not trust the
harness's own ``budget_check`` field: every budget claim is recomputed from the raw per-arm
records.

Falsifier under test (from assignment asg-2026-09-11-A2-deepseek-flash-20-29):
    "Harness compares arms at unequal token budget."

Positive controls (mutated copies) prove the audit has teeth: if the comparison really were
unmatched in any of four ways (spread, unequal caps, overspend, wall-limited), the audit
must flip to unmatched.  No network, no model calls.

Usage:
    python3 artifacts/worker-20/a2_independent_budget_check.py <report.json> <report.csv>
"""
from __future__ import annotations

import copy
import csv
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
METRICS = (
    "accepted_claim_rate", "hard_failure_rate", "citation_support", "duplication",
    "reviewer_agreement", "novel_accepted_coverage", "cost_per_accepted_claim",
    "per_class_coverage",
)
CLASSES = ("AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH")
EXPECTED_ARMS = {"strong_single", "self_consistency", "independent_cheap",
                 "cheap_coordinator", "random_iid_null"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(report: dict) -> dict:
    """Recompute the matched-budget verdict from raw arm records.  Returns violations."""
    v: list[str] = []
    arms = report["arms"]
    by_name = {a["arm"]: a for a in arms}
    primary = [a for a in arms if a["is_primary"]]

    if set(by_name) != EXPECTED_ARMS:
        v.append(f"arm set mismatch: {sorted(by_name)}")
    if len(primary) != 4:
        v.append(f"expected 4 primary arms, found {len(primary)}")
    if not any(a["is_null"] and not a["is_primary"] for a in arms):
        v.append("no non-primary null control arm")

    # C1 -- identical enforced caps across primary arms
    caps = {(a["token_budget"], a["wall_budget"]) for a in primary}
    if len(caps) != 1:
        v.append(f"unequal enforced caps across primary arms: {sorted(caps)}")

    # C2 -- no arm overspends either cap
    for a in arms:
        if a["tokens_consumed"] > a["token_budget"] + 1e-9:
            v.append(f"{a['arm']}: token overspend "
                     f"{a['tokens_consumed']} > {a['token_budget']}")
        if a["wall_consumed"] > a["wall_budget"] + 1e-9:
            v.append(f"{a['arm']}: wall overspend "
                     f"{a['wall_consumed']} > {a['wall_budget']}")

    # C3 -- the binding resource is the token budget for every primary arm
    for a in primary:
        if a["stop_reason"] != "token_budget":
            v.append(f"{a['arm']}: primary arm not token-limited "
                     f"(stop_reason={a['stop_reason']})")
        if a["wall_consumed"] >= a["wall_budget"] - 1e-9:
            v.append(f"{a['arm']}: primary arm wall-clock saturated")

    # C4 -- token consumption spread inside the pre-registered tolerance
    tol = float(report["config"]["token_tolerance"])
    if primary:
        consumed = [a["tokens_consumed"] for a in primary]
        spread = (max(consumed) - min(consumed)) / max(1.0, primary[0]["token_budget"])
        if spread > tol:
            v.append(f"token spread {spread:.4f} > tolerance {tol}")
    else:
        spread = None

    # C5 -- all eight pre-registered metrics present on every arm, no scalar score
    if tuple(report.get("pre_registered_metrics", ())) != METRICS:
        v.append("pre_registered_metrics does not match the eight declared metrics")
    for a in arms:
        for m in METRICS:
            if m not in a:
                v.append(f"{a['arm']}: missing metric {m}")
    pcc = by_name.get("strong_single", {}).get("per_class_coverage")
    if not isinstance(pcc, dict) or set(pcc) != set(CLASSES):
        v.append("per_class_coverage does not cover the four frozen classes")
    if report.get("no_universal_scalar_score") is not True:
        v.append("report does not assert no_universal_scalar_score")
    for k in ("score", "total_score", "combined_score"):
        if k in report:
            v.append(f"report carries a universal scalar field: {k}")

    return {"matched": not v, "violations": v, "token_spread_fraction": spread,
            "caps": sorted(caps), "binding": {a["arm"]: a["stop_reason"] for a in primary}}


def main() -> int:
    rep_path, csv_path = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    harness = ROOT / "evaluation" / "ablation_harness.py"
    report = json.loads(rep_path.read_text())

    checks = []

    def rec(name, ok, detail):
        checks.append({"name": name, "pass": bool(ok), "detail": detail})

    # 0 -- report is bound to the canonical harness bytes
    rec("generator_hash_binds_canonical_harness",
        report.get("generator_sha256") == sha256(harness),
        f"report={report.get('generator_sha256', '')[:12]} harness={sha256(harness)[:12]}")

    # 1 -- identity/class binding of the artifact under audit
    rec("node_class_gate",
        report.get("node_id") == "A2" and report.get("class_id") == "GLOBAL"
        and report.get("gate") == "G-AUDIT",
        f"node={report.get('node_id')} class={report.get('class_id')} gate={report.get('gate')}")

    # 2 -- the primary audit, recomputed from raw records
    base = audit(report)
    rec("matched_budget_recomputed_from_raw", base["matched"],
        f"spread={base['token_spread_fraction']} violations={base['violations']}")

    # 3 -- the harness's own verdict agrees with the independent recomputation
    hb = report["budget_check"]
    rec("harness_and_independent_verdict_agree",
        bool(hb["matched"]) == base["matched"] and not hb["violations"],
        f"harness matched={hb['matched']} limits={len(hb['limits'])}")

    # 4..7 -- positive controls: mutate a copy, the audit must reject each falsifier
    def control(name, mutate, needle):
        bad = copy.deepcopy(report)
        mutate(bad)
        res = audit(bad)
        hit = (not res["matched"]) and any(needle in x for x in res["violations"])
        rec(name, hit,
            f"flags={[x for x in res['violations'] if needle in x][:1]}")

    def spread_mut(b):
        for a in b["arms"]:
            if a["arm"] == "self_consistency":
                a["tokens_consumed"] = a["token_budget"] * 0.5

    def caps_mut(b):
        for a in b["arms"]:
            if a["arm"] == "independent_cheap":
                a["token_budget"] += 1000

    def overspend_mut(b):
        for a in b["arms"]:
            if a["arm"] == "strong_single":
                a["tokens_consumed"] = a["token_budget"] + 1.0

    def wall_mut(b):
        for a in b["arms"]:
            if a["arm"] == "cheap_coordinator":
                a["stop_reason"] = "wall_clock"

    control("control_unequal_token_consumption_rejected", spread_mut, "token spread")
    control("control_unequal_caps_rejected", caps_mut, "unequal enforced caps")
    control("control_overspend_rejected", overspend_mut, "overspend")
    control("control_wall_limited_rejected", wall_mut, "not token-limited")

    # 8 -- CSV agrees with JSON on per-arm cost/outcome
    rows = {r["arm"]: r for r in csv.DictReader(csv_path.open())}
    ok_csv = set(rows) == set(EXPECTED_ARMS)
    detail_csv = []
    for name, row in rows.items():
        j = next(a for a in report["arms"] if a["arm"] == name)
        same = (abs(float(row["tokens_consumed"]) - j["tokens_consumed"]) < 1e-6
                and int(row["accepted"]) == j["accepted"])
        if not same:
            ok_csv = False
            detail_csv.append(name)
    rec("csv_matches_json", ok_csv,
        f"rows={len(rows)} mismatches={detail_csv}")

    # 9 -- determinism: two fresh harness runs reproduce the numeric report
    import subprocess
    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix="a2det_", dir=str(ROOT / "artifacts" / "worker-20")))
    outs = []
    for i in range(2):
        p = tmp / f"run{i}.json"
        subprocess.run([sys.executable, str(harness), "--dry-run", "--json-out", str(p)],
                       check=True, capture_output=True, text=True, cwd=str(ROOT))
        d = json.loads(p.read_text())
        d.pop("generated_at", None)
        outs.append(d)
    rec("deterministic_two_fresh_runs", outs[0] == outs[1],
        f"identical numeric report: {outs[0] == outs[1]}")
    for p in tmp.glob("*"):
        p.unlink()
    tmp.rmdir()

    result = {
        "artifact": "A2-independent-budget-check",
        "node_id": "A2",
        "class_id": "GLOBAL",
        "gate": "G-AUDIT",
        "falsifier": "Harness compares arms at unequal token budget.",
        "falsifier_triggered": not base["matched"],
        "audited_report": {"path": str(rep_path.relative_to(ROOT)), "sha256": sha256(rep_path)},
        "audited_csv": {"path": str(csv_path.relative_to(ROOT)), "sha256": sha256(csv_path)},
        "audited_harness": {"path": "evaluation/ablation_harness.py", "sha256": sha256(harness)},
        "checks": checks,
        "checks_passed": sum(c["pass"] for c in checks),
        "checks_total": len(checks),
        "audit_pass": all(c["pass"] for c in checks),
        "controls": {c["name"]: c["pass"] for c in checks if c["name"].startswith("control_")},
        "independent_recomputation": base,
        "limitations": [
            "verdict is about the harness mechanism on synthetic inputs, not about any model",
            "token matching forces different episode prefixes per arm (strong=50, self_consistency=10,"
            " independent_cheap=33, cheap_coordinator=31); rate metrics are therefore computed over"
            " different episode subsets and are not directly comparable as measured effect sizes",
            "wall-clock caps are equal and never binding, so wall-clock is matched as a cap but is"
            " not an active constraint under the default config",
            "author of the harness and auditor of this run share agent slot deepseek-flash-20"
            " (different process instances); an independent third-party review is still required",
        ],
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["audit_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
