#!/usr/bin/env python3
"""Lead independent 4-rung replication order study (N0, flat space).

Read-only driver: imports the pinned replication module
``numerics/tests/flat_wave_replication.py`` and calls its public
``order_study`` at the harness resolutions plus one extra refinement
(``dr = 0.025``).  It does not edit any pinned artifact.

Purpose: close the audit finding that the replication evidence used only three
resolutions, and attach the R5-style uncertainty to the order fits.

Usage:
    python3 numerics/protocol/lead_4rung_replication.py \
        --json-out artifacts/numerics/n0/lead_4rung_replication.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import sys
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "numerics" / "tests"))

import flat_wave_replication as repl  # noqa: E402

DRS_3 = [0.2, 0.1, 0.05]
DRS_4 = [0.2, 0.1, 0.05, 0.025]
SCHEMES = ["lffd", "cnfd", "cnfem"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fit_uncertainty(drs, errs):
    """Least-squares slope standard error for log(err) vs log(dr)."""
    x = np.log(np.asarray(drs, float))
    y = np.log(np.asarray(errs, float))
    coeffs, cov = np.polyfit(x, y, 1, cov=True)
    se = float(math.sqrt(max(cov[0, 0], 0.0)))
    return float(coeffs[0]), se


def study_block(scheme):
    st4 = repl.order_study(scheme, dr_values=DRS_4, cfl=0.5, r_max=30.0, t_end=6.0)
    errs = [r["l2_error"] for r in st4["rows"]]
    p4, se4 = fit_uncertainty(DRS_4, errs)
    p3, se3 = fit_uncertainty(DRS_3, errs[:3])
    pair = repl.pair_orders(DRS_4, errs)
    half_range = (max(pair) - min(pair)) / 2.0
    return {
        "scheme": scheme,
        "dr_values": DRS_4,
        "rows": [
            {"dr": r["dr"], "dt": r["dt"], "steps": r["steps"], "l2_error": r["l2_error"]}
            for r in st4["rows"]
        ],
        "pair_orders": pair,
        "fit_order_3rung": p3,
        "fit_order_4rung": p4,
        "uncertainty": {
            "pair_spread_half_range": half_range,
            "least_squares_standard_error": se4,
            "reported_delta": max(half_range, se4),
        },
        "monotone": st4["monotone"],
        "within_harness_tol": st4["within_harness_tol"],
        "uncertainty_3rung_standard_error": se3,
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--json-out", default=None)
    args = ap.parse_args(argv)

    t0 = time.time()
    # Fail-closed control: the pinned module's own self-test must pass first.
    selftest_pass = bool(repl.selftest(verbose=False))
    if not selftest_pass:
        raise SystemExit("ABORT: flat_wave_replication selftest failed at the pinned revision")

    studies = {s: study_block(s) for s in SCHEMES}

    def agree(a, b):
        da = studies[a]["uncertainty"]["reported_delta"]
        db = studies[b]["uncertainty"]["reported_delta"]
        diff = abs(studies[a]["fit_order_4rung"] - studies[b]["fit_order_4rung"])
        floor = max(0.25, math.sqrt(da * da + db * db))
        return {
            "schemes": [a, b],
            "delta_order": diff,
            "agreement_floor": floor,
            "rule": "|pA - pB| <= max(0.25, sqrt(dA^2 + dB^2))",
            "agree": bool(diff <= floor),
        }

    report = {
        "artifact": "lead independent 4-rung replication order study",
        "node_id": "N0",
        "gate": "G-NUM",
        "class_id": "AF-WCC-SCALAR-SPH",
        "class_binding": "calibration sub-case (test-field, fixed Minkowski); N0 does not exercise the Einstein-coupled class",
        "conclusion_type": "numerical_evidence",
        "claims_not_made": [
            "no physics claim; no cosmic-censorship claim",
            "no gate verdict: this report is evidence for a lead G-NUM proposal, not a verdict",
        ],
        "config": {"dr_values": DRS_4, "cfl": 0.5, "r_max": 30.0, "t_end": 6.0, "p_expected": 2.0},
        "selftest_pass": selftest_pass,
        "studies": studies,
        "agreement_pairs": [agree("cnfd", "lffd"), agree("cnfem", "lffd"), agree("cnfem", "cnfd")],
        "provenance": {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "driver_sha256": sha256(Path(__file__)),
            "replication_module_sha256": sha256(REPO / "numerics" / "tests" / "flat_wave_replication.py"),
            "reference_scheme_note": "lffd is the reference-family control; cnfd/cnfem are the independent schemes",
            "numpy": np.__version__,
            "platform": platform.platform(),
            "python": sys.version.split()[0],
            "wall_seconds": None,
        },
        "validation_status": "unverified",
    }
    report["provenance"]["wall_seconds"] = round(time.time() - t0, 3)

    text = json.dumps(report, indent=2, sort_keys=True)
    if args.json_out:
        out = Path(args.json_out)
        if not out.is_absolute():
            out = REPO / out
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text + "\n")
        print(f"wrote {out}")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
