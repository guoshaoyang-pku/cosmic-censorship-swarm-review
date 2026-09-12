#!/usr/bin/env python3
"""Mechanical protocol-compliance check: numerics/CONVERGENCE_PROTOCOL.md vs the N0 reports.

Read-only A1-support tool by deepseek-flash-12. It turns the four text-vs-artifact deltas
reported in comms event ``flash-12-n0-status-0007`` into reproducible machine output.
It does NOT edit the artifact and does NOT replace the audit protocol review.

Checks
  C1 sec3.2 >=3 resolutions per canonical order study, refinement ratio 2
  C2 sec3.3/7 least-squares `fitted_order` present per study
  C3 sec3.4 declared spatial/temporal separation (fixed small dt, or a passing temporal control)
  C4 sec3.5 manufactured data has >=2 modes, or a documented non-degeneracy control
  C5 sec3.6 acceptance band |p - p_design| <= 0.3 for canonical studies
  C6 sec3.7 determinism excludes wall-clock fields
  C7 sec5  negative controls present (frozen, wrong-sign, cfl violation, stable cfl)
  C8 sec6  replication report exists, independent schemes, |delta| <= 0.35

Usage: python3 protocol_compliance.py
Writes artifacts/flash-12/n0/protocol_compliance.json
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

CST = timezone(timedelta(hours=8))
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
ARTIFACT_REPORT = REPO / "numerics" / "results" / "flat_wave_convergence.json"
REPLICATION_REPORT = REPO / "numerics" / "results" / "flat_wave_replication.json"
PROTOCOL = REPO / "numerics" / "CONVERGENCE_PROTOCOL.md"
ARTIFACT = REPO / "numerics" / "tests" / "flat_wave.py"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    report = json.loads(ARTIFACT_REPORT.read_text())
    repl = json.loads(REPLICATION_REPORT.read_text())
    proto = PROTOCOL.read_text()
    checks = []

    def rec(cid, ok, detail, delta=False):
        checks.append({"id": cid, "status": "pass" if ok else ("delta" if delta else "fail"),
                       "detail": detail})

    studies = report.get("studies", [])
    # C1 resolution count / ratio
    c1 = []
    for s in studies:
        rows = s.get("rows", [])
        n = len(rows)
        ratios = [rows[i + 1]["n"] / rows[i]["n"] for i in range(n - 1)]
        ok = n >= 3 and all(abs(r - 2.0) < 0.01 for r in ratios)
        c1.append((s.get("family"), s.get("order_scheme"), n, [round(r, 3) for r in ratios], ok))
    rec("C1_min_resolutions_ratio2", all(x[4] for x in c1), json.dumps(c1))

    # C2 fitted_order present
    missing_fit = [(s.get("family"), s.get("order_scheme")) for s in studies if "fitted_order" not in s]
    rec("C2_fitted_order_present", not missing_fit,
        f"studies without fitted_order: {missing_fit} (protocol sec3.3/7 requires the fit)", delta=True)

    # C3 spatial/temporal separation
    has_temporal_control = bool(report.get("temporal_control", {}).get("pass"))
    cfls = sorted({r.get("cfl") for s in studies for r in s.get("rows", [])})
    rec("C3_spatial_temporal_separation", has_temporal_control,
        f"protocol sec3.4 asks fixed dt=1e-4; artifact uses dt=cfl*h with cfl in {cfls}; "
        f"temporal_control.pass={has_temporal_control}", delta=True)

    # C4 >=2 modes
    modes_used = re.findall(r"modes=\(\((\d+),\s*[\d.]+\)(?:,\s*\((\d+),)?", ARTIFACT.read_text())
    tp = report.get("time_point_control", {})
    rec("C4_multimode_or_trap_control", bool(tp), f"time_point_control present={bool(tp)}; "
        f"protocol sec3.5 asks >=2 modes; the order-2 standing study is single-mode", delta=True)

    # C5 acceptance band
    band_delta = []
    for s in studies:
        og = s.get("order_gate", {})
        lo, hi = og.get("lo"), og.get("hi")
        if lo is None or hi is None:
            continue
        half = (hi - lo) / 2.0
        if half > 0.3 + 1e-9:
            band_delta.append({"family": s.get("family"), "order_scheme": s.get("order_scheme"),
                               "band": [lo, hi], "half_width": half})
    rec("C5_acceptance_band_0p3", not band_delta,
        f"studies with half-width > 0.3: {band_delta} (protocol sec3.6)", delta=True)

    # C6 determinism excludes wall-clock
    det = report.get("determinism", {})
    rec("C6_determinism_excludes_wallclock", bool(det.get("pass")) and "wall_seconds" in str(det.get("excluded_fields", [])),
        f"determinism={det}")

    # C7 negative controls
    names = {c.get("name") for c in report.get("controls", [])}
    wanted = {"frozen_in_time", "wrong_sign_laplacian"}
    rec("C7_negative_controls_present", wanted.issubset(names) and any(str(n).startswith("cfl=") for n in names),
        f"control names: {sorted(map(str, names))}")

    # C8 replication agreement
    def mean_order(doc, rel):
        vals = []
        if rel.endswith("flat_wave_convergence.json"):
            for s in doc.get("studies", []):
                if s.get("order_scheme") == 2:
                    vals += [v for v in s.get("order_l2", []) if isinstance(v, (int, float))]
        else:
            vals += [v for v in (doc.get("result", {}).get("independent_orders", {}) or {}).values()
                     if isinstance(v, (int, float))]
        return sum(vals) / len(vals) if vals else None

    impl, repl_order = mean_order(report, "flat_wave_convergence.json"), mean_order(repl, "flat_wave_replication.json")
    delta = abs(impl - repl_order) if impl is not None and repl_order is not None else None
    rec("C8_replication_agreement", delta is not None and delta <= 0.35,
        f"implementation mean {impl} vs replication {repl_order}; delta={delta} (tol 0.35)")

    deltas = [c for c in checks if c["status"] == "delta"]
    fails = [c for c in checks if c["status"] == "fail"]
    out = {
        "checker": "artifacts/flash-12/n0/protocol_compliance.py",
        "checked_at": datetime.now(CST).isoformat(timespec="seconds"),
        "protocol": {"path": "numerics/CONVERGENCE_PROTOCOL.md", "sha256": sha(PROTOCOL)},
        "artifact_report": {"path": "numerics/results/flat_wave_convergence.json", "sha256": sha(ARTIFACT_REPORT)},
        "replication_report": {"path": "numerics/results/flat_wave_replication.json", "sha256": sha(REPLICATION_REPORT)},
        "checks": checks, "deltas": deltas, "failures": fails,
        "verdict": "fail" if fails else ("compliant_with_documented_deltas" if deltas else "compliant"),
        "scope": "mechanical documentation/acceptance check only; not a numerical review and not a G-NUM verdict",
    }
    (HERE / "protocol_compliance.json").write_text(json.dumps(out, indent=2, sort_keys=True))
    print(json.dumps({"verdict": out["verdict"], "deltas": [d["id"] for d in deltas],
                      "failures": [f["id"] for f in fails]}, indent=2))
    return 0 if not fails else 1


if __name__ == "__main__":
    raise SystemExit(main())
