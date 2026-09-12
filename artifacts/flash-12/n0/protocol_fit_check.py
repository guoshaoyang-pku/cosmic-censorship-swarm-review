#!/usr/bin/env python3
"""N0 protocol-delta closure probe: least-squares ``fitted_order`` + canonical band.

Class binding: ``AF-WCC-SCALAR-SPH`` | node ``N0`` | gate ``G-NUM`` (numerics_lock LOCKED,
flat-space only).  Worker: ``deepseek-flash-12``.

Why this file exists
--------------------
``flash-12-n0-artifact-0007`` recorded two protocol deltas against the accepted canonical
artifact ``numerics/tests/flat_wave.py`` (sha256 ``8b52014dac47...``):

* **C2** -- the canonical report has no ``fitted_order`` per study, while
  ``numerics/CONVERGENCE_PROTOCOL.md`` sec3.3/sec7 require the least-squares fit and say
  "order claims use the fit";
* **C5** -- the implemented order-4 acceptance band is +-0.4 while sec3.6 sets +-0.3.

This probe *does not edit the frozen artifact* (that would invalidate the lead review pin
and the map's frozen hash).  It reads the hash-pinned canonical report, recomputes the
missing statistic from the report's own rows, and decides whether the deltas are
documentation-only or substantive:

* if every canonical study's fitted order is inside ``|p - p_design| <= 0.3``, the C2/C5
  deltas cannot hide an order failure -- C2 is a schema omission and C5 a band width that
  is wider than needed at the fit level;
* if any fitted order falls outside the canonical band, the deltas are substantive and the
  artifact's order claim fails under its own protocol (a finding, not a smoothing-over).

The falsifier is machine-checkable: any fitted ``|p - p_design| > 0.3``, or any recomputed
pairwise order disagreeing with the report's stored ``order_l2`` by more than 1e-9, falsifies
the closure verdict.

Scope: mechanical/numerical documentation check.  Not a physics review, not a G-NUM verdict,
sets no node status, claims no completion.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]  # artifacts/flash-12/n0/<this> -> repo root
CANONICAL_REPORT = "numerics/results/flat_wave_convergence.json"
REPLICATION_REPORT = "numerics/results/flat_wave_replication.json"
CANONICAL_ARTIFACT = "numerics/tests/flat_wave.py"
PROTOCOL = "numerics/CONVERGENCE_PROTOCOL.md"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def lsq_fit_order(xs, ys):
    """OLS slope of log(e) vs log(h) with R^2 and slope standard error."""
    n = len(xs)
    if n < 2:
        raise ValueError("need >= 2 points for a fit")
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    slope = sxy / sxx
    intercept = my - slope * mx
    resid = [y - (intercept + slope * x) for x, y in zip(xs, ys)]
    sse = sum(r * r for r in resid)
    sst = sum((y - my) ** 2 for y in ys)
    r2 = 1.0 - sse / sst if sst > 0 else float("nan")
    se = math.sqrt((sse / (n - 2)) / sxx) if n > 2 and sse > 0 else 0.0
    return {
        "fitted_order": slope,
        "intercept": intercept,
        "r2": r2,
        "slope_stderr": se,
        "max_abs_log_residual": max(abs(r) for r in resid),
        "n_points": n,
    }


def pairwise_orders(xs, ys):
    out = []
    for i in range(len(xs) - 1):
        out.append(math.log(ys[i] / ys[i + 1]) / math.log(xs[i] / xs[i + 1]))
    return out


def canonical_study_checks(rep, band=0.3):
    studies = []
    for s in rep["studies"]:
        rows = s["rows"]
        h = [r["dx"] for r in rows]
        e_l2 = [r["l2_error"] for r in rows]
        e_linf = [r["linf_error"] for r in rows]
        fit_l2 = lsq_fit_order([math.log(v) for v in h], [math.log(v) for v in e_l2])
        fit_linf = lsq_fit_order([math.log(v) for v in h], [math.log(v) for v in e_linf])
        pair_l2 = pairwise_orders(h, e_l2)
        stored = s.get("order_l2", [])
        max_pair_delta = max((abs(a - b) for a, b in zip(pair_l2, stored)), default=float("nan"))
        ratios = [h[i] / h[i + 1] for i in range(len(h) - 1)]
        p = s["order_scheme"]
        pair_violations = [
            {"pair": i, "order": round(v, 4), "deviation": round(abs(v - p), 4)}
            for i, v in enumerate(pair_l2) if abs(v - p) > band
        ]
        studies.append({
            "family": s["family"],
            "order_scheme": p,
            "n_resolutions": len(rows),
            "refinement_ratios": ratios,
            "refinement_ratio_2": all(abs(r - 2.0) < 1e-9 for r in ratios),
            "fitted_order_l2": fit_l2,
            "fitted_order_linf": fit_linf,
            "pairwise_order_l2_recomputed": pair_l2,
            "pairwise_order_l2_stored": stored,
            "max_pairwise_recompute_delta": max_pair_delta,
            "recompute_matches_stored": bool(max_pair_delta <= 1e-9),
            "canonical_band_half_width": band,
            "fit_l2_within_canonical_band": bool(abs(fit_l2["fitted_order"] - p) <= band),
            "fit_linf_within_canonical_band": bool(abs(fit_linf["fitted_order"] - p) <= band),
            "fit_l2_deviation": abs(fit_l2["fitted_order"] - p),
            "implemented_gate_band": s.get("order_gate"),
            "implemented_band_half_width": (
                None if not s.get("order_gate") else
                (s["order_gate"]["hi"] - s["order_gate"]["lo"]) / 2.0),
            "pairwise_canonical_band_violations": pair_violations,
            "fitted_order_field_present_in_report": "fitted_order" in s,
        })
    return studies


def replication_checks(rep):
    out = []
    for s in rep.get("order_studies", []):
        rows = s["rows"]
        h = [r["dr"] for r in rows]
        e = [r["l2_error"] for r in rows]
        fit = lsq_fit_order([math.log(v) for v in h], [math.log(v) for v in e])
        out.append({
            "scheme": s["scheme"],
            "n_resolutions": len(rows),
            "fitted_order_recomputed": fit["fitted_order"],
            "fit_order_stored_in_report": s.get("fit_order"),
            "recompute_delta_vs_stored": abs(fit["fitted_order"] - float(s.get("fit_order", float("nan")))),
            "pair_orders_stored": s.get("pair_orders"),
            "within_harness_tol": s.get("within_harness_tol"),
        })
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--report", default=CANONICAL_REPORT)
    ap.add_argument("--replication", default=REPLICATION_REPORT)
    ap.add_argument("--json-out", default=None)
    ap.add_argument("--band", type=float, default=0.3)
    args = ap.parse_args(argv)

    canon_path = ROOT / args.report
    repl_path = ROOT / args.replication
    artifact_path = ROOT / CANONICAL_ARTIFACT
    protocol_path = ROOT / PROTOCOL
    canon = json.loads(canon_path.read_text())
    repl = json.loads(repl_path.read_text())
    artifact_sha = sha256_file(artifact_path)
    protocol_sha = sha256_file(protocol_path)

    declared_sha = canon.get("provenance", {}).get("script_sha256")
    pinned_ok = declared_sha == artifact_sha

    studies = canonical_study_checks(canon, band=args.band)
    repl_rows = replication_checks(repl)

    # C2/C5 verdict: does the fit statistic (protocol sec3.3 "order claims use the fit")
    # pass the canonical band on every canonical study?
    fit_band_ok = all(s["fit_l2_within_canonical_band"] and s["fit_linf_within_canonical_band"]
                      for s in studies)
    recompute_ok = all(s["recompute_matches_stored"] for s in studies)
    ratio_ok = all(s["refinement_ratio_2"] for s in studies)
    fitted_field_missing = any(not s["fitted_order_field_present_in_report"] for s in studies)
    wider_band = any((s["implemented_band_half_width"] or 0) > args.band + 1e-12 for s in studies)
    pair_viol = [{"family": s["family"], "order_scheme": s["order_scheme"], **v}
                 for s in studies for v in s["pairwise_canonical_band_violations"]]

    # Replication agreement at the fit statistic (protocol sec6: agree within 0.35).
    canon_fit_mean = (sum(s["fitted_order_l2"]["fitted_order"]
                          for s in studies if s["order_scheme"] == 2) /
                      max(1, sum(1 for s in studies if s["order_scheme"] == 2)))
    agree = []
    for r in repl_rows:
        delta = abs(r["fitted_order_recomputed"] - canon_fit_mean)
        agree.append({"scheme": r["scheme"], "delta_vs_canonical_fit_mean": delta,
                      "within_0p35": bool(delta <= 0.35)})

    deltas = []
    if fitted_field_missing:
        deltas.append({
            "id": "C2_fitted_order_field",
            "status": "closed_at_fit_level" if fit_band_ok else "substantive",
            "detail": "report omits fitted_order; recomputed fit passes the canonical band on "
                      "every study" if fit_band_ok else
                      "report omits fitted_order and a recomputed fit fails the canonical band",
        })
    if wider_band or pair_viol:
        deltas.append({
            "id": "C5_band_width",
            "status": "closed_at_fit_level_with_pairwise_caveat" if fit_band_ok else "substantive",
            "detail": ("implemented order-4 gate band is +-0.4 > canonical +-0.3; the "
                       "least-squares fit (the statistic sec3.3 says order claims use) is "
                       "inside +-0.3, so the wider band is not masking a fit failure; "
                       f"pairwise strict-band violations at the coarse end: {pair_viol}"
                       if fit_band_ok else
                       "wider band accompanies a fit outside the canonical band"),
        })

    verdict = ("deltas_documentation_only" if (fit_band_ok and recompute_ok and ratio_ok)
               else "delta_substantive")
    out = {
        "actor": "deepseek-flash-12",
        "class_id": "AF-WCC-SCALAR-SPH",
        "node_id": "N0",
        "gate": "G-NUM",
        "check_id": "flash12-n0-protocol-fit-closure",
        "scope": ("mechanical closure probe for deltas C2 (missing fitted_order) and C5 "
                  "(order-4 band width) at the pinned canonical artifact hash; not a physics "
                  "review and not a G-NUM verdict"),
        "pinned_inputs": {
            "canonical_artifact": {"path": CANONICAL_ARTIFACT, "sha256": artifact_sha},
            "canonical_report": {"path": args.report, "sha256": sha256_file(canon_path),
                                 "declared_script_sha256": declared_sha,
                                 "report_hash_matches_disk": bool(pinned_ok)},
            "replication_report": {"path": args.replication,
                                   "sha256": sha256_file(repl_path)},
            "protocol": {"path": PROTOCOL, "sha256": protocol_sha,
                         "canonical_band_half_width": args.band},
        },
        "checks": {
            "report_artifact_hash_pinned": bool(pinned_ok),
            "refinement_ratio_2_all_studies": bool(ratio_ok),
            "stored_pairwise_orders_recompute_clean": bool(recompute_ok),
            "all_canonical_fits_within_band": bool(fit_band_ok),
            "c2_fitted_order_field_missing_in_report": bool(fitted_field_missing),
            "c5_implemented_band_wider_than_canonical": bool(wider_band),
            "pairwise_canonical_band_violations": pair_viol,
        },
        "studies": studies,
        "replication_fit_agreement": {
            "canonical_order2_fit_mean": canon_fit_mean,
            "schemes": agree,
            "all_within_protocol_tol_0p35": all(a["within_0p35"] for a in agree),
        },
        "replication_rows": repl_rows,
        "deltas": deltas,
        "verdict": verdict,
        "falsifier": ("any fitted |p - p_design| > 0.3 on a canonical study, or any recomputed "
                      "pairwise order differing from the report's stored order_l2 by > 1e-9, "
                      "falsifies the documentation-only verdict and makes C2/C5 substantive"),
        "next_falsifier": ("re-run after any edit to numerics/tests/flat_wave.py or "
                           "numerics/CONVERGENCE_PROTOCOL.md; the pins "
                           f"{artifact_sha[:12]}/{protocol_sha[:12]} must be re-derived"),
        "claims_completion": False,
        "conclusion_type_of_measurements": "numerical_evidence",
        "validation_status": "unverified",
    }
    text = json.dumps(out, indent=2, sort_keys=True)
    if args.json_out:
        p = ROOT / args.json_out
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        print(f"wrote {p}")
    summary = {
        "verdict": verdict,
        "checks": {k: v for k, v in out["checks"].items()
                   if k != "pairwise_canonical_band_violations"},
        "pairwise_canonical_band_violations": pair_viol,
        "fitted_orders": [
            {"family": s["family"], "order_scheme": s["order_scheme"],
             "fit_l2": round(s["fitted_order_l2"]["fitted_order"], 6),
             "fit_linf": round(s["fitted_order_linf"]["fitted_order"], 6),
             "fit_l2_within_0p3": s["fit_l2_within_canonical_band"]}
            for s in studies],
        "replication_fit_agreement": out["replication_fit_agreement"],
        "deltas": deltas,
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if verdict == "deltas_documentation_only" else 1


if __name__ == "__main__":
    raise SystemExit(main())
